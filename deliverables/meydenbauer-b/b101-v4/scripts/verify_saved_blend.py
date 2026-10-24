#!/usr/bin/env python3
"""Reopen/persistence verification for a saved Meydenbauer .blend."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import runpy
import sys
from datetime import datetime, timezone
import bpy

ROOT = Path(__file__).resolve().parents[1]
BUILD_SCRIPT = ROOT / "scripts" / "build_meydenbauer_b101_v4.py"
DEFAULT_REPORT = ROOT / "output" / "saved_blend_verification.json"


def _args_after_dashdash():
    return sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []


def parse_args():
    p=argparse.ArgumentParser()
    p.add_argument("--report", default=str(DEFAULT_REPORT))
    p.add_argument("--fail-on-warning", action="store_true")
    return p.parse_args(_args_after_dashdash())


def main():
    args=parse_args()
    ns=runpy.run_path(str(BUILD_SCRIPT), run_name="meyd_validator")
    ns["RUN_PASSES"]=(1,2,3)
    issues=ns["validate_model"]()
    scene=bpy.context.scene
    ctrl=bpy.data.objects.get("PHASE_CONTROLLER")

    # Force each checkpoint so dependency graph + custom-property animation gets evaluated.
    checkpoints=[1,31,38,50,61,68,76,83,89,91,121,151,181,211]
    frame_state=[]
    for frame in checkpoints:
        scene.frame_set(frame)
        frame_state.append({
            "frame": frame,
            "Construction_Phase": ctrl.get("Construction_Phase") if ctrl else None,
            "Demolition_Subphase": ctrl.get("Demolition_Subphase") if ctrl else None,
        })
    scene.frame_set(1)

    modifier_ok=False
    slab=bpy.data.objects.get("BuildingB_SOG_5p5in")
    if slab:
        mod=slab.modifiers.get("MEYD_Trench_Difference")
        modifier_ok=bool(mod)

    report={
        "timestamp_utc":datetime.now(timezone.utc).isoformat(),
        "blender_version":bpy.app.version_string,
        "blend_filepath":bpy.data.filepath,
        "validation_issues":issues,
        "validation_passed":not issues,
        "boolean_modifier_present":modifier_ok,
        "frame_state":frame_state,
        "object_count":len(bpy.data.objects),
        "collection_count":len(bpy.data.collections),
    }
    out=Path(args.report); out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,indent=2,sort_keys=True),encoding="utf-8")
    print(f"SAVED_BLEND_VERIFY_REPORT={out.resolve()}")
    if args.fail_on_warning and issues:
        raise SystemExit(2)

if __name__=="__main__":
    main()
