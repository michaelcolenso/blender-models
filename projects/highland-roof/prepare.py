"""Record source measurements and refit the photo camera to the corrected tops."""
import copy
import json
import sys
from pathlib import Path

import numpy as np
from scipy.optimize import least_squares
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
OUT = ROOT/"deliverables/highland-roof"
sys.path.insert(0, str(ROOT/"projects/highland-daylight"))
from fit_camera import project


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    cfg = json.loads((HERE/"geometry.json").read_text())
    base = json.loads((ROOT/cfg["base_spec"]).read_text())
    spec = copy.deepcopy(base)
    spec["roof_geometry_revision"] = cfg
    (HERE/"geometry-revision.spec.json").write_text(json.dumps(spec, indent=2)+"\n")
    registration = cfg["vertical_registration"]
    a, b = registration["controls"]
    scale = (b["pixel_y"]-a["pixel_y"])/(a["z_in"]-b["z_in"])
    holdout = registration["holdout"]
    predicted = a["pixel_y"]+(a["z_in"]-holdout["z_in"])*scale
    measurements = []
    for band in cfg["terrace_bands"]:
        measured = (a["pixel_y"]-band["source_pick_y"])/scale
        assert abs(measured-band["height_in"]) < registration["height_uncertainty_in"]
        measurements.append({"id": band["id"], "source_pixel_y": band["source_pick_y"],
                             "scaled_height_in": measured, "modeled_height_in": band["height_in"],
                             "uncertainty_in": registration["height_uncertainty_in"], "status": "provisional"})
    report = {"source_crop": cfg["source_crop"], "vertical_registration": registration,
              "pixels_per_inch": scale, "holdout_predicted_pixel_y": predicted,
              "holdout_residual_px": abs(predicted-holdout["pixel_y"]),
              "measurements": measurements, "confirmed_dimensions_added": 0,
              "scope": "Repeated-floor scan registration and approximate parapet/cornice heights. No independent dimensional tolerance or as-built claim."}
    (OUT/"source-measurements.json").write_text(json.dumps(report, indent=2)+"\n")
    image = Image.open(ROOT/cfg["source_crop"]).convert("RGB")
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default(size=28)
    for row in [*registration["controls"], holdout]:
        y = row["pixel_y"]
        draw.line((0, y, image.width, y), fill="#00a9ad", width=3)
        draw.text((10, y+5), f"{row['level']} / z={row['z_in']} in / y={y}", font=font, fill="#00767a", stroke_width=2, stroke_fill="white")
    for i, band in enumerate(cfg["terrace_bands"]):
        x0, x1 = band["source_pick_x_span"]
        y = band["source_pick_y"]
        color = ["#e87500", "#e7a800", "#c84b18"][i]
        draw.line((x0, y, x1, y), fill=color, width=7)
        draw.text((x0, y-45), f"{band['height_in']} in provisional +/-3 in", font=font, fill=color, stroke_width=2, stroke_fill="white")
    image.save(OUT/"Highland-source-height-picks.png")
    Image.open(ROOT/cfg["source_crop"]).crop(cfg["window_dividers"]["source_crop_box"]).resize((1220,480)).save(OUT/"Highland-MN-window-source.png")

    picks = json.loads((ROOT/cfg["photo_landmarks"]).read_text())
    for item in picks["landmarks"]:
        if item["z_in"] == 627:
            item["previous_z_in"] = 627
            item["z_in"] += {16: 28, 17: 28, 12: 30, 13: 30, 20: 26, 21: 26}.get(item["vertex"], 0)
            item["height_basis"] = "Revised terrace band top; provisional scan height from source-measurements.json."
    picks["basis"] += " Terrace-top correspondences now refer to the revised provisional band tops, rather than the R5 floor plane."
    (HERE/"photo-landmarks.json").write_text(json.dumps(picks, indent=2)+"\n")
    points = np.array([[*spec["polygons"][v["polygon"]][v["vertex"]], v["z_in"]] for v in picks["landmarks"]])*.0254
    pixels = np.array([v["pixel"] for v in picks["landmarks"]])
    sigma = np.array([v["uncertainty_px"] for v in picks["landmarks"]])
    previous = json.loads((ROOT/cfg["previous_camera_fit"]).read_text())
    prior = [*previous["position_m"], *previous["yaw_pitch_roll_radians"], previous["lens_mm"]]
    lower = [40, -85, .6, .2, -.1, -.06, 16]
    upper = [100, -5, 6, 1.4, .45, .06, 70]
    def residual(p):
        return ((project(p, points, picks["image_size"])-pixels)/sigma[:, None]).ravel()
    result = least_squares(residual, prior, bounds=(lower, upper), loss="soft_l1", max_nfev=5000,
                           xtol=1e-12, ftol=1e-12, gtol=1e-12)
    predictions = project(result.x, points, picks["image_size"])
    errors = np.linalg.norm(predictions-pixels, axis=1)
    prior_errors = np.linalg.norm(project(prior, points, picks["image_size"])-pixels, axis=1)
    fitted = {"method": "Robust pinhole fit, centered principal point, 36 mm horizontal sensor, no distortion",
              "scope": picks["basis"], "source_photo": picks["photo"], "image_size": picks["image_size"],
              "position_m": result.x[:3].tolist(), "yaw_pitch_roll_radians": result.x[3:6].tolist(),
              "lens_mm": float(result.x[6]), "success": bool(result.success),
              "bounds": {"lower": lower, "upper": upper}, "active_bounds": result.active_mask.tolist(),
              "landmark_rmse_px": float(np.sqrt(np.mean(errors**2))),
              "same_geometry_previous_camera_rmse_px": float(np.sqrt(np.mean(prior_errors**2))),
              "maximum_landmark_error_px": float(max(errors)),
              "landmarks": [{**item, "position_m": point.tolist(), "projected_pixel": pixel.tolist(), "error_px": float(error)}
                            for item, point, pixel, error in zip(picks["landmarks"], points, predictions, errors)],
              "limitation": "Fitting residuals use the same manual observations as the fit. The changed model heights prevent treating this as an independent comparison with the prior revision's metric."}
    assert fitted["success"]
    (OUT/"camera-fit.json").write_text(json.dumps(fitted, indent=2)+"\n")
    print(json.dumps({"pixels_per_inch": scale, "holdout_error_px": report["holdout_residual_px"],
                      "band_heights_in": [m["modeled_height_in"] for m in measurements],
                      "camera_rmse_px": fitted["landmark_rmse_px"]}, indent=2))


if __name__ == "__main__":
    main()
