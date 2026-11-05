# Highland domestic-water model study

This replaces the earlier sheet-stack approach with editable pipe, equipment and fixture geometry. Start review with **Unit A / 107**, then its drawing overlay. The building and boiler views are supporting system studies. A separate **P1** scene traces the south residential corridor and Unit 107 service approach from P2.2, registered to A2.02 through shared structural grids. Unit 107 and P1 plan XY are provisional, Unit 107 ceiling heights are provisionally derived from the structural set and the unit RCP, pipe elevations remain assumed (held inside the derived ceiling-to-soffit band), and building floor datums follow A3.11. This is not a dimensionally coordinated model or a verified representation of installed conditions.

## Reproduce

Python 3.11 with `bpy==5.0.1`, PyMuPDF, Pillow and OpenCV (only for re-running source registration); Node with the pinned dependencies in package.json.

```bash
python projects/highland/products/water/register_source.py  # optional: reproduce saved Unit 107 registration
python projects/highland/products/water/prepare_p1_sources.py  # optional: requires the local full-set PDF
python projects/highland/products/water/register_p1.py
python projects/highland/products/water/prepare_spec.py
python projects/highland/products/water/build.py
cd projects/highland/products/water
npm install
npm run bundle
python package_viewer.py
python make_review.py
```

The same sequence runs as product steps from the repo root: `uv run bm run highland/water build`, then `viewer`, then `video` (film, preview GIF and viewer preview PNGs; needs FFmpeg and the system libraries Playwright's Chromium links against).

Outputs go to `build/highland-water/`. `prepare_spec.py` is the manual takeoff / presentation-coordinate definition. Its expanded `highland-water.spec.json` is the single input used for geometry, connectivity checks and drawing overlay. All dimensional values are inches; Blender uses meters internally. This project uses a dedicated builder because the repository's house extractor does not support scanned multistory plumbing plans. It is not wired into the existing house-model CI workflow.

## Sources and interpretation

- User-supplied **RL–REVISED Highland Condos Plumbing 10-29-07.pdf**, original issue October 29, 2007. Source manifest records the SHA-256.
- P3.02, PDF page 13: domestic-water riser diagram and detail 1, low-temperature boiler piping. Detail 1 explicitly has no scale.
- P4.01, PDF page 15: Unit A / 107 domestic water plan. The source crop is preserved in `source-review/unit-a.png`.
- Architectural excerpt: **Pages from 200 W. Highland Construction Plans - Complete.pdf**, 11 sheets. A2.03 (uploaded page 1) and A3.11 (uploaded page 9), both dated April 2, 2007, supply structural-grid dimensions and floor elevations. See `calibration.json` and `source-manifest.json`. The excerpt begins at R1 and does not include the P1 architectural unit plan.
- Full construction set: **200 W. Highland Construction Plans - Complete.pdf**, 190 scanned pages. A2.02 (page 46, April 2, 2007) supplies P1 architecture; P2.2 (page 183, September 28, 2006) supplies the P1 plumbing trace and is marked **reference only / separate permit**. The newer October 2007 P4.01 remains governing for Unit 107 internal routing.
- Structural set: **Structural Plans - 200 W Highland - 4.02.07.pdf** (Perbix Bykonen, 24 pages, April 2, 2007). S2.3 (page 4) R1 plan, S3.4 (page 14) PT beam schedule, S3.7 (page 17) and S3.8 (page 18) sections give the R1 slab and band-beam soffit elevations over P1.
- **A7.63** (full set page 126), RCP: Unit 107, April 2, 2007, Addendum 1 May 1, 2007: ceiling drops measured from the drop-slab soffit.
- **Plumbing - 200 W Highland - 9.28.06.pdf** (11 pages) is a lower-resolution OCR copy of full-set pages 176–186; it adds searchable text but no P3/P4 sheets and no water-pipe elevations.
- Review annotations help identify stack groups; they do not establish installed conditions or a new governing issue date.
- Building terminal groups: 01 = 5; 02 = 5; 03 = 4; 04 = 4; 05 = 5. The 04 group's R1 dwelling continuation is unresolved. Unit 106 / 107 is a separate paired continuation.
- Unit A symbols: 3 WCs, 4 lavatories, 2 showers, 1 tub, 1 kitchen sink, 1 dishwasher, 1 washer box, 1 hose bib. The washer body is only a representative context envelope for WB1. The dishwasher supply connection remains unresolved and is omitted. The 2006 reference-only P1.1 fixture schedule lists P-7A dishwasher as ½ inch HW only, no CW; its tie-in point is not shown.

## Assumptions and omissions

**Overall element status remains assumed** wherever full XYZ or envelope is not established. Source-traced unit and P1 elements additionally carry `xy_status: provisional` (the new local bathroom service offsets and hardware carry `xy_status: assumed`), `z_status: assumed` and `envelope_status: assumed`; building level references carry `datum_status: confirmed`. A pipe's `size_status` is separate: confirmed means its nominal size is called out; it does not make its route confirmed.

- P1 XY uses independent shared-grid fits on A2.02 and P2.2, approximately 1.5 working pixels/inch. Maximum grid-pick residual is 4.77 inches on P2.2 and 2.25 inches on A2.02; local route trace allowance is ±6 inches. P1 covers only the south corridor mains and Unit 107 approach. Its exact P4.01 tie-in, other P1 services, and actual pipe elevations are unresolved.
- Unit plan XY uses **0.51398349 inch per normalized pixel**, replacing the arbitrary 0.4. Dimensions between common grids 6–10 on A2.03 total 1,236 inches; P2.02 measures 927 PDF points, giving 0.75 point/inch. Independent E–H spans agree within 0.6%. A similarity registration transfers this scale from P2.02 to the enlarged P4.01 crop (21 inliers; median residual 0.224 PDF point). Working allowances: ±1% scale, ±6 inches local simplified trace; these are conservative allowances, not survey accuracy.
- Unit 107 ceilings (provisional, `calibration.json` → `unit_107_ceiling`): R1 top of slab 353.0 ft, bottom of slab 351.88 ft, band-beam soffits 351.21 ft (R1-B11–B14, S3.8 det. 19/20) and 351.13 ft (R1-B7/B9, S3.7 det. 15). A7.63 measures drops from the lower of slab or drop slab, so from 351.21 ft: living/dining −8 in → **102.5 in**, hallway plenum −12 in → **98.5 in**, laundry/mechanical −18 in → **92.5 in** above the P1 floor (342.00 ft). A7.63 gives each drop as ±; master WIC is shaded low-dropped without a dimension. RFI 99, ASI 54, RFI 245 (ceiling heights), RFI 344, RFI 201 and RFI 366 revised these conditions. Their responses will not be supplied (owner, 2026-11-05), so the A7.63 derivation is the working basis; it stays provisional and does not represent the revised conditions.
- Unit overhead pipe elevations are **assumed** at 108 inches CW, 106 inches HW and 104 inches HWC (previously 102/100/98, which put HWC below the derived ceilings), with 6 inches below floor for the island route. `prepare_spec.py` fails if any overhead unit run (centerline ± half nominal bore) leaves the 102.5–109.56 inch band between the highest derived ceiling and the lowest documented soffit. No drawing gives water-pipe elevations; the band is a constraint, not a measurement. P1 corridor runs use the same heights; corridor ceilings are not derived. Fixture drops, body dimensions and connecting hardware are representative.
- Building floor elevations (feet): P2 332.00, P1 342.00, R1 353.00, R2 363.25, R3 373.50, R4 383.75, R5 394.25. Model Z uses P2 as zero. The upper guide is **PLATE 404.42**, not a uniform roof. A3.11 shows other roof/plate elevations too.
- A3.11 interval notes include (+1/4 inch) additions that do not exactly match the decimal elevation differences. The model follows labeled elevations and preserves this discrepancy for clarification.
- Branches remain an assumed 104 inches above each served floor. Stack XY, pipe separation, lateral lengths, offsets and reducer positions remain assumed.
- Plant and fixture envelopes, pipe ports, valves, fittings and pump shapes are assumed. The schematic's external equipment dimensions are not inferred from its drawing scale.
- Visual pipe diameter uses nominal bore, not verified outside diameter. Building pipes use 2.5× enlargement; Unit A uses 1.5×; plant uses 1×. No material, schedule, wall thickness or insulation is established.
- Unit branch continuations in the building view have representative assumed sizes pending unit-specific takeoff. Reducer geometry is simplified.
- Unit A island route between annotated drops and exact hot/return loop junctions are assumed. The 2D overlay deliberately exposes this approximation. A visual comparison has been performed; the source registration has a measured residual, but the simplified pipe-route overlay has no field accuracy or dimensional acceptance.
- Boiler charging and return connections are diagrammatic. Relief/drain piping, flues, detailed controls and balancing bypasses are incomplete. WAC2 is a loose spare and is not shown as installed.
- Common-area, garage and irrigation services are not included. Unit 106 is a continuation only.
- Sanitary, vent, gas, fire protection and an architectural building model are not included.
- Do not extract construction quantities or shutdown boundaries from these coordinates.

## Validation performed

- Unique IDs and provenance on model elements; positive pipe diameters and explicit nominal-size status.
- Counts checked against the takeoff: 5 stack groups, 23 typical branch groups, 14 Unit A fixtures, 2 boilers, 2 storage tanks, 4 expansion vessels, 3 installed pumps, 3 P1 corridor mains and 3 P1 Unit 107 approaches.
- All vertices and terminal routes in the building, unit and P1 distribution graphs reach their own system root. Tees on straight segments are recognized. Separate-system reachability does not validate hydraulic sizing, plant internals, cross-system return flow or source interpretation.
- Cycles CPU renders inspected in plan, front, side and isometric views. Orange provenance renders identify the assumed spatial geometry. Owner-color views identify systems, not provenance. Review PNGs were checked for blank output.
- Unit A and P1 model-projected overlays visually reviewed against their source crops. The P1 overlay caught and corrected a corridor-band placement error before delivery. Grid calibration, registration residuals and seven floor datums are checked automatically. Pipe routes remain simplified traces, not field-verified alignment. A bathroom close-up was also inspected.
- The standalone HTML embeds all four GLBs (Unit 107, building, plant, P1). P1 is a fourth view framed on its water mains. It was tested in headless Chromium at desktop and phone widths: all four views load with no console errors, and selecting a P1 main shows its P2.2 source and provisional/assumed status.

## Next inputs needed

The full set now supplies the P1 architectural plan/RCP and a reference-only P1 plumbing plan. The RFI 99/245/344/201/366 and ASI 54 responses will not be supplied; the A7.63 ceiling derivation and the assumed 108/106/104 in pipe heights stand as the working basis. Still open, if records turn up: actual pipe elevations and the exact P2.2-to-P4.01 Unit 107 tie-in. Resolve the dishwasher connection and return-loop details. Establish shaft positions before placing the risers spatially. If the objective is the actual installed system, confirm routes and equipment with field records/photos. Extend to other P1 services, other units and sanitary/vent/gas only after the pilot geometry is checked.

The working model and review documents are delivered under `projects/highland/deliverables/water/`. A 24-second animated model review now shows the bathroom, fixture connections and full-unit context. It retains visible assumption labels throughout.

## Architectural update

The full takeoff and assumptions are in `calibration.json`. The horizontal calibration increases the earlier Unit 107 XY dimensions by 28.5%; pipe diameters, fixture body envelopes and vertical pipe offsets do not scale with that correction. Floor datums are updated independently. The supplied architecture is dated April 2007 and the plumbing October 2007; shared geometry supports registration, but neither set is treated as evidence of installed conditions.

## Bathroom pilot refinement

The five-fixture primary bathroom now has an explicit port contract in `bathroom_pilot`: five cold and four hot supply connections, five representative fixture stops, two mixing bodies, two mixed-water outlets and five flexible fixture connectors. Elbows and tees are separately selectable geometry derived from the pipe routes. Their counts are model counts, not a drawing takeoff or product schedule.

`bathroom.py` adds these details to the expanded specification. Fixture anchors retain their calibrated-plan basis; lavatory and toilet drops move to **assumed wall-side positions** behind the fixture envelopes. These offsets are not covered by the schematic ±6 inch trace allowance. Overhead CW/HW/HWC are separated at assumed heights of 108/106/104 inches (originally 102/100/98; see the structural ceiling update); both existing schematic hot-to-return joins remain connected across those offsets.

The builder checks each drop/connector endpoint against the corresponding fixture or mixer port, ensures the toilet receives cold water only, verifies both mixed outlets, and checks that stops lie on their supply routes. A generated-mesh check measures clearance between the five wall-side vertical supply drops and the actual lavatory/toilet bounds. This is a targeted interference check; it does not establish whole-model clash freedom, hydraulic adequacy, code compliance, temperature performance or installed conditions. Purple indicates mixed water without asserting any temperature setting.

The bathroom domestic-water pilot is ready for visual review. Sanitary/vent systems remain outside this model. The two-page `Unit-107-bathroom-pilot.pdf` shows the bathroom and fixture connections; the full review retains the source overlay and calibration evidence. The Blender file now opens on the bathroom. Use Bathroom or Connections in the standalone viewer to inspect it; Fittings toggles the representative hardware.

## Animated review

`render_video.cjs` captures deterministic Three.js camera sweeps at 1280 × 720, 24 fps, and encodes an H.264 MP4 with FFmpeg. `render_previews.cjs` screenshots the viewer's Bathroom, Connections and Reset views at 1440 × 1000 for the deliverable README. Both use the Playwright version pinned in `package.json` and its own Chromium. After the viewer step, run:

```bash
uv run bm run highland/water video
```

`make_video.sh` serves `build/highland-water/` on a free local port, renders the film and previews, cuts the preview GIF from the first 10 s (shot 1) at 10 fps and 800 px, fully decodes the MP4, and fails if the decoded frame count differs from the captured one. If Chromium reports missing libraries (`libnss3`, `libnspr4`, `libasound2t64` on Ubuntu), install them with apt.

The 24-second sequence contains a bathroom orbit, an under-fixture connection view and full-unit context. The video uses the same GLB geometry as the viewer; it does not add any pipe routes. `video-validation.json` records frame count, timing and browser errors. Captured frames and decoded video frames were inspected before delivery.

## Structural ceiling update

The spec carries the provisional Unit 107 ceiling derivation above and the raised assumed pipe heights (108/106/104 inches). The deliverables under `projects/highland/deliverables/water/` were rebuilt from it on 2026-11-04 (`build`, `viewer`, `video`). The review PDF, viewer and film state the provisional ceilings and assumed heights and are marked "Illustrative, not a contract document". Files over 1 MB are on the `highland-water-2026-11-04` GitHub Release, recorded in `release-assets.json`.
