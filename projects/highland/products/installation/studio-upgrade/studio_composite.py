"""Exact-color display plate, editorial graphics and narrated 90-second assembly.

Blender's RGBA PNGs have already passed through AgX. Alpha over the paper in
display-linear sRGB, then add display-referred typography. The PNG background
is exact; H.264 color conversion/quantization can change individual pixels.
"""
import argparse
import json
import subprocess
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent
OUT = ROOT/'output'
C = json.loads((ROOT/'studio-config.json').read_text())
SPEC = json.loads((PROJECT/'animation-90s/animation-spec.json').read_text())
EVENTS = json.loads((PROJECT/'animation-90s/editorial-events.json').read_text())
FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
BOLD = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
PAPER = tuple(int(C['background_srgb'][i:i+2],16) for i in (1,3,5))
OLD = SPEC['palette']
COLOR_REPLACEMENTS = {OLD.get(k):v for k,v in C['palette'].items() if k in OLD}
for e in EVENTS:
    e['color'] = COLOR_REPLACEMENTS.get(e['color'],e['color'])
    if e['type']=='text' and e['color']==C['palette']['access']:
        e['color']=C['palette']['accent_ink']
    if e.get('text')=='Follow the water': e['text']='Exterior to\nsystem'
    if e.get('text')=='One shared system. A coordinated replacement.': e['text']='Begin at the building. Follow the water.'
    if e.get('text')=='Three connected services': e['text']='Exterior overview'
    if e.get('text')=='Source-labeled riser groups': e['text']='Three connected services'
    if e.get('text')=='P3.02 · PDF 13' and e['start']==0:e['text']='Exterior study / P3.02'
EVENTS += [
    {'type':'text','text':'ASSEMBLY HIGHLIGHT · NOT WATER FLOW','start':29,'end':45,'x':96,'y':1790,'size':29,'color':C['palette']['ink'],'bold':True},
    {'type':'text','text':'SCHEMATIC FLOW · AFTER DEPICTED TRANSFER','start':67,'end':85,'x':96,'y':1790,'size':29,'color':C['palette']['ink'],'bold':True},
]
# Match the access legend's symbol to its dashed volume rather than a solid pipe.
for e in list(EVENTS):
    if e['type']=='rect' and e['x']==2920 and e['y']==1708 and e['w']==24:
        EVENTS.remove(e)
        for dx,dy,w,h in [(0,0,8,3),(0,0,3,8),(16,0,8,3),(21,0,3,8),(0,21,8,3),(0,16,3,8),(16,21,8,3),(21,16,3,8)]:
            EVENTS.append(dict(e,x=e['x']+dx,y=e['y']+dy,w=w,h=h))
SHOTS = [
    ('01-exterior',0,4.5),('01-shared',3.5,8),
    *[(f"{s['id']:02}-unit" if s['scene']=='unit' else '08-shared',s['start'],s['end']) for s in SPEC['shots'][1:]],
]


def linear(x):
    return np.where(x<=.04045,x/12.92,((x+.055)/1.055)**2.4)


def display(x):
    return np.where(x<=.0031308,x*12.92,1.055*np.maximum(x,0)**(1/2.4)-.055)


_INK = None
_INK_MIPS = {}


def blueprint_ink():
    global _INK
    if _INK is not None:return _INK
    src=np.asarray(Image.open(ROOT/'assets/unit-b-plan-400dpi.png').convert('RGB'))
    rgb=src.astype(np.float32)/255
    luminance=rgb[:,:,0]*.2126+rgb[:,:,1]*.7152+rgb[:,:,2]*.0722
    b=C['blueprint'];alpha=np.clip((b['paper_white_point']-luminance)/(b['paper_white_point']-b['ink_black_point']),0,1)*b['opacity']
    ink=np.empty((*src.shape[:2],4),dtype=np.uint8)
    ink[:,:,:3]=[int(b['ink_srgb'][i:i+2],16) for i in (1,3,5)]
    saturation=(rgb.max(axis=2)-rgb.min(axis=2))/np.maximum(rgb.max(axis=2),.001)
    colored=saturation>.12
    ink[:,:,:3][colored]=src[colored]
    ink[:,:,3]=np.rint(alpha*255).astype(np.uint8)
    _INK=ink
    return ink


def background(image,metadata):
    import cv2
    w,h=image.size
    result=Image.new('RGBA',(w,h),PAPER+(255,))
    corners=metadata.get('blueprint_corners')
    if corners:
        ink=blueprint_ink();ih,iw=ink.shape[:2]
        # Prefilter fine CAD strokes before perspective minification. Cubic
        # sampling alone can alias a 6384px drawing into a 960px viewport.
        mip_width=min(iw,max(2048,w*2))
        if mip_width<iw:
            if mip_width not in _INK_MIPS:
                _INK_MIPS[mip_width]=cv2.resize(ink,(mip_width,round(ih*mip_width/iw)),interpolation=cv2.INTER_AREA)
            ink=_INK_MIPS[mip_width];ih,iw=ink.shape[:2]
        start=np.float32([[0,0],[iw-1,0],[iw-1,ih-1],[0,ih-1]])
        end=np.float32([[x*w,y*h] for x,y in corners])
        transform=cv2.getPerspectiveTransform(start,end)
        warped=cv2.warpPerspective(ink,transform,(w,h),flags=cv2.INTER_CUBIC,borderMode=cv2.BORDER_CONSTANT)
        result.alpha_composite(Image.fromarray(warped))
    for face in metadata.get('context_faces',[]):
        layer=Image.new('RGBA',(w,h),(0,0,0,0));d=ImageDraw.Draw(layer)
        color=(224,233,235,24) if face['role']=='ghost_wall' else (236,175,57,6)
        d.polygon([(x*w,y*h) for x,y in face['points']],fill=color)
        result.alpha_composite(layer)
    return np.asarray(result.convert('RGB'),dtype=np.float32)/255


def paper_over(image,metadata=None):
    src = np.asarray(image.convert('RGBA'),dtype=np.float32)/255
    profile=OUT/'sequence-profile.json'
    preview=metadata.get('preview') if metadata and 'preview' in metadata else (json.loads(profile.read_text()).get('preview') if profile.exists() else False)
    if preview:
        # Denoising RGB alone leaves low-sample shadow-catcher alpha grain.
        # Keep opaque/saturated geometry and its AA edges; smooth only the
        # low-alpha neutral receiving layer, before adding the blueprint/text.
        import cv2
        alpha0=src[:,:,3]
        rgb0=src[:,:,:3]
        saturation=(rgb0.max(axis=2)-rgb0.min(axis=2))/np.maximum(rgb0.max(axis=2),.001)
        protect=((alpha0>.65)|((alpha0>.08)&(saturation>.16))).astype(np.uint8)
        protect=cv2.dilate(protect,np.ones((3,3),np.uint8))>0
        weight=np.where(protect,0,alpha0)
        filtered=cv2.GaussianBlur(weight,(0,0),1.6)
        premult=cv2.GaussianBlur(rgb0*weight[:,:,None],(0,0),1.6)
        color=premult/np.maximum(filtered[:,:,None],1e-6)
        src[:,:,:3]=np.where(protect[:,:,None],rgb0,color)
        src[:,:,3]=np.where(protect,alpha0,filtered*.85)
    alpha = src[:,:,3:4]
    base=background(image,metadata) if metadata else np.array(PAPER,dtype=np.float32)/255
    combined = linear(src[:,:,:3])*alpha+linear(base)*(1-alpha)
    rgb = np.rint(np.clip(display(combined),0,1)*255).astype(np.uint8)
    if not metadata:rgb[alpha[:,:,0]==0] = PAPER
    return Image.fromarray(rgb)


def editorial(image,t,size=(1920,1080)):
    result = Image.new('RGB',size,PAPER)
    scale = size[0]/3840
    tile = (round(32*scale),round(272*scale),round(2816*scale),round(1584*scale))
    image = image.resize(tile[2:],Image.Resampling.LANCZOS)
    result.paste(image,tile[:2])
    d = ImageDraw.Draw(result)
    for e in EVENTS:
        if not e['start']<=t<e['end']:continue
        x,y = e['x']*scale,e['y']*scale
        if e['type']=='rect':
            d.rectangle((x,y,x+e['w']*scale,y+e['h']*scale),fill=e['color'])
        else:
            f = ImageFont.truetype(BOLD if e['bold'] else FONT,round(e['size']*scale))
            d.multiline_text((x,y),e['text'],font=f,fill=e['color'],spacing=round(e['size']*.22*scale))
    d.rectangle((96*scale,2132*scale,(96+3648*t/90)*scale,2138*scale),fill=C['palette']['ink'])
    return result


def badges(image,items):
    """Screen-space labels: vector text stays horizontal regardless of camera."""
    d=ImageDraw.Draw(image)
    f=ImageFont.truetype(BOLD,17)
    for pin in items:
        ax,ay=16+pin['u']*1408,136+pin['v']*792
        text=pin['text']
        width=d.textbbox((0,0),text,font=f)[2]+24
        x=max(28,min(1424-width-10,ax+24))
        y=max(150,min(880,ay-60))
        left=pin['text'].startswith('Unit 101 irrigation')
        if left:
            x=max(28,min(1424-width-10,ax-width-24));y=max(150,min(880,ay+24))
        color=C['palette']['access'] if pin['warning'] else '#66757B'
        d.line((ax,ay,x+width-10 if left else x+10,y+16),fill=color,width=2)
        d.ellipse((ax-3,ay-3,ax+3,ay+3),fill=color)
        d.rounded_rectangle((x,y,x+width,y+34),radius=5,fill=PAPER,outline=color,width=1)
        d.text((x+12,y+7),text,font=f,fill=C['palette']['ink'])
    return image


def reviews():
    folder = OUT/'review'
    folder.mkdir(exist_ok=True)
    for p in sorted((OUT/'review-raw').glob('*.png')):
        t=float(p.stem.rsplit('-',1)[-1][:-1])
        meta=p.with_suffix('.json')
        metadata=json.loads(meta.read_text()) if meta.exists() else None
        image=editorial(paper_over(Image.open(p),metadata),t)
        if metadata:badges(image,metadata['pins'])
        image.save(folder/p.name)
        assert image.getpixel((0,0))==PAPER
    print('REVIEW_COMPOSITE_PASS',len(list(folder.glob('*.png'))),flush=True)


def color_reference():
    profile=json.loads((OUT/'sequence-profile.json').read_text())
    index=round((69-58)*profile['native_fps'])
    raw=OUT/'raw/06-unit'/f'{index:04}.png'
    meta=json.loads(raw.with_suffix('.json').read_text())
    result=editorial(paper_over(Image.open(raw),meta),69)
    badges(result,meta['pins'])
    assert result.getpixel((0,0))==PAPER
    result.save(OUT/'Highland-studio-color-reference.png')


def ass_time(t):
    cs=round(t*100)
    return f'{cs//360000}:{cs//6000%60:02}:{cs//100%60:02}.{cs%100:02}'


def write_ass(native_fps=None):
    old=(PROJECT/'animation-90s/editorial.ass').read_text()
    header=old.split('[Events]')[0]+'[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n'
    rows=[header]
    for e in EVENTS:
        color='&H'+e['color'][5:7]+e['color'][3:5]+e['color'][1:3]+'&'
        tags=f"\\an7\\pos({e['x']},{e['y']})\\1c{color}\\bord0\\shad0"
        if e['type']=='rect':
            tags+='\\p1'
            body=f"m 0 0 l {e['w']} 0 {e['w']} {e['h']} 0 {e['h']}"
        else:
            tags+=f"\\fs{e['size']}\\b{1 if e['bold'] else 0}"
            if e['text']!=SPEC['footer']:tags+='\\fad(180,120)'
            body=e['text'].replace('\n','\\N')
        rows.append(f"Dialogue: 1,{ass_time(e['start'])},{ass_time(e['end'])},Editorial,,0,0,0,,{{{tags}}}{body}\n")
    # A pulsing, uncalibrated test icon reinforces the required hold. It contains
    # no pressure scale, numerical value or success indication.
    for n in range(4):
        t=54+n
        angle=np.linspace(0,2*np.pi,49)
        outer=[(44*np.cos(a),44*np.sin(a)) for a in angle]
        inner=[(39*np.cos(a),39*np.sin(a)) for a in angle[::-1]]
        shape='m '+' '.join(f'{x:.1f} {y:.1f}' for x,y in outer[:1])+' l '+' '.join(f'{x:.1f} {y:.1f}' for x,y in outer[1:])
        shape+=' m '+' '.join(f'{x:.1f} {y:.1f}' for x,y in inner[:1])+' l '+' '.join(f'{x:.1f} {y:.1f}' for x,y in inner[1:])
        rows.append(f'Dialogue: 3,{ass_time(t)},{ass_time(t+1)},Editorial,,0,0,0,,{{\\an7\\pos(3660,1230)\\p1\\1c&H39AFEC&\\bord0\\shad0\\fad(220,220)}}{shape}\n')
    # Each pin is projected by Blender at every native camera sample. ASS draws
    # the label after scaling, keeping its text sharp in the 1080p master.
    for name,start,end in SHOTS:
        metas=[m for m in sorted((OUT/'raw'/name).glob('*.json')) if m.stem.isdigit()]
        for index,meta in enumerate(metas):
            sample=json.loads(meta.read_text())
            following=json.loads(metas[min(index+1,len(metas)-1)].read_text())
            t=sample['t'];stop=min(end,t+1/(native_fps or C['render']['native_fps']))
            if name=='01-exterior' or (name=='01-shared' and t<4.25):continue
            for pin in sample['pins']:
                ax,ay=32+pin['u']*2816,272+pin['v']*1584
                width=min(1150,38*len(pin['text'])*.53+48)
                x=max(56,min(2830-width,ax+48));y=max(300,min(1760,ay-120))
                next_pin=next((p for p in following['pins'] if p['text']==pin['text']),pin)
                ax2,ay2=32+next_pin['u']*2816,272+next_pin['v']*1584
                x2=max(56,min(2830-width,ax2+48));y2=max(300,min(1760,ay2-120))
                left=pin['text'].startswith('Unit 101 irrigation')
                if left:
                    x=max(56,min(2830-width,ax-width-48));y=max(300,min(1760,ay+48))
                    x2=max(56,min(2830-width,ax2-width-48));y2=max(300,min(1760,ay2+48))
                border='&H3979AC&' if pin['warning'] else '&H7B7566&'
                tags=f'\\an7\\move({x:.1f},{y:.1f},{x2:.1f},{y2:.1f})\\fs38\\b1\\1c&H3A3429&\\3c&HF2F6F7&\\bord6\\shad0'
                rows.append(f"Dialogue: 4,{ass_time(t)},{ass_time(stop)},Editorial,,0,0,0,,{{{tags}}}{pin['text']}\n")
                endpoint=x+width-16 if left else x+16
                shape=f'm 0 0 l {endpoint-ax:.1f} {y+30-ay:.1f} {endpoint+2-ax:.1f} {y+30-ay:.1f} 2 0'
                rows.append(f'Dialogue: 3,{ass_time(t)},{ass_time(stop)},Editorial,,0,0,0,,{{\\an7\\move({ax:.1f},{ay:.1f},{ax2:.1f},{ay2:.1f})\\p1\\1c{border}\\bord0\\shad0}}{shape}\n')
    path=OUT/'studio-editorial.ass'
    path.write_text(''.join(rows))
    (OUT/'studio-editorial-events.json').write_text(json.dumps(EVENTS,indent=2,ensure_ascii=False)+'\n')
    return path


def audio_cues():
    import wave
    source=PROJECT/'animation-90s/audio/mix.wav'
    with wave.open(str(source),'rb') as w:
        assert w.getsampwidth()==2 and w.getframerate()==48000
        channels=w.getnchannels();rate=w.getframerate()
        audio=np.frombuffer(w.readframes(w.getnframes()),dtype='<i2').reshape(-1,channels).astype(np.float32)/32768
    for when in [4,8,18,22,29,38,45,54,58,61,64,67,73,77,82,85]:
        n=round(.11*rate);t=np.arange(n)/rate
        cue=np.sin(math_tau()*780*t)*np.exp(-t*42)*np.sin(np.pi*np.arange(n)/n)*.007
        index=round(when*rate);audio[index:index+n]+=cue[:,None]
    # Quiet noise swells accompany the focus glides, below the narration/score.
    rng=np.random.default_rng(200)
    for when in [3.5,20,50.5,64.5]:
        n=round(.7*rate);noise=rng.normal(0,.002,n)
        noise=np.convolve(noise,np.ones(32)/32,mode='same')*np.sin(np.pi*np.arange(n)/n)**2
        index=round(when*rate);audio[index:index+n]+=noise[:,None]
    target=OUT/'studio-mix.wav'
    with wave.open(str(target),'wb') as w:
        w.setnchannels(channels);w.setsampwidth(2);w.setframerate(rate)
        w.writeframes((np.clip(audio,-1,1)*32767).astype('<i2').tobytes())
    return target


def math_tau():
    return 2*np.pi


def run(command,log):
    with (OUT/log).open('w') as stream:
        subprocess.run(command,check=True,stdout=stream,stderr=subprocess.STDOUT)


def valid_clip(path,expected_frames):
    try:
        result=json.loads(subprocess.check_output(['ffprobe','-v','error','-select_streams','v:0','-show_entries','stream=nb_frames,avg_frame_rate','-of','json',str(path)],stderr=subprocess.DEVNULL))
        v=result['streams'][0]
        return v['avg_frame_rate']=='24/1' and int(v['nb_frames'])==expected_frames
    except (FileNotFoundError,subprocess.CalledProcessError,ValueError,KeyError,IndexError):
        return False


def interpolate(folder,count,target,fps,native_fps):
    import cv2
    cv2.setNumThreads(1)
    factor=fps//native_fps
    assert fps%native_fps==0
    def read(n):
        metadata=json.loads((folder/f'{n:04}.json').read_text())
        return np.asarray(paper_over(Image.open(folder/f'{n:04}.png'),metadata))[:,:,::-1].copy()
    first=read(0)
    height,width=first.shape[:2]
    estimator=cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM)
    grid_x,grid_y=np.meshgrid(np.arange(width,dtype=np.float32),np.arange(height,dtype=np.float32))
    flow_size=(width//2,height//2)
    with (OUT/(target.stem+'-flow.log')).open('w') as stream:
        proc=subprocess.Popen(['ffmpeg','-y','-loglevel','error','-f','rawvideo','-pix_fmt','bgr24','-s',f'{width}x{height}','-r',str(fps),'-i','pipe:0','-an','-vf','scale=out_color_matrix=bt709:out_range=tv,format=yuv420p','-c:v','libx264','-preset','veryfast','-crf','16','-threads','1','-color_primaries','bt709','-color_trc','bt709','-colorspace','bt709','-color_range','tv',str(target)],stdin=subprocess.PIPE,stdout=stream,stderr=subprocess.STDOUT)
        left=first
        for n in range(count):
            if factor==1:
                proc.stdin.write(read(n).tobytes())
                continue
            right=read(min(n+1,count-1))
            if n==count-1:
                for _ in range(factor):proc.stdin.write(left.tobytes())
                break
            a=cv2.cvtColor(cv2.resize(left,flow_size),cv2.COLOR_BGR2GRAY)
            b=cv2.cvtColor(cv2.resize(right,flow_size),cv2.COLOR_BGR2GRAY)
            forward=cv2.resize(estimator.calc(a,b,None),(width,height))*2
            backward=cv2.resize(estimator.calc(b,a,None),(width,height))*2
            proc.stdin.write(left.tobytes())
            for i in range(1,factor):
                u=i/factor
                wa=cv2.remap(left,grid_x-u*forward[:,:,0],grid_y-u*forward[:,:,1],cv2.INTER_CUBIC,borderMode=cv2.BORDER_REPLICATE)
                wb=cv2.remap(right,grid_x-(1-u)*backward[:,:,0],grid_y-(1-u)*backward[:,:,1],cv2.INTER_CUBIC,borderMode=cv2.BORDER_REPLICATE)
                proc.stdin.write(cv2.addWeighted(wa,1-u,wb,u,0).tobytes())
            left=right
        proc.stdin.close()
        assert proc.wait()==0,target


def sequence(watch,native_fps,master_width=1920):
    clips=OUT/'clips'
    clips.mkdir(exist_ok=True)
    for name,start,end in SHOTS:
        count=round((end-start)*native_fps)
        folder=OUT/'raw'/name
        while not ((folder/f'{count-1:04}.png').exists() and (folder/f'{count-1:04}.json').exists()):
            if not watch:raise FileNotFoundError(f'Incomplete native frames: {name}')
            time.sleep(2)
        target=clips/(name+'.mp4')
        expected_frames=round((end-start)*24)
        if not valid_clip(target,expected_frames):
            temporary=target.with_name(target.stem+'-encoding.mp4')
            interpolate(folder,count,temporary,24,native_fps)
            assert valid_clip(temporary,expected_frames),name
            temporary.replace(target)
        print('STUDIO_CLIP_COMPLETE',name,flush=True)
    opening=clips/'opening-08s.mp4'
    run(['ffmpeg','-y','-filter_complex_threads','1','-i',str(clips/'01-exterior.mp4'),'-i',str(clips/'01-shared.mp4'),'-filter_complex','[0:v][1:v]xfade=transition=fade:duration=1:offset=3.5,format=yuv420p[v]','-map','[v]','-t','8','-c:v','libx264','-crf','16','-threads','2',str(opening)],'opening-encode.log')
    assert valid_clip(opening,192),'Exterior/shared opening timing'
    listing=clips/'list.txt'
    listing.write_text("file 'opening-08s.mp4'\n"+''.join(f"file '{name}.mp4'\n" for name,_,_ in SHOTS[2:]))
    joined=OUT/'studio-model-90s.mp4'
    run(['ffmpeg','-y','-f','concat','-safe','0','-i',str(listing),'-c','copy',str(joined)],'concat.log')
    assert valid_clip(joined,2160),'Complete 90-second model timeline'
    ass=write_ass(native_fps)
    color_reference()
    target=OUT/('Highland-repipe-studio-90s-4K.mp4' if master_width==3840 else 'Highland-repipe-studio-90s-1080p.mp4')
    video=f'scale=2816:1584:flags=lanczos:in_color_matrix=bt709,format=rgb24,pad=3840:2160:32:272:color=0xf7f6f2,ass=filename={ass}' if master_width==3840 else f'scale=1408:792:flags=lanczos:in_color_matrix=bt709,format=rgb24,pad=1920:1080:16:136:color=0xf7f6f2,ass=filename={ass}'
    video+=',scale=out_color_matrix=bt709:out_range=tv,format=yuv420p'
    run(['ffmpeg','-y','-filter_threads','1','-i',str(joined),'-i',str(audio_cues()),'-i',str(PROJECT/'animation-90s/Highland-repipe-90s.srt'),'-map','0:v','-map','1:a','-map','2:0','-vf',video,'-t','90','-r','24','-c:v','libx264','-crf','18','-preset','veryfast','-threads','2','-color_primaries','bt709','-color_trc','bt709','-colorspace','bt709','-color_range','tv','-c:a','aac','-b:a','192k','-af','loudnorm=I=-16:TP=-1.5:LRA=9,aresample=48000','-c:s','mov_text','-movflags','+faststart',str(target)],'master-encode.log')
    print('STUDIO_MASTER_COMPLETE',target,flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--sequence',action='store_true')
    p.add_argument('--watch',action='store_true')
    p.add_argument('--native-fps',type=int,default=C['render']['native_fps'])
    p.add_argument('--master-width',type=int,choices=[1920,3840],default=1920)
    args=p.parse_args()
    if args.sequence:sequence(args.watch,args.native_fps,args.master_width)
    else:reviews()
