import json
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).parent
SOURCE = HERE.parents[3] / "build/highland-water/p1-source"
OUT = HERE / "source-review"

# Manually picked shared grid intersections on the 144-dpi working rasters.
# X distances are from grid 7; Y distances are from grid E, positive upward.
plumbing_grids = {
    "x": {"7": 3142, "8": 3642, "9": 4146, "10": 4694},
    "y": {"E": 2386, "F": 2712, "G": 3158, "H": 3427},
}
architecture_grids = {
    "x": {"6": 2880, "7": 3168, "8": 3673, "9": 4173, "10": 4744},
    "y": {"E": 2402, "F": 2728, "G": 3165, "H": 3431},
}
x_distances = {"6": -195, "7": 0, "8": 333, "9": 666, "10": 1041}
y_distances = {"E": 0, "F": -216, "G": -510, "H": -690}

def fit_axis(pixels, distances):
    names = list(pixels)
    design = np.array([[pixels[name], 1] for name in names])
    values = np.array([distances[name] for name in names])
    scale, offset = np.linalg.lstsq(design, values, rcond=None)[0]
    predicted = design @ np.array([scale, offset])
    return {
        "names": names,
        "working_px": [pixels[name] for name in names],
        "distance_in": [distances[name] for name in names],
        "in_per_working_px": float(scale),
        "offset_in": float(offset),
        "residual_in": (predicted - values).tolist(),
    }

result = {
    "method": "Least-squares registration of manually picked shared structural grids; no title-block scale used",
    "source": "P2.2, full-set PDF page 183, 09-28-06, reference only / separate permit",
    "target": "A2.02, full-set PDF page 46, 04-02-07",
    "working_pixels_per_pdf_point": 2.0,
    "status": "provisional",
    "plumbing": {
        "x": fit_axis(plumbing_grids["x"], x_distances),
        "y": fit_axis(plumbing_grids["y"], y_distances),
    },
    "architecture": {
        "x": fit_axis(architecture_grids["x"], x_distances),
        "y": fit_axis(architecture_grids["y"], y_distances),
    },
}
for sheet in ("plumbing", "architecture"):
    px_per_in = 1 / result[sheet]["x"]["in_per_working_px"]
    py_per_in = -1 / result[sheet]["y"]["in_per_working_px"]
    result[sheet]["working_px_per_in"] = [float(px_per_in), float(py_per_in)]
    result[sheet]["max_grid_residual_in"] = float(max(
        abs(v) for axis in ("x", "y") for v in result[sheet][axis]["residual_in"]
    ))
(OUT / "registration-p1.json").write_text(json.dumps(result, indent=2) + "\n")

architecture = cv2.imread(str(SOURCE / "A2.02.png"))
plumbing = cv2.imread(str(SOURCE / "P2.2.png"))
overlay = cv2.addWeighted(architecture, 0.5, plumbing, 0.5, 0)
for grids, color in ((architecture_grids, (220, 80, 40)), (plumbing_grids, (40, 180, 220))):
    for px in grids["x"].values():
        cv2.line(overlay, (px, 450), (px, 3650), color, 2)
    for py in grids["y"].values():
        cv2.line(overlay, (2750, py), (5100, py), color, 2)
preview = overlay[400:3700, 2700:5200]
preview = cv2.resize(preview, (1500, round(preview.shape[0] * 1500 / preview.shape[1])))
cv2.imwrite(str(OUT / "registration-p1-matches.jpg"), preview, [cv2.IMWRITE_JPEG_QUALITY, 92])
print(json.dumps(result, indent=2))
