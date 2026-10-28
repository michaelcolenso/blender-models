"""Open committed .blend files and fail if any external file they reference is missing.

    uv run bm audit-blends [file.blend ...]     # default: every tracked .blend (LFS pointers are skipped)

Moving folders silently breaks relative paths saved inside .blend files (textures, linked libraries,
sounds); this catches it. Runs in bpy, so `bm` calls it in a subprocess.
"""
import json
import subprocess
import sys
from pathlib import Path

import bpy

from bmodels.paths import ROOT
from bmodels.render_assets import scene_asset_paths

LFS_POINTER = b"version https://git-lfs.github.com/spec/v1"


def tracked_blends():
    out = subprocess.run(["git", "ls-files", "*.blend"], cwd=ROOT, capture_output=True, text=True, check=True).stdout
    return [ROOT / f for f in out.split()]


def audit(path):
    if path.read_bytes()[:len(LFS_POINTER)] == LFS_POINTER:
        return {"file": str(path.relative_to(ROOT)), "skipped": "LFS pointer (run with LFS checked out)"}
    bpy.ops.wm.open_mainfile(filepath=str(path))
    paths = sorted({p for scene in bpy.data.scenes for p in scene_asset_paths(bpy, scene)})
    missing = [p for p in paths if not Path(p).is_file()]
    return {"file": str(path.relative_to(ROOT)), "external": len(paths), "missing": missing}


def main():
    files = [Path(f).resolve() for f in sys.argv[1:]] or tracked_blends()
    results = [audit(f) for f in files]
    for r in results:
        state = "skip" if "skipped" in r else ("FAIL" if r["missing"] else "ok  ")
        print(f"{state}  {r['file']}  " + (r.get("skipped") or f"{r['external']} external files"), flush=True)
        for m in r.get("missing", []):
            print(f"        missing: {m}")
    print(json.dumps({"audited": sum("skipped" not in r for r in results),
                      "skipped": sum("skipped" in r for r in results),
                      "failed": sum(bool(r.get("missing")) for r in results)}))
    sys.exit(1 if any(r.get("missing") for r in results) else 0)


if __name__ == "__main__":
    main()
