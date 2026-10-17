"""Readable PDF storyboard, captioned method video and model handoff package."""
import json,csv,subprocess,zipfile,textwrap
from pathlib import Path
from xml.sax.saxutils import escape
from PIL import Image,ImageDraw,ImageFont
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor,white
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle
ROOT=Path(__file__).resolve().parent
S=json.loads((ROOT/'installation-data.json').read_text())
WIDTH,HEIGHT=1152,720
TEAL='#123d43';GRAY='#4d6266';PAPER='#f5f5ee'
P=ParagraphStyle('body',fontName='Helvetica',fontSize=12,leading=17,textColor=HexColor(TEAL))
SMALL=ParagraphStyle('small',parent=P,fontSize=9,leading=12)
def paragraph(c,text,x,y,w,style=P):
 p=Paragraph(escape(text).replace('\n','<br/>'),style);_,h=p.wrap(w,600);p.drawOn(c,x,y-h);return h
def page(c,n,kicker,title,sub):
 c.setFillColor(HexColor(PAPER));c.rect(0,0,WIDTH,HEIGHT,fill=1,stroke=0)
 c.setFillColor(HexColor(TEAL));c.setFont('Helvetica-Bold',10);c.drawString(38,683,kicker.upper())
 c.setFont('Helvetica-Bold',29);c.drawString(38,642,title)
 paragraph(c,sub,38,620,1075,SMALL)
 c.setStrokeColor(HexColor('#d1dcda'));c.line(38,49,1115,49)
 c.setFont('Helvetica',9);c.setFillColor(HexColor(GRAY));c.drawString(38,29,'200 W Highland | INSTALLATION COORDINATION | Assumed geometry - do not measure or use for fabrication')
 c.drawRightString(1115,29,f'{n:02}')
def image_fit(c,path,x,y,w,h):
 im=Image.open(path);ratio=min(w/im.width,h/im.height);nw,nh=im.width*ratio,im.height*ratio
 c.drawImage(ImageReader(im),x+(w-nw)/2,y+(h-nh)/2,width=nw,height=nh)
def legend(c,x,y):
 for label,color in [('Cold water','#0861c1'),('Hot water','#d92412'),('Circulation return','#7821b8'),('Access / test','#ed6e0a')]:
  c.setFillColor(HexColor(color));c.rect(x,y,15,5,fill=1,stroke=0);c.setFillColor(HexColor(TEAL));c.setFont('Helvetica',10);c.drawString(x+21,y-1,label);x+=155
def overlay():
 im=Image.open(ROOT/'unit-b-plan.png').convert('RGB');d=ImageDraw.Draw(im);w,h=im.size
 colors={'CW':'#006ace','HW':'#e02c1b','HWC':'#8032bb'}
 for e in S['elements']:
  if e['type']=='pipe':
   pts=[(round(p[0]*w),round(p[1]*h)) for p in e['points']]
   d.line(pts,fill=colors[e['system']],width=9,joint='curve')
 font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',35)
 for e in S['elements']:
  if e['type']=='access':
   x0,y0,x1,y1=e['rect'];r=[int(x0*w),int(y0*h),int(x1*w),int(y1*h)];d.rectangle(r,outline='#f07808',width=7)
   d.rectangle((r[0],r[1]-43,r[0]+92,r[1]),fill='#fff3d8');d.text((r[0]+5,r[1]-40),e['id'],font=font,fill='#864000')
  elif e['type']=='terminal':
   x,y=int(e['at'][0]*w),int(e['at'][1]*h);d.ellipse((x-15,y-15,x+15,y+15),fill='#123d43')
   d.rectangle((x+15,y-24,x+110,y+19),fill='white');d.text((x+20,y-23),e['id'],font=font,fill='#123d43')
 im.save(ROOT/'renders'/'plan-route-overlay.png')

def pdf():
 c=canvas.Canvas(str(ROOT/'Highland-installation-storyboard.pdf'),pagesize=(WIDTH,HEIGHT))
 c.setTitle('200 W Highland - Repipe Installation Model');c.setAuthor('Project coordination')
 page(c,1,'Installation model / 2026-10-17','Install alongside. Test. Transfer. Restore.',
      'Shared distribution + Unit B / 106 pilot | Source issue 29 October 2007 | Proposed method, subject to field verification')
 image_fit(c,ROOT/'renders/shared-distribution.png',30,100,765,490)
 paragraph(c,'Shared-system coordination',820,575,285,ParagraphStyle('heading',parent=P,fontName='Helvetica-Bold',fontSize=17,leading=22))
 paragraph(c,'The five numbered review labels and auxiliary-service notes come from P3.02. The three colored networks show a proposed replacement concept.',820,535,280)
 paragraph(c,'Schematic positions and candidate valve symbols do not establish actual chases, served units or usable shutdown boundaries.',820,435,280)
 paragraph(c,'Unit 106 / 107 is a separate tie-in on the source diagram. No connection to a numbered stack is asserted.',820,335,280)
 legend(c,40,79);c.showPage()
 page(c,2,'Pilot / P4.01 - PDF 15','Unit B / 106: routes and access',
      'Plan-overlay trace follows drawing relationships. New elevations, sizes and opening extents are assumed; fixture-group symbols do not establish fixture counts.')
 image_fit(c,ROOT/'renders/plan-route-overlay.png',30,75,700,525)
 y=580
 for e in [e for e in S['elements'] if e['type']=='access']:
  y-=paragraph(c,e['id']+'  '+e['label'],755,y,350,P)+12
 paragraph(c,'Keep the kitchen low-wall route visible in field review. Trace the circulation-return termination and balancing arrangement before adopting the proposed loop.',755,y-10,350)
 legend(c,40,62);c.showPage()
 for p in S['phases']:
  page(c,p['id']+3,f"Stage {p['id']+1} / 6",p['title'],p['caption'])
  image_fit(c,ROOT/'renders'/f"phase-{p['id']+1:02}.png",25,86,755,515)
  y=585
  for item in p['work']:
   y-=paragraph(c,'- '+item,800,y,315,P)+12
  gate=ParagraphStyle('gate',parent=P,fontName='Helvetica-Bold',fontSize=11,leading=15)
  paragraph(c,'Release condition: '+p['gate'],800,min(y-15,235),315,gate)
  legend(c,40,67);c.showPage()
 page(c,9,'Exceptions / sources','Carry these exceptions into every work package',
      'The notes below are supplied drawing annotations; each needs current field confirmation before isolation or repetitive installation.')
 image_fit(c,ROOT/'risers-200dpi.png',35,240,700,350)
 image_fit(c,ROOT/'unit-b-service.png',40,65,235,170)
 paragraph(c,'P4.01 service callouts: unit shutoffs, water meter, circulation return, and alarm-linked solenoid. Device condition and proposed assembly order remain unverified.',290,218,445,P)
 y=580
 for note in S['shared_distribution']['source_notes']:
  y-=paragraph(c,note['id']+'  '+note['text']+' ('+note['source']+')',765,y,350,P)+16
 c.showPage()
 page(c,10,'Review / provenance','All new physical geometry remains assumed',
      'Orange = assumed. Green = source-confirmed content. Yellow = provisional. Unchanged source pixels are retained beneath the proposed model.')
 for view,x,y in [('plan',35,335),('iso',395,335),('front',35,86),('side',395,86)]:
  image_fit(c,ROOT/'renders'/f'review-{view}.png',x,y,345,230)
  c.setFillColor(HexColor(TEAL));c.setFont('Helvetica-Bold',10);c.drawString(x+5,y+225,view.upper())
 paragraph(c,'Before issuing an installation design',780,582,320,ParagraphStyle('head2',parent=P,fontName='Helvetica-Bold',fontSize=16,leading=21))
 y=540
 for t in [
  'Confirm address: project title says 200; source location block says 202 W Highland Drive, Seattle.',
  'Approve replacement material and calculate supply / return sizes from measured demand, pressure and route lengths.',
  'Verify actual chases, heights, penetration assemblies, valve performance and all affected services.',
  'Document inspection/test requirements, commissioning criteria and resident outage arrangements.',
  'Resolve Unit 302 and Unit 101 exceptions before repeating the pilot route.',
 ]:y-=paragraph(c,'- '+t,780,y,320,P)+13
 paragraph(c,'Automated checks: source identity, proposed graph continuity, cold-only branches, model metadata and nonblank renders. Visual review recorded separately. No field or hydraulic validation is claimed.',780,151,320,SMALL)
 c.save()

def video():
 target=ROOT/'video-frames';target.mkdir(exist_ok=True)
 fb='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf';bold='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
 for p in S['phases']:
  im=Image.new('RGB',(1600,1100),PAPER);d=ImageDraw.Draw(im)
  d.text((45,24),'200 W HIGHLAND  /  INSTALLATION MODEL',font=ImageFont.truetype(bold,22),fill=TEAL)
  d.text((45,66),f"{p['id']+1:02}  {p['title']}",font=ImageFont.truetype(bold,43),fill=TEAL)
  src=Image.open(ROOT/'renders'/f"phase-{p['id']+1:02}.png").convert('RGB');src.thumbnail((1520,825));im.paste(src,((1600-src.width)//2,140))
  d.text((45,978),p['caption'],font=ImageFont.truetype(fb,23),fill=TEAL)
  d.text((45,1037),'ASSUMED GEOMETRY | Method sequence only | P4.01 Unit B / 106 | No measured takeoff',font=ImageFont.truetype(bold,19),fill=GRAY)
  im.save(target/f"stage-{p['id']:02}.png")
 subprocess.run(['ffmpeg','-y','-framerate','1/4','-i',str(target/'stage-%02d.png'),'-vf','fps=24,format=yuv420p','-c:v','libx264','-crf','21','-movflags','+faststart',str(ROOT/'Highland-installation-sequence.mp4')],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)

def handoff():
 with (ROOT/'installation-elements.csv').open('w',newline='') as f:
  writer=csv.writer(f,lineterminator='\n');writer.writerow(['ID','type','system','phase','description','geometry_status','source','basis','quantity_use'])
  for e in S['elements']:writer.writerow([e['id'],e['type'],e.get('system',''),e['phase']+1,e.get('description',e.get('label','')),e['status'],e['source'],e['basis'],'NOT FOR TAKEOFF'])
 report='''# 200 W Highland — installation model

Built 17 October 2026 from the supplied 19-sheet drawing set dated 29 October 2007. The previous owner drawing atlas and original plans are unchanged.

## Open first

- **Highland-installation-storyboard.pdf** — ten-page review: shared-system schematic, Unit B / 106 plan overlay, six installation stages, source exceptions and provenance views.
- **Highland-installation-sequence.mp4** — 24-second captioned method sequence, four seconds per stage. This is a storyboard video; it does not simulate labor duration.
- **Highland-installation-unit-B.blend** — editable proposed pilot; six visibility stages at frames 1, 25, 49, 73, 97 and 121. Open the timeline at these frames. All drawing textures are packed. The file opens at completed installation, frame 121.
- **Highland-installation-shared.blend** — separate proposed distribution schematic with the five numbered review groups and auxiliary-service stubs.
- Matching **.glb** files — portable static proposed models with provenance metadata. Visibility sequence remains in Blender and video; GLBs show the final stage.
- **installation-elements.csv** — element register with stable IDs, sources, installation stages and assumptions; no purchase quantities or measured pipe lengths.

## Modeled installation

1. Verify service boundaries and protect finishes.
2. Make controlled access openings; prepare support and penetration strategy.
3. Install new cold, hot and circulation-return distribution as an isolated network.
4. Complete branches, cap boundaries, test and inspect the new network.
5. Cut over within verified isolation boundaries; inspect final connections, flush and commission.
6. Restore rated assemblies and finishes after acceptance; retain service access and hand over as-builts.

Source-linked details include the Unit B kitchen low-wall supply and service/meter/control coordination, the three-system distribution, irrigation through Unit 101, Unit 302's alternate wall location, the distinct 106/107 tie-in, and the garage/trash plus fitness/janitor services.

## Provenance and geometry limits

**Every new physical element is assumed.** P4.01 supplies route relationships and fixture-group context, not field dimensions. The source plan's printed scale has not been calibrated against dimension strings, so the 480 x 442.1 inch display mapping is arbitrary. Do not measure the model, compute quantities from it, or adopt drawn diameters as pipe sizes. Pipes and symbols are enlarged for readability.

The assumed elements are listed individually in installation-elements.csv and highland-installation-proposed.yaml: all supply/return paths, fixture-group endpoints, access rectangles A01–A05, protection footprint P01, service assembly SVC01, test symbol TEST01, support symbols, and restoration boundaries. The shared-model positions, riser heights, valve symbols, return loops and auxiliary stubs are also assumed. Review colors: orange assumed, yellow provisional, green confirmed; drawing pixels are confirmed source content but their physical mapping is assumed.

No individual fixture count, existing CPVC alignment, usable isolation boundary, affected-unit list, actual pipe support spacing, firestop product/detail, final material, hydraulic sizing, labor duration or outage duration is established. Fixture-group endpoints are diagram symbols; individual appliance/fixture connections remain to be detailed. The proposed return termination and balancing arrangement require field tracing and design confirmation. Test caps/gauge and service symbols explain the process, not a specified test rig or assembly order. The protection footprint is illustrative and does not verify actual entry/egress.

The existing drawing reference has a separate spec, highland-installation-existing-reference.yaml. It records unchanged source pixels and the user's report of failing CPVC; it does not assert an existing-condition pipe model. The proposed installation is a separate spec and separate Blender files. Original boiler equipment is not replaced by this model; system tie-ins remain to be verified.

The drawing project title reads **200 West Highland Drive**; its location block reads **202 W Highland Drive, Seattle, WA 98119**. Confirm property address and governing revision. Drawing issue and annotation dates are not interchangeable; supplied review annotations may be later.

## Design release information still needed

Confirm measured routes/elevations, current configuration, water pressure under demand, fixture demand, material suitability, hot-water and return conditions, rated assemblies, actual valve operation, inspection and testing criteria, outage arrangements and exception routes. A qualified plumbing designer/contractor must convert this method model into the installation design under the applicable Seattle requirements.

## Rebuild

The model uses a dedicated spec-driven pipe builder because the existing generic house/detail builder does not support this scanned, multistory plumbing set. The supplied plan was rasterized at 200 dpi for source review; no automatic dimensional extraction is claimed.

```bash
python prepare_spec.py
/workspace/.venvs/blender-models/bin/python build_installation.py
/workspace/.venvs/blender-models/bin/python verify_blends.py
python validate_installation.py
python package_installation.py
```

Keep highland-installation-proposed.yaml as the model source of truth when revising geometry. prepare_spec.py recreates the initial spec; do not run it over later field edits. build_installation.py reads the YAML. package_installation.py and validation use the matching installation-data.json generated from that same YAML when packaging.

## Validation

See validation.json for automated results and VISUAL-REVIEW.md for the visual inspection record. These checks establish source identity, proposed network continuity and delivery integrity; they do not establish field dimensions, hydraulic performance or code approval. The previous source atlas files remain unchanged.
'''
 (ROOT/'README.md').write_text(report)

def zip_package():
 destination=ROOT.parent/'Highland-installation-model.zip'
 files=['README.md','VISUAL-REVIEW.md','Highland-installation-storyboard.pdf','Highland-installation-sequence.mp4',
  'Highland-installation-unit-B.blend','Highland-installation-unit-B.glb','Highland-installation-shared.blend','Highland-installation-shared.glb',
  'highland-installation-proposed.yaml','highland-installation-existing-reference.yaml','installation-data.json','installation-elements.csv',
  'validation.json','blender-validation.json','build-result.json','prepare_spec.py','build_installation.py','validate_installation.py','verify_blends.py','package_installation.py',
  'unit-b-plan.png','unit-b-service.png','risers-200dpi.png']
 with zipfile.ZipFile(destination,'w',zipfile.ZIP_DEFLATED) as z:
  for name in ['Highland-original.pdf','source-manifest.json']:
   z.write(ROOT.parent/name,name)
  for name in files:
   p=ROOT/name
   if p.exists():z.write(p,'Highland-installation/'+name)
  for p in (ROOT/'renders').glob('*.png'):z.write(p,'Highland-installation/renders/'+p.name)
 print('Package:',destination)

if __name__=='__main__':
 # Refresh downstream artifacts from the governing YAML, including later field edits.
 import yaml
 S=yaml.safe_load((ROOT/'highland-installation-proposed.yaml').read_text())
 (ROOT/'installation-data.json').write_text(json.dumps(S,indent=2))
 overlay();pdf();video();handoff();zip_package()
