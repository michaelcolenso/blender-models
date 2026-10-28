"""Meaningful source, staging, direction, framing and delivery checks."""
import hashlib
import json
import math
import sys
from pathlib import Path

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector
import studio_upgrade as studio

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'output'
CHECKS=[]


def check(name,condition):
    CHECKS.append({'check':name,'passed':bool(condition)})
    if not condition:raise AssertionError(name)


def state(scene,t):
    bpy.context.window.scene=scene
    scene.frame_set(round(t*24)+1)
    bpy.context.view_layer.update()


def main():
    source=ROOT.parent/'animation-90s/Highland-repipe-90s.blend'
    bpy.ops.wm.open_mainfile(filepath=str(source))
    original={name:{o.name:studio.geometry_digest(o) for o in bpy.data.scenes[name].objects if o.get('element_id') and o.type in {'CURVE','MESH'}} for name in ['3D - Unit B installation','3D - Shared distribution']}
    bpy.ops.wm.open_mainfile(filepath=str(OUT/'Highland-studio-upgrade.blend'))
    check('Three explicit source-derived 3D scenes',len(bpy.data.scenes)==3)
    for name,objects in original.items():
        sc=bpy.data.scenes[name]
        check(name+' source geometry unchanged',all(studio.geometry_digest(sc.objects[n])==v for n,v in objects.items()))
    unit=bpy.data.scenes['3D - Unit B installation']
    shared=bpy.data.scenes['3D - Shared distribution']
    for sc in [unit,shared]:
        check(sc.name+' Cycles, AgX, transparent',sc.render.engine=='CYCLES' and sc.view_settings.view_transform=='AgX' and sc.render.film_transparent)
        check(sc.name+' true shadow receiver',any(o.is_shadow_catcher for o in sc.objects))
        for o in sc.objects:
            if o.type=='CURVE' and o.get('system') in {'CW','HW','HWC'} and o.get('element_id'):
                bs=next(n for n in o.data.materials[0].node_tree.nodes if n.type=='BSDF_PRINCIPLED')
                check('Coated Principled '+o.name,abs(bs.inputs['Roughness'].default_value-.25)<1e-6 and abs(bs.inputs['Coat Weight'].default_value-.5)<1e-6)
    plan=next(o for o in unit.objects if o.name.startswith('P4.01 Unit B'))
    texture=next(n for n in plan.data.materials[0].node_tree.nodes if n.type=='TEX_IMAGE')
    check('Native 400 dpi Cubic source texture',texture.interpolation=='Cubic' and list(texture.image.size)==[6384,5880])
    for t,flow in [(30,0),(55,0),(60,0),(66.9,0),(67,1),(69,1)]:
        state(unit,t)
        mat=bpy.data.materials['Studio | Pulse CW-01']
        check(f'Flow gate at {t}s',mat.node_tree.nodes['Flow release gate'].outputs[0].default_value==flow)
    state(unit,55)
    check('Gauge shown at required testing hold',not unit.objects['TEST-GAUGE'].hide_render)
    state(unit,60)
    check('Proposed closing valve icons',not unit.objects['Studio proposed valve ring CW'].hide_render and unit.objects['Studio proposed valve handle CW'].rotation_euler.z>.5)
    state(unit,64)
    check('Valve-icon interval ends after depicted connection',unit.objects['Studio proposed valve ring CW'].hide_render)
    state(unit,42.5)
    visible_points=[]
    for name in ['CW-01','CW-02','CW-03','HW-01','HW-02','HW-03','HWC-01']:
        o=unit.objects[name]
        for p in o.data.splines[0].points:
            uv=world_to_camera_view(unit,unit.camera,o.matrix_world@Vector(p.co[:3]))
            visible_points.append(uv.z>0 and .015<uv.x<.985 and .015<uv.y<.985)
    check('Installation wide retains all distribution control points',all(visible_points))
    for t in [18,22,26,30,47,54,58,61,68,73]:
        state(unit,t-1/24);a=unit.camera.location.copy();scale=unit.camera.data.ortho_scale
        state(unit,t+1/24)
        check(f'Continuous focus move at {t}s',(unit.camera.location-a).length<.35 and abs(unit.camera.data.ortho_scale-scale)<.35)
    state(unit,80)
    walls=[o for o in unit.objects if o.get('presentation_role')=='ghost_wall']
    check('Ten illustrative ghost walls',len(walls)==10 and all(not o.hide_render for o in walls))
    check('Ghost height is the specified display height',all(abs(max(v.co.z for v in o.data.vertices)-1.0668)<1e-4 for o in walls))
    check('Access envelopes restored after transfer',unit.objects['Studio access A01'].hide_render and not unit.objects['A01-RESTORE'].hide_render)
    state(shared,88)
    for o in shared.objects:
        if o.type=='CURVE' and o.get('system')=='HWC':
            mat=bpy.data.materials['Studio | Pulse '+o.name]
            sign=mat.node_tree.nodes['Pulse spacing'].inputs[1].default_value
            check('Shared return direction '+o.name,(sign>0)==o.name.startswith('RETURN-'))
    check('Tilted source labels suppressed',all(o.hide_render for o in shared.objects if o.type=='FONT'))
    exterior=bpy.data.scenes['STUDIO - Exterior opening']
    state(exterior,0)
    check('Actual exterior model starts the film',exterior.camera.data.type=='PERSP' and len(exterior.objects)>1000)
    check('Source animation unchanged',hashlib.sha256(source.read_bytes()).hexdigest()==json.loads((OUT/'build-validation.json').read_text())['source_animation_sha256'])
    result={'passed':True,'checks':CHECKS,'count':len(CHECKS),'scope':'Presentation/source/staging checks; not field, hydraulic or code acceptance.'}
    (OUT/'studio-validation.json').write_text(json.dumps(result,indent=2)+'\n')
    print('STUDIO_VALIDATION_PASS',len(CHECKS),'checks')


if __name__=='__main__':main()
