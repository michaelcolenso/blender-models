#!/usr/bin/env python3
"""Blender-side build runner for the Meydenbauer B-101 v4 handoff.

Run from Blender, not system Python:
  blender --background --factory-startup --python scripts/run_build_and_verify.py -- [options]
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import runpy
import sys
import traceback
from datetime import datetime, timezone

import bpy

ROOT = Path(__file__).resolve().parents[1]
BUILD_SCRIPT = ROOT / "scripts" / "build_meydenbauer_b101_v4.py"
DEFAULT_BLEND = ROOT / "output" / "Meydenbauer_B101_Demolition_v4.blend"
DEFAULT_REPORT = ROOT / "output" / "build_validation_report.json"
DEFAULT_RENDERS = ROOT / "renders"

DEMO_FRAMES = {
    1: "existing",
    38: "remove_reinstall_access_items",
    50: "finish_stripout",
    61: "wall_stack_exposure",
    68: "slab_sawcut",
    76: "slab_lift_vapor_exposure",
    83: "excavation_expose_ci",
    89: "ci_removed_clean_trench",
}


def _args_after_dashdash():
    if "--" not in sys.argv:
        return []
    return sys.argv[sys.argv.index("--") + 1 :]


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--passes", default="1,2,3", help="Comma-separated pass list; default 1,2,3")
    p.add_argument("--blend", default=str(DEFAULT_BLEND), help="Output .blend path")
    p.add_argument("--report", default=str(DEFAULT_REPORT), help="JSON build report path")
    p.add_argument("--render-keyframes", action="store_true", help="Render the B-101 demolition checkpoints")
    p.add_argument("--render-dir", default=str(DEFAULT_RENDERS), help="Render output directory")
    p.add_argument("--resolution-x", type=int, default=1280)
    p.add_argument("--resolution-y", type=int, default=720)
    p.add_argument("--samples", type=int, default=32)
    p.add_argument("--fail-on-warning", action="store_true", help="Return nonzero if model validation emits any issue")
    return p.parse_args(_args_after_dashdash())


def choose_render_engine(scene):
    # Blender 4.x/5.x Eevee identifier, then older 3.x fallback, then Cycles.
    for engine in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE", "CYCLES"):
        try:
            scene.render.engine = engine
            return engine
        except Exception:
            pass
    return scene.render.engine


def summarize_scene(issues):
    scene = bpy.context.scene
    ctrl = bpy.data.objects.get("PHASE_CONTROLLER")
    collection_counts = {}
    for c in bpy.data.collections:
        collection_counts[c.name] = len(c.objects)

    role_counts = {}
    for o in bpy.data.objects:
        role = o.get("PHASE_ROLE") or o.get("DEMO_ROLE") or "UNCLASSIFIED"
        role_counts[role] = role_counts.get(role, 0) + 1

    named_expectations = [
        "PHASE_CONTROLLER",
        "BuildingB_SOG_5p5in",
        "B101_DEMO_PriorRepair_NoDemo_Envelope",
        "B101_DEMO_WCCarrier_North_CarrierBody",
        "B101_DEMO_WCCarrier_South_CarrierBody",
        "B101_DEMO_Cut_PriorABS_Tie",
        "B101_DEMO_Cut_Exterior6in_18inLimit",
        "MEYD_ISO_CAMERA",
    ]

    meyd_props = {}
    for k in scene.keys():
        if str(k).startswith("MEYD_"):
            v = scene[k]
            if isinstance(v, (str, int, float, bool)):
                meyd_props[k] = v

    return {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "blender_version": bpy.app.version_string,
        "blender_version_tuple": list(bpy.app.version),
        "blend_filepath": bpy.data.filepath,
        "object_count": len(bpy.data.objects),
        "collection_count": len(bpy.data.collections),
        "mesh_count": len(bpy.data.meshes),
        "curve_count": len(bpy.data.curves),
        "material_count": len(bpy.data.materials),
        "camera": scene.camera.name if scene.camera else None,
        "frame_start": scene.frame_start,
        "frame_end": scene.frame_end,
        "timeline_markers": {m.name: m.frame for m in scene.timeline_markers},
        "controller": ({
            "Construction_Phase": ctrl.get("Construction_Phase"),
            "Demolition_Subphase": ctrl.get("Demolition_Subphase"),
            "Alternate_1_Floor_Mounted_Toilets": ctrl.get("Alternate_1_Floor_Mounted_Toilets"),
            "Alternate_2_New_Bathtubs": ctrl.get("Alternate_2_New_Bathtubs"),
        } if ctrl else None),
        "expected_objects": {name: (bpy.data.objects.get(name) is not None) for name in named_expectations},
        "collection_object_counts": collection_counts,
        "role_counts": role_counts,
        "scene_metrics": meyd_props,
        "validation_issues": list(issues),
        "validation_passed": not issues,
    }


def render_checkpoints(args):
    render_dir = Path(args.render_dir)
    render_dir.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    engine = choose_render_engine(scene)
    scene.render.resolution_x = args.resolution_x
    scene.render.resolution_y = args.resolution_y
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    if hasattr(scene, "eevee") and hasattr(scene.eevee, "taa_render_samples"):
        scene.eevee.taa_render_samples = args.samples
    if hasattr(scene, "cycles"):
        scene.cycles.samples = args.samples
    results = []
    for frame, label in DEMO_FRAMES.items():
        scene.frame_set(frame)
        out = render_dir / f"B101_demo_{frame:03d}_{label}.png"
        scene.render.filepath = str(out)
        bpy.ops.render.render(write_still=True)
        results.append(str(out))
    scene.frame_set(1)
    return engine, results


def main():
    args = parse_args()
    passes = tuple(int(x.strip()) for x in args.passes.split(",") if x.strip())
    Path(args.blend).parent.mkdir(parents=True, exist_ok=True)
    Path(args.report).parent.mkdir(parents=True, exist_ok=True)

    report = {
        "runner": str(Path(__file__).resolve()),
        "build_script": str(BUILD_SCRIPT),
        "requested_passes": list(passes),
        "runtime_exception": None,
    }

    try:
        ns = runpy.run_path(str(BUILD_SCRIPT), run_name="meyd_build")
        ns["RUN_PASSES"] = passes
        ns["VALIDATE_AFTER_RUN"] = False
        ns["main"]()
        issues = ns["validate_model"]()

        bpy.context.scene.frame_set(1)
        bpy.ops.wm.save_as_mainfile(filepath=str(Path(args.blend).resolve()))

        render_engine = None
        render_files = []
        if args.render_keyframes:
            render_engine, render_files = render_checkpoints(args)
            bpy.context.scene.frame_set(1)
            bpy.ops.wm.save_as_mainfile(filepath=str(Path(args.blend).resolve()))

        report.update(summarize_scene(issues))
        report["saved_blend"] = str(Path(args.blend).resolve())
        report["render_engine"] = render_engine
        report["render_files"] = render_files
        report["build_completed"] = True

        Path(args.report).write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
        print(f"\nHANDOFF_BUILD_REPORT={Path(args.report).resolve()}")
        print(f"HANDOFF_BLEND={Path(args.blend).resolve()}")
        if args.fail_on_warning and issues:
            raise SystemExit(2)
        return 0
    except SystemExit:
        raise
    except Exception as exc:
        report["build_completed"] = False
        report["runtime_exception"] = repr(exc)
        report["traceback"] = traceback.format_exc()
        try:
            Path(args.report).write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
        except Exception:
            pass
        traceback.print_exc()
        raise SystemExit(1)


if __name__ == "__main__":
    main()
