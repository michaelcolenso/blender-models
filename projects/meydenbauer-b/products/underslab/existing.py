"""Existing under-slab waste piping to be removed, from the demolition plan (P1.01).

P1.01 draws each pipe to be removed as a dashed centreline in the 0.96 pt black pen, crossed
by 0.48 pt diagonal hatch strokes. A heavy dash that a hatch stroke crosses is existing pipe;
dashes are bridged into continuous runs. Each run takes the nominal size of the nearest new
run on P1.02 (KEAD replaces in kind along the same routes) and is assigned to a unit by grid.
Writes meydenbauer-b.existing.json. Depth is not documented: realism/animation place the
existing pipe at the new pipe's modelled profile (assumed).

Usage: python projects/meydenbauer-b/products/underslab/existing.py sources/meydenbauer/exhibit-a-bid-set.pdf
"""
import json, math, sys
from pathlib import Path

import pymupdf
from shapely.geometry import LineString
from shapely.ops import linemerge, unary_union
from shapely.strtree import STRtree

sys.path.insert(0, str(Path(__file__).parent))
from prepare import PT_PER_FT, grid_calibration  # noqa: E402

HERE = Path(__file__).parent
PAGE = 4                       # P1.01
BRIDGE = 3.0                   # pt each dash is extended to close the dash gaps (about 5 pt)
UNITS = {"B-101": (-4.0, 45.9), "B-102": (45.9, 80.0), "B-103": (80.0, 113.6), "B-104": (113.6, 166.0)}


def main(pdf):
    page = pymupdf.open(pdf)[PAGE]
    M = page.rotation_matrix
    col, row, sx, sy = grid_calibration(page, M)
    ox, oy = col["A"], row["1"]
    heavy, hatch = [], []
    for p in page.get_drawings():
        if p["type"] != "s" or tuple(round(x, 2) for x in (p.get("color") or ())) != (0, 0, 0):
            continue
        w = round(p.get("width") or 0, 2)
        for it in p["items"]:
            if it[0] != "l":
                continue
            a, b = it[1] * M, it[2] * M
            if not (480 < a.x < 2020 and 640 < a.y < 1440):
                continue
            L = a.distance_to(b)
            if w == 0.96 and L > 0.5:
                heavy.append(LineString([(a.x, a.y), (b.x, b.y)]))
            elif w == 0.48 and 4 < L < 9 and abs(a.x - b.x) > 1 and abs(a.y - b.y) > 1:
                hatch.append(LineString([(a.x, a.y), (b.x, b.y)]))
    tree = STRtree(hatch)
    dashes = [h for h in heavy if any(hatch[j].intersects(h) for j in tree.query(h))]

    def extend(ls):
        (x1, y1), (x2, y2) = ls.coords
        L = math.hypot(x2 - x1, y2 - y1); u = ((x2 - x1) / L, (y2 - y1) / L)
        return LineString([(x1 - u[0] * BRIDGE, y1 - u[1] * BRIDGE), (x2 + u[0] * BRIDGE, y2 + u[1] * BRIDGE)])
    merged = linemerge(unary_union([extend(d) for d in dashes]))
    runs = [g for g in getattr(merged, "geoms", [merged]) if g.length > 1.5 * PT_PER_FT]

    new = json.loads((HERE / "meydenbauer-b.spec.json").read_text())
    new_edges = []
    for u in new["units"]:
        N = u["nodes"]
        for e in u["edges"]:
            a = N[e["a"]]["xy_ft"]; b = N[e["b"]]["xy_ft"]
            new_edges.append((LineString([a, b]), e["nominal_in"]))
    to_ft = lambda p: ((p[0] - ox) / PT_PER_FT, (p[1] - oy) / PT_PER_FT)
    out = []
    for g in runs:
        pts = [to_ft(p) for p in g.simplify(0.3).coords]
        ls = LineString(pts)
        mid = ls.interpolate(0.5, normalized=True)
        unit = next(k for k, (x0, x1) in UNITS.items() if x0 <= mid.x < x1)
        d, nom = min((ls.distance(e), n) for e, n in new_edges)
        out.append({"unit": unit, "points_ft": [[round(x, 3), round(y, 3)] for x, y in pts],
                    "length_ft": round(ls.length, 2), "nominal_in": nom if d < 2.0 else 2,
                    "nearest_new_ft": round(d, 2)})
    spec = {"source": "P1.01 Waste Plumbing Demolition Plan: hatched dashed centrelines (remove & replace)",
            "calibration_pt_per_ft": [round(sx, 3), round(sy, 3)],
            "status": "provisional (plan); depth assumed = new pipe profile; material per SOR (cast iron)",
            "runs": out}
    (HERE / "meydenbauer-b.existing.json").write_text(json.dumps(spec, indent=1))
    by = {}
    for r in out:
        by[r["unit"]] = by.get(r["unit"], 0) + r["length_ft"]
    far = [r for r in out if r["nearest_new_ft"] > 2.0]
    print(f"{len(dashes)} hatched dashes -> {len(out)} runs, {sum(r['length_ft'] for r in out):.1f} ft; "
          f"by unit { {k: round(v, 1) for k, v in sorted(by.items())} }; {len(far)} runs > 2 ft from any new run")


if __name__ == "__main__":
    main(sys.argv[1])
