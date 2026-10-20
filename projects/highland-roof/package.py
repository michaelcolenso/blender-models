"""Package exact reviewed outputs with the native base and reproduction sources."""
import hashlib
import json
import zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
OUT=ROOT/'deliverables/highland-roof'


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    check=json.loads((OUT/'delivery-validation.json').read_text())
    media=json.loads((OUT/'media-validation.json').read_text())
    review=json.loads((OUT/'visual-review.json').read_text())
    assert review['final_still_reviewed'] and review['all_comparison_pages_reviewed'] and review['decoded_movie_frames_reviewed']
    for name,key in [('Highland-daylight-geometry-revised.png','still_sha256'),('Highland-roof-and-terrace-revised.blend','native_sha256'),('Highland-geometry-revised.glb','glb_sha256')]:
        assert check[key]==sha(OUT/name)
    assert review['still_sha256']==check['still_sha256']
    assert review['movie_sha256']==media['movie_sha256']==sha(OUT/'Highland-dusk-geometry-revised-18s.mp4')
    assert review['pdf_sha256']==sha(OUT/'Highland-roof-terrace-source-comparison.pdf')
    outputs=sorted(p for p in OUT.rglob('*') if p.is_file() and p.suffix not in ('.zip','.blend1') and p.name not in ('.gitignore','source-manifest.json','package-validation.json','Highland-daylight-geometry-preview.png','preview-render.json'))
    sources=sorted(p for p in HERE.iterdir() if p.is_file() and p.name!='.gitignore')
    for rel in ['deliverables/highland-daylight/Highland-daylight-photo-study.blend','deliverables/highland-daylight/camera-fit.json','projects/highland-daylight/fit_camera.py','projects/highland-daylight/photo-landmarks.json','projects/highland-refined/exterior-revised.spec.json','projects/highland-refined/HANDOFF.md','projects/highland-cinematic/assets/source.json','projects/highland-cinematic/assets/kloofendal_48d_partly_cloudy_puresky_4k.hdr']:
        sources.append(ROOT/rel)
    sources+=sorted((ROOT/'projects/highland-exterior/source-review').glob('*.png'))
    sources+=sorted((ROOT/'projects/highland-exterior/source-review').glob('user-photo-*.jpg'))
    manifest={'outputs':{str(p.relative_to(OUT)):{'bytes':p.stat().st_size,'sha256':sha(p)} for p in outputs},
              'reproduction_inputs':{str(p.relative_to(ROOT)):{'bytes':p.stat().st_size,'sha256':sha(p)} for p in sources}}
    (OUT/'source-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    archive=OUT/'Highland-roof-editable.zip'
    with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in outputs+[OUT/'source-manifest.json']:z.write(p,str(p.relative_to(OUT)))
        for p in sources:z.write(p,'reproduction/'+str(p.relative_to(ROOT)))
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        count=len(z.infolist())
    result={'file':archive.name,'bytes':archive.stat().st_size,'sha256':sha(archive),'files':count,'crc_check_passed':True,
            'visual_review_bound_to_exact_still_pdf_and_movie':True}
    (OUT/'package-validation.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))


if __name__=='__main__':
    main()
