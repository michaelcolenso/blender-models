"""Record structure under the trenches, and where the trenches meet it.

Exhibit B (Concrete Technology Corp. record set, 1974, "for reference only") was registered to the
bid-set grid from its own grid bubbles (fit residual <= 0.26 ft; see README). From it:
- Every exterior wall stands on a strip footing 2'-6" wide, centred under the wall (FPB1/FPB2,
  sections 9-11/D2). Its plan comes from the P2.1 exterior walls; its width, top and bottom from D2.
- Footings traced from the registered scan where a trench comes within a few feet (TRACED).
Writes meydenbauer-b.structure.json, including a trench-vs-footing clash list for three POC
invert depths. No Blender here.

Usage: python projects/meydenbauer-b/products/underslab/structure.py
"""
import json
from pathlib import Path

import numpy as np
from shapely.geometry import Point, Polygon
from shapely.ops import unary_union

HERE = Path(__file__).parent
from bmodels.paths import ROOT  # noqa: E402  (repo root)
SPEC = json.loads((HERE / "meydenbauer-b.spec.json").read_text())
SHELL = json.loads((HERE / "meydenbauer-b.shell.json").read_text())
TAKE = json.loads((ROOT / "build/meydenbauer-b/takeoff.json").read_text())

FOOTING_W = 2.5          # ft, 1'-3" + 1'-3" (sections 9, 10/D2); traced band on FPB1 at B-101: 2.5 ft
FOOTING_TOP = 0.33       # ft below FF: underside of the 4" slab (assumed)
FOOTING_BOT = 3.33       # ft below FF: 10" + 2'-6" (sections 10, 11/D2)
POC_ZONE = 4.0           # ft of flow from the tie-in: the exterior footing crossing detailed in A-A/P5.1
NEAR = 1.5               # ft: a trench this close to a footing and deeper than its bottom undermines it

# Traced by eye from Exhibit B registered to the grid (feet from grid A / grid 1, KEAD frame).
TRACED = [
    {"id": "FTG-core-JK-north", "ring_ft": [(113.7, 41.9), (129.0, 41.9), (129.0, 47.5), (113.7, 47.5)],
     "source": "Exhibit B FPB2: dashed footing at the lower stair core (precast K-L), north band"},
]


def exterior_footing():
    env = Polygon(SHELL["envelope_ft"])
    band = env.exterior.buffer(1.6)
    walls = unary_union([Polygon(w["ring_ft"]).buffer(0) for w in SHELL["walls"]])
    ext = walls.intersection(band)
    # Grow each exterior wall piece to the footing width: wall (~0.6-0.9 ft) + about 0.85 ft a side.
    f = ext.buffer(0.85, cap_style="flat", join_style="mitre").intersection(env.buffer(1.3))
    return [p for p in getattr(f, "geoms", [f]) if p.geom_type == "Polygon" and p.area > 1.0]


def clash(footings):
    rows = []
    fpoly = [(f["id"], Polygon(f["ring_ft"])) for f in footings]
    for su, tu in zip(SPEC["units"], TAKE["units"]):
        N = su["nodes"]
        samples = []
        for e in su["edges"]:
            a, b = N[e["a"]], N[e["b"]]
            n = max(2, int(e["length_ft"] / 0.25) + 1)
            for t in np.linspace(0, 1, n):
                samples.append((a["xy_ft"][0] + (b["xy_ft"][0] - a["xy_ft"][0]) * t,
                                a["xy_ft"][1] + (b["xy_ft"][1] - a["xy_ft"][1]) * t,
                                a["flow_ft"] + (b["flow_ft"] - a["flow_ft"]) * t, e["length_ft"] / (n - 1)))
        for d0 in TAKE["inputs"]["tie_depths_ft"]:
            through, at_poc, beside, where = 0.0, 0.0, 0.0, {}
            for x, y, flow, dl in samples:
                bottom = d0 - TAKE["inputs"]["slope_ft_per_ft"] * flow + TAKE["inputs"]["bedding_ft"]
                trench = Point(x, y).buffer(1.0)                       # 2'-0" trench (10/P5.1)
                for fid, fp in fpoly:
                    if fp.intersects(trench) and bottom > FOOTING_TOP:
                        if flow < POC_ZONE:
                            at_poc += dl                    # the documented crossing (sleeve, A-A/P5.1)
                        else:
                            through += dl; where.setdefault(fid, [0.0, 0.0])[0] += dl
                        break
                    if fp.distance(Point(x, y)) < 1.0 + NEAR and bottom > FOOTING_BOT:
                        beside += dl; where.setdefault(fid, [0.0, 0.0])[1] += dl; break
            rows.append({"unit": su["unit"], "poc_invert_ft": d0, "poc_crossing_lf": round(at_poc, 1),
                         "through_footing_lf": round(through, 1),
                         "deeper_than_adjacent_footing_lf": round(beside, 1),
                         "by_footing": {k: [round(v[0], 1), round(v[1], 1)] for k, v in where.items()}})
    return rows


def main():
    footings = []
    for i, p in enumerate(exterior_footing()):
        footings.append({"id": f"FTG-ext-{i:02d}", "ring_ft": list(p.exterior.coords), "top_ft": FOOTING_TOP,
                         "bottom_ft": FOOTING_BOT, "status": "provisional",
                         "source": "plan: P2.1 exterior walls grown to 2'-6\"; depth: Exhibit B sections 10, 11/D2"})
    for t in TRACED:
        footings.append({**t, "top_ft": FOOTING_TOP, "bottom_ft": FOOTING_BOT, "status": "provisional"})
    rows = clash(footings)
    out = {"source": "Exhibit B record set (reference only), registered to the bid-set grid; slab thickness assumed",
           "footings": footings, "clash": rows,
           "rules": {"poc_crossing": "trench within 4 ft of flow from the tie-in crosses the exterior footing (sleeve per A-A/P5.1)",
                     "through": "elsewhere, the 2'-0\" trench overlaps a footing in plan below the slab",
                     "deeper_than_adjacent": f"trench within {NEAR} ft of a footing and below its bottom ({FOOTING_BOT} ft)"}}
    (HERE / "meydenbauer-b.structure.json").write_text(json.dumps(out, indent=1))
    print(f"{len(footings)} footing pieces")
    for r in rows:
        if r["poc_invert_ft"] == 3.5 or r["through_footing_lf"] or r["deeper_than_adjacent_footing_lf"]:
            print(f'{r["unit"]} @ {r["poc_invert_ft"]} ft: POC crossing {r["poc_crossing_lf"]:4.1f} LF, other through {r["through_footing_lf"]:5.1f} LF, '
                  f'beside-and-deeper {r["deeper_than_adjacent_footing_lf"]:5.1f} LF  {r["by_footing"]}')


if __name__ == "__main__":
    main()
