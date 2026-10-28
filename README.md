# Blender models of construction projects

Dimensionally accurate, provenance-tracked 3D models of restoration and defect-repair work in occupied
multifamily buildings, built headless in Blender from construction drawings, details, specs and site photos.
Accuracy first, realism second: every dimension traces to a source or is labeled assumed, automated checks
must pass, and the renders get looked at. How models are made: **[docs/METHOD.md](docs/METHOD.md)** ·
step-by-step commands: **[docs/RUNBOOK.md](docs/RUNBOOK.md)**.

## Quickstart

```bash
uv sync                                   # Python 3.11 + locked bpy 5.0.1, PyMuPDF, OpenCV (one environment)
uvx pre-commit install                    # once per clone: blocks oversized or unsourced commits
uv run bm list                            # sites, specs, products
uv run bm new <site> --type detail        # start a project from templates/project/
uv run bm build <site>                    # build + verify every spec of a site (or <site>/<spec>)
uv run bm check                           # provenance, metadata, large files, links, tests
```

Linux needs the X11 libraries bpy links against:
`sudo apt-get install libx11-6 libxrender1 libxfixes3 libxi6 libxext6 libxkbcommon0 libsm6 libice6 libgl1`.
Always run Python through uv (`uv run python …`, `uv run bm …`). Node pieces (browser viewers, Playwright
films) use npm inside their product folder.

## Layout

```
projects/<site>/
  project.yaml               name, address, building type, scope, release tag prefix
  sources/manifest.json      inventory of drawings and photos (the files themselves stay out of git)
  specs/*.yaml               spec-driven models: detail | house | room | element  → `bm build`
  takeoff/                   extracted plan data the specs read
  products/<name>/           bespoke pipelines (films, viewers, bid models) + product.yaml steps → `bm run`
  deliverables/<name>/       what gets handed over: READMEs, previews; large files via Releases
src/bmodels/                 the shared toolkit and the `bm` CLI
templates/project/           what `bm new` copies
assets/                      shared CC0 assets (HDRIs)
render/                      saved-scene shot catalog for the render-scenes workflow
docs/                        METHOD.md, RUNBOOK.md
```

## Sites

| Site | Name | Specs | Products |
|---|---|---|---|
| [field-parapet](projects/field-parapet/) | Field parapet (site photo P1) | field-parapet-existing, field-parapet-proposed | — |
| [highland](projects/highland/) | 200 W. Highland condominiums | — | exterior, installation, repipe, walkthrough, water |
| [meydenbauer-b](projects/meydenbauer-b/) | 101 Meydenbauer, Building B | — | underslab |
| [qp-cottage-a](projects/qp-cottage-a/) | Quail Park of Lynnwood — Cottage Duplex A | qp-cottage-a, qp-rake-ah700-12 | — |
| [room-living-kitchen](projects/room-living-kitchen/) | Living room / kitchen (occupied apartment) | room-living-kitchen | — |
| [sample](projects/sample/) | SAMPLE — pipeline fixture (not a real project) | sample-bay | — |

Regenerate with `uv run bm list --markdown`. Highlights: Highland
[archviz walkthrough](projects/highland/deliverables/archviz/README.md),
[installation film](projects/highland/deliverables/installation/README.md),
[cinema shot list](projects/highland/products/walkthrough/CINEMA.md) (film not published);
Meydenbauer [bid model, realism views and 4D films](projects/meydenbauer-b/deliverables/underslab/README.md).

## Commands

| Command | Does |
|---|---|
| `bm build [path \| site \| site/spec] [--realistic] [--changed BASE]` | build, verify and render specs → `build/<site>/<spec>/` |
| `bm run <site>/<product> <step> [args]` | run a step declared in `product.yaml` |
| `bm check [--staged \| --base REF]` · `bm check-products` | repo checks · every product's `check` step |
| `bm publish <site>/<product> <files…>` · `bm assets pull\|verify <manifest>` | large outputs to/from GitHub Releases |
| `bm calibrate`, `extract`, `overlay`, `detail-overlay` | drawing intake (see the runbook) |
| `bm render`, `render-plan`, `animate-house`, `animate-sequence`, `room`, `skp`, `usdz`, `audit-blends` | renders, sequences, exports, scene audit |

## Large files

New files over 1 MB (MP4, .blend, ZIP, EXR, GLB, big GIF/HTML) go to **GitHub Releases**, not git:
`uv run bm publish <site>/<product> <files…>` uploads them, records sha256 in the product's
`release-assets.json`, keeps the local copies out of git and prints README links; `uv run bm assets pull
<manifest>` restores them. `bm check` (pre-commit and CI) rejects new oversized files. Files already in Git LFS
stay there and may be updated; nothing new goes to LFS.

## CI

| Workflow | When | What |
|---|---|---|
| `build-models` | specs, takeoff, products, `src/`, lock change | `bm build --changed` (every spec when code or the lock changes) and `bm check-products`; reports in the job summary, `build/` as artifact |
| `checks` | every PR and push to main | `bm check --base …` (provenance, metadata, large files, links, tests) and `bm audit-blends` |
| `render-scenes` | `render/`, renderer or project changes | render each shot in `render/scenes.json` on CPU and validate the pixels |
| `highland-*` | manual | Highland native film, archviz review and preview renders |

Every workflow sets up through `.github/actions/setup-blender-env` (apt libraries, setup-uv cached on
`uv.lock`, `uv sync --frozen`). Pushes from a local clone can change workflow files; cloud agent tokens
without the `workflow` scope cannot.
