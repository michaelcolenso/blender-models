"""Fit an illustrative pinhole camera to manually selected photo correspondences."""
import json
from pathlib import Path

import numpy as np
from scipy.optimize import least_squares

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
OUT = ROOT / "deliverables/highland-daylight"


def project(parameters, points, size):
    x, y, z, yaw, pitch, roll, lens = parameters
    forward = np.array([-np.sin(yaw)*np.cos(pitch), np.cos(yaw)*np.cos(pitch), np.sin(pitch)])
    right = np.array([np.cos(yaw), np.sin(yaw), 0.])
    up = np.cross(right, forward)
    r = right*np.cos(roll) + up*np.sin(roll)
    u = up*np.cos(roll) - right*np.sin(roll)
    delta = points - [x, y, z]
    depth = delta @ forward
    focal = size[0] * lens / 36
    return np.column_stack((size[0]/2+focal*(delta@r)/depth,
                            size[1]/2-focal*(delta@u)/depth))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    picks = json.loads((HERE / "photo-landmarks.json").read_text())
    spec = json.loads((ROOT / "projects/highland-refined/exterior-revised.spec.json").read_text())
    points = np.array([[*spec["polygons"][v["polygon"]][v["vertex"]], v["z_in"]]
                       for v in picks["landmarks"]]) * .0254
    pixels = np.array([v["pixel"] for v in picks["landmarks"]])
    sigma = np.array([v["uncertainty_px"] for v in picks["landmarks"]])
    def residual(p):
        return ((project(p, points, picks["image_size"]) - pixels) / sigma[:, None]).ravel()
    # Fixed centered principal point, square pixels, no distortion. Weakly
    # constrain only plausible camera placement; all bounds are reported.
    lower = [40, -85, .6, .2, -.1, -.06, 16]
    upper = [100, -5, 6, 1.4, .45, .06, 70]
    initial = [65, -30, 2.7, .75, .12, 0, 30]
    result = least_squares(residual, initial, bounds=(lower, upper), loss="soft_l1",
                           f_scale=1, max_nfev=5000, xtol=1e-12, ftol=1e-12, gtol=1e-12)
    p = result.x
    predictions = project(p, points, picks["image_size"])
    errors = np.linalg.norm(predictions-pixels, axis=1)
    baseline = [68, -55, 3.8, np.arctan2(48, 77.5), np.arctan2(6.7, np.hypot(48, 77.5)), 0, 46]
    baseline_errors = np.linalg.norm(project(baseline, points, picks["image_size"])-pixels, axis=1)
    report = {
        "method": "Robust least-squares pinhole fit; centered principal point; 36 mm horizontal sensor; no lens distortion",
        "scope": picks["basis"], "success": bool(result.success), "source_photo": picks["photo"],
        "image_size": picks["image_size"], "position_m": p[:3].tolist(),
        "yaw_pitch_roll_radians": p[3:6].tolist(), "lens_mm": float(p[6]),
        "bounds": {"lower": lower, "upper": upper},
        "active_bounds": result.active_mask.tolist(),
        "landmark_rmse_px": float(np.sqrt(np.mean(errors**2))),
        "previous_camera_rmse_px": float(np.sqrt(np.mean(baseline_errors**2))),
        "maximum_landmark_error_px": float(max(errors)),
        "landmarks": [{**v, "position_m": point.tolist(), "projected_pixel": prediction.tolist(),
                       "error_px": float(error)}
                      for v, point, prediction, error in zip(picks["landmarks"], points, predictions, errors)],
        "limitations": ["Residuals describe selected manual correspondences on a simplified model; they are not independent accuracy measurements.",
                        "No surveyed camera, calibrated scale, focal metadata, distortion correction or dimensional tolerance is established.",
                        "Model and photo roof profiles differ; these differences must remain visible in the comparison."]
    }
    (OUT / "camera-fit.json").write_text(json.dumps(report, indent=2)+"\n")
    print(json.dumps({k: report[k] for k in ("success", "position_m", "lens_mm", "landmark_rmse_px", "previous_camera_rmse_px", "active_bounds")}, indent=2))


if __name__ == "__main__":
    main()
