"""Route QA board: check a route-control CSV and draw it over its plan sheet for sign-off, before any 3D work.

  uv run bm route-qa routes.csv [--fittings fittings.csv] --out build/<site>/route-qa/<name> \
      [--pdf sources/X.pdf --page 3 --control "23.25,0=1210.5,644.2" ... | --controls controls.csv] \
      [--x-dir down --y-dir left] [--focus x0,y0,x1,y1] [--title "B-101 under-slab waste"]

Routes CSV: one row per control point with `system, role, point_seq`, an `x_ft*` and a `y_ft*` column, and
optionally `unit, parent_role, nominal_in, scope_status`. Fittings CSV: `id`, `x_ft*`, `y_ft*`, optionally
`component, demo_status`. Coordinates are plan feet in whatever axes the CSV header names.

Checks (bpy-free; any FAIL exits 1, `--strict` also fails on WARN):
  sequence      every route has >= 2 points, point_seq 1..n, no zero-length segment
  status        every row carries a scope_status; sizes are constant along a route
  connectivity  a route with a parent_role ends on its parent's centreline (--tol-ft)
  duplicates    no two routes model the same length of pipe (collinear overlap)
  fittings      every fitting sits on a route centreline (--tol-ft)
  registration  (with --pdf) control points fit one affine sheet->plan transform within --max-residual-ft

With --pdf the sheet is the underlay, registered by >= 3 control points `x_ft,y_ft=page_x_pt,page_y_pt`
(PDF points, as `bm calibrate` prints them). Take them from the sheet's own grid or dimension strings, never
from the title-block scale. Four or more give a residual; three fit exactly and prove nothing. The board also
reports the share of route length lying on drawing ink: evidence, not proof. Without --pdf the routes are
drawn on a blank grid and the board says so.

Writes <out>.png (board with route schedule, checks and a sign-off block) and <out>.json (checks, lengths,
input hashes). The board is a review aid: illustrative, not a contract document.
"""
import argparse
import csv
import hashlib
import itertools
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

PLAN_W, PLAN_H, SIDE_W, HEAD_H, FOOT_H, PAD = 1700, 1300, 860, 110, 150, 24
COLORS = {"new": (0, 140, 70), "remain": (70, 100, 160), "remove": (200, 40, 30), "other": (120, 60, 160)}
FIT_COLORS = {"REMOVE": (200, 40, 30), "CUT": (230, 120, 0), "CONDITIONAL": (190, 150, 0)}
DIRS = {"right": (1, 0), "left": (-1, 0), "down": (0, 1), "up": (0, -1)}
DISCLAIMER = "Illustrative, not a contract document."


# ----------------------------------------------------------------------------- input
def _col(fields, prefix, path):
    hits = [f for f in fields if f.strip().lower().startswith(prefix)]
    if not hits:
        raise SystemExit(f"{path}: no column starting with '{prefix}' (have: {', '.join(fields)})")
    return hits[0]


def _rows(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        r = csv.DictReader(f)
        return r.fieldnames or [], [{k: (v or "").strip() for k, v in row.items() if k} for row in r]


def load_routes(path):
    """-> (routes, axis names). A route: {key, unit, system, role, parent, pts, seqs, sizes, statuses}."""
    fields, rows = _rows(path)
    xc, yc = _col(fields, "x_ft", path), _col(fields, "y_ft", path)
    for need in ("system", "role", "point_seq"):
        if need not in fields:
            raise SystemExit(f"{path}: missing column '{need}'")
    by = defaultdict(list)
    for n, row in enumerate(rows, start=2):
        try:
            by[(row.get("unit", ""), row["system"], row["role"])].append(
                (int(row["point_seq"]), float(row[xc]), float(row[yc]), row))
        except ValueError as e:
            raise SystemExit(f"{path}:{n}: {e}") from None
    routes = []
    for (unit, system, role), pts in by.items():
        pts.sort(key=lambda p: p[0])
        routes.append({
            "key": "/".join(v for v in (unit, system, role) if v), "unit": unit, "system": system, "role": role,
            "parent": next((p[3].get("parent_role") for p in pts if p[3].get("parent_role")), ""),
            "pts": [(p[1], p[2]) for p in pts], "seqs": [p[0] for p in pts],
            "sizes": [p[3].get("nominal_in", "") for p in pts],
            "statuses": [p[3].get("scope_status", "") for p in pts],
        })
    return routes, (xc, yc)


def load_fittings(path):
    fields, rows = _rows(path)
    xc, yc = _col(fields, "x_ft", path), _col(fields, "y_ft", path)
    return [{"id": r.get("id") or f"row{n}", "xy": (float(r[xc]), float(r[yc])), "component": r.get("component", ""),
             "status": r.get("demo_status", "").upper()} for n, r in enumerate(rows, start=2)]


def load_controls(pairs, path):
    out = []
    for s in pairs or []:
        try:
            plan, page = s.split("=")
            out.append((*map(float, plan.split(",")), *map(float, page.split(",")), f"C{len(out) + 1}"))
        except ValueError:
            raise SystemExit(f"--control '{s}': expected x_ft,y_ft=page_x_pt,page_y_pt") from None
    if path:
        for r in _rows(path)[1]:
            out.append((float(r["x_ft"]), float(r["y_ft"]), float(r["page_x_pt"]), float(r["page_y_pt"]),
                        r.get("label") or f"C{len(out) + 1}"))
    return out


def status_class(text):
    t = text.upper()
    if t.startswith("NEW"):
        return "new"
    if "REMOVE" in t or "DEMO" in t:
        return "remove"
    if any(k in t for k in ("REMAIN", "EXISTING", "PRIOR")):
        return "remain"
    return "other"


# ----------------------------------------------------------------------------- geometry
def seg_dist(p, a, b):
    ax, ay, bx, by = *a, *b
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy
    t = 0 if L2 == 0 else max(0, min(1, ((p[0] - ax) * dx + (p[1] - ay) * dy) / L2))
    return math.hypot(p[0] - ax - t * dx, p[1] - ay - t * dy)


def segments(route):
    return list(zip(route["pts"], route["pts"][1:]))


def route_dist(p, route):
    return min((seg_dist(p, a, b) for a, b in segments(route)), default=math.inf)


def length(route):
    return sum(math.dist(a, b) for a, b in segments(route))


def overlap(s, t, tol):
    """Length two segments share when they lie on the same line (within tol)."""
    (a, b), (c, d) = s, t
    L = math.dist(a, b)
    if L == 0 or math.dist(c, d) == 0:
        return 0.0
    ux, uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
    off = [abs((p[0] - a[0]) * uy - (p[1] - a[1]) * ux) for p in (c, d)]
    if max(off) > tol:
        return 0.0
    lo, hi = sorted(((p[0] - a[0]) * ux + (p[1] - a[1]) * uy) for p in (c, d))
    return max(0.0, min(hi, L) - max(lo, 0.0))


def fit_affine(controls):
    """Plan ft -> page pt, least squares. Returns (M 2x3, per-control residual in ft, pt per ft on each axis)."""
    A = np.array([[c[0], c[1], 1.0] for c in controls])
    B = np.array([[c[2], c[3]] for c in controls])
    if len(controls) < 3 or np.linalg.matrix_rank(A, tol=1e-6) < 3:
        raise SystemExit("registration needs at least 3 control points that are not on one line")
    M = np.linalg.lstsq(A, B, rcond=None)[0].T
    sx, sy = float(np.hypot(*M[:, 0])), float(np.hypot(*M[:, 1]))
    res = np.hypot(*(A @ M.T - B).T) / math.sqrt(sx * sy)
    return M, [float(r) for r in res], (sx, sy)


# ----------------------------------------------------------------------------- checks
def run_checks(routes, fittings, tol):
    out = []

    def add(name, problems, warns=(), ok=""):
        level = "fail" if problems else "warn" if warns else "pass"
        out.append({"name": name, "level": level, "detail": "; ".join([*problems, *warns]) or ok})

    bad = []
    for r in routes:
        if len(r["pts"]) < 2:
            bad.append(f"{r['key']} has {len(r['pts'])} point")
        if r["seqs"] != list(range(1, len(r["seqs"]) + 1)):
            bad.append(f"{r['key']} point_seq is {r['seqs']}, expected 1..{len(r['seqs'])}")
        bad += [f"{r['key']} repeats point {a}" for a, b in segments(r) if math.dist(a, b) == 0]
    add("sequence", bad, ok=f"{len(routes)} routes, {sum(len(r['pts']) for r in routes)} control points")

    missing = [f"{r['key']} point {s} has no scope_status" for r in routes for s, st in zip(r["seqs"], r["statuses"]) if not st]
    sizes = [f"{r['key']} has no nominal_in" if set(r["sizes"]) == {""} else f"{r['key']} changes size {sorted(set(r['sizes']))}"
             for r in routes if len(set(r["sizes"])) > 1 or set(r["sizes"]) == {""}]
    fv = sum("FIELD VERIFY" in st.upper() for r in routes for st in r["statuses"])
    add("status", missing, sizes, ok=f"every point has a status; {fv} points tagged FIELD VERIFY")

    bad, warns, n = [], [], 0
    for r in routes:
        if not r["parent"] or len(r["pts"]) < 2:
            continue
        n += 1
        same = [o for o in routes if o is not r and o["unit"] == r["unit"]]
        parents = [o for o in same if o["role"] == r["parent"]] or [o for o in same if o["system"] == r["parent"]]
        named = bool(parents)
        if not named:
            parents = same
        dist = {o["key"]: min(route_dist(r["pts"][0], o), route_dist(r["pts"][-1], o)) for o in parents}
        d = min(dist.values(), default=math.inf)
        hit = ", ".join(k for k, v in dist.items() if v <= tol)
        if d > tol:
            bad.append(f"{r['key']} ends {d:.2f} ft from parent '{r['parent']}'")
        elif not named:
            warns.append(f"{r['key']}: parent '{r['parent']}' is not a role or system; it does end on {hit}")
    add("connectivity", bad, warns, ok=f"routes with a parent: {n}, each ends on it within {tol} ft")

    bad = []
    for i, r in enumerate(routes):
        for o in routes[i + 1:]:
            shared = sum(overlap(s, t, tol) for s in segments(r) for t in segments(o))
            if shared > tol:
                bad.append(f"{r['key']} and {o['key']} both model {shared:.2f} ft of the same pipe")
    add("duplicates", bad, ok="no pipe is modelled twice")

    if fittings is not None:
        bad = []
        for f in fittings:
            d = min((route_dist(f["xy"], r) for r in routes), default=math.inf)
            if d > tol:
                bad.append(f"{f['id']} is {d:.2f} ft off the nearest route")
        ids = [f["id"] for f in fittings]
        dup = sorted({i for i in ids if ids.count(i) > 1})
        add("fittings", bad + [f"duplicate fitting id {i}" for i in dup], ok=f"{len(fittings)} fittings on a route within {tol} ft")
    return out


def registration_check(controls, residuals, scales, max_res):
    worst = max(residuals)
    name = controls[residuals.index(worst)][4]
    aniso = abs(scales[0] / scales[1] - 1)
    detail = (f"{len(controls)} controls, {scales[0]:.3f} x {scales[1]:.3f} pt/ft, "
              f"max residual {worst:.3f} ft at {name} (limit {max_res} ft)")
    if worst > max_res:
        return {"name": "registration", "level": "fail", "detail": detail}
    if len(controls) == 3:
        return {"name": "registration", "level": "warn",
                "detail": f"3 controls fit exactly, so the registration is unchecked; add a fourth. {detail}"}
    if aniso > 0.02:
        return {"name": "registration", "level": "warn", "detail": f"x and y scales differ by {aniso:.1%}. {detail}"}
    return {"name": "registration", "level": "pass", "detail": detail}


# ----------------------------------------------------------------------------- board
def _font(size, bold=False, mono=False):
    try:
        return ImageFont.truetype("DejaVuSansMono.ttf" if mono else "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf", size)
    except OSError:
        return ImageFont.load_default(size)


def _window(points):
    """View rectangle (u0, v0, scale) that fits the points in the plan panel with a margin."""
    us, vs = [p[0] for p in points], [p[1] for p in points]
    w, h = (max(us) - min(us)) or 1.0, (max(vs) - min(vs)) or 1.0
    s = min(PLAN_W / (w * 1.3), PLAN_H / (h * 1.3))
    return (min(us) + max(us)) / 2 - PLAN_W / s / 2, (min(vs) + max(vs)) / 2 - PLAN_H / s / 2, s


def _underlay(pdf, page_no, u0, v0, s):
    import pymupdf
    page = pymupdf.open(pdf)[page_no - 1]
    clip = pymupdf.Rect(u0, v0, u0 + PLAN_W / s, v0 + PLAN_H / s)
    pix = page.get_pixmap(matrix=pymupdf.Matrix(s, s), clip=clip & page.rect, colorspace=pymupdf.csGRAY)
    grey = np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.width)
    full = np.full((PLAN_H, PLAN_W), 255, np.uint8)
    ox, oy = round((max(clip.x0, page.rect.x0) - u0) * s), round((max(clip.y0, page.rect.y0) - v0) * s)
    h, w = min(grey.shape[0], PLAN_H - oy), min(grey.shape[1], PLAN_W - ox)
    full[oy:oy + h, ox:ox + w] = grey[:h, :w]
    return full, page.rotation


def ink_agreement(ink, routes, to_px, px_per_ft, tol_ft):
    """Share of route length (sampled every 0.25 ft) with drawing ink within tol_ft. Evidence, not proof."""
    r = max(1, round(tol_ft * px_per_ft))
    near = ink.copy()
    for dy in range(-r, r + 1):  # dilate by a disc without needing opencv
        w = int(math.sqrt(r * r - dy * dy))
        rows = np.roll(ink, dy, axis=0)
        for dx in range(-w, w + 1):
            near |= np.roll(rows, dx, axis=1)
    hit = tot = 0
    for route in routes:
        for a, b in segments(route):
            for t in np.linspace(0, 1, max(2, int(math.dist(a, b) / 0.25) + 1)):
                x, y = to_px((a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])))
                if 0 <= int(y) < PLAN_H and 0 <= int(x) < PLAN_W:
                    tot += 1
                    hit += bool(near[int(y), int(x)])
    return hit / tot if tot else None


def draw_board(routes, fittings, checks, to_px, px_per_ft, axes, axis_names, meta, underlay=None, controls=()):
    W, H = PAD * 3 + PLAN_W + SIDE_W, HEAD_H + PLAN_H + FOOT_H + PAD
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)
    f_s, f_m, f_b, f_t = _font(17), _font(21), _font(21, True), _font(34, True)
    ox, oy = PAD, HEAD_H
    if underlay is not None:
        img.paste(Image.fromarray((255 - (255 - underlay.astype(np.int16)) * 0.45).astype(np.uint8)), (ox, oy))
    else:
        step = 5 * px_per_ft
        for i in range(int(PLAN_W / step) + 1):
            d.line([ox + i * step, oy, ox + i * step, oy + PLAN_H], fill=(232, 232, 232))
        for i in range(int(PLAN_H / step) + 1):
            d.line([ox, oy + i * step, ox + PLAN_W, oy + i * step], fill=(232, 232, 232))
        d.text((ox + 12, oy + 10), "NO SHEET UNDERLAY: routes only, 5 ft grid", font=f_b, fill=(170, 0, 0))
    d.rectangle([ox, oy, ox + PLAN_W, oy + PLAN_H], outline="black", width=2)
    P = lambda p: (ox + to_px(p)[0], oy + to_px(p)[1])

    for n, r in enumerate(routes, start=1):
        col = COLORS[status_class(r["statuses"][0])]
        size = float(r["sizes"][0] or 2)
        pts = [P(p) for p in r["pts"]]
        d.line(pts, fill=col, width=int(3 + size), joint="curve")
        for p in pts:
            d.ellipse([p[0] - 5, p[1] - 5, p[0] + 5, p[1] + 5], fill="white", outline=col, width=2)
        a, b = max(itertools.pairwise(pts), key=lambda s: math.dist(*s), default=(pts[0], pts[0]))
        cx, cy = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        d.ellipse([cx - 15, cy - 15, cx + 15, cy + 15], fill="white", outline=col, width=3)
        d.text((cx, cy), str(n), font=f_s, fill="black", anchor="mm")

    stacks = defaultdict(list)
    for f in fittings or []:
        x, y = P(f["xy"])
        stacks[(round(x / 6), round(y / 6))].append((x, y, f))
    for group in stacks.values():
        x, y, f0 = group[0]
        col = FIT_COLORS.get(f0["status"], (40, 40, 40))
        d.line([x - 7, y - 7, x + 7, y + 7], fill=col, width=3)
        d.line([x - 7, y + 7, x + 7, y - 7], fill=col, width=3)
        d.text((x + 9, y - 22), "/".join(g[2]["id"] for g in group), font=f_s, fill=col,
               stroke_width=3, stroke_fill="white")
    for c in controls:
        x, y = P((c[0], c[1]))
        d.rectangle([x - 9, y - 9, x + 9, y + 9], outline=(0, 0, 0), width=2)
        d.line([x - 14, y, x + 14, y], fill="black")
        d.line([x, y - 14, x, y + 14], fill="black")
        d.text((x + 12, y + 8), c[4], font=f_s, fill="black", stroke_width=3, stroke_fill="white")

    # anything drawn past the plan frame (cropped views) is masked before the panels go on
    for box in ([0, 0, W, oy - 1], [0, oy + PLAN_H + 1, W, H], [0, 0, ox - 1, H], [ox + PLAN_W + 1, 0, W, H]):
        d.rectangle(box, fill="white")
    d.rectangle([ox, oy, ox + PLAN_W, oy + PLAN_H], outline="black", width=2)

    # scale bar and plan axes
    bx, byy = ox + 30, oy + PLAN_H - 40
    d.line([bx, byy, bx + 5 * px_per_ft, byy], fill="black", width=5)
    d.text((bx, byy - 28), "5 ft", font=f_m, fill="black", stroke_width=3, stroke_fill="white")
    cx, cy = ox + PLAN_W - 120, oy + PLAN_H - 110
    for (ux, uy), name in zip(axes, axis_names):
        d.line([cx, cy, cx + ux * 70, cy + uy * 70], fill="black", width=3)
        d.text((cx + ux * 86, cy + uy * 86), "+" + name.split("_ft")[0], font=f_m, fill="black", anchor="mm",
               stroke_width=3, stroke_fill="white")

    # header and side panel
    verdict = "FAIL" if any(c["level"] == "fail" for c in checks) else "PASS"
    d.text((PAD, 18), meta["title"], font=f_t, fill="black")
    d.text((PAD, 66), f"Route QA board  |  {meta['routes_name']} sha256 {meta['routes_sha'][:12]}"
           + (f"  |  {meta['sheet']}" if meta.get("sheet") else "  |  no sheet"), font=f_m, fill=(60, 60, 60))
    d.text((W - PAD, 18), f"CHECKS: {verdict}", font=f_t, fill=(0, 130, 60) if verdict == "PASS" else (200, 30, 30), anchor="ra")
    x, y = PAD * 2 + PLAN_W, HEAD_H

    def line(text, font=f_s, fill="black", dy=24):
        nonlocal y
        d.text((x, y), text, font=font, fill=fill)
        y += dy

    line("Routes (plan length; axes: " + ", ".join(n.replace("_ft_", " ").replace("_ft", "") for n in axis_names) + ")", f_b, dy=32)
    for n, r in enumerate(routes, start=1):
        cls = status_class(r["statuses"][0])
        fv = " FV" if any("FIELD VERIFY" in s.upper() for s in r["statuses"]) else ""
        size = (r["sizes"][0] or "?") + " in"
        line(f"{n:>2} {(r['system'] + ' / ' + r['role'])[:42]:<42} {size:>6} {length(r):7.2f} ft  {cls}{fv}",
             _font(15, mono=True), COLORS[cls], 21)
    line("FV = FIELD VERIFY in scope_status. Colour: " + ", ".join(COLORS), f_s, (90, 90, 90), 34)
    if fittings:
        line(f"Fittings: {len(fittings)}", f_b, dy=30)
        counts = defaultdict(int)
        for f in fittings:
            counts[(f["status"] or "-", f["component"] or "-")] += 1
        for (st, comp), k in sorted(counts.items()):
            line(f"{k:>3} x {comp[:44]:<44} {st}", _font(15, mono=True), FIT_COLORS.get(st, (40, 40, 40)), 21)
        y += 14
    line("Checks", f_b, dy=30)
    for c in checks:
        col = {"pass": (0, 130, 60), "warn": (190, 120, 0), "fail": (200, 30, 30)}[c["level"]]
        line(f"{c['level'].upper():<5} {c['name']}", f_b, col, 26)
        words, cur = c["detail"].split(), ""
        for w in words:
            if d.textlength(cur + " " + w, font=_font(15)) > SIDE_W - 30:
                line(cur, _font(15), (60, 60, 60), 20)
                cur = w
            else:
                cur = (cur + " " + w).strip()
        line(cur, _font(15), (60, 60, 60), 26)
    for extra in meta.get("notes", []):
        line(extra, _font(15), (60, 60, 60), 22)

    fy = HEAD_H + PLAN_H + 16
    d.text((PAD, fy), DISCLAIMER + " Routes are model controls traced or calibrated from the drawings; "
           "points tagged FIELD VERIFY are unverified.", font=f_m, fill=(170, 0, 0))
    scope = "internally consistent and registered to the sheet" if underlay is not None else \
        "internally consistent; it has NOT been compared with any sheet"
    d.text((PAD, fy + 34), f"Passing checks means the table is {scope}. "
           "It does not mean the routes match as-built conditions.", font=f_s, fill=(60, 60, 60))
    d.text((PAD, fy + 78), "Reviewed by: ______________________    Date: ____________    [  ] accepted for modelling"
           "    [  ] revise and resubmit    Notes: ____________________________________", font=f_m, fill="black")
    return img


# ----------------------------------------------------------------------------- main
def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run(a):
    routes, axis_names = load_routes(a.routes)
    if not routes:
        raise SystemExit(f"{a.routes}: no rows")
    fittings = load_fittings(a.fittings) if a.fittings else None
    checks = run_checks(routes, fittings, a.tol_ft)
    controls = load_controls(a.control, a.controls)
    pts = [p for r in routes for p in r["pts"]] + [f["xy"] for f in fittings or []] + [(c[0], c[1]) for c in controls]
    notes, underlay, report_reg = [], None, None
    if a.pdf:
        M, residuals, scales = fit_affine(controls)
        checks.append(registration_check(controls, residuals, scales, a.max_residual_ft))
        view = lambda p: tuple(M @ (p[0], p[1], 1.0))
        axes = [tuple(M[:, 0] / scales[0]), tuple(M[:, 1] / scales[1])]
        report_reg = {"controls": [{"label": c[4], "plan_ft": c[:2], "page_pt": c[2:4], "residual_ft": round(r, 4)}
                                   for c, r in zip(controls, residuals)], "pt_per_ft": [round(s, 4) for s in scales]}
    else:
        if controls:
            raise SystemExit("--control/--controls need --pdf and --page")
        (ux, uy), (vx, vy) = DIRS[a.x_dir], DIRS[a.y_dir]
        if ux * vx + uy * vy != 0:
            raise SystemExit("--x-dir and --y-dir must be perpendicular")
        view = lambda p: (p[0] * ux + p[1] * vx, p[0] * uy + p[1] * vy)
        axes, scales = [(ux, uy), (vx, vy)], (1.0, 1.0)
    if a.focus:
        try:
            fx0, fy0, fx1, fy1 = map(float, a.focus.split(","))
        except ValueError:
            raise SystemExit("--focus expects x0_ft,y0_ft,x1_ft,y1_ft") from None
        pts = [(fx0, fy0), (fx0, fy1), (fx1, fy0), (fx1, fy1)]
        notes.append(f"View cropped to plan x {fx0:g}..{fx1:g} ft, y {fy0:g}..{fy1:g} ft; checks cover the whole table.")
    u0, v0, s = _window([view(p) for p in pts])
    to_px = lambda p: ((view(p)[0] - u0) * s, (view(p)[1] - v0) * s)
    px_per_ft = s * math.sqrt(scales[0] * scales[1])
    ink_share = None
    if a.pdf:
        underlay, rotation = _underlay(a.pdf, a.page, u0, v0, s)
        if rotation:
            notes.append(f"WARN: sheet page is rotated {rotation} deg; control points on rotated pages are untested.")
        ink_share = ink_agreement(underlay < 128, routes, to_px, px_per_ft, a.ink_tol_ft)
        if ink_share is not None:
            notes.append(f"Evidence, not proof: {ink_share:.0%} of route length lies within {a.ink_tol_ft} ft of drawing ink.")
    if a.strict:
        for c in checks:
            c["level"] = "fail" if c["level"] == "warn" else c["level"]
    meta = {"title": a.title or Path(a.routes).stem, "routes_name": Path(a.routes).name, "routes_sha": sha(a.routes),
            "sheet": f"{Path(a.pdf).name} p.{a.page}" if a.pdf else None, "notes": notes}
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    board = draw_board(routes, fittings, checks, to_px, px_per_ft, axes, axis_names, meta, underlay, controls)
    board.save(out.with_suffix(".png"))
    failed = [c for c in checks if c["level"] == "fail"]
    report = {
        "verdict": "fail" if failed else "pass", "checks": checks, "tolerance_ft": a.tol_ft,
        "inputs": {"routes": {"file": Path(a.routes).name, "sha256": meta["routes_sha"]},
                   **({"fittings": {"file": Path(a.fittings).name, "sha256": sha(a.fittings)}} if a.fittings else {}),
                   **({"sheet": {"file": Path(a.pdf).name, "page": a.page, "sha256": sha(a.pdf)}} if a.pdf else {})},
        "routes": [{"key": r["key"], "parent": r["parent"], "nominal_in": r["sizes"][0], "points": len(r["pts"]),
                    "plan_length_ft": round(length(r), 3), "class": status_class(r["statuses"][0]),
                    "field_verify": any("FIELD VERIFY" in s.upper() for s in r["statuses"])} for r in routes],
        "fittings": len(fittings) if fittings is not None else None,
        "registration": report_reg, "ink_agreement": None if ink_share is None else round(ink_share, 4),
        "disclaimer": DISCLAIMER,
    }
    out.with_suffix(".json").write_text(json.dumps(report, indent=2) + "\n")
    for c in checks:
        print(f"{c['level'].upper():<5} {c['name']}: {c['detail']}")
    for n in notes:
        print(n)
    print(f"**{'FAIL' if failed else 'PASS'}** — {len(checks) - len(failed)}/{len(checks)} checks -> {out.with_suffix('.png')}")
    return report


def main(argv=None):
    ap = argparse.ArgumentParser(prog="bm route-qa", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("routes", help="route-control CSV")
    ap.add_argument("--fittings", help="fitting schedule CSV")
    ap.add_argument("--out", required=True, help="output path without extension (writes .png and .json)")
    ap.add_argument("--title")
    ap.add_argument("--pdf", help="plan sheet PDF used as the underlay")
    ap.add_argument("--page", type=int, default=1, help="1-based page")
    ap.add_argument("--control", action="append", metavar="X_FT,Y_FT=PAGE_X_PT,PAGE_Y_PT", help="repeat, >= 3")
    ap.add_argument("--controls", help="CSV with x_ft,y_ft,page_x_pt,page_y_pt[,label]")
    ap.add_argument("--x-dir", choices=DIRS, default="right", help="screen direction of +x without --pdf")
    ap.add_argument("--y-dir", choices=DIRS, default="up", help="screen direction of +y without --pdf")
    ap.add_argument("--focus", metavar="X0,Y0,X1,Y1", help="crop the view to this plan-ft box (checks still cover everything)")
    ap.add_argument("--tol-ft", type=float, default=0.05, help="connectivity / fitting / overlap tolerance")
    ap.add_argument("--max-residual-ft", type=float, default=0.25, help="registration limit")
    ap.add_argument("--ink-tol-ft", type=float, default=0.25, help="distance that counts as 'on drawing ink'")
    ap.add_argument("--strict", action="store_true", help="warnings fail too")
    a = ap.parse_args(argv)
    if a.pdf and not (a.control or a.controls):
        raise SystemExit("--pdf needs control points (--control ... or --controls file.csv)")
    return 1 if run(a)["verdict"] == "fail" else 0


if __name__ == "__main__":
    sys.exit(main())
