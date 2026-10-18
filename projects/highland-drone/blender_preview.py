"""Render a small, reproducible Cycles preview of the existing Highland exterior.

This is deliberately limited to the Blender exterior study. The corridor
walkthrough is built in Three.js and is not present in this .blend file.
"""

import argparse
import hashlib
import json
import time
from pathlib import Path

import bpy


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "deliverables/highland-exterior/Highland-exterior.blend"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "build/highland-blender-preview")
    parser.add_argument("--samples", type=int, default=16)
    parser.add_argument("--width", type=int, default=540)
    parser.add_argument("--height", type=int, default=960)
    args = parser.parse_args()
    if args.samples < 1 or args.width < 64 or args.height < 64:
        parser.error("Samples must be positive and dimensions at least 64 pixels")

    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
    scene = bpy.context.scene
    if scene.camera is None:
        raise RuntimeError(f"No render camera in {SOURCE}")
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = args.samples
    scene.cycles.use_denoising = True
    scene.render.threads_mode = "AUTO"
    scene.render.resolution_x = args.width
    scene.render.resolution_y = args.height
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.filepath = str(output / "highland-exterior-portrait.png")
    # Keep the saved review camera's focal length for a closer phone portrait.
    scene.camera.data.type = "PERSP"
    scene.camera.data.lens = 36
    for obj in bpy.data.objects:
        if obj.name.startswith("caption-") or obj.name == "caption backing":
            obj.hide_render = True
    bpy.ops.render.render(write_still=True)
    result = Path(scene.render.filepath)
    if not result.is_file() or result.stat().st_size < 1000:
        raise RuntimeError("Cycles did not produce a usable image")
    manifest = {
        "source": str(SOURCE.relative_to(ROOT)),
        "source_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        "blender": bpy.app.version_string,
        "engine": scene.render.engine,
        "device": scene.cycles.device,
        "samples": args.samples,
        "resolution": [args.width, args.height],
        "render_seconds": round(time.monotonic() - started, 1),
        "image": result.name,
        "scope": "Exterior study only; corridor interior remains a separate Three.js model.",
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
