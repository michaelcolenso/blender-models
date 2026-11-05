"""Diagnostic screenshot: actual slab opening versus authored protection outline; no save."""
import bpy
from pathlib import Path
from mathutils import Vector
root=Path(__file__).resolve().parents[1]
s=bpy.context.scene;s.frame_set(89)
for o in bpy.data.objects:
    if o.animation_data:
        for fc in list(o.animation_data.drivers):
            if fc.data_path in ('hide_render','hide_viewport'):o.driver_remove(fc.data_path)
    if o.type not in ('CAMERA','LIGHT'):o.hide_render=o.name!='BuildingB_SOG_5p5in';o.hide_viewport=o.hide_render
m=bpy.data.materials.new('QA_Protection_Boundary_Red');m.diffuse_color=(.9,.04,.03,1)
env=bpy.data.objects['B101_DEMO_PriorRepair_NoDemo_Envelope'];bb=[env.matrix_world@Vector(v) for v in env.bound_box]
x0,x1=min(v.x for v in bb),max(v.x for v in bb);y0,y1=min(v.y for v in bb),max(v.y for v in bb)
c=bpy.data.curves.new('QA_EnvelopeOutline','CURVE');c.dimensions='3D';c.bevel_depth=.025;c.bevel_resolution=1
sp=c.splines.new('POLY');sp.points.add(4)
for p,co in zip(sp.points,[(x0,y0,.05,1),(x1,y0,.05,1),(x1,y1,.05,1),(x0,y1,.05,1),(x0,y0,.05,1)]):p.co=co
ob=bpy.data.objects.new('QA_EnvelopeOutline',c);s.collection.objects.link(ob);c.materials.append(m)
t=bpy.data.curves.new('QA_Label','FONT');t.body='RED LINE: NO-DEMO ENVELOPE\nOpening crosses into protected side (+Y)';t.size=.24
o=bpy.data.objects.new('QA_Label',t);s.collection.objects.link(o);o.location=(19.6,30.2,.06);t.materials.append(m)
s.render.engine='BLENDER_WORKBENCH';s.display.shading.color_type='MATERIAL';s.display.shading.show_cavity=True;s.display.shading.cavity_type='BOTH'
s.render.resolution_x=1400;s.render.resolution_y=1000;s.render.resolution_percentage=100
cam=s.camera;cam.data.type='ORTHO';cam.data.ortho_scale=10;cam.location=(23,28,40);cam.rotation_euler=(0,0,0)
s.render.filepath=str(root/'renders/detail/B101_prior_ABS_envelope_conflict_089.png');bpy.ops.render.render(write_still=True)
