"""Supplementary diagnostic views from saved blend; never saves scene changes."""
import bpy, math, sys
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]
scene=bpy.context.scene
scene.render.engine='BLENDER_WORKBENCH'
scene.render.resolution_x=1600;scene.render.resolution_y=1200;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'
shade=scene.display.shading;shade.light='STUDIO';shade.color_type='MATERIAL';shade.show_shadows=True;shade.show_cavity=True;shade.cavity_type='BOTH';shade.background_type='WORLD';scene.world.color=(.13,.13,.13)
cam=scene.camera
cam.data.type='ORTHO';cam.data.ortho_scale=62
cam.location=(22,-32,65)
cam.rotation_euler=(Vector((22,20,0))-cam.location).to_track_quat('-Z','Y').to_euler()
folder=ROOT/'renders/detail';folder.mkdir(exist_ok=True)
# Diagnostic cutaway only: omit upper-floor context, east wall, garages and opaque soil.
for o in bpy.data.objects:
    if o.name.startswith(('BldgB_UpperFloor_', 'East_Garage_Block_', 'CTX_')) or o.name in ('East_Exterior_Wall','North_Exterior_Wall','Subgrade_Soil_Mass'):
        o.hide_render=True;o.hide_viewport=True
for frame in ([] if '--isolated-only' in sys.argv else [1,38,50,61,68,76,83,89]):
    scene.frame_set(frame)
    scene.render.filepath=str(folder/f'B101_close_{frame:03d}.png')
    bpy.ops.render.render(write_still=True)
# Isolate evaluated slab/cutters from the rest of model for a clear Boolean plan review.
scene.frame_set(89)
for o in bpy.data.objects:
    if o.animation_data:
        for fc in list(o.animation_data.drivers):
            if fc.data_path in ('hide_render','hide_viewport'):o.driver_remove(fc.data_path)
    if o.type not in ('CAMERA','LIGHT'):o.hide_render=o.name!='BuildingB_SOG_5p5in';o.hide_viewport=o.hide_render
cam.location=(23,20,90);cam.rotation_euler=(0,0,0);cam.data.ortho_scale=70
scene.render.filepath=str(folder/'B101_slab_boolean_top_089.png');bpy.ops.render.render(write_still=True)
# Plumbing/cuts/supports only, after selecting their phase-visible state at exposed-CI checkpoint.
scene.frame_set(83)
for o in bpy.data.objects:
    if o.type not in ('CAMERA','LIGHT'):
        visible=o.name.startswith(('B101_DEMO_CI_','B101_DEMO_ExistingPTrap_','B101_DEMO_WCCarrier_','B101_DEMO_Cut_')) or ('B101' in o.name and (('ABS' in o.name and o.get('PHASE_ROLE')=='REMAIN') or 'EX_CI' in o.name))
        o.hide_render=not visible;o.hide_viewport=not visible
cam.location=(22,-32,55);cam.rotation_euler=(Vector((22,20,0))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=50
scene.render.filepath=str(folder/'B101_fittings_cuts_supports_083.png');bpy.ops.render.render(write_still=True)
scene.frame_set(91)
for o in bpy.data.objects:
    if o.type not in ('CAMERA','LIGHT'):
        visible='B101' in o.name and o.get('PHASE_ROLE') in ('NEW_ABS','REMAIN')
        o.hide_render=not visible;o.hide_viewport=not visible
scene.render.filepath=str(folder/'B101_new_ABS_route_091.png');bpy.ops.render.render(write_still=True)
print('DETAIL_RENDERS_COMPLETE',flush=True)
