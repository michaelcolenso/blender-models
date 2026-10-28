"""Full-frame architectural film: work first, typography close to the action.

Uses the validated clean CG plate, with no surrounding frame or sidebar. Titles
settle softly beside the work; the physical sequence and approved audio stay intact.
"""
import argparse
import bisect
import hashlib
import json
import math
import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parent
PROJECT=ROOT.parent
OUT=ROOT/'output'
OUT.mkdir(exist_ok=True)
D=json.loads((ROOT/'design.json').read_text())
W,H=D['width'],D['height']
FPS=D['fps']
ASSETS=ROOT/'assets'
FONT_DIR=ASSETS/'fonts'
SERIF=FONT_DIR/'NotoSerifDisplay-Regular.ttf'
SANS=FONT_DIR/'NotoSans-Regular.ttf'
SOURCE=OUT/'media/model-90s.mp4' if (OUT/'media/model-90s.mp4').exists() else PROJECT/'studio-upgrade/output/studio-model-90s.mp4'
APPROVED=OUT/'media/approved-audio.m4a' if (OUT/'media/approved-audio.m4a').exists() else PROJECT/'studio-upgrade/output/Highland-repipe-studio-90s-1080p.mp4'
TRACKS=json.loads((ASSETS/'anchors.json').read_text())['tracks']
TRACKS={t['id']:t for t in TRACKS}
FONT_CACHE={}

def digest(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def optional_subtitles(path):
    """Clear the MP4 subtitle track's enabled-by-default bit, retaining selection.

    Some MOV muxers enable the first subtitle even with disposition=0. This
    changes only tkhd flags, never media bytes, sample tables or timings.
    """
    data=path.read_bytes()
    def boxes(start,end):
        p=start
        while p+8<=end:
            size=int.from_bytes(data[p:p+4],'big');kind=data[p+4:p+8];header=8
            if size==1:size=int.from_bytes(data[p+8:p+16],'big');header=16
            if size==0:size=end-p
            if size<header or p+size>end:raise ValueError('Invalid MP4 atom bounds')
            yield kind,p+header,p+size
            p+=size
    offsets=[]
    for kind,start,end in boxes(0,len(data)):
        if kind!=b'moov':continue
        for kind,ts,te in boxes(start,end):
            if kind!=b'trak':continue
            tkhd=None;handler=None
            for kind,s,e in boxes(ts,te):
                if kind==b'tkhd':tkhd=s
                if kind==b'mdia':
                    for kind,ms,me in boxes(s,e):
                        if kind==b'hdlr':handler=data[ms+8:ms+12]
            if tkhd is not None and handler in {b'text',b'sbtl',b'subt'}:offsets.append(tkhd+3)
    with path.open('r+b') as f:
        for offset in offsets:f.seek(offset);f.write(bytes([data[offset]&0xFE]))

def ease(value):
    value=max(0,min(1,value))
    return value*value*(3-2*value)

def reframe(t):
    keys=D['reframe']
    if t<=keys[0][0]:return tuple(keys[0][1:])
    if t>=keys[-1][0]:return tuple(keys[-1][1:])
    a,b=next((a,b) for a,b in zip(keys,keys[1:]) if a[0]<=t<b[0])
    u=ease((t-a[0])/(b[0]-a[0]))
    return tuple(x*(1-u)+y*u for x,y in zip(a[1:],b[1:]))

def point_at(track,t):
    samples=track['samples']
    if not samples:return None
    times=[s['t'] for s in samples]
    n=bisect.bisect_right(times,t)
    if n==0:a=b=samples[0];u=0
    elif n==len(samples):a=b=samples[-1];u=0
    else:
        a,b=samples[n-1:n+1];u=(t-a['t'])/(b['t']-a['t'])
    x=a['x']*(1-u)+b['x']*u;y=a['y']*(1-u)+b['y']*u
    # Invert the previous inset coordinates. The new film has no viewport inset.
    x=(x-32)/2816;y=(y-272)/1584
    z,cx,cy=reframe(t)
    return (W*(.5+(x-cx)*z),H*(.5+(y-cy)*z))

def font(size,sans=False):
    key=(round(size),sans)
    if key not in FONT_CACHE:FONT_CACHE[key]=ImageFont.truetype(str(SANS if sans else SERIF),max(1,key[0]))
    return FONT_CACHE[key]

def text_size(text,size,sans=False):
    f=font(size,sans)
    lines=text.splitlines()
    return max(f.getlength(line) for line in lines),len(lines)*size*1.23

def cue_pose(cue,t):
    intro=ease((t-cue['start'])/.72)
    outro=ease((cue['end']-t)/.72)
    alpha=intro*outro
    x,y=cue['position'][0]*W,cue['position'][1]*H
    anchor=None
    if cue.get('anchor') in TRACKS:
        track=TRACKS[cue['anchor']]
        anchor=point_at(track,t)
        reference=point_at(track,(cue['start']+cue['end'])/2)
        x+=(anchor[0]-reference[0])*.22;y+=(anchor[1]-reference[1])*.22
        if not track['samples'][0]['t']<=t<=track['samples'][-1]['t']:anchor=None
    y+=16*(1-intro)-6*(1-outro)
    size=cue['size']*(.985+.015*intro)
    width,height=text_size(cue['text'],size,cue.get('sans',False))
    x=max(52,min(W-52-width,x));y=max(62,min(H-122-height,y))
    return x,y,size,alpha,height,anchor

def frame_events(t):
    result=[]
    for cue in D['cues']:
        if not cue['start']<=t<cue['end']:continue
        x,y,size,alpha,height,anchor=cue_pose(cue,t)
        result.append({'id':cue['id'],'type':'text','text':cue['text'],'x':x,'y':y,'size':size,'alpha':alpha,'sans':cue.get('sans',False),'color':D['ink'],'blur':1.4*(1-ease((t-cue['start'])/.72))})
        if cue.get('detail'):
            result.append({'id':cue['id']+'-detail','type':'text','text':cue['detail'],'x':x+2,'y':y+height+14,'size':17,'alpha':alpha*ease((t-cue['start']-.2)/.7),'sans':True,'color':D['muted'],'blur':0})
        if anchor and cue['start']<=t<cue['start']+1.3 and 45<anchor[0]<W-45 and 45<anchor[1]<H-75:
            # A caption-arrival glimmer; it never travels along a pipe.
            result.append({'id':cue['id']+'-glimmer','type':'dot','x':anchor[0],'y':anchor[1],'alpha':.34*math.sin(math.pi*(t-cue['start'])/1.3)**2,'color':D['accent']})
    if 54<=t<58:
        result.append({'id':'required-hold','type':'text','text':'Before service transfer','x':W*.60+2,'y':H*.24+174,'size':16,'alpha':ease((t-54)/.6)*ease((58-t)/.5),'sans':True,'color':'#8C704C','blur':0})
    if 4.9<=t<7.9:
        cue=next(c for c in D['cues'] if c['id']=='shared');x,y,_,_,height,_=cue_pose(cue,t)
        result.append({'id':'exceptions','type':'text','text':'Unit 101 / 302 exceptions · separate review','x':x+2,'y':y+height+58,'size':14,'alpha':ease((t-4.9)/.6)*ease((7.9-t)/.5),'sans':True,'color':D['muted'],'blur':0})
    if 29<=t<85:
        words=[('Cold','#147ECC'),('Hot','#D94736'),('Return','#E7772C'),('Access','#9A722D')]
        x=W-430
        for label,color in words:
            result.append({'id':'legend-'+label,'type':'text','text':'· '+label,'x':x,'y':H-72,'size':16,'alpha':.80*ease((t-29)/.7),'sans':True,'color':color,'blur':0})
            x+=104
        qualifier='Assembly reveal · isolated replacement' if t<45 else ('Schematic flow · after depicted transfer' if t>=67 else None)
        if qualifier:
            result.append({'id':'flow-meaning','type':'text','text':qualifier,'x':52,'y':H-72,'size':13,'alpha':.72,'sans':True,'color':D['muted'],'blur':0})
    result.append({'id':'footer','type':'text','text':D['footer'],'x':52,'y':H-37,'size':13,'alpha':.82,'sans':True,'color':'#4B5554','blur':0})
    return result

def ass_time(t):
    n=round(t*100)
    return f'{n//360000}:{n//6000%60:02}:{n//100%60:02}.{n%100:02}'

def ass_color(value):return '&H'+value[5:7]+value[3:5]+value[1:3]+'&'

def write_ass():
    header='''[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 2
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Air,Noto Serif Display,54,&H003A3429,&H003A3429,&H00F2F6F7,&H00000000,0,0,0,0,100,100,0,0,1,0.5,0,7,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
'''
    lines=[header]
    for f in range(2160):
        t=f/FPS
        for e in frame_events(t):
            opacity=round(255*(1-max(0,min(1,e['alpha']))))
            pos=f"\\an7\\pos({e['x']:.2f},{e['y']:.2f})\\alpha&H{opacity:02X}&\\1c{ass_color(e['color'])}\\shad0"
            if e['type']=='dot':
                tags=pos+'\\an5\\p1\\bord0\\blur3'
                body='m -3 0 b -3 -4 3 -4 3 0 b 3 4 -3 4 -3 0'
                layer=1
            else:
                name='Noto Sans' if e['sans'] else 'Noto Serif Display'
                tags=pos+f"\\fn{name}\\fs{e['size']:.2f}\\bord{0 if e['sans'] else .5}\\blur{e['blur']:.2f}"
                body=e['text'].replace('\n','\\N');layer=3
            lines.append(f"Dialogue: {layer},{ass_time(t)},{ass_time((f+1)/FPS)},Air,{e['id']},0,0,0,,{{{tags}}}{body}\n")
    path=OUT/'immersive-titles.ass';path.write_text(''.join(lines))
    return path

def expression(component):
    # zoompan's output-frame index is the same 24 fps timeline as the title rig.
    result=str(D['reframe'][-1][component])
    for a,b in reversed(list(zip(D['reframe'],D['reframe'][1:]))):
        u=f'clip((on/{FPS}-{a[0]})/{b[0]-a[0]},0,1)'
        smooth=f'(({u})*({u})*(3-2*({u})))'
        value=f'({a[component]}+({b[component]-a[component]})*{smooth})'
        result=f'if(lt(on,{b[0]*FPS}),{value},{result})'
    return result

def filtergraph(ass=None):
    z=expression(1);cx=expression(2);cy=expression(3)
    chain=f"scale=iw:ih:in_color_matrix=bt709,format=rgb24,pad=iw*2:ih*2:iw/2:ih/2:color=0x{D['paper'][1:]},format=gbrp"
    chain+=f",zoompan=z='2*({z})':x='iw*(.25+.5*({cx}))-iw/zoom/2':y='ih*(.25+.5*({cy}))-ih/zoom/2':d=1:s={W}x{H}:fps={FPS},format=rgb24"
    if ass:chain+=f',ass=filename={ass}:fontsdir={FONT_DIR}'
    return chain

def source_frame(t):
    p=OUT/'design-reference'/f'{t:04.1f}.png'
    p.parent.mkdir(exist_ok=True)
    if not p.exists():subprocess.run(['ffmpeg','-y','-loglevel','error','-ss',str(t),'-i',str(SOURCE),'-frames:v','1',str(p)],check=True)
    return Image.open(p).convert('RGB')

def still(t):
    im=source_frame(t);z,cx,cy=reframe(t)
    # PIL's extent transform and FFmpeg zoompan share this same crop rectangle.
    iw,ih=im.size
    bounds=((cx-.5/z)*iw,(cy-.5/z)*ih,(cx+.5/z)*iw,(cy+.5/z)*ih)
    result=im.transform((W,H),Image.Transform.EXTENT,bounds,resample=Image.Resampling.BICUBIC,fillcolor=D['paper']).convert('RGBA')
    overlay=Image.new('RGBA',(W,H),(0,0,0,0));d=ImageDraw.Draw(overlay)
    for e in frame_events(t):
        color=tuple(int(e['color'][i:i+2],16) for i in (1,3,5))+(round(e['alpha']*255),)
        if e['type']=='dot':d.ellipse((e['x']-3,e['y']-3,e['x']+3,e['y']+3),fill=color)
        else:
            for n,line in enumerate(e['text'].splitlines()):
                d.text((e['x'],e['y']+n*e['size']*1.23),line,font=font(e['size'],e['sans']),fill=color,anchor='lt')
    result.alpha_composite(overlay)
    return result.convert('RGB')

def previews():
    folder=OUT/'storyboard';folder.mkdir(exist_ok=True)
    times=[1.8,6.2,13,22.5,33.5,55.5,60.5,69.5,79,88]
    contact=Image.new('RGB',(1920,648),D['paper'])
    for i,t in enumerate(times):
        im=still(t);im.save(folder/f'{i+1:02}-{t:04.1f}s.png')
        im.thumbnail((384,216));contact.paste(im,((i%5)*384,(i//5)*216))
    contact=contact.crop((0,0,1920,432));contact.save(OUT/'Highland-immersive-storyboard.png')
    write_ass()
    print('IMMERSIVE_PREVIEW_READY',folder,flush=True)

def export():
    global SOURCE,APPROVED
    media=OUT/'media';media.mkdir(exist_ok=True)
    model=media/'model-90s.mp4';audio=media/'approved-audio.m4a';captions=media/'narration.srt'
    if not model.exists():shutil.copy2(SOURCE,model)
    if not audio.exists():
        subprocess.run(['ffmpeg','-y','-loglevel','error','-i',str(APPROVED),'-map','0:a','-c:a','copy','-t','90',str(audio)],check=True)
    if not captions.exists():shutil.copy2(PROJECT/'animation-90s/Highland-repipe-90s.srt',captions)
    SOURCE,APPROVED=model,audio
    ass=write_ass();target=OUT/'Highland-repipe-immersive-90s-1080p.mp4'
    temporary=target.with_name(target.stem+'-encoding.mp4')
    command=['ffmpeg','-y','-filter_threads','1','-i',str(SOURCE),'-i',str(APPROVED),'-i',str(captions),'-map','0:v','-map','1:a','-map','2:0',
             '-vf',filtergraph(ass)+',scale=out_color_matrix=bt709:out_range=tv,format=yuv420p','-t','90','-frames:v','2160','-r','24','-c:v','libx264','-crf','18','-preset','veryfast','-threads','2',
             '-color_primaries','bt709','-color_trc','bt709','-colorspace','bt709','-color_range','tv','-c:a','copy','-c:s','mov_text','-disposition:s:0','0',
             '-metadata','title=200 W Highland | Repipe installation — immersive cut','-movflags','+faststart',str(temporary)]
    with (OUT/'encode.log').open('w') as log:subprocess.run(command,check=True,stdout=log,stderr=subprocess.STDOUT)
    optional_subtitles(temporary)
    probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(temporary)]))
    video=next(s for s in probe['streams'] if s['codec_type']=='video')
    assert video['width']==W and video['height']==H and int(video['nb_frames'])==2160 and video['avg_frame_rate']=='24/1'
    assert abs(float(video['duration'])-90)<.001
    temporary.replace(target)
    (OUT/'source-manifest.json').write_text(json.dumps({'clean_cg':{'path':str(SOURCE.relative_to(PROJECT)),'sha256':digest(SOURCE)},
       'approved_audio_movie_sha256':digest(APPROVED),'design_sha256':digest(ROOT/'design.json'),
       'native_cg_profile':json.loads((PROJECT/'studio-upgrade/output/sequence-profile.json').read_text()),
       'layout':'Full-frame model imagery, no surrounding inset/border/sidebar. New typography and editorial focus transform; original 3D geometry/sequence unchanged.'},indent=2)+'\n')
    print('IMMERSIVE_FILM_READY',target,flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--previews',action='store_true')
    args=p.parse_args()
    if args.previews:previews()
    else:export()
