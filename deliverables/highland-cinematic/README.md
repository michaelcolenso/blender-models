# 200 West Highland / dusk exterior

The whole-building exterior visualization uses the supplied photographs and the existing model registered to the architectural drawing excerpts. It is rendered in native Blender Cycles, with a packed editable scene.

- `Highland-dusk-4K.png`: 3840 × 2560 exterior hero image.
- `Highland-dusk.blend`: editable scene, Blender 5.0.1 or newer. The 4K sky texture is packed; no external textures or network are required to render it.
- `Highland-dusk.glb`: portable 3D geometry. Procedural surfaces are simplified to base colors and area-light illumination is not reproduced in GLB.
- `scene-validation.json`: architectural geometry protection, source-opening inventory and assumptions.
- `delivery-validation.json`: actual image dimensions, image statistics, file hashes and readback/visual-review record.
- `Highland-dusk-editable.zip`: scene, portable model, render, specification, source records and handoff notes.

The pass improves glazing, folded curtains, shallow room dressing, brick surfaces, foliage, street surfaces, sky and lighting. The original 1,103 architectural mesh objects are preserved. Their vertices, polygon connectivity and transforms are checked before and after the presentation pass.

The source exterior remains an architectural study. It contains 165 representative openings and 26 unresolved drawing candidates; wall returns, opening details, lower enclosure, balcony sections, roof details and grade retain the earlier model's recorded limitations. Apartment interiors, lighting, landscape, vehicles and neighboring-building appearance are illustrative. The supplied photos provide appearance references without dimensional calibration. This rendering does not establish installed conditions.

Sources and reconstruction notes: `../../projects/highland-cinematic/README.md` and `../../projects/highland-exterior/README.md`. The original architectural PDF is not present in this workspace; the existing registered specification and drawing crops are reused.

Sky: [Kloofendal 48d Partly Cloudy / Poly Haven](https://polyhaven.com/a/kloofendal_48d_partly_cloudy_puresky), [CC0](https://polyhaven.com/license). Background footprints: [OpenStreetMap contributors](https://www.openstreetmap.org/copyright), ODbL 1.0; approximate registration and assumed heights/facades. Botanical and street-detail meshes are original procedural geometry.
