"""Package the finished, validated files with a minimal reproduction record."""
import hashlib
import json
import struct
import zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
OUT=ROOT/'deliverables/highland-cinematic'
readback=json.loads((OUT/'scene-readback.json').read_text())
assert readback['scene_readback'] and not readback['external_images_required']
data=(OUT/'Highland-dusk.glb').read_bytes()
magic,version,size=struct.unpack('<4sII',data[:12])
assert magic==b'glTF' and version==2 and size==len(data)
length,kind=struct.unpack('<II',data[12:20]);assert kind==0x4e4f534a
glb=json.loads(data[20:20+length])
assert len(glb['nodes'])>1100 and len(glb['meshes'])>1000
manifest=json.loads((OUT/'delivery-validation.json').read_text())
assert manifest.get('visual_review_completed') is True, 'Complete visual review before packaging'
manifest.update(scene_readback=readback,glb_nodes=len(glb['nodes']),glb_meshes=len(glb['meshes']))
manifest['files']['Highland-dusk.glb']={'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
(OUT/'delivery-validation.json').write_text(json.dumps(manifest,indent=2)+'\n')
source_records={'architectural_pdf_sha256_recorded_by_original_study':json.loads((ROOT/'projects/highland-exterior/exterior.spec.json').read_text())['source_pdf_sha256'],'sources':[]}
for relative in ['deliverables/highland-exterior/Highland-exterior.blend','projects/highland-exterior/exterior.spec.json','projects/highland-exterior/source-review/user-photo-01.jpg','projects/highland-exterior/source-review/user-photo-02.jpg','projects/highland-cinematic/assets/kloofendal_48d_partly_cloudy_puresky_4k.hdr','projects/highland-drone/flight.spec.json']:
    path=ROOT/relative
    source_records['sources'].append({'path':relative,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
(OUT/'source-records.json').write_text(json.dumps(source_records,indent=2)+'\n')
with zipfile.ZipFile(OUT/'Highland-dusk-editable.zip','w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for filename in ['Highland-dusk-4K.png','Highland-dusk.blend','Highland-dusk.glb','README.md','scene-validation.json','scene-readback.json','delivery-validation.json','source-records.json','final-render.json']:
        z.write(OUT/filename,filename)
    reproduction=[]
    reproduction.extend(HERE/filename for filename in ['scene.json','README.md','build.py','export.py','package.py','validate_delivery.py'])
    reproduction.extend((HERE/'assets').iterdir())
    reproduction.extend(ROOT/relative for relative in ['deliverables/highland-exterior/Highland-exterior.blend','projects/highland-exterior/exterior.spec.json','projects/highland-exterior/README.md','projects/highland-exterior/report.md','projects/highland-drone/flight.spec.json','projects/highland-drone/osm-buildings-source.json'])
    reproduction.extend((ROOT/'projects/highland-exterior/source-review').iterdir())
    for path in reproduction:
        if path.is_file():z.write(path,'reproduction/'+str(path.relative_to(ROOT)))
    z.write(ROOT/'deliverables/highland-exterior/Highland-exterior-review.pdf','reference/Exterior-elevation-review.pdf')
    z.writestr('REPRODUCE.md','# Rebuild or render\n\nOpen Highland-dusk.blend in Blender 5.0.1 or newer to edit or render the packed scene.\n\nFor a complete scripted rebuild, use Python with bpy==5.0.1 installed, change into reproduction/, and run:\n\n```bash\npython projects/highland-cinematic/build.py\n```\n\nAll runtime source models, specifications, photographic/drawing crops and the CC0 sky asset needed by that builder are included. The original architectural PDF is not included or required by this presentation builder. Pillow is needed only for validate_delivery.py.\n')
print('Packaged',OUT/'Highland-dusk-editable.zip')
