"""Validate native Cycles frames, add phone captions, and encode the owner film."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageStat
import audio

ROOT=Path(__file__).resolve().parents[4]
FPS,COUNT=24,624
CHAPTERS=[(0,'ARRIVAL','200 W. Highland'),(5.2,'ENTRY','East glazing / Lobby 110'),(8.8,'CORRIDOR 108','Approaching Elevator M1'),(13.2,'ELEVATOR M1','Boarding at R1'),(15.2,'ARCHITECTURAL SECTION','R1 to R2 / 10 ft 3 in rise'),(19.2,'CORRIDOR 208','Toward Stair M1')]


def font(size,bold=False):
    return ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans'+('-Bold' if bold else '')+'.ttf',size)


def main():
    p=argparse.ArgumentParser();p.add_argument('--frames',type=Path,default=ROOT/'build/highland-blender/frames');p.add_argument('--output',type=Path,default=ROOT/'projects/highland/deliverables/blender-film');p.add_argument('--review-only',action='store_true',help='Caption the available review frames without encoding a film');a=p.parse_args()
    a.output.mkdir(parents=True,exist_ok=True);comps=a.frames.parent/'composited';comps.mkdir(exist_ok=True)
    files=sorted(a.frames.glob('frame_*.png')) if a.review_only else [a.frames/f'frame_{j:04d}.png' for j in range(1,COUNT+1)]
    if not files:raise RuntimeError('No Blender frames found')
    missing=[p.name for p in files if not p.exists()]
    if missing:raise RuntimeError(f'Missing native Blender frames: {missing[:12]}')
    size=Image.open(files[0]).size;w,h=size;scale=w/540
    fonts={key:font(max(9,round(s*scale)),bold) for key,s,bold in [('small',12,False),('tag',15,True),('title',23,True),('sub',17,False)]}
    for src in files:
        j=int(src.stem.split('_')[-1])-1
        base=Image.open(src).convert('RGB');assert base.size==size
        if j%72==0:assert max(ImageStat.Stat(base).stddev)>10,src
        t=j/FPS;over=Image.new('RGBA',size,(0,0,0,0));d=ImageDraw.Draw(over)
        for y in range(round(130*scale)):
            d.line((0,y,w,y),fill=(5,12,18,int(155*(1-y/(130*scale)))))
        for y in range(h-round(155*scale),h):
            d.line((0,y,w,y),fill=(5,12,18,int(200*(y-(h-155*scale))/(155*scale))))
        x=round(24*scale)
        d.text((x,round(22*scale)),'200 W. HIGHLAND / OWNER TOUR',font=fonts['tag'],fill=(222,193,141,255))
        d.text((x,round(48*scale)),'Lobby → Corridors 108 + 208',font=fonts['title'],fill='white')
        chapter=next(c for c in reversed(CHAPTERS) if t>=c[0])
        d.text((x,h-round(123*scale)),chapter[1],font=fonts['tag'],fill=(233,201,146,255))
        d.text((x,h-round(96*scale)),chapter[2],font=fonts['sub'],fill='white')
        if 15.2<=t<=19.1:
            u=max(0,min(1,(t-16)/1.8));u=u*u*(3-2*u)
            d.text((x,h-round(68*scale)),f'ELEVATION +{353+10.25*u:.2f} FT',font=fonts['small'],fill=(215,225,234,255))
        d.line((x,h-round(43*scale),w-x,h-round(43*scale)),fill=(210,210,210,100),width=1)
        d.line((x,h-round(43*scale),x+(w-2*x)*j/(COUNT-1),h-round(43*scale)),fill=(225,185,116,255),width=2)
        d.text((x,h-round(30*scale)),'Drawing-based study / interior details and finishes illustrative',font=fonts['small'],fill=(200,212,220,255))
        # A small schematic camera marker is driven by the same source route.
        from build_blender import trajectory, I
        pos,look=trajectory(t);upper=t>=17.8
        mx,my=w-round(108*scale),round(105*scale);mw,mh=round(84*scale),round(125*scale)
        d.rounded_rectangle((mx-8*scale,my-22*scale,mx+mw+8*scale,my+mh+9*scale),radius=7*scale,fill=(6,19,27,160))
        d.text((mx,my-17*scale),'R2' if upper else 'R1',font=fonts['small'],fill=(237,205,151,255))
        def mappt(xi,yi):return (mx+(xi-800)/700*mw,my+(1570-yi)/950*mh)
        for bounds in ([(879,951,670,1540)] if upper else [(879,951,670,1540),(951,1120,1296,1368),(1120,1475,1260,1405)]):
            x0,x1,y0,y1=bounds;a0=mappt(x0,y1);a1=mappt(x1,y0);d.rectangle((*a0,*a1),fill=(206,196,158,50),outline=(210,184,130,190),width=1)
        q=mappt(pos.x/I,pos.y/I);q=(max(mx,min(mx+mw,q[0])),max(my,min(my+mh,q[1])))
        d.ellipse((q[0]-3*scale,q[1]-3*scale,q[0]+3*scale,q[1]+3*scale),fill=(255,221,146,255))
        Image.alpha_composite(base.convert('RGBA'),over).convert('RGB').save(comps/f'frame_{j+1:04d}.png')
    if a.review_only:
        print(f'Captioned {len(files)} real Blender review frames in {comps}');return
    audio.BUILD=a.frames.parent;sound=audio.synthesize()
    movie=a.output/'Highland-Blender-walkthrough.mp4'
    subprocess.run(['ffmpeg','-y','-loglevel','error','-framerate',str(FPS),'-start_number','1','-i',str(comps/'frame_%04d.png'),'-i',str(sound),'-c:v','libx264','-preset','medium','-crf','18','-pix_fmt','yuv420p','-c:a','aac','-b:a','160k','-movflags','+faststart','-shortest',str(movie)],check=True)
    probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(movie)]))
    video=next(s for s in probe['streams'] if s['codec_type']=='video');soundtrack=next(s for s in probe['streams'] if s['codec_type']=='audio')
    assert (int(video['nb_frames']),video['r_frame_rate'],video['codec_name'])==(COUNT,'24/1','h264')
    assert abs(float(probe['format']['duration'])-26)<.06 and soundtrack['channels']==2
    for name,t in [('Highland-Blender-poster.png',22),('Highland-Blender-section.png',16.5)]:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-ss',str(t),'-i',str(movie),'-frames:v','1',str(a.output/name)],check=True)
    subprocess.run(['ffmpeg','-y','-loglevel','error','-ss','13','-t','7','-i',str(movie),'-vf','fps=8,scale=270:-1:flags=lanczos,split[a][b];[a]palettegen[p];[b][p]paletteuse','-loop','0',str(a.output/'Highland-Blender-preview.gif')],check=True)
    report={'engine':'Blender 5.0.1 / Cycles CPU','frames':COUNT,'fps':FPS,'resolution':size,'duration_seconds':26,'audio':'stereo AAC','video_sha256':hashlib.sha256(movie.read_bytes()).hexdigest(),'source_frame_count':len(files)}
    report['assembler_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    provenance=a.frames.parent/'native-frame-provenance.json'
    if provenance.exists():report['native_frame_provenance_sha256']=hashlib.sha256(provenance.read_bytes()).hexdigest()
    (a.output/'media-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))


if __name__=='__main__':main()
