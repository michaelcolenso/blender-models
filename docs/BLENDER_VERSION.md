# Blender and Python version policy

**Supported runtime: Blender 5.0.1 (the `bpy==5.0.1` wheel) on Python 3.11.** Nothing else is tested, locked or
guaranteed by this repo. This page records why the pin is deliberate, what is supported versus exploratory, and the
gates any upgrade must clear. It changes no pin, lock or code.

Labels: **confirmed** = read from a file in this repo (cited); **not verified** = stated by a source I did not re-test.

## What is pinned, and where

| Pin | Where | Status |
|---|---|---|
| `bpy==5.0.1` | `pyproject.toml` dependencies; `uv.lock` resolves `bpy 5.0.1` | confirmed |
| Python `==3.11.*` | `pyproject.toml` `requires-python` (comment: "bpy 5.0.x wheels are cp311 only"); `.python-version` is `3.11` | confirmed |
| NumPy 1.26.4 | `uv.lock`; the `vision` group comment says bpy 5.0.1 requires `numpy<2` | confirmed |
| `opencv-python-headless==4.10.0.84` | `pyproject.toml` `vision` group: newest OpenCV that runs on `numpy<2`; the pin also keeps the graded cinema film reproducible | confirmed |
| `bpy.app.version_string == "5.0.1"` | `src/bmodels/render_scene.py` raises `ValueError` otherwise. `render/README.md`: "change the dependency pin and version check together when upgrading" | confirmed |

CI installs from the same lock (`.github/actions/setup-blender-env`: `uv sync --frozen`, then prints
`bpy.app.version_string`). Local machines, CI and RunPod therefore run the same Blender build.

## Why it is pinned

1. **Reproducible, auditable output.** Models feed scopes, PCOs and resident notices. A given spec should rebuild to the
   same geometry, checks and renders from any machine. Floating `bpy` or OpenCV would let a dependency bump change a
   deliverable without any change to a spec.
2. **The pins are coupled.** bpy 5.0.1 forces Python 3.11 and `numpy<2`; that caps OpenCV at 4.10. Moving one
   pin means re-solving the others.
3. **File compatibility runs one way.** `projects/highland/products/walkthrough/README.md` notes that a system Blender 4.3
   cannot open the delivered Blender 5 `.blend`. Re-saving committed `.blend` files with a different Blender version is
   an upgrade cost, not a side effect (`bm audit-blends` exists for the packed-asset rule).
4. **Visual regressions are silent.** Materials, lighting, compositor and EEVEE/Cycles behavior can shift between
   Blender versions while every numeric check still passes. This repo requires both checks and looking at renders
   ([AGENTS.md](../AGENTS.md)).

## Supported versus exploratory

| | Supported | Exploratory (not a supported runtime) |
|---|---|---|
| Blender | 5.0.1 via the locked `bpy` wheel | Anything else, including the 5.2 notes below |
| Python | 3.11 | Any other minor version |
| Evidence | CI (`build-models`, `checks`, `render-scenes`) and local `bm doctor` | Single-machine probes |

`.claude/skills/scenario-blender-expert/references/blender-5.2-deltas.md` is an imported agent-skill reference about
Blender 5.2.1 (its own text says it was probed on 2026-09-24 with Python 3.13). It is **not** a statement that this repo
runs on 5.2. It has not been re-tested against this repo's code, specs or CI. Use it to recognise API differences, never as
a reason to change a pin. Some of its guidance may not apply to 5.0.1 (not verified).

## Upgrade gates

An upgrade is a separate piece of work that needs **explicit owner approval before it starts**. Do not upgrade to "fix"
an unrelated problem. All gates must be met in one PR (or an explicitly stacked series) with the evidence in the
description:

1. **Scope and approval.** Name the target Blender/Python/NumPy/OpenCV versions and why. Owner approves.
2. **Baseline on 5.0.1.** On current `main`, record `uv run pytest -q`, `uv run bm check`, `uv run bm build` for every
   spec (`report.json` check counts), `uv run bm check-products`, `uv run bm audit-blends`, and the `render-scenes`
   outputs. Keep the baseline renders.
3. **Change the pins together.** `pyproject.toml`, `uv.lock` (via `uv add` / `uv lock`, never by hand), `.python-version`,
   the `render_scene.py` version check, `render/README.md`, and any product docs that state `5.0.1`
   (`grep -rn "5\.0\.1"`). Re-solve NumPy and OpenCV.
4. **Same tests, new runtime.** Repeat every baseline command. Any spec whose check counts or extents change is a
   defect until explained; geometry must not move because of a Blender upgrade.
5. **Visual comparison.** Review the review PNGs of at least one spec per model type (detail, house, room), the
   `render-scenes` shots, and one film frame set side by side with the baseline. Record what you looked at; "checks passed"
   alone is not sufficient.
6. **Committed `.blend` files and films.** Decide per file whether it is re-saved or left as built; run
   `bm audit-blends`. Published films and Release assets are not silently replaced.
7. **GPU path.** Confirm the RunPod scripts (`products/*/runpod_*.sh`) against the new wheel's GPU support; this cannot
   be verified on CPU-only machines or CI.
8. **Rollback.** Keep the change revertable as one commit/PR (restore the pins and lock). Do not delete the baseline until
   the new runtime has been through a CI run on `main`.

The upgrade PR must not claim CI green until the run has completed.
