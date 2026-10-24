# Source Index

## Contract / design sources

### Exhibit A — Waste Re-Pipe Bid Set
Primary drawing source for demolition, routing, enlarged plans, and plumbing details.

Key sheets used by the model:

- P1.01 — Waste Plumbing Demolition Plan; demolition notes and protected prior B-101 repair.
- P1.02 — Foundation / under-slab routing context and east laterals.
- P2.1 — first-floor waste context.
- P3.1 — Units B-101 / B-102 enlarged plumbing plan.
- P3.2 — Units B-103 / B-104 enlarged plumbing plan.
- P5.0 — trench/backfill and connection details.
- P5.1 — trench infill / penetration / related plumbing details.

### Addendum 1 — 2026-10-16
Use the current addendum where it modifies or clarifies earlier documents.

Critical Scope of Repair passages used in v4:

- Under-slab system includes cast-iron pipe, fittings, elbows, tees, adapters, first-floor P-traps, and toilet wall flanges/carriers.
- Replacement extends from side sewer connection outside the building (+18 inches) inward to first-floor fixture drains and vertical DWV reconnections.
- Existing B-101 prior repair remains to minimize interior finish damage.
- Present pipe should be completely removed unless Engineer-approved abandonment is authorized.
- Existing vapor barrier is exposed/identified/preserved for transition to new Stegowrap.
- Vertical stack exposure must permit complete fittings/connections; wye, combination wye + 1/8 bend, sanitary tee as applicable.
- Support piping above and below cut locations; no partial/notch repairs.

### Project Manual Bid Set — 2026-09-28

- Section 02 41 19 — Selective Demolition.
- Systematic demolition; neat sawcuts; protect work to remain; maintain utilities; remove/reinstall/salvage requirements; pollution/dust control.
- Section 03 30 00 — Cast-in-Place Concrete and related slab restoration requirements.

### Scope of Repair — 2026-09-18
Earlier SOR source retained for comparison/context; Addendum 1 is the later clarification where applicable.

### Exhibit B — Record Drawings Partial Precast Concrete Panel Set
Structural/context reference. Do not infer demolition permission from these record drawings alone.

## Derived model / QA sources

- `data/b101_route_controls_calibrated_v2.csv` — plan-traced B-101 route-control export used for QA/reference. The primary v4 script embeds the corresponding route data.
- `data/B101_demolition_fitting_schedule_v4.csv` — generated fitting/cut demolition inventory and confidence notes.
- `qa/B101_calibrated_QA_board.png` — B-101 route calibration visual.
- `qa/B101_demolition_plan_overlay_v3.png` — demolition access/trench/no-demo overlay.
- `qa/B101_fitting_cut_QA_overlay_v4.png` — fitting, P-trap, carrier, bend, and cut-location QA overlay.

## Original modeling brief

`sources/modeling_brief.txt`

This is the implementation brief that defined the desired collection hierarchy, materials, 4D phasing, and unit-specific finish modeling. Contract/source documents remain authoritative where geometry/scope conflicts with the brief.
