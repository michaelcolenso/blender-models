# Meydenbauer 4D Blender Script — Critical Review + Route Revision v2

## Result

Revised script: `meydenbauer_4d_3pass_v2.py`

Static verification status: **PASS**
- Python compilation: PASS
- AST parse / duplicate top-level definitions: PASS
- Pure route/network validation: PASS (0 issues)
- Connected 4in→6in→existing lateral network: PASS for B-101 through B-104
- Gravity direction: PASS for all modeled main/branch segments
- Replacement lateral scope: PASS at 18 in outside east foundation
- Blender runtime execution: NOT RUN (Blender executable is not installed in this runtime)

## High-value defects found and corrected

1. **Longitudinal grid was 5.5 in short.** H-I is 27'-6.5 in on the bid sheet, not 27'-1 in. Building A-M is now 160'-5.5 in.
2. **Pipe routes were too schematic.** Replaced with P1.02/P3.1/P3.2 grid-relative control tables for all four units, including actual plan bend character and east exit locations.
3. **6 in scope was modeled too far outside.** New 6 in laterals now stop exactly 18 in beyond the east foundation, with separate existing-lateral context continuing to the 8 in side sewer.
4. **B-101/B-104 prior ABS risked scope ambiguity.** Prior 4 in Schedule 40 ABS is explicitly separated and tagged REMAIN.
5. **Branches could visually float from mains.** Z is now solved as one connected gravity network; branch endpoints inherit main elevation at their junction.
6. **Trench bedding/backfill used generic depths.** Layers now derive from the connected pipe centerline/diameter for each segment.
7. **Boolean trench cutters could leave corner slivers.** Cutter ends now overlap at bends and extend 1 in above slab top to avoid coplanar Boolean faces.
8. **Boolean fallback could silently cut only one trench.** Removed. A collection-Boolean failure now raises explicitly rather than producing plausible but wrong geometry.
9. **4→6 transition coupling was oriented vertically.** Corrected to horizontal along the east-west lateral.
10. **Water-test and borescope visuals used independent approximate paths.** They now reuse the same solved 3D pipe network.
11. **Polygon prism cap winding could produce bad normals.** Corrected for consistent manifold shading/export.
12. **Phase driver failures could be silent.** Visibility-driver errors are now tagged and surfaced in model validation.
13. **Phase startup state was not fully deterministic.** `PHASE_CONTROLLER` now explicitly returns the scene to frame 1 after keyframe creation.

## Geometry/source reconciliation

- Building B modeled as slab-on-grade with four ground-floor units.
- Apparent stack context remains 12 stacks: four 4 in + eight 3 in.
- Existing side sewer context is explicitly 8 in; the requested collection name `Side_Sewer_Main_6in` is retained only for hierarchy compatibility. Scene metadata identifies the actual nominal size.
- Under-slab model depths produced by the current connected controls are approximately 2.55–3.61 ft, within the documented 2.5–4.5 ft investigation range.
- Raw trench plan area using current assumed widths is 496.8 sf before overlap, versus the 700 sf contract allowance. The script treats 700 sf as a benchmark, not a forced geometric target.

## Remaining material risks before construction-grade use

1. Exact invert elevations are still field-verification data; the drawings explicitly require verification before installation.
2. Route control points are traced plan approximations, not Matterport/GPR survey coordinates.
3. Interior architectural partitions and finish zones remain visualization-grade; they are not a full architectural BIM reconstruction.
4. Actual Blender evaluation/render still needs one run in Blender to verify dependency-graph behavior, Boolean evaluation, driver assignment, and render appearance.

## Recommended Blender acceptance test

Run the complete script in a blank Blender file, then check:
- `validate_model()` prints no warnings;
- slab Boolean opens all trench paths without corner slivers;
- Phase 1→8 visibility changes correctly at frames 1/31/61/91/121/151/181/211;
- B-101/B-104 retained ABS remains visible while cast iron disappears after Phase 3;
- Phase 5 water proxy sits inside the new 4 in mains;
- Phase 6 bedding/backfill/pourback exactly follows the same trench route;
- no adverse-slope or disconnected-junction warning appears.
