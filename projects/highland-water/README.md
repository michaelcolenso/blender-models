# Highland domestic-water model study

This replaces the earlier sheet-stack approach with editable pipe, equipment and fixture geometry. Start review with **Unit A / 107**, then its drawing overlay. The building and boiler views are supporting system studies. This is not yet a dimensionally coordinated model or a verified representation of installed conditions.

## Reproduce

Python 3.11 with `bpy==5.0.1`, PyMuPDF and Pillow; Node with the pinned dependencies in package.json.

```bash
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
- Review annotations help identify stack groups; they do not establish installed conditions or a new governing issue date.
- Building terminal groups: 01 = 5; 02 = 5; 03 = 4; 04 = 4; 05 = 5. The 04 group's R1 dwelling continuation is unresolved. Unit 106 / 107 is a separate paired continuation.
- Unit A symbols: 3 WCs, 4 lavatories, 2 showers, 1 tub, 1 kitchen sink, 1 dishwasher, 1 washer box, 1 hose bib. The washer body is only a representative context envelope for WB1. The dishwasher supply connection remains unresolved and is omitted.

## Assumptions and omissions

**Every spatial element is tagged assumed**, because its XYZ or envelope is not dimensionally established. A pipe's `size_status` is separate: confirmed means its nominal size is called out; it does not make its route confirmed.

- Unit plan XY coordinates are a visual trace, with an arbitrary 0.4 inch/pixel conversion. This is explicitly **not** a scale calibration. Typical elevations: 102 inches overhead, 6 inches below floor for the island route. Fixture drops and body dimensions are representative.
- Building levels are spaced 126 inches, with branches 104 inches above their served floor. Stack XY positions and separation, lateral branch lengths, main offsets and reducer positions are assumed.
- Plant and fixture envelopes, pipe ports, valves, fittings and pump shapes are assumed. The schematic's external equipment dimensions are not inferred from its drawing scale.
- Visual pipe diameter uses nominal bore, not verified outside diameter. Building pipes use 2.5× enlargement; Unit A uses 1.5×; plant uses 1×. No material, schedule, wall thickness or insulation is established.
- Unit branch continuations in the building view have representative assumed sizes pending unit-specific takeoff. Reducer geometry is simplified.
- Unit A island route between annotated drops and exact hot/return loop junctions are assumed. The 2D overlay deliberately exposes this approximation. A visual comparison has been performed; there is no calibrated overlay score or dimensional acceptance.
- Boiler charging and return connections are diagrammatic. Relief/drain piping, flues, detailed controls and balancing bypasses are incomplete. WAC2 is a loose spare and is not shown as installed.
- Common-area, garage and irrigation services are not included. Unit 106 is a continuation only.
- Sanitary, vent, gas, fire protection and an architectural building model are not included.
- Do not extract construction quantities or shutdown boundaries from these coordinates.

## Validation performed

- Unique IDs and provenance on 319 elements; positive pipe diameters and explicit nominal-size status.
- Counts checked against the takeoff: 5 stack groups, 23 typical branch groups, 14 Unit A fixtures, 2 boilers, 2 storage tanks, 4 expansion vessels, 3 installed pumps.
- All vertices and terminal routes in the building and unit distribution graphs reach their own system root. Tees on straight segments are recognized. Separate-system reachability does not validate hydraulic sizing, plant internals, cross-system return flow or source interpretation.
- Cycles CPU renders inspected in plan, front, side and isometric views. Orange provenance renders identify the assumed spatial geometry. Owner-color views identify systems, not provenance. Review PNGs were checked for blank output.
- Unit A model-projected overlay visually reviewed against the source crop. It is a route review, not measured alignment.
- Standalone HTML tested over local HTTP in Chromium with software WebGL: all three GLBs load; system toggles and source dialog work; no JavaScript errors or horizontal overflow at desktop/mobile sizes. Camera framing was corrected after inspecting the mobile screenshot. Offline file opening was not tested in the managed browser, which disallows local file URLs; the viewer embeds all models and code and makes no external asset requests.

## Next inputs needed

Begin with one verified Unit 107 plan dimension or a dimensioned architectural plan, then ceiling / floor elevations. Resolve its dishwasher connection and return-loop details. Establish shaft positions before placing the risers spatially. If the objective is the actual installed system, confirm routes and equipment with field records/photos. Extend to other units and sanitary/vent/gas only after the pilot geometry is checked.

The working model and review documents are delivered under `deliverables/highland-water/`. No new owner walkthrough video was made: dimensional review comes first.
