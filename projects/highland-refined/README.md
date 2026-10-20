# 200 West Highland / revised exterior and film

This revision follows the supplied architectural drawing crops and owner photographs. It corrects the visible south bay assignment, removes continuous pale floor bands through the brick fields, adds denser balcony infill and broad central window panes, and develops the terrace edge, selected balcony furnishings, vehicles and quiet neighboring context.

## Source and accuracy basis

The original registered footprint, dimensional grid, six floor elevations and roof/parapet datums remain unchanged. Ten south opening candidates omitted by the earlier projection are restored within the appropriate plan bays. The revised inventory is **175 openings**. Sixteen rear/return candidates remain unresolved. `revision-ledger.json` records every changed/restored opening, its old and new values, source and assumption basis.

The bay assignment uses A2.03/A2.04 plan-return topology and A3.01 opening order. Exact jamb offsets remain assumed. This is not a measured camera match or a verified as-built. Photographs have no independently calibrated scale reference; no dimensional tolerance or photometric color calibration is asserted. The original architectural PDF is absent from this workspace; the existing registered specification and drawing crops are reused.

The photo comparison is qualitative. The photograph and render have independently fitted panels, different weather and an approximate camera. Source/render elevation panels are also qualitative rather than calibrated measured overlays. The provenance view colors complete source components orange because they retain assumed geometry. No new component is promoted to fully confirmed status.

Terrace levels, steps, furnishings, guard-infill sections/count, glazing reflectance, materials, landscape, generic vehicles, neighboring heights/facades and lighting are illustrative. An extended ground mesh continues the inherited assumed grade beneath the background context; it is not surveyed topography. Existing-conditions geometry remains separate from the plumbing/repipe projects. No construction quantities are issued.

## Deliverables and rendering

- `Highland-daylight-revised.png`: native Blender Cycles daylight reference view, 1920 × 1280, adaptive sampling up to 48 samples and denoising.
- `Highland-photo-and-drawing-comparison.pdf`: supplied photo beside the revised daylight view, source elevation comparisons, plan and provenance views.
- `Highland-dusk-approach-and-rise-18s.mp4`: 18 seconds at 24 fps, 1920 × 1080, H.264 with limited-range BT.709 color. Every one of its 432 frames is rendered from a continuous 3D camera path.
- `Highland-revised-daylight-and-film.blend`: packed Blender 5.0.1 scene with separate **Daylight reference comparison** and **Dusk exterior film** scenes and native camera keyframes.
- `Highland-revised-exterior.glb`: portable geometry companion with source/assumption metadata; procedural materials simplify in a generic GLB viewer.
- `element-provenance.csv`: every mesh/curve element, its collection, status, source and assumption basis. Complete components remain assumed even when individual datum properties are documented.
- Validation, revision ledger, camera coordinates, review frames and the editable source package.

The movie uses Three.js PBR shading on the building, simplified diffuse shading on context/foliage, and the exported native geometry. The source architecture is not decimated. Foliage uses an explicit animation LOD: one of eight tree leaves and one of four hedge/shrub leaves, with compensated size. The complete leaf geometry remains in the Blender scene. Native area-light appearance is approximated with emissive room surfaces, environment/directional lighting and static street-light pool decals for the movie. The Cycles still is the reference for the detailed beauty materials. Film output is not a Cycles animation or an interpolation between stills.

## Reproduction

Use Python with `bpy==5.0.1` for Blender scripts, and Python with Pillow and ReportLab for the report/package scripts. Node dependencies are pinned by `package-lock.json`; install with `npm ci --ignore-scripts` in this project. A local Chromium at `/usr/bin/chromium` and FFmpeg are required for capture.

```bash
python projects/highland-refined/prepare.py
HIGHLAND_SPEC_PATH=projects/highland-refined/exterior-revised.spec.json HIGHLAND_OUT_DIR=build/highland-refined python projects/highland-exterior/build.py --build-only
python projects/highland-cinematic/build.py --config projects/highland-refined/presentation.json --output-dir build/highland-refined/presentation --build-only
python projects/highland-refined/detail.py
python projects/highland-refined/render-review.py
node projects/highland-refined/render-film.cjs --review-only
node projects/highland-refined/render-film.cjs
python projects/highland-refined/report.py
python projects/highland-refined/validate-scene.py
# Visually review the still, source views, PDF and decoded movie frames.
# Record that review in deliverables/highland-refined/visual-review.json.
python projects/highland-refined/package.py
```

Camera validation projects the complete architectural bounding box through every native camera frame and rejects clipping; this is a presentation-framing check, not a surveyed clearance assessment. Source factory checks retain the floor/grid datums and opening inventory. Final image/video dimensions, decoded frame count, visual review and archive checks are recorded in the deliverable validation.

Sky: [Poly Haven / Kloofendal 48d Partly Cloudy](https://polyhaven.com/a/kloofendal_48d_partly_cloudy_puresky), [CC0](https://polyhaven.com/license). Neighborhood footprints: [OpenStreetMap contributors](https://www.openstreetmap.org/copyright), ODbL 1.0; inherited registration and heights are approximate. Procedural plants, furniture and vehicles are original presentation assets.
