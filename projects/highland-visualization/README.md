# Highland / revision 06 dusk visualization

An 18-second, 1280 × 720, 24 fps camera animation of the reconciled Highland exterior. It samples the existing native dusk camera at all 432 frames, beginning with a street approach and rising to show the R5 terraces and roof. The geometry comes directly from revision 06; no native geometry or camera keys are edited or saved by this presentation pass.

The Three.js film approximates native lighting and materials. Architecture is preserved without decimation; foliage alone uses the existing display LOD. The native Cycles reference remains [the revision 06 dusk still](../../deliverables/highland-drawings/Highland-dusk-drawing-reconciled.png). Plan XY is provisional, full profiles/guards/site remain assumed, and north stair/MU and R1 entry audits remain deferred.

The source native, GLB, drawing validation and camera export are bound by exact SHA-256 hashes in `deliverables/highland-visualization/source-validation.json`. The lossless frame cache has a signature covering the source model, exported camera, presentation configuration, viewer, capture code, sky, package lock and runtime. Changed inputs require a new cache; interrupted captures resume.

Run from the repository root:

```bash
HIGHLAND_BLENDER_PY=/workspace/.venvs/blender-models/bin/python
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=3 "$HIGHLAND_BLENDER_PY" projects/highland-visualization/export.py
npm ci --prefix projects/highland-visualization
node projects/highland-visualization/render-film.cjs --review-only --aa-compare
# Inspect the seven review frames before capturing the complete film.
node projects/highland-visualization/render-film.cjs
python projects/highland-visualization/finish-film.py
python projects/highland-visualization/validate_media.py
python projects/highland-visualization/review_movie.py
```

Requirements: Python 3.11/bpy 5.0.1 for the camera export; Pillow for media checks; pinned Three.js 0.180.0 and Playwright 1.62.1; Chromium and FFmpeg. `CHROMIUM_PATH` overrides `/usr/bin/chromium`. Rendering uses headless Chromium's software WebGL. The existing revision 03 renderer provides the reviewed 4x MSAA pass for rails/window frames followed by full-frame FXAA. The base geometry, context, sky and warm window groups are batched by material.

Frame capture is lossless RGB PNG; the delivered MP4 is H.264/yuv420p with explicit limited-range BT.709 tags and fast-start metadata. Validation fully decodes the film, checks frame counts/timing/color, source hashes, cache completeness, browser errors and image variation. Visual review records the seven preview views, anti-aliasing comparison, decoded opening/middle/closing frames and poster by exact hash.

Sky: Poly Haven's Kloofendal 48d Partly Cloudy (CC0). Approximate neighborhood footprints derive from OpenStreetMap contributors (ODbL); finish/context interpretation follows the existing native model. The source drawing PDFs, measurement qualifications and remaining source differences remain in the separate drawing-reconciliation delivery.

The deferred north comparison retains its 42.443-overview-pixel diagnostic maximum; other source residuals remain in the linked drawing review. The animation does not resolve those differences.
