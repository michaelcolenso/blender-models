"""B-101 v4.1: rebuild the recovered B-101 v4 package with b101_v4_1.patch and run its own checks.

Copies vdc-recovery/snapshots/b101 to build/meydenbauer-b/b101-review/pkg (the snapshot itself is never
edited, so its recovery hashes stay valid), applies the patch, then runs the package's strict build,
saved-blend reopen check and extended QA with bpy, and renders the eight demolition keyframes on CPU Cycles.

    python build.py            # full run (bpy; ~4 min CPU)
    python build.py --check    # CI: patch applies cleanly and patched scripts compile; no bpy
"""
import json
import py_compile
import shutil
import subprocess
import sys
from pathlib import Path

from bmodels.paths import ROOT

HERE = Path(__file__).resolve().parent
SNAPSHOT = ROOT / "projects/meydenbauer-b/products/vdc-recovery/snapshots/b101"
PATCH = HERE / "b101_v4_1.patch"
BUILD = ROOT / "build/meydenbauer-b/b101-review"
PKG = BUILD / "pkg"
BLEND = "output/Meydenbauer_B101_Demolition_v4.blend"


def prepare():
    if PKG.exists():
        shutil.rmtree(PKG)
    shutil.copytree(SNAPSHOT, PKG)
    # PKG is inside the repo; from a subdirectory git apply silently skips paths, so apply from ROOT.
    subprocess.run(["git", "apply", f"--directory={PKG.relative_to(ROOT)}", str(PATCH)], cwd=ROOT, check=True)
    if b"V41_CLIPPED_AT_NO_DEMO_ENVELOPE" not in (PKG / "scripts/build_meydenbauer_b101_v4.py").read_bytes():
        raise SystemExit("b101_v4_1.patch did not apply")
    for f in ("build_meydenbauer_b101_v4.py", "run_build_and_verify.py"):
        py_compile.compile(str(PKG / "scripts" / f), doraise=True)


def run_bpy(code, log):
    """Run a snippet in a fresh Python with bpy (one Blender session per step, like the package's launcher)."""
    with open(PKG / "logs" / log, "w") as out:
        return subprocess.run([sys.executable, "-c", code], cwd=PKG, stdout=out, stderr=subprocess.STDOUT).returncode


FRAMES = ("050_finish_stripout", "068_slab_sawcut", "083_excavation_expose_ci", "089_ci_removed_clean_trench")


def make_deliverables():
    """Stamp four keyframes with the illustrative label and save them as small JPEGs for the README."""
    from PIL import Image, ImageDraw, ImageFont
    from bmodels.record import LABEL
    out = ROOT / "projects/meydenbauer-b/deliverables/b101-review"
    out.mkdir(parents=True, exist_ok=True)
    footer = "Meydenbauer B-101 v4.1 · drawings P1.01/P1.02/P3.1 + 10-16-2026 Addendum · not field verified"
    for key in FRAMES:
        im = Image.open(PKG / f"renders/B101_demo_{key}.png").convert("RGB")
        w, h = im.size
        canvas = Image.new("RGB", (w, h + 62), "white")
        canvas.paste(im, (0, 0))
        d = ImageDraw.Draw(canvas)
        try:
            bold, reg = ImageFont.truetype("DejaVuSans-Bold.ttf", 17), ImageFont.truetype("DejaVuSans.ttf", 15)
        except OSError:
            bold = reg = ImageFont.load_default()
        d.text((14, h + 8), LABEL, fill=(160, 30, 30), font=bold)
        d.text((14, h + 34), footer, fill=(40, 40, 40), font=reg)
        canvas.save(out / f"B101_v41_{key[:3]}.jpg", quality=82, optimize=True)


def main():
    prepare()
    if "--check" in sys.argv:
        print("ok    b101 v4.1 patch applies and patched scripts compile")
        return
    (PKG / "output" / "build_validation_report.json").unlink(missing_ok=True)
    steps = {
        "build": ("import sys,runpy;sys.argv=['blender','--','--fail-on-warning','--render-keyframes','--samples','16'];"
                  "runpy.run_path('scripts/run_build_and_verify.py',run_name='__main__')", "v41_build.log"),
    }
    for name in ("verify_saved_blend", "extended_runtime_qa"):
        steps[name] = (f"import sys,runpy,bpy;bpy.ops.wm.open_mainfile(filepath='{BLEND}');"
                       f"sys.argv=['blender','--','--fail-on-warning'];runpy.run_path('scripts/{name}.py',run_name='__main__')",
                       f"v41_{name}.log")
    results = {name: run_bpy(code, log) for name, (code, log) in steps.items()}
    qa = json.loads((PKG / "output/extended_runtime_qa.json").read_text())
    summary = {
        "exit_codes": results,
        "prior_abs_envelope_open_samples": qa["prior_abs_envelope"]["opening_samples"],
        "boolean_grid_mismatches": qa["boolean_grid"]["mismatch_count"],
        "slab_nonmanifold_edges": qa["slab"]["nonmanifold_edges"],
        "counts": qa["counts"],
        "saved_routes_pass": all(r["passed"] for r in qa["saved_route_checks"]),
        "renders": sorted(p.name for p in (PKG / "renders").glob("*.png")),
    }
    # extended_runtime_qa.py always exits 0, so enforce its results here.
    failures = [name for name, ok in {
        "a step exited non-zero": not any(results.values()),
        "slab opened inside the prior-repair no-demo envelope": summary["prior_abs_envelope_open_samples"] == 0,
        "slab Boolean differs from the cutter union": summary["boolean_grid_mismatches"] == 0,
        "slab has non-manifold edges": summary["slab_nonmanifold_edges"] == 0,
        "a saved route differs from its controls": summary["saved_routes_pass"],
        "invalid or flagged drivers": not (qa["invalid_drivers"] or qa["flagged_driver_errors"]),
        "missing keyframe renders": len(summary["renders"]) == 8,
    }.items() if not ok]
    summary["failures"] = failures
    (BUILD / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    if failures:
        sys.exit("B-101 v4.1 review FAILED: " + "; ".join(failures))
    make_deliverables()


if __name__ == "__main__":
    main()
