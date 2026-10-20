# Highland exterior / roof and terrace revision 03

Open [the daylight still](Highland-daylight-geometry-revised.png), [the 18-second dusk film](Highland-dusk-geometry-revised-18s.mp4), [the source comparison](Highland-roof-terrace-source-comparison.pdf) or [the editable Blender file](Highland-roof-and-terrace-revised.blend). Continuation notes: [HANDOFF.md](HANDOFF.md).

This revision corrects selected roof/terrace geometry and mirrored MN window dividers, then carries the corrected exterior into a new daylight still and dusk film. It starts from the delivered daylight revision 02; older deliverables remain available.

The original architectural PDF and opening schedule are absent. All 175 opening records and 16 unresolved candidates are retained. Complete components remain assumed even where a top datum is documented. This is an illustrative exterior study, unsuitable for construction dimensions or quantities.

## Geometry decisions

- Central brick terrace band: 28 in above R5; southwest cornice: 26 in; southeast corner cornice: 30 in. Heights are provisional local scan measurements, about +/-3 in. Complete sections, projections and returns remain assumed.
- Main coping tops terminate at the documented 406.25/407.75 ft controls. Tower caps terminate at the inherited 415.00/414.41 ft and clerestory top. Trimmed the three tower bodies below their caps to remove coincident faces. Removed the previous small per-segment offsets; mitered main and tower caps in plan to remove overlapping corner faces.
- Two R5 wall headers crossing the retained north/south roof split now follow each roof plate height on the proper side of the split.
- Eight south MN frame objects on R1-R4 have mirrored internal vertical bars at approximately 65%/35% of width from west to east. These ratios are provisional (+/-0.03); exact frame sections remain assumed. Opening extents, glass, sills, perimeter frames and horizontal rails are unchanged.
- Registered polygons, six floor datums, grid spans, roof plates and split control remain unchanged. Of 955 original protected meshes, 914 are identical; 39 existing meshes change, two are removed and 16 are added, yielding 969. Changes are bounded by an explicit allowlist and read back from the saved native file.

`geometry.json` records source picks and decisions. `prepare.py` regenerates the complete spec and fits the camera to the revised terrace tops. The source registration uses R5/R4 floor ticks and checks R3. Its local residual is not a dimensional accuracy certificate. Camera residuals use the same nine manual points used for fitting; the changed geometry prevents direct comparison with the previous revision's residual metric.

## Reproduce

Run from the repository root, or `reproduction/` in the ZIP. Python with NumPy, SciPy, Pillow and ReportLab is needed for preparation/reporting. Blender Python needs bpy 5.0.1 and Pillow. Node uses pinned npm dependencies; Chromium and FFmpeg must be installed.

```bash
HIGHLAND_BLENDER_PY=/workspace/.venvs/blender-models/bin/python
python projects/highland-roof/prepare.py
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=3 "$HIGHLAND_BLENDER_PY" projects/highland-roof/build.py
"$HIGHLAND_BLENDER_PY" projects/highland-roof/review_geometry.py
"$HIGHLAND_BLENDER_PY" projects/highland-roof/render_still.py
"$HIGHLAND_BLENDER_PY" projects/highland-roof/render_still.py --night-frames 1,217,432
npm ci --prefix projects/highland-roof
node projects/highland-roof/render-film.cjs --review-only --aa-compare
```

Inspect the still, source comparison, provenance views and seven movie review frames before the full capture:

```bash
node projects/highland-roof/render-film.cjs
"$HIGHLAND_BLENDER_PY" projects/highland-roof/validate.py
python projects/highland-roof/validate_media.py
python projects/highland-roof/report.py
```

`render-film.cjs` caches lossless PNGs under `build/highland-geometry/film-frames/`. A signature binds them to the exact geometry, camera, viewer, sky, capture code and runtime. A changed signature fails rather than reusing stale frames. Move/remove that cache after changing inputs. Interrupted captures resume. `--encode-only` reassembles a complete matching cache. `CHROMIUM_PATH` overrides `/usr/bin/chromium`.

The film samples the native Blender camera at all 432 frames, with Three.js materials, approximate lighting, static shadow maps and foliage simplification. Architecture is not decimated. The base is rendered once into a half-float target. Rails and window frames receive native 4x MSAA against the copied base depth, followed by full-frame FXAA. This concentrates the extra samples on thin geometry. The baseline comparison uses the same scene with FXAA only. Glass, area lights, foliage and context differ from native Cycles. The daylight still is the native material reference. The editable file contains both day and dusk scenes and the full native animation camera.

After inspecting all PDF pages and decoded opening/middle/closing movie frames, record their exact hashes in `visual-review.json`, then run `package.py`. The archive is ignored in Git to avoid duplicating large assets; individual deliverables are versioned. Check `delivery-validation.json`, `media-validation.json`, `visual-review.json` and `package-validation.json` for the exact delivered files.

## Next source work

Obtain original A2.03/A2.04/A2.07 and A3.01/A3.02 sheets, a window schedule and clearer north/return photographs. Resolve the sixteen opening conflicts against those records. Confirm terrace sections, guards, finish products and site dimensions before further architectural detail changes. Native Cycles movie output needs a suitable GPU or render farm; benchmark the delivered native camera before selecting production quality.

## Attribution

Sky: [Poly Haven / Kloofendal 48d Partly Cloudy](https://polyhaven.com/a/kloofendal_48d_partly_cloudy_puresky), CC0. Neighborhood footprints: [OpenStreetMap contributors](https://www.openstreetmap.org/copyright), ODbL 1.0. Heights and facade appearance are approximate. Owner photographs are supplied project references. Drawing crops retain their original source identifiers; no original architectural PDF is included.
