"""Render native video frames from a signed plan, retaining the source rig."""
import argparse
import importlib.util
import json
import math
import shutil
import time
from pathlib import Path

from PIL import Image

from render_scene import configure_device, validate_image
from video_common import ROOT, digest, load_plan, materialize, signature
from video_graphics import compose


def studio_adapter():
    path = ROOT / "projects/highland-installation/studio-upgrade/render_studio.py"
    spec = importlib.util.spec_from_file_location("existing_studio_renderer", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def external_assets(bpy):
    """Check render data, excluding source-file paths retained as provenance metadata."""
    paths = set()
    for collection in (bpy.data.images, bpy.data.fonts, bpy.data.libraries,
                       bpy.data.sounds, bpy.data.movieclips, bpy.data.volumes, bpy.data.cache_files):
        for item in collection:
            path = getattr(item, "filepath", "")
            if not path or path == "<builtin>" or getattr(item, "packed_file", None):
                continue
            if getattr(item, "source", None) in ("GENERATED", "VIEWER"):
                continue
            paths.add(bpy.path.abspath(path, library=getattr(item, "library", None)))
    return sorted(paths)


def render(plan, output, chunk_id=None, plate_cache=None):
    import bpy

    if bpy.app.version_string != plan["blender_version"]:
        raise ValueError(f"Expected Blender {plan['blender_version']}; found {bpy.app.version_string}")
    chunks = [c for c in plan["chunks"] if chunk_id is None or c["id"] == chunk_id]
    if not chunks:
        raise ValueError(f"Unknown chunk: {chunk_id}")
    source = materialize(plan["model"]["blend"], plan["model"]["sha256"])
    bpy.context.preferences.filepaths.use_scripts_auto_execute = False
    bpy.ops.wm.open_mainfile(filepath=str(source), load_ui=False, use_scripts=False)
    missing = [p for p in external_assets(bpy) if not Path(p).is_file()]
    if missing:
        raise ValueError(f"Missing model dependencies: {missing}")
    adapter = studio_adapter()
    scenes = {}
    settings = plan["settings"]
    for alias in {f["scene"] for c in chunks for f in plan["frames"][c["first"]:c["last"]+1]}:
        entry = plan["model"]["scenes"][alias]
        scene = bpy.data.scenes.get(entry["name"])
        if scene is None:
            raise ValueError(f"Scene missing: {entry['name']}")
        if scene.render.fps / scene.render.fps_base != plan["model"]["source_fps"]:
            raise ValueError(f"Source scene FPS does not match its catalog entry: {scene.name}")
        camera = scene.objects.get(entry["camera"])
        if camera is None or camera.type != "CAMERA":
            raise ValueError(f"Camera missing: {entry['camera']}")
        scene.camera = camera
        scene.render.engine = "CYCLES"
        scene.render.use_sequencer = False
        scene.render.use_border = False
        scene.render.use_crop_to_border = False
        scene.render.resolution_x, scene.render.resolution_y = settings["width"], settings["height"]
        scene.render.resolution_percentage = 100
        scene.render.image_settings.file_format = "PNG"
        scene.render.image_settings.color_mode = "RGBA"
        scene.render.image_settings.color_depth = "8"
        # Combined PNG is the output; unused auxiliary passes only add work.
        for layer in scene.view_layers:
            layer.use_pass_ambient_occlusion = False
            layer.use_pass_shadow = False
            layer.cycles.use_pass_shadow_catcher = False
        scene.cycles.samples = settings["samples"]
        scene.cycles.use_adaptive_sampling = False
        scene.cycles.use_denoising = True
        scene.cycles.seed = 0
        scene.cycles.use_animated_seed = False
        configure_device(bpy, scene, plan["device"])
        scenes[alias] = scene
    frames_dir = output / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    plates_dir = plate_cache or output / "plates"
    plates_dir.mkdir(parents=True, exist_ok=True)
    (output / "plates").mkdir(exist_ok=True)
    for chunk in chunks:
        preferences = bpy.context.preferences.addons["cycles"].preferences
        report = {"chunk": chunk["id"], "plan_id": plan["plan_id"], "status": "failed", "frames": [],
                  "blender": bpy.app.version_string, "device": plan["device"],
                  "gpu_devices": [{"name": d.name, "type": d.type} for d in preferences.devices if d.use and d.type != "CPU"]}
        started = time.monotonic()
        try:
            for frame in plan["frames"][chunk["first"]:chunk["last"]+1]:
                index = frame["index"]
                target = frames_dir / f"f{index:06}.png"
                metadata = target.with_suffix(".json")
                if target.exists() or metadata.exists():
                    if not target.exists() or not metadata.exists():
                        raise ValueError(f"Incomplete cached frame: {index}; remove the incomplete pair and retry")
                    previous = json.loads(metadata.read_text())
                    if previous.get("plan_id") != plan["plan_id"] or previous.get("sha256") != digest(target):
                        raise ValueError(f"Cached frame {index} does not match this plan")
                    report["frames"].append(index)
                    continue
                scene = scenes[frame["scene"]]
                source_frame = 1 + frame["source_time"] * plan["model"]["source_fps"]
                if not scene.frame_start <= source_frame < scene.frame_end + 1:
                    raise ValueError(f"Source frame outside saved timeline: {source_frame}")
                bpy.context.window.scene = scene
                scene.frame_set(math.floor(source_frame), subframe=source_frame % 1)
                bpy.context.view_layer.update()
                plate_key = signature({"plate_id": plan["plate_id"], "scene": frame["scene"], "source_time": frame["source_time"]})
                raw_path = plates_dir / f"{plate_key}.png"
                plate_metadata = raw_path.with_suffix(".json")
                began = time.monotonic()
                if raw_path.exists() and plate_metadata.exists():
                    plate = json.loads(plate_metadata.read_text())
                    if plate.get("sha256") != digest(raw_path):
                        raise ValueError(f"Cached plate changed: {plate_key}")
                    checks = validate_image(raw_path, settings["width"], settings["height"])
                else:
                    scene.render.filepath = str(raw_path.resolve())
                    bpy.ops.render.render(write_still=True, scene=scene.name)
                    if bpy.app.autoexec_fail:
                        raise ValueError("Blocked Python driver/script; bake the source rig before rendering")
                    checks = validate_image(raw_path, settings["width"], settings["height"])
                    plate_metadata.write_text(json.dumps({"sha256": digest(raw_path), "raw_checks": checks}, indent=2) + "\n")
                if bpy.app.autoexec_fail:
                    raise ValueError("Blocked Python driver/script; bake the source rig before rendering")
                pins = adapter.pins(scene, frame["source_time"])
                with Image.open(raw_path) as raw:
                    image = compose(raw, plan, frame, pins)
                    image.save(target)
                metadata.write_text(json.dumps({**frame, "plan_id": plan["plan_id"], "sha256": digest(target),
                                                "raw_checks": checks, "device": plan["device"], "labels": pins,
                                                "plate_key": plate_key, "plate_sha256": digest(raw_path),
                                                "seconds": round(time.monotonic() - began, 3)}, indent=2) + "\n")
                if plates_dir.resolve() != (output / "plates").resolve():
                    shutil.copy2(raw_path, output / "plates" / raw_path.name)
                    shutil.copy2(plate_metadata, output / "plates" / plate_metadata.name)
                report["frames"].append(index)
                print(f"Rendered {frame['shot']} frame {index} at source {frame['source_time']:.3f}s", flush=True)
            report["status"] = "rendered"
        except Exception as error:
            report["error"] = str(error)
            raise
        finally:
            report["duration_seconds"] = round(time.monotonic() - started, 3)
            (output / f"{chunk['id']}.json").write_text(json.dumps(report, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--chunk")
    parser.add_argument("--plates", type=Path, help="Reuse a previous run's compatible raw image plates")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    render(load_plan(args.plan), args.output, args.chunk, args.plates)


if __name__ == "__main__":
    main()
