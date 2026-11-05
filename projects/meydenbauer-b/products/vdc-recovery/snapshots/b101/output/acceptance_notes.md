# B-101 v4 execution and acceptance review

**REVISION REQUIRED — model execution and coordination acceptance are separate results.**

Execution completed successfully: all three passes, strict validation, eight requested Eevee renders, save, and fresh-process reopen verification. Launcher exit code: 0. Both supplied validation reports contain no issues. The saved scene contains 1,038 objects. No runtime fixes were necessary. Twelve additional diagnostic renders are included.

## Environment and commands

Blender 4.3.2; Linux x86_64, kernel 6.18.55. Package directory: `/workspace/meydenbauer-run/Meydenbauer_B101_Blender_Core_v4`.

Primary command: `bash run_blender.sh --render-keyframes`.
The launcher adds `--fail-on-warning`, builds passes 1,2,3, saves the blend, renders eight checkpoints, saves again at frame 1, and opens the saved file in a fresh Blender process for verification.

Additional read-only checks: `blender --background output/Meydenbauer_B101_Demolition_v4.blend --python-exit-code 1 --python scripts/extended_runtime_qa.py`.
Diagnostic views: the same command with `scripts/render_detail_qa.py`.

## Acceptance blockers

1. **Protected prior-ABS envelope conflict.** At frame 89, evaluated slab openings intersect `B101_DEMO_PriorRepair_NoDemo_Envelope`. A 3-inch sample grid finds 38 open samples of 6,400 within that envelope, approximately 2.375 square feet (sampling estimate, not an exact quantity). The responsible authored cutter objects are `TrenchCutter_B101_001` and `TrenchCutter_B101_008`, near the tie/laundry interface around X=22–24 ft, Y=27.5–28.5 ft. This is actual evaluated geometry, not a missing modifier or failed Boolean. The broad envelope remains FIELD_VERIFY; resolving the intended boundary requires a modeling/scope decision. No route or protection-boundary redesign was made.
2. **Authored review-camera visibility.** `MEYD_ISO_CAMERA` is a general building camera, poorly framing B-101 and looking through upper-floor context. Upper-floor slabs obscure demolition; Phase 1 x-ray is noisy, and later phases make the structural material opaque. Requested renders are preserved. Supplemental cutaways temporarily omit obstructing context without saving changes. The default camera does not meet the checklist requirement to show B-101 work clearly enough for coordination.

## Evaluated runtime checks

- No invalid drivers, `MEYD_DRIVER_ERROR` flags, or nonfinite object transforms were found at tested checkpoints.
- `Construction_Phase` and `Demolition_Subphase` evaluate to the intended states: 1/0, 2/1, 2/2, 3/3, 3/4, 3/5, 3/6, 3/7 for the requested eight frames. Later construction phases also evaluate through frame 211.
- Slab Boolean is off through frame 68 and on from frame 76. Both viewport/render toggles agree.
- Evaluated slab: 454 vertices, 239 faces, zero nonmanifold edges, Z=-0.4583333 to 0 feet, consistent with 5.5 inches.
- A 3-inch grid across the original slab footprint checks 170,130 points against the actual cutter union: zero mismatches; 7,566 open samples. This supports correct Boolean evaluation; it does not establish source correctness or exclude every sub-grid sliver.
- Expected fitting inventory exists: 10 junction bodies, seven P-traps/conditional traps, seven plan bend objects, both WC carrier bodies, and ten temporary support rings (above/below five vertical cuts).
- WC cut elevations are 40 inches; wet-core/laundry cuts are 36 inches. Exterior cut is at Y=-1.5 feet, the +18-inch exterior limit. These remain coordination targets with FIELD_VERIFY tags.
- Seven REMAIN-role objects stay render-visible at all eight checkpoints. Existing demolition cast-iron role count changes from 88 to zero at frame 89; retained objects remain.
- 198 objects retain FIELD_VERIFY tags. No surveyed/as-built or fabrication claim is made.

## Visual review and limitations

Supplemental Workbench cutaways are geometry diagnostics, not replacements for the unchanged Eevee deliverables. Camera and visibility overrides are documented in changes.md and in the diagnostic script. The source blend retains its authored camera, scene content and shaders.

Frames 001/038/050 show existing fixtures followed by access-item proxies/protection and finish-strip markers. Frame 061 removes the finish strip markers and shows vertical exposure/cut markers. Frame 068 adds sawcuts. Frame 076 shows lifted slab chunks and vapor exposure. Later-frame, slab-only and fitting-only review findings are recorded below.

The supplied static route validator checks calibrated control bounds, continuity, transition elevations, lateral extent, slopes, and prior-ABS tie location. The original contract PDFs are not included in this core package; no independent contract-document/as-built certification is claimed.

The east structural crossing warning remains FIELD_VERIFY / DO_NOT_CUT_STRUCTURE. Slab cutters are not applied to foundation objects. Actual structural conditions remain unverified.

All supplied Python sources are byte-identical to the uploaded ZIP. Added scripts only inspect or render the saved scene. No runtime model correction was required.

### Completed diagnostic render review

- Frame 076: chunks visibly lift above the trench; vapor/excavation overlays appear.
- Frame 083: chunks are gone; CI assemblies, WC carriers and cut/support rings remain. Frame 089 removes the CI/carrier assemblies. Excavation/vapor overlays persist, so this is a coordination visualization rather than a literal empty soil cavity.
- Isolated slab plan: openings are continuous across B-101 branch/main bends, with no visible disconnected corner slivers at this render scale. Cutter endpoint extensions create some small notches/steps. The no-demo-boundary intrusion remains a blocker.
- Fitting-only view: branches and bends follow the modeled pipe directions; cut rings and above/below supports are aligned around the corresponding verticals. Generic traps/fixture stubs are coordination proxies, not surveyed complete fixture connections. Exact concealed fitting classifications remain FIELD_VERIFY.
- Frame 038 default Eevee view is almost entirely occluded by opaque upper-floor slabs, confirming that the supplied camera cannot visually establish the demolition progression. Diagnostic views resolve inspection access, but do not repair the source model's camera/visibility acceptance failure.

See `renders/detail/B101_prior_ABS_envelope_conflict_089.png` for a close-up of the actual evaluated opening crossing the red diagnostic outline of the existing no-demo envelope. The outline derives from that object's bounds; it is not a newly asserted field boundary.

The isolated new-ABS view at frame 091 follows the QA board topology, including both wet-core branch clusters and the retained prior-ABS tie. This additional diagnostic view is included as `renders/detail/B101_new_ABS_route_091.png`.

Timing qualification: the authored access-item movement begins at frame 038 and reaches storage at 048. Frame 038 itself shows the start of movement, not completed storage. This is documented rather than retiming the source animation.
