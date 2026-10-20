"""Render the saved corrected scene without rebuilding or overwriting its rig."""
import argparse
import json
import time
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/"deliverables/highland-roof"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preview", action="store_true")
    parser.add_argument("--night-frames", default="")
    args = parser.parse_args()
    start = time.monotonic()
    timings = {}
    bpy.ops.wm.open_mainfile(filepath=str(OUT/"Highland-roof-and-terrace-revised.blend"), load_ui=False, use_scripts=False)
    if args.night_frames:
        scene = bpy.data.scenes["Dusk / roof and terrace revision 03"]
        bpy.context.window.scene = scene
        scene.render.resolution_x, scene.render.resolution_y = 640, 360
        scene.cycles.samples = 8
        scene.cycles.adaptive_min_samples = 4
        folder = OUT/"cycles-dusk-benchmark"
        folder.mkdir(exist_ok=True)
        for frame in map(int, args.night_frames.split(",")):
            scene.frame_set(frame)
            scene.render.filepath = str(folder/f"frame-{frame:03}.png")
            before = time.monotonic()
            bpy.ops.render.render(write_still=True, scene=scene.name)
            timings[frame] = round(time.monotonic()-before, 2)
            print(f"Native dusk frame {frame}: {timings[frame]:.1f}s", flush=True)
    else:
        scene = bpy.data.scenes["Daylight / roof and terrace revision 03"]
        bpy.context.window.scene = scene
        scene.render.resolution_percentage = 50 if args.preview else 100
        if args.preview:
            scene.cycles.samples = 12
            scene.cycles.adaptive_min_samples = 8
            scene.cycles.adaptive_threshold = .065
        name = "Highland-daylight-geometry-preview.png" if args.preview else "Highland-daylight-geometry-revised.png"
        scene.render.filepath = str(OUT/name)
        print(f"Rendering {name} / {scene.cycles.samples} samples", flush=True)
        bpy.ops.render.render(write_still=True, scene=scene.name)
    record = {"preview": args.preview, "night_frames": args.night_frames, "elapsed_seconds": round(time.monotonic()-start, 2),
              "samples": scene.cycles.samples, "resolution_percentage": scene.render.resolution_percentage,
              "resolution": [scene.render.resolution_x*scene.render.resolution_percentage//100, scene.render.resolution_y*scene.render.resolution_percentage//100],
              "frame_seconds": timings}
    (OUT/("native-dusk-benchmark.json" if args.night_frames else "preview-render.json" if args.preview else "native-render.json")).write_text(json.dumps(record, indent=2)+"\n")
    print(json.dumps(record), flush=True)


if __name__ == "__main__":
    main()
