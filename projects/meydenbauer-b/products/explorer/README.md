# Meydenbauer Time + Decision Propagation Explorer

The Explorer reads `state/project-state.json` as its only construction-state input. Python adapts the
existing takeoff, schedule and logistics calculations into that state; JavaScript selects canonical
intervals, styles, quantities and decisions. It does not calculate excavation, production or scenario schedules.

## Run

Serve the repository root, for example with `uv run --no-sync python -m http.server 8000`, then open
`http://localhost:8000/projects/meydenbauer-b/products/explorer/index.html`.

Three.js and its loaders use the pinned import map in `index.html` (network access to unpkg required).
The GLB is the existing checked-in under-slab schematic. Its older export lacks `cie_id` extras;
the canonical adapter maps its deterministic pipe/trench node names to semantic element IDs. Newer
exports with `cie_id` extras also work. Material instances are isolated so one unit's state cannot recolor another.

## Time and decision behavior

- Scrub or play 0–81.5 **working days**, B-103 → B-102 → B-101 → B-104, eight phases per unit.
  Click a unit to jump to its start and inspect it; phase buttons jump to exact boundaries.
- Intervals are half-open: the exact boundary belongs to the next phase/unit. Day 81.5 has no active activity.
- The default Time view gives pipes and trench overlays distinct canonical color/opacity states for all eight
  phases, plus future/complete states. Scrubbing from another mode returns to Time.
- Active unit/phase, elapsed/remaining baseline and phase duration, and scenario-tagged unit quantities are shown.
- S1 uses takeoff case `S1@3.5`, S2 uses `S2@3.5`, and S3 uses `S3@4.5`. The S3 comparison combines a deeper
  assumed invert with wider deep cuts; it is not an isolated trench-width experiment.
- Scenario choices update exact takeoff quantities, allowance comparisons and selected-element inspection.
  S1/S3 durations are **not calculated**. The timeline and geometry always remain the **S2 strawman baseline**.
  S2's rates/order are assumptions, not an approved construction schedule. No excavation-only delta is
  presented as a complete scenario duration.
- Colors/opacity are schematic phase overlays, not simulated demolition, measured installed quantities,
  verified test acceptance or scenario-specific geometry. Model/Evidence/Risk modes retain the source mesh materials.

Selecting pipework resolves its semantic ID, then inherited unit/system evidence and claims, scoped quantities,
activities and open issues. Inspector quantities show their owning IDs to distinguish pipe, unit and system totals.

## Regenerate and verify

```bash
uv run --no-sync python projects/meydenbauer-b/state/build_from_artifacts.py
uv run --no-sync python projects/meydenbauer-b/products/explorer/time_model.py
uv run --no-sync bm run meydenbauer-b/explorer check
uv run --no-sync pytest -q tests/test_meydenbauer_time.py
```

`check` is CPU-only and read-only. It verifies canonical snapshot/projection drift, the exact schedule against
`schedule.build(takeoff)`, real GLB-name bindings, and Node tests of the browser's actual interval/scenario helpers.
The full pytest suite also checks canonical provenance and cross-unit activity predecessors. `time-state.json`
is a reviewable generated projection; the browser reads the canonical state's identical metadata directly so
it cannot mix stale snapshots from independent requests.
