"""Render the delivered native still and four source-provenance views."""
import argparse
import hashlib
import json
import time
from pathlib import Path

import bpy
from mathutils import Vector
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'deliverables/highland-drawings'


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--review',action='store_true');args=parser.parse_args()
    bpy.ops.wm.open_mainfile(filepath=str(OUT/'Highland-drawing-reconciled.blend'),load_ui=False,use_scripts=False)
    scene=next(s for s in bpy.data.scenes if s.name.startswith('Daylight'))
    bpy.context.window.scene=scene
    scene.render.threads_mode='FIXED';scene.render.threads=3
    started=time.monotonic()
    outputs=[]
    if not args.review:
        scene.render.filepath=str(OUT/'Highland-daylight-drawing-reconciled.png')
        bpy.ops.render.render(write_still=True,scene=scene.name)
        outputs.append(Path(scene.render.filepath))
    else:
        architecture={o for c in ('Envelope','Glazing','Balconies','Roof') for o in bpy.data.collections[c].objects}
        for o in scene.objects:
            if o.type in ('MESH','CURVE','FONT') and o not in architecture:o.hide_render=True
        scene.compositing_node_group=None
        world=bpy.data.worlds.new('Revision 05 provenance review');world.use_nodes=True
        world.node_tree.nodes.get('Background').inputs['Color'].default_value=(.6,.65,.7,1)
        world.node_tree.nodes.get('Background').inputs['Strength'].default_value=.65
        scene.world=world;scene.render.resolution_x=1200;scene.render.resolution_y=900
        scene.render.resolution_percentage=100;scene.cycles.samples=12;scene.cycles.adaptive_min_samples=4
        scene.view_settings.exposure=0
        material=bpy.data.materials.new('Review / complete components assumed');material.use_nodes=True
        material.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value=(1,.24,.035,1)
        scene.view_layers[0].material_override=material
        camera=scene.camera;camera.data.type='ORTHO';camera.data.shift_x=camera.data.shift_y=0
        folder=OUT/'geometry-review';folder.mkdir(exist_ok=True)
        for name,location,target,scale in [('north',(18.5,120,11),(18.5,22,11),47),('south',(18.5,-85,11),(18.5,22,11),47),('plan',(18.5,22,105),(18.5,22,0),68),('iso',(80,95,42),(18.5,22,10),70),('p1-plan',(18.5,22,105),(18.5,22,0),68),('p1-south',(18.5,-85,1.7),(18.5,22,1.7),43),('r5-return',(57,-19,29),(32,10,18),20)]:
            for o in architecture:
                o.hide_render=(name.startswith('p1-') and not (o.name.startswith(('wall-P1-','south-P1-','east-P1-')) or o.name=='slab-P1'))
            camera.location=location;camera.rotation_euler=(Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.ortho_scale=scale
            path=folder/(name+'.png');scene.render.filepath=str(path)
            bpy.ops.render.render(write_still=True,scene=scene.name)
            im=Image.open(path).convert('RGB');footer=Image.new('RGB',(1200,944),'white');footer.paste(im)
            ImageDraw.Draw(footer).text((15,913),f'Revision 05 / {name} | Orange: complete components assumed. Measured plan positions provisional. Not for construction.',fill='#263943',font=ImageFont.load_default(size=16))
            footer.save(path);outputs.append(path);print('REVIEW',name,flush=True)
    report={'elapsed_seconds':round(time.monotonic()-started,2),'samples':scene.cycles.samples,'images':{str(p.relative_to(OUT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in outputs}}
    (OUT/('review-render.json' if args.review else 'native-render.json')).write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report),flush=True)


if __name__=='__main__':main()
