"""Small source-geometry/provenance views, independent of the beauty scene."""
import bpy
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'deliverables/highland-refined/source-review';OUT.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'build/highland-refined/Highland-exterior.blend'),load_ui=False,use_scripts=False)
s=bpy.context.scene
architecture=[o for name in ('Envelope','Glazing','Balconies','Roof') for o in bpy.data.collections[name].objects]
for o in s.objects:
    if o.type in ('MESH','FONT') and o not in architecture:o.hide_render=True
s.render.resolution_x=800;s.render.resolution_y=600;s.render.resolution_percentage=100;s.cycles.samples=12;s.cycles.use_denoising=True;s.render.threads_mode='FIXED';s.render.threads=3
s.camera.data.type='ORTHO';s.camera.data.shift_y=0
views=[('south',(18.5,-85,11),(18.5,22,11),47),('east',(115,22,11),(18.5,22,11),59),('plan',(18.5,22,105),(18.5,22,0),68),('provenance',(80,-80,40),(18.5,22,10),70)]
for name,pos,target,scale in views:
    if name=='provenance':
        m=bpy.data.materials.new('Assumed / orange');m.use_nodes=True;m.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value=(1,.24,.035,1)
        for o in architecture:o.data.materials.clear();o.data.materials.append(m)
    s.camera.location=pos;s.camera.rotation_euler=(Vector(target)-s.camera.location).to_track_quat('-Z','Y').to_euler();s.camera.data.ortho_scale=scale
    s.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True)
    print('REVIEW',name,flush=True)
