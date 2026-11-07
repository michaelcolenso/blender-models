# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

@AGENTS.md

## Architecture (the parts that span files)

- **`bm` CLI** (`src/bmodels/cli.py`, entry point `bm = bmodels.cli:main`). Most subcommands shell out to
  `python -m bmodels.<module>` (e.g. `bm build` runs `python -m bmodels.build <spec> --out build/<site>/`
  once per spec). Pass-through tools (`render`, `room`, `skp`, `usdz`, `audit-blends`, …) map 1:1 to modules.
- **Spec pipeline.** `spec.py` loads a spec and checks its provenance without bpy, so `bm check` and CI planning
  work anywhere. `build.py` (needs bpy) sends each element to a builder by `type`: `detail` → `detail.py`,
  `house` → `house.py`, plus `qto.py` for the xlsx takeoff. A spec with top-level `items` is a room spec
  and goes whole to `room.py`. Then `verify()` runs the spec's `checks` and blank-render guards are added.
  The `.blend`/`.glb`/PNGs are written and `record.py` writes `report.md`/`report.json`. Any failed check
  exits 1.
- **`bm build --changed BASE`** picks specs from the git diff. A change under `src/` or to the lock rebuilds
  every spec. A change anywhere in a site except `products/`/`deliverables/` rebuilds that site's specs.
- **`bm check`** (`checks.py`) checks specs, site/product metadata, large files (with `--staged`/`--base` only)
  and markdown links, then runs `pytest -q`.
- **`src/cie/`**: the Construction Intelligence Engine semantic kernel (claims, evidence, elements, scenarios).
  It is a second package, separate from `bmodels`, specified in `docs/CONSTRUCTION_INTELLIGENCE_SPEC.md`.
  The `tests/test_cie_*` and `tests/test_meydenbauer_*` tests exercise it.

## Tests

- `uv run pytest -q`; one test: `uv run pytest tests/test_bm.py -k <name> -q`.
- Most tests are bpy-free. Tests that need bpy skip when it can't be imported (e.g. `test_render_workflow.py`).
  bpy imports on this laptop, so they run here too; on a machine without bpy a green run doesn't cover them.
- Lint: `uv run ruff check` (line length 120).

## Claude Code

- Project skills in `.claude/skills/`: `model-from-drawings` (drawing set or photo → verified spec model),
  `ship-deliverable` (render outputs → Releases → deliverable README → PR) and `archviz-film-upgrade`
  (VDC/BIM scene → path-traced presentation film; presentation films only, not review renders or
  coordination/work-sequence films). Use them for those tasks.
- Entire records sessions as checkpoints on commit (`.entire/`); don't create checkpoints manually unless asked.
