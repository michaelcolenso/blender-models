"""Additional presentation QA; the two original gate scripts are unchanged.

Run finalize_blender.py first. This checks its result, tracked anchors, actual
camera continuity, recursive VSE channels and the proposed-status presentation.
It does not substitute for deliver_animation.py after a complete film rebuild.
"""
import hashlib
import json
import math
from pathlib import Path

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

ROOT=Path(__file__).resolve().parent
EXPECTED={
    'finalize_blender.py':'391df0eede54c97635ad07873f0bc88573fbb5dd660f30e130ca0fdc12a55778',
    'deliver_animation.py':'7ec90be7b854b78c28dd936e5e957a604455855f863b7213b141dabb9c5591eb',
}
checks=[]
def check(name,condition):
    checks.append({'check':name,'passed':bool(condition)})
    assert condition,name
def state(scene,t):
    bpy.context.window.scene=scene
    scene.frame_set(round(t*24)+1)
    bpy.context.view_layer.update()

for name,digest in EXPECTED.items():
    check(name+' byte-for-byte unchanged',hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest)
result=json.loads((ROOT/'blender-validation.json').read_text())
check('94 original unit objects compared',result['source_geometry']['unit']=={'compared':94,'unchanged':True})
check('45 original shared objects compared',result['source_geometry']['shared']=={'compared':45,'unchanged':True})
check('All original staging assertions passed',all(result['staging'].values()))
check('Eight original VSE strip-bound checks passed',len(result['movie_timeline'])==8)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Highland-repipe-90s.blend'))
master=bpy.data.scenes['MASTER - 90 seconds']
def all_strips(strips):
    for strip in strips:
        yield strip
        if strip.type=='META':yield from all_strips(strip.strips)
strips=list(all_strips(master.sequence_editor.strips))
check('All root and nested VSE channels below 128',max(s.channel for s in strips)<128)
check('Native tracked-label group retained by finalizer',any(s.name=='Camera-tracked callouts' and s.type=='META' for s in strips))
tracked=next(s for s in strips if s.name=='Camera-tracked callouts')
check('Callouts start at 4.5s without an exterior prehold',tracked.frame_final_start==109 and tracked.frame_final_end==2161 and tracked.frame_offset_start==0)
check('Editable exterior/shared dissolve retained',any(s.name=='Exterior to shared system' and s.type=='META' for s in strips))
unit=bpy.data.scenes['3D - Unit B installation']
for t in [18,22,26,29,30,45,47,54,58,61,68,73]:
    state(unit,t-1/24);point=unit.camera.location.copy();scale=unit.camera.data.ortho_scale
    state(unit,t+1/24)
    check(f'Continuous camera at {t}s',(unit.camera.location-point).length<.35 and abs(unit.camera.data.ortho_scale-scale)<.35)
state(unit,42.5)
visible=[]
for name in ['CW-01','CW-02','CW-03','HW-01','HW-02','HW-03','HWC-01']:
    obj=unit.objects[name]
    for point in obj.data.splines[0].points:
        uv=world_to_camera_view(unit,unit.camera,obj.matrix_world@Vector(point.co[:3]))
        visible.append(uv.z>0 and .015<uv.x<.985 and .015<uv.y<.985)
check('Wide view retains all main distribution control points',all(visible))
data=json.loads((ROOT/'callouts-2d.json').read_text())
check('Per-frame projection format',data['version']==2 and data['fps']==24 and data['size']==[3840,2160])
check('Kitchen callout uses source CW-04, not wet-wall A03',any(t['object']=='CW-04' and t['point']=='last' for t in data['tracks'] if 'Kitchen' in t['label']))
check('No invented rated-restoration label',all('rated' not in t['label'].lower() for t in data['tracks']))
worst=0
for track in data['tracks']:
    scene=bpy.data.scenes['3D - Unit B installation' if track['scene']=='unit' else '3D - Shared distribution']
    obj=scene.objects[track['object']]
    samples=track['samples']
    check('Visible projection samples '+track['id'],bool(samples))
    for sample in samples:
        state(scene,sample['t'])
        if track.get('point') in {'first','last'}:
            point=obj.matrix_world@Vector(obj.data.splines[0].points[0 if track['point']=='first' else -1].co[:3])
        elif obj.type=='CURVE':
            points=[obj.matrix_world@Vector(p.co[:3]) for sp in obj.data.splines for p in sp.points]
            point=sum(points,Vector())/len(points)
        else:point=obj.matrix_world.translation
        uv=world_to_camera_view(scene,scene.camera,point)
        worst=max(worst,math.hypot(sample['x']-(32+uv.x*2816),sample['y']-(272+(1-uv.y)*1584)))
check('All callout anchors match actual camera within 0.01 pixels',worst<.01)
check('Pipe material uses coated Principled, not emission-only',all(any(n.type=='BSDF_PRINCIPLED' and abs(n.inputs['Coat Weight'].default_value-.5)<1e-6 for n in unit.objects[name].data.materials[0].node_tree.nodes) for name in ['CW-01','HW-01','HWC-01']))
ext=bpy.data.scenes['STUDIO - Exterior opening']
check('Actual exterior source scene present',len(ext.objects)>1000 and ext.camera.data.type=='PERSP')
check('3D scene sizes match the unchanged VSE scaling',all((s.render.resolution_x,s.render.resolution_y)==(1600,900) for s in [unit,ext,bpy.data.scenes['3D - Shared distribution']]))
report={'passed':True,'checks':checks,'count':len(checks),'max_vse_channel':max(s.channel for s in strips),'maximum_anchor_error_pixels':worst,
        'scope':'Source geometry, staging, native editable timeline and presentation QA. Full-movie export checks require a complete rebuild.'}
(ROOT/'presentation-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print('PRESENTATION_VALIDATION_PASS',len(checks),'checks; max VSE channel',report['max_vse_channel'])
