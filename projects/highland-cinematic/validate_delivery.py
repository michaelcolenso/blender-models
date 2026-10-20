"""Validate the actual rendered output and record a portable delivery manifest."""
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageStat

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = ROOT / 'deliverables/highland-cinematic'
image = OUT / 'Highland-dusk-4K.png'
scene = json.loads((OUT / 'scene-validation.json').read_text())
with Image.open(image) as im:
    im.load()
    assert im.size == (3840, 2560), im.size
    assert im.mode in ('RGB', 'RGBA'), im.mode
    stats = ImageStat.Stat(im.convert('RGB'))
    assert max(stats.stddev) > 12, 'Near-uniform render'
    assert min(stats.mean) > 8, 'Render appears severely underexposed'
    pixels = {'size': list(im.size), 'mean_rgb': stats.mean, 'stddev_rgb': stats.stddev}
assert scene['architecture_unchanged']
assert scene['protected_mesh_objects'] == 1103
assert scene['source_openings'] == 165
manifest = {'image_validation': pixels, 'architecture_unchanged': True, 'geometry_scope': 'Existing exterior drawing study; dimensional limitations persist.', 'visual_review_required': True, 'files': {}}
for filename in ('Highland-dusk-4K.png', 'Highland-dusk.blend', 'scene-validation.json', 'final-render.json'):
    path = OUT / filename
    assert path.is_file() and path.stat().st_size > 0
    manifest['files'][filename] = {'bytes': path.stat().st_size, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
(OUT / 'delivery-validation.json').write_text(json.dumps(manifest, indent=2) + '\n')
print(json.dumps(manifest, indent=2))
