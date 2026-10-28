"""Validate the full cut, decode review frames and package the editable sources."""
import hashlib
import json
import shutil
import subprocess
import zipfile
from pathlib import Path

from PIL import Image

import compose_immersive as film

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'output'
REPO=ROOT.parents[4]
DEST=REPO/'projects/highland/deliverables/installation/immersive-film'
MOVIE=OUT/'Highland-repipe-immersive-90s-1080p.mp4'
CHECKS=[]

def check(name,condition):
    CHECKS.append({'check':name,'passed':bool(condition)})
    assert condition,name

def audio_hash(path):
    data=subprocess.check_output(['ffmpeg','-v','error','-i',str(path),'-map','0:a:0','-c:a','copy','-f','adts','-'])
    return hashlib.sha256(data).hexdigest()

def validate():
    probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(MOVIE)]))
    v=next(s for s in probe['streams'] if s['codec_type']=='video')
    a=next(s for s in probe['streams'] if s['codec_type']=='audio')
    check('Full 90-second picture',abs(float(v['duration'])-90)<.001)
    check('Exactly 2160 frames at 24 fps',int(v['nb_frames'])==2160 and v['avg_frame_rate']=='24/1')
    check('1920x1080 H264 review',(v['width'],v['height'],v['codec_name'],v['pix_fmt'])==(1920,1080,'h264','yuv420p'))
    check('AAC stereo at 48 kHz',a['codec_name']=='aac' and a['channels']==2 and a['sample_rate']=='48000')
    check('Selectable narration captions',any(s['codec_type']=='subtitle' and s['codec_name']=='mov_text' and not s.get('disposition',{}).get('default') for s in probe['streams']))
    original=ROOT.parent/'studio-upgrade/output/Highland-repipe-studio-90s-1080p.mp4'
    if not original.exists():original=OUT/'media/approved-audio.m4a'
    check('Approved audio compressed payload unchanged',audio_hash(MOVIE)==audio_hash(original))
    check('Full-frame design with zero inset',film.D['layout']=='full_frame' and film.D['frame_inset']==0)
    check('No framing rectangle events',all(e['type'] in {'text','dot'} for f in range(2160) for e in film.frame_events(f/24)))
    check('Conceptual-status footer on every frame',all(any(e['id']=='footer' and e['alpha']>.8 for e in film.frame_events(f/24)) for f in range(2160)))
    check('Exterior opening framing retained',all(film.reframe(f/24)==(1,0.5,0.5) for f in range(192)))
    check('Whole-system closing framing retained',all(film.reframe(f/24)==(1,0.5,0.5) for f in range(2040,2160)))
    before=film.reframe(0)
    for f in range(1,2160):
        now=film.reframe(f/24)
        assert max(abs(a-b) for a,b in zip(now,before))<.005,'Abrupt editorial focus move'
        before=now
    check('Smooth editorial focus moves',True)
    for f in range(2160):
        for e in film.frame_events(f/24):
            if e['type']=='text' and e['alpha']>.1:
                width,height=film.text_size(e['text'],e['size'],e['sans'])
                assert 0<=e['x'] and e['x']+width<film.W and 0<=e['y'] and e['y']+height<film.H,(f,e['id'])
    check('Visible typography stays inside picture',True)
    editor=json.loads((OUT/'blender-validation.json').read_text())
    check('Retained 3D source geometry unchanged',editor['passed'] and editor['source_3D_geometry_unchanged'])
    check('Editable master occupies all 2160 frames',editor['master_picture_range']==[1,2161])
    check('Editable VSE channels below 128',editor['max_vse_channel']<128)
    check('Editable title text and timing match film',editor['title_text_and_intervals_match_film'])
    check('Original gate files unchanged',all(film.digest(ROOT.parent/'animation-90s'/name)==digest for name,digest in {
        'finalize_blender.py':'391df0eede54c97635ad07873f0bc88573fbb5dd660f30e130ca0fdc12a55778',
        'deliver_animation.py':'7ec90be7b854b78c28dd936e5e957a604455855f863b7213b141dabb9c5591eb'}.items()))
    report={'passed':True,'checks':CHECKS,'count':len(CHECKS),'scope':'Complete full-frame movie, audio, source/editor fidelity and graphics QA. Existing model geometry/provenance and required field checks remain unchanged.',
            'render_note':'1080p editorial review reuses the validated 960x540 / four-sample / two-native-fps CG plate, motion-interpolated to 24 fps. New full-frame typography and editorial reframing; no new 3D render is claimed.'}
    (OUT/'delivery-validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print('IMMERSIVE_DELIVERY_PASS',len(CHECKS),'checks',flush=True)

def storyboard():
    folder=OUT/'final-storyboard';folder.mkdir(exist_ok=True)
    times=[1.8,6.2,13,22.5,33.5,55.5,60.5,69.5,79,88]
    contact=Image.new('RGB',(1920,432),film.D['paper'])
    for i,t in enumerate(times):
        path=folder/f'{i+1:02}-{t:04.1f}s.png'
        subprocess.run(['ffmpeg','-y','-loglevel','error','-ss',str(t),'-i',str(MOVIE),'-frames:v','1',str(path)],check=True)
        im=Image.open(path).convert('RGB');assert im.size==(1920,1080)
        im.thumbnail((384,216));contact.paste(im,((i%5)*384,(i//5)*216))
    contact.save(OUT/'Highland-immersive-storyboard.png')
    # Caption arrivals and the focus move can also be compared frame by frame.
    for t in [0,19,19.35,19.75,20.3,29,31,34,89.9]:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-ss',str(t),'-i',str(MOVIE),'-frames:v','1',str(folder/f'qa-{t:05.2f}.png')],check=True)

def package():
    DEST.mkdir(parents=True,exist_ok=True)
    for name in [MOVIE.name,'Highland-immersive-editable.blend','Highland-immersive-storyboard.png','delivery-validation.json','blender-validation.json','source-manifest.json']:
        shutil.copy2(OUT/name,DEST/name)
    shutil.copy2(ROOT/'README.md',DEST/'README.md')
    (DEST/'storyboard').mkdir(exist_ok=True)
    for p in (OUT/'final-storyboard').glob('[0-9]*.png'):shutil.copy2(p,DEST/'storyboard'/p.name)
    target=DEST/'Highland-immersive-editable.zip';temporary=target.with_suffix('.encoding.zip')
    prefix='Highland-immersive/'
    files=[]
    for p in ROOT.iterdir():
        if p.is_file() and p.suffix in {'.py','.json','.md'}:files.append((p,p.relative_to(REPO)))
    for p in (ROOT/'assets').rglob('*'):
        if p.is_file():files.append((p,p.relative_to(REPO)))
    for p in (OUT/'media').iterdir():
        if p.is_file():files.append((p,p.relative_to(REPO)))
    for name in ['Highland-immersive-editable.blend','source-manifest.json','delivery-validation.json','blender-validation.json','immersive-titles.ass']:
        p=OUT/name;files.append((p,p.relative_to(REPO)))
    for name in ['highland-installation-proposed.yaml','installation-data.json','Highland-installation-unit-B.blend','Highland-installation-shared.blend']:
        p=ROOT.parent/'installation'/name;files.append((p,p.relative_to(REPO)))
    for name in ['Highland-original.pdf','source-manifest.json']:
        p=ROOT.parent/name;files.append((p,p.relative_to(REPO)))
    for name in ['finalize_blender.py','deliver_animation.py']:
        p=ROOT.parent/'animation-90s'/name;files.append((p,p.relative_to(REPO)))
    manifest={str(relative):{'bytes':p.stat().st_size,'sha256':film.digest(p)} for p,relative in files}
    with zipfile.ZipFile(temporary,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        z.writestr(prefix+'README.txt','Open projects/highland/products/installation/immersive-film/output/Highland-immersive-editable.blend on MASTER - Immersive film. Keep this entire directory tree. The final movie is a separate download.\n')
        z.writestr(prefix+'file-manifest.json',json.dumps(manifest,indent=2))
        for p,relative in files:z.write(p,prefix+str(relative))
    with zipfile.ZipFile(temporary) as z:assert z.testzip() is None
    temporary.replace(target)
    hashes={name:film.digest(DEST/name) for name in [MOVIE.name,target.name,'Highland-immersive-editable.blend']}
    (DEST/'delivery-files.json').write_text(json.dumps(hashes,indent=2)+'\n')
    print('IMMERSIVE_PACKAGE_READY',target,flush=True)

if __name__=='__main__':validate();storyboard();package()
