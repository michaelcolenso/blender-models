"""Package the rebuilt revision 06 model as the exterior-reconciliation deliverable.

    python package.py [--from DIR]

DIR (default $BM_BUILD) holds the build/validate outputs. Use the CI artifact of the
`build-models` run when publishing, so the .blend/.glb/.csv recorded here are the files
CI rebuilt and verified (`gh run download <run> -n models-<sha>`).

Writes, under deliverables/exterior-reconciliation/:
- previews/: JPEG stills and the 12 geometry review views, from render.py's PNGs (each < 1 MB);
- delivery-validation.json and render-records.json (small, tracked);
and products/exterior-reconciliation/release-assets.json, recording the large files by
size and sha256 for `bm assets` (published to the existing release by the owner).
"""
import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / 'builder'))
import paths  # noqa: E402

DELIVER = HERE.parent.parent / 'deliverables/exterior-reconciliation'
TAG = 'highland-exterior-reconciliation-2026-11-05'
REPO = 'michaelcolenso/blender-models'
ARCHIVE_COMMIT = 'bddd5b8fb4085677028108754ef82a722bc0b17c'
# Archived revision 06 review report, byte-identical to the archive blob. Describes the same
# geometry (architecture inventory 69e546b6…); published unchanged, not regenerated.
HISTORICAL_REPORT = {'name': 'Highland-drawing-reconciliation-rev06-review.pdf',
                     'source_path': 'deliverables/highland-drawings/Highland-drawing-reconciliation.pdf',
                     'git_blob_sha': '5748aef2e98354c6eff57e1c17cb7f4078f5bcf3'}
STILLS = {'Highland-daylight-drawing-reconciled.png': 'native-render.json',
          'Highland-dusk-drawing-reconciled.png': 'dusk-render.json'}
NOTICE = 'Illustrative, not a contract document.'
REVIEW_VIEWS = ('north', 'south', 'plan', 'iso', 'p1-plan', 'p1-south', 'r5-return', 'west', 'east',
                'r5-plan', 'r5-southwest', 'terrace-plan')  # render.py --review, all views


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def jpeg(source, target, max_bytes=950_000):
    image = Image.open(source).convert('RGB')
    for quality in (92, 88, 84, 80, 75):
        image.save(target, 'JPEG', quality=quality, optimize=True, progressive=True)
        if target.stat().st_size <= max_bytes:
            return quality
    raise SystemExit(f'{target.name} stays over {max_bytes} bytes')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--from', dest='source', type=Path, default=paths.OUT,
                        help='directory with build/validate outputs (default: $BM_BUILD)')
    parser.add_argument('--renders', type=Path, default=paths.OUT,
                        help='directory with render.py outputs (default: $BM_BUILD)')
    parser.add_argument('--report', type=Path, help='local copy of the archived review PDF, to record it')
    args = parser.parse_args()
    src, renders = args.source, args.renders

    native, glb = src / paths.NATIVE.name, src / paths.GLB.name
    delivery = json.loads((src / 'delivery-validation.json').read_text())
    geometry = json.loads((src / 'geometry-validation.json').read_text())
    check = json.loads((DELIVER / 'native-check.json').read_text())
    assert delivery['status'] == 'PASS' and check['status'] == 'PASS'
    assert delivery['native_sha256'] == sha(native) == geometry['native_sha256'], 'validation is not for this .blend'
    assert delivery['glb_sha256'] == sha(glb), 'validation is not for this .glb'
    inventory = hashlib.sha256(json.dumps(geometry['after'], sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    assert inventory == check['architecture_inventory_sha256'], 'model is not the verified revision 06 geometry'

    # Renders may come from another build of the same geometry: tie them by architecture inventory.
    records = {}
    for name in ('native-render.json', 'dusk-render.json', 'review-render.json'):
        record = json.loads((renders / name).read_text())
        assert record['architecture_inventory_sha256'] == inventory, f'{name} rendered other geometry'
        for image, digest in record['images'].items():
            assert sha(renders / image) == digest, f'{image} changed after rendering'
        record.pop('native_sha256')  # that build's .blend file hash; the geometry is pinned above
        records[name] = record

    previews = DELIVER / 'previews'
    previews.mkdir(parents=True, exist_ok=True)
    made = {}
    for png in STILLS:
        made[png] = jpeg(renders / png, previews / png.replace('.png', '.jpg'))
    # Exactly the hash-checked images of the review record, and all 12 views: a partial
    # `render.py --review --views` run or stale PNGs in the folder must not be published.
    review = sorted(records['review-render.json']['images'])
    expected = sorted(f'geometry-review/{view}.png' for view in REVIEW_VIEWS)
    assert review == expected, f'review record must cover exactly the 12 views; has {review}'
    for image in review:
        png = renders / image
        made[image] = jpeg(png, previews / f'review-{png.stem}.jpg')
    stale = {p.name for p in previews.glob('review-*.jpg')} - {f'review-{Path(i).stem}.jpg' for i in review}
    assert not stale, f'unexpected previews: {sorted(stale)}'

    (DELIVER / 'delivery-validation.json').write_text(json.dumps(delivery, indent=2) + '\n')
    (DELIVER / 'render-records.json').write_text(json.dumps({
        'architecture_inventory_sha256': inventory,
        'note': 'CPU Cycles renders of the verified revision 06 geometry; previews are JPEG copies of these PNGs.',
        'renders': records, 'preview_jpeg_quality': made, 'notice': NOTICE}, indent=2) + '\n')

    assets = [{'name': p.name, 'bytes': p.stat().st_size, 'sha256': sha(p)}
              for p in (native, glb, src / 'element-provenance.csv')]
    manifest_path = HERE / 'release-assets.json'
    old = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    report = next((a for a in old.get('assets', []) if a['name'] == HISTORICAL_REPORT['name']), None)
    if args.report:
        data = args.report.read_bytes()
        blob = hashlib.sha1(f'blob {len(data)}\0'.encode() + data).hexdigest()
        assert blob == HISTORICAL_REPORT['git_blob_sha'], 'not the archived review PDF'
        report = {'name': HISTORICAL_REPORT['name'], 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
    assert report, 'pass --report <archived PDF> once to record it'
    manifest = {'repository': REPO, 'tag': TAG, 'storage': 'release',
                'note': (f'Revision 06 deliverables. {paths.NATIVE.name}, {paths.GLB.name} and element-provenance.csv '
                         'are the files the CI product check rebuilt and validated (see '
                         '../../deliverables/exterior-reconciliation/delivery-validation.json). '
                         f'{HISTORICAL_REPORT["name"]} is byte-identical to archive blob {HISTORICAL_REPORT["git_blob_sha"]} '
                         f'({HISTORICAL_REPORT["source_path"]} at {ARCHIVE_COMMIT}). {NOTICE}'),
                'assets': assets + [report]}
    manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')
    print(f'PACKAGED {len(made)} previews; release manifest: {len(manifest["assets"])} assets')
    for a in manifest['assets']:
        print(f"  {a['bytes']:>10}  {a['sha256'][:12]}  {a['name']}")


if __name__ == '__main__':
    os.environ.setdefault('BM_BUILD', str(paths.OUT))
    main()
