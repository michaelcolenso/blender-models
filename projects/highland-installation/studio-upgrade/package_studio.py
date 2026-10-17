"""Validate the completed review, extract its storyboard, and package the project."""
import argparse
import hashlib
import json
import shutil
import subprocess
import time
import zipfile
from pathlib import Path

from PIL import Image,ImageDraw,ImageFont
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

ROOT=Path(__file__).resolve().parent
PROJECT=ROOT.parent
REPO=PROJECT.parents[1]
OUT=ROOT/'output'
DEST=REPO/'deliverables/highland-installation/studio-upgrade'
MOVIE=OUT/'Highland-repipe-studio-90s-1080p.mp4'


def probe(path):
    return json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(path)],stderr=subprocess.DEVNULL))


def await_movie(watch):
    while True:
        try:
            p=probe(MOVIE)
            v=next(s for s in p['streams'] if s['codec_type']=='video')
            if int(v.get('nb_frames',0))==2160:return p
        except (FileNotFoundError,subprocess.CalledProcessError,StopIteration,ValueError):pass
        if not watch:raise RuntimeError('Completed 90-second review is not available yet.')
        time.sleep(2)


def validate(p):
    v=next(s for s in p['streams'] if s['codec_type']=='video')
    a=next(s for s in p['streams'] if s['codec_type']=='audio')
    conditions={
        'exact_90_seconds':abs(float(p['format']['duration'])-90)<.02,
        '1080p':(v['width'],v['height'])==(1920,1080),
        '24fps_2160_frames':v['avg_frame_rate']=='24/1' and int(v['nb_frames'])==2160,
        'h264_yuv420p':v['codec_name']=='h264' and v['pix_fmt']=='yuv420p',
        'aac_48k_stereo':a['codec_name']=='aac' and int(a['sample_rate'])==48000 and int(a['channels'])==2,
        'selectable_narration_captions':any(s['codec_type']=='subtitle' for s in p['streams']),
    }
    profile=json.loads((OUT/'sequence-profile.json').read_text())
    assert profile['source_blend_sha256']==hashlib.sha256((OUT/'Highland-studio-upgrade.blend').read_bytes()).hexdigest()
    spec=json.loads((PROJECT/'animation-90s/animation-spec.json').read_text())
    for name,expected in spec['sources'].items():
        conditions['original_source_unchanged_'+name]=hashlib.sha256((PROJECT/'installation'/name).read_bytes()).hexdigest()==expected
    frames=sorted((OUT/'raw').glob('*/*.png'))
    conditions['native_frame_coverage']=len(frames)==round((90+1)*profile['native_fps'])
    conditions['native_frame_sidecars']=all(p.with_suffix('.json').exists() for p in frames)
    conditions['blender_source_staging_checks']=json.loads((OUT/'studio-validation.json').read_text())['passed']
    assert all(conditions.values()),conditions
    report={'passed':True,'checks':conditions,'render_profile':profile,'delivery_note':'1080p review: Cycles model imagery sampled at the recorded native resolution/fps, motion-interpolated to 24 fps and scaled; sharp editorial graphics added at delivery size. Full native-production settings are in the guide.'}
    (OUT/'delivery-validation.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


def storyboard():
    folder=OUT/'storyboard'
    folder.mkdir(exist_ok=True)
    times=[1.5,13,23.5,42.5,55.5,69,80,88]
    pdf=canvas.Canvas(str(OUT/'Highland-studio-storyboard.pdf'),pagesize=(960,540))
    pdf.setTitle('Highland studio treatment — eight review frames')
    contact=Image.new('RGB',(1920,540),'#F7F6F2')
    for i,t in enumerate(times):
        target=folder/f'shot-{i+1:02}.png'
        subprocess.run(['ffmpeg','-y','-loglevel','error','-ss',str(t),'-i',str(MOVIE),'-frames:v','1',str(target)],check=True)
        image=Image.open(target).convert('RGB')
        assert image.size==(1920,1080)
        pdf.drawImage(ImageReader(image),0,0,width=960,height=540);pdf.showPage()
        small=image.resize((480,270),Image.Resampling.LANCZOS)
        contact.paste(small,((i%4)*480,(i//4)*270))
    pdf.save();contact.save(OUT/'Highland-studio-storyboard.png')
    # Extra frames cover the dissolve labels and the proposed isolation close-up.
    for t in [0,4,6.5,60.5,66.5,68.5]:
        subprocess.run(['ffmpeg','-y','-loglevel','error','-ss',str(t),'-i',str(MOVIE),'-frames:v','1',str(folder/f'qa-{t:04.1f}s.png')],check=True)


def copy_deliverables():
    DEST.mkdir(parents=True,exist_ok=True)
    for name in ['Highland-repipe-studio-90s-1080p.mp4','Highland-studio-upgrade.blend','Highland-studio-upgrade-guide.pdf','Highland-studio-storyboard.pdf','Highland-studio-storyboard.png','Highland-studio-color-reference.png','studio-validation.json','media-validation.json','delivery-validation.json','sequence-profile.json']:
        shutil.copy2(OUT/name,DEST/name)
    shutil.copy2(ROOT/'UPGRADE-GUIDE.md',DEST/'UPGRADE-GUIDE.md')
    target=DEST/'storyboard';target.mkdir(exist_ok=True)
    for p in (OUT/'storyboard').glob('shot-*.png'):shutil.copy2(p,target/p.name)
    check=Image.open(DEST/'Highland-studio-color-reference.png')
    assert check.getpixel((0,0))==(247,246,242)


def package():
    target=DEST/'Highland-studio-upgrade-editable.zip'
    prefix='Highland-studio-upgrade/'
    files=[]
    for p in ROOT.iterdir():
        if p.is_file() and p.suffix in {'.py','.json','.md','.txt'}:files.append((p,p.relative_to(REPO)))
    for p in (ROOT/'assets').iterdir():
        if p.is_file():files.append((p,p.relative_to(REPO)))
    for name in ['Highland-studio-upgrade.blend','Highland-studio-upgrade-guide.pdf','Highland-studio-storyboard.pdf','studio-validation.json','media-validation.json','build-validation.json','delivery-validation.json','sequence-profile.json']:
        p=OUT/name;files.append((p,p.relative_to(REPO)))
    for name in ['Highland-repipe-90s.blend','animation-spec.json','editorial.ass','editorial-events.json','opening-source.png','Highland-repipe-90s.srt','audio/mix.wav','audio/CREDITS.txt','audio/ljspeech-MODEL_CARD']:
        p=PROJECT/'animation-90s'/name;files.append((p,p.relative_to(REPO)))
    for name in ['Highland-installation-unit-B.blend','Highland-installation-shared.blend','installation-data.json','highland-installation-proposed.yaml','highland-installation-existing-reference.yaml','installation-elements.csv']:
        p=PROJECT/'installation'/name;files.append((p,p.relative_to(REPO)))
    for name in ['Highland-original.pdf','source-manifest.json']:
        p=PROJECT/name;files.append((p,p.relative_to(REPO)))
    for name in ['deliverables/highland-exterior/Highland-exterior.blend','projects/highland-exterior/exterior.spec.json','projects/highland-exterior/README.md','projects/highland-exterior/photo-manifest.json']:
        files.append((REPO/name,Path(name)))
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        z.writestr(prefix+'README.txt','Open projects/highland-installation/studio-upgrade/output/Highland-studio-upgrade.blend for the three editable 3D scenes. Read the guide PDF in the same output folder. Scripts and all rebuild source inputs retain their repository-relative layout. The MP4 review is a separate download.\n')
        for path,relative in files:z.write(path,prefix+str(relative))
        for p in (OUT/'storyboard').glob('shot-*.png'):z.write(p,prefix+str(p.relative_to(REPO)))
    with zipfile.ZipFile(target) as z:assert z.testzip() is None
    manifest=[]
    for name in [MOVIE.name,target.name,'Highland-studio-upgrade.blend','Highland-studio-upgrade-guide.pdf','Highland-studio-storyboard.pdf']:
        p=DEST/name
        with p.open('rb') as f:digest=hashlib.file_digest(f,'sha256').hexdigest()
        manifest.append({'name':name,'bytes':p.stat().st_size,'sha256':digest})
    (DEST/'delivery-files.json').write_text(json.dumps({'files':manifest},indent=2)+'\n')
    print('STUDIO_PACKAGE_COMPLETE',target,flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--watch',action='store_true')
    parser.add_argument('--package-only',action='store_true')
    args=parser.parse_args()
    if args.package_only:package()
    else:
        validate(await_movie(args.watch));storyboard();copy_deliverables()
        print('STUDIO_DELIVERY_VALIDATED; inspect storyboard before --package-only',flush=True)
