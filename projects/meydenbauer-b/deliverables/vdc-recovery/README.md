# Meydenbauer B — VDC and B101 v4 reconciliation

**Illustrative, not a contract document.** The recovered data is provisional or assumed, as labelled in its
sources, and none of it is field-verified. This report compares it with the canonical under-slab state. It
recommends nothing for adoption yet.

Generated figures are in [reconciliation.json](reconciliation.json), produced by the
[vdc-recovery product](../../products/vdc-recovery/README.md). Lengths are LF, areas SF, volumes CY. The
canonical values are takeoff S2 @ 3.5 ft unless stated otherwise.

## Findings

1. **The new-ABS totals agree only by coincidence.** VDC has 311.65 LF against canonical 312.74 LF, a
   difference of −0.35%. By unit, the differences are large and offset each other:

   | Unit | VDC | Canonical | Δ |
   |---|---:|---:|---:|
   | B101 | 72.59 | 66.21 | +6.38 |
   | B102 | 76.06 | 85.21 | −9.15 |
   | B103 | 93.30 | 64.81 | +28.49 |
   | B104 | 69.70 | 96.51 | −26.81 |

   VDC models 30 schematic routes, one per fixture group, and measures them on curve centerlines.
   Canonical has 136 segments extracted from P1.02. Don't use the VDC total to confirm the bid quantity.
2. **B103 has a route that isn't in the canonical extraction.** `NEW_ABS_B103_4in_RAISED_FLOOR` is 30.7 LF,
   and its endpoints lie 17–24 ft from any canonical B-103 segment. It accounts for most of B103's +28.5 LF.
   B103 is also the only unit where VDC's new length (93.3) differs from its demolition length (62.6). Is
   this run in scope? A drawing or RFI must answer that; this report doesn't. Six other routes also have an
   endpoint more than 5 ft from canonical: the B101 and B102 mains, the B102 and B103 6-inch laterals, B102
   kitchen and B104 laundry. I compared endpoints only, because the full curves exist only in the archived
   scenes.
3. **B101 v4 agrees with canonical B-101 on the new work.** It has 45 route controls. Those for the new
   main, branches and stubs lie 0.01–1.23 ft from canonical B-101 segments. The existing connection to the
   side sewer lies 9–18 ft away, outside canonical's extent. The retained, previously repaired
   kitchen/dining run lies 11–20 ft away, so canonical correctly leaves it out of new work, as B101 v4 states.
   VDC's B101 total (72.59 LF) is higher than canonical (66.21 LF).
4. **The same plan frame, but different geometry.** Both datasets are in feet in the same frame. The median
   VDC route endpoint lies 0.86 ft from a canonical segment of the same unit. That is close enough to
   cross-reference units and routes, but VDC's identifiers can't be mapped one-to-one onto canonical
   elements. VDC has 2,980 objects with unique IDs; none of them exists in canonical state.
5. **Slab cut is close in total, not by unit.** VDC's 634.9 SF falls between canonical S1 (590.1) and S2
   (686.1); canonical S3 is 991.0. B101, B102 and B103 are within 15 SF of S2. B104 is 158.4 against 214.7.
6. **Volumes aren't comparable.** VDC's bedding plus backfill (144.7 CY) is not bank excavation (canonical S2:
   82.4 CY). The two use different boundaries and methods.
7. **The schedules aren't alternatives.** VDC MEYD-BL-001 is 8 serial project-wide phases, 29 working days,
   2027-01-04 to 2027-02-11, and it retimes the 672-frame animation. Canonical is 32 activities chained unit
   by unit: 81.5 working days, about 115 calendar days. They differ in structure, and in their scope, crew
   and occupancy assumptions. Neither duration can stand in for the other until those are reconciled.
8. **The issue lists differ.**
   - VDC raised 5 issues. P2-001, the B103 slab penetration, is resolved with a modeled sleeve. Four are
     open: P2-002 and P2-004 (B101 lav slope 0.319 against 0.250 in/ft), P2-003 (side-sewer slope
     undocumented) and P2-005 (B103 raised-floor slope undocumented).
   - Canonical has 2 issues, including POC inverts undocumented (critical).
   - None of them are cross-linked yet.
9. **VDC covers more scope.** It quantifies items canonical doesn't carry: fixtures to reinstall (60),
   cleanouts (20), firestops (12), framing (48), patch, protection, vapor-barrier and pourback areas, hydro-test
   routes, and more. Canonical carries what VDC lacks: the S1/S2/S3 trench scenarios, allowance decisions,
   haul logistics and the occupied unit-by-unit sequence.

## Owner decisions (2026-11-05)

These are recorded as claims in the canonical state, with owner-decision evidence.

1. **The B103 raised-floor route is not in scope.** `NEW_ABS_B103_4in_RAISED_FLOOR` and its sleeve stay out
   of canonical state.
2. **VDC's extra scope items are adopted** as canonical unit-level quantities: 40 in all, 10 measures × 4 units.
   - **Counts:** fixtures, casework and finishes to reinstall; new cleanouts, firestops, fittings and framing.
   - **Areas:** new patch, wall-opening demolition and temporary protection.
   - **Status:** they are **assumed, low confidence**. VDC modeled a typical unit, so most values are
     identical in all four units. Field-verify them before pricing.
   - **Kept on canonical geometry:** quantities VDC measured from its own routes (pipe, slab cut, bedding,
     backfill, pourback, vapor barrier, test routes), plus context objects and existing-to-remain items. The
     reasons are in [scope_import.py](../../products/vdc-recovery/scope_import.py).
3. **The canonical schedule governs:** 81.5 working days, unit by unit. VDC MEYD-BL-001 (29 working days)
   is reference only.
4. **The archived scenes are to be published to Releases for geometry review.** The seven `.blend` files
   (443 MB) are listed in [release-assets.json](../../products/vdc-recovery/release-assets.json), and the
   owner uploads them with `publish_scenes.sh`. Canonical state does not depend on them.

Not decided: whether VDC's 4 open issues (slopes, undocumented inverts) become canonical issues.
