"""Read the unchanged revision-06 native model and sample its dusk camera."""
import hashlib
import json
import math
import struct
import sys
from pathlib import Path

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
OUT=ROOT/'deliverables/highland-visualization'
sys.path.insert(0,str(ROOT/'projects/highland-drawings'))
from build import inventory


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    cfg=json.loads((HERE/'film.json').read_text());OUT.mkdir(exist_ok=True)
    native=ROOT/cfg['source_native'];glb=ROOT/cfg['source_glb']
    validation=json.loads((ROOT/cfg['source_validation']).read_text())
    assert validation['status']=='PASS'
    assert validation['native_sha256']==sha(native) and validation['glb_sha256']==sha(glb)
    geometry=json.loads((ROOT/'deliverables/highland-drawings/geometry-validation.json').read_text())
    bpy.ops.wm.open_mainfile(filepath=str(native),load_ui=False,use_scripts=False)
    assert inventory()==geometry['after']
    scene=bpy.data.scenes[cfg['scene']];bpy.context.window.scene=scene
    # Only presentation aspect is evaluated; the source native file is not saved.
    scene.render.resolution_x=cfg['width'];scene.render.resolution_y=cfg['height'];scene.render.resolution_percentage=100
    architecture=[bpy.data.objects[n] for n in geometry['after']]
    points=[o.matrix_world@Vector(v) for o in architecture for v in o.bound_box]
    lo=Vector([min(p[k] for p in points) for k in range(3)]);hi=Vector([max(p[k] for p in points) for k in range(3)])
    bounds=[Vector((x,y,z)) for x in (lo.x,hi.x) for y in (lo.y,hi.y) for z in (lo.z,hi.z)]
    camera_path=[];margin=1
    for frame in range(1,cfg['frames']+1):
        scene.frame_set(frame);bpy.context.view_layer.update()
        projected=[world_to_camera_view(scene,scene.camera,p) for p in bounds]
        margin=min(margin,min(min(p.x,p.y,1-p.x,1-p.y) for p in projected));assert margin>.015
        matrix=scene.camera.matrix_world;position=matrix.translation
        direction=matrix.to_quaternion()@Vector((0,0,-1))
        fov=math.degrees(2*math.atan(scene.camera.data.sensor_width/scene.camera.data.lens/2*cfg['height']/cfg['width']))
        camera_path.append({'frame':frame,'time':(frame-1)/cfg['fps'],'position_m':list(position),'target_m':list(position+direction*100),'vertical_fov_degrees':fov})
    assert inventory()==geometry['after']
    data=glb.read_bytes();size,kind=struct.unpack_from('<II',data,12);assert kind==0x4e4f534a
    doc=json.loads(data[20:20+size]);nodes=[n for n in doc['nodes'] if 'mesh' in n]
    assert set(geometry['after'])<={n['name'] for n in nodes}
    report={'status':'PASS','source_native':cfg['source_native'],'source_native_sha256':sha(native),
        'source_glb':cfg['source_glb'],'source_glb_sha256':sha(glb),'source_validation_sha256':sha(ROOT/cfg['source_validation']),
        'architecture_unchanged':True,'architecture_meshes':len(geometry['after']),'glb_mesh_nodes':len(nodes),
        'opening_count':validation['opening_inventory'],'camera_frames_checked':len(camera_path),'minimum_frame_margin':margin,
        'lit_window_ids':sorted(o.name.split(' / ',1)[-1] for o in scene.objects if o.type=='LIGHT' and o.name.startswith('Apartment warm light / ')),
        'source_north_status':'Deferred and unchanged','film_dimensions':[cfg['width'],cfg['height']],
        'duration_seconds':cfg['frames']/cfg['fps'],'fps':cfg['fps'],'basis':cfg['basis']}
    (OUT/'camera-path.json').write_text(json.dumps(camera_path,indent=2)+'\n')
    (OUT/'source-validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='lit_window_ids'},indent=2),flush=True)


if __name__=='__main__':main()
