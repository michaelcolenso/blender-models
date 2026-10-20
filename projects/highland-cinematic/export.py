"""Read back the packed deliverable and export a portable geometry companion."""
import json
from pathlib import Path

import bpy

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'deliverables/highland-cinematic'
bpy.context.preferences.filepaths.use_scripts_auto_execute=False
bpy.ops.wm.open_mainfile(filepath=str(OUT/'Highland-dusk.blend'),load_ui=False,use_scripts=False)
s=bpy.context.scene
assert s.render.resolution_x==3840 and s.render.resolution_y==2560
assert s.render.engine=='CYCLES'
images=[im for im in bpy.data.images if im.source=='FILE']
assert images and all(im.packed_file for im in images)
assert s.get('source_architecture_sha256')==json.loads((OUT/'scene-validation.json').read_text())['base_architecture_sha256']
materials={p.material_index for p in bpy.data.objects['continuous-site-context'].data.polygons}
assert materials=={0,1,2},materials
bpy.ops.object.select_all(action='DESELECT')
meshes=[o for o in s.objects if o.type=='MESH']
for o in meshes:o.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(OUT/'Highland-dusk.glb'),export_format='GLB',use_selection=True,export_extras=True,export_cameras=False,export_lights=False)
report={'scene_readback':True,'render_engine':s.render.engine,'render_dimensions':[s.render.resolution_x,s.render.resolution_y],'packed_images':[{'name':im.name,'size':list(im.size)} for im in images],'external_images_required':False,'site_surface_material_slots':sorted(materials),'glb_mesh_objects_exported':len(meshes),'area_lighting_and_procedural_materials_simplified_in_glb':True}
(OUT/'scene-readback.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
