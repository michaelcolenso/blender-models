"""Complete the R5 enclosure audit while preserving the deferred north wall."""
import copy
import json
from pathlib import Path

from PIL import ImageDraw, ImageFont

from shell import interpolate

HERE = Path(__file__).resolve().parent
CFG = json.loads((HERE/'r5-decisions.json').read_text())


def reconcile(spec, registrations, out, plans, raster):
    before = copy.deepcopy(spec)
    reg = registrations['R5']
    def convert(value, axis):
        return round(interpolate(value, reg[f'grid_{axis}_pixels'], reg[f'grid_{axis}_inches']), 3)
    polygon = [[convert(x,'x'),convert(y,'y')] for x,y in CFG['polygon_pixels']]
    # Continue the two deferred north endpoints without shifting their facade.
    polygon[0] = before['polygons']['r5'][0].copy()
    polygon[1] = before['polygons']['r5'][1].copy()
    polygon[2][0] = polygon[1][0]
    polygon[-1][0] = polygon[0][0]
    spec['polygons']['r5'] = polygon
    changes = []
    for row in CFG['openings']:
        old = next(e for e in spec['openings'] if e['id']==row['id'])
        a,b = polygon[row['segment']],polygon[(row['segment']+1)%len(polygon)]
        axis = 0 if row['face']=='south' else 1
        low,high = sorted(convert(p,'x' if axis==0 else 'y') for p in row['jamb_pixels'])
        assert min(a[axis],b[axis])+3 < low < high < max(a[axis],b[axis])-3, (row['id'],a,b,low,high)
        source = f"A2.07 plan / A3.0{2 if row['face']=='west' else 1} {row['face']} elevation; uploaded PDFs"
        entry = dict(id=row['id'],face=row['face'],level='R5',polygon='r5',segment=row['segment'],
            u=(low+high)/2,width=round(high-low,3),z=627+row['sill_in'],height=row['height_in'],
            kind=row['kind'],drawing_mark=row['mark'],status='assumed',xy_status='provisional',
            source=source,source_pixels=old['source_pixels'],source_width_in=round(high-low,3),
            plan_depth_in=a[1-axis],plan_jamb_pixels=row['jamb_pixels'],plan_wall_pixel=row['wall_pixel'],
            geometry_revision=CFG['revision'],basis='A2.07 wall and jamb picks govern provisional XY; actual elevation order/marks identify the opening. No jamb clipping. Sill/head heights, wall and complete frame sections remain assumed.')
        if row['id'] in CFG['south_pair']['ids']:
            entry['opening_group']='south-R5-MO-MJ'
            entry['basis'] += ' '+CFG['south_pair']['basis']
        spec['openings']=[e for e in spec['openings'] if e['id']!=row['id']]+[entry]
        changes.append({'id':entry['id'],'old':old,'new':entry})
    assert len(spec['openings'])==192
    assert [e for e in spec['openings'] if e['face']=='north']==[e for e in before['openings'] if e['face']=='north']
    group = CFG['south_pair']
    spec['opening_groups']=[{
        'id':'south-R5-MO-MJ','level':'R5','segment':6,'openings':group['ids'],
        'outer_jambs_in':[convert(p,'x') for p in group['outer_jamb_pixels']],
        'interface_in':convert(group['interface_pixel'],'x'),'basis':group['basis'],
        'status':'assumed','xy_status':'provisional','source':'A2.07 south glazing band / A3.01 MO and MJ marks'}]
    spec['r5_completion']={
        'revision':CFG['revision'],'source':CFG['source'],'polygon_pixels':CFG['polygon_pixels'],
        'north_tiein':CFG['north_tiein'],'changed_r5_segments':list(range(1,len(polygon))),
        'r5_opening_count':34,'rechecked_south_east_west_openings':len(changes),
        'south_pair':group,'limits':CFG['limits']}
    # Supersede the previous continuation's pending R5 notes; retain other limits.
    spec['limitations']=[s for s in spec['limitations'] if not s.startswith('The southeast R5 corner and adjoining openings are provisionally reconciled.')]
    spec['limitations'].extend(CFG['limits'])
    source_east=convert(1477,'x');source_south=convert(920,'y')
    report={
        'revision':CFG['revision'],'old_polygon':before['polygons']['r5'],'new_polygon':polygon,
        'opening_changes':changes,'opening_groups':spec['opening_groups'],
        'north_tiein':CFG['north_tiein'],
        'retained_north_tiein_model_minus_plan_in':{
            'west_x':round(polygon[0][0]-convert(993,'x'),3),
            'east_x':round(polygon[1][0]-convert(1510,'x'),3),
            'north_y':round(polygon[0][1]-convert(239,'y'),3)},
        'southeast_model_minus_governing_plan_in':{
            'long_east_line':round(polygon[4][0]-source_east,3),
            'south_baseline':round(polygon[6][1]-source_south,3)},
        'limits':CFG['limits'],
        'disposition':'R5 enclosure topology and south/east/west jambs provisionally reconciled; north work deferred and source discrepancies retained.'}
    (out/'r5-completion.json').write_text(json.dumps(report,indent=2)+'\n')
    font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',20)
    for name,box,roof in [('R5-enclosure-completed',(925,210,1545,990),False),
                          ('R5-SW-completed',(975,450,1210,975),False),
                          ('R5-east-completed',(1390,455,1525,945),False),
                          ('R5-MO-MJ-completed',(1360,885,1445,945),False),
                          ('R5-roof-completed',(925,210,1545,990),True)]:
        im=raster(plans[8 if roof else 7],box);draw=ImageDraw.Draw(im);scale=200/72/.6
        registration=registrations['Roof' if roof else 'R5']
        def project(p):
            return ((interpolate(p[0],registration['grid_x_inches'],registration['grid_x_pixels'])-box[0])*scale,
                    (interpolate(p[1],registration['grid_y_inches'],registration['grid_y_pixels'])-box[1])*scale)
        draw.line([project(p) for p in polygon+[polygon[0]]],fill='#1265c4',width=5)
        if not roof:
            draw.line([project(p) for p in before['polygons']['r5']+[before['polygons']['r5'][0]]],fill='#bd473f',width=3)
            for row in CFG['openings']:
                lo,hi=row['jamb_pixels'];c=row['wall_pixel']
                ends=([lo,c],[hi,c]) if row['face']=='south' else ([c,lo],[c,hi])
                points=[((x-box[0])*scale,(y-box[1])*scale) for x,y in ends]
                draw.line(points,fill='#008663',width=7)
                if name not in ('R5-enclosure-completed','R5-MO-MJ-completed'):
                    draw.text((points[0][0]+8,points[0][1]+8),row['id']+' / '+row['mark'],font=font,
                              fill='#007755',stroke_width=1,stroke_fill='white')
        text='Blue: revised enclosure'+(' / A2.08 comparison' if roof else ' | Red: revision 05 | Green: jambs')
        draw.text((8,8),text,font=font,fill='#1265c4',stroke_width=1,stroke_fill='white')
        im.save(out/'source-review'/f'{name}.png')
    return report
