"""Plan takeoff: extract walls, windows and perimeter door openings from a vector PDF floor plan.

Usage:
    uv run bm extract <plan.pdf> --page N --clip x0,y0,x1,y1 --pt-per-ft 18
        --center-px CX --rear-px RY --half right --out takeoff/<name>.json

Method (all at an exact 2 px per inch raster of the sheet):
  * Walls are drawn as hollow outlines, so the white core between the two faces
    is a thin enclosed region. Cores with half-width 2.5-7.5 px (wall 5-15 in)
    are wall; cores under 2.3 px half-width inside the wall band are window glazing.
  * Door openings are perimeter gaps between collinear wall ends.
  * Output coordinates: inches, X from party-wall centerline (+ = right unit),
    Y from rear wall face toward the front. Only one half is extracted when the
    units are mirror images; the builder mirrors it.
Everything this produces is status 'provisional' (scaled from a drawing whose
scale was verified against its dimension strings); checks in the spec compare it
to the documented dimensions.
"""
import argparse, json
import numpy as np, cv2, pymupdf as fitz

PX_PER_IN = 2


def raster(pdf, page, clip, pt_per_ft):
    d = fitz.open(pdf)
    pt_per_in = pt_per_ft / 12
    dpi = int(round(PX_PER_IN * 72 / pt_per_in))
    pix = d[page].get_pixmap(clip=fitz.Rect(*clip), dpi=dpi, colorspace=fitz.csGRAY)
    a = np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.width)
    return (a < 128).astype(np.uint8)


def cores(ink):
    white = 1 - ink
    n, lab, st, _ = cv2.connectedComponentsWithStats(white, connectivity=4)
    dt = cv2.distanceTransform(white, cv2.DIST_L2, 3)
    mx = np.zeros(n); np.maximum.at(mx, lab.ravel(), dt.ravel())
    return n, lab, st, mx


def extract(ink, cx, ry, half):
    n, lab, st, mx = cores(ink)
    band = np.zeros(n, bool)
    for i in range(1, n):  # pass 1: anything thin & elongated = wall band candidate
        x, y, w, h, a = st[i]; L, S = max(w, h), min(w, h)
        if mx[i] <= 7.5 and a >= 60 and (L >= 60 or (L / S >= 1.8 and a / (w * h) > 0.5 and L >= 16)):
            band[i] = True
    bandm = cv2.dilate(band[lab].astype(np.uint8), np.ones((3, 3), np.uint8))
    wallc = np.zeros(n, bool); winc = np.zeros(n, bool)
    for i in range(1, n):
        x, y, w, h, a = st[i]; L, S = max(w, h), min(w, h)
        if not bandm[y:y + h, x:x + w].any():
            continue
        if 2.5 <= mx[i] <= 7.5 and band[i]:
            wallc[i] = True
        elif mx[i] < 2.3 and L >= 12 and L / max(S, 1) >= 3:
            winc[i] = True
    wall = cv2.dilate(wallc[lab].astype(np.uint8), np.ones((3, 3), np.uint8))
    win = cv2.dilate(winc[lab].astype(np.uint8), np.ones((5, 5), np.uint8))
    n3, l3, s3, _ = cv2.connectedComponentsWithStats(wall, connectivity=8)
    for i in range(1, n3):
        if max(s3[i][2], s3[i][3]) < 30:
            wall[l3 == i] = 0
    glaze = win.copy()           # glazing strips stay in the wall mask; openings are cut from the spec
    # keep one half
    H, W = wall.shape
    if half == "right":
        wall[:, :cx] = 0; win[:, :cx] = 0; glaze[:, :cx] = 0
    wall = np.maximum(wall, (glaze > 0) & (cv2.dilate(wall, np.ones((9, 9), np.uint8)) > 0)).astype(np.uint8)
    # footprint of this half (close openings up to 18 ft along walls)
    solid = np.maximum(wall, win); P = 400; k = np.pad(solid, P); K = 24 * 18
    c = cv2.morphologyEx(k, cv2.MORPH_CLOSE, np.ones((1, K), np.uint8))
    c = cv2.morphologyEx(c, cv2.MORPH_CLOSE, np.ones((K, 1), np.uint8))
    c = np.maximum(c, k)
    cs, _ = cv2.findContours(c, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    big = max(cs, key=cv2.contourArea)
    fp = np.zeros_like(c); cv2.drawContours(fp, [big], -1, 1, -1); fp = fp[P:-P, P:-P]
    if half == "right":
        fp[:, :cx] = 0
    edge = fp - cv2.erode(fp, np.ones((41, 41), np.uint8))
    edge[:, cx - 25:cx + 25] = 0  # party wall is not perimeter
    to_in = lambda x, y: (round((x - cx) / PX_PER_IN, 1), round((y - ry) / PX_PER_IN, 1))

    def boxes(mask, min_len):
        out = []
        n, l, s, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
        for i in range(1, n):
            x, y, w, h, a = s[i]
            if max(w, h) < min_len or min(w, h) > 20:
                continue
            if edge[y:y + h, x:x + w].mean() < 0.9:
                continue
            x0, y0 = to_in(x, y); x1, y1 = to_in(x + w, y + h)
            out.append({"x0": x0, "y0": y0, "x1": x1, "y1": y1, "axis": "x" if w >= h else "y"})
        return out

    windows = boxes(win, 20)
    # perimeter gaps (doors): closed band minus walls/windows
    gapsm = ((cv2.morphologyEx(np.pad(wall | win, P), cv2.MORPH_CLOSE, np.ones((1, K), np.uint8)) |
              cv2.morphologyEx(np.pad(wall | win, P), cv2.MORPH_CLOSE, np.ones((K, 1), np.uint8)))[P:-P, P:-P]
             & (1 - (wall | win)) & edge)
    gapsm = cv2.morphologyEx(gapsm.astype(np.uint8), cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    doors = boxes(gapsm, 48)
    # wall polygons (outer rings + holes), inches
    cs, hier = cv2.findContours(wall, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
    rings = []
    for i, cnt in enumerate(cs):
        ap = cv2.approxPolyDP(cnt, 1.0, True).reshape(-1, 2)
        if len(ap) < 3 or cv2.contourArea(cnt) < 40:
            continue
        rings.append({"hole": bool(hier[0][i][3] >= 0), "pts": [to_in(x, y) for x, y in ap]})
    rects = []  # axis-aligned rectangle decomposition (row runs merged down columns)
    active = {}
    for yy in range(wall.shape[0] + 1):
        row = wall[yy] if yy < wall.shape[0] else np.zeros(wall.shape[1], np.uint8)
        d = np.diff(np.concatenate([[0], row, [0]]).astype(np.int8))
        runs = set(zip(np.where(d == 1)[0], np.where(d == -1)[0]))
        for r in list(active):
            if r not in runs:
                x0p, x1p = r; y0p = active.pop(r)
                a0 = to_in(x0p, y0p); a1 = to_in(x1p, yy)
                rects.append([a0[0], a0[1], a1[0], a1[1]])
        for r in runs:
            if r not in active:
                active[r] = yy
    fcs, _ = cv2.findContours(fp, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    fring = [to_in(x, y) for x, y in cv2.approxPolyDP(max(fcs, key=cv2.contourArea), 1.0, True).reshape(-1, 2)]
    dbg = np.full(ink.shape + (3,), 255, np.uint8); dbg[ink > 0] = (205, 205, 205); dbg[wall > 0] = (0, 0, 0)
    for o, col in [(windows, (0, 140, 255)), (doors, (255, 80, 0))]:
        for i, b in enumerate(o):
            p0 = (int(b["x0"] * PX_PER_IN + cx), int(b["y0"] * PX_PER_IN + ry)); p1 = (int(b["x1"] * PX_PER_IN + cx), int(b["y1"] * PX_PER_IN + ry))
            cv2.rectangle(dbg, p0, p1, col, 3)
            cv2.putText(dbg, f"{'W' if col[0] == 0 else 'D'}{i} {b['x0']:.0f},{b['y0']:.0f}", (p0[0], p0[1] - 4), 0, 0.45, col, 1)
    extract.debug = dbg
    return {"wall_rects": rects, "wall_rings": rings, "footprint": fring, "windows": windows, "doors": doors}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf"); ap.add_argument("--page", type=int, required=True)
    ap.add_argument("--clip", required=True); ap.add_argument("--pt-per-ft", type=float, required=True)
    ap.add_argument("--center-px", type=int, required=True); ap.add_argument("--rear-px", type=int, required=True)
    ap.add_argument("--half", default="right"); ap.add_argument("--out", required=True)
    a = ap.parse_args()
    ink = raster(a.pdf, a.page - 1, [float(v) for v in a.clip.split(",")], a.pt_per_ft)
    res = extract(ink, a.center_px, a.rear_px, a.half)
    res["meta"] = {"pdf": a.pdf.split("/")[-1], "page": a.page, "clip": a.clip, "pt_per_ft": a.pt_per_ft,
                   "px_per_in": PX_PER_IN, "center_px": a.center_px, "rear_px": a.rear_px, "half": a.half}
    json.dump(res, open(a.out, "w"), indent=1)
    cv2.imwrite(a.out.rsplit(".", 1)[0] + "_review.png", extract.debug)
    print(f"walls rings={len(res['wall_rings'])} windows={len(res['windows'])} doors={len(res['doors'])}")
