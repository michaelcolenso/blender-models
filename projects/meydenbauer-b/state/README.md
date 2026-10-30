# Meydenbauer canonical construction state

`build_from_artifacts.py` is the live adapter for the existing under-slab spec, takeoff, logistics and schedule.
It writes the reviewable `project-state.json` snapshot consumed by the Explorer. `build_project_state.py`
is a compatibility entrypoint to the same adapter; it no longer supplies bootstrap constants.

The adapter calls `schedule.build(takeoff)` using the committed takeoff. The schedule's default build-file
input and production formulas remain unchanged. No Blender build or drawing extraction is needed to regenerate state.

The snapshot includes 136 pipe elements, four units, unit and system scenario quantities, 32 globally chained
activities, inherited evidence/claims/issues, and canonical time/decision metadata:

- `metadata.timeline`: S2 baseline intervals, activity/unit IDs, assumed rates/constraints and schematic phase styles.
- `metadata.decisions`: exact allowance decisions from takeoff; S1/S3 duration is null with `not_calculated` status.
- `metadata.geometry_bindings`: deterministic GLB-node names → semantic IDs and presentation roles, including older
  GLBs without semantic extras. No geometry is created or changed by this adapter.

Case selection is explicit: S1@3.5, S2@3.5, S3@4.5. Values retain takeoff precision. Compared with the retired bootstrap,
pipe length is 312.738611 LF rather than 312.75 LF; S2 slab is 686.115257 SF rather than 686 SF; S3 is 990.957845 SF
rather than 991 SF. These are precision/source corrections, not geometry changes.

```bash
uv run --no-sync python projects/meydenbauer-b/state/build_from_artifacts.py
uv run --no-sync python projects/meydenbauer-b/state/build_from_artifacts.py --check
uv run --no-sync pytest -q tests/test_meydenbauer_artifact_adapter.py tests/test_meydenbauer_time.py
```

The check command fails on snapshot drift and never regenerates it silently.
