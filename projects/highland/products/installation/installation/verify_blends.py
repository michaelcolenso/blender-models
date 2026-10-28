"""Open the saved models, verify staged visibility and snapshot static exports."""
import json
from pathlib import Path
import bpy
from mathutils import Vector
import build_installation as model
ROOT=Path(__file__).resolve().parent
result={}
for stem in ['Highland-installation-unit-B','Highland-installation-shared']:
 bpy.ops.wm.open_mainfile(filepath=str(ROOT/(stem+'.blend')))
 sc=bpy.context.scene
 if 'unit-B' in stem:
  counts=[]
  for frame in [1,25,49,73,97,121]:
   sc.frame_set(frame);bpy.context.view_layer.update()
   counts.append(sum(o.type in {'CURVE','MESH','FONT'} and not o.hide_render for o in sc.objects))
  assert counts[0]<counts[2]<counts[3],counts
  assert len(sc.timeline_markers)==6
  assert all(i.packed_file for i in bpy.data.images if i.source=='FILE' and i.name.endswith('.png'))
  assert bpy.data.objects['CW-01'].get('system')=='CW'
  sc.frame_set(121)
  assert not bpy.data.objects['CW-01'].hide_render
  assert bpy.data.objects['TEST-GAUGE'].hide_render
  result[stem]={'stage_visible_counts':counts,'packed_source':True,'final_frame':121}
 else:
  for obj in list(sc.objects):
   if obj.get('source','').startswith('P4.01'):
    bpy.data.objects.remove(obj,do_unlink=True)
  assert len([o for o in sc.objects if o.name.startswith('STACK-')])==15
  result[stem]={'three_system_risers':15}
  sc.timeline_markers.clear();sc.frame_start=1;sc.frame_end=1;sc.frame_set(1)
  bpy.data.objects['Studio ground'].location.z=-3
  sc.camera.location=(13,-20,17);sc.camera.rotation_euler=(Vector((0,0,2))-sc.camera.location).to_track_quat('-Z','Y').to_euler();sc.camera.data.ortho_scale=22
  model.render(sc,'shared-distribution.png')
  bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/(stem+'.blend')))
 model.export(sc,ROOT/(stem+'.glb'))
(ROOT/'blender-validation.json').write_text(json.dumps(result,indent=2))
print('BLENDER_READBACK_PASS',result)
