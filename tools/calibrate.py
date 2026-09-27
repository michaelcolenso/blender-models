"""Calibration helpers so an operator never has to eyeball scales or pixel offsets.

  sheets  List pages with their own sheet number (title block) and drawing titles.
          python tools/calibrate.py sheets <pdf>

  scale   Find a sheet's true scale from one of its own dimension strings.
          python tools/calibrate.py scale <pdf> --page 4 --text "39-0" --feet 39
          -> tick positions, pt/ft, and the implied scale (18 pt/ft = 1/4" = 1'-0").
          Always cross-check with a second, different string (--text "78-0" --feet 78).

  plan    Suggest --center-px / --rear-px for extract_plan.py from a pair of tick marks
          (e.g. the overall-width string's ends) and the rear wall face.
          python tools/calibrate.py plan <pdf> --page 4 --clip x0,y0,x1,y1 --pt-per-ft 18 \
                 --left-tick-pt 676.75 --right-tick-pt 2080.75

  outline List the heaviest orthogonal lines (roof-plan eave/fascia outline) in feet from an origin
          python tools/calibrate.py outline <pdf> --page 5 --clip 576,486,2250,1620 --pt-per-ft 18 \
                 --origin-x-pt 1378.8 --origin-y-pt 561.3

  elev    Suggest --floor-row / --center-col for overlay.py on an elevation.
          python tools/calibrate.py elev <pdf> --page 6 --clip x0,y0,x1,y1 --pt-per-ft 9 \
                 --plate-in 109.125 --half-width-in 436
          Finds the pair of long horizontal lines separated by the documented floor-to-plate
          height (FF line and truss-bearing line), and the wall-face columns separated by the
          known wall-to-wall width, and reports the centre.
"""
import argparse, math, sys
import numpy as np, pymupdf as fitz


def segs(page):
    out = []
    for d in page.get_drawings():
        for it in d["items"]:
            if it[0] == "l":
                out.append((it[1].x, it[1].y, it[2].x, it[2].y))
    return out


def ticks_near(page, rect, band=12):
    """Short diagonal segments (architectural dimension ticks) on the dimension line near a text box."""
    cy = (rect.y0 + rect.y1) / 2
    t = []
    for x0, y0, x1, y1 in segs(page):
        L = math.hypot(x1 - x0, y1 - y0)
        if 3 <= L <= 10 and abs(abs(x1 - x0) - abs(y1 - y0)) < 1.0:
            my = (y0 + y1) / 2
            if rect.y0 - 2 <= my <= rect.y1 + band:
                t.append(((x0 + x1) / 2, my))
    return t


def cmd_scale(a):
    page = fitz.open(a.pdf)[a.page - 1]
    hits = page.search_for(a.text)
    if not hits:
        sys.exit(f"text '{a.text}' not found on page {a.page}")
    for r in hits:
        cx = (r.x0 + r.x1) / 2
        t = ticks_near(page, r)
        # ticks on the same dimension line: same y within 1.5 pt of each other
        best = None
        for ty in sorted({round(y, 1) for _, y in t}):
            row = sorted(x for x, y in t if abs(y - ty) < 1.5)
            left = [x for x in row if x < cx]; right = [x for x in row if x > cx]
            if left and right:
                span = min(right) - max(left)
                if best is None or span < best[0]:
                    best = (span, max(left), min(right), ty)
        if not best:
            print(f"'{a.text}' at x={cx:.1f},y={r.y0:.1f}: no bracketing ticks found"); continue
        span, l, rr, ty = best
        ptft = span / a.feet
        scale_in = ptft / 72  # inches of paper per foot
        print(f"'{a.text}' at x={cx:.1f},y={r.y0:.1f}: ticks {l:.2f} -> {rr:.2f} (y={ty}) span {span:.2f} pt "
              f"= {ptft:.3f} pt/ft  = {scale_in:.4f} in of paper per ft  (1/{round(1/scale_in)}\" = 1'-0\" if integer)")


def cmd_plan(a):
    x0, y0, x1, y1 = [float(v) for v in a.clip.split(",")]
    px_per_pt = 2 * 12 / a.pt_per_ft  # extract_plan rasterizes at 2 px/in
    cx_pt = (a.left_tick_pt + a.right_tick_pt) / 2
    print(f"--center-px {round((cx_pt - x0) * px_per_pt)}   (midpoint of ticks, pt {cx_pt:.2f})")
    print("--rear-px: run extract once, open the wall mask / plan raster, and set it to the row of the")
    print("  rear exterior wall FACE of the section you want as Y=0 (Cottage A: 156).")


def cmd_elev(a):
    x0, y0, x1, y1 = [float(v) for v in a.clip.split(",")]
    dpi = int(round(72 / (a.pt_per_ft / 12)))
    pix = fitz.open(a.pdf)[a.page - 1].get_pixmap(clip=fitz.Rect(x0, y0, x1, y1), dpi=dpi, colorspace=fitz.csGRAY)
    ink = np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.width) < 128
    H, W = ink.shape
    rows = ink.sum(1)
    long_rows = [i for i in range(H) if rows[i] > 0.25 * W]
    best = None
    for i in long_rows:
        for j in long_rows:
            d = j - i
            if d > 0 and abs(d - a.plate_in) <= 3 and (best is None or abs(d - a.plate_in) < best[0]):
                best = (abs(d - a.plate_in), i, j)
    if not best:
        print("no FF/plate line pair found; long rows:", long_rows); return
    _, top, ff = best
    print(f"--floor-row {ff}   (truss-bearing line at row {top}; separation {ff - top} in vs {a.plate_in} documented)")
    cols = ink[top + 5:ff - 5].sum(0)
    tall = [c for c in range(W) if cols[c] > 0.8 * (ff - top - 10)]
    pairs = [(l, r) for l in tall for r in tall if r > l and abs((r - l) - 2 * a.half_width_in) <= 3]
    if pairs:
        l, r = min(pairs, key=lambda p: abs((p[1] - p[0]) - 2 * a.half_width_in))
        print(f"--center-col {round((l + r) / 2)}   (wall faces at cols {l} and {r}, {r - l} in apart vs {2 * a.half_width_in} expected)")
    else:
        print("no wall-face pair at the expected width; tall columns:", tall[:10], "...", tall[-10:])


def cmd_sheets(a):
    """Page -> sheet number (title-block code nearest the bottom-right corner) and drawing titles."""
    import re
    d = fitz.open(a.pdf)
    code = re.compile(r"^[A-Z]{1,2}\d{3}[A-Z]?$")
    for i, p in enumerate(d):
        W, H = p.rect.width, p.rect.height
        words = [w for w in p.get_text("words") if code.match(w[4])]
        sheet = max(words, key=lambda w: w[2] / W + w[3] / H)[4] if words else "-"
        titles = sorted({l.strip() for l in p.get_text().split("\n")
                         if re.search(r"(PLAN|ELEVATIONS?|SECTIONS?|SCHEDULE|DETAILS?)\s*$", l.strip()) and len(l.strip()) < 60})
        print(f"{i + 1:>3}  {sheet:<7} {' | '.join(titles)[:120]}")


def cmd_outline(a):
    """Heaviest orthogonal linework in a clip (roof-plan fascia/eave outline), in feet from an origin."""
    page = fitz.open(a.pdf)[a.page - 1]
    x0, y0, x1, y1 = [float(v) for v in a.clip.split(",")]
    R = fitz.Rect(x0, y0, x1, y1); items = []
    for d in page.get_drawings():
        if not R.intersects(d["rect"]):
            continue
        w = d.get("width") or 0
        for it in d["items"]:
            if it[0] == "l":
                p, q = it[1], it[2]
                if (abs(p.x - q.x) < 0.3 or abs(p.y - q.y) < 0.3) and math.hypot(q.x - p.x, q.y - p.y) > 6:
                    items.append((round(w, 2), p, q))
    wmax = max(w for w, _, _ in items)
    ft = lambda x, y: (round((x - a.origin_x_pt) / a.pt_per_ft, 3), round((y - a.origin_y_pt) / a.pt_per_ft, 3))
    xs = sorted({ft(p.x, 0)[0] for w, p, q in items if w == wmax and abs(p.x - q.x) < 0.3})
    ys = sorted({ft(0, p.y)[1] for w, p, q in items if w == wmax and abs(p.y - q.y) < 0.3})
    print(f"heaviest stroke {wmax} pt; {sum(1 for w,_,_ in items if w == wmax)} segments")
    print("vertical outline lines at X (ft):", xs)
    print("horizontal outline lines at Y (ft):", ys)
    for w, p, q in items:
        if w == wmax:
            print("  seg", ft(p.x, p.y), "->", ft(q.x, q.y))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("scale"); s.add_argument("pdf"); s.add_argument("--page", type=int, required=True)
    s.add_argument("--text", required=True); s.add_argument("--feet", type=float, required=True)
    p = sub.add_parser("plan"); p.add_argument("pdf"); p.add_argument("--page", type=int, required=True)
    p.add_argument("--clip", required=True); p.add_argument("--pt-per-ft", type=float, required=True)
    p.add_argument("--left-tick-pt", type=float, required=True); p.add_argument("--right-tick-pt", type=float, required=True)
    e = sub.add_parser("elev"); e.add_argument("pdf"); e.add_argument("--page", type=int, required=True)
    e.add_argument("--clip", required=True); e.add_argument("--pt-per-ft", type=float, required=True)
    e.add_argument("--plate-in", type=float, required=True); e.add_argument("--half-width-in", type=float, required=True)
    sh = sub.add_parser("sheets"); sh.add_argument("pdf")
    o = sub.add_parser("outline"); o.add_argument("pdf"); o.add_argument("--page", type=int, required=True)
    o.add_argument("--clip", required=True); o.add_argument("--pt-per-ft", type=float, required=True)
    o.add_argument("--origin-x-pt", type=float, required=True); o.add_argument("--origin-y-pt", type=float, required=True)
    a = ap.parse_args()
    {"sheets": cmd_sheets, "scale": cmd_scale, "plan": cmd_plan, "elev": cmd_elev, "outline": cmd_outline}[a.cmd](a)
