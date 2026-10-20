import os
import zipfile

PACKAGE_DIR = "Highland_20k_Upgrade_Package"
os.makedirs(PACKAGE_DIR, exist_ok=True)

# ==============================================================================
# FILE 1: AGENT_INSTRUCTIONS.md (Complete Spec & Execution Protocol)
# ==============================================================================
agent_md = """# 200 W. Highland — $20,000 Archviz Upgrade Specification
**Target Software:** Blender 4.0+ (Python `bpy` API)
**Project Goal:** Transform the 9:16 BIM walkthrough (`Lobby -> Corridors 108 + 208`) into a 16:9 widescreen, path-traced luxury architectural film culminating in a sunlit Top-Floor Penthouse reveal.

---

## 1. Executive Summary of Required Fixes
1. **Aspect Ratio & Framing:** Convert from 9:16 vertical to **16:9 Widescreen (`3840x2160`)** using architectural tilt-shift lenses (`Rotation X = 90°`, `Rotation Y = 0°`, vertical framing adjusted via `Shift Y`).
2. **Camera Blocking:** Replace the single continuous spline path (which clips through doors at `00:04` and `00:14` and stares into drywall corners at `00:08` and `00:12`) with a **6-camera linear Steadicam cut sequence** bound to timeline markers.
3. **Render Engine & Lighting:** Switch to **Cycles GPU** with **AgX (Medium High Contrast)** color management. Replace flat emissive lighting with invisible `95°` spread Area Lights (`visible_glossy = False` to eliminate the circular specular hotspot on Elevator M1 at `00:13`).
4. **Global PBR Upgrade:** Inject a `3mm` (`0.003m`) `ShaderNodeBevel` into all architectural materials and clamp blown-out white ceiling emissives to warm `3500K` (`Strength = 4.0`).
5. **Hero X-Ray Section (`00:14–00:18`):** Use an animated Boolean Cutter (`XRay_Section_Cutter`) with a glowing gold cut-face shader (`MAT_Section_Cut_Glow`) so only the elevator shaft facade slices open while hiding background massing blocks.
6. **The Emotional Payoff (`00:19–00:26`):** Instead of ending at the brown utility door (`STAIR M1`) at the end of Corridor 208, attach the generated **Penthouse Soundstage** directly behind the `STAIR M1` threshold so the camera glides out of the dim corridor into a golden-hour top-floor living room overlooking the setback terrace.

---

## 2. Automated Execution Protocol (For AI Agent or Technical Artist)

### Step 1: Run Master Scene Upgrader (`01_master_scene_upgrade.py`)
Execute inside Blender (`blender your_scene.blend --python 01_master_scene_upgrade.py` or via the Scripting tab).
* Configures Cycles, AgX, 16:9 4K resolution, and OpenImageDenoise.
* Generates the 6-camera rig (`CAM_01` through `CAM_06`) and binds them to frame markers (`1, 121, 251, 421, 551, 580`).
* Injects micro-bevels across all scene materials and fixes light ray-visibility.
* Builds the Realtime Compositor node tree (`Fog Glow Glare` + `Lens Dispersion`).

### Step 2: Run Penthouse & X-Ray Rig Builder (`02_penthouse_and_xray_rig.py`)
* Generates the `Penthouse_Soundstage` collection parented to `PENTHOUSE_MASTER_HANDLE` (8m x 7m x 3.4m room shell, entry doorway Boolean, wide-plank oak floor, bronze window mullions, terrace glass railing, Sky Portal, and `2800K` Golden Hour Sun).
* Generates the `XRay_Section_Cutter` Boolean rig for frames `415–550`.

### Step 3: Scene Alignment & Asset Population Checklist
1. **Snap Penthouse to Corridor 208:**
   * Locate the `STAIR M1` door mesh at the end of Corridor 208.
   * Copy its world coordinates/orientation to `PENTHOUSE_MASTER_HANDLE` so the Penthouse entry doorway aligns seamlessly with the end of Corridor 208.
   * Rotate the `STAIR M1` door open `80°` on the Z-axis (or hide it) and hide the overhead `STAIR M1` sign so golden sunset light spills into the corridor carpet.
2. **Align Camera Coordinates:**
   * Verify `CAM_01` through `CAM_05` world coordinates match the building's local origin offset.
   * Keyframe the exterior entry glass doors (`Frames 70–110`) and Elevator M1 doors (`Frames 380–415`) opening so cameras never clip through solid geometry.
3. **Populate Hero Assets (BlenderKit / Poly Haven):**
   * Load a 4K Dusk HDRI into the World Shader.
   * Place 1 modern sofa, 1 olive tree/plant, and 2 outdoor terrace lounge chairs inside `Penthouse_Soundstage`.
   * Add door handles and room number plaques to Corridor 208 unit doors.
4. **HUD / Typography Adjustment:**
   * Remove the floor-projected text spline (`LOBBY 110`, `CORRIDOR 208`).
   * At Frame 580 (`00:19`), update top-left HUD text to `Lobby -> Penthouse Residence` and bottom-left text to `PENTHOUSE / West Terrace Reveal`.
"""

# ==============================================================================
# FILE 2: 01_master_scene_upgrade.py (Render, Cameras, Shaders, Compositor)
# ==============================================================================
script_01 = """import bpy
import math

def run_master_upgrade():
    scene = bpy.context.scene

    # 1. CYCLES, 16:9 4K & AgX COLOR MANAGEMENT
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'GPU'
    scene.render.resolution_x = 3840
    scene.render.resolution_y = 2160
    scene.render.resolution_percentage = 50 # 1080p preview; set 100 for final 4K
    scene.render.fps = 30
    scene.frame_start = 1
    scene.frame_end = 780

    scene.cycles.samples = 512
    scene.cycles.adaptive_threshold = 0.015
    scene.cycles.use_denoising = True
    scene.cycles.denoiser = 'OPENIMAGEDENOISE'
    scene.cycles.denoising_input_passes = 'RGB_ALBEDO_NORMAL'

    scene.cycles.max_bounces = 12
    scene.cycles.diffuse_bounces = 4
    scene.cycles.glossy_bounces = 4
    scene.cycles.transmission_bounces = 8
    scene.cycles.volume_bounces = 2
    scene.cycles.sample_clamp_indirect = 10.0

    try:
        scene.view_settings.view_transform = 'AgX'
        scene.view_settings.look = 'AgX - Medium High Contrast'
    except TypeError:
        scene.view_settings.view_transform = 'Filmic'
        scene.view_settings.look = 'Medium High Contrast'

    # 2. MULTI-CAMERA RIG & MARKERS
    cam_col = bpy.data.collections.get("Archviz_Cameras")
    if not cam_col:
        cam_col = bpy.data.collections.new("Archviz_Cameras")
        scene.collection.children.link(cam_col)

    scene.timeline_markers.clear()

    shots = [
        ("CAM_01_Exterior",         1,   120, (0, -15, 2.2), (90, 0, 0),  28),
        ("CAM_02_Lobby110",         121, 250, (0, -4, 1.6),  (90, 0, 0),  28),
        ("CAM_03_ElevatorApproach", 251, 420, (0, 4, 1.6),   (90, 0, 90), 28),
        ("CAM_04_SectionRise",      421, 550, (-6, 6, 4.0),  (90, 0, 45), 32),
        ("CAM_05_Corridor208",      551, 579, (0, 6, 4.8),   (90, 0, 0),  28),
    ]

    for name, f_start, f_end, loc, rot, lens in shots:
        cam_data = bpy.data.cameras.new(name)
        cam_data.lens = lens
        cam_data.sensor_width = 36.0
        cam_data.passepartout_alpha = 0.95
        cam_data.show_composition_thirds = True
        cam_data.show_composition_center = True

        cam_obj = bpy.data.objects.new(name, cam_data)
        cam_col.objects.link(cam_obj)
        cam_obj.location = loc
        cam_obj.rotation_euler = [math.radians(a) for a in rot]

        cam_obj.keyframe_insert(data_path="location", frame=f_start)
        cam_obj.keyframe_insert(data_path="location", frame=f_end)

        if cam_obj.animation_data and cam_obj.animation_data.action:
            for fcurve in cam_obj.animation_data.action.fcurves:
                for kf in fcurve.keyframe_points:
                    kf.interpolation = 'LINEAR'

        marker = scene.timeline_markers.new(name=name, frame=f_start)
        marker.camera = cam_obj

    # 3. GLOBAL MATERIAL UPGRADER (Micro-Bevels & Warm Emissives)
    for mat in bpy.data.materials:
        if not mat.use_nodes or not mat.node_tree:
            continue
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links

        for node in nodes:
            if node.type == 'BSDF_PRINCIPLED':
                if not node.inputs['Normal'].is_linked:
                    bevel = nodes.new(type='ShaderNodeBevel')
                    bevel.samples = 4
                    bevel.inputs['Radius'].default_value = 0.003
                    bevel.location = (node.location.x - 250, node.location.y - 300)
                    links.new(bevel.outputs['Normal'], node.inputs['Normal'])
                if not node.inputs['Roughness'].is_linked:
                    if node.inputs['Roughness'].default_value > 0.85:
                        node.inputs['Roughness'].default_value = 0.65
            elif node.type == 'EMISSION':
                if node.inputs['Strength'].default_value > 6.0:
                    node.inputs['Strength'].default_value = 4.0
                node.inputs['Color'].default_value = (1.0, 0.95, 0.88, 1.0)

    # 4. LIGHT RAY-VISIBILITY FIX
    for obj in bpy.data.objects:
        if obj.type == 'LIGHT':
            obj.visible_camera = False
            obj.visible_glossy = False
            if obj.data.type == 'AREA':
                obj.data.spread = math.radians(95)

    # 5. COMPOSITOR PIPELINE (Fog Glow + Lens Dispersion)
    scene.use_nodes = True
    c_tree = scene.node_tree
    c_nodes = c_tree.nodes
    c_links = c_tree.links
    c_nodes.clear()

    r_layers = c_nodes.new('CompositorNodeRLayers')
    r_layers.location = (-400, 0)

    glare = c_nodes.new('CompositorNodeGlare')
    glare.glare_type = 'FOG_GLOW'
    glare.quality = 'HIGH'
    glare.threshold = 0.85
    glare.size = 7
    glare.location = (0, 0)

    lens = c_nodes.new('CompositorNodeLensdist')
    lens.use_fit = True
    lens.inputs['Distort'].default_value = -0.008
    lens.inputs['Dispersion'].default_value = 0.004
    lens.location = (250, 0)

    comp = c_nodes.new('CompositorNodeComposite')
    comp.location = (500, 0)

    c_links.new(r_layers.outputs['Image'], glare.inputs['Image'])
    c_links.new(glare.outputs['Image'], lens.inputs['Image'])
    c_links.new(lens.outputs['Image'], comp.inputs['Image'])

    print("✅ Step 1 Complete: Master Scene Upgrade Applied.")

if __name__ == "__main__":
    run_master_upgrade()
"""

# ==============================================================================
# FILE 3: 02_penthouse_and_xray_rig.py (Penthouse Soundstage + X-Ray Section)
# ==============================================================================
script_02 = """import bpy
import bmesh
import math

def build_penthouse_and_xray():
    scene = bpy.context.scene
    scene.frame_end = 780

    # ==========================================
    # PART A: PENTHOUSE SOUNDSTAGE GENERATOR
    # ==========================================
    ph_col = bpy.data.collections.get("Penthouse_Soundstage")
    if not ph_col:
        ph_col = bpy.data.collections.new("Penthouse_Soundstage")
        scene.collection.children.link(ph_col)

    def link_to_ph(obj):
        for c in obj.users_collection:
            c.objects.unlink(obj)
        ph_col.objects.link(obj)

    master = bpy.data.objects.new("PENTHOUSE_MASTER_HANDLE", None)
    master.empty_display_type = 'ARROWS'
    master.empty_display_size = 2.0
    master.location = (0, 10, 4.0)
    link_to_ph(master)

    def make_mat(name, color, rough, metal=0.0, trans=0.0):
        m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
        m.use_nodes = True
        bsdf = m.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            bsdf.inputs["Base Color"].default_value = color
            bsdf.inputs["Roughness"].default_value = rough
            bsdf.inputs["Metallic"].default_value = metal
            if trans > 0:
                key = "Transmission Weight" if "Transmission Weight" in bsdf.inputs else "Transmission"
                bsdf.inputs[key].default_value = trans
        return m

    mat_wall = make_mat("PH_Warm_Plaster", (0.93, 0.91, 0.87, 1.0), 0.55)
    mat_oak = make_mat("PH_Wide_Oak", (0.36, 0.23, 0.13, 1.0), 0.26)
    mat_mullion = make_mat("PH_Anodized_Bronze", (0.04, 0.035, 0.03, 1.0), 0.25, metal=0.85)
    mat_glass = make_mat("PH_Clear_Glass", (1.0, 1.0, 1.0, 1.0), 0.02, trans=0.95)

    bpy.ops.mesh.primitive_cube_add(size=1.0)
    shell = bpy.context.active_object
    shell.name = "PH_Room_Walls"
    shell.parent = master
    shell.location = (0, 3.5, 1.7)
    shell.scale = (8.0, 7.0, 3.4)
    bpy.ops.object.transform_apply(scale=True)
    link_to_ph(shell)

    bpy.ops.object.mode_set(mode='EDIT')
    bm = bmesh.from_edit_mesh(shell.data)
    bm.faces.ensure_lookup_table()
    win_faces = [f for f in bm.faces if f.normal.y > 0.9]
    bmesh.ops.delete(bm, geom=win_faces, context='FACES')
    for f in bm.faces:
        f.normal_flip()
    bmesh.update_edit_mesh(shell.data)
    bpy.ops.object.mode_set(mode='OBJECT')
    shell.data.materials.append(mat_wall)

    bpy.ops.mesh.primitive_cube_add(size=1.0)
    door_cutter = bpy.context.active_object
    door_cutter.name = "PH_Entry_Door_Cutter"
    door_cutter.parent = master
    door_cutter.location = (0, 0, 1.15)
    door_cutter.scale = (1.3, 0.6, 2.3)
    door_cutter.display_type = 'WIRE'
    door_cutter.hide_render = True
    door_cutter.visible_camera = False
    link_to_ph(door_cutter)

    bool_mod = shell.modifiers.new(name="Entry_Door_Opening", type='BOOLEAN')
    bool_mod.operation = 'DIFFERENCE'
    bool_mod.object = door_cutter

    bpy.ops.mesh.primitive_plane_add(size=1.0)
    floor = bpy.context.active_object
    floor.name = "PH_Oak_Flooring"
    floor.parent = master
    floor.location = (0, 5.0, 0.01)
    floor.scale = (8.0, 10.0, 1.0)
    floor.data.materials.append(mat_oak)
    link_to_ph(floor)

    for x_pos in [-3.95, -1.35, 1.35, 3.95]:
        bpy.ops.mesh.primitive_cube_add(size=1.0)
        mullion = bpy.context.active_object
        mullion.name = "PH_Window_Mullion"
        mullion.parent = master
        mullion.location = (x_pos, 6.95, 1.7)
        mullion.scale = (0.08, 0.12, 3.4)
        mullion.data.materials.append(mat_mullion)
        link_to_ph(mullion)

    bpy.ops.mesh.primitive_plane_add(size=1.0)
    glass = bpy.context.active_object
    glass.name = "PH_Window_Glass"
    glass.parent = master
    glass.location = (0, 6.95, 1.7)
    glass.scale = (8.0, 3.4, 1.0)
    glass.rotation_euler[0] = math.radians(90)
    glass.data.materials.append(mat_glass)
    link_to_ph(glass)

    bpy.ops.mesh.primitive_cube_add(size=1.0)
    railing = bpy.context.active_object
    railing.name = "PH_Terrace_Railing"
    railing.parent = master
    railing.location = (0, 9.8, 0.55)
    railing.scale = (8.0, 0.04, 1.1)
    railing.data.materials.append(mat_glass)
    link_to_ph(railing)

    portal_data = bpy.data.lights.new(name="PH_Sky_Portal", type='AREA')
    portal_data.shape = 'RECTANGLE'
    portal_data.size = 7.8
    portal_data.size_y = 3.2
    portal_data.is_portal = True
    portal = bpy.data.objects.new("PH_Sky_Portal", portal_data)
    portal.parent = master
    portal.location = (0, 7.3, 1.7)
    portal.rotation_euler = (math.radians(-90), 0, 0)
    link_to_ph(portal)

    sun_data = bpy.data.lights.new(name="PH_Golden_Sun", type='SUN')
    sun_data.energy = 4.5
    sun_data.color = (1.0, 0.74, 0.48)
    sun_data.angle = math.radians(2.5)
    sun = bpy.data.objects.new("PH_Golden_Sun", sun_data)
    sun.parent = master
    sun.location = (0, 9.0, 2.5)
    sun.rotation_euler = (math.radians(-78), math.radians(15), math.radians(20))
    link_to_ph(sun)

    cam_data = bpy.data.cameras.new("CAM_06_PenthouseReveal")
    cam_data.lens = 24.0
    cam_data.passepartout_alpha = 0.95
    cam_data.dof.use_dof = True
    cam_data.dof.focus_distance = 6.0
    cam_data.dof.aperture_fstop = 4.0
    cam = bpy.data.objects.new("CAM_06_PenthouseReveal", cam_data)
    cam.parent = master
    link_to_ph(cam)

    cam.location = (0, -1.5, 1.6)
    cam.rotation_euler = (math.radians(90), 0, 0)
    cam.keyframe_insert(data_path="location", frame=580)

    cam.location = (0, 4.2, 1.6)
    cam.keyframe_insert(data_path="location", frame=780)

    for fcurve in cam.animation_data.action.fcurves:
        for kf in fcurve.keyframe_points:
            kf.interpolation = 'LINEAR'

    marker = scene.timeline_markers.new(name="CAM_06_PenthouseReveal", frame=580)
    marker.camera = cam

    # ==========================================
    # PART B: X-RAY BOOLEAN ELEVATOR CUTTER RIG
    # ==========================================
    cut_mat = bpy.data.materials.get("MAT_Section_Cut_Glow") or bpy.data.materials.new("MAT_Section_Cut_Glow")
    cut_mat.use_nodes = True
    nodes = cut_mat.node_tree.nodes
    nodes.clear()
    emiss = nodes.new('ShaderNodeEmission')
    emiss.inputs['Color'].default_value = (1.0, 0.78, 0.45, 1.0)
    emiss.inputs['Strength'].default_value = 6.0
    out = nodes.new('ShaderNodeOutputMaterial')
    cut_mat.node_tree.links.new(emiss.outputs['Emission'], out.inputs['Surface'])

    bpy.ops.mesh.primitive_cube_add(size=8.0, location=(0, 4, 5))
    cutter = bpy.context.active_object
    cutter.name = "XRay_Section_Cutter"
    cutter.display_type = 'WIRE'
    cutter.visible_camera = False
    cutter.visible_diffuse = False
    cutter.visible_glossy = False
    cutter.visible_shadow = False
    cutter.data.materials.append(cut_mat)

    cutter.scale = (0.01, 0.01, 0.01)
    cutter.keyframe_insert(data_path="scale", frame=415)
    cutter.scale = (1.0, 1.0, 1.5)
    cutter.keyframe_insert(data_path="scale", frame=435)
    cutter.keyframe_insert(data_path="scale", frame=535)
    cutter.scale = (0.01, 0.01, 0.01)
    cutter.keyframe_insert(data_path="scale", frame=550)

    print("✅ Step 2 Complete: Penthouse Soundstage & X-Ray Section Rig Built.")

if __name__ == "__main__":
    build_penthouse_and_xray()
"""

files = {
    "AGENT_INSTRUCTIONS.md": agent_md,
    "01_master_scene_upgrade.py": script_01,
    "02_penthouse_and_xray_rig.py": script_02,
}

for filename, content in files.items():
    filepath = os.path.join(PACKAGE_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

zip_filename = "Highland_20k_Upgrade_Package.zip"
with zipfile.ZipFile(zip_filename, "w", zipfile.ZIP_DEFLATED) as zf:
    for filename in files.keys():
        zf.write(os.path.join(PACKAGE_DIR, filename), arcname=filename)

print(f"✅ Created folder '{PACKAGE_DIR}/' and archive '{zip_filename}'!")
