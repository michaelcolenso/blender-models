"""Render four source-provenance views and a fixed-camera before/after review."""
import json
from pathlib import Path

import bpy
from mathutils import Vector
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/"deliverables/highland-roof"
TRADES = ("Envelope", "Glazing", "Balconies", "Roof")


def render_review(native, prefix, full):
    bpy.ops.wm.open_mainfile(filepath=str(native), load_ui=False, use_scripts=False)
    scene = next(s for s in bpy.data.scenes if s.name.startswith("Daylight"))
    bpy.context.window.scene = scene
    architecture = {o for c in TRADES for o in bpy.data.collections[c].objects}
    for obj in scene.objects:
        if obj.type in ("MESH", "CURVE", "FONT") and obj not in architecture:
            obj.hide_render = True
    scene.compositing_node_group = None
    world = bpy.data.worlds.new("Review / neutral illumination")
    world.use_nodes = True
    world.node_tree.nodes.get("Background").inputs["Color"].default_value = (.6, .65, .7, 1)
    world.node_tree.nodes.get("Background").inputs["Strength"].default_value = .65
    scene.world = world
    scene.render.resolution_x, scene.render.resolution_y = 800, 600
    scene.render.resolution_percentage = 100
    scene.cycles.samples = 8
    scene.cycles.adaptive_min_samples = 4
    scene.view_settings.exposure = 0
    material = bpy.data.materials.new("Review / assumed complete components")
    material.use_nodes = True
    material.node_tree.nodes.get("Principled BSDF").inputs["Base Color"].default_value = (1, .24, .035, 1)
    scene.view_layers[0].material_override = material
    camera = scene.camera
    camera.data.type = "ORTHO"
    camera.data.shift_x = camera.data.shift_y = 0
    folder = OUT/"geometry-review"
    folder.mkdir(exist_ok=True)
    views = [("south", (18.5, -85, 11), (18.5, 22, 11), 47),
             ("east", (115, 22, 11), (18.5, 22, 11), 59),
             ("plan", (18.5, 22, 105), (18.5, 22, 0), 68),
             ("iso", (80, -80, 40), (18.5, 22, 10), 70)]
    if not full:
        views = views[:1]
    for name, location, target, scale in views:
        camera.location = location
        camera.rotation_euler = (Vector(target)-camera.location).to_track_quat("-Z", "Y").to_euler()
        camera.data.ortho_scale = scale
        destination = folder/f"{prefix}-{name}.png"
        scene.render.filepath = str(destination)
        bpy.ops.render.render(write_still=True, scene=scene.name)
        image = Image.open(destination).convert("RGB")
        footer = Image.new("RGB", (800, 638), "white")
        footer.paste(image)
        draw = ImageDraw.Draw(footer)
        draw.text((12, 610), f"{prefix} / {name} | Orange: complete components retain assumed geometry. Not a construction document.",
                  fill="#263943", font=ImageFont.load_default(size=12))
        footer.save(destination)
        print("REVIEW", prefix, name, flush=True)


def main():
    render_review(ROOT/"deliverables/highland-daylight/Highland-daylight-photo-study.blend", "before", False)
    render_review(OUT/"Highland-roof-and-terrace-revised.blend", "after", True)
    (OUT/"geometry-review.json").write_text(json.dumps({"views": ["south", "east", "plan", "iso"],
        "before_after_camera_identical": True, "provenance": "Complete components assumed / orange. Some separate datum properties are confirmed; provisional band heights do not confirm complete sections.",
        "visual_review": "See visual-review.json for the exact reviewed outputs."}, indent=2)+"\n")


if __name__ == "__main__":
    main()
