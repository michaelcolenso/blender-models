# Meydenbauer canonical construction state

This directory is the migration seam between the existing Meydenbauer production pipeline and the Construction Intelligence Engine.

`build_project_state.py` wraps verified values from the current under-slab deliverable in the canonical semantic model. It deliberately does **not** replace the existing extraction, takeoff, scheduling, logistics or Blender code yet.

The first state encodes the decision chain behind the slab allowance: drawing evidence, unknown POC depth, confirmed typical trench width, S1/S2/S3 scenarios, slab-cut/excavation quantities and unresolved risk.

## Run

From the repository root:

```bash
python projects/meydenbauer-b/state/build_project_state.py
pytest -q tests/test_cie_kernel.py tests/test_meydenbauer_state.py
```

The generated `project-state.json` is committed as a reviewable golden snapshot. A later CI step should regenerate it and fail on unexplained drift.

## Next extraction seam

Replace bootstrap constants with adapters reading `takeoff.json`, schedule/logistics outputs and per-run metadata. Then emit individual pipe/trench/fixture/structure elements with stable IDs. The first target is a real B-104 pipe that can be selected in the GLB and traced through evidence, quantity, scenario and activity records.
