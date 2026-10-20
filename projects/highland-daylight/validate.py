"""Read back the delivered scene and inspect real image/source invariants."""
import hashlib
import json
import struct
from pathlib import Path

import bpy
from PIL import Image, ImageStat
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

from build import architecture_hash

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "deliverables/highland-daylight"


def main():
    report = json.loads((OUT/"scene-validation.json").read_text())
    baseline = json.loads((ROOT/"deliverables/highland-refined/scene-readback.json").read_text())
    fit = json.loads((OUT/"camera-fit.json").read_text())
    audit = json.loads((OUT/"opening-audit.json").read_text())
    native = OUT/"Highland-daylight-photo-study.blend"
    bpy.ops.wm.open_mainfile(filepath=str(native), load_ui=False, use_scripts=False)
    scene = bpy.context.scene
    digest, count = architecture_hash()
    assert len(bpy.data.scenes) == 1
    assert digest == baseline["revised_architecture_sha256"] == report["architecture_before_sha256"]
    assert count == 955
    assert hashlib.sha256((ROOT/report["source_blend"]).read_bytes()).hexdigest() == report["source_blend_sha256"]
    assert scene.camera.animation_data is None
    assert scene.camera.data.animation_data is None
    assert scene.camera.data.sensor_fit == "HORIZONTAL"
    assert all(n.scene == scene for n in scene.compositing_node_group.nodes if n.bl_idname == "CompositorNodeRLayers")
    external = [i.filepath for i in bpy.data.images if i.source == "FILE" and i.users and not i.packed_file]
    assert not external, external
    untagged = [o.name for o in scene.objects if o.type in ("MESH", "CURVE") and not all(o.get(k) for k in ("source", "status", "basis"))]
    assert not untagged, untagged
    errors = []
    for point in fit["landmarks"]:
        p = world_to_camera_view(scene, scene.camera, Vector(point["position_m"]))
        pixel = [p.x*fit["image_size"][0], (1-p.y)*fit["image_size"][1]]
        errors.append(sum((a-b)**2 for a, b in zip(pixel, point["projected_pixel"]))**.5)
    assert max(errors) < .001
    assert audit["opening_inventory"] == 175 and audit["remaining_unresolved"] == 16
    projections = [world_to_camera_view(scene, scene.camera, obj.matrix_world@Vector(corner))
                   for name in ("Envelope", "Glazing", "Balconies", "Roof")
                   for obj in bpy.data.collections[name].objects if obj.type == "MESH"
                   for corner in obj.bound_box]
    frame_margin = min(min(p.x, p.y, 1-p.x, 1-p.y) for p in projections)
    assert frame_margin > .005, frame_margin
    glb = OUT/"Highland-daylight-photo-study.glb"
    binary = glb.read_bytes()
    magic, version, length = struct.unpack_from("<4sII", binary)
    assert magic == b"glTF" and version == 2 and length == len(binary)
    chunk_length, chunk_type = struct.unpack_from("<I4s", binary, 12)
    assert chunk_type == b"JSON"
    document = json.loads(binary[20:20+chunk_length])
    mesh_nodes = [n for n in document["nodes"] if "mesh" in n]
    untagged_glb = [n.get("name") for n in mesh_nodes
                    if not all(n.get("extras", {}).get(k) for k in ("status", "source", "basis"))]
    assert not untagged_glb, untagged_glb[:10]
    assert len(mesh_nodes) >= count
    protected_names = {obj.name for name in ("Envelope", "Glazing", "Balconies", "Roof")
                       for obj in bpy.data.collections[name].objects if obj.type == "MESH"}
    assert protected_names <= {node.get("name") for node in mesh_nodes}
    still = OUT/"Highland-daylight-photo-study.png"
    with Image.open(still) as im:
        assert im.size == tuple(report["resolution"])
        im.load()
        variation = max(ImageStat.Stat(im.convert("RGB").resize((128, 128))).stddev)/255
        assert variation > .03
    result = {"native_readback": True, "single_daylight_scene": True,
              "protected_architectural_meshes": count, "architecture_sha256": digest,
              "matches_original_handoff_geometry": True, "original_handoff_file_unchanged": True,
              "external_images_required": external, "untagged_geometry": untagged,
              "maximum_camera_projection_error_px": max(errors), "opening_inventory": 175,
              "remaining_unresolved": 16, "image_dimensions": report["resolution"],
              "architectural_frame_margin": frame_margin, "glb_mesh_nodes": len(mesh_nodes),
              "glb_untagged_mesh_nodes": untagged_glb, "glb_sha256": hashlib.sha256(binary).hexdigest(),
              "pixel_standard_deviation": round(variation, 6), "visual_review": "See visual-review.json",
              "still_sha256": hashlib.sha256(still.read_bytes()).hexdigest(),
              "native_sha256": hashlib.sha256(native.read_bytes()).hexdigest(),
              "scope": "Portability, image and consistency checks; no new dimensional accuracy claim."}
    (OUT/"delivery-validation.json").write_text(json.dumps(result, indent=2)+"\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
