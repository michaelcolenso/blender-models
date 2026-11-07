---
name: archviz-film-upgrade
description: Upgrade a VDC/BIM/CAD scene in Blender 5.x into a high-end path-traced architectural presentation film — level two-point cameras, multi-camera linear cuts, compression-and-release narrative, AgX, micro-bevels, fixture glow vs. real area lights, section reveals, sky portals, Blender 5 compositor and slotted-action APIs. Use for archviz/walkthrough presentation films, not for review renders or coordination/work-sequence films.
---

# VDC-to-archviz film upgrade

## How this fits this repo (read first; overrides the directive where they differ)

- **Scope:** presentation films only (e.g. `highland/walkthrough`, `deliverables/archviz`). Review renders keep their
  provenance colors and plan/iso cameras. Coordination and work-sequence films (e.g. the `highland/risers` Corridor
  108 sequence) keep their own framing and may end in a corridor; Rule 3 doesn't apply to them.
- **Realism never changes geometry** (`docs/METHOD.md`). The bevel is a shader effect, which is fine. The section rig
  in Module B adds non-destructive modifiers to a presentation scene only, never to a spec build. Every film still
  carries the "illustrative, not a contract document" strip.
- **Diagnostic frames (section 0):** write them under `build/<site>/<product>/diagnostics/` (git-ignored), not
  `/tmp`; scripts take the path from `$BM_BUILD` or an argument, never a hard-coded one. Look at every frame with the
  Read tool and say in the report which frames you looked at. "Ran without errors" doesn't count as checked (the
  repo's "checks passed" and "looked at the renders" rule). On CPU, a 1920×1080 frame at 32 samples can take minutes on
  a heavy scene, so render the diagnostics at 25% while iterating and save 50% for the final pass.
- **Where it runs:** `scene.cycles.device = 'GPU'` only on RunPod (`products/*/runpod_*.sh`). This laptop and CI
  render on CPU; for CPU previews set the device to `'CPU'` and lower the resolution and samples.
- **`device = 'GPU'` alone is not enough headless.** Script 2 never enables a compute device, so Cycles quietly
  renders on CPU. Use `configure_device()` in `projects/highland/products/walkthrough/cinema.py`: it sets
  `compute_device_type` (`OPTIX`/`CUDA`), enables the devices and exits if none is found, so it never falls back
  silently.
- **House example:** `projects/highland/products/walkthrough/` (`CINEMA.md`, `cinema.shots.json`, `cinema.py`,
  `cinema_score.py`, `cinema_finish.py`) already implements most of section 8: a shot list as data, cuts on
  musical beats, level lens-shifted cameras, motion blur, frame claiming across parallel GPU workers, benchmarking,
  a graded finish and an original score. Extend it or copy its patterns before writing a new pipeline.
- **Section 8** (the end of this file) holds the repo's own agency-grade additions to the directive. Apply them
  together with it.
- **Existing compositor:** Script 2 deletes the scene's current `compositing_node_group`. Look at what it does first
  (e.g. a caption or disclaimer pass) and rebuild that into the new tree.
- **Boolean solver:** use `'MANIFOLD'`, not `'EXACT'`. Exact fails on the coplanar faces architectural meshes always
  have.
- **Lens distortion bends straight lines,** which works against Rule 1. Keep `Distortion` at 0 and use dispersion only
  if wanted.
- **Tested 2026-11-06 on headless bpy 5.0.1:** all three scripts run on a test scene. The compositor renders
  (not black), camera keys come out `LINEAR`, the marker binds the camera, and the guardrail table's node names
  and socket names match this build. One fix was made: Module C sets `portal_data.cycles.is_portal`
  (plain `is_portal` raises `AttributeError` in 5.0.1).
- **Code placement:** if these scripts get reused, port them into `src/bmodels/` as shared code (repo root from
  `bmodels.paths.ROOT`, no hard-coded paths) instead of copying them into each product. Committed `.blend` files stay
  self-contained (packed assets).

---

# Agent Directive: Universal $20k VDC-to-Archviz Upgrade Pipeline (Blender 5.0+)

## 0. PRIME DIRECTIVE: The Visual Verification Loop (Never Fly Blind)

You are a visual artist, not just a code generator. A Python script that executes without errors DOES NOT mean the shot looks good. BIM/VDC geometry frequently contains offset origins, flipped normals, overlapping coplanar faces (Z-fighting), and unapplied scales that break procedural assumptions.

For EVERY camera shot and lighting setup you create, you MUST execute this closed-loop verification cycle before moving on:

1. **Render a Fast Diagnostic Frame:**
   Programmatically render the start, middle, and end frames of each shot at 50% resolution (`1920x1080`, `32` Cycles samples with OIDN enabled) to a temporary directory (`/tmp/vdc_audit_frame_XXXX.png`).
2. **Visually Inspect the Output (Multimodal Vision + Histogram Check):**
   Load and inspect the rendered PNG image. Audit it against five strict visual criteria:
   - **Obstruction Check:** Is the camera clipped inside a wall, mullion, door, or ceiling?
   - **Composition & Balance:** Are vertical lines parallel to the frame edges? Does the floor or ceiling occupy more than 45% of the frame (adjust `shift_y` if so)?
   - **Lighting Ratio (Contrast):** Is the image flat and evenly lit? Every luxury shot requires a clear hierarchy of light: a bright focal destination, mid-tone architectural surfaces, and soft contact shadows grounding the floor/wall intersections.
   - **Highlight/Shadow Clipping:** Are emissive fixtures blooming naturally, or are walls blown out to pure `#FFFFFF` white or crushed into noisy `#000000` black?
   - **Scale & Tactility:** Do materials read at the right real-world UV scale (e.g., brick courses, wood planks, carpet tiles), or are textures stretched/microscopic because object scale wasn't applied (`bpy.ops.object.transform_apply(scale=True)`)?
3. **Iterate Until It Passes:**
   If a diagnostic frame fails ANY of the five checks above, adjust the camera coordinates, light power/angles, or UV mapping and re-render the diagnostic frame until the image looks like an architectural photograph.

## 1. Mission & Role
You are a Lead Technical Artist and Blender 5.0+ Python (`bpy`) Automation Agent. Your objective is to transform raw Virtual Design & Construction (VDC), BIM, or CAD geometry imports inside **Blender 5.x** into **ultra-high-end, path-traced architectural films**.

Raw VDC exports look like engineering diagrams because they suffer from six systemic flaws:
1. Clipped highlight values and narrow-gamut color management.
2. Unnatural continuous "robot spline" camera paths that clip through doors and stare into corners.
3. Razor-sharp 90-degree polygon edges and flat, zero-imperfection shaders.
4. Blown-out emissive ceiling strips and visible light-source specular blobs.
5. Technical cross-sections that reveal untextured background massing.
6. Lack of narrative emotional payoff ("Compression & Release").

---

## 2. CRITICAL: Blender 5.0+ Breaking API Guardrails (Do Not Use 4.x Syntax)

Blender 5.0+ removed legacy shortcuts that dominate older training data. Enforce these exact **Blender 5.x API patterns**:

| System | Deprecated (Blender 4.x — FAILS in 5.x) | Required Blender 5.0+ Syntax |
| :--- | :--- | :--- |
| **Compositor Tree** | `scene.use_nodes = True`<br>`scene.node_tree` (`AttributeError`) | `tree = bpy.data.node_groups.new("Archviz_Comp", "CompositorNodeTree")`<br>`scene.compositing_node_group = tree` |
| **Compositor Output** | `nodes.new('CompositorNodeComposite')` (Removed) | `tree.interface.new_socket(name="Image", in_out="OUTPUT", socket_type="NodeSocketColor")`<br>`out = tree.nodes.new("NodeGroupOutput")` |
| **Compositor Node Options** | `glare.glare_type = 'FOG_GLOW'`<br>`glare.size = 7`<br>`lens.use_fit = True` | Node options are now **Input Sockets** using UI-label strings & `0.0–1.0` floats:<br>`glare.inputs["Type"].default_value = "Fog Glow"`<br>`glare.inputs["Quality"].default_value = "High"`<br>`glare.inputs["Size"].default_value = 0.65`<br>`lens.inputs["Distortion"].default_value = -0.008`<br>`lens.inputs["Dispersion"].default_value = 0.0035`<br>`lens.inputs["Fit"].default_value = True` |
| **Removed Comp Nodes** | `CompositorNodeMixRGB`, `CompositorNodeGamma`, `CompositorNodeMapRange` | Use unified Shader nodes inside the Compositor:<br>`ShaderNodeMix`, `ShaderNodeGamma`, `ShaderNodeMapRange` |
| **Animation F-Curves** | `action.fcurves` (`AttributeError` — Slotted Actions required) | Use `bpy_extras.anim_utils`:<br>`cb = anim_utils.action_ensure_channelbag_for_slot(action, obj.animation_data.action_slot)`<br>`for fcurve in cb.fcurves:` |
| **Property Access** | `scene['cycles']` (Dict-style access removed for `bpy.props`) | Always use dot-attribute syntax: `scene.cycles.samples` |
| **Material / World Nodes** | `mat.use_nodes = True` (Deprecated no-op in 5.x) | Always on by default in 5.0+, or guarded gracefully. |

---

## 3. Universal Architectural & Cinematography Rules

### Rule 1: Two-Point Perspective (Architectural Tilt-Shift)
* **Never tilt an architectural camera up or down.** Vertical architectural lines (walls, columns, doorframes, mullions) must remain 100% parallel to the frame edges.
* Lock every camera's `rotation_euler.x = math.radians(90)` and `rotation_euler.y = 0.0`.
* Frame vertical elevation exclusively via `camera.data.shift_y` (`-0.05` to `+0.15`).
* Use `24mm–35mm` focal lengths (`36mm` full-frame sensor width) in **16:9 Widescreen** (`3840x2160`).

### Rule 2: Multi-Camera Linear Cuts Over Single-Spline Paths
* Never use a single continuous camera spline that twists 90 degrees inside tight corridors or ghosts through closed doors.
* Break the journey into discrete **3-to-5-second cinematic shots** (`CAM_01`, `CAM_02`, etc.) bound to Timeline Markers.
* Force **100% `LINEAR` keyframe interpolation** on all camera location/rotation f-curves via the Blender 5.0+ Slotted Action `channelbag` so movement feels like a constant-velocity Steadicam across cuts.
* Keyframe any door in the camera's path open (`75°–90°` swing or slide) prior to the camera crossing the threshold.

### Rule 3: Narrative "Compression & Release"
* Never end an architectural tour in an enclosed service space (corridors, stairwells, mechanical rooms, or elevator lobbies).
* Circulation spaces are the **Compression Phase** (controlled, warm 3500K artificial light). The final 20% of the timeline must transition into a **Release Phase**—a sunlit destination with high ceilings, natural exterior light (`2800K–4000K` low-angle sun + Sky Portals), and exterior context views.

### Rule 4: Separate Fixture Glow from Scene Illumination
* Clamp visible light fixture `Emission` nodes to `Strength: 3.0–5.0` (`#FFF4E6` warm white) so the fixture reads as diffused acrylic under AgX / ACES 2.0 color management.
* Place actual Blender `AREA` lights (`Spread: 85°–105°`) just below ceiling fixtures and inside coves to cast physical light falloff, and set `light_obj.visible_camera = False` and `light_obj.visible_glossy = False` so they never create artificial specular hotspots on doors, glass, or polished floors.

---

## 4. Script 1: `01_scene_audit_b5.py` (Blender 5.0+ Scene Inspector)

Run this first to inspect collections, spatial bounds, slotted animations, and engine settings.

```python
import bpy
import mathutils

def audit_vdc_scene_b5():
    scene = bpy.context.scene
    print("\n================ BLENDER 5.0+ VDC SCENE AUDIT ================")
    print(f"Blender Version: {bpy.app.version_string}")
    print(f"File: {bpy.data.filepath or 'Unsaved File'}")
    print(f"Engine: {scene.render.engine} | FPS: {scene.render.fps} | Frames: {scene.frame_start}-{scene.frame_end}")

    print("\n1. COLLECTIONS:")
    for col in bpy.data.collections:
        print(f"  - {col.name}: {len(col.objects)} objects")

    meshes = [o for o in scene.objects if o.type == 'MESH' and not o.hide_render]
    if meshes:
        min_co = mathutils.Vector((1e9, 1e9, 1e9))
        max_co = mathutils.Vector((-1e9, -1e9, -1e9))
        for obj in meshes:
            for corner in obj.bound_box:
                world_co = obj.matrix_world @ mathutils.Vector(corner)
                min_co.x = min(min_co.x, world_co.x)
                min_co.y = min(min_co.y, world_co.y)
                min_co.z = min(min_co.z, world_co.z)
                max_co.x = max(max_co.x, world_co.x)
                max_co.y = max(max_co.y, world_co.y)
                max_co.z = max(max_co.z, world_co.z)
        print(f"\n2. WORLD BOUNDS (Meters):")
        print(f"  - Min (X,Y,Z): ({min_co.x:.2f}, {min_co.y:.2f}, {min_co.z:.2f})")
        print(f"  - Max (X,Y,Z): ({max_co.x:.2f}, {max_co.y:.2f}, {max_co.z:.2f})")
        print(f"  - Footprint: {(max_co.x - min_co.x):.2f}m x {(max_co.y - min_co.y):.2f}m x {(max_co.z - min_co.z):.2f}m tall")

    print("\n3. CAMERAS & SLOTTED ACTIONS:")
    for obj in scene.objects:
        if obj.type == 'CAMERA' or (obj.animation_data and obj.animation_data.action):
            slot_name = getattr(obj.animation_data, "action_slot", None)
            slot_info = f" | Slot: {slot_name.name_display}" if slot_name else ""
            print(f"  - {obj.name} ({obj.type}) at {[round(c, 2) for c in obj.location]}{slot_info}")

    print(f"\n4. TOTALS: {len(meshes)} Meshes | {len(bpy.data.materials)} Materials | {len([o for o in scene.objects if o.type == 'LIGHT'])} Lights")
    print("==============================================================\n")

if __name__ == "__main__":
    audit_vdc_scene_b5()
```

---

## 5. Script 2: `02_universal_vdc_upgrader_b5.py` (Engine, Shaders, Lights & 5.0 Compositor)

Run this script on any Blender 5.0+ BIM/VDC scene to configure Cycles GPU, AgX color management, global 3mm shader micro-bevels, procedural roughness breakup, light ray-visibility fixes, and the **Blender 5.0 `compositing_node_group` pipeline**.

```python
import bpy
import math

def apply_universal_vdc_upgrades_b5():
    scene = bpy.context.scene

    # =========================================================================
    # 1. RENDER ENGINE & AgX / ACES 2.0 COLOR SCIENCE
    # =========================================================================
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'GPU'
    scene.render.resolution_x = 3840
    scene.render.resolution_y = 2160
    scene.render.resolution_percentage = 50  # 1080p preview; set 100 for final 4K
    scene.render.use_compositing = True

    # Sampling & Albedo/Normal-Preserving Denoiser
    scene.cycles.samples = 512
    scene.cycles.adaptive_threshold = 0.015
    scene.cycles.use_denoising = True
    scene.cycles.denoiser = 'OPENIMAGEDENOISE'
    scene.cycles.denoising_input_passes = 'RGB_ALBEDO_NORMAL'

    # Architectural Light Bounce Profile
    scene.cycles.max_bounces = 12
    scene.cycles.diffuse_bounces = 4
    scene.cycles.glossy_bounces = 4
    scene.cycles.transmission_bounces = 8
    scene.cycles.volume_bounces = 2
    scene.cycles.sample_clamp_indirect = 10.0

    # Blender 5.0 AgX Color Management
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.look = 'AgX - Medium High Contrast'

    # =========================================================================
    # 2. GLOBAL PBR SHADER UPGRADER (Micro-Bevels + Roughness Breakup + Emissives)
    # =========================================================================
    for mat in bpy.data.materials:
        if not mat.node_tree:
            continue
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links

        for node in list(nodes):
            if node.type == 'BSDF_PRINCIPLED':
                # A. Inject 3mm Architectural Micro-Bevel into unlinked Normals
                if not node.inputs['Normal'].is_linked:
                    bevel = nodes.new(type='ShaderNodeBevel')
                    bevel.samples = 4
                    bevel.inputs['Radius'].default_value = 0.003
                    bevel.location = (node.location.x - 280, node.location.y - 320)
                    links.new(bevel.outputs['Normal'], node.inputs['Normal'])

                # B. Replace flat CG Roughness with subtle procedural micro-variation
                if not node.inputs['Roughness'].is_linked:
                    base_r = node.inputs['Roughness'].default_value
                    if base_r > 0.85:
                        base_r = 0.60

                    tex_coord = nodes.new('ShaderNodeTexCoord')
                    tex_coord.location = (node.location.x - 700, node.location.y - 100)

                    noise = nodes.new('ShaderNodeTexNoise')
                    noise.inputs['Scale'].default_value = 120.0
                    noise.inputs['Detail'].default_value = 8.0
                    noise.inputs['Roughness'].default_value = 0.6
                    noise.location = (node.location.x - 500, node.location.y - 100)

                    ramp = nodes.new('ShaderNodeMapRange')
                    ramp.inputs['To Min'].default_value = max(0.05, base_r - 0.06)
                    ramp.inputs['To Max'].default_value = min(0.95, base_r + 0.06)
                    ramp.location = (node.location.x - 280, node.location.y - 100)

                    links.new(tex_coord.outputs['Object'], noise.inputs['Vector'])
                    links.new(noise.outputs['Fac'], ramp.inputs['Value'])
                    links.new(ramp.outputs['Result'], node.inputs['Roughness'])

                # C. Tame Principled BSDF Emission Strength if driven directly
                if 'Emission Strength' in node.inputs and node.inputs['Emission Strength'].default_value > 6.0:
                    node.inputs['Emission Strength'].default_value = 4.0
                    node.inputs['Emission Color'].default_value = (1.0, 0.95, 0.88, 1.0)

            # D. Tame Dedicated Emission Shader Nodes to Warm 3500K
            elif node.type == 'EMISSION':
                if node.inputs['Strength'].default_value > 6.0:
                    node.inputs['Strength'].default_value = 4.0
                node.inputs['Color'].default_value = (1.0, 0.95, 0.88, 1.0)

    # =========================================================================
    # 3. LIGHT FIXER (Eliminate Specular Blobs & Enforce Architectural Spread)
    # =========================================================================
    for obj in bpy.data.objects:
        if obj.type == 'LIGHT':
            obj.visible_camera = False
            obj.visible_glossy = False
            if obj.data.type == 'AREA':
                obj.data.spread = math.radians(95)

    # =========================================================================
    # 4. BLENDER 5.0+ COMPOSITOR NODE GROUP PIPELINE
    # =========================================================================
    if scene.compositing_node_group:
        bpy.data.node_groups.remove(scene.compositing_node_group)

    comp_tree = bpy.data.node_groups.new("VDC_Archviz_Compositor", "CompositorNodeTree")
    scene.compositing_node_group = comp_tree

    # Create required Group Output Color Socket on tree.interface
    comp_tree.interface.new_socket(
        name="Image",
        in_out="OUTPUT",
        socket_type="NodeSocketColor"
    )

    c_nodes = comp_tree.nodes
    c_links = comp_tree.links
    c_nodes.clear()

    # Render Layers Input
    r_layers = c_nodes.new("CompositorNodeRLayers")
    r_layers.location = (-450, 0)

    # Blender 5.0 Socket-Driven Glare Node
    glare = c_nodes.new("CompositorNodeGlare")
    glare.location = (-100, 0)
    glare.inputs["Type"].default_value = "Fog Glow"
    glare.inputs["Quality"].default_value = "High"
    glare.inputs["Threshold"].default_value = 0.85
    glare.inputs["Size"].default_value = 0.65  # 0.0 to 1.0 scale in Blender 5.0+

    # Blender 5.0 Socket-Driven Lens Distortion Node
    lens = c_nodes.new("CompositorNodeLensdist")
    lens.location = (200, 0)
    lens.inputs["Distortion"].default_value = -0.008
    lens.inputs["Dispersion"].default_value = 0.0035
    lens.inputs["Fit"].default_value = True

    # Group Output Node (Replaces removed CompositorNodeComposite)
    group_out = c_nodes.new("NodeGroupOutput")
    group_out.location = (500, 0)

    c_links.new(r_layers.outputs["Image"], glare.inputs["Image"])
    c_links.new(glare.outputs["Image"], lens.inputs["Image"])
    c_links.new(lens.outputs["Image"], group_out.inputs["Image"])

    print("✅ Blender 5.0+ Universal VDC Upgrades Applied Successfully.")

if __name__ == "__main__":
    apply_universal_vdc_upgrades_b5()
```

---

## 6. Script 3: `03_cinematic_rigs_b5.py` (Blender 5.0 Slotted Action Cameras, X-Ray Section & Portals)

Import or invoke these reusable functions to build multi-camera cuts using **Blender 5.0+ Slotted Actions (`channelbag`)**, glowing Boolean architectural cross-sections, and Golden-Hour "Release" lighting rigs.

```python
import bpy
from bpy_extras import anim_utils
import math

# =============================================================================
# HELPER: ENFORCE LINEAR INTERPOLATION IN BLENDER 5.0+ SLOTTED ACTIONS
# =============================================================================
def set_linear_interpolation_b5(obj):
    """
    Reaches into the Blender 5.0+ Slotted Action channelbag for the given object
    and forces all keyframe points to LINEAR interpolation.
    """
    anim = obj.animation_data
    if not anim or not anim.action or not anim.action_slot:
        return
    channelbag = anim_utils.action_ensure_channelbag_for_slot(anim.action, anim.action_slot)
    if channelbag:
        for fcurve in channelbag.fcurves:
            for kf in fcurve.keyframe_points:
                kf.interpolation = 'LINEAR'


# =============================================================================
# MODULE A: CREATE ARCHITECTURAL TILT-SHIFT CAMERA SHOT (BLENDER 5.0+)
# =============================================================================
def create_archviz_shot_b5(name, frame_start, frame_end, start_loc, end_loc, yaw_deg, lens_mm=28.0, shift_y=0.0, dof_dist=0.0):
    """
    Creates a level 2-point perspective camera with LINEAR Steadicam motion
    using Blender 5.0 Slotted Action channelbags and binds it to a timeline marker.
    """
    scene = bpy.context.scene
    cam_col = bpy.data.collections.get("Archviz_Cameras")
    if not cam_col:
        cam_col = bpy.data.collections.new("Archviz_Cameras")
        scene.collection.children.link(cam_col)

    cam_data = bpy.data.cameras.new(name)
    cam_data.lens = lens_mm
    cam_data.sensor_width = 36.0
    cam_data.shift_y = shift_y
    cam_data.passepartout_alpha = 0.95
    cam_data.show_composition_thirds = True
    cam_data.show_composition_center = True

    if dof_dist > 0.0:
        cam_data.dof.use_dof = True
        cam_data.dof.focus_distance = dof_dist
        cam_data.dof.aperture_fstop = 4.0

    cam_obj = bpy.data.objects.new(name, cam_data)
    cam_col.objects.link(cam_obj)

    # Lock X=90°, Y=0° so vertical lines never converge
    cam_obj.rotation_euler = (math.radians(90), 0.0, math.radians(yaw_deg))

    cam_obj.location = start_loc
    cam_obj.keyframe_insert(data_path="location", frame=frame_start)
    cam_obj.location = end_loc
    cam_obj.keyframe_insert(data_path="location", frame=frame_end)

    # Set linear interpolation via Blender 5.0 channelbag API
    set_linear_interpolation_b5(cam_obj)

    marker = scene.timeline_markers.new(name=name, frame=frame_start)
    marker.camera = cam_obj
    return cam_obj


# =============================================================================
# MODULE B: ANIMATED BOOLEAN X-RAY SECTION RIG (BLENDER 5.0+)
# =============================================================================
def create_boolean_section_rig_b5(target_objects, location, dimensions, frame_in, frame_hold_start, frame_hold_end, frame_out):
    """
    Creates an invisible animated Boolean cutter box that slices open a list of
    target architectural meshes and applies a glowing gold emissive shader ONLY
    to the sliced cross-section faces.
    """
    cut_mat = bpy.data.materials.get("MAT_VDC_Section_Glow") or bpy.data.materials.new("MAT_VDC_Section_Glow")
    nodes = cut_mat.node_tree.nodes
    nodes.clear()

    emiss = nodes.new('ShaderNodeEmission')
    emiss.inputs['Color'].default_value = (1.0, 0.78, 0.45, 1.0)  # Architectural gold
    emiss.inputs['Strength'].default_value = 6.0
    out = nodes.new('ShaderNodeOutputMaterial')
    cut_mat.node_tree.links.new(emiss.outputs['Emission'], out.inputs['Surface'])

    bpy.ops.mesh.primitive_cube_add(size=1.0, location=location)
    cutter = bpy.context.active_object
    cutter.name = "VDC_Boolean_Section_Cutter"
    cutter.display_type = 'WIRE'
    cutter.visible_camera = False
    cutter.visible_diffuse = False
    cutter.visible_glossy = False
    cutter.visible_shadow = False
    cutter.data.materials.append(cut_mat)

    cutter.scale = (0.001, 0.001, 0.001)
    cutter.keyframe_insert(data_path="scale", frame=frame_in)

    cutter.scale = dimensions
    cutter.keyframe_insert(data_path="scale", frame=frame_hold_start)
    cutter.keyframe_insert(data_path="scale", frame=frame_hold_end)

    cutter.scale = (0.001, 0.001, 0.001)
    cutter.keyframe_insert(data_path="scale", frame=frame_out)

    set_linear_interpolation_b5(cutter)

    for obj in target_objects:
        if obj.type == 'MESH' and obj != cutter:
            if cut_mat.name not in obj.data.materials:
                obj.data.materials.append(cut_mat)
            mod = obj.modifiers.new(name="VDC_Section_Cut", type='BOOLEAN')
            mod.operation = 'DIFFERENCE'
            mod.object = cutter
            mod.solver = 'EXACT'

    return cutter


# =============================================================================
# MODULE C: NATURAL LIGHT "RELEASE" PORTAL & SUN RIG
# =============================================================================
def create_golden_hour_window_rig_b5(window_location, window_yaw_deg, width=6.0, height=3.0, sun_elevation_deg=10.0):
    """
    Places a Cycles Sky Portal directly over an exterior window opening alongside
    a low-angle 2800K Golden Hour Sun to create dramatic interior light shafts.
    """
    scene = bpy.context.scene

    # 1. Cycles Interior Sky Portal
    portal_data = bpy.data.lights.new(name="VDC_Window_Portal", type='AREA')
    portal_data.shape = 'RECTANGLE'
    portal_data.size = width
    portal_data.size_y = height
    portal_data.cycles.is_portal = True  # Blender 5.x: the portal flag is a Cycles light property

    portal_obj = bpy.data.objects.new("VDC_Window_Portal", portal_data)
    scene.collection.objects.link(portal_obj)
    portal_obj.location = window_location
    portal_obj.rotation_euler = (math.radians(90), 0.0, math.radians(window_yaw_deg))

    # 2. Warm 2800K Directional Sunset Light
    sun_data = bpy.data.lights.new(name="VDC_Golden_Sun", type='SUN')
    sun_data.energy = 4.5
    sun_data.color = (1.0, 0.74, 0.48)
    sun_data.angle = math.radians(2.5)

    sun_obj = bpy.data.objects.new("VDC_Golden_Sun", sun_data)
    scene.collection.objects.link(sun_obj)
    sun_obj.location = window_location
    sun_obj.rotation_euler = (math.radians(90.0 - sun_elevation_deg), 0.0, math.radians(window_yaw_deg + 15.0))

    return portal_obj, sun_obj
```

---

## 7. Pre-Render Verification Checklist (Blender 5.0+)

Before rendering final frames or animations, the agent must verify:
- [ ] **Blender 5.0 Compositor Verified:** `scene.compositing_node_group` is assigned and terminates in a linked `NodeGroupOutput` node with a `NodeSocketColor` output interface socket (unlinked output produces black frames).
- [ ] **Slotted Action Linear Motion:** All animated cameras have had their f-curves set to `LINEAR` via `anim_utils.action_ensure_channelbag_for_slot()`.
- [ ] **No Vertical Convergence:** Every active camera has `rotation_euler.x == 90°` and `rotation_euler.y == 0°`.
- [ ] **No Geometry Clipping:** No camera passes through closed doors, mullions, or walls at any frame.
- [ ] **No Light Specular Blobs:** All filler `AREA` and `POINT` lights have `visible_camera = False` and `visible_glossy = False`.
- [ ] **Emotional Payoff Delivered:** The final 20% of the timeline transitions out of artificial interior circulation into a naturally lit destination space.

---

## 8. Agency-grade additions (repo maintainers, 2026-11-06)

What separates a $100k agency film from a good render is mostly decided before Cycles runs: the brief, the boards,
the edit and the sound. Then comes discipline about light and material values, and a QC pass nobody skips. Every
API named below was checked against bpy 5.0.1 on 2026-11-06.

### 8.1 Pre-production (decide the film before building it)

- **Brief in one sentence:** who watches it (owner, board, residents, jury), what they must believe at the end,
  and the runtime. 45–90 s is the usual length for an owner or marketing film; residents need 20–40 s per notice.
- **Reference board:** 6–10 frames from real architectural photography and agency films, one per shot, noting
  lens, camera height, time of day and light direction. Match a mood, never copy a frame.
- **Shot list as data:** one JSON entry per shot with lens, shift, keys, focus and an exposure trim, like
  `cinema.shots.json`. Code reads it, so changing the edit doesn't mean editing code.
- **Animatic first:** 10–25% resolution, 4–8 samples, Cycles. Workbench and EEVEE render blank frames headless, so
  Cycles is the only option here. Cut it to the music before spending any real render time. Agencies lock the
  edit at animatic stage; re-cutting after final renders is the most expensive mistake.
- **Cut to music:** shot lengths in whole beats (e.g. 80 BPM: 3 s = 4 beats), with chord changes on the cuts.
  `cinema_score.py` shows how.
- **Handles:** render 8–12 extra frames at both ends of every shot so the edit can slip without re-rendering.

### 8.2 VDC/BIM import hygiene (fix the model before lighting it)

- **Recenter near the origin.** BIM exports often sit at state-plane or survey coordinates, hundreds of km from 0.
  Float precision then makes animated cameras jitter and causes shadow and z-fighting artifacts. Move the model so
  the area of interest is within about 1 km of the origin, and record the offset as a custom property so it can be
  undone.
- **Apply scale and rotation** (`transform_apply(location=False, rotation=True, scale=True)`), recalculate normals,
  and merge by distance at 0.1 mm.
- **Find and fix coplanar duplicates.** Hunt for z-fighting with a diagnostic frame at grazing angles: overlapping
  slabs and finishes, a wall drawn twice by two trades. Delete the duplicate or offset it by 1 mm, and record which
  one stays (the governing trade).
- **Keep identity.** Carry the IFC GlobalId or Revit element ID into `cie_id` and other custom properties, so a
  frame can be traced back to the element that drew it. Import IFC with `ifcopenshell` (not installed;
  `uv add ifcopenshell` and check `uv lock` keeps numpy<2 for bpy) or the Bonsai extension. Speckle is an option
  for live Revit to Blender.
- **Bevel what the camera sees.** The Bevel shader in the directive is costly per sample and doesn't change
  silhouettes. For hero objects in close-up shots, a Bevel modifier (2–3 mm, `harden_normals`) plus a
  WeightedNormal modifier looks better and renders faster. Use it only in the presentation scene, never in a spec
  build.

### 8.3 Cameras and motion

- **Heights:** interiors at 1.2–1.5 m (just below eye level reads as more generous). Exteriors at 1.6 m for
  pedestrian views, or 4–15 m for a modest elevated view. Drone-height views are for context only.
- **Speeds:** a dolly or slider moves at 0.2–0.6 m/s. Any faster reads as a video game. Pans are rare and slow
  (under 5°/s).
- **Detail inserts:** 50–85 mm, still level (Rule 1), shallow depth of field (f/2–f/4) on materials and
  hardware. One insert every 3–4 shots gives the edit rhythm. The house film's walnut slat insert is an example.
  Wider shots stay at f/5.6–f/11 so the architecture stays sharp.
- **Bokeh:** set `dof.aperture_blades` to 7–9 and a small `aperture_rotation`; round bokeh from blades = 0 reads
  as CG.
- **Motion blur on:** `render.use_motion_blur = True`, `motion_blur_shutter = 0.5` (180°). Without it, linear camera
  moves strobe.
- **Handheld life (optional):** an `FModifierNoise` on the location f-curves only (0.5–2 mm amplitude, slow).
  Never put it on rotation, because Rule 1 locks the camera level.
- **Aspect ratio:** 16:9 per the directive. For marketing films, 2.39:1 is a valid option
  (the house film uses it); render 16:9 and crop, or set the resolution directly.

### 8.4 Light (get the values physical, then make it beautiful)

- **Sky:** `ShaderNodeTexSky` with `sky_type = 'MULTIPLE_SCATTERING'` for physically based daylight. Or an HDRI
  from Poly Haven (`bmodels.polyhaven`, checksum-locked, CC0) when real cloud and context reflections matter. Rotate
  the sun to the site's true north and a real date and time, and record both.
- **Color temperature:** set `light.use_temperature = True` and `light.temperature` in kelvin. That avoids
  hand-picked RGB: 2700–3000 K for residential, 3500 K for corridors (the directive's compression phase), 4000 K
  for back-of-house. Use `ShaderNodeBlackbody` for emissive fixtures, so a fixture's glow matches its light.
- **Real fixtures:** when the fixture schedule names a product, drive the area or spot light with that
  manufacturer's IES file (`ShaderNodeTexIES`). Wall-washer scallops are what make a corridor look real.
- **Exposure, not wattage:** balance a shot with `view_settings.exposure` (per shot, from the shot list's exposure
  trim) and `light.exposure`. Don't scale every light up.
- **Light linking:** `obj.light_linking.receiver_collection` / `blocker_collection` (Cycles) for a rim on one
  object or a kicker on the hero material without spilling everywhere. Use it sparingly and only in presentation
  scenes.
- **Light groups:** add `view_layer.lightgroups` (e.g. `sun`, `sky`, `interior`, `fixtures`) and set `obj.lightgroup`.
  The balance between day and fixtures can then be re-graded in post without re-rendering. It's the cheapest
  agency trick there is.
- **Noise control:** `cycles.use_light_tree` (on by default) for many fixtures. `cycles.use_guiding = True` (path
  guiding, CPU only) helps interiors lit through windows. `blur_glossy` at 0.5–1.0, caustics off
  (`caustics_reflective`/`caustics_refractive = False`) unless they're the subject.
- **Color views:** AgX "AgX - Medium High Contrast" is the default and verified. "AgX - Punchy" works for exterior
  dusk. "ACES 2.0" and "Khronos PBR Neutral" also exist in this build. Pick one per film and never mix them. Note
  that in 5.0.1 the look names carry the "AgX - " prefix.

### 8.5 Materials, scale and dressing

- **Albedo discipline:** the brightest real paint is about 0.8–0.85 linear albedo, so never use 1.0 white. Black
  materials stay at 0.02–0.04 or above. Concrete sits around 0.3–0.4 and wood around 0.2–0.45. Most "CG look"
  comes from albedos that are too bright or too saturated.
- **Real-world mapping:** for BIM without UVs, use box projection (`ShaderNodeTexImage.projection = 'BOX'`,
  `projection_blend` 0.1–0.2) in object or world space, in metres. `bmodels.polyhaven` already does this.
  Diagnostic check: a brick course is 75 mm with a 10 mm joint (UK/metric) or 2⅝" per course (US modular), and
  carpet tiles are 500–610 mm.
- **Break repetition:** use `ShaderNodeObjectInfo` → Random to vary hue, value and roughness by ±2–5% per object
  (doors, tiles, planks). Rotate and offset texture coordinates per object too.
- **Wear where it would really occur:** use `ShaderNodeAmbientOcclusion` or Pointiness (Cycles) for faint grime in
  corners and wear on edges. Keep it under 5% in a new building. "New construction" should look new, not dirty.
- **Glass:** model glazing with real thickness, IOR 1.5 and a faint green-blue tint. Use portals at window
  openings (the directive's Module C) instead of hiding glass from shadow rays, which leaks light.
- **People and life:** a few scaled, animated 3D people (licensed, e.g. Renderpeople or AXYZ anima), sitting or
  walking slowly, motion-blurred. Never more than the space would really hold. In occupied-building films, people
  must not suggest residents in unsafe positions near work zones.
- **Vegetation:** scatter with Geometry Nodes using Poly Haven or licensed plant assets, with density and scale
  variation (±15%), and wind as a slow noise on a GN rotation. See the `scenario-blender-geometry-nodes` skill.
- **Licensing:** record every downloaded asset's source, license and checksum (`bmodels.polyhaven` writes the lock
  for Poly Haven). Prefer CC0 (Poly Haven, ambientCG). Megascans/Fab and paid people libraries have
  per-project terms, so check them before they appear in a client deliverable.

### 8.6 Rendering pipeline

- **Profiles:** at least three (animatic, preview, final), like `PROFILES` in `cinema.py`. Benchmark one frame per
  shot before launching a sequence, and estimate total hours. `cinema.py --bench` is the example.
- **Final quality:** noise threshold 0.005–0.01 with enough max samples that the denoiser does little work. An
  over-denoised animation smears and flickers frame to frame. Keep `use_animated_seed = False` for stills; for
  animation, test both on a 2 s clip and look at the flicker.
- **`render.use_persistent_data = True`** for sequences (it keeps the BVH and textures between frames).
- **Render to EXR, grade later:** see 8.6a. Never bake a look into PNGs you can't re-grade.
- **Parallel GPUs:** one frame per worker with a claim file, like `claim_frames`/`check_claim` in `cinema.py`. The
  same Blender (5.0.1) and the same `uv.lock` on every worker, with the source scene hash recorded per frame.
- **Committed scenes stay self-contained:** pack textures, HDRIs and sounds before saving (`bm audit-blends`).

### 8.6a Studio EXR and AOV pipeline (tested on bpy 5.0.1, 2026-11-06)

Why it matters: when a client asks for "the oak floor 15% lighter, the brick warmer", Cryptomatte plus light
groups in a multilayer EXR sequence turn that into a compositor re-grade instead of a full Cycles re-render.
Depth, mist and normals give depth haze and relighting tricks in post.

What the tests on this repo's bpy 5.0.1 showed:

| Claim | Result |
|---|---|
| `file_format = 'OPEN_EXR_MULTILAYER'` | Fails on its own (`enum not found`). Set `image_settings.media_type = 'MULTI_LAYER_IMAGE'` first. |
| Half float corrupts Cryptomatte and depth | No. With `color_depth = '16'`, Blender 5 writes Combined and albedo as half, and Depth, Vector, Cryptomatte and the denoising normal and depth as 32-bit float on its own. |
| `DWAA` is safe for every pass | Not assumed. DWAA is lossy, and Blender applies it to every part of the file, Cryptomatte included. Use a lossless codec (`PIZ` or `ZIP`) whenever Cryptomatte, depth or vectors are in the file. Keep DWAA for beauty-only proxies. |
| Temporal denoising | `bpy.ops.cycles.denoise_animation` exists, but in 5.0.1 it needs Denoising Data, the Vector pass and `use_exr_interleave = True` (it can't read the default multi-part layout). With OIDN on CPU it is **not** temporal: a frame's result didn't change when its neighbour changed. Whether it is temporal with OptiX on an NVIDIA GPU is untested. Until it's shown, fight flicker with samples (noise threshold ≤ 0.01) and a light denoise, and check flicker in QC (8.8). |
| Vector pass with Cycles motion blur on | Cycles still writes a Vector pass. Its usefulness wasn't checked. Keep render-time motion blur for this repo's films: post vector blur smears transparency (x-ray sections, glass) and depth of field. |
| Persistent data saves 25–40% | Measured on the Highland cinema scene (lobby, CPU, 640 × 268, 8 samples): frames 2–5 took 33.6 s with it vs 44.7 s without (−25%); the first frame was slower (12.1 vs 9.4 s). The saving is the fixed per-frame sync and BVH cost, so it shrinks as a share at final sample counts. Only frames rendered in one process benefit. |
| `use_pass_cryptomatte_accurate`, `pass_cryptomatte_depth`, mist `falloff = 'QUADRATIC'` | All exist and work. |

The function, corrected for 5.0.1 and this repo:

```python
import bpy

def configure_studio_exr_pipeline_b5(scene=None, light_groups=None, mist=(2.0, 35.0)):
    scene = scene or bpy.context.scene
    vl = scene.view_layers[0]

    # Passes for grading, relighting and the (optional) animation denoiser
    for p in ("use_pass_combined", "use_pass_z", "use_pass_mist", "use_pass_normal", "use_pass_vector",
              "use_pass_diffuse_color", "use_pass_glossy_direct", "use_pass_emit", "use_pass_ambient_occlusion"):
        setattr(vl, p, True)
    vl.cycles.denoising_store_passes = True       # albedo, normal, depth for denoise_animation

    # Cryptomatte: per-object/material/asset mattes for revisions without re-rendering
    vl.use_pass_cryptomatte_object = True
    vl.use_pass_cryptomatte_material = True
    vl.use_pass_cryptomatte_asset = True
    vl.pass_cryptomatte_depth = 6
    vl.use_pass_cryptomatte_accurate = True

    # Light groups: re-balance sun/sky/interior/fixtures in post (the snippet's title promised them)
    for name, objects in (light_groups or {}).items():
        if name not in vl.lightgroups:
            vl.lightgroups.add(name=name)
        for o in objects:
            o.lightgroup = name

    # Mist for depth haze
    ms = scene.world.mist_settings
    ms.use_mist = True; ms.start, ms.depth = mist; ms.falloff = 'QUADRATIC'

    # Multilayer EXR, Blender 5 style
    ims = scene.render.image_settings
    ims.media_type = 'MULTI_LAYER_IMAGE'          # required before OPEN_EXR_MULTILAYER is accepted
    ims.file_format = 'OPEN_EXR_MULTILAYER'
    ims.color_depth = '16'                        # beauty half; data passes are float automatically
    ims.exr_codec = 'PIZ'                         # lossless: Cryptomatte, depth and vectors survive
    ims.use_exr_interleave = True                 # single-part layout that denoise_animation can read

    scene.render.use_persistent_data = True       # keep BVH and textures between frames
```

Use it in the final and uhd profiles only. Proof and animatic frames stay PNG. EXR sizes: a 4K multilayer frame
with these passes runs tens of MB, so budget the disk before a 600+ frame run (the Highland 4K PNGs were already
≈ 16 GB).

### 8.7 Post, sound and delivery

- **Grade:** a light touch. Slight lift in the shadows, protected highlights, a gentle vignette, and 1–2% film
  grain (it hides banding in skies and walls). Grade in Blender's compositor (5.0 node-group API) or in
  DaVinci Resolve (free) from the EXRs. The repo's `vision` group (OpenCV 4.10, numpy<2) handles scripted
  finishing, see `cinema_finish.py`.
- **Sound is half the film:** a score cut to the edit, room tone in every interior, and quiet foley for doors,
  footsteps, the elevator and the city. Agencies spend real money here. The repo has the `audio` group
  (`uv sync --group audio`: Piper TTS narration, SciPy) and `cinema_score.py` for an original score. Licensed music
  needs its license recorded with the deliverable.
- **Typography:** one typeface, generous tracking, a title and an end card, sparing lower-thirds. On every frame,
  the "illustrative, not a contract document" strip sits below the image, never over it.
- **Masters:** ProRes 422 HQ (FFmpeg codec `PRORES`) or DNxHR as the master. H.264 or H.265 at high bitrate (4K: about
  40–60 Mb/s) for review and web, plus a 1080p version for email and phones. Use Rec.709 or sRGB for every
  deliverable unless an HDR deliverable is explicitly ordered (`Rec.2100-PQ` exists in this build but needs an HDR
  grade). Files over 1 MB go to GitHub Releases (`bm publish`).

### 8.8 QC: automate the boring checks, look at everything else

On top of section 0 and section 7, run these on every rendered sequence, all from the repo with numpy/OpenCV:
- **Blank or black frames:** mean and std per frame, like the builder's `image_is_blank`.
- **Clipping:** the share of pixels at the top or bottom of the range per frame. Flag over 0.5% outside fixtures and
  windows.
- **Flicker:** the frame-to-frame change in mean luminance within a shot, and in a 64-px grid. A spike that isn't a
  cut is denoiser flicker or a missing frame.
- **Frame count and continuity:** every frame in every shot is present and in order, with the same resolution and
  source hash (no frame from an old scene version).
- **Then watch it** at full size, at real speed, with sound, on a reasonably calibrated display and on a phone.
  Write down which version you watched.

### 8.9 What makes a VDC film worth more than a beautiful one

Agencies sell beauty. This repo sells beauty that is true, and that is the premium:
- **Truth layer:** every film has a matching provenance pass (the review colors) of its key frames. Every visible
  assumed element is known, and it is listed in the deliverable README.
- **Construction storytelling:** use 4D sequences tied to the schedule (`cie` activities), existing and proposed
  as separate scenes cut together, X-ray and section reveals of concealed conditions (Module B, gold cut faces),
  exploded axonometrics for trade sequence, and animated callouts that cite the drawing (sheet and detail) next to
  the thing they label.
- **Occupied buildings:** show protection, egress and the work zone as their own collection; residents should
  be able to read "where, when, how long" in one shot.
- **Never fake it to make it pretty.** No moved walls for a better composition, no invented windows for light, no
  removed structure that's really there. If a shot needs it, it's a different shot.

### 8.10 Tools at a glance

| Tool | Use | Status here |
|---|---|---|
| `bmodels.polyhaven` + `assets/hdri` | CC0 textures, models and HDRIs, checksum-locked, box-projected | in repo |
| `vision` group (OpenCV 4.10) | finishing, QC metrics, review sheets | installed by default |
| `audio` group (Piper TTS, SciPy) | narration, generated score | `uv sync --group audio` |
| FFmpeg | encode ProRes/H.264/H.265, contact sheets | on PATH (`bm doctor`) |
| `ifcopenshell` | IFC import with GlobalIds | not installed: `uv add`, check numpy<2 |
| Bonsai (Blender extension) | IFC authoring/import inside Blender | not installed; extensions install via `bpy.ops.extensions`, verify headless first |
| Speckle connector | live Revit/Rhino → Blender | external, not set up |
| DaVinci Resolve (free) | edit, grade from EXR, ProRes masters | external app |
| Paid add-ons (e.g. Photographer, Geo-Scatter, Gaffer) | GUI conveniences for exposure, scatter and light management | optional; bake their results into the `.blend` and never make a headless step depend on them |
| Licensed people (Renderpeople, AXYZ anima), Megascans/Fab | entourage, hero materials | paid; record the license per deliverable |
