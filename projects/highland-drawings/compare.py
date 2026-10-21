"""Expose remaining north model/elevation disagreement with a diagnostic overlay."""
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
OUT=ROOT/'deliverables/highland-drawings'


def main():
    spec=json.loads((HERE/'reconciled.spec.json').read_text())
    im=Image.open(OUT/'source-review/A3.02-north.png').convert('RGB')
    draw=ImageDraw.Draw(im);scale=200/72/.6
    xs=[1393,1224,1073,922];values=[195,528,861,1236]
    def project(u):
        k=next((k for k in range(3) if u<=values[k+1]),2)
        return xs[k]+(u-values[k])/(values[k+1]-values[k])*(xs[k+1]-xs[k])
    records=[]
    font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',22)
    for e in spec['openings']:
        if e['face']!='north' or e['level'] not in ('R2','R3','R4','R5'):continue
        lo,hi=sorted(project(u) for u in (e['u']-e['width']/2,e['u']+e['width']/2))
        top=212+(627-e['z']-e['height'])*57/126
        bottom=212+(627-e['z'])*57/126
        box=((lo-825)*scale,(top-20)*scale,(hi-825)*scale,(bottom-20)*scale)
        draw.rectangle(box,outline='#1265c4',width=3)
        if e['level']=='R5':draw.text((box[0],box[1]-25),e['id'][-2:],font=font,fill='#1265c4',stroke_fill='white',stroke_width=1)
        target=sum(e['source_pixels'])/2;pred=project(e['u'])
        records.append({'id':e['id'],'source_elevation_center_px':target,
                        'plan_model_projected_center_px':round(pred,3),'delta_px':round(pred-target,3)})
    im.save(OUT/'source-review/north-plan-model-overlay.png')
    report={'basis':'Diagnostic spec projection onto A3.02, not an independent rendered-edge measurement. Native frame extents were separately read back against the spec. Blue outlines use plan-governed jamb positions and assumed sill/head heights. No accuracy certificate or edge-agreement pass is claimed.',
        'elevation_grid_pixels':[922,1073,1224,1393],'elevation_grid_inches':[1236,861,528,195],
        'floor_ticks':{'R5':212,'R4':269},'max_abs_horizontal_center_delta_px':max(abs(r['delta_px']) for r in records),
        'findings':'Residual model-versus-elevation disagreement remains, especially around the north stair/MU pair. Plan jambs govern provisional placements; simplified walls, raster picks and drawing registration also affect comparison. The 15 accepted candidates establish presence and provisional plan locations, not fully reconciled dimensions. A4 window details, RFI responses and field verification are needed before confirmation.',
        'opening_comparisons':records}
    (OUT/'elevation-comparison.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Diagnostic maximum center delta:',report['max_abs_horizontal_center_delta_px'],'pixels on the inherited 0.6 raster.')


if __name__=='__main__':main()
