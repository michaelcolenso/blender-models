"""Package the integrated rig with the studio dependencies the legacy ZIP omits.

Use --review for the explicitly labeled eight-still/code-review package. Without
that flag, require fresh full-movie validation from unchanged deliver_animation.py.
"""
import argparse
import hashlib
import json
import zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parent
PROJECT=ROOT.parent
REPO=PROJECT.parents[3]

def digest(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def package(destination,review):
    destination.mkdir(parents=True,exist_ok=True)
    qa=json.loads((ROOT/'presentation-validation.json').read_text())
    assert qa['passed'] and qa['max_vse_channel']<128
    if not review:
        record=ROOT/'delivery-validation.json'
        full=json.loads(record.read_text())
        spec=json.loads((ROOT/'animation-spec.json').read_text())
        assert full['passed'] and full['render_method']==spec['render_method']
        assert record.stat().st_mtime>=max((ROOT/name).stat().st_mtime for name in ['Highland-repipe-90s-4K.mp4','Highland-repipe-90s-1080p.mp4','animation-spec.json'])
    files={}
    def add(path,relative):
        assert path.is_file(),path
        files[str(relative)]=path
    animation=Path('projects/highland/products/installation/animation-90s')
    for name in ['prepare_animation.py','animate_highland.py','compose_film.py','make_audio.py','finalize_blender.py','deliver_animation.py','verify_presentation.py','package_rebuild.py',
                 'Highland-repipe-90s.blend','animation-spec.json','callouts-2d.json','Highland-repipe-90s.srt','editorial.ass','editorial-events.json','opening-source.png','opening-source.json',
                 'blender-validation.json','presentation-validation.json','pipeline-smoke-validation.json','REBUILD-NOTES.md',
                 'audio/narration.wav','audio/original-score.wav','audio/mix.wav','audio/timing.json','audio/ui-cues.json','audio/CREDITS.txt','audio/ljspeech-MODEL_CARD']:
        p=ROOT/name
        if p.exists():add(p,animation/name)
    for p in (ROOT/'storyboard-preview').glob('*.png'):add(p,animation/'storyboard-preview'/p.name)
    for name in ['storyboard-preview-contact.png','editable-master-check.png','editable-exterior-check.png','validator-source-hashes.json']:
        p=ROOT/name
        if p.exists():add(p,animation/name)
    if not review:
        for name in ['delivery-validation.json','Highland-repipe-storyboard.pdf']:add(ROOT/name,animation/name)
    studio=PROJECT/'studio-upgrade'
    for p in studio.iterdir():
        if p.is_file() and p.suffix in {'.py','.json','.md','.txt'}:add(p,p.relative_to(REPO))
    for p in (studio/'assets').iterdir():
        if p.is_file():add(p,p.relative_to(REPO))
    installation=PROJECT/'installation'
    for name in ['Highland-installation-unit-B.blend','Highland-installation-shared.blend','highland-installation-proposed.yaml','installation-data.json','highland-installation-existing-reference.yaml',
                 'unit-b-plan.png','unit-b-service.png','risers-200dpi.png','installation-elements.csv']:
        add(installation/name,(installation/name).relative_to(REPO))
    for name in ['Highland-original.pdf','source-manifest.json']:
        add(PROJECT/name,(PROJECT/name).relative_to(REPO))
    for name in ['projects/highland/deliverables/exterior/Highland-exterior.blend','projects/highland/products/exterior/exterior.spec.json','projects/highland/products/exterior/photo-manifest.json','projects/highland/products/exterior/README.md']:
        add(REPO/name,Path(name))
    scope={'review_only':review,'new_full_movie_export_included':False,'full_delivery_validated':not review,
           'description':'Editable rig, corrected scripts and eight-still review. Full movies remain separate downloads.' if review else 'Validated integrated rebuild; movies remain separate downloads.'}
    manifest={name:{'bytes':p.stat().st_size,'sha256':digest(p)} for name,p in sorted(files.items())}
    target=destination/('Highland-corrected-rebuild-review.zip' if review else 'Highland-corrected-rebuild.zip')
    temporary=target.with_suffix('.encoding.zip')
    prefix='Highland-corrected-rebuild/'
    with zipfile.ZipFile(temporary,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        z.writestr(prefix+'README.txt','Open projects/highland/products/installation/animation-90s/Highland-repipe-90s.blend on MASTER - 90 seconds. Read REBUILD-NOTES.md beside it. Preserve this entire directory tree. This package does not include a new full-length film.\n' if review else 'Open projects/highland/products/installation/animation-90s/Highland-repipe-90s.blend. Keep the full directory tree and read REBUILD-NOTES.md. Movies are separate downloads.\n')
        z.writestr(prefix+'package-scope.json',json.dumps(scope,indent=2))
        z.writestr(prefix+'file-manifest.json',json.dumps(manifest,indent=2))
        for name,p in sorted(files.items()):z.write(p,prefix+name)
    with zipfile.ZipFile(temporary) as z:assert z.testzip() is None
    temporary.replace(target)
    (destination/'package-validation.json').write_text(json.dumps({'passed':True,'scope':scope,'archive':target.name,'archive_sha256':digest(target),'members':len(files)+3,'crc_passed':True},indent=2)+'\n')
    print('REBUILD_PACKAGE_COMPLETE',target,flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--destination',type=Path,required=True)
    p.add_argument('--review',action='store_true')
    args=p.parse_args();package(args.destination.resolve(),args.review)
