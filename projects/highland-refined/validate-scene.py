"""Read the saved native deliverable and verify its portable source controls."""
import hashlib
import json
import csv
from pathlib import Path

import bpy

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'deliverables/highland-refined'
path=OUT/'Highland-revised-daylight-and-film.blend'
bpy.context.preferences.filepaths.use_scripts_auto_execute=False
bpy.ops.wm.open_mainfile(filepath=str(path),load_ui=False,use_scripts=False)
night=bpy.data.scenes['Dusk exterior film']
day=bpy.data.scenes['Daylight reference comparison']
assert len(bpy.data.scenes)==2
assert night.camera!=day.camera and night.world!=day.world
assert night.compositing_node_group!=day.compositing_node_group
assert (night.frame_start,night.frame_end,night.render.fps)==(1,432,24)
assert (night.render.resolution_x,night.render.resolution_y)==(1920,1080)
assert (day.render.resolution_x,day.render.resolution_y)==(1920,1280)
assert day.cycles.samples==48
digest=hashlib.sha256();count=0;untagged=[]
for name in ('Envelope','Glazing','Balconies','Roof'):
    for o in sorted(bpy.data.collections[name].objects,key=lambda o:o.name):
        if o.type!='MESH':continue
        if not all(o.get(k) for k in ('source','status','basis')):untagged.append(o.name)
        record=[o.name,[list(row) for row in o.matrix_world],[list(v.co) for v in o.data.vertices],[list(p.vertices) for p in o.data.polygons]]
        digest.update(json.dumps(record,separators=(',',':')).encode());count+=1
expected=json.loads((ROOT/'build/highland-refined/presentation/scene-validation.json').read_text())
assert digest.hexdigest()==expected['base_architecture_sha256']
assert count==expected['protected_mesh_objects']==955 and not untagged
untagged_meshes=[o.name for o in bpy.data.objects if o.type in ('MESH','CURVE') and not all(o.get(k) for k in ('source','status','basis'))]
assert not untagged_meshes,untagged_meshes[:10]
external=[im.filepath for im in bpy.data.images if im.source=='FILE' and not im.packed_file]
assert not external,external
assert night.camera.animation_data and night.camera.data.animation_data
assert not day.camera.animation_data
assert all(n.scene==day for n in day.compositing_node_group.nodes if n.bl_idname=='CompositorNodeRLayers')
# Normalize saved output locations without changing geometry or rendering.
night.render.filepath='//native-film/frame-'
day.render.filepath='//Highland-daylight-revised.png'
bpy.context.window.scene=night
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(path))
report={'scene_readback':True,'blender':bpy.app.version_string,'scenes':[s.name for s in bpy.data.scenes],
    'protected_architectural_meshes':count,'revised_architecture_sha256':digest.hexdigest(),
    'revised_architecture_preserved':True,'untagged_architectural_meshes':untagged,
    'untagged_geometry':untagged_meshes,'external_images_required':external,
    'packed_file_images':len([im for im in bpy.data.images if im.source=='FILE' and im.packed_file]),
    'native_camera_keyframes':True,'portable_render_paths':True,
    'scope':'Readback and consistency checks; source accuracy remains limited as documented.'}
with (OUT/'element-provenance.csv').open('w',newline='') as f:
    writer=csv.writer(f);writer.writerow(['element','type','collections','status','source','basis'])
    for o in sorted(bpy.data.objects,key=lambda o:o.name):
        if o.type not in ('MESH','CURVE'):continue
        writer.writerow([o.name,o.type,'; '.join(c.name for c in o.users_collection),o.get('status',''),o.get('source',''),o.get('basis','')])
report['element_provenance_inventory']='element-provenance.csv'
(OUT/'scene-readback.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report),flush=True)
