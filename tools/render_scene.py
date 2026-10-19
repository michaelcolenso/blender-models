"""Render a cataloged .blend scene using the pinned bpy Python runtime."""
import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageStat

from render_assets import validate_scene_assets
from render_plan import CATALOG, PROFILES, ROOT, load_shots, select_shots


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_image(path, width, height):
    with Image.open(path) as image:
        image.load()
        if image.size != (width, height):
            raise ValueError(f"Wrong image size: {image.size}, expected {(width, height)}")
        if image.convert("RGBA").getchannel("A").getextrema()[1] == 0:
            raise ValueError("Render is fully transparent")
        deviation = max(ImageStat.Stat(image.convert("RGB").resize((128, 128))).stddev) / 255
        if deviation < 0.003:
            raise ValueError("Render appears blank (near-uniform pixels)")
    return {"dimensions_ok": True, "nonblank": True, "pixel_stddev": round(deviation, 6)}


def add_notice(source, destination, notice):
    """Append a readable footer without covering model geometry or existing labels."""
    with Image.open(source) as image:
        image = image.convert("RGB")
        font = ImageFont.load_default(size=13)
        draw = ImageDraw.Draw(image)
        lines = []
        for text in ("Illustrative coordination model - field verification required.", notice):
            line = ""
            for word in text.split():
                candidate = f"{line} {word}".strip()
                if line and draw.textlength(candidate, font=font) > image.width - 24:
                    lines.append(line)
                    line = word
                else:
                    line = candidate
            lines.append(line)
        output = Image.new("RGB", (image.width, image.height + len(lines) * 18 + 16), "white")
        output.paste(image)
        draw = ImageDraw.Draw(output)
        for index, line in enumerate(lines):
            draw.text((12, image.height + 8 + index * 18), line, font=font, fill="#222222")
        output.save(destination)
        return list(output.size)


def configure_device(bpy, scene, backend):
    scene.cycles.device = "CPU"
    if backend == "CPU":
        return
    preferences = bpy.context.preferences.addons["cycles"].preferences
    preferences.compute_device_type = backend
    preferences.get_devices()
    found = False
    for device in preferences.devices:
        device.use = device.type == backend
        found |= device.use
    if not found:
        raise ValueError(f"No {backend} device found; refusing to fall back to CPU")
    scene.cycles.device = "GPU"


def render(args, report):
    import bpy

    if bpy.app.version_string != "5.0.1":
        raise ValueError(f"Expected Blender 5.0.1; found {bpy.app.version_string}")
    if args.shot == "all":
        raise ValueError("Render one shot ID at a time; use render_plan.py to expand 'all'")
    shot = select_shots(load_shots(args.catalog), args.shot)[0]
    model = ROOT / shot["blend"]
    report.update(shot=shot, blender=bpy.app.version_string, model_sha256=sha256(model))
    bpy.context.preferences.filepaths.use_scripts_auto_execute = False
    bpy.ops.wm.open_mainfile(filepath=str(model), load_ui=False, use_scripts=False)
    scene = bpy.data.scenes.get(shot["scene"])
    if scene is None:
        raise ValueError(f"Scene not found: {shot['scene']}")
    camera = scene.objects.get(shot["camera"])
    if camera is None or camera.type != "CAMERA":
        raise ValueError(f"Camera not found in scene: {shot['camera']}")
    if not scene.frame_start <= shot["frame"] <= scene.frame_end:
        raise ValueError(f"Frame {shot['frame']} is outside scene range {scene.frame_start}..{scene.frame_end}")
    # Packed data is covered by the .blend hash; hash ordinary external files too.
    dependencies = validate_scene_assets(bpy, scene)
    report["dependencies"] = [{"path": path, "sha256": sha256(path)} for path in dependencies]
    bpy.context.window.scene = scene
    scene.camera = camera
    scene.frame_set(shot["frame"])
    profile = PROFILES[args.profile]
    # Keep the authored camera framing, including portrait and wide shots.
    scale = profile["max_dimension"] / max(scene.render.resolution_x, scene.render.resolution_y)
    width = max(4, round(scene.render.resolution_x * scale))
    height = max(4, round(scene.render.resolution_y * scale))
    scene.render.engine = "CYCLES"
    configure_device(bpy, scene, args.device)
    scene.cycles.samples = profile["samples"]
    scene.cycles.use_adaptive_sampling = False
    scene.cycles.use_denoising = True
    scene.cycles.seed = 0
    scene.cycles.use_animated_seed = False
    scene.render.resolution_x = width
    scene.render.resolution_y = height
    scene.render.resolution_percentage = 100
    scene.render.use_border = False
    scene.render.use_crop_to_border = False
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.color_depth = "8"
    scene.render.use_file_extension = True
    scene.render.threads_mode = "AUTO"
    raw = args.output / "raw.png"
    scene.render.filepath = str(raw.resolve())
    bpy.context.view_layer.update()
    bpy.ops.render.render(write_still=True, scene=scene.name)
    if bpy.app.autoexec_fail:
        raise ValueError("Scene needs blocked Python scripts or drivers; bake them before CI rendering")
    report["checks"] = validate_image(raw, width, height)
    output = args.output / "render.png"
    report["output_size"] = add_notice(raw, output, shot["notice"])
    report["output_sha256"] = sha256(output)
    report["settings"] = {**profile, "width": width, "height": height,
                          "device": args.device, "seed": 0, "engine": "CYCLES"}
    report["status"] = "render_checks_passed"
    raw.unlink()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=CATALOG)
    parser.add_argument("--shot", required=True)
    parser.add_argument("--profile", choices=PROFILES, default="preview")
    parser.add_argument("--device", choices=("CPU", "CUDA", "OPTIX"), default="CPU")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    for filename in ("raw.png", "render.png"):
        (args.output / filename).unlink(missing_ok=True)
    report = {
        "status": "failed", "shot_id": args.shot, "profile": args.profile,
        "visual_review": "pending", "geometry_validation": "not performed by this render job",
        "commit": os.environ.get("GITHUB_SHA", "local"),
        "workflow_run": os.environ.get("GITHUB_RUN_ID", "local"),
    }
    started = time.monotonic()
    try:
        render(args, report)
    except Exception as error:
        report["error"] = str(error)
        print(f"Render failed: {error}", file=sys.stderr)
    report["duration_seconds"] = round(time.monotonic() - started, 2)
    (args.output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    lines = [
        f"## Render: {args.shot}", f"Status: {report['status']}",
        f"Profile: {args.profile}; device: {args.device}",
        "Visual review: pending. Geometry validation belongs to the source model's build checks.",
    ]
    if "error" in report:
        lines.append(f"Error: {report['error']}")
    if "shot" in report:
        lines.append(f"Model note: {report['shot']['notice']}")
    (args.output / "report.md").write_text("\n\n".join(lines) + "\n")
    return 0 if report["status"] == "render_checks_passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
