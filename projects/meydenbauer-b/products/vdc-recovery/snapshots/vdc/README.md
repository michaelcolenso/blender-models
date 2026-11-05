# Meydenbauer B — VDC Data Spine (Phases 1–3)

VDC upgrade of the 4D construction-sequence model: stable element data spine,
constructability validation, and schedule-driven 4D retiming.

## Model files
- `Meydenbauer_4D_Construction_Sequence_VDC.blend` — Phase 1: data spine (2,980 objects,
  stable `vdc_element_id`, discipline/system/phase/cost-code metadata). Animation unchanged from source.
- `Meydenbauer_4D_Construction_Sequence_VDC_Phase2.blend` — Phase 2 (rev VDC-P2-002):
  route slopes/inverts, clearance checks, final-state quantities written back;
  VDC-P2-001 slab penetration resolved with modeled sleeve `PLM-B103-NEW-SLEEVE-0001`
  (6 in bore, 1.35 in annular gap, +2 in above slab / -3 in below soffit).
- `Meydenbauer_4D_Construction_Sequence_VDC_Phase3.blend` — Phase 3: animation retimed to
  baseline schedule MEYD-BL-001 (29 working days, 2027-01-04 → 2027-02-11, 5-day week).
  Schedule embedded as `VDC_SCHEDULE.json`; all 2,981 objects linked to activities.

## Registers and reports
- Phase 1: `Meydenbauer_VDC_Element_Register.csv`, `..._Data_Spine_Schema.json`,
  `..._Phase1_Validation.json`, `..._Phase1_Data_Package.xlsx`
- Phase 2: `..._Phase2_Issue_Register.csv`, `..._Phase2_Route_Diagnostics.csv`,
  `..._Phase2_Quantity_Refinements.csv`, `..._Phase2_Constructability_Report.json`,
  `..._Phase2_Constructability_Package.xlsx`
- Phase 3: `Meydenbauer_VDC_Schedule.csv`, `..._Phase3_Schedule_Package.xlsx`
- Integrity checks: `..._Integrity_Check.json` (per phase); checksums: `..._SHA256.txt`

## Open constructability issues (rev VDC-P2-002)
- VDC-P2-002 / P2-004: actual slope 0.319 in/ft vs documented 0.250 in/ft (B101 lav branches)
- VDC-P2-003: EX_Side_Sewer_Main_8in slope undocumented — field verify
- VDC-P2-005: NEW_ABS_B103_4in_RAISED_FLOOR slope undocumented — field verify

Units: 1 Blender unit = 1 ft, Z-up, imperial. Quantities evaluated at frame 672 (final state).

## Phase 4 — model-linked takeoff (rev VDC-P4-001)
- `Meydenbauer_VDC_Phase4_Takeoff.csv` — 195 lines by cost code / unit / component
- `Meydenbauer_VDC_Phase4_Takeoff_Backing.csv` — element-level backing (full traceability)
- `Meydenbauer_VDC_Phase4_Takeoff_Package.xlsx` — workbook
- `Meydenbauer_4D_Construction_Sequence_VDC_Phase4.blend` — takeoff embedded as `VDC_TAKEOFF.json`

## Phase 5 — field installation package (rev VDC-P5-001)
- Installation schedule (30 routes, layout coordinates + inverts), penetration schedule,
  hydro-test package (47 routes), field verification checklist (75 items)
- `Meydenbauer_4D_Construction_Sequence_VDC_Phase5.blend` — field package embedded

## Phase 6 — cinematic hero renders
- `phase6_renders/` — 4x 1920x1080 Cycles stills (existing / install / hydro test / as-built)
