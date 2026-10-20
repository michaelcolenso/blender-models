# 200 West Highland / dusk exterior

An exterior presentation pass on the existing drawing-based Highland model, using the two supplied appearance photographs. The new scene adds dusk illumination, transmissive glass, room returns and folded curtains, procedural trees and hedges, damp paving, curbs, garden fencing and illustrative street lamps. The architectural meshes remain identical to the original exterior study.

## Source basis

- `../highland-exterior/exterior.spec.json`: registered plan outlines, opening inventory and floor/roof datums from the supplied 2007 architectural drawing excerpts. See that project's README and review report for the unresolved plan/elevation conflicts.
- `../highland-exterior/source-review/user-photo-01.jpg` and `user-photo-02.jpg`: appearance references for brick, pale caps, dark framing, balcony recesses and planted edges. The photographs are not used as dimensional measurements.
- `../../deliverables/highland-exterior/Highland-exterior.blend`: the existing exterior study, retained as the architectural source.
- `scene.json`: the reproducible camera, lighting/presentation basis, source inventory and rendering settings for this pass.
- The same CC0 Poly Haven sky as the earlier study is upgraded to 4K and packed in the delivered Blender scene. Attribution and the downloaded file's SHA-256 are in `assets/source.json`.

The available drawing crops and existing registered specification are reused. The original architectural PDF referenced by the older builder is absent from this workspace; no new extraction or dimensional certification is claimed.

Background neighborhood footprints reuse the existing drone project's local OpenStreetMap extract, © OpenStreetMap contributors, available under the Open Database License (ODbL 1.0). Registration, heights, facade treatment and generic parked vehicles are assumed presentation context. This is a north-facing building portrait; no south-facing skyline is inserted behind the north-facing camera view.

## Accuracy and presentation assumptions

The original exterior model's 165 representative openings and 26 unresolved source candidates remain unchanged. The original floor/roof datum basis and simplified wall returns, sill/head heights, balcony dimensions, lower enclosure, grade and roof details continue to apply. Realistic materials and illumination do not resolve those geometric limitations.

Apartment rooms are shallow presentation sets behind the glass, not modeled unit layouts. Lamps, room finishes, furniture, curtain patterns, night-time occupancy, foliage, garden fencing, curb sections, street-lamp positions, weather, camera height and material reflectance are assumed. The rendering includes a concise approximation notice. All added objects carry `status`, `source` and `basis` properties in the Blender file.

## Build and render

From the repository root, using Python with `bpy==5.0.1` installed:

```bash
python projects/highland-cinematic/build.py --preview
python projects/highland-cinematic/build.py
```

The preview is 1440 × 960 at 24 samples. The final target is 3840 × 2560 at up to 96 samples, with adaptive sampling, denoising and CPU Cycles. `--build-only`, `--width` and `--samples` are also available. The builder saves the packed editable scene before rendering. Rebuilding needs the local source model and existing sky asset; rendering the packed `.blend` needs no network or external textures.

Output: `../../deliverables/highland-cinematic/`.

## Verification

The builder hashes every vertex, polygon and object transform in the Envelope, Glazing, Balconies and Roof collections before and after the presentation pass, and fails if the architecture changes. It also checks the opening inventory and metadata for all source and presentation components. This protects the existing model; it does not certify its dimensional accuracy. Final image dimensions, pixel variation, packed dependencies and visual review are recorded separately in the delivery validation.
