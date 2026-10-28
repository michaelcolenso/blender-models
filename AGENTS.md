# AGENTS.md

Provenance-tracked Blender models of construction projects, one folder per jobsite. Method:
`docs/METHOD.md` (read before modeling). Commands step by step: `docs/RUNBOOK.md`. Layout: `README.md`.

## Start here

```bash
uv sync                      # once per session if pyproject.toml/uv.lock changed
uv run bm doctor             # what this machine can run, and the exact fix for each gap
uv run bm list --json        # every site, spec (with kind), product (with steps) and deliverable folder
uv run bm run <site>/<product>   # a product's steps and their commands
```

Don't guess paths or commands: `bm list --json` and `product.yaml` are the source of truth. Every product
has a `README.md` next to its `product.yaml`.

## What runs where

| Work | This laptop (WSL, no GPU) | CI (GitHub Actions) | RunPod GPU |
|---|---|---|---|
| `bm check`, specs, links, metadata, tests without bpy | yes | `checks` | — |
| bpy builds/renders (`bm build`, `bm render`, `audit-blends`) | only after `bm doctor`'s apt fix | `build-models`, `checks`, `render-scenes` | yes |
| product `check` steps | bpy-free ones | `build-models` | — |
| prepare/extract from source PDFs | only if PDFs are in `projects/<site>/sources/` | never (not committed) | if copied |
| GPU Cycles films | no | no | `products/*/runpod_*.sh` |

If something can only be verified in CI, say so, push a branch, and read the run (`gh pr checks <n>`,
`gh run view <id> --log-failed`) instead of claiming it works.

## Verify your change

| You changed | Run | Must see |
|---|---|---|
| a spec or takeoff | `uv run bm build <site>/<spec> --no-render`, then without `--no-render` and look at the review PNGs in `build/<site>/<spec>/` | `**PASS** — n/n checks` |
| `src/bmodels/` | `uv run pytest -q` and `uv run bm check`; CI rebuilds every spec | all pass |
| a product | `uv run bm run <site>/<product> check` (or `bm check-products`) | exit 0, no tracked diff |
| docs or moved files | `uv run bm check --no-tests` | `ok markdown links` |
| dependencies | `uv add …` (never edit the lock by hand), `uv lock --check` | lock in sync |

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
- The bpy 5.0.1 wheel mislabels its tag, so a syncing `uv run` reinstalls bpy each time (harmless, ~0.1 s).
  In scripts and parallel workers: `uv sync --frozen` once, then `uv run --no-sync …`.
- Build outputs go to `build/` (git-ignored): specs to `build/<site>/<spec>/` (`report.md`, `report.json`,
  `.blend`, `.glb`, review PNGs). Read `report.json` for machine-readable check results.
- Headless Blender has no GPU: Cycles on CPU only (Workbench/EEVEE render blank). Cameras need explicit
  rotation. This laptop (WSL, Iris Xe) cannot import bpy without the X11 libs and has no GPU or Unreal:
  bpy builds are verified by CI; GPU renders run on RunPod (`products/*/runpod_*.sh`).

## Where work goes

- New project: `uv run bm new <site> [--type element|detail]`; new product: `uv run bm add-product <site>/<name>`.
  Then fill `project.yaml` and
  `sources/manifest.json`. Source PDFs/photos stay in `sources/` (git-ignored, only the manifest is committed).
- Spec-driven models: `projects/<site>/specs/*.yaml`, built with `bm build <site>[/<spec>]`.
- Anything bespoke (films, viewers, bid models): `projects/<site>/products/<name>/` with a `product.yaml`
  (`kind`, `description`, `deliverables`, `steps`). Include a `check` step: fast, CPU, no source PDFs, ideally
  "regenerate a tracked output and `git diff --exit-code` it"; CI runs it. Steps run from the repo root
  with `$BM_PRODUCT_DIR`, `$BM_BUILD`, `$BM_DELIVERABLES` set. Run with `bm run`.
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

## Known traps

- **Generated READMEs.** Several deliverable READMEs are written by product scripts (e.g.
  `products/walkthrough/package_archviz_film.py`). Edit the script too, or the next run reverts your change.
- **LFS pointers.** Without `git lfs pull`, some `.blend`/`.mp4`/`.zip` files are 130-byte pointer files;
  `bm doctor` lists them. Don't treat them as corrupt or re-render them.
- **Self-contained scenes.** Committed `.blend` files pack their textures, HDRIs and sounds; keep it that way
  (`bm audit-blends` fails on external paths that are missing).
- **Hard-coded paths.** Never write absolute or session paths (`/workspace/…`, `/home/…`) into scripts;
  inputs come from `projects/<site>/sources/` or an argument, the repo root from `bmodels.paths.ROOT`.
- **Stacked PRs.** A PR based on another branch merges into that branch, not `main`, unless the base branch
  is deleted when it merges. Prefer one PR to `main`; if stacking, say so in each PR.
- **Shell quoting.** Write commit messages and PR bodies with a quoted heredoc (`-F - <<'EOF'`); backticks
  inside double quotes execute.

## Working style

Ask once, batched, only for what the documents can't answer (a missing detail, which revision governs).
Otherwise take the next step and mark assumptions. Don't claim accuracy beyond what the sources support.
