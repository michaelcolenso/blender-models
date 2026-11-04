"""Read-only source recovery checks; no Blender, PDF extraction, or tracked writes."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter
from pathlib import Path

from shapely.geometry import LineString, Polygon

from bmodels.paths import ROOT

HERE = Path(__file__).resolve().parent
SITE = ROOT / "projects/highland"
REPORT = SITE / "deliverables/exterior-reconciliation/source-check.json"
SNAPSHOTS = {
    "reconciled.spec.json", "decisions.json", "shell-decisions.json", "r5-decisions.json",
    "terrace-decisions.json", "presentation.json", "revision04-north-baseline.json",
    "revision05-controls.json", "stage1-r5-baseline.json", "base-roof.spec.json",
    "source-inventory.json", "revision04.spec.json",
}
GEOMETRY_FIELDS = ("id", "face", "level", "polygon", "segment", "u", "width", "z", "height", "plan_depth_in")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read(path):
    return json.loads(path.read_text())


def verify_snapshot(product_dir=HERE):
    manifest = read(product_dir / "recovery.json")
    expected = {f"snapshots/{name}" for name in SNAPSHOTS}
    files = manifest["files"]
    require(len(files) == len(expected) and {row["file"] for row in files} == expected,
            "Recovery manifest must contain each expected snapshot exactly once")
    records = {}
    for row in files:
        path = product_dir / row["file"]
        data = path.read_bytes()
        require(len(data) == row["bytes"], f"Snapshot size drift: {row['file']}")
        require(hashlib.sha256(data).hexdigest() == row["sha256"], f"Snapshot hash drift: {row['file']}")
        blob = hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()
        require(blob == row["git_blob_sha"], f"Git blob drift: {row['file']}")
        records[path.name] = json.loads(data)
    return manifest, records


def audit_geometry(records):
    spec = records["reconciled.spec.json"]
    base = records["base-roof.spec.json"]
    north_base = records["revision04.spec.json"]
    require(spec["units"] == "inches", "Source coordinates must stay in inches")
    for key in ("grid_dimensions_in", "roof_plate_z", "north_roof_plate_z", "north_roof_split_y"):
        require(spec[key] == base[key], f"Protected control changed: {key}")
    for key in ("r1", "typical"):
        require(spec["polygons"][key] == base["polygons"][key], f"Protected polygon changed: {key}")
    require([(row["name"], row["z"]) for row in spec["levels"]] ==
            [(row["name"], row["z"]) for row in base["levels"]], "Protected floor datums changed")
    require(spec["roof_features"][:2] == base["roof_features"][:2], "Protected tower geometry changed")
    require([row["top"] for row in spec["roof_features"]] == [row["top"] for row in base["roof_features"]],
            "Protected roof feature datums changed")
    require(spec["polygons"]["r5"][:2] == north_base["polygons"]["r5"][:2], "Deferred north wall moved")
    for name, points in spec["polygons"].items():
        polygon = Polygon(points)
        require(polygon.is_valid and polygon.area > 0, f"Invalid enclosure: {name}")

    openings = spec["openings"]
    by_id = {row["id"]: row for row in openings}
    require(len(by_id) == len(openings) == 192, "Opening inventory must contain 192 unique IDs")
    counts = dict(Counter(row["level"] for row in openings))
    require(counts == {"P1": 14, "R1": 36, "R2": 36, "R3": 36, "R4": 36, "R5": 34},
            "Opening inventory changed by floor")
    for row in openings:
        require(row["status"] == "assumed" and row.get("source") and row.get("basis"),
                f"Complete opening must remain assumed with source/basis: {row['id']}")
        require(row["width"] > 0 and row["height"] > 0, f"Invalid opening dimensions: {row['id']}")
        require(row["level"] in counts and row["polygon"] in spec["polygons"], f"Invalid opening binding: {row['id']}")
        require(0 <= row["segment"] < len(spec["polygons"][row["polygon"]]), f"Invalid wall segment: {row['id']}")
        if row["level"] == "P1" or (row["level"] == "R5" and row["face"] != "north"):
            polygon = spec["polygons"][row["polygon"]]
            a, b = polygon[row["segment"]], polygon[(row["segment"] + 1) % len(polygon)]
            axis = 0 if a[0] != b[0] else 1
            low, high = row["u"] - row["width"] / 2, row["u"] + row["width"] / 2
            require(min(a[axis], b[axis]) < low < high < max(a[axis], b[axis]),
                    f"Opening overruns reconciled wall: {row['id']}")
    north_fields = lambda rows: [tuple(row[key] for key in GEOMETRY_FIELDS) for row in rows
                                 if row["face"] == "north" and row["level"] != "P1"]
    require(north_fields(openings) == north_fields(north_base["openings"]), "Deferred north opening geometry changed")
    require(len(north_fields(openings)) == 30, "Deferred north opening set changed")

    r5 = spec["r5_completion"]
    require(len(spec["polygons"]["r5"]) == 14, "R5 enclosure must retain 14 vertices")
    require(r5["rechecked_south_east_west_openings"] == 28, "R5 recheck scope changed")
    pair = sorted((by_id[name] for name in r5["south_pair"]["ids"]), key=lambda row: row["u"])
    require([row["drawing_mark"] for row in pair] == ["MO", "MJ"], "South pair must retain MO/MJ marks")
    require(pair[0]["segment"] == pair[1]["segment"] and pair[0]["z"] == pair[1]["z"] and
            pair[0]["height"] == pair[1]["height"], "South pair must share a wall and vertical extent")
    gap = pair[1]["u"] - pair[1]["width"] / 2 - pair[0]["u"] - pair[0]["width"] / 2
    require(abs(gap) < 0.001, "South MO/MJ pair must retain its contiguous interface")
    group = next(row for row in spec["opening_groups"] if row["id"] == "south-R5-MO-MJ")
    require(group["openings"] == [row["id"] for row in pair], "South opening group binding changed")

    terrace = spec["terrace_review"]
    room = Polygon(spec["polygons"]["r5"])
    surfaces = [Polygon(row["polygon"]) for row in terrace["surfaces"]]
    require(len(surfaces) == 6 and sum(row["kind"] == "planter" for row in terrace["surfaces"]) == 1,
            "Expected five walking surfaces and one planter")
    for row, surface in zip(terrace["surfaces"], surfaces):
        require(surface.is_valid and surface.area > 0, f"Invalid terrace surface: {row['id']}")
        require(surface.intersection(room).area < 0.001, f"Terrace overlaps enclosed room: {row['id']}")
    for i, surface in enumerate(surfaces):
        require(all(surface.intersection(other).area < 0.001 for other in surfaces[i + 1:]),
                "Terrace surfaces overlap")
    require(len(terrace["guards"]) == 5 and len(terrace["bands"]) == 3, "Terrace path inventory changed")
    for row in terrace["guards"]:
        path = LineString(row["path"])
        require(path.is_simple and path.length > 0, f"Invalid guard path: {row['id']}")
        require(path.intersection(room).length < 0.001, f"Guard crosses room or glazing boundary: {row['id']}")
        require(len(row["band_heights_in"]) == len(row["path"]) - 1, f"Guard support binding changed: {row['id']}")
    require(terrace["guard_section"]["status"] == "assumed", "Guard section cannot become confirmed")
    require([row["height_in"] for row in terrace["bands"]] == [26, 28, 30] and
            all(row["height_status"] == "provisional" for row in terrace["bands"]), "Band assumptions changed")
    require(spec["presentation_refresh"]["deferred_faces"] == ["north"], "North presentation deferral changed")

    calibration = spec["drawing_reconciliation"]["calibration"]
    require(set(calibration) == {"P1", "R1", "R2", "R3", "R4", "R5", "Roof"}, "Missing sheet calibration")
    for name, row in calibration.items():
        require(row["status"] == "provisional" and row["pick_uncertainty_in"] == 3, f"Calibration status changed: {name}")
        pixels, inches = row["grid_x_pixels"], row["grid_x_inches"]
        rates = [(b - a) / (d - c) for a, b, c, d in zip(pixels, pixels[1:], inches, inches[1:])]
        require(len(rates) == len(row["pixels_per_inch_by_span"]) == 4 and
                all(rate > 0 and math.isclose(rate, recorded, abs_tol=1e-12)
                    for rate, recorded in zip(rates, row["pixels_per_inch_by_span"])),
                f"Sheet calibration does not reconcile to dimension strings: {name}")

    controls = {}
    for filename, key, expected in [("revision04-north-baseline.json", "mesh_hashes", 97),
                                    ("revision05-controls.json", "mesh_hashes", 815),
                                    ("stage1-r5-baseline.json", "core_mesh_hashes", 99)]:
        values = records[filename][key]
        require(len(values) == expected and all(len(value) == 64 for value in values.values()),
                f"Historical mesh control inventory changed: {filename}")
        controls[filename] = expected
    return {"opening_counts": counts, "deferred_north_openings": 30, "r5_vertices": 14,
            "terrace_surfaces": 6, "guard_paths": 5, "band_paths": 3, "south_pair_gap_in": round(gap, 6),
            "independently_registered_sheets": len(calibration), "historical_mesh_hash_counts": controls}


def build_report(product_dir=HERE, source_manifest=SITE / "sources/manifest.json"):
    recovery, records = verify_snapshot(product_dir)
    geometry = audit_geometry(records)
    documents = read(source_manifest)["documents"]
    require(documents == records["source-inventory.json"] == records["reconciled.spec.json"]["drawing_reconciliation"]["sources"],
            "Source document registry drift")
    return {"status": "PASS", "scope": "source snapshot integrity and CPU consistency only",
            "source_commit": recovery["source_commit"], "source_tag": recovery["source_tag"],
            "verified_snapshot_blobs": len(records), **geometry,
            "document_count": len(documents), "document_sheet_count": sum(len(row["sheets"]) for row in documents),
            "native_mesh_readback": "not_run", "source_pdf_review": "not_run", "visual_review": "not_run",
            "notice": "Illustrative, not a contract document. Source XY provisional; complete components assumed. "
                      "Historical hashes are preserved controls, not validation of a current Blender scene."}


def verify_sources(source_dir=SITE / "sources", require_sources=False):
    statuses = []
    for row in read(source_dir / "manifest.json")["documents"]:
        path = source_dir / row["file"]
        if not path.is_file():
            require(not require_sources, f"Missing source PDF: {row['file']}")
            statuses.append(f"MISSING {row['file']}")
            continue
        require(path.stat().st_size == row["bytes"] and hashlib.sha256(path.read_bytes()).hexdigest() == row["sha256"],
                f"Source PDF does not match recorded source: {row['file']}")
        statuses.append(f"HASH VERIFIED {row['file']} (contents not reviewed)")
    return statuses


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-sources", action="store_true", help="also fail when any source PDF is unavailable")
    args = parser.parse_args()
    try:
        report = build_report()
        require(report == read(REPORT), "Tracked source report drift; review the inputs and update the report explicitly")
        statuses = verify_sources(require_sources=args.require_sources)
    except (ValueError, KeyError, OSError, TypeError) as error:
        raise SystemExit(f"HIGHLAND SOURCE CHECK FAILED: {error}") from error
    print("HIGHLAND SOURCE CHECK PASS — archived blobs, source locators, protected controls and planar consistency")
    print("\n".join(statuses))
    print("Native mesh readback, source PDF review and visual review: NOT RUN")


if __name__ == "__main__":
    main()
