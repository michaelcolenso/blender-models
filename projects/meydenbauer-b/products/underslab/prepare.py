"""Extract the Building B under-slab waste network from the vector bid set into a spec.

Reads sheet P1.02 (Waste Plumbing Foundation Plan, 1/8" = 1'-0") of Exhibit A, finds the
new-pipe linework (0.96 pt black strokes), nodes it into one graph per unit, labels the
ends from the sheet text, and writes meydenbauer-b.spec.json. No Blender here.

Usage: python projects/meydenbauer-b/products/underslab/prepare.py sources/meydenbauer/exhibit-a-bid-set.pdf
"""
import hashlib, heapq, json, math, sys
from collections import defaultdict
from pathlib import Path

import pymupdf
from shapely.geometry import LineString, Point
from shapely.ops import snap, unary_union

HERE = Path(__file__).parent
from bmodels.paths import ROOT as REPO  # noqa: E402
PAGE = 5                       # P1.02 is the sixth page of Exhibit A
PT_PER_FT = 9.0                # 1/8" = 1'-0" on a 36x24 plot; verified below from the grid
GRID_X = {"A": 0.0}            # feet, from the P1.02 dimension string A..M
for name, ft in zip("BCDEFGHIJKLM", [31 + 5/12, 3.25, 8, 3.25, 27 + 1/12, 7, 7, 27 + 6.5/12,
                                      3.25, 8, 3.25, 31 + 5/12]):
    GRID_X[name] = list(GRID_X.values())[-1] + ft
GRID_Y = {"1": 0.0}            # feet, rows 1..6 from the P1.02 dimension string
for name, ft in zip("23456", [6 + 4/12, 19 + 10/12, 19 + 5/12, 14 + 5/12, 6 + 4/12]):
    GRID_Y[name] = list(GRID_Y.values())[-1] + ft
UNITS = ["B-101", "B-102", "B-103", "B-104"]    # north to south = left to right on the sheet
SNAP = 2.5                     # pt (0.28 ft); branch ends are drawn up to ~2 pt short of the trunk
EXT_WALL_TOL = 4.0             # pt

# Sizes: P1.02 labels trunks "4" WASTE, TYP." and fixture/stack ends; keynotes give fixture
# branch sizes (2: WC 3" W, 3: wall-hung WC 4" W, 4-9,13: 2" W). See size_rule() below.
FIXTURE_BRANCH_IN = {"WC": 3, "LAV": 2, "SHR": 2, "TUB": 2, "KS": 2, "WB": 2}

# Reviewed by eye against P1.02 (keynote circles and riser hexagons are drawn as graphics, so
# they cannot be read from the text layer). Coordinates are feet from grid A/1; each entry
# names the label it comes from. Tie-in = the "4" WASTE TO 6" WASTE" 2-way cleanout (keynote 1).
REVIEWED = {
    "B-101": {"tie": (23.3, -2.1), "tie_basis": "keynote 1 at grid 1, P1.02",
              "ends": {(13.4, 13.5): ("WC", "WC; leader \"3\"W UP, TYP.\""),
                       (23.3, 27.2): ("WB", "WB; leader \"3\"W UP, TYP.\"; trunk labelled 4\"W")}},
    "B-102": {"tie": (75.1, 4.4), "tie_basis": "keynote 1 near grid F/2, P1.02",
              "ends": {(59.5, 11.6): ("STACK-4", "riser B/P4.1, keynote 16, \"4\"W UP (26 DFU)\" at WC"),
                       (65.4, 27.3): ("STACK-3", "keynote 16, leader \"3\"W UP, TYP.\""),
                       (64.7, 13.2): ("TEE", "shower branch drawn just short of the WC branch; a tee, not an end")}},
    "B-103": {"tie": (89.3, 4.4), "tie_basis": "keynote 1 near grid H/2, P1.02",
              "ends": {(100.7, 14.4): ("STACK-4", "riser A/P4.1, keynote 16, \"4\"W UP (26 DFU)\""),
                       (99.1, 27.4): ("STACK-3", "keynote 16, leader \"3\"W UP, TYP.\"")}},
    "B-104": {"tie": (138.7, -2.1), "tie_basis": "keynote 1 at grid 1, P1.02",
              "ends": {(122.5, 40.4): ("STACK-4", "riser A/P4.1 at KS, keynote 16, \"4\"W UP (26 DFU)\""),
                       (147.8, 14.1): ("WC", "WC; leader \"3\"W UP, TYP.\"")}},
}


def grid_calibration(page, M):
    """Return grid bubble centres (sheet points) and the measured scale."""
    bubbles = defaultdict(list)
    for w in page.get_text("words"):
        if w[4] in GRID_X or w[4] in GRID_Y:
            c = (pymupdf.Point(w[0], w[1]) + pymupdf.Point(w[2], w[3])) / 2 * M
            bubbles[w[4]].append((c.x, c.y))
    # Column bubbles sit in one row (y ~ 732); row bubbles at both ends of the plan.
    col = {k: min(v, key=lambda p: abs(p[1] - 732))[0] for k, v in bubbles.items() if k in GRID_X}
    row = {k: sorted(v, key=lambda p: p[0])[0][1] for k, v in bubbles.items() if k in GRID_Y}
    scale_x = (col["M"] - col["A"]) / (GRID_X["M"] - GRID_X["A"])
    scale_y = (row["6"] - row["1"]) / (GRID_Y["6"] - GRID_Y["1"])
    return col, row, scale_x, scale_y


def new_pipe_lines(page, M):
    out = []
    for p in page.get_drawings():
        if p["type"] != "s" or round(p.get("width") or 0, 2) != 0.96:
            continue
        if tuple(round(x, 2) for x in p["color"]) != (0, 0, 0):
            continue
        for it in p["items"]:
            if it[0] != "l":
                continue
            a, b = it[1] * M, it[2] * M
            if 480 < a.x < 2010 and 600 < a.y < 1420 and a.distance_to(b) > 0.05:
                out.append(LineString([(a.x, a.y), (b.x, b.y)]))
    return out


def networks(lines):
    """Four unit networks; small drafting-gap fragments (<= 6 strokes, <= 3 pt away) rejoin them."""
    blob = unary_union([l.buffer(0.7) for l in lines])
    groups = []
    for poly in getattr(blob, "geoms", [blob]):
        groups.append([l for l in lines if poly.contains(l.centroid)])
    groups.sort(key=lambda g: -sum(l.length for l in g))
    mains, rest = groups[:4], groups[4:]
    joined = []
    for g in rest:
        if len(g) > 6:
            continue                                  # keynote tags carry their own text strokes
        geom = unary_union(g)
        d = [geom.distance(unary_union(m)) for m in mains]
        i = min(range(4), key=d.__getitem__)
        if d[i] <= 3.0:
            mains[i] = mains[i] + g
            joined.append({"strokes": len(g), "length_ft": round(geom.length / PT_PER_FT, 2),
                           "gap_pt": round(d[i], 2)})
    mains.sort(key=lambda m: min(l.bounds[0] for l in m))
    return mains, joined


def node_graph(lines):
    """Snap branch ends onto trunks, node every crossing/tee, return (nodes, edges)."""
    whole = unary_union(lines)
    snapped = [snap(l, whole, SNAP) for l in lines]
    noded = unary_union(snapped)
    key = lambda p: (round(p[0] / 0.5), round(p[1] / 0.5))
    nodes, edges = {}, []
    for seg in getattr(noded, "geoms", [noded]):
        cs = list(seg.coords)
        for a, b in zip(cs, cs[1:]):
            ka, kb = key(a), key(b)
            nodes.setdefault(ka, a); nodes.setdefault(kb, b)
            if ka != kb:
                edges.append((ka, kb))
    edges = list({tuple(sorted(e)) for e in edges})
    return nodes, edges


def classify_end(pt, words):
    """Nearest fixture tag (WC, LAV, SHR, TUB, KS, WB) within 22 pt of a pipe end; else END."""
    near = sorted((math.hypot(x - pt[0], y - pt[1]), t) for (x, y), t in words)
    close = [t for d, t in near if d < 22]
    for tag in ("WC", "LAV", "SHR", "TUB", "KS", "WB"):
        if tag in close[:3]:
            return tag
    return "END"


def main(pdf):
    doc = pymupdf.open(pdf)
    page = doc[PAGE]
    M = page.rotation_matrix
    col, row, sx, sy = grid_calibration(page, M)
    words = []
    for w in page.get_text("words"):
        c = (pymupdf.Point(w[0], w[1]) + pymupdf.Point(w[2], w[3])) / 2 * M
        words.append(((c.x, c.y), w[4]))

    origin = (col["A"], row["1"])
    to_ft = lambda p: ((p[0] - origin[0]) / PT_PER_FT, (p[1] - origin[1]) / PT_PER_FT)

    nets, joined = networks(new_pipe_lines(page, M))
    assert len(nets) == 4, f"expected 4 unit networks, found {len(nets)}"
    spec_units = []
    for unit, lines in zip(UNITS, nets):
        nodes, edges = node_graph(lines)
        adj = defaultdict(dict)
        for a, b in edges:
            L = math.dist(nodes[a], nodes[b]); adj[a][b] = L; adj[b][a] = L
        ov = REVIEWED[unit]
        to_pt = lambda f: (origin[0] + f[0] * PT_PER_FT, origin[1] + f[1] * PT_PER_FT)
        leaves = lambda: [k for k in adj if len(adj[k]) == 1]
        tie = min(leaves(), key=lambda k: math.dist(nodes[k], to_pt(ov["tie"])))
        assert math.dist(nodes[tie], to_pt(ov["tie"])) < PT_PER_FT, f"{unit}: reviewed tie-in not found"
        # The 2-way cleanout symbol at the POC is drawn in the same pen as the pipe: drop every
        # stroke within 2.5 ft of the POC that is not on the pipe itself (stubs and tiny loops).
        def tree():
            dist = {tie: 0.0}; prev = {}; pq = [(0.0, tie)]
            while pq:
                d, k = heapq.heappop(pq)
                if d > dist[k]:
                    continue
                for n, L in adj[k].items():
                    if d + L < dist.get(n, 1e18):
                        dist[n] = d + L; prev[n] = k; heapq.heappush(pq, (d + L, n))
            return dist, prev
        pruned = 0
        while True:
            dist, prev = tree()
            on_tree = {tuple(sorted((k, p))) for k, p in prev.items()}
            near = lambda k: math.dist(nodes[k], nodes[tie]) < 2.5 * PT_PER_FT
            junk = [k for k in leaves() if k != tie and near(k) and classify_end(nodes[k], words) == "END"]
            junk_edges = [(a, b) for a in adj for b in adj[a] if a < b and near(a) and near(b)
                          and (a, b) not in on_tree and adj[a][b] < PT_PER_FT]
            if not junk and not junk_edges:
                break
            for k in junk:
                for n in adj.pop(k):
                    adj[n].pop(k, None)
                pruned += 1
            for a_, b_ in junk_edges:
                adj[a_].pop(b_, None); adj[b_].pop(a_, None); pruned += 1
        assert len(dist) == len(adj), f"{unit}: network not fully connected after noding"
        ends = []
        for k in leaves():
            if k == tie:
                continue
            kind, note = classify_end(nodes[k], words), "fixture tag within 22 pt on P1.02"
            for xy, (k2, n2) in ov["ends"].items():
                if math.dist(nodes[k], to_pt(xy)) < PT_PER_FT:
                    kind, note = k2, n2
            ends.append({"node": k, "kind": kind, "basis": note})
        # Sizes: runs from the POC to a stack, and to the most remote end, are the 4" building
        # drain (P1.02 "4" WASTE, TYP." / "4"W"); other branches take the largest fixture they
        # serve (P1.02 labels "3"W UP" at WC/WB, "2"W UP" at LAV; keynotes 4-7: 2" W).
        remote = max(ends, key=lambda e: dist[e["node"]])["node"]
        end_in = {"STACK-4": 4, "STACK-3": 4, "WC": 3, "WB": 3, "TEE": 0}
        size, load = {}, defaultdict(int)
        for e in ends:
            k = e["node"]
            nominal = 4 if k == remote else end_in.get(e["kind"], 2)
            while k != tie:
                p = prev[k]; ek = tuple(sorted((k, p)))
                size[ek] = max(size.get(ek, 0), nominal); load[ek] += e["kind"] != "TEE"
                k = p
        edge_list = sorted({tuple(sorted((a, b))) for a in adj for b in adj[a]})
        # Strokes closing a small loop (e.g. two branches drawn into one fitting) are kept as
        # drawn and take the size of the largest run they touch.
        off_tree = [e for e in edge_list if e not in size]
        for a_, b_ in off_tree:
            size[(a_, b_)] = max([v for (x, y), v in size.items() if {x, y} & {a_, b_}] or [2])
        assert sum(adj[a_][b_] for a_, b_ in off_tree) < 2 * PT_PER_FT, f"{unit}: large unexplained loop"
        key = lambda k: f"{k[0]}_{k[1]}"
        spec_units.append({
            "unit": unit,
            "tie_in": {"node": key(tie), "xy_ft": to_ft(nodes[tie]), "basis": ov["tie_basis"]},
            "cleanout_symbol_strokes_dropped": pruned,
            "loop_strokes_kept_ft": sum(adj[a_][b_] for a_, b_ in off_tree) / PT_PER_FT,
            "nodes": {key(k): {"xy_ft": to_ft(nodes[k]), "flow_ft": dist[k] / PT_PER_FT} for k in adj},
            "edges": [{"a": key(a), "b": key(b), "length_ft": math.dist(nodes[a], nodes[b]) / PT_PER_FT,
                       "nominal_in": max(size[(a, b)], 2), "fixtures_served": load[(a, b)]}
                      for a, b in edge_list],
            "ends": [{"node": key(e["node"]), "kind": e["kind"], "basis": e["basis"]} for e in ends],
        })

    spec = {
        "project": "101 Meydenbauer — Building B under-slab waste re-pipe (bid model)",
        "sources": [
            {"id": "P1.02", "doc": "Exhibit A bid set 25-048, sheet P1.02 Waste Plumbing Foundation Plan",
             "rev": "Rev 2 BID SET 08/31/2026 (title block)", "scale": "1/8\" = 1'-0\"",
             "sha256": hashlib.sha256(Path(pdf).read_bytes()).hexdigest()},
            {"id": "10/P5.1", "doc": "Exhibit A sheet P5.1 detail 10 Trench Infill",
             "note": "2'-0\" typ. trench (1'-3\" min); pour-back thicker of existing or 5\" min"},
            {"id": "2/P5.0", "doc": "Exhibit A sheet P5.0 detail 2 Bedding", "note": "4\" bedding below pipe"},
            {"id": "SOR", "doc": "Scope of Repair 25-048 (09/18/2026, reissued Addendum 1 10/16/2026)",
             "note": "recorded depths 2-1/2 to 4-1/2 ft; replace from 18\" outside footprint inward"},
            {"id": "SOR-Fig3-4", "doc": "SOR Figures 3 and 4", "note": "ABS 6\" OD 6.625\"; 4\" OD 4.5\""},
            {"id": "BF-A1", "doc": "Bid Form 00 41 13, Addendum 1", "note": "Allowance 7 = 700 SF slab cut/excavate/backfill/patch"},
        ],
        "calibration": {
            "pt_per_ft_assumed": PT_PER_FT,
            "measured_x_pt_per_ft": sx, "measured_y_pt_per_ft": sy,
            "grid_columns_pt": col, "grid_rows_pt": row,
            "origin": "grid A / grid 1 intersection; +x south (along the building), +y west",
            "status": "provisional",
            "basis": "scaled from vector linework; scale verified against grid dimension strings A-M and 1-6",
        },
        "units": spec_units,
        "drafting_gaps_joined": joined,
        "provenance": {
            "routes_xy": {"status": "provisional", "source": "P1.02",
                          "note": "drawn route as plotted; KEAD notes the design is diagrammatic and stack locations are to be field verified"},
            "pipe_sizes": {"status": "provisional", "source": "P1.02 labels + keynotes",
                           "basis": "trunks carrying >1 fixture = 4\" (\"4\" WASTE, TYP.\"); ends sized by fixture keynote or \"UP\" label"},
            "depths": {"status": "assumed", "basis": "tie-in invert from SOR recorded range; 1/4\" per ft slope (P1.02) upstream"},
            "slab_thickness": {"status": "assumed", "basis": "not documented; 10/P5.1 pour-back is 5\" min"},
        },
    }
    # Plan underlay for the model: P1.02 rendered at 3 px/pt and cropped to the building.
    # Saved under build/ (git-ignored) because it reproduces the engineer's drawing.
    zoom, ft_box = 3.0, (-12.0, -10.0, 172.0, 70.0)
    pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom))
    bdir = REPO / "build" / "meydenbauer-b"; bdir.mkdir(parents=True, exist_ok=True)
    full = bdir / "_p102_full.png"; pix.save(full)
    from PIL import Image
    x0 = (origin[0] + ft_box[0] * PT_PER_FT) * zoom; y0 = (origin[1] + ft_box[1] * PT_PER_FT) * zoom
    x1 = (origin[0] + ft_box[2] * PT_PER_FT) * zoom; y1 = (origin[1] + ft_box[3] * PT_PER_FT) * zoom
    Image.open(full).crop((round(x0), round(y0), round(x1), round(y1))).save(bdir / "underlay_P1.02.png")
    full.unlink()
    spec["underlay"] = {"file": "build/meydenbauer-b/underlay_P1.02.png", "ft_box": ft_box,
                        "px_per_ft": zoom * PT_PER_FT, "source": "P1.02", "status": "provisional"}
    out = HERE / "meydenbauer-b.spec.json"
    out.write_text(json.dumps(spec, indent=1))
    print(f"scale check: x {sx:.3f} pt/ft, y {sy:.3f} pt/ft (expected {PT_PER_FT})")
    for u in spec_units:
        L = sum(e["length_ft"] for e in u["edges"])
        kinds = defaultdict(int)  # noqa
        for e in u["ends"]:
            kinds[e["kind"]] += 1
        by = defaultdict(float)
        for e in u["edges"]:
            by[e["nominal_in"]] += e["length_ft"]
        print(f'{u["unit"]}: {L:6.1f} LF  ends={dict(kinds)}  by size={ {k: round(v,1) for k,v in sorted(by.items())} }')
    print("wrote", out)


if __name__ == "__main__":
    main(sys.argv[1])
