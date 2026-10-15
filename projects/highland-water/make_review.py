"""Drawing overlay and review PDF, built from the same spec as the 3D model."""
from pathlib import Path
import json,base64,hashlib,fitz,shutil
from PIL import Image,ImageStat

HERE=Path(__file__).parent
BUILD=HERE.parent.parent/'build/highland-water'
spec=json.loads((HERE/'highland-water.spec.json').read_text())
source=HERE/'source-review/unit-a.png'
colors={'CW':'#006fd6','HW':'#e33a16','HWC':'#008050'}
svg=['<svg xmlns="http://www.w3.org/2000/svg" width="1824" height="1372" viewBox="0 0 1824 1372">',
 f'<image width="1824" height="1372" href="data:image/png;base64,{base64.b64encode(source.read_bytes()).decode()}" opacity="0.72"/>']
for e in spec['elements']:
    if e['scene']!='unit' or e['kind']!='pipe':continue
    pts=[(x/.4+900,700-y/.4) for x,y,z in e['points']]
    points=' '.join(f'{x:.2f},{y:.2f}' for x,y in pts)
    dashed='stroke-dasharray="9 6"' if e['id'].startswith('island-underfloor') or e['system']=='HWC' else ''
    svg.append(f'<polyline points="{points}" fill="none" stroke="{colors[e["system"]]}" stroke-width="3" {dashed}><title>{e["id"]}: {e["nominal_in"]} in nominal; coordinates assumed</title></polyline>')
svg.append('</svg>')
(BUILD/'unit-107-trace.svg').write_text(''.join(svg))
html='''<!doctype html><html><meta charset="utf-8"><title>Unit 107 | trace review</title><style>body{font:15px/1.6 Arial;background:#ecf1f4;color:#142934;margin:0}header{padding:20px 30px;background:#112936;color:white;position:sticky;top:0}h1{font-size:23px;margin:0}p{margin:6px 0}button{padding:8px 15px;cursor:pointer}svg{width:100%;height:auto}small{color:#becfd8}</style><header><h1>Unit A / 107 — drawing-to-model trace</h1><p>Blue: cold · Orange: hot · Green: circulation return · Dashed kitchen route: assumed below floor</p><button onclick="document.querySelectorAll('polyline').forEach(p=>p.style.display=p.style.display==='none'?'':'none')">Toggle modeled routes</button><p><small>Review overlay only. XY is a visual trace, not a calibrated measurement. Vertical drops collapse to points. Pipe separation is expanded in places for readability.</small></p></header>'''+''.join(svg)+'</html>'
(BUILD/'Unit-107-trace-review.html').write_text(html)

# Fail on blank review images; make a contact sheet for human inspection.
review_names=['review-plan','review-front','review-side','review-iso','review-building']
contact=Image.new('RGB',(1200,450*3),'#152c39')
for i,name in enumerate(review_names):
    im=Image.open(BUILD/(name+'.png')).convert('RGB')
    assert max(ImageStat.Stat(im).stddev)>5,(name,'blank render')
    im.thumbnail((600,450));contact.paste(im,((i%2)*600,(i//2)*450))
contact.save(BUILD/'provenance-review-contact.jpg',quality=90)

doc=fitz.open()
def page(title,subtitle):
    p=doc.new_page(width=1000,height=760);p.draw_rect(p.rect,color=None,fill=(.045,.095,.13))
    p.insert_text((35,39),'HIGHLAND / DOMESTIC WATER',fontsize=10,color=(.61,.79,.84))
    p.insert_text((35,77),title,fontsize=26,color=(.94,.97,.98))
    p.insert_textbox(fitz.Rect(35,90,960,137),subtitle,fontsize=11,color=(.72,.82,.87))
    p.insert_text((35,738),'DRAWING-BASED MODEL STUDY  |  Positions and envelopes assumed. Not an as-built or construction document.',fontsize=9,color=(.65,.76,.81))
    return p
p=page('Start with one dwelling: Unit A / 107','Modeled supply pipes and fixture connections from P4.01. Colors: blue cold, orange hot, green circulation return. Geometry is editable; routes and heights still need dimensional verification.')
p.insert_image(fitz.Rect(35,140,965,710),filename=str(BUILD/'unit-iso.png'),keep_proportion=True)
p=page('Check the route before extending the model','Overlay generated from the 3D specification, projected back onto the source crop. Kitchen underfloor path and exact loop joins remain assumptions. This is a visual review, not a measured overlay or a passed dimensional check.')
svgdoc=fitz.open(stream=(BUILD/'unit-107-trace.svg').read_bytes(),filetype='svg')
pdf=fitz.open('pdf',svgdoc.convert_to_pdf());p.show_pdf_page(fitz.Rect(35,140,965,710),pdf,0)
p=page('The shared network','P3.02 supports five labeled stack groups. The 03 group stops below R5; the 04 group has no resolved R1 dwelling branch. Layout and floor elevations in this view are presentation assumptions.')
p.insert_image(fitz.Rect(35,140,965,710),filename=str(BUILD/'building-iso.png'),keep_proportion=True)
p=page('Plant connections','P3.02 / detail 1: two boilers, two storage tanks, four expansion vessels and three installed pumps. WAC2 is a loose spare. Equipment envelopes are representative; relief piping, flues, detailed controls and balancing bypasses are incomplete.')
p.insert_image(fitz.Rect(35,140,965,710),filename=str(BUILD/'plant-iso.png'),keep_proportion=True)
p=page('What is checked, and what is still needed','This first model establishes actual pipe geometry and a reviewable drawing basis. It is not yet a dimensionally coordinated owner presentation.')
text='CHECKED\n\n- Unique element IDs and provenance on all 319 elements.\n- Document-based counts: 5 stack groups, 23 explicit branch groups, 14 Unit A fixtures.\n- Every modeled distribution branch reaches its own system inlet.\n- Separate cold / hot / return geometry; editable Blender and GLB exports.\n\nNEEDED BEFORE ACCURATE PLACEMENT\n\n- A dimensioned architectural plan or a verified reference dimension for Unit 107.\n- Floor-to-floor elevations, ceiling heights and pipe elevations.\n- Riser / shaft locations, pipe offsets and equipment dimensions.\n- Resolution of the 04 stack R1 connection and Unit A dishwasher connection.\n- Field verification if the objective is existing installed plumbing.\n\nCURRENT SCOPE\n\nDomestic water supply and return only. Sanitary, vent and gas systems are not modeled.\nNo construction lengths or quantities can be extracted reliably from assumed coordinates.\nThe complete assumptions and omissions are recorded in the specification and README.'
p.insert_textbox(fitz.Rect(45,155,945,700),text,fontsize=13,lineheight=1.4,color=(.84,.90,.94))
doc.save(BUILD/'Highland-pipe-model-review.pdf',garbage=4,deflate=True)
print('Review PDF, trace overlay and provenance contact sheet created.')
