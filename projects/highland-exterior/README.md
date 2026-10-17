# 200 W. Highland exterior study

An editable Blender exterior built from the 2007 architectural drawings and the owner's two appearance photos. Includes a stepped shell, 165 representative facade openings, recessed balconies, upper terraces, roof enclosures and a sloping street context. This is a first exterior study, not a verified as-built or an exact photographic reconstruction.

## Sources and coordinates

The supplied **Pages from 200 W. Highland Construction Plans - Complete.pdf**, dated 04-02-07, is the dimensional source. Its SHA-256 is recorded in `exterior.spec.json`.

| PDF page | Sheet | Use |
|---|---|---|
| 1 | A2.03 | R1 outline and dimensioned grids |
| 2 | A2.04 | Typical R2-R4 outline |
| 5 | A2.07 | R5 setback and terrace |
| 6 | A2.08 | Roof outlines and parapet datums |
| 7 | A3.01 | South/east facade patterns |
| 8 | A3.02 | North/west facade patterns |
| 9 | A3.11 | Floor datums |

Source crops were reviewed at 200 dpi. Manual picks in `prepare.py` refer to the 1815 x 1296 sheet previews. Plan coordinates are registered piecewise to the dimension strings: X grids 6-10 span 103 ft; Y grids H-A span 150 ft. Those are **grid spans**, not overall building extents. X points east, Y north, Z up; zero Z is the P1 floor at elevation 342 ft. Documented floor elevations are 342, 353, 363.25, 373.5, 383.75 and 394.25 ft. Elevator/stair parapet tops are 415/414.41 ft.

`photo-manifest.json` identifies both user images. Photo 01 carries a Street View caption of September 2025 / 1213 2nd Ave W; that caption is not independent address verification. Photo 02 shows the southeast corner. Photos inform red-brown brick, dark frames, pale cornices, recesses and vegetation only. No reference object was established for photo scaling; perspective, lighting and processing prevent a dimensional tolerance or exact color match.

## Assumptions and unresolved differences

- The stepped plan outlines are manually simplified. Elevation grid spacing does not agree uniformly with the dimensioned plans, especially on the south. Facade positions use explicit piecewise registration; there is no defensible single dimensional tolerance or global overlay score.
- There are 165 representative openings, not a verified window/door schedule. Twenty-six source candidates were omitted because they did not fit the simplified footprint; every omission has a reason in the spec. Eighteen padded recess boundaries are clipped to their wall segment during building; the validation file lists them.
- Sill/head heights, mullions, wall thickness, frames, rail sections, projecting caps, balcony depth (60 in), guards (42 in), slab thickness and entry steps are assumed. Recesses are normalized to fit the simplified wall returns.
- Roof-cap pieces have minute vertical offsets (0.02 in per segment) to prevent coincident rendering surfaces; these offsets are presentation geometry, not construction details.
- Lower P1 enclosure reuses the R1 outline because the architectural P1 plan is absent. R2-R4 use one typical outline. Lower terraces, patio walls and retaining details are simplified or omitted.
- Roof drainage falls, roof equipment and mechanical screens are representative. Roof split location and local parapet/cap details are simplified. Roof feature top datums are documented; their complete geometry is not.
- Grade is an assumed bilinear surface: north corners rise 12/19 ft from the south. Street/sidewalk widths, surface boundaries, trees and shrubs are presentation context. Adjacent buildings, exact landscape, signage, furniture and exterior lighting are omitted.
- Brick color and texture, all other finishes, glazing reflectance and planting are interpretations of the supplied photos. Procedural brick appears in Blender renders; the portable GLB uses its plain base color.

Each complete object is conservatively tagged **assumed**, with a source and basis. Separate properties identify provisional XY placement or confirmed roof datums where applicable. Consequently the provenance renders are orange throughout; green would wrongly imply an entire component was fully documented. The exterior remains separate from the existing water and proposed repipe scenes.

## Reproduce and review

This multistory scanned set is outside the repository's vector-PDF house pipeline. The dedicated manual specification/build path below avoids unsupported automatic extraction and quantity claims.

```bash
# Python with bpy 5.0.1, Pillow, numpy and PyMuPDF installed
python projects/highland-exterior/build.py
python projects/highland-exterior/package.py
```

`exterior.spec.json` is the geometry input. `prepare.py` regenerates that spec from the recorded manual source picks; its PDF path can be changed to the local copy of the same source. Build requires no source PDF. `--quick` renders only the southeast preview; `--beauty-only` renders the two presentation views. A full run is required before packaging.

Builder assertions check the two grid spans, six floor datums, elevator top, unique object names, opening inventory and provenance. Packaging rejects blank images, checks GLB structure/metadata and records file hashes. These checks do not establish facade dimensional accuracy or a fully resolved architectural model.

The review PDF pairs all four source elevations with orthographic renders, plus a roof/plan view and provenance contact sheet. These are qualitative comparisons with independently fitted image panels, **not same-scale overlays**. Source grid inconsistencies and omitted candidates remain open rather than being concealed by an alignment score. No quantity takeoff is provided for this provisional exterior study.

Deliverables: two perspective PNGs, editable `.blend`, portable `.glb`, review PDF and validation record in `deliverables/highland-exterior/`.
