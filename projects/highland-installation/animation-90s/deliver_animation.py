"""Validate and package the finished movie, captions, storyboard and editable rig."""
import json,subprocess,time,sys,hashlib,zipfile,wave,re
from pathlib import Path
from PIL import Image,ImageStat,ImageChops,ImageDraw
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
ROOT=Path(__file__).resolve().parent;S=json.loads((ROOT/'animation-spec.json').read_text())
CHECKS=[]
def check(name,ok,detail=''):
 CHECKS.append({'check':name,'passed':bool(ok),'detail':detail})
 if not ok:raise AssertionError(name+': '+str(detail))
def probe(path):
 return json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(path)],stderr=subprocess.DEVNULL))
def await_master():
 while True:
  try:
   p=probe(ROOT/'Highland-repipe-90s-1080p.mp4');v=next(s for s in p['streams'] if s['codec_type']=='video')
   if int(v.get('nb_frames',0))==2160:return
  except Exception:pass
  if '--watch' not in sys.argv:raise RuntimeError('Finished master/review encode not available.')
  time.sleep(2)
def package():
 destination=ROOT.parent/'Highland-repipe-animation-editable.zip'
 include=['Highland-repipe-90s.blend','Highland-repipe-90s.srt','Highland-repipe-storyboard.pdf','README.md','VISUAL-REVIEW.md',
          'animation-spec.json','blender-validation.json','delivery-validation.json','editorial.ass','editorial-events.json','opening-source.png',
          'prepare_animation.py','animate_highland.py','compose_film.py','finalize_blender.py','make_audio.py','deliver_animation.py',
          'audio/mix.wav','audio/narration.wav','audio/original-score.wav','audio/timing.json','audio/CREDITS.txt','audio/ljspeech-MODEL_CARD']
 with zipfile.ZipFile(destination,'w',zipfile.ZIP_DEFLATED) as z:
  for name in include:
   p=ROOT/name
   if p.exists():z.write(p,'Highland-repipe/animation-90s/'+name)
  for p in (ROOT/'storyboard').glob('*.png'):z.write(p,'Highland-repipe/animation-90s/storyboard/'+p.name)
  for name in ['Highland-installation-unit-B.blend','Highland-installation-shared.blend','highland-installation-proposed.yaml','installation-data.json','unit-b-plan.png','unit-b-service.png','risers-200dpi.png']:
   z.write(ROOT.parent/'installation'/name,'Highland-repipe/installation/'+name)
 with zipfile.ZipFile(destination) as z:assert z.testzip() is None
 print('EDITABLE_PACKAGE',destination.stat().st_size,'bytes',flush=True)
 return destination
def validate():
 for path,size in [(ROOT/'Highland-repipe-90s-4K.mp4',(3840,2160)),(ROOT/'Highland-repipe-90s-1080p.mp4',(1920,1080))]:
  p=probe(path);v=next(x for x in p['streams'] if x['codec_type']=='video');a=next(x for x in p['streams'] if x['codec_type']=='audio')
  check(path.name+' resolution',(v['width'],v['height'])==size)
  check(path.name+' exact runtime',abs(float(p['format']['duration'])-90)<.05)
  check(path.name+' 24fps / 2160 frames',v['avg_frame_rate']=='24/1' and int(v['nb_frames'])==2160)
  check(path.name+' playback codecs',v['codec_name']=='h264' and a['codec_name']=='aac' and v['pix_fmt']=='yuv420p')
  check(path.name+' audio sample rate',int(a['sample_rate'])==48000)
 for filename,digest in S['sources'].items():check('Original unchanged: '+filename,hashlib.sha256((ROOT.parent/'installation'/filename).read_bytes()).hexdigest()==digest)
 states=json.loads((ROOT/'blender-validation.json').read_text())
 check('Source model geometry unchanged',all(x['unchanged'] for x in states['source_geometry'].values()),'94 unit and 45 shared elements compared, including transforms and pipe control points')
 check('Installation stage logic',all(states['staging'].values()))
 for sh in S['shots']:
  folder=ROOT/'frames'/f"shot-{sh['id']:02}";count=round((sh['end']-sh['start'])*S['render_fps'])
  check(f"Shot {sh['id']} native render coverage",all((folder/f'{n:04}.png').exists() for n in range(count)),str(count)+' native scene frames')
  a=Image.open(folder/'0000.png').convert('RGB').resize((160,90));b=Image.open(folder/f'{count-1:04}.png').convert('RGB').resize((160,90))
  check(f"Shot {sh['id']} animated",sum(ImageStat.Stat(ImageChops.difference(a,b)).mean)>.05)
 timing=json.loads((ROOT/'audio/timing.json').read_text())
 check('Narration captions cover all eight shots',len(timing)==8 and (ROOT/'Highland-repipe-90s.srt').read_text().count('-->')==8)
 check('Narration stays inside its shots',all(sh['start']<=t['start']<t['end']<=sh['end'] for sh,t in zip(S['shots'],timing)))
 check('Exact source-facing footer in graphics',S['footer'] in (ROOT/'editorial-events.json').read_text())
 return CHECKS
def optional_subtitles():
 for name in ['Highland-repipe-90s-4K.mp4','Highland-repipe-90s-1080p.mp4']:
  path=ROOT/name;temp=ROOT/(path.stem+'-metadata.mp4')
  subprocess.run(['ffmpeg','-y','-loglevel','error','-i',str(path),'-map','0','-c','copy','-disposition:s:0','0','-metadata:s:s:0','title=Narration captions (optional)','-movflags','+faststart',str(temp)],check=True)
  temp.replace(path)
def storyboard():
 out=ROOT/'storyboard';out.mkdir(exist_ok=True)
 times=[4.5,13,23.5,42.5,55.5,69,80,88]
 pdf=canvas.Canvas(str(ROOT/'Highland-repipe-storyboard.pdf'),pagesize=(1152,648));pdf.setTitle('200 W Highland — Animation Storyboard')
 for i,t in enumerate(times):
  path=out/f'shot-{i+1:02}.png'
  subprocess.run(['ffmpeg','-y','-loglevel','error','-ss',str(t),'-i',str(ROOT/'Highland-repipe-90s-4K.mp4'),'-frames:v','1',str(path)],check=True)
  im=Image.open(path).convert('RGB');check(f'Storyboard {i+1} 4K',im.size==(3840,2160))
  check(f'Storyboard {i+1} nonblank',max(ImageStat.Stat(im.resize((160,90))).stddev)>12)
  pdf.drawImage(ImageReader(im),0,0,width=1152,height=648);pdf.showPage()
 # Eight small review images in four columns / two rows.
 contact=Image.new('RGB',(1920,540),'white')
 for i in range(8):
  im=Image.open(out/f'shot-{i+1:02}.png').convert('RGB');im.thumbnail((480,270));contact.paste(im,((i%4)*480,(i//4)*270))
 contact.save(ROOT/'storyboard-contact.png');pdf.save()
def documentation():
 report='''# 200 W Highland — 90-second repipe animation

## Watch and review

- **Highland-repipe-90s-4K.mp4** — 90 seconds, 3840 × 2160, 24 fps, H.264/AAC, with narration, original instrumental music, graphic cues and on-screen editorial captions.
- **Highland-repipe-90s-1080p.mp4** — smaller review copy with the same sequence and audio.
- **Highland-repipe-90s.srt** — narration captions, timed to the actual synthesized voice. A selectable subtitle track is also embedded in the movies.
- **Highland-repipe-storyboard.pdf** — eight representative frames from the delivered master.
- **storyboard/shot-01.png … shot-08.png** — the same eight frames at 3840 × 2160.
- **Highland-repipe-90s.blend** — editable 90-second assembly with two source-derived 3D scenes, animated cameras, pipe growth, test/cutover visibility, presentation flow markers, native text/graphics and audio.

Open the Blender file on its **MASTER - 90 seconds** scene. The timeline is frames 1–2160 at 24 fps. Eight scene strips occupy the exact requested ranges. Edit geometry/cameras in **3D - Unit B installation** or **3D - Shared distribution**. The original installation models are included separately and unchanged. Extract the whole ZIP before opening; keep the audio and opening-source image beside the project in their provided folders.

## Sequence

00:00–00:08 — source drawing and shared system, with Unit 101 / Unit 302 exception references.
00:08–00:18 — verify routes, services and access; show protection.
00:18–00:29 — reveal access and support coordination; identify the kitchen low-wall route.
00:29–00:45 — grow the new cold, hot and circulation-return distribution.
00:45–00:58 — complete branches and show the required test/inspection hold.
00:58–01:13 — depict isolation, connection, final checks, flushing and return balancing; flow appears at 01:07.
01:13–01:25 — change access to restoration boundaries and document retained service access.
01:25–01:30 — return to the shared system for the closing frame.

## Source fidelity and limits

This is a proposed installation-method animation, not a record of completed work or a construction design. Physical pipe paths, sizes and elevations, service boundaries, access locations, supports and restoration areas retain the assumptions of the original source model. The source plan issue is 29 October 2007. Existing conditions and governing revisions require confirmation.

The movie does not add a surveyed building shell, a verified existing CPVC network, individual fixture quantities, an approved firestop detail, test readings, actual shutdown durations or measured flow performance. Existing-condition information remains in the unchanged drawing context. Unit B / 106 is a pilot, not a route automatically applied to other unit types. Unit 101's irrigation drop and Unit 302's alternate-wall note remain explicit exceptions. The original source title says 200 W Highland while its location block says 202 W Highland; that discrepancy remains unresolved in the source handoff.

Camera moves, schematic highlights and flow particles are presentation elements. Particles indicate conceptual direction after the depicted transfer; they are not a hydraulic simulation. Assembly devices remain coordination symbols. Required testing/inspection is shown as a future release condition, without an assertion that a field test passed.

## Production resolution and audio

The delivered master and editorial graphics are 3840 × 2160 at 24 fps. Model imagery was rendered in Cycles CPU at 1600 × 900 and six native samples per second, then motion-interpolated to 24 fps and scaled for the 4K composition. The editable Blender rig contains full 24 fps camera and construction animation and can be re-rendered at a higher native spatial/temporal sampling rate. Normal-based analytical shading keeps the diagram clear without altering the source geometry.

Narration is locally synthesized using Piper's en_US-ljspeech-high voice, whose model card identifies the LJ Speech public-domain dataset. It is not a recording of a project representative. Instrumental music and transition cues are an original procedural composition. See audio/CREDITS.txt. Separate narration, score and combined WAV files are included for editing.

## Validation

See delivery-validation.json and blender-validation.json. Checks cover source-file hashes, unchanged geometry for 94 unit elements and 45 shared elements, exact shot ranges, pipe-reveal order, testing/cutover states, flow timing and motion, restoration order, native frame coverage, movie resolution/runtime/frame rate/codecs, audio timing, captions and storyboard image integrity. Visual inspection is recorded in VISUAL-REVIEW.md.

## Rebuild

Keep the original installation spec as the geometry authority and animation-spec.json as the production timeline. Python scripts require Blender bpy 5.0.1, Pillow, NumPy, OpenCV and FFmpeg; audio regeneration additionally needs Piper, SciPy and the referenced voice model. The supplied WAV files allow visual re-rendering without downloading voice weights. The scripts use the supplied animation-90s / installation folder relationship. In this prepared workspace:

```bash
/workspace/.venvs/blender-models/bin/python animate_highland.py --resume
/workspace/.venvs/highland-audio/bin/python compose_film.py --watch
/workspace/.venvs/blender-models/bin/python finalize_blender.py
python deliver_animation.py
```

The MP4 graphics and Blender graphics use the same event/timing data; their rasterization can differ slightly. The native Blender master renders scene strips directly. The delivered movie uses the interpolated render/compositing pipeline described above.
'''
 (ROOT/'README.md').write_text(report)
def main():
 await_master();optional_subtitles();validate();storyboard();documentation()
 (ROOT/'delivery-validation.json').write_text(json.dumps({'passed':True,'checks':CHECKS,'render_method':S['render_method']},indent=2))
 package();print('DELIVERY_READY',len(CHECKS),'checks',flush=True)
if __name__=='__main__':main()
