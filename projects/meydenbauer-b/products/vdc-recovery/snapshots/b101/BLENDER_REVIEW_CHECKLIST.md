# Blender Acceptance Checklist — B-101 v4

The build is not accepted until these checks are reviewed in the actual Blender scene.

## A. Build integrity

- [ ] `scripts/preflight.py` reports `passed: true`.
- [ ] Blender build exits 0 with `--fail-on-warning`.
- [ ] `output/Meydenbauer_B101_Demolition_v4.blend` is created.
- [ ] Saved-blend verification exits 0 after reopening the file.
- [ ] `PHASE_CONTROLLER` exists and exposes `Construction_Phase` and `Demolition_Subphase`.
- [ ] No object has `MEYD_DRIVER_ERROR` set.

## B. Structural / Boolean review

- [ ] `BuildingB_SOG_5p5in` has `MEYD_Trench_Difference` Boolean modifier.
- [ ] Trench Boolean cuts are continuous at bends; no thin corner slivers remain.
- [ ] No Boolean cut intrudes into the B-101 prior-ABS no-demo envelope.
- [ ] East foundation crossing does not imply an unverified structural cut.
- [ ] Slab thickness appears consistently 5–6 inches, with model basis 5.5 inches.

## C. B-101 route calibration

Use `qa/B101_calibrated_QA_board.png` and the P1.02/P3.1 overlays.

- [ ] New 4-inch wet-core main follows the calibrated plan route.
- [ ] Prior ABS kitchen/dining route remains distinct and protected.
- [ ] Prior ABS terminates at the modeled tie without accidental replacement trench continuing into it.
- [ ] New 4-inch main connects continuously to the new 6-inch lateral.
- [ ] Replacement lateral stops 18 inches beyond the foundation face.
- [ ] Branches and fixture stubs terminate in the intended fixture clusters.

## D. Demolition sequence review

At the key frames:

- [ ] Frame 001: existing/initial state is coherent.
- [ ] Frame 038: remove/reinstall access items move to protected storage state.
- [ ] Frame 050: finish strip-out appears only where access is modeled.
- [ ] Frame 061: wall/carrier/vertical-stack exposure is visible without excessive wall demolition.
- [ ] Frame 068: sawcut edges are visible and clean.
- [ ] Frame 076: slab chunks lift/remove; vapor barrier is exposed rather than treated as wholesale demolition.
- [ ] Frame 083: excavation exposes existing cast iron.
- [ ] Frame 089: cast iron is removed and clean trench remains.

## E. Fittings / carriers / cuts

Use `qa/B101_fitting_cut_QA_overlay_v4.png` and `data/B101_demolition_fitting_schedule_v4.csv`.

- [ ] At least 10 modeled existing junction fitting bodies exist.
- [ ] Plan-derived bend objects are oriented along pipe tangents rather than floating or rotated arbitrarily.
- [ ] Seven P-trap/conditional trap objects are present; kitchen trap remains conditional where prior repair scope is uncertain.
- [ ] Both WC carrier/flange assemblies are present and positioned in-wall.
- [ ] WC/stack cut rings are visible at their rule-based model elevations.
- [ ] Temporary support indicators appear above and below vertical cut locations.
- [ ] Prior-ABS tie cut is clearly marked `FIELD_VERIFY`.
- [ ] Exterior 6-inch scope cut is at the +18-inch replacement limit.

## F. Visual / camera review

- [ ] `MEYD_ISO_CAMERA` shows the B-101 demolition work clearly enough for coordination.
- [ ] Materials distinguish existing CI, retained ABS, new ABS, concrete, excavation, vapor barrier, and demolition/highlight layers.
- [ ] X-ray/cutaway treatment does not obscure the demolition geometry.
- [ ] Rendered keyframes contain no missing materials, black frames, clipping, or hidden-camera failures.

## G. Acceptance outcome

Record one result in `output/acceptance_notes.md`:

- **ACCEPTED FOR COORDINATION** — geometry/phasing behaves as intended, with field-verify items preserved.
- **REVISION REQUIRED** — list exact object names/frames and screenshots.

Do not upgrade the status to fabrication/as-built without field-verified routing, inverts, existing fitting conditions, and structural/finish confirmation.
