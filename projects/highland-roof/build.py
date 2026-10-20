"""Save corrected day/dusk scenes, portable geometry and source-bounded evidence."""
import hashlib
import json
import math
from pathlib import Path

import bpy
from mathutils import Matrix, Vector
from bpy_extras.object_utils import world_to_camera_view

from geometry import apply_geometry, inventory, digest

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
OUT = ROOT/"deliverables/highland-roof"


def layer_named(root, name):
    if root.name == name:
        return root
    for child in root.children:
        found = layer_named(child, name)
        if found:
            return found
    return None


def caption(scene, camera, name, notice):
    collection = bpy.data.collections.new(name)
    scene.collection.children.link(collection)
    hw = camera.data.sensor_width/camera.data.lens
    vh = hw*scene.render.resolution_y/scene.render.resolution_x
    for body, size, y in (("200 WEST HIGHLAND / GEOMETRY REVISION 03", .019, -.435), (notice, .011, -.463)):
        data = bpy.data.curves.new(body, "FONT")
        data.body = body
        data.size = vh*size
        obj = bpy.data.objects.new(body, data)
        collection.objects.link(obj)
        obj.parent = camera
        obj.location = (-hw*.465, vh*y, -1)
        obj.visible_shadow = False
        data.materials.append(bpy.data.materials["Typography / ivory"])
        obj["status"] = "assumed"
        obj["source"] = "Presentation specification / revision 03"
        obj["basis"] = "Presentation caption and source-limit notice."
    return collection


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    cfg = json.loads((HERE/"geometry.json").read_text())
    spec = json.loads((HERE/"geometry-revision.spec.json").read_text())
    visual = json.loads((HERE/"presentation.json").read_text())
    fit = json.loads((OUT/"camera-fit.json").read_text())
    source = ROOT/cfg["base_blend"]
    bpy.context.preferences.filepaths.use_scripts_auto_execute = False
    bpy.ops.wm.open_mainfile(filepath=str(source), load_ui=False, use_scripts=False)
    day = bpy.context.scene
    geometry = apply_geometry(cfg, spec)
    for obj in day.objects:
        if obj.type == "FONT":
            obj.hide_render = True
    day.name = visual["day_scene"]
    camera = day.camera
    camera.name = visual["day_camera"]
    camera.location = fit["position_m"]
    camera.data.lens = fit["lens_mm"]
    yaw, pitch, roll = fit["yaw_pitch_roll_radians"]
    forward = Vector((-math.sin(yaw)*math.cos(pitch), math.cos(yaw)*math.cos(pitch), math.sin(pitch)))
    right = Vector((math.cos(yaw), math.sin(yaw), 0))
    up = right.cross(forward)
    r = right*math.cos(roll)+up*math.sin(roll)
    u = up*math.cos(roll)-right*math.sin(roll)
    camera.rotation_euler = Matrix((r, u, -forward)).transposed().to_euler()
    day.render.resolution_x, day.render.resolution_y = visual["day_resolution"]
    day.render.resolution_percentage = 100
    day.cycles.samples = visual["day_samples"]
    day.cycles.adaptive_threshold = visual["day_adaptive_threshold"]
    day.cycles.adaptive_min_samples = 8
    day.render.filepath = "//Highland-daylight-geometry-revised.png"
    day_titles = caption(day, camera, "Revision 03 / daylight titles", visual["notice"])

    night = day.copy()
    night.name = visual["night_scene"]
    night.camera = bpy.data.objects[visual["night_camera"]]
    night.compositing_node_group = day.compositing_node_group.copy()
    for node in night.compositing_node_group.nodes:
        if node.bl_idname == "CompositorNodeRLayers":
            node.scene = night
    night.render.resolution_x, night.render.resolution_y = visual["film_resolution"]
    night.render.resolution_percentage = 100
    night.render.fps = visual["film_fps"]
    night.frame_start, night.frame_end = 1, visual["film_frames"]
    night.render.filepath = "//native-dusk/frame-"
    layer_named(night.view_layers[0].layer_collection, "Presentation / lighting").exclude = False
    layer_named(night.view_layers[0].layer_collection, "Daylight / sun").exclude = True
    layer_named(night.view_layers[0].layer_collection, "Daylight / dry site surfaces").exclude = True
    layer_named(night.view_layers[0].layer_collection, "Site").exclude = False
    layer_named(night.view_layers[0].layer_collection, day_titles.name).exclude = True
    world = bpy.data.worlds.new("Dusk 03 / packed sky")
    world.use_nodes = True
    night.world = world
    n, links = world.node_tree.nodes, world.node_tree.links
    environment = n.new("ShaderNodeTexEnvironment")
    environment.image = next(image for image in bpy.data.images if image.name.endswith("_4k.hdr") and image.packed_file)
    coords, mapping = n.new("ShaderNodeTexCoord"), n.new("ShaderNodeMapping")
    mapping.inputs["Rotation"].default_value[2] = math.radians(125)
    links.new(coords.outputs["Generated"], mapping.inputs["Vector"])
    links.new(mapping.outputs[0], environment.inputs["Vector"])
    tint = n.new("ShaderNodeMixRGB")
    tint.blend_type = "MULTIPLY"
    tint.inputs[0].default_value = .68
    tint.inputs[2].default_value = (.4, .56, 1, 1)
    links.new(environment.outputs[0], tint.inputs[1])
    background = n.get("Background")
    background.inputs["Strength"].default_value = .20
    links.new(tint.outputs[0], background.inputs["Color"])
    lamp_collection = bpy.data.collections.new("Dusk 03 / warm visible lamps")
    night.collection.children.link(lamp_collection)
    materials = {}
    for name, strength in (("Street / warm opal", 4), ("Room / warm lampshade", 1.8)):
        material = bpy.data.materials[name].copy()
        material.name = "Dusk 03 / "+name
        material.node_tree.nodes.get("Principled BSDF").inputs["Emission Strength"].default_value = strength
        materials[name] = material
    for obj in list(night.objects):
        if obj.type != "MESH" or not any(mat and mat.name in materials for mat in obj.data.materials):
            continue
        copy = obj.copy()
        copy.data = obj.data.copy()
        copy.name = "Dusk 03 / "+obj.name
        for i, material in enumerate(copy.data.materials):
            if material and material.name in materials:
                copy.data.materials[i] = materials[material.name]
        lamp_collection.objects.link(copy)
        obj.hide_set(True, view_layer=night.view_layers[0])
    bpy.context.window.scene = night
    night.frame_set(145)
    caption(night, night.camera, "Revision 03 / dusk titles", visual["notice"])

    architecture = [obj for name in ("Envelope", "Glazing", "Balconies", "Roof") for obj in bpy.data.collections[name].objects if obj.type == "MESH"]
    corners = [obj.matrix_world@Vector(v) for obj in architecture for v in obj.bound_box]
    lo = Vector([min(v[k] for v in corners) for k in range(3)])
    hi = Vector([max(v[k] for v in corners) for k in range(3)])
    envelope = [Vector((x, y, z)) for x in (lo.x, hi.x) for y in (lo.y, hi.y) for z in (lo.z, hi.z)]
    camera_path = []
    minimum_margin = 1
    for frame in range(1, visual["film_frames"]+1):
        night.frame_set(frame)
        projected = [world_to_camera_view(night, night.camera, p) for p in envelope]
        margin = min(min(p.x, p.y, 1-p.x, 1-p.y) for p in projected)
        minimum_margin = min(minimum_margin, margin)
        assert margin > .015, (frame, margin)
        direction = night.camera.rotation_euler.to_quaternion()@Vector((0, 0, -1))
        camera_path.append({"frame": frame, "time": (frame-1)/24,
                            "position_m": list(night.camera.location),
                            "target_m": list(night.camera.location+direction*100),
                            "vertical_fov_degrees": math.degrees(2*math.atan((night.camera.data.sensor_width/night.camera.data.lens/2)*1080/1920))})
    night.frame_set(145)
    bpy.context.window.scene = day
    bpy.context.view_layer.update()
    projection_errors = []
    for item in fit["landmarks"]:
        p = world_to_camera_view(day, day.camera, Vector(item["position_m"]))
        projection_errors.append(math.dist([p.x*665, (1-p.y)*441], item["projected_pixel"]))
    assert max(projection_errors) < .001
    for scene in (day, night):
        missing = [obj.name for obj in scene.objects if obj.type in ("MESH", "CURVE") and not all(obj.get(k) for k in ("source", "status", "basis"))]
        assert not missing, missing[:10]
        scene["geometry_spec"] = "projects/highland-roof/geometry-revision.spec.json"
        scene["architecture_inventory_sha256"] = geometry["after_inventory_sha256"]
    for node in day.compositing_node_group.nodes:
        if node.bl_idname == "CompositorNodeRLayers":
            node.scene = day
    assert inventory() == geometry["after"]
    bpy.ops.file.pack_all()
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/"Highland-roof-and-terrace-revised.blend"))
    bpy.context.window.scene = night
    bpy.ops.object.select_all(action="DESELECT")
    for obj in night.objects:
        if obj.type in ("MESH", "CURVE") and not obj.hide_render and obj.visible_get():
            obj.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(OUT/"Highland-geometry-revised.glb"), export_format="GLB", use_selection=True,
                              export_extras=True, export_animations=False, export_cameras=False, export_lights=False)
    geometry["base_blend_sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
    (OUT/"geometry-validation.json").write_text(json.dumps(geometry, indent=2)+"\n")
    (OUT/"camera-path.json").write_text(json.dumps(camera_path, indent=2)+"\n")
    report = {"opening_count": len(spec["openings"]), "remaining_unresolved_candidates": len(spec["rejected_candidates"]),
              "camera_frames_checked": 432, "minimum_frame_margin": minimum_margin,
              "camera_fit_projection_max_error_px": max(projection_errors),
              "lit_window_ids": [obj.name.split(" / ", 1)[-1] for obj in night.objects if obj.type == "LIGHT" and obj.name.startswith("Apartment warm light / ")],
              "film_dimensions": [1920, 1080], "duration_seconds": 18, "fps": 24,
              "geometry_inventory_sha256": geometry["after_inventory_sha256"], "visual_review": "See visual-review.json for the exact reviewed outputs."}
    (OUT/"revision-validation.json").write_text(json.dumps(report, indent=2)+"\n")
    print(json.dumps({"before_meshes": geometry["before_meshes"], "after_meshes": geometry["after_meshes"],
                      "unchanged_meshes": geometry["unchanged_meshes"], "split_headers": geometry["split_wall_headers"],
                      "film_minimum_margin": minimum_margin}, indent=2), flush=True)


if __name__ == "__main__":
    main()
