"""Ground-floor shell of Building B from the vector bid set: walls, openings and rooms.

Reads sheet P2.1 (First Floor Waste Plumbing Plan, 1/8" = 1'-0"), which carries the architectural
base drawn from KEAD's Matterport scans: walls as double lines in the 0.48 pt grey pen, door gaps,
window glazing lines, and room tags with measured area and ceiling height. Writes
meydenbauer-b.shell.json in the same grid frame as meydenbauer-b.spec.json. No Blender here.

Checks (reported, not gating): each closed room is compared with the area KEAD measured for it.
Rooms that open onto the glazed west wall or merge across an unclosed gap do not close.

Usage: python projects/meydenbauer-b/shell.py sources/meydenbauer/exhibit-a-bid-set.pdf
"""
import json, math, re, sys
from pathlib import Path

import pymupdf
import shapely
from shapely.geometry import LineString, MultiPoint, Point, Polygon, box
from shapely.ops import unary_union
from shapely.strtree import STRtree

sys.path.insert(0, str(Path(__file__).parent))
from prepare import PT_PER_FT, grid_calibration  # noqa: E402

HERE = Path(__file__).parent
PAGE = 6                                   # P2.1
WALL_IN = (3.0, 13.0)                      # wall thickness band (2x4 partitions to precast + furring)
GLASS_IN = (0.3, 2.9)                      # window glazing lines drawn closer than any wall
DOOR_FT = (1.8, 4.2)                       # gap widths closed as door/window openings
ROOM_TOL = 0.06                            # 6 % of the measured room area

# Reviewed by eye on P2.1 (feet from grid A/1): double outlines that are not walls.
NOT_WALLS = [
    ((94.5, 52.0, 113.5, 62.0), "B-103 DINING octagon: raised-floor / ceiling outline, not a wall"),
]


def segments(page, M, col, row):
    out = []
    for p in page.get_drawings():
        if p["type"] != "s" or round(p.get("width") or 0, 2) != 0.48:
            continue
        if tuple(round(x, 2) for x in p["color"]) != (0.3, 0.3, 0.3):
            continue
        for it in p["items"]:
            if it[0] != "l":
                continue
            a, b = it[1] * M, it[2] * M
            if not (480 < a.x < 2020 and 640 < a.y < 1440) or a.distance_to(b) < 0.3:
                continue
            vert, hor = abs(a.x - b.x) < 0.05, abs(a.y - b.y) < 0.05
            short = a.distance_to(b) < 30
            if short and vert and any(abs(a.x - c) < 0.4 for c in col.values()):
                continue                    # grid-line dashes
            if short and hor and any(abs(a.y - r) < 0.4 for r in row.values()):
                continue
            out.append(((a.x, a.y), (b.x, b.y)))
    return out


def pair(segs, lo_in, hi_in, min_overlap_ft):
    """Rectangles between each line and its nearest parallel partner on either side."""
    lines = [LineString(s) for s in segs]
    tree = STRtree(lines)
    lo, hi = lo_in / 12 * PT_PER_FT, hi_in / 12 * PT_PER_FT
    rects = []
    for i, s in enumerate(segs):
        (x1, y1), (x2, y2) = s
        L = math.hypot(x2 - x1, y2 - y1)
        u = ((x2 - x1) / L, (y2 - y1) / L); n = (-u[1], u[0])
        t = lambda P: (P[0] - x1) * u[0] + (P[1] - y1) * u[1]
        best = {}
        for j in tree.query(lines[i].buffer(hi)):
            if j == i:
                continue
            (a1, b1), (a2, b2) = segs[j]
            L2 = math.hypot(a2 - a1, b2 - b1)
            if abs(u[0] * (b2 - b1) / L2 - u[1] * (a2 - a1) / L2) > 0.01:
                continue
            off = (a1 - x1) * n[0] + (b1 - y1) * n[1]
            if not lo <= abs(off) <= hi:
                continue
            s0, s1 = sorted((t(s[0]), t(s[1]))); o0, o1 = sorted((t((a1, b1)), t((a2, b2))))
            lo_t, hi_t = max(s0, o0), min(s1, o1)
            if hi_t - lo_t < min_overlap_ft * PT_PER_FT:
                continue
            side = off > 0
            if side not in best or abs(off) < abs(best[side][0]):
                best[side] = (off, lo_t, hi_t)
        for off, a, b in best.values():
            P = lambda tt, o: (x1 + u[0] * tt + n[0] * o, y1 + u[1] * tt + n[1] * o)
            rects.append((Polygon([P(a, 0), P(b, 0), P(b, off), P(a, off)]), u, abs(off)))
    return unary_union([r.buffer(0.05, join_style="mitre") for r, _, _ in rects]), rects


def thickness(g):
    return 2 * g.area / g.length


def parts(g):
    return [p for p in getattr(g, "geoms", [g]) if p.geom_type == "Polygon" and not p.is_empty]


def main(pdf):
    doc = pymupdf.open(pdf)
    page = doc[PAGE]
    M = page.rotation_matrix
    col, row, sx, sy = grid_calibration(page, M)
    ox, oy = col["A"], row["1"]
    to_ft = lambda p: ((p[0] - ox) / PT_PER_FT, (p[1] - oy) / PT_PER_FT)
    to_pt = lambda p: (ox + p[0] * PT_PER_FT, oy + p[1] * PT_PER_FT)

    segs = segments(page, M, col, row)
    walls, rects = pair(segs, *WALL_IN, min_overlap_ft=0.4)
    r = 0.3 * PT_PER_FT                                      # close dash gaps along a wall line
    walls = walls.buffer(r, join_style="mitre").buffer(-r, join_style="mitre")
    for (x0, y0, x1, y1), why in NOT_WALLS:
        walls = walls.difference(box(*to_pt((x0, y0)), *to_pt((x1, y1))))
    walls = unary_union([p for p in parts(walls) if p.area > 0.3 * PT_PER_FT ** 2])
    glass, _ = pair(segs, *GLASS_IN, min_overlap_ft=1.0)
    # Concrete walls: 6.5 in and thicker (7-8 in precast panels and 8 in CIP per Exhibit B D2 sections;
    # framed partitions measure 3-6 in). Used for the footing / thickened-slab layer.
    thick = unary_union([r.buffer(0.05) for r, u, t in rects if t / PT_PER_FT * 12 >= 6.5])
    thick = [p for p in parts(thick.buffer(0.3 * PT_PER_FT).buffer(-0.3 * PT_PER_FT)) if p.area > 1.0 * PT_PER_FT ** 2]

    # Openings: extend every wall rectangle past each end until it meets the next wall. A 1.8-4.2 ft
    # bridge is a door; a longer one (to 14 ft) is a window bay if it lies on the building perimeter.
    # Envelope: concave hull of the densified wall outlines (ratio tuned by eye on P2.1; it follows the
    # east bump-outs and west bays to within about a foot).
    dense = [q for p in parts(walls) for q in p.segmentize(0.5 * PT_PER_FT).exterior.coords]
    envelope = shapely.concave_hull(MultiPoint(dense), ratio=0.09)
    openings, seen = [], []
    for rect, u, t in rects:
        cs = list(rect.exterior.coords)[:4]
        c = rect.centroid
        proj = [((x - c.x) * u[0] + (y - c.y) * u[1]) for x, y in cs]
        half = max(proj)
        for sgn in (1, -1):
            end = (c.x + sgn * u[0] * half, c.y + sgn * u[1] * half)
            probe = LineString([end, (end[0] + sgn * u[0] * 14 * PT_PER_FT, end[1] + sgn * u[1] * 14 * PT_PER_FT)])
            hit = probe.intersection(walls.buffer(-0.3))
            if hit.is_empty:
                continue
            d = min(Point(end).distance(g) for g in getattr(hit, "geoms", [hit]))
            span = d / PT_PER_FT
            if span < DOOR_FT[0] - 0.3:
                continue
            n = (-u[1], u[0])
            far = (end[0] + sgn * u[0] * d, end[1] + sgn * u[1] * d)
            strip = Polygon([(end[0] + n[0] * t / 2, end[1] + n[1] * t / 2), (far[0] + n[0] * t / 2, far[1] + n[1] * t / 2),
                             (far[0] - n[0] * t / 2, far[1] - n[1] * t / 2), (end[0] - n[0] * t / 2, end[1] - n[1] * t / 2)])
            mid = strip.centroid
            outside = [not envelope.contains(Point(mid.x + k * n[0] * 2.5 * PT_PER_FT, mid.y + k * n[1] * 2.5 * PT_PER_FT)) for k in (1, -1)]
            perimeter = any(outside) and envelope.exterior.distance(mid) < 1.5 * PT_PER_FT
            if span <= DOOR_FT[1] and not perimeter:
                kind = "door"
            elif perimeter:
                kind = "window"
            else:
                continue
            if any(strip.buffer(-0.5).intersects(o) for o in seen):
                continue
            seen.append(strip)
            openings.append({"kind": kind, "poly": strip, "span_ft": round(span, 2)})

    # Facade glazing: stretches of the envelope with no wall within 0.8 ft (the west window walls).
    ring = envelope.exterior
    n_s = int(ring.length / (0.25 * PT_PER_FT))
    cover = walls.buffer(0.8 * PT_PER_FT).union(unary_union([o["poly"] for o in openings]).buffer(0.5 * PT_PER_FT))
    run = []
    for i in range(n_s + 1):
        pt = ring.interpolate(i / n_s, normalized=True)
        if not cover.contains(pt):
            run.append(pt)
            continue
        west = run and min(q.y for q in run) > oy + 28 * PT_PER_FT    # east-side hull chords span notches
        if len(run) * 0.25 >= 1.5 and west:
            seg = LineString([(q.x, q.y) for q in run])
            openings.append({"kind": "window", "poly": seg.buffer(0.25 * PT_PER_FT, cap_style="flat"),
                             "span_ft": round(seg.length / PT_PER_FT, 2), "facade_gap": True})
        run = []

    solid = unary_union([walls] + [o["poly"] for o in openings])
    rooms = [Polygon(h) for p in parts(solid) for h in p.interiors]
    rooms = [rm for rm in rooms if rm.area > 3 * PT_PER_FT ** 2]

    tags = []
    for b in page.get_text("dict")["blocks"]:
        for ln in b.get("lines", []):
            t = " ".join(s["text"] for s in ln["spans"]).strip()
            x0, y0, x1, y1 = ln["bbox"]
            c = (pymupdf.Point(x0, y0) + pymupdf.Point(x1, y1)) / 2 * M
            tags.append(((c.x, c.y), t))
    room_out, checks = [], []
    for rm in rooms:
        inside = sorted(((xy[1], t) for xy, t in tags if rm.contains(Point(xy))))
        name = next((t for _, t in inside if re.fullmatch(r"[A-Z ]{3,}", t) and t not in ("TYP",)), None)
        sf = next((float(m.group(1)) for _, t in inside if (m := re.fullmatch(r"([\d.]+) SF", t))), None)
        ch = next((int(m.group(1)) + int(m.group(2)) / 12 for _, t in inside
                   if (m := re.fullmatch(r"CH: (\d+)' - (\d+)\"", t))), None)
        area = rm.area / PT_PER_FT ** 2
        if sf:
            checks.append({"room": name, "measured_sf": sf, "model_sf": round(area, 2),
                           "ok": abs(area - sf) <= ROOM_TOL * sf})
        room_out.append({"name": name, "area_sf": round(area, 2), "measured_sf": sf, "ch_ft": ch,
                         "ring_ft": [to_ft(p) for p in rm.exterior.coords],
                         "status": "provisional" if sf else "assumed"})

    # Tubs and showers: clusters of the 0.48 pt black fixture pen sized like a tub or shower,
    # classified by the nearest TUB / SHR end on P1.02 (meydenbauer-b.spec.json).
    fx = []
    for p in page.get_drawings():
        if p["type"] != "s" or round(p.get("width") or 0, 2) != 0.48 or tuple(round(x, 2) for x in p["color"]) != (0, 0, 0):
            continue
        for it in p["items"]:
            if it[0] in ("l", "c"):
                a, b = it[1] * M, (it[2] if it[0] == "l" else it[4]) * M
                if a.distance_to(b) > 0.05 and 480 < a.x < 2020 and 640 < a.y < 1440:
                    fx.append(LineString([(a.x, a.y), (b.x, b.y)]).buffer(0.4))
    spec_ends = [(e["kind"], tuple(u["nodes"][e["node"]]["xy_ft"]))
                 for u in json.loads((HERE / "meydenbauer-b.spec.json").read_text())["units"] for e in u["ends"]]
    fixtures = []
    for g in parts(unary_union(fx)):
        x0, y0, x1, y1 = g.bounds
        w, h = (x1 - x0) / PT_PER_FT, (y1 - y0) / PT_PER_FT
        if not (max(w, h) > 3.5 and min(w, h) > 1.5):
            continue
        bb = [to_ft((x0, y0)), to_ft((x1, y1))]
        cbox = box(bb[0][0], bb[0][1], bb[1][0], bb[1][1])
        near = sorted((cbox.distance(Point(xy)), k) for k, xy in spec_ends if k in ("TUB", "SHR"))
        kind = near[0][1] if near and near[0][0] < 3.0 else "SHR"
        if any(f["kind"] == kind and box(*f["box_ft"][0], *f["box_ft"][1]).intersects(cbox) for f in fixtures):
            continue                                    # nested outline of the same fixture
        fixtures.append({"kind": kind, "box_ft": bb, "status": "provisional",
                         "basis": "fixture symbol extent on P2.1; type from nearest P1.02 end"})

    bx = lambda f: box(*f["box_ft"][0], *f["box_ft"][1])
    fixtures = [f for f in fixtures if not any(g is not f and bx(f).contains(bx(g).buffer(-0.1)) for g in fixtures)]

    ring = lambda g: [to_ft(p) for p in g.exterior.coords]
    spec = {
        "source": {"sheet": "P2.1 First Floor Waste Plumbing Plan (architectural base from KEAD Matterport + field measurements)",
                   "page": PAGE + 1, "scale": "1/8\" = 1'-0\"",
                   "calibration_pt_per_ft": [round(sx, 3), round(sy, 3)]},
        "walls": [{"ring_ft": ring(p), "holes_ft": [[to_ft(q) for q in h.coords] for h in p.interiors],
                   "thickness_in": round(thickness(p) / PT_PER_FT * 12, 1)} for p in parts(walls)],
        "openings": [{"kind": o["kind"], "ring_ft": ring(o["poly"]), "span_ft": o.get("span_ft")} for o in openings],
        "concrete_walls": [{"ring_ft": ring(p), "thickness_in": round(thickness(p) / PT_PER_FT * 12, 1)} for p in thick],
        "rooms": room_out,
        "fixtures": fixtures,
        "room_checks": checks,
        "excluded": [{"box_ft": b, "why": w} for b, w in NOT_WALLS],
        "envelope_ft": ring(envelope),
        "provenance": {
            "walls": {"status": "provisional", "basis": "paired double lines 3-13 in apart on P2.1; plotted scale verified"},
            "openings": {"status": "provisional", "basis": "wall gaps 1.8-4.2 ft; glazing lines mark windows"},
            "heights": {"status": "confirmed", "basis": "room tags CH on P2.1 (KEAD Matterport)"},
            "door_head": {"status": "assumed", "value_ft": 6.667},
        },
    }
    rnd = lambda o: round(o, 3) if isinstance(o, float) else [rnd(v) for v in o] if isinstance(o, (list, tuple)) \
        else {k: rnd(v) for k, v in o.items()} if isinstance(o, dict) else o
    out = HERE / "meydenbauer-b.shell.json"
    out.write_text(json.dumps(rnd(spec), separators=(",", ":")))
    bad = [c for c in checks if not c["ok"]]
    print(f"scale {sx:.3f}/{sy:.3f} pt/ft; walls {len(spec['walls'])} pieces "
          f"{walls.area / PT_PER_FT ** 2:.0f} SF; openings {sum(o['kind'] == 'door' for o in openings)} doors, "
          f"{sum(o['kind'] == 'window' for o in openings)} windows; rooms {len(room_out)}")
    print(f"room area checks (reported, not gating): {len(checks) - len(bad)}/{len(checks)} within {ROOM_TOL:.0%}")
    for c in sorted(checks, key=lambda c: c["measured_sf"]):
        print(f'  {"ok " if c["ok"] else "BAD"} {c["room"]!s:12s} measured {c["measured_sf"]:8.2f}  model {c["model_sf"]:8.2f}')
    print("wrote", out)


if __name__ == "__main__":
    main(sys.argv[1])
