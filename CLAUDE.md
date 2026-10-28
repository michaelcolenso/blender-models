# CLAUDE.md

Provenance-tracked Blender models of construction projects. Method: `docs/METHOD.md` (read before modeling).
Commands step by step: `docs/RUNBOOK.md`. Layout and tools: `README.md`.

## Non-negotiables

- Every element is `confirmed` (with `source`), `provisional` (with `source` + reference and tolerance) or
  `assumed` (with `basis`). Never present assumed or provisional geometry as documented.
- The spec is the source of truth; never hand-edit geometry without changing the spec.
- Actual lumber sizes (2x10 = 1½ × 9¼), never nominal. Never scale an NTS detail. Calibrate every sheet
  from its own dimension strings, not the title-block scale.
- Conflicting sources: model the governing document and flag the conflict; don't average or pick silently.
- Existing-conditions and proposed-repair models are separate specs/scenes.
- "Checks passed" and "looked at the renders" are both required; say which you did.
- Renders used in a scope, PCO or resident notice carry "illustrative, not a contract document".

## Environment

- **uv only.** `uv sync`, then `uv run bm …` / `uv run python …`. Never `pip`, never a bare venv, never
  `requirements.txt`. Add dependencies with `uv add` (or `uv add --group <pdf|vision|audio|dev>`).
- The bpy 5.0.1 wheel mislabels its tag, so a syncing `uv run` reinstalls bpy each time. In scripts and
  parallel workers: `uv sync --frozen` once, then `uv run --no-sync …`.
- Headless Blender has no GPU: Cycles on CPU only (Workbench/EEVEE render blank). Cameras need explicit
  rotation. This laptop (WSL, Iris Xe) cannot import bpy without the X11 libs and has no GPU or Unreal:
  bpy builds are verified by CI; GPU renders run on RunPod (`products/*/runpod_*.sh`).

## Where work goes

- New project: `uv run bm new <site> [--type element|detail]`, then fill `project.yaml` and
  `sources/manifest.json`. Source PDFs/photos stay in `sources/` (git-ignored, only the manifest is committed).
- Spec-driven models: `projects/<site>/specs/*.yaml`, built with `bm build <site>[/<spec>]`.
- Anything bespoke (films, viewers, bid models): `projects/<site>/products/<name>/` with a `product.yaml`
  listing `steps` (one must be `check`: fast, CPU, no source PDFs; CI runs it). Run with `bm run`.
- Shared code goes in `src/bmodels/`, never imported across sites through `sys.path`. Shared CC0 assets go
  in `assets/`. Repo root in scripts: `from bmodels.paths import ROOT`, not counted `parents[N]`.
- Handover files: `projects/<site>/deliverables/<name>/`.

## Large files

New files over 1 MB go to GitHub Releases: `bm publish <site>/<product> <files…>`, then link the printed
URLs from the deliverable README. Never add new files to Git LFS. `bm check --staged` (pre-commit) and CI
block oversized commits; exceptions go in `.bmcheck.yaml` with a reason.

## Before you finish

- `uv run bm check` (and `bm check-products` if you touched a product) must pass.
- Moving files: `git mv`, keep markdown links relative and valid (`bm check` verifies them), and run
  `bm audit-blends` in CI for any moved `.blend`.
- Commit or push only when asked; branch first if on `main`.

## Working style

Ask once, batched, only for what the documents can't answer (a missing detail, which revision governs).
Otherwise take the next step and mark assumptions. Don't claim accuracy beyond what the sources support.
