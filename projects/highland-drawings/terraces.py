"""Prepare source-backed terrace, planter, band and guard arrangement."""
import copy
import json
from pathlib import Path

from PIL import ImageDraw, ImageFont

from shell import interpolate

HERE=Path(__file__).resolve().parent
CFG=json.loads((HERE/'terrace-decisions.json').read_text())


def inside(point,polygon):
    x,y=point;result=False
    for a,b in zip(polygon,polygon[1:]+polygon[:1]):
        if (a[1]>y)!=(b[1]>y) and x<(b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0]:result=not result
    return result


def intersection_area(first,second):
    # Exact cell partition for these orthogonal plan polygons.
    xs=sorted({p[0] for p in first+second});ys=sorted({p[1] for p in first+second})
    return sum((b-a)*(d-c) for a,b in zip(xs,xs[1:]) for c,d in zip(ys,ys[1:])
               if inside(((a+b)/2,(c+d)/2),first) and inside(((a+b)/2,(c+d)/2),second))


def reconcile(spec,registrations,out,plans,raster):
    old=copy.deepcopy(next(e for e in spec['roof_features'] if e['id']=='south-clerestory'))
    def points(pixels,registration='R5',anchor=None):
        reg=registrations[registration]
        result=[]
        for x,y in pixels:
            xx=round(interpolate(x,reg['grid_x_pixels'],reg['grid_x_inches']),3)
            yy=round(interpolate(y,reg['grid_y_pixels'],reg['grid_y_inches']),3)
            if anchor=='north-west':
                if x==993:xx=spec['polygons']['r5'][0][0]
                if y==239:yy=spec['polygons']['r5'][0][1]
            if anchor=='north-east' and x==1510:xx=spec['polygons']['r5'][1][0]
            result.append([xx,yy])
        return result
    review=copy.deepcopy(CFG)
    for row in review['surfaces']:
        row['polygon']=points(row['polygon_pixels'],anchor=row.get('anchor'))
        assert intersection_area(row['polygon'],spec['polygons']['r5'])<.001,('terrace enters room',row['id'])
    for i,row in enumerate(review['surfaces']):
        for other in review['surfaces'][i+1:]:
            assert intersection_area(row['polygon'],other['polygon'])<.001,('overlapping terrace zones',row['id'],other['id'])
    for row in review['guards']:
        row['path']=points(row['path_pixels'],anchor=row.get('anchor'))
        assert len(row['band_heights_in'])==len(row['path'])-1
    for row in review['bands']:row['path']=points(row['path_pixels'])
    feature=next(e for e in spec['roof_features'] if e['id']=='south-clerestory')
    feature['polygon']=points(CFG['clerestory_polygon_roof_pixels'],'Roof')
    feature['basis']='A2.08 re-registered clerestory footprint; documented 407.75-foot complete top retained. Body/cap thickness, complete profiles and glazing sections remain assumed.'
    review['clerestory_old_polygon']=old['polygon'];review['clerestory_new_polygon']=feature['polygon']
    review['surface_room_overlap_sq_in']=0;review['surface_surface_overlap_sq_in']=0
    spec['terrace_review']=review;spec['limitations'].extend(CFG['limits'])
    (out/'terrace-review.json').write_text(json.dumps(review,indent=2)+'\n')
    font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',21)
    for name,box in [('R5-terrace-arrangement',(925,215,1550,1020)),('R5-south-terraces',(1070,805,1530,1020))]:
        im=raster(plans[7],box);draw=ImageDraw.Draw(im);scale=200/72/.6
        def project(p):return ((p[0]-box[0])*scale,(p[1]-box[1])*scale)
        for row in CFG['surfaces']:
            color='#875c2d' if row['kind']=='planter' else '#008663'
            draw.line([project(p) for p in row['polygon_pixels']+[row['polygon_pixels'][0]]],fill=color,width=5)
        for row in CFG['guards']:draw.line([project(p) for p in row['path_pixels']],fill='#1265c4',width=7)
        for row in CFG['bands']:
            path=row['path_pixels']+([row['path_pixels'][0]] if row.get('closed') else [])
            draw.line([project(p) for p in path],fill='#bc3f80',width=4)
        draw.text((10,10),'Blue: guards | Green: terraces | Brown: planter | Pink: band/coping paths',fill='#1265c4',font=font,stroke_width=1,stroke_fill='white')
        im.save(out/'source-review'/f'{name}.png')
    return review
