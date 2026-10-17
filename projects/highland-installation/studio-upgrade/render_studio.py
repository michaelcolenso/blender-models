"""Render review frames or a resumable native sequence from the studio variant."""
import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

ROOT = Path(__file__).resolve().parent
C = json.loads((ROOT / 'studio-config.json').read_text())
OUT = ROOT / 'output'
SHOTS = [
    {'id': '01-exterior', 'start': 0, 'end': 4.5, 'scene': 'STUDIO - Exterior opening'},
    {'id': '01-shared', 'start': 3.5, 'end': 8, 'scene': '3D - Shared distribution'},
    *[{'id': f"{s['id']:02}-unit" if s['scene']=='unit' else '08-shared', 'start': s['start'], 'end': s['end'], 'scene': '3D - Unit B installation' if s['scene']=='unit' else '3D - Shared distribution'}
      for s in json.loads((ROOT.parent / 'animation-90s/animation-spec.json').read_text())['shots'][1:]],
]


def pins(scene,t):
    anchors=[]
    if scene.name=='3D - Shared distribution':
        for group in ["'01","'03","'02","'04","'05"]:
            obj=scene.objects['STACK-'+group+'-CW']
            pos=obj.matrix_world@Vector(obj.data.splines[0].points[-1].co[:3])
            anchors.append(('Riser '+group,pos,False))
        if 3.5<=t<8:
            obj=scene.objects['SH-IRR-CW']
            pos=obj.matrix_world@Vector(obj.data.splines[0].points[-1].co[:3])
            anchors.append(('Unit 101 irrigation · verify route',pos,True))
    elif scene.name=='3D - Unit B installation':
        if 8<=t<18 or 52<=t<67:
            message='Service assembly · field verify' if t<58 else 'Proposed isolation · verify on site'
            anchors.append((message,scene.objects['SVC-CW'].location.copy(),t>=58))
        elif 18<=t<29:
            obj=scene.objects['CW-04']
            pos=obj.matrix_world@Vector(obj.data.splines[0].points[-1].co[:3])
            anchors.append(('Kitchen · low-wall connection',pos,False))
        elif 67<=t<73:
            obj=scene.objects['HWC-01']
            pos=obj.matrix_world@Vector(obj.data.splines[0].points[0].co[:3])
            anchors.append(('Hot + return circulation · schematic',pos,False))
        elif 73<=t<85:
            obj=scene.objects['A04-RESTORE']
            pos=obj.matrix_world@Vector(obj.data.splines[0].points[0].co[:3])
            anchors.append(('Restore · retain service access',pos,False))
    result=[]
    for text,point,warning in anchors:
        uv=world_to_camera_view(scene,scene.camera,point)
        if uv.z>0 and 0<=uv.x<=1 and 0<=uv.y<=1:
            result.append({'text':text,'u':uv.x,'v':1-uv.y,'warning':warning})
    return result


def blueprint_projection(scene):
    obj=next((o for o in scene.objects if o.name.startswith('P4.01 Unit B')),None)
    if not obj:return None
    corners={}
    uv_layer=obj.data.uv_layers.active
    for loop in obj.data.loops:
        uv=uv_layer.data[loop.index].uv
        point=obj.matrix_world@obj.data.vertices[loop.vertex_index].co
        projected=world_to_camera_view(scene,scene.camera,point)
        corners[(round(uv.x),round(uv.y))]=[projected.x,1-projected.y]
    return [corners[key] for key in [(0,1),(1,1),(1,0),(0,0)]]


def ghost_projection(scene):
    result=[]
    for obj in scene.objects:
        role=obj.get('presentation_role')
        if role not in {'ghost_wall','access_envelope'} or obj.type!='MESH':continue
        # Visibility tracks still govern the composited illustrative surfaces.
        if obj.hide_viewport:continue
        for poly in obj.data.polygons:
            points=[]
            for i in poly.vertices:
                uv=world_to_camera_view(scene,scene.camera,obj.matrix_world@obj.data.vertices[i].co)
                points.append([uv.x,1-uv.y])
            result.append({'points':points,'role':role})
    return result


def main():
    argv = sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else sys.argv[1:]
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--sequence', action='store_true')
    p.add_argument('--samples', type=int, default=C['render']['samples'])
    p.add_argument('--width', type=int, default=C['render']['width'])
    p.add_argument('--native-fps', type=int, default=C['render']['native_fps'])
    p.add_argument('--shot', help='Optional one-shot ID, e.g. 06-unit')
    p.add_argument('--preview',action='store_true',help='Denoised review with unused auxiliary passes disabled; contact AO shader remains active')
    p.add_argument('--device',choices=['CPU','GPU'],default='CPU')
    args = p.parse_args(argv)
    if args.native_fps<1 or 24%args.native_fps:
        raise ValueError('Native FPS must be a positive divisor of 24.')
    bpy.ops.wm.open_mainfile(filepath=str(OUT/'Highland-studio-upgrade.blend'))
    profile={'samples':args.samples,'width':args.width,'height':round(args.width*9/16),'native_fps':args.native_fps,'preview':args.preview,'device':args.device,'source_blend_sha256':hashlib.sha256((OUT/'Highland-studio-upgrade.blend').read_bytes()).hexdigest()}
    (OUT/('sequence-profile.json' if args.sequence else 'review-profile.json')).write_text(json.dumps(profile,indent=2)+'\n')
    report = []
    if args.sequence:
        jobs = [(s, [(n, s['start']+n/args.native_fps) for n in range(round((s['end']-s['start'])*args.native_fps))]) for s in SHOTS if not args.shot or s['id']==args.shot]
    else:
        stills = [('01-exterior', 1.5), ('03-unit', 23.5), ('04-unit', 42.5), ('06-unit', 60), ('06-unit', 69), ('07-unit', 80)]
        jobs = [(next(s for s in SHOTS if s['id']==shot), [(round(t*24), t)]) for shot,t in stills]
    for shot, times in jobs:
        scene = bpy.data.scenes[shot['scene']]
        bpy.context.window.scene = scene
        scene.cycles.samples = args.samples
        scene.cycles.device = args.device
        if args.preview:
            scene.cycles.use_denoising=True
            for layer in scene.view_layers:
                layer.use_pass_ambient_occlusion=False
                layer.use_pass_shadow=False
                layer.cycles.use_pass_shadow_catcher=False
            # Deterministic display-space blueprint and context fills avoid
            # Monte Carlo alpha noise. Geometry, edges and shadows remain 3D.
            for obj in scene.objects:
                if obj.name.startswith('P4.01 Unit B') or (obj.type=='MESH' and obj.get('presentation_role') in {'ghost_wall','access_envelope'}):
                    obj.driver_add('hide_render').driver.expression='True'
        scene.render.resolution_x = args.width
        scene.render.resolution_y = round(args.width*9/16)
        folder = OUT / ('raw/'+shot['id'] if args.sequence else 'review-raw')
        folder.mkdir(parents=True, exist_ok=True)
        signature=folder/'render-profile.json'
        if signature.exists() and json.loads(signature.read_text())!=profile:
            raise RuntimeError(f'Render profile changed; move or remove the old generated cache first: {folder}')
        signature.write_text(json.dumps(profile,indent=2)+'\n')
        begin = time.time()
        for n,t in times:
            target = folder/(f'{n:04}.png' if args.sequence else f'{shot["id"]}-{t:04.1f}s.png')
            if target.exists() and target.stat().st_size>10000:
                continue
            scene.frame_set(round(t*24)+1)
            bpy.context.view_layer.update()
            scene.render.filepath = str(target)
            bpy.ops.render.render(write_still=True)
            target.with_suffix('.json').write_text(json.dumps({'t':t,'preview':args.preview,'pins':pins(scene,t),'blueprint_corners':blueprint_projection(scene) if args.preview else None,'context_faces':ghost_projection(scene) if args.preview else []}))
            print('STUDIO_FRAME',shot['id'],n,'time',round(t,3),'elapsed',round(time.time()-begin,1),flush=True)
        report.append({'shot':shot['id'],'frames':len(times),'elapsed_s':round(time.time()-begin,2)})
    (OUT/('sequence-render.json' if args.sequence else 'review-render.json')).write_text(json.dumps(report,indent=2)+'\n')


if __name__ == '__main__':
    main()
