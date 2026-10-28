"""Site logistics for the unit-by-unit sequence: entries, site massing, haul routes, haul quantities.

Nothing here is drawn on the bid set. Everything is an ASSUMPTION for the bid team, located from:
  SOR Figure 8 (aerial)    staging ~1,000 SF east of the garages, along the SE 3rd St drive, beside the
                           north end of Building B. Scale read off the aerial (~4 px/ft); not to scale.
  SOR general note 10      Association designates ~1,000 SF; contractor fences it.
  SOR note 3 (p. 11)       side-sewer connections in the planter between the garages and Building B.
  00 22 13 1.14.B          "limit building access to a single entry at ground level".
  P2.1                     X-hatched cores between B-101/B-102 (grid C-D) and B-103/B-104 (grid J-K),
                           each in a ~4 ft recess of the east face. Read here as the stair-core entries.
Reading of 1.14.B used here: one entry in use at a time. Units go one at a time, so the entry
switches once, from the J-K core (B-103) to the C-D core (B-102, B-101) and back to J-K (B-104).
That reading is an assumption to confirm (README: bid clarifications; the RFI cutoff was Oct 23).

Writes meydenbauer-b.logistics.json. No Blender here.
Usage: python projects/meydenbauer-b/products/underslab/logistics.py
"""
import json, math
from pathlib import Path

from shapely.geometry import LineString, Polygon, box
from shapely.ops import unary_union

import schedule as SCHED

HERE = Path(__file__).resolve().parent
from bmodels.paths import ROOT  # noqa: E402  (repo root)
SHELL = json.loads((HERE / "meydenbauer-b.shell.json").read_text())
TAKE = json.loads((ROOT / "build/meydenbauer-b/takeoff.json").read_text())

GRADE = -TAKE["inputs"]["slab_ft"]          # outside grade taken at the slab underside (as realism.py)
FLOOR_Z, GRADE_Z = 0.09, GRADE + 0.04       # route ribbon heights
CORES = {"C-D": 38.67, "J-K": 121.79}       # core centre x, ft from grid A (grid C-D and J-K midpoints)
UNIT_ENTRY = {"B-101": "C-D", "B-102": "C-D", "B-103": "J-K", "B-104": "J-K"}
GAP_Y = -5.0          # walk line in the planter between the building and the garages (garages ~10 ft east)
DRIVE_Y = -51.0       # SE 3rd St drive centreline
TURN_X = 8.0          # haul turns east north of the garages, across the paved area at the north end
BIN = box(22, -73.5, 34, -66)                # 10-yd roll-off, about 12 x 7.5 ft (size assumed)
STOCKPILE_C, STOCKPILE_R = (47.0, -71.0), 5.0
BIN_CY = 10.0
BARROW_CF = 4.0       # loose CF per wheelbarrow trip (assumed)

MASSING = [   # (id, kind, rectangle x0, y0, x1, y1 in plan ft, height ft); all assumed from Fig 8
    ("garage-north", "garage", (20, -40, 46, -10), 10.0),
    ("garage-south", "garage", (48, -40, 101, -10), 10.0),
    ("drive", "drive", (-30, -62, 175, -40), 0.0),
    ("staging", "staging", (12, -84, 57, -62), 0.0),
]


def entry_point(cx):
    """Where the core line meets the envelope's east face (the recess)."""
    env = Polygon(SHELL["envelope_ft"])
    seg = LineString([(cx, -30), (cx, 70)]).intersection(env)
    return (cx, round(seg.bounds[1], 2))


def work_point(unit):
    u = next(u for u in TAKE["units"] if u["unit"] == unit)
    g = unary_union([Polygon(r) for r in u["footprint_S2"]])
    p = g.representative_point()
    return (round(p.x, 2), round(p.y, 2))


def route(unit, to_xy):
    cx = CORES[UNIT_ENTRY[unit]]
    ex, ey = entry_point(cx)
    wx, wy = work_point(unit)
    pts = [(wx, wy, FLOOR_Z), (cx, 12.0, FLOOR_Z), (ex, ey, FLOOR_Z), (ex, ey - 0.6, GRADE_Z),
           (cx, GAP_Y, GRADE_Z), (TURN_X, GAP_Y, GRADE_Z), (TURN_X, DRIVE_Y, GRADE_Z),
           (to_xy[0], DRIVE_Y, GRADE_Z), (to_xy[0], to_xy[1], GRADE_Z)]
    return [[round(v, 2) for v in p] for p in pts]


def length(pts):
    return sum(math.dist(a[:2], b[:2]) for a, b in zip(pts, pts[1:]))


def build():
    plan = SCHED.build()
    bin_door = (28.0, -64.5)
    pile_edge = (STOCKPILE_C[0], STOCKPILE_C[1] + STOCKPILE_R + 0.5)
    routes, haul = {}, {}
    for u in plan["units"]:
        name, q = u["unit"], u["quantities"]
        out = route(name, bin_door)
        inn = list(reversed(route(name, pile_edge)))
        routes[name] = {"entry": UNIT_ENTRY[name], "out_ft": out, "in_ft": inn,
                        "out_length_ft": round(length(out)), "in_length_ft": round(length(inn))}
        haul[name] = {"out_cy_loose": q["haul_out_cy"], "in_cy": q["haul_in_cy"], "concrete_cy": q["concrete_cy"],
                      "bin_swaps": math.ceil(q["haul_out_cy"] / BIN_CY),
                      "barrow_trips_out": math.ceil(q["haul_out_cy"] * 27 / BARROW_CF),
                      "barrow_trips_in": math.ceil(q["haul_in_cy"] * 27 / BARROW_CF)}
    entries = {k: {"door_ft": entry_point(cx), "inside_ft": (cx, 12.0),
                   "units": [u for u, e in UNIT_ENTRY.items() if e == k]} for k, cx in CORES.items()}
    return {
        "status": "ASSUMED: locations and sizes read from SOR Fig 8 and P2.1; not surveyed, not to scale",
        "basis": ["SOR Fig 8: staging ~1,000 SF east of the garages along the SE 3rd St drive",
                  "SOR note 10: Association designates ~1,000 SF; contractor fences it",
                  "SOR note 3: side-sewer connections in the planter between the garages and Building B",
                  "00 22 13 1.14.B: single entry at ground level (read as one entry in use at a time)",
                  "P2.1: X-hatched cores at grid C-D and J-K in recesses of the east face (read as entries)"],
        "grade_ft": GRADE,
        "entries": entries,
        "massing": [{"id": i, "kind": k, "ring_ft": list(box(*r).exterior.coords), "height_ft": h} for i, k, r, h in MASSING],
        "bin": {"ring_ft": list(BIN.exterior.coords), "cy": BIN_CY, "height_ft": 3.5},
        "stockpile": {"centre_ft": STOCKPILE_C, "radius_ft": STOCKPILE_R, "height_ft": 3.5},
        "routes": routes, "haul": haul,
        "assumed_rates": {"bin_cy": BIN_CY, "barrow_cf": BARROW_CF},
        "flags": ["Haul path crosses the planter between Building B and the garages: ground protection and "
                  "landscape restoration to price; confirm the path with the Association",
                  "Two core entries are used over the job (one at a time): confirm 1.14.B allows this, or "
                  "name the single entry and the interior path to the other units"],
    }


if __name__ == "__main__":
    L = build()
    (HERE / "meydenbauer-b.logistics.json").write_text(json.dumps(L, indent=1))
    for k, r in L["routes"].items():
        h = L["haul"][k]
        print(f'{k}: via {r["entry"]} core, out {r["out_length_ft"]} ft, in {r["in_length_ft"]} ft; '
              f'{h["out_cy_loose"]} CY out = {h["bin_swaps"]} x {BIN_CY:g}-yd bins, ~{h["barrow_trips_out"]} barrow trips')
