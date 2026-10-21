"""Package exact reviewed delivery files, source PDFs and reproducible model inputs."""
import hashlib
import json
import zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
OUT=ROOT/'deliverables/highland-drawings'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    visual=json.loads((OUT/'visual-review.json').read_text())
    assert visual['status']=='reviewed'
    assert not visual.get('pending')
    for name,digest in visual['reviewed_files'].items():assert sha(OUT/name)==digest,name
    validate=json.loads((OUT/'delivery-validation.json').read_text())
    assert validate['status']=='PASS'
    assert validate['native_sha256']==sha(OUT/'Highland-drawing-reconciled.blend')
    assert validate['glb_sha256']==sha(OUT/'Highland-drawing-reconciled.glb')
    assert visual['native_sha256']==validate['native_sha256']
    assert sha(OUT/'reconciled.spec.json')==sha(HERE/'reconciled.spec.json')
    records=[]
    def include(path,name):records.append((path,name))
    for path in sorted(OUT.rglob('*')):
        if path.is_file() and path.name not in ('.gitignore','Highland-drawing-editable.zip','package-validation.json','source-manifest.json'):
            include(path,'delivery/'+str(path.relative_to(OUT)))
    for path in sorted(HERE.rglob('*')):
        if path.is_file() and '__pycache__' not in path.parts:
            include(path,'reproduction/'+str(path.relative_to(ROOT)))
    for name in ('deliverables/highland-roof/Highland-roof-and-terrace-revised.blend',
                 'projects/highland-roof/geometry-revision.spec.json','projects/highland-roof/geometry.json','projects/highland-exterior/build.py',
                 'deliverables/highland-roof/opening-audit.json'):
        include(ROOT/name,'reproduction/'+name)
    manifest={'files':[{'path':name,'bytes':path.stat().st_size,'sha256':sha(path)} for path,name in records]}
    (OUT/'source-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    archive=OUT/'Highland-drawing-editable.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for path,name in records:z.write(path,name)
        z.write(OUT/'source-manifest.json','source-manifest.json')
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        for item in manifest['files']:
            assert hashlib.sha256(z.read(item['path'])).hexdigest()==item['sha256']
        count=len(z.namelist())
    report={'status':'PASS','archive':archive.name,'files':count,'bytes':archive.stat().st_size,
            'sha256':sha(archive),'crc_check':'PASS','manifest_exact_file_hashes':'PASS',
            'visual_review_sha256':sha(OUT/'visual-review.json')}
    (OUT/'package-validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2),flush=True)


if __name__=='__main__':main()
