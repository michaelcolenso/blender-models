"""Extract sheet registration and riser markups from the governing plumbing set.

Needs the source PDF in projects/highland/sources/ (git-ignored). Writes the committed
source-review/plan-marks.json and review crops; takeoff.py reads only the JSON, so CI never
needs the PDF.

Registration: the grid bubbles on every P2.0x sheet are found with a Hough circle search and
fitted to the A2.03 grid dimension strings by least squares (no title-block scale is used).
Markups: the drawings carry vector PDF annotations (Square = riser box, colored by the sheet
legend: green "continuous riser or riser going up", orange "riser going down"). Their
rectangles are transformed through the page rotation into grid inches.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pymupdf

from bmodels.paths import PROJECTS

SITE = PROJECTS / "highland"
HERE = Path(__file__).parent
PDF = SITE / "sources" / "RL- REVISED Highland Condos Plumbing 10-29-07.pdf"
OUT = HERE / "source-review"

# A2.03 (full set page 47, 04-02-07): grid dimension strings, inches. X east from grid 7,
# Y north from grid E. 6-7 16'-3", 7-8 27'-9", 8-9 27'-9", 9-10 31'-3" (top string);
# A-B 30'-6", B-C 27'-0", C-D 17'-6", D-E 17'-6", E-F 18'-0", F-G 24'-6", G-H 15'-0" (right string).
GRID_X = {"6": -195, "7": 0, "8": 333, "9": 666, "10": 1041}
GRID_Y = {"A": 1110, "B": 744, "C": 420, "D": 210, "E": 0, "F": -216, "G": -510, "H": -690}
SHEETS = {4: ("P2.01", "P2"), 5: ("P2.02", "P1"), 6: ("P2.03", "R1"), 7: ("P2.04", "R2"),
          8: ("P2.05", "R3"), 9: ("P2.06", "R4"), 10: ("P2.07", "R5")}
LEGEND = {(0.0, 1.0, 0.5): "UP", (1.0, 0.5, 0.0): "DN"}
PLAN_MIN_X_PT = 1300  # markups left of this are the sheet legend, not plan marks


def bubbles(page):
    import cv2
    z = 2.0
    pix = page.get_pixmap(matrix=pymupdf.Matrix(z, z), colorspace=pymupdf.csGRAY)
    im = np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.width)
    found = {}
    for strip, (x0, y0, x1, y1) in {"top": (1300, 80, 2450, 160), "right": (2600, 320, 2690, 1780)}.items():
        crop = im[int(y0 * z):int(y1 * z), int(x0 * z):int(x1 * z)]
        c = cv2.HoughCircles(cv2.GaussianBlur(crop, (5, 5), 1), cv2.HOUGH_GRADIENT, 1, 60,
                             param1=120, param2=30, minRadius=22, maxRadius=32)
        found[strip] = [] if c is None else [(x / z + x0, y / z + y0) for x, y, _ in c[0]]
    xs = sorted(p[0] for p in found["top"])
    ys = sorted(p[1] for p in found["right"])
    assert len(xs) == len(GRID_X) and len(ys) == len(GRID_Y), (len(xs), len(ys))
    return dict(zip(GRID_X, xs)), dict(zip(GRID_Y, ys))


def fit(pts, dist):
    a = np.array([[pts[k], 1] for k in dist]); v = np.array(list(dist.values()))
    (s, o), *_ = np.linalg.lstsq(a, v, rcond=None)
    return float(s), float(o), float(np.abs(a @ [s, o] - v).max())


def main():
    if not PDF.exists():
        sys.exit(f"missing {PDF.relative_to(SITE)}: restore it with `bm run highland/installation restore` "
                 "(Highland-original.pdf, sha256 93c5426c...) and copy it under that name")
    doc = pymupdf.open(PDF)
    OUT.mkdir(exist_ok=True)
    result = {"source": PDF.name, "sha256_expected": "93c5426cc8604ec33abd0b13ece1f5c6b76fe0417a2efcd9aca84701d294586a",
              "units": "inches; x east of grid 7, y north of grid E",
              "grid_source": "A2.03 Level R1 plan, full set page 47, 04-02-07, grid dimension strings",
              "sheets": {}}
    for page_no, (sheet, level) in SHEETS.items():
        page = doc[page_no - 1]
        bx, by = bubbles(page)
        sx, ox, rx = fit(bx, GRID_X)
        sy, oy, ry = fit(by, GRID_Y)
        to_in = lambda p: [round(sx * p.x + ox, 1), round(sy * p.y + oy, 1)]  # noqa: E731
        boxes = []
        for a in page.annots():
            if a.type[1] != "Square":
                continue
            kind = LEGEND.get(tuple(round(c, 2) for c in (a.colors.get("stroke") or ())))
            r = a.rect * page.rotation_matrix
            if kind is None or r.x0 < PLAN_MIN_X_PT:
                continue
            boxes.append({"kind": kind, "center_in": to_in((r.tl + r.br) / 2),
                          "size_in": [round(abs(r.width * sx)), round(abs(r.height * sy))]})
        boxes.sort(key=lambda b: (-b["center_in"][1], b["center_in"][0]))
        result["sheets"][sheet] = {"page": page_no, "level": level,
                                   "pt_per_in": [round(1 / sx, 5), round(-1 / sy, 5)],
                                   "origin_pt": [round(-ox / sx, 2), round(-oy / sy, 2)],
                                   "grid_residual_in": round(max(rx, ry), 2), "riser_boxes": boxes}
        print(sheet, level, "residual", round(max(rx, ry), 2), "in;", len(boxes), "riser boxes")
    (OUT / "plan-marks.json").write_text(json.dumps(result, indent=1) + "\n")
    crops(doc)


def crops(doc):
    """Review crops at each traced stack, R1-R5, so the takeoff can be checked without the PDF."""
    from PIL import Image, ImageDraw
    from takeoff import FLOORS, STACKS  # noqa: E402  (same folder)
    marks = json.loads((OUT / "plan-marks.json").read_text())
    for sid, st in STACKS.items():
        tiles = []
        for sheet, info in marks["sheets"].items():
            if info["level"] not in ("R1", "R2", "R3", "R4", "R5"):
                continue
            page = doc[info["page"] - 1]
            ptx, pty = info["pt_per_in"]
            lv = info["level"]
            off = st.get("offset_at") and FLOORS.index(lv) >= FLOORS.index(st["offset_at"])
            x, y = st["to_seed"] if off else st["seed"]
            ox, oy = info["origin_pt"]  # grid 7 / E on this sheet
            r = pymupdf.Rect(ox + ptx * (x - 90), oy - pty * (y + 70), ox + ptx * (x + 90), oy - pty * (y - 70))
            pix = page.get_pixmap(dpi=150, clip=r)
            im = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            ImageDraw.Draw(im).text((6, 4), f"{sheet} {info['level']}", fill=(200, 0, 0))
            tiles.append(im)
        w, h = tiles[0].size
        sheet_im = Image.new("RGB", (w * len(tiles), h), "white")
        for i, t in enumerate(tiles):
            sheet_im.paste(t, (i * w, 0))
        sheet_im.save(OUT / f"stack-{sid}.jpg", quality=80)


if __name__ == "__main__":
    sys.path.insert(0, str(HERE))
    main()
