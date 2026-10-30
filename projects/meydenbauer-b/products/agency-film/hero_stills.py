"""Render the agency film's hero stills from the committed overview 4D scene (CPU Cycles).

    uv run python projects/meydenbauer-b/products/agency-film/hero_stills.py --res 2560x1072 --samples 24
    uv run python projects/meydenbauer-b/products/agency-film/hero_stills.py --res 480x200 --samples 6 --only H2-abs   # framing test
"""
import argparse
import json
import time
from pathlib import Path

import bpy
from mathutils import Vector

from bmodels.paths import ROOT

HERE = Path(__file__).resolve().parent
OUT = ROOT / "build" / "meydenbauer-b" / "agency-film" / "stills"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--res", default="2560x1072")
    ap.add_argument("--samples", type=int, default=24)
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--tag", default="")
    a = ap.parse_args()
    spec = json.loads((HERE / "hero_shots.json").read_text())
    bpy.ops.wm.open_mainfile(filepath=str(ROOT / spec["scene"]))
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"; sc.cycles.device = "CPU"
    sc.cycles.samples = a.samples; sc.cycles.use_denoising = True; sc.cycles.denoiser = "OPENIMAGEDENOISE"
    sc.cycles.max_bounces = 6; sc.cycles.transparent_max_bounces = 24; sc.cycles.sample_clamp_indirect = 6
    sc.render.resolution_x, sc.render.resolution_y = (int(v) for v in a.res.split("x"))
    sc.render.resolution_percentage = 100
    sc.view_settings.view_transform = "AgX"; sc.view_settings.look = "AgX - Medium High Contrast"
    # A fixed camera per still: drop the baked sequence camera's animation.
    co = sc.camera; co.animation_data_clear(); tgt = co.data.dof.focus_object
    if tgt is not None:
        tgt.animation_data_clear()
    OUT.mkdir(parents=True, exist_ok=True)
    for s in spec["shots"]:
        if a.only and s["id"] not in a.only:
            continue
        sc.frame_set(s["frame"])
        c, t = Vector(s["camera"]), Vector(s["target"])
        co.rotation_mode = "QUATERNION"; co.location = c
        co.rotation_quaternion = (t - c).to_track_quat("-Z", "Y")
        co.data.lens = s["lens"]; co.data.dof.aperture_fstop = s["fstop"]
        if tgt is not None:
            tgt.location = t
        sc.render.filepath = str(OUT / f"{s['id']}{a.tag}.png")
        t0 = time.time(); bpy.ops.render.render(write_still=True)
        print(f"STILL {s['id']} {time.time() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
