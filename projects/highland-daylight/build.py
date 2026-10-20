"""Create a separate, source-preserving daylight revision from the packed handoff."""
import argparse
import hashlib
import json
import math
import random
import time
from pathlib import Path

import bpy
from mathutils import Matrix, Vector
from bpy_extras.object_utils import world_to_camera_view

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
OUT = ROOT / "deliverables/highland-daylight"
ARCHITECTURE = ("Envelope", "Glazing", "Balconies", "Roof")


def architecture_hash():
    digest = hashlib.sha256()
    count = 0
    for name in ARCHITECTURE:
        for obj in sorted(bpy.data.collections[name].objects, key=lambda o: o.name):
            if obj.type != "MESH":
                continue
            record = [obj.name, [list(row) for row in obj.matrix_world],
                      [list(v.co) for v in obj.data.vertices], [list(p.vertices) for p in obj.data.polygons]]
            digest.update(json.dumps(record, separators=(",", ":")).encode())
            count += 1
    return digest.hexdigest(), count


def tag(obj, basis):
    obj["status"] = "assumed"
    obj["source"] = "Owner photo-02 / projects/highland-daylight/daylight.json"
    obj["basis"] = basis
    return obj


def plant(config, collection, rng, index):
    """Folded individual leaves and pale flower clusters; no opaque canopy shell."""
    vertices, faces, colors = [], [], []
    center = Vector(config["center_m"])
    radius, height = config["radius_m"], config["height_m"]
    for _ in range(4000):
        z = rng.uniform(.15, height)
        width = radius * math.sqrt(max(.08, 1-((z/height-.5)*1.7)**2))
        a = rng.uniform(0, math.tau)
        r = width * math.sqrt(rng.uniform(.25, 1))
        point = center + Vector((math.cos(a)*r, math.sin(a)*r, z))
        u = Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-.55, .55))).normalized()
        v = u.cross(Vector((.1, .2, 1))).normalized()
        length = rng.uniform(.075, .15)
        k = len(vertices)
        vertices.extend([point-u*length/2, point+v*length*.25,
                         point+u*length/2, point-v*length*.25,
                         point+Vector((0, 0, length*.07))])
        faces.extend([(k+4, k+j, k+(j+1)%4) for j in range(4)])
        color = rng.choices(range(5), [3, 5, 4, 2, .8 if z > height*.6 else 0])[0]
        colors.extend([color]*4)
    mesh = bpy.data.meshes.new(f"Layered terrace shrub {index:02}")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(mesh.name, mesh)
    collection.objects.link(obj)
    for name in ("Botanical / leaf 0", "Botanical / leaf 1", "Botanical / leaf 2", "Botanical / leaf 3", "Daylight / pale flowers"):
        mesh.materials.append(bpy.data.materials[name])
    for face, color in zip(mesh.polygons, colors):
        face.material_index = color
        face.use_smooth = True
    return obj


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preview", action="store_true")
    parser.add_argument("--build-only", action="store_true")
    args = parser.parse_args()
    started = time.monotonic()
    OUT.mkdir(parents=True, exist_ok=True)
    config = json.loads((HERE / "daylight.json").read_text())
    fit = json.loads((OUT / "camera-fit.json").read_text())
    bpy.context.preferences.filepaths.use_scripts_auto_execute = False
    bpy.ops.wm.open_mainfile(filepath=str(ROOT / config["source_blend"]), load_ui=False, use_scripts=False)
    scene = bpy.data.scenes[config["source_scene"]]
    bpy.context.window.scene = scene
    before_hash, before_count = architecture_hash()
    for other in list(bpy.data.scenes):
        if other != scene:
            bpy.data.scenes.remove(other)
    scene.name = config["scene_name"]
    for node in scene.compositing_node_group.nodes:
        if node.bl_idname == "CompositorNodeRLayers":
            node.scene = scene
    for obj in scene.objects:
        if obj.type == "FONT":
            obj.hide_render = True
    camera = scene.camera
    camera.name = "Photo reference / fitted pinhole camera"
    camera.animation_data_clear()
    camera.data.animation_data_clear()
    camera.data.sensor_fit = "HORIZONTAL"
    camera.data.sensor_width = 36
    camera.data.lens = fit["lens_mm"]
    camera.data.shift_x = camera.data.shift_y = 0
    camera.location = fit["position_m"]
    yaw, pitch, roll = fit["yaw_pitch_roll_radians"]
    forward = Vector((-math.sin(yaw)*math.cos(pitch), math.cos(yaw)*math.cos(pitch), math.sin(pitch)))
    right = Vector((math.cos(yaw), math.sin(yaw), 0))
    up = right.cross(forward)
    r = right*math.cos(roll) + up*math.sin(roll)
    u = up*math.cos(roll) - right*math.sin(roll)
    camera.rotation_euler = Matrix((r, u, -forward)).transposed().to_euler()
    camera.data.dof.use_dof = False

    # Keep model dimensions and every architectural vertex/transform intact.
    for axis in ("x", "y"):
        mat = bpy.data.materials["brick-"+axis]
        for node in mat.node_tree.nodes:
            if node.bl_idname == "ShaderNodeTexBrick":
                for socket, key in (("Color1", "color_1"), ("Color2", "color_2"), ("Mortar", "mortar"),
                                    ("Brick Width", "width_m"), ("Row Height", "course_m"), ("Mortar Size", "mortar_m")):
                    node.inputs[socket].default_value = config["brick"][key]
            if node.bl_idname == "ShaderNodeMixRGB" and node.blend_type == "MULTIPLY":
                node.inputs[0].default_value = .10
    for name, color in (("concrete", config["concrete_color"]), ("metal", config["rooftop_metal_color"])):
        mat = bpy.data.materials[name]
        mat.node_tree.nodes.get("Principled BSDF").inputs["Base Color"].default_value = color
        mat.diffuse_color = color
    glass = bpy.data.materials["glass"].node_tree.nodes.get("Principled BSDF")
    glass.inputs["Roughness"].default_value = .065
    glass.inputs["IOR"].default_value = 1.5
    curtain_hidden = []
    for obj in scene.objects:
        if obj.name.startswith("Linen folds / ") and sum(map(ord, obj.name.split(" / ")[-1].split(".")[0])) % 3:
            obj.hide_render = True
            curtain_hidden.append(obj.name)
    for name in ("Street / warm opal", "Room / warm lampshade"):
        bpy.data.materials[name].node_tree.nodes.get("Principled BSDF").inputs["Emission Strength"].default_value = 0

    world = bpy.data.worlds.new("Daylight / clear sky study")
    world.use_nodes = True
    scene.world = world
    nodes, links = world.node_tree.nodes, world.node_tree.links
    sky = nodes.new("ShaderNodeTexSky")
    sky.sky_type = "MULTIPLE_SCATTERING"
    sky.sun_disc = False
    sky.sun_elevation = math.atan2(1, math.hypot(.4, .55))
    sky.sun_rotation = math.atan2(-.55, -.4)
    sky.air_density = 1.0
    sky.aerosol_density = .35
    sky.ozone_density = 1.0
    background = nodes.get("Background")
    background.inputs["Strength"].default_value = config["sky_strength"]
    links.new(sky.outputs[0], background.inputs["Color"])
    # The source photograph has a deep clear sky. Use a simple blue gradient
    # for camera/reflection rays, while the procedural sky supplies diffuse
    # illumination. Both are explicit presentation choices in the saved nodes.
    coords = nodes.new("ShaderNodeTexCoord")
    separate = nodes.new("ShaderNodeSeparateXYZ")
    links.new(coords.outputs["Normal"], separate.inputs[0])
    gradient = nodes.new("ShaderNodeValToRGB")
    gradient.color_ramp.elements[0].position = 0
    gradient.color_ramp.elements[0].color = config["visible_sky_horizon"]
    gradient.color_ramp.elements[1].position = .65
    gradient.color_ramp.elements[1].color = config["visible_sky_zenith"]
    links.new(separate.outputs["Z"], gradient.inputs[0])
    visible = nodes.new("ShaderNodeBackground")
    visible.name = "Interpreted clear sky / camera and reflections"
    visible.inputs["Strength"].default_value = .8
    links.new(gradient.outputs["Color"], visible.inputs["Color"])
    path = nodes.new("ShaderNodeLightPath")
    ray = nodes.new("ShaderNodeMath")
    ray.operation = "MAXIMUM"
    links.new(path.outputs["Is Camera Ray"], ray.inputs[0])
    links.new(path.outputs["Is Glossy Ray"], ray.inputs[1])
    mix = nodes.new("ShaderNodeMixShader")
    links.new(ray.outputs[0], mix.inputs[0])
    links.new(background.outputs[0], mix.inputs[1])
    links.new(visible.outputs[0], mix.inputs[2])
    links.new(mix.outputs[0], nodes.get("World Output").inputs["Surface"])
    sun = bpy.data.objects["Daylight key"]
    sun.data.energy = config["sun_energy"]
    sun.data.color = config["sun_color"]
    sun.data.angle = math.radians(1.1)
    scene.view_settings.exposure = config["exposure"]
    scene.view_settings.look = "AgX - Medium High Contrast"

    collection = bpy.data.collections.new("Daylight / interpreted terrace planting")
    scene.collection.children.link(collection)
    flower = bpy.data.materials.new("Daylight / pale flowers")
    flower.use_nodes = True
    flower.node_tree.nodes.get("Principled BSDF").inputs["Base Color"].default_value = (.71, .65, .43, 1)
    flower.node_tree.nodes.get("Principled BSDF").inputs["Roughness"].default_value = .8
    rng = random.Random(config["seed"])
    for i, shrub in enumerate(config["shrubs"]):
        tag(plant(shrub, collection, rng, i), config["planting_basis"])

    scene.render.resolution_x, scene.render.resolution_y = config["resolution"]
    scene.render.resolution_percentage = 50 if args.preview else 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 16 if args.preview else config["samples"]
    scene.cycles.adaptive_threshold = .045 if args.preview else .025
    scene.cycles.use_denoising = True
    scene.cycles.seed = config["seed"]
    scene.render.threads_mode = "FIXED"
    scene.render.threads = 3
    scene.render.film_transparent = False
    scene.render.use_border = False
    scene.render.pixel_aspect_x = scene.render.pixel_aspect_y = 1
    caption_collection = bpy.data.collections.new("Daylight / revision notice")
    scene.collection.children.link(caption_collection)
    hw = 36 / camera.data.lens
    vh = hw * scene.render.resolution_y/scene.render.resolution_x
    for body, size, y in (("200 WEST HIGHLAND / DAYLIGHT STUDY", .019, -.435),
                           (config["notice"], .011, -.463)):
        data = bpy.data.curves.new(body, "FONT")
        data.body = body
        data.size = vh*size
        obj = bpy.data.objects.new(body, data)
        caption_collection.objects.link(obj)
        obj.parent = camera
        obj.location = (-hw*.465, vh*y, -1)
        obj.visible_shadow = False
        data.materials.append(bpy.data.materials["Typography / ivory"])
        tag(obj, "Presentation caption identifying the revision and assumptions.")
    bpy.context.view_layer.update()
    after_hash, after_count = architecture_hash()
    assert (before_hash, before_count) == (after_hash, after_count)
    assert before_count == 955
    projection_errors = []
    for landmark in fit["landmarks"]:
        p = world_to_camera_view(scene, camera, Vector(landmark["position_m"]))
        pixel = [p.x*fit["image_size"][0], (1-p.y)*fit["image_size"][1]]
        projection_errors.append(math.dist(pixel, landmark["projected_pixel"]))
    assert max(projection_errors) < .001, projection_errors
    untagged = [o.name for o in scene.objects if o.type in ("MESH", "CURVE") and not all(o.get(k) for k in ("source", "status", "basis"))]
    assert not untagged, untagged
    filename = "Highland-daylight-preview.png" if args.preview else "Highland-daylight-photo-study.png"
    scene.render.filepath = "//"+filename
    scene["daylight_revision_config"] = "projects/highland-daylight/daylight.json"
    scene["camera_fit_basis"] = fit["scope"]
    bpy.ops.file.pack_all()
    bpy.context.preferences.filepaths.save_version = 0
    if not args.preview:
        bpy.ops.wm.save_as_mainfile(filepath=str(OUT / "Highland-daylight-photo-study.blend"))
    print(f"Verified {after_count} architectural meshes; saved camera agrees with the fit to {max(projection_errors):.6f} px.", flush=True)
    report = {"source_blend": config["source_blend"], "source_blend_sha256": hashlib.sha256((ROOT/config["source_blend"]).read_bytes()).hexdigest(),
              "architecture_before_sha256": before_hash, "architecture_after_sha256": after_hash,
              "architectural_geometry_preserved": True, "protected_architectural_meshes": after_count,
              "untagged_geometry": untagged, "blender_projection_max_error_px": max(projection_errors),
              "opening_count": 175, "unresolved_openings": 16,
              "added_shrubs": len(config["shrubs"]), "open_curtain_panels": len(curtain_hidden),
              "resolution": config["resolution"], "samples": scene.cycles.samples,
              "preview": args.preview, "visual_review": "pending"}
    if not args.build_only:
        scene.render.filepath = str(OUT / filename)
        print(f"Rendering {filename} / {scene.cycles.samples} samples / CPU.", flush=True)
        bpy.ops.render.render(write_still=True, scene=scene.name)
    if not args.preview:
        bpy.ops.object.select_all(action="DESELECT")
        for obj in scene.objects:
            if obj.type in ("MESH", "CURVE") and not obj.hide_render and obj.visible_get():
                obj.select_set(True)
        bpy.ops.export_scene.gltf(filepath=str(OUT/"Highland-daylight-photo-study.glb"),
                                  export_format="GLB", use_selection=True,
                                  export_extras=True, export_animations=False,
                                  export_cameras=False, export_lights=False)
    report["elapsed_seconds"] = round(time.monotonic()-started, 2)
    (OUT / ("preview-validation.json" if args.preview else "scene-validation.json")).write_text(json.dumps(report, indent=2)+"\n")
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()
