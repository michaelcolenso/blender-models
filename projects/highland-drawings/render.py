"""Render native day/dusk stills, camera endpoints and source-provenance views."""
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
    parser=argparse.ArgumentParser();modes=parser.add_mutually_exclusive_group();modes.add_argument('--review',action='store_true');modes.add_argument('--dusk',action='store_true');modes.add_argument('--dusk-review',action='store_true');parser.add_argument('--views',default='');args=parser.parse_args()
    bpy.ops.wm.open_mainfile(filepath=str(OUT/'Highland-drawing-reconciled.blend'),load_ui=False,use_scripts=False)
    spec=json.loads((ROOT/'projects/highland-drawings/reconciled.spec.json').read_text())
    presentation=spec['presentation_refresh']
    scene=next(s for s in bpy.data.scenes if s.name.startswith('Dusk' if args.dusk or args.dusk_review else 'Daylight'))
    bpy.context.window.scene=scene
    scene.render.threads_mode='FIXED';scene.render.threads=3
    started=time.monotonic()
    outputs=[]
    if not args.review:
        recipe=presentation['dusk_review' if args.dusk_review else 'dusk' if args.dusk else 'day']
        scene.render.resolution_x,scene.render.resolution_y=recipe['resolution'];scene.render.resolution_percentage=100
        scene.cycles.samples=recipe['samples'];scene.cycles.adaptive_min_samples=4 if args.dusk_review else 8
        for frame in recipe.get('frames',[recipe.get('frame',1)]):
            scene.frame_set(frame)
            name=f'dusk-review/frame-{frame:03}.png' if args.dusk_review else 'Highland-dusk-drawing-reconciled.png' if args.dusk else 'Highland-daylight-drawing-reconciled.png'
            path=OUT/name;path.parent.mkdir(parents=True,exist_ok=True);scene.render.filepath=str(path)
            bpy.ops.render.render(write_still=True,scene=scene.name);outputs.append(path)
    else:
        architecture={o for c in ('Envelope','Glazing','Balconies','Roof') for o in bpy.data.collections[c].objects}
        for o in scene.objects:
            if o.type in ('MESH','CURVE','FONT') and o not in architecture:o.hide_render=True
        scene.compositing_node_group=None
        world=bpy.data.worlds.new('Revision 06 provenance review');world.use_nodes=True
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
        for name,location,target,scale in [('north',(18.5,120,11),(18.5,22,11),47),('south',(18.5,-85,11),(18.5,22,11),47),('plan',(18.5,22,105),(18.5,22,0),68),('iso',(80,95,42),(18.5,22,10),70),('p1-plan',(18.5,22,105),(18.5,22,0),68),('p1-south',(18.5,-85,1.7),(18.5,22,1.7),43),('r5-return',(57,-19,29),(32,10,18),20),('west',(-80,22,11),(18.5,22,11),59),('east',(100,22,11),(18.5,22,11),59),('r5-plan',(19,25,100),(19,25,16),63),('r5-southwest',(-12,-12,30),(13,13,18),24),('terrace-plan',(19,25,100),(19,25,0),63)]:
            if args.views and name not in args.views.split(','): continue
            for o in architecture:
                o.hide_render=(name.startswith('p1-') and not (o.name.startswith(('wall-P1-','south-P1-','east-P1-')) or o.name=='slab-P1'))
                if name=='terrace-plan': o.hide_render=not (o.name.startswith(('R5 terrace ', 'wall-R5-','south-R5-','east-R5-','west-R5-')) or o.name=='slab-R5')
                if name=='r5-plan': o.hide_render=not(o.name.startswith(('wall-R5-','south-R5-','east-R5-','west-R5-')) or o.name=='slab-R5')
            camera.location=location;camera.rotation_euler=(Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.ortho_scale=scale
            path=folder/(name+'.png');scene.render.filepath=str(path)
            bpy.ops.render.render(write_still=True,scene=scene.name)
            im=Image.open(path).convert('RGB');footer=Image.new('RGB',(1200,944),'white');footer.paste(im)
            ImageDraw.Draw(footer).text((15,913),f'Revision 06 / {name} | Orange: complete components assumed. Measured plan positions provisional. Not for construction.',fill='#263943',font=ImageFont.load_default(size=16))
            footer.save(path);outputs.append(path);print('REVIEW',name,flush=True)
    report={'native_sha256':hashlib.sha256((OUT/'Highland-drawing-reconciled.blend').read_bytes()).hexdigest(),'scene':scene.name,'architecture_inventory_sha256':scene['architecture_inventory_sha256'],'elapsed_seconds':round(time.monotonic()-started,2),'samples':scene.cycles.samples,'images':{str(p.relative_to(OUT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in outputs}}
    (OUT/('review-render.json' if args.review else 'dusk-review-render.json' if args.dusk_review else 'dusk-render.json' if args.dusk else 'native-render.json')).write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report),flush=True)


if __name__=='__main__':main()
