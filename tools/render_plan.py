"""Validate the shot catalog and emit a GitHub Actions matrix (no bpy needed)."""
import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "render/scenes.json"
PROFILES = {
    "preview": {"max_dimension": 640, "samples": 16},
    "final": {"max_dimension": 1600, "samples": 128},
}


def load_shots(catalog=CATALOG, root=ROOT):
    data = json.loads(Path(catalog).read_text())
    if data.get("schema_version") != 1:
        raise ValueError("Expected catalog schema_version 1")
    shots = data.get("shots")
    if not isinstance(shots, list) or not 1 <= len(shots) <= 128:
        raise ValueError("Catalog must contain between 1 and 128 shots")
    seen = set()
    for shot in shots:
        if not isinstance(shot, dict):
            raise ValueError("Each shot must be an object")
        shot_id = shot.get("id", "")
        if not isinstance(shot_id, str) or not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", shot_id):
            raise ValueError("Shot IDs must use lowercase letters, digits, underscores or hyphens")
        if shot_id == "all":
            raise ValueError("Shot ID 'all' is reserved for selecting the entire catalog")
        if shot_id in seen:
            raise ValueError(f"Duplicate shot ID: {shot_id}")
        seen.add(shot_id)
        for field in ("blend", "scene", "camera", "notice"):
            if not isinstance(shot.get(field), str) or not shot[field].strip():
                raise ValueError(f"{shot_id}: {field} must be a nonempty string")
        relative = Path(shot["blend"])
        path = (root / relative).resolve()
        if relative.is_absolute() or not path.is_relative_to(root.resolve()):
            raise ValueError(f"{shot_id}: blend must stay inside the repository")
        if path.suffix.lower() != ".blend" or not path.is_file():
            raise ValueError(f"{shot_id}: missing .blend file: {relative}")
        frame = shot.get("frame")
        if type(frame) is not int or not 0 <= frame <= 1_048_574:
            raise ValueError(f"{shot_id}: frame must be an integer in Blender's supported range")
    return shots


def select_shots(shots, selection):
    if selection == "all":
        return shots
    selected = [shot for shot in shots if shot["id"] == selection]
    if not selected:
        raise ValueError(f"Unknown shot: {selection}")
    return selected


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=CATALOG)
    parser.add_argument("--shot", default="all")
    args = parser.parse_args()
    shots = select_shots(load_shots(args.catalog), args.shot)
    print(json.dumps({"include": [{"shot": shot["id"]} for shot in shots]}, separators=(",", ":")))


if __name__ == "__main__":
    main()
