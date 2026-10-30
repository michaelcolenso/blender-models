# Meydenbauer Construction Intelligence Explorer

A deliberately small, static first Explorer slice over the canonical CIE state and semantic GLB metadata.

## What it proves

1. A clicked GLB object resolves through its `cie_id` to the canonical project state.
2. The inspector walks from an element to claims/evidence, quantities, activities, and open issues.
3. Evidence mode visually separates confirmed/provisional/assumed/unknown geometry instead of flattening certainty.
4. S1/S2/S3 switching reads scenario quantities from project state and makes the 700 SF allowance decision explicit.

No construction math lives in the browser. The Explorer is a view over `state/project-state.json`; the existing takeoff/schedule/logistics pipeline remains authoritative.

## Run

Serve the repository root with any static HTTP server and open:

`projects/meydenbauer-b/products/explorer/index.html`

The page expects the semantic GLB at `projects/meydenbauer-b/deliverables/underslab/Meydenbauer-B-underslab.glb` and project state at `projects/meydenbauer-b/state/project-state.json`.

## Verify

`uv run bm run meydenbauer-b/explorer check`

The check is CPU-only and validates the state contract, scenario decision values, UI wiring, semantic selection path, and absence of duplicated scenario headline values in JavaScript.
