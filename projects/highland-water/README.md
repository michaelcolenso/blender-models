# Highland domestic-water model study

This replaces the earlier sheet-stack approach with editable pipe, equipment and fixture geometry. Start review with **Unit A / 107**, then its drawing overlay. The building and boiler views are supporting system studies. Unit 107 plan XY is now provisionally calibrated from the supplied architectural grid, and building floor datums follow A3.11. This is not yet a dimensionally coordinated model or a verified representation of installed conditions.

## Reproduce

Python 3.11 with `bpy==5.0.1`, PyMuPDF, Pillow and OpenCV (only for re-running source registration); Node with the pinned dependencies in package.json.

```bash
python projects/highland-water/register_source.py  # optional: reproduce saved source registration
python projects/highland-water/prepare_spec.py
python projects/highland-water/build.py
cd projects/highland-water
npm install
npm run bundle
python package_viewer.py
python make_review.py
```

Outputs go to `build/highland-water/`. `prepare_spec.py` is the manual takeoff / presentation-coordinate definition. Its expanded `highland-water.spec.json` is the single input used for geometry, connectivity checks and drawing overlay. All dimensional values are inches; Blender uses meters internally. This project uses a dedicated builder because the repository's house extractor does not support scanned multistory plumbing plans. It is not wired into the existing house-model CI workflow.

## Sources and interpretation

- User-supplied **RL–REVISED Highland Condos Plumbing 10-29-07.pdf**, original issue October 29, 2007. Source manifest records the SHA-256.
- P3.02, PDF page 13: domestic-water riser diagram and detail 1, low-temperature boiler piping. Detail 1 explicitly has no scale.
- P4.01, PDF page 15: Unit A / 107 domestic water plan. The source crop is preserved in `source-review/unit-a.png`.
- Architectural excerpt: **Pages from 200 W. Highland Construction Plans - Complete.pdf**, 11 sheets. A2.03 (uploaded page 1) and A3.11 (uploaded page 9), both dated April 2, 2007, supply structural-grid dimensions and floor elevations. See `calibration.json` and `source-manifest.json`. The excerpt begins at R1 and does not include the P1 architectural unit plan.
- Review annotations help identify stack groups; they do not establish installed conditions or a new governing issue date.
- Building terminal groups: 01 = 5; 02 = 5; 03 = 4; 04 = 4; 05 = 5. The 04 group's R1 dwelling continuation is unresolved. Unit 106 / 107 is a separate paired continuation.
- Unit A symbols: 3 WCs, 4 lavatories, 2 showers, 1 tub, 1 kitchen sink, 1 dishwasher, 1 washer box, 1 hose bib. The washer body is only a representative context envelope for WB1. The dishwasher supply connection remains unresolved and is omitted.

## Assumptions and omissions

**Overall element status remains assumed** wherever full XYZ or envelope is not established. Unit elements additionally carry `xy_status: provisional`, `z_status: assumed` and `envelope_status: assumed`; building level references carry `datum_status: confirmed`. A pipe's `size_status` is separate: confirmed means its nominal size is called out; it does not make its route confirmed.

- Unit plan XY uses **0.51398349 inch per normalized pixel**, replacing the arbitrary 0.4. Dimensions between common grids 6–10 on A2.03 total 1,236 inches; P2.02 measures 927 PDF points, giving 0.75 point/inch. Independent E–H spans agree within 0.6%. A similarity registration transfers this scale from P2.02 to the enlarged P4.01 crop (21 inliers; median residual 0.224 PDF point). Working allowances: ±1% scale, ±6 inches local simplified trace; these are conservative allowances, not survey accuracy.
- Unit pipe elevations remain 102 inches overhead and 6 inches below floor for the island route. A3.11 gives 132 inches floor-to-floor at Unit 107, **not** a clear ceiling height. Fixture drops, body dimensions and connecting hardware are representative.
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

- Unique IDs and provenance on 319 elements; positive pipe diameters and explicit nominal-size status.
- Counts checked against the takeoff: 5 stack groups, 23 typical branch groups, 14 Unit A fixtures, 2 boilers, 2 storage tanks, 4 expansion vessels, 3 installed pumps.
- All vertices and terminal routes in the building and unit distribution graphs reach their own system root. Tees on straight segments are recognized. Separate-system reachability does not validate hydraulic sizing, plant internals, cross-system return flow or source interpretation.
- Cycles CPU renders inspected in plan, front, side and isometric views. Orange provenance renders identify the assumed spatial geometry. Owner-color views identify systems, not provenance. Review PNGs were checked for blank output.
- Unit A model-projected overlay visually reviewed against the source crop. Grid calibration, registration residual and seven floor datums are checked automatically. Pipe routes remain a simplified trace, not field-verified alignment. A bathroom close-up was also inspected.
- Standalone HTML tested over local HTTP in Chromium with software WebGL: all three GLBs load; system toggles and source dialog work; no JavaScript errors or horizontal overflow at desktop/mobile sizes. Camera framing was corrected after inspecting the mobile screenshot. Offline file opening was not tested in the managed browser, which disallows local file URLs; the viewer embeds all models and code and makes no external asset requests.

## Next inputs needed

The new excerpt supplies enough information for provisional XY calibration and documented floor datums. Next obtain the P1 / Unit 107 architectural and reflected-ceiling plans, clear ceiling heights and actual pipe elevations. Resolve its dishwasher connection and return-loop details. Establish shaft positions before placing the risers spatially. If the objective is the actual installed system, confirm routes and equipment with field records/photos. Extend to other units and sanitary/vent/gas only after the pilot geometry is checked.

The working model and review documents are delivered under `deliverables/highland-water/`. No new owner walkthrough video was made: dimensional review comes first.

## Architectural update

The full takeoff and assumptions are in `calibration.json`. The horizontal calibration increases the earlier Unit 107 XY dimensions by 28.5%; pipe diameters, fixture body envelopes and vertical pipe offsets do not scale with that correction. Floor datums are updated independently. The supplied architecture is dated April 2007 and the plumbing October 2007; shared geometry supports registration, but neither set is treated as evidence of installed conditions.
