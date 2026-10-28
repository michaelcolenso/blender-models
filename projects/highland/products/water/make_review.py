"""Drawing overlay and review PDF, built from the same spec as the 3D model."""
from pathlib import Path
import json,base64,hashlib,fitz,shutil
from PIL import Image,ImageStat

HERE=Path(__file__).parent
BUILD=HERE.parents[3]/'build/highland-water'
spec=json.loads((HERE/'highland-water.spec.json').read_text())
validation=json.loads((BUILD/'validation.json').read_text())
cal=spec['calibration'];xy_scale=cal['unit_xy_in_per_normalized_pixel']
source=HERE/'source-review/unit-a.png'
colors={'CW':'#006fd6','HW':'#e33a16','HWC':'#008050','MW':'#8855cf'}
svg=['<svg xmlns="http://www.w3.org/2000/svg" width="1824" height="1372" viewBox="0 0 1824 1372">',
 f'<image width="1824" height="1372" href="data:image/png;base64,{base64.b64encode(source.read_bytes()).decode()}" opacity="0.72"/>']
for e in spec['elements']:
    if e['scene']!='unit' or e['kind']!='pipe':continue
    pts=[(x/xy_scale+900,700-y/xy_scale) for x,y,z in e['points']]
    points=' '.join(f'{x:.2f},{y:.2f}' for x,y in pts)
    dashed='stroke-dasharray="9 6"' if e['id'].startswith('island-underfloor') or e['system']=='HWC' else ''
    svg.append(f'<polyline points="{points}" fill="none" stroke="{colors[e["system"]]}" stroke-width="3" {dashed}><title>{e["id"]}: {e["nominal_in"]} in nominal; XY {e.get("xy_status", "provisional")}; heights assumed</title></polyline>')
svg.append('</svg>')
(BUILD/'unit-107-trace.svg').write_text(''.join(svg))
html='''<!doctype html><html><meta charset="utf-8"><title>Unit 107 | trace review</title><style>body{font:15px/1.6 Arial;background:#ecf1f4;color:#142934;margin:0}header{padding:20px 30px;background:#112936;color:white;position:sticky;top:0}h1{font-size:23px;margin:0}p{margin:6px 0}button{padding:8px 15px;cursor:pointer}svg{width:100%;height:auto}small{color:#becfd8}</style><header><h1>Unit A / 107 — drawing-to-model trace</h1><p>Blue: cold · Orange: hot · Green: circulation return · Purple: mixed outlet · Dashed kitchen route: assumed below floor</p><button onclick="document.querySelectorAll('polyline').forEach(p=>p.style.display=p.style.display==='none'?'':'none')">Toggle modeled routes</button><p><small>Review overlay only. Fixture anchors derive from the shared structural grid (scale allowance ±1%). Bathroom wall-side service offsets are assumed and are not covered by the schematic ±6 in trace allowance. Vertical drops collapse to points. Pipe separation is expanded in places for readability.</small></p></header>'''+''.join(svg)+'</html>'
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
    p.insert_text((35,738),'MODEL STUDY | Unit XY provisionally calibrated; pipe heights and envelopes assumed. Not an as-built.',fontsize=9,color=(.65,.76,.81))
    return p
p=page('Unit 107: scale tied to the construction plans','Unit XY is now provisionally calibrated through A2.03 structural grid dimensions and the P2.02 plumbing plan. Colors: blue cold, orange hot, green return, purple mixed water. Pipe heights and fixture envelopes remain assumed.')
p.insert_image(fitz.Rect(35,140,965,710),filename=str(BUILD/'unit-iso.png'),keep_proportion=True)
p=page('Primary bathroom: supply connections','Nine explicit fixture ports connect the two lavatories, tub, shower and toilet. Rounded elbows, branch tees, five shutoffs and two mixing bodies are representative hardware. Heights and local wall-side offsets remain assumed.')
p.insert_image(fitz.Rect(35,140,965,710),filename=str(BUILD/'unit-bath.png'),keep_proportion=True)
p=page('Fixture connections: behind the basins','Vertical supplies run behind the fixture envelopes. Short flexible connectors join five shutoffs to the two faucets and toilet tank. Both mixing bodies have connected mixed-water outlets. No sanitary or vent piping is represented.')
p.insert_image(fitz.Rect(35,140,965,710),filename=str(BUILD/'bath-connections.png'),keep_proportion=True)
p=page('Check the route before extending the model','Overlay generated from the calibrated specification and projected back to P4.01. Scale allowance: +/-1%; schematic trace allowance: +/-6 in. Bathroom wall-side service offsets are additional assumptions. Kitchen underfloor path and exact loop joins remain assumptions. Not a field survey.')
svgdoc=fitz.open(stream=(BUILD/'unit-107-trace.svg').read_bytes(),filetype='svg')
pdf=fitz.open('pdf',svgdoc.convert_to_pdf());p.show_pdf_page(fitz.Rect(35,140,965,710),pdf,0)
p=page('The shared network: documented floor datums','Floor levels now follow A3.11: P2 332.00, P1 342.00, R1 353.00, R2 363.25, R3 373.50, R4 383.75, R5 394.25 ft. The upper guide is PLATE 404.42, not a flat roof. Stack XY and pipe offsets remain assumed.')
p.insert_image(fitz.Rect(35,140,965,710),filename=str(BUILD/'building-iso.png'),keep_proportion=True)
p=page('Plant connections','P3.02 / detail 1: two boilers, two storage tanks, four expansion vessels and three installed pumps. WAC2 is a loose spare. Equipment envelopes are representative; relief piping, flues, detailed controls and balancing bypasses are incomplete.')
p.insert_image(fitz.Rect(35,140,965,710),filename=str(BUILD/'plant-iso.png'),keep_proportion=True)
p=page('Calibration evidence','A2.03 dimensions the shared structural grid. Those dimensions calibrate P2.02; matched architectural features then transfer scale to the enlarged P4.01 Unit A drawing. The excerpt does not include the P1 architectural plan.')
p.insert_image(fitz.Rect(35,155,690,360),filename=str(HERE/'source-review/architectural-grid-dimensions.png'),keep_proportion=True)
p.insert_image(fitz.Rect(730,145,960,695),filename=str(HERE/'source-review/architectural-levels.png'),keep_proportion=True)
evidence='HORIZONTAL GRID\n6-7: 16 ft 3 in | 7-8: 27 ft 9 in\n8-9: 27 ft 9 in | 9-10: 31 ft 3 in\nOverall: 1,236 in across 927 PDF points on P2.02\nScale: 0.75 PDF points / inch\n\nINDEPENDENT VERTICAL CHECK\nE-F: 18 ft | F-G: 24 ft 6 in | G-H: 15 ft\nAll individual spans agree with the working scale within 0.6%.\n\nCROP REGISTRATION\n21 matching features; median residual 0.224 PDF points.\nUnit conversion: 0.51398 in per normalized pixel.\nPlan dimensions increase 28.5% from the earlier placeholder.\n\nDATUM CAUTION\nUse the labeled elevations; some interval notes also say\n(+1/4 in). That small discrepancy is retained for review.\n11 ft at Unit 107 is floor-to-floor, not clear ceiling height.'
p.insert_textbox(fitz.Rect(40,370,705,705),evidence,fontsize=11,lineheight=1.25,color=(.84,.90,.94))
p=page('What is checked, and what is still needed','The new construction plans establish building levels and support a provisional horizontal calibration. Concealed pipe placement and equipment geometry still require further evidence.')
text=f'CHECKED\n\n- Unique IDs and provenance on {len(spec["elements"])} elements; distribution graphs remain connected.\n- Five stack groups, 23 explicit branch groups, 14 Unit A fixtures.\n- Bathroom: 9 fixture ports, 5 stops, 2 mixing bodies and 2 mixed outlets checked.\n- Seven floor datums match A3.11; Unit 107 floor-to-floor height is 132 in.\n- Horizontal and vertical structural-grid spans agree within the raster allowance.\n- Cross-sheet registration and model-projected drawing overlay reviewed.\n\nSTILL NEEDED\n\n- Unit 107 / P1 architectural and reflected-ceiling plans (not in this excerpt).\n- Clear ceiling heights, concealed pipe elevations, offsets and actual shaft positions.\n- Equipment dimensions; resolution of the 04 stack R1 and dishwasher connections.\n- Clarification of quarter-inch interval notes versus the labeled floor elevations.\n- Field records or measurements if installed conditions are the objective.\n\nCURRENT SCOPE\n\nDomestic water supply and return only; sanitary, vent and gas are not modeled.\nWorking allowances are not survey accuracy: +/-1% scale; +/-6 in local route trace.\nNo construction lengths or quantities should be taken from this model.'
p.insert_textbox(fitz.Rect(45,155,945,700),text,fontsize=13,lineheight=1.4,color=(.84,.90,.94))
doc.save(BUILD/'Highland-pipe-model-review.pdf',garbage=4,deflate=True)
bathdoc=fitz.open();bathdoc.insert_pdf(doc,from_page=1,to_page=2);bathdoc.save(BUILD/'Unit-107-bathroom-pilot.pdf',garbage=4,deflate=True)
print('Complete review and two-page bathroom pilot PDF created.')
