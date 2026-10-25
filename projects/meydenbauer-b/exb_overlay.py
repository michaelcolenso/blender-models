"""Register the 1974 precast foundation plans (Exhibit B, FPB1/FPB2) to the bid-set grid and overlay
the trench footprints and the modelled footings, so the footing layer can be checked by eye.

Grid bubble positions were read by eye from the 150 dpi rasters (REVIEWED below). Exhibit B
labels its columns A-N without I; its J-N are the bid set's I-M, and its row 6 is the bid set's
row 1. Fit residuals are printed; the 2026-10-24 run gave <= 0.06 ft (FPB1) and <= 0.26 ft (FPB2).

Usage: python projects/meydenbauer-b/exb_overlay.py sources/meydenbauer/exhibit-b-precast-panels.pdf
Writes build/meydenbauer-b/exhibit-b-overlay.png (reproduces the record drawing: internal use only).
"""
import json, subprocess, sys, tempfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
KX = {"A": 0, "B": 31.417, "C": 34.667, "D": 42.667, "E": 45.917, "F": 73.0, "G": 80.0, "H": 87.0,
      "J": 114.542, "K": 117.792, "L": 125.792, "M": 129.042, "N": 160.458}
KY = {6: 0, 5: 6.333, 4: 26.167, 3: 45.583, 2: 60.0, 1: 66.333}
REVIEWED = {   # page: grid-line pixel positions at 150 dpi
    1: {"cols": {"A": 449, "B": 1162, "C": 1234, "D": 1416, "E": 1488, "F": 2102, "G": 2262, "H": 2421},
        "rows": {6: 440, 5: 580, 4: 1026, 3: 1460, 2: 1784, 1: 1924}},
    2: {"cols": {"G": 672, "H": 832, "J": 1442, "K": 1518, "L": 1695, "M": 1772, "N": 2483},
        "rows": {6: 500, 5: 650, 4: 1096, 3: 1524, 2: 1854, 1: 2000}},
}
S, X0, Y0, X1, Y1 = 12.0, -12, -10, 172, 72


def main(pdf):
    out = np.full((int((Y1 - Y0) * S), int((X1 - X0) * S)), 255, np.uint8)
    xs = X0 + (np.arange(out.shape[1]) + 0.5) / S; ys = Y0 + (np.arange(out.shape[0]) + 0.5) / S
    XX, YY = np.meshgrid(xs, ys)
    with tempfile.TemporaryDirectory() as tmp:
        for page, ref in REVIEWED.items():
            subprocess.run(["pdftoppm", "-r", "150", "-f", str(page), "-l", str(page), "-png", pdf, f"{tmp}/p"], check=True)
            a = np.array(Image.open(next(Path(tmp).glob(f"p-*{page}.png"))).convert("L"))
            cx = np.array([[v, 1] for v in ref["cols"].values()]); tx = np.array([KX[k] for k in ref["cols"]])
            cy = np.array([[v, 1] for v in ref["rows"].values()]); ty = np.array([KY[k] for k in ref["rows"]])
            (ax, bx), *_ = np.linalg.lstsq(cx, tx, rcond=None); (ay, by), *_ = np.linalg.lstsq(cy, ty, rcond=None)
            print(f"FPB{page}: {1 / ax:.2f} x {1 / ay:.2f} px/ft; max residual "
                  f"{max(abs(cx @ (ax, bx) - tx).max(), abs(cy @ (ay, by) - ty).max()):.2f} ft")
            mask = XX < 88 if page == 1 else XX >= 88
            px = ((XX - bx) / ax).round().astype(int); py = ((YY - by) / ay).round().astype(int)
            ok = mask & (px >= 0) & (px < a.shape[1]) & (py >= 0) & (py < a.shape[0])
            out[ok] = a[py[ok], px[ok]]
    img = Image.fromarray(out).convert("RGB"); d = ImageDraw.Draw(img, "RGBA")
    P = lambda p: ((p[0] - X0) * S, (p[1] - Y0) * S)
    for f in json.loads((HERE / "meydenbauer-b.structure.json").read_text())["footings"]:
        d.polygon([P(p) for p in f["ring_ft"]], fill=(0, 170, 0, 70), outline=(0, 120, 0, 255))
    for u in json.loads((ROOT / "build/meydenbauer-b/takeoff.json").read_text())["units"]:
        for r in u["footprint_S2"]:
            d.polygon([P(p) for p in r], fill=(230, 40, 20, 80), outline=(200, 0, 0, 255))
    path = ROOT / "build/meydenbauer-b/exhibit-b-overlay.png"
    img.save(path); print("wrote", path)


if __name__ == "__main__":
    main(sys.argv[1])
