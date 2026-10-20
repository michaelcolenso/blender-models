"""A qualitative photo/drawing comparison and actual 3D-film storyboard."""
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4,landscape
from reportlab.lib.colors import HexColor
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph
from PIL import Image
from reportlab.lib.utils import ImageReader
import json,io

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];OUT=ROOT/'deliverables/highland-refined'
W,H=landscape(A4);pdf=OUT/'Highland-photo-and-drawing-comparison.pdf';c=canvas.Canvas(str(pdf),pagesize=(W,H));c.setTitle('200 West Highland - exterior revision review')
navy=HexColor('#162b3b');gray=HexColor('#52616b');style=ParagraphStyle('notes',fontName='Helvetica',fontSize=10,leading=14,textColor=gray)

def header(subtitle,page):
    c.setFillColor(navy);c.setFont('Helvetica',23);c.drawString(34,H-44,'200 WEST HIGHLAND')
    c.setFont('Helvetica',12);c.setFillColor(gray);c.drawString(34,H-66,subtitle)
    c.setStrokeColor(HexColor('#d8e1e6'));c.line(34,H-80,W-34,H-80)
    c.setFont('Helvetica',8);c.drawString(34,19,'Drawing-based visualization - source conflicts and presentation assumptions remain.');c.drawRightString(W-34,19,str(page))

def picture(path,x,y,w,h):
    with Image.open(path) as im:
        iw,ih=im.size
        # Compress only the PDF's embedded resource, leaving source images intact.
        small=im.convert('RGB');small.thumbnail((1800,1800),Image.Resampling.LANCZOS)
        buffer=io.BytesIO();small.save(buffer,format='JPEG',quality=92);buffer.seek(0)
        resource=ImageReader(buffer)
    factor=min(w/iw,h/ih);rw,rh=iw*factor,ih*factor
    c.setFillColor(HexColor('#f0f3f4'));c.rect(x,y,w,h,fill=1,stroke=0)
    c.drawImage(resource,x+(w-rw)/2,y+(h-rh)/2,width=rw,height=rh,preserveAspectRatio=True,mask='auto')

def text(s,x,y,w):
    p=Paragraph(s,style);_,h=p.wrap(w,H);p.drawOn(c,x,y-h);return h

def label(s,x,y):c.setFillColor(navy);c.setFont('Helvetica-Bold',10);c.drawString(x,y,s)

header('Provided photograph and revised daylight view',1)
panel=(W-84)/2
picture(ROOT/'projects/highland-exterior/source-review/user-photo-02.jpg',34,235,panel,252)
picture(OUT/'Highland-daylight-revised.png',50+panel,235,panel,252)
label('Provided appearance photograph',34,216);label('Revised daylight model / Cycles',50+panel,216)
text('<b>Geometry revision.</b> Ten south opening candidates have been restored within the registered plan bays. The revised model has 175 openings; 16 rear/return candidates remain unresolved. Exact jamb offsets remain assumed.',34,193,panel)
text('<b>Visible detail.</b> Continuous pale bands through brick fields were removed. Wide windows have broader center panes, guards have denser infill, and the terrace edge and selected balcony furnishings have been developed.',50+panel,193,panel)
text('<b>How to use this comparison.</b> The panels are independently fitted. Camera, weather, exposure and site context differ; this is a qualitative appearance and bay-pattern review. No measured camera fit, dimensional tolerance or photographic color calibration is claimed. The footprint, dimensional grid and floor/roof datums are retained from the original registered study.',34,103,W-68)
c.showPage()

header('South and east elevation patterns',2)
for i,(face,sheet) in enumerate([('south','A3.01 south elevation'),('east','A3.01 east elevation')]):
    y=H-290-i*222
    picture(ROOT/f'projects/highland-exterior/source-review/{face}.png',34,y,panel,174)
    picture(OUT/f'source-review/{face}.png',50+panel,y,panel,174)
    label(sheet,34,y-17);label('Revised orthographic model',50+panel,y-17)
text('Source and model panels are independently fitted, not calibrated measured overlays. Review opening order, plan returns, cornices and infill character. The drawing crops and inherited registration do not support a single dimensional alignment tolerance. Unresolved rear/return candidates remain in the revision ledger.',34,67,W-68)
c.showPage()

header('Plan controls and conservative provenance',3)
width=(W-92)/3
for i,(path,title) in enumerate([(ROOT/'projects/highland-exterior/source-review/r1-outline.png','A2.03 R1 plan crop'),(OUT/'source-review/plan.png','Revised model / plan'),(OUT/'source-review/provenance.png','Assumed components / orange')]):
    x=34+i*(width+12);picture(path,x,160,width,325);label(title,x,144)
text('<b>Retained controls.</b> Registered plan polygons and grid spans; floor elevations 342.00, 353.00, 363.25, 373.50, 383.75 and 394.25 ft; documented roof/parapet top datums. Exact opening offsets, sections, terrace levels and presentation props remain assumed.',34,115,W-68)
text('<b>Orange provenance.</b> Complete components retain assumed geometry even when individual floor or roof datums are documented. The color view does not imply a wholly confirmed component or certify installed conditions. The original architectural PDF is absent here; existing source crops and the registered specification are reused.',34,70,W-68)
c.showPage()

header('Continuous 18-second approach and rising orbit',4)
frames=[0,72,144,216,288,360,431];width=(W-110)/4;height=width*9/16
for i,f in enumerate(frames):
    x=34+(i%4)*(width+14);y=H-115-(i//4)*(height+30)-height
    picture(OUT/f'film-review/frame-{f:03}.png',x,y,width,height);label(f'{f/24:.2f} s / frame {f+1}',x,y-15)
text('All 432 camera frames retain the full architectural bounding box. The movie uses the exported 3D geometry with real-time PBR building materials, simpler diffuse context/foliage shading and a documented foliage LOD. The native scene preserves the complete geometry and camera keyframes. The Cycles daylight still is the detailed material reference.',34,190,W-68)
c.save();print(pdf)
