"""Validate exterior renders and package the owner/review deliverables."""
from pathlib import Path
import hashlib,json,shutil,struct,io
import fitz
import numpy as np
from PIL import Image

H=Path(__file__).parent
B=H.parents[3]/'build/highland-exterior'
D=H.parents[3]/'projects/highland/deliverables/exterior'
D.mkdir(parents=True,exist_ok=True)
names=['southeast','east-entry','south-review','east-review','west-review','north-review','plan-review',
       'provenance-south-review','provenance-east-review','provenance-plan-review','provenance-southeast']
report=json.loads((B/'validation.json').read_text())
report['render_checks']={}
for name in names:
    a=np.asarray(Image.open(B/(name+'.png')).convert('RGB'))
    # Exclude the caption from the nonblank image check.
    a=a[:int(len(a)*.86)]
    sd=float(a.std());assert sd>10, f'Blank or almost uniform image: {name}'
    report['render_checks'][name]={'rgb_stddev':round(sd,2),'nonblank':True}
data=(B/'Highland-exterior.glb').read_bytes()
magic,version,total=struct.unpack_from('<4sII',data)
assert magic==b'glTF' and version==2 and total==len(data)
size,typ=struct.unpack_from('<II',data,12);assert typ==0x4e4f534a
g=json.loads(data[20:20+size]);mesh_nodes=[n for n in g['nodes'] if 'mesh' in n]
assert len(mesh_nodes)==report['objects']
assert all(n.get('extras',{}).get('status')=='assumed' and n['extras'].get('source') for n in mesh_nodes)
report['glb_checks']={'version':version,'mesh_nodes':len(mesh_nodes),'provenance_present':True}
(D/'elements.json').write_text(json.dumps([dict(name=n.get('name'),**n['extras']) for n in mesh_nodes],indent=2)+'\n')

doc=fitz.open()
def page(title,subtitle):
    p=doc.new_page(width=1000,height=750)
    p.draw_rect(p.rect,color=None,fill=(.96,.97,.96))
    p.insert_text((30,36),title,fontsize=22,color=(.08,.17,.19))
    p.insert_textbox(fitz.Rect(30,48,970,90),subtitle,fontsize=10,color=(.25,.31,.32))
    p.insert_text((30,730),'200 W. Highland | Exterior drawing study | Provisional / assumed geometry | Not construction documents',fontsize=9)
    return p
def pic(p,path,rect):
    im=Image.open(path).convert('RGB');im.thumbnail((2400,1800))
    buf=io.BytesIO();im.save(buf,format='JPEG',quality=88,optimize=True)
    p.insert_image(fitz.Rect(*rect),stream=buf.getvalue(),keep_proportion=True)
p=page('200 W. Highland - exterior study','First exterior model from the 2007 architectural set, with finish families and balcony character informed by the two owner photos.')
pic(p,B/'southeast.png',(30,90,970,710))
p=page('East entry and uphill frontage','The sloping grade, street widths, entry steps and landscape are presentation assumptions, not surveyed site geometry.')
pic(p,B/'east-entry.png',(30,90,970,710))
for face,sheet in [('south','A3.01 / 01'),('east','A3.01 / 02'),('west','A3.02 / 02'),('north','A3.02 / 01')]:
    p=page(face.title()+' elevation comparison',sheet+' above; model below. Independently fitted panels for qualitative review, not a same-scale overlay. Window schedule and facade details remain unresolved.')
    pic(p,H/'source-review'/f'{face}.png',(30,90,970,370))
    pic(p,B/f'{face}-review.png',(30,385,970,710))
p=page('Roof and stepped footprint','A2.08 source at left; model plan at right. Plan grids control scale; roof slopes, drains, equipment and local parapet details are simplified.')
pic(p,H/'source-review/roof.png',(30,100,485,710));pic(p,B/'plan-review.png',(505,100,970,710))
p=page('Geometry provenance','Orange = assumed complete component. Individual objects retain sources and separate provisional XY / confirmed datum properties where available.')
for name,rect in zip(names[-4:],[(30,95,490,390),(510,95,970,390),(30,400,490,695),(510,400,970,695)]):pic(p,B/(name+'.png'),rect)
p=page('What is checked - and what remains approximate','Source inventory, assumptions and reproduction instructions are included alongside the model.')
body='''SOURCE BASIS
Architectural PDF dated 04-02-07: A2.03, A2.04, A2.07, A2.08, A3.01, A3.02 and A3.11. Two owner photos supply appearance only; neither establishes dimensional scale.

DOCUMENTED CONTROL
Grid spans: 103 ft east-west and 150 ft north-south (not building extents). Floors: 342, 353, 363.25, 373.5, 383.75 and 394.25 ft. Elevator/stair parapets: 415 / 414.41 ft.

AUTOMATED CHECKS
Grid/floor/elevator values, unique object IDs, opening inventory, provenance, nonblank rendered images and portable GLB metadata are checked. These checks are consistency checks, not proof of an exact architectural reconstruction.

OPEN ISSUES
165 representative openings; 26 candidates omitted at conflicting plan returns; 18 padded balcony recess boundaries clipped. Elevation grids disagree with plan spacing, so no global accuracy tolerance or overlay score is claimed. Sills, heads, balcony depth, frames and rails are standardized assumptions. R2-R4 repeat a typical outline; P1 uses the R1 enclosure outline.

PRESENTATION ASSUMPTIONS
Materials, roof details, roof equipment, entry steps, grade, streets and vegetation remain approximate. Neighboring buildings, detailed patio/retaining walls and facade accessories are omitted. GLB uses a flat brick base color; Blender retains the procedural brick texture.

INTENDED USE
Owner discussion and visual context. Separate from the plumbing/repipe proposal. Not an as-built survey, quantity takeoff, access plan or construction document.'''
assert p.insert_textbox(fitz.Rect(40,105,950,710),body,fontsize=13,lineheight=1.25)>=0
doc.save(D/'Highland-exterior-review.pdf',garbage=4,deflate=True)
for src,dst in [('southeast.png','Highland-exterior-southeast.png'),('east-entry.png','Highland-exterior-east-entry.png'),('Highland-exterior.blend','Highland-exterior.blend'),('Highland-exterior.glb','Highland-exterior.glb')]:shutil.copyfile(B/src,D/dst)
report['artifact_sha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in D.iterdir() if p.suffix in ['.png','.blend','.glb','.pdf']}
(D/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(f'Packaged {len(names)} checked renders and {len(mesh_nodes)} GLB mesh nodes.')
