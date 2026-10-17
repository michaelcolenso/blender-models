"""Motion interpolation, native 4K editorial graphics and final narrated master."""
import json,subprocess,time,textwrap,sys
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parent;S=json.loads((ROOT/'animation-spec.json').read_text())
CLIPS=ROOT/'clips';CLIPS.mkdir(exist_ok=True)
W,H=3840,2160;TILE=(32,272,2816,1584);P=S['palette']
FONT='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf';BOLD='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
def font(n,bold=False):return ImageFont.truetype(BOLD if bold else FONT,n)
def wrap_pixels(text,size,width,bold=False):
 f=font(size,bold);lines=[];line=''
 for word in text.split():
  test=(line+' '+word).strip()
  if f.getlength(test)>width and line:lines.append(line);line=word
  else:line=test
 if line:lines.append(line)
 return '\n'.join(lines)
def text(t,start,end,x,y,size,color=None,bold=False,width=900):
 return {'type':'text','text':wrap_pixels(t,size,width,bold),'start':start,'end':end,'x':x,'y':y,'size':size,'color':color or P['ink'],'bold':bold}
def rect(start,end,x,y,w,h,color):return {'type':'rect','start':start,'end':end,'x':x,'y':y,'w':w,'h':h,'color':color}
def events():
 e=[text('200 W HIGHLAND',0,90,96,72,54,bold=True,width=1800),
    text('PROPOSED REPIPE  /  UNIT B · 106',0,90,2740,92,32,P['muted'],width=1000),
    text(S['footer'],0,90,96,2073,34,P['muted'],width=3500),
    rect(0,90,96,209,3648,3,'#d4ddda'),rect(0,90,96,2132,3648,6,'#d4ddda')]
 for j,(system,label) in enumerate([('CW','Cold water'),('HW','Hot water'),('HWC','Circulation return'),('access','Proposed access')]):
  y=1510+j*62;e.extend([rect(0,90,2920,y+12,24,24,P[system]),text(label,0,90,2966,y,36,P['muted'],width=740)])
 for sh in S['shots']:
  a,b=sh['start'],sh['end'];e.append(text(f"{sh['id']:02} / 08",a,b,2920,330,36,P['access'],bold=True,width=750))
  e.append(text(sh['title'],a,b,2920,414,82,bold=True,width=790))
  y=735
  for i,item in enumerate(sh['points']):
   e.append(rect(a,b,2920,y+15,10,10,P['access']))
   tx=text(item,a,b,2950,y,47,P['muted'],width=750);e.append(tx);y+=max(115,len(tx['text'].splitlines())*65+37)
  e.append(text(sh['source'],a,b,2920,1390,32,P['muted'],width=790))
  e.append(text(sh['caption'],a,b,96,1892,72,bold=True,width=2710))
  if sh['id']==1:
   e.append(text('Unit 101 · irrigation drop / P3.02',4.2,8,2920,1162,31,P['access'],width=790))
   e.append(text('Unit 302 · alternate wall / P4.02',5,8,2920,1260,31,P['access'],width=790))
  if sh['id']==5:
   e.append(rect(54,58,2900,1150,840,170,'#f9e9cc'))
   e.append(text('REQUIRED TEST + INSPECTION',54,58,2930,1175,32,P['ink'],bold=True,width=770))
   e.append(text('Before service transfer',54,58,2930,1250,35,P['ink'],width=770))
  if sh['id']==6:
   for a2,b2,label in [(58,61,'ISOLATE + DRAIN'),(61,64,'CONNECT + INSPECT'),(64,67,'CHECK + FLUSH'),(67,73,'BALANCE CIRCULATION')]:
    e.append(rect(a2,b2,2900,1150,840,150,'#e8eeea'));e.append(text(label,a2,b2,2930,1190,35,P['ink'],bold=True,width=770))
  if sh['id']==7:
   e.append(text('VALVE ID  ·  PHOTO RECORD  ·  AS-BUILT',77,85,2920,1160,32,P['access'],bold=True,width=790))
 return e
E=events()
def opening_image():
 im=Image.new('RGB',(1600,900),P['paper']);src=Image.open(ROOT.parent/'installation/risers-200dpi.png').convert('RGB');src.thumbnail((1510,720));im.paste(src,((1600-src.width)//2,120+(720-src.height)//2));d=ImageDraw.Draw(im)
 d.text((45,36),'P3.02  /  SOURCE DOMESTIC WATER RISER DIAGRAM',font=font(30,True),fill=P['ink'])
 d.text((45,850),'Drawing issue · 29 October 2007',font=font(24),fill=P['muted'])
 im.save(ROOT/'opening-source.png')
def png_frame(sh,path,target=None,t=None):
 t=(sh['start']+sh['end'])/2 if t is None else t
 canvas=Image.new('RGB',(W,H),P['paper']);im=Image.open(path).convert('RGB').resize((TILE[2],TILE[3]),Image.Resampling.LANCZOS);canvas.paste(im,TILE[:2]);d=ImageDraw.Draw(canvas)
 for e in E:
  if not e['start']<=t<e['end']:continue
  if e['type']=='rect':d.rectangle((e['x'],e['y'],e['x']+e['w'],e['y']+e['h']),fill=e['color'])
  else:d.multiline_text((e['x'],e['y']),e['text'],font=font(e['size'],e['bold']),fill=e['color'],spacing=int(e['size']*.22))
 d.rectangle((96,2132,96+round(3648*t/90),2138),fill=P['ink'])
 if target:canvas.save(target)
 return canvas
def ass_time(t):
 cs=round(t*100);return f'{cs//360000}:{cs//6000%60:02}:{cs//100%60:02}.{cs%100:02}'
def color(h):return '&H'+h[5:7]+h[3:5]+h[1:3]+'&'
def write_ass():
 header='''[Script Info]
ScriptType: v4.00+
PlayResX: 3840
PlayResY: 2160
ScaledBorderAndShadow: yes
WrapStyle: 2
YCbCr Matrix: TV.709

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Editorial,DejaVu Sans,48,&H00433D12,&H00433D12,&H00FFFFFF,&H00000000,0,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
'''
 lines=[header]
 for e in E:
  pos=f"\\an7\\pos({e['x']},{e['y']})\\1c{color(e['color'])}\\bord0\\shad0"
  if e['type']=='rect':
   tags=pos+'\\p1';body=f"m 0 0 l {e['w']} 0 {e['w']} {e['h']} 0 {e['h']}"
  else:
   tags=pos+f"\\fs{e['size']}\\b{1 if e['bold'] else 0}\\fad(180,120)";body=e['text'].replace('\n','\\N')
  lines.append(f"Dialogue: 1,{ass_time(e['start'])},{ass_time(e['end'])},Editorial,,0,0,0,,{{{tags}}}{body}\n")
 # A moving rectangular clip exposes the full-length progress rule smoothly.
 tags=f"\\an7\\pos(96,2132)\\p1\\bord0\\shad0\\1c{color(P['ink'])}\\clip(96,2132,96,2138)\\t(0,90000,\\clip(96,2132,3744,2138))"
 lines.append('Dialogue: 2,0:00:00.00,0:01:30.00,Editorial,,0,0,0,,{'+tags+'}m 0 0 l 3648 0 3648 6 0 6\n')
 (ROOT/'editorial.ass').write_text(''.join(lines));(ROOT/'editorial-events.json').write_text(json.dumps(E,indent=2,ensure_ascii=False))
def run(cmd,log):
 with (ROOT/log).open('w') as out:subprocess.run(cmd,check=True,stdout=out,stderr=subprocess.STDOUT)
def probe(path):
 return json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(path)]))
def interpolate_clip(folder,count,target):
 import cv2,numpy as np
 cv2.setNumThreads(1)
 width,height=S['render_size'];factor=S['fps']//S['render_fps']
 assert S['fps']%S['render_fps']==0
 cmd=['ffmpeg','-y','-loglevel','error','-f','rawvideo','-pix_fmt','bgr24','-s',f'{width}x{height}','-r','24','-i','pipe:0','-an','-c:v','libx264','-preset','veryfast','-crf','16','-threads','1','-pix_fmt','yuv420p','-movflags','+faststart',str(target)]
 with (ROOT/(target.stem+'-flow.log')).open('w') as log:
  proc=subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=log,stderr=subprocess.STDOUT)
  estimator=cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM)
  estimator.setGradientDescentIterations(16);estimator.setVariationalRefinementIterations(3)
  flow_size=(width//2,height//2);grid_x,grid_y=np.meshgrid(np.arange(width,dtype=np.float32),np.arange(height,dtype=np.float32))
  left=cv2.imread(str(folder/'0000.png'));assert left is not None
  for i in range(count):
   right=cv2.imread(str(folder/f'{min(i+1,count-1):04}.png'));assert right is not None
   if i==count-1:
    for _ in range(factor):proc.stdin.write(left.tobytes())
    break
   a=cv2.cvtColor(cv2.resize(left,flow_size),cv2.COLOR_BGR2GRAY);b=cv2.cvtColor(cv2.resize(right,flow_size),cv2.COLOR_BGR2GRAY)
   forward=cv2.resize(estimator.calc(a,b,None),(width,height))*2
   backward=cv2.resize(estimator.calc(b,a,None),(width,height))*2
   proc.stdin.write(left.tobytes())
   for j in range(1,factor):
    u=j/factor
    wa=cv2.remap(left,grid_x-u*forward[:,:,0],grid_y-u*forward[:,:,1],cv2.INTER_CUBIC,borderMode=cv2.BORDER_REPLICATE)
    wb=cv2.remap(right,grid_x-(1-u)*backward[:,:,0],grid_y-(1-u)*backward[:,:,1],cv2.INTER_CUBIC,borderMode=cv2.BORDER_REPLICATE)
    mixed=cv2.addWeighted(wa,1-u,wb,u,0)
    proc.stdin.write(mixed.tobytes())
   left=right
  proc.stdin.close();code=proc.wait()
  if code:raise RuntimeError('Frame interpolation/encoding failed: '+str(log.name))
def encode_shots(watch=False):
 for sh in S['shots']:
  count=round((sh['end']-sh['start'])*S['render_fps']);folder=ROOT/'frames'/f"shot-{sh['id']:02}"
  while not (folder/f'{count-1:04}.png').exists():
   if not watch:raise RuntimeError('Missing frames for shot '+str(sh['id']))
   time.sleep(2)
  target=CLIPS/f"shot-{sh['id']:02}.mp4";duration=sh['end']-sh['start']
  if target.exists():
   try:
    if abs(float(probe(target)['format']['duration'])-duration)<.02:continue
   except Exception:pass
  started=time.time()
  interpolate_clip(folder,count,target)
  assert abs(float(probe(target)['format']['duration'])-duration)<.02
  print('CLIP_COMPLETE',sh['id'],duration,'s; processing',round(time.time()-started,1),'s',flush=True)
 listing=ROOT/'clip-list.txt';listing.write_text(''.join(f"file 'clips/shot-{sh['id']:02}.mp4'\n" for sh in S['shots']))
 run(['ffmpeg','-y','-f','concat','-safe','0','-i',str(listing),'-c','copy',str(ROOT/'uncaptioned-90s.mp4')],'concat.log')
def master():
 opening_image();write_ass();target=ROOT/'Highland-repipe-90s-4K.mp4'
 filters=f"[0:v]scale=2816:1584:flags=lanczos,pad=3840:2160:32:272:color=0xf5f5ee[base];[2:v]format=rgba,scale=2816:1584:flags=lanczos,fade=t=out:st=1.6:d=0.9:alpha=1[scan];[base][scan]overlay=32:272:enable='lt(t,2.5)':shortest=1[open];[open]ass=filename={ROOT/'editorial.ass'}[v]"
 run(['ffmpeg','-y','-threads','2','-filter_complex_threads','1','-i',str(ROOT/'uncaptioned-90s.mp4'),'-i',str(ROOT/'audio/mix.wav'),'-loop','1','-framerate','24','-i',str(ROOT/'opening-source.png'),'-i',str(ROOT/'Highland-repipe-90s.srt'),'-filter_complex',filters,'-map','[v]','-map','1:a','-map','3:0','-c:v','libx264','-preset','veryfast','-crf','18','-threads','2','-pix_fmt','yuv420p','-r','24','-frames:v','2160','-t','90','-c:a','aac','-b:a','192k','-af','loudnorm=I=-16:TP=-1.5:LRA=9,aresample=48000,afade=t=out:st=89.7:d=0.3','-c:s','mov_text','-metadata:s:s:0','language=eng','-metadata','title=200 W Highland | Proposed Repipe Installation','-movflags','+faststart',str(target)],'master-encode.log')
 print('MASTER_COMPLETE',target,flush=True)
 run(['ffmpeg','-y','-threads','2','-i',str(target),'-map','0:v','-map','0:a','-map','0:s?','-vf','scale=1920:1080:flags=lanczos','-c:v','libx264','-crf','21','-preset','veryfast','-threads','2','-c:a','copy','-c:s','copy','-movflags','+faststart',str(ROOT/'Highland-repipe-90s-1080p.mp4')],'review-encode.log')
 print('REVIEW_COMPLETE',flush=True)
def previews():
 folder=ROOT/'storyboard-preview';folder.mkdir(exist_ok=True)
 contact=Image.new('RGB',(1920,540),'white')
 for i,sh in enumerate(S['shots']):
  im=png_frame(sh,ROOT/'preview'/f"shot-{sh['id']:02}.png",folder/f"{sh['id']:02}.png")
  im.thumbnail((480,270));contact.paste(im,((i%4)*480,(i//4)*270))
 contact.save(ROOT/'storyboard-preview-contact.png');write_ass();opening_image()
if __name__=='__main__':
 if '--previews' in sys.argv:previews()
 else:encode_shots('--watch' in sys.argv);master()
