# Showcase: "One Model"

A marketing film for the studio: one building seen seven ways, each movement showing a Blender 5 capability on
real geometry. The plan is in [`shots.json`](shots.json) (about 60 s, 16:9 with a 9:16 cut, cut to 80 BPM).

| # | Movement | Capability | Status |
|---|---|---|---|
| 1 | Ink | Grease Pencil v3 draw-on, Geometry Nodes extrusion | proof rendered |
| 2 | Assembly | Geometry Nodes simulation zone, XPBD solver | planned |
| 3 | Light | physical sky, light groups, light linking | planned |
| 4 | Matter | Cycles, CC0 scans, bevel, depth of field | planned |
| 5 | X-ray | animated section, flow along curves | planned |
| 6 | Truth | Freestyle, clay, provenance colours | proof rendered |
| 7 | Release | the roof descent from the owner film | exists in `walkthrough` |

## The building is generalized

The canvas is the Highland exterior study, but nothing on screen identifies it: no address, sheet numbers,
signage, street names or OSM neighbours. `proto.py` deletes the caption objects, and `build.py --check` fails
if a movement's title or description names the site or a sheet. The massing itself is still the real
building's, so treat the film as public only with that accepted. Mirroring or re-cladding the facade is the
next step if it must not be recognizable at all.

The provenance colours in movement 6 follow each element's own `status`, as the exterior builder's provenance
pass does. On this model every element is `assumed`: 165 window positions are provisional and 3 roof datums
are confirmed, but those are attribute-level facts, so they don't turn the whole element yellow or green. Showing
them needs their own treatment (for example a marker at the confirmed datum), never a recoloured element.

## Blender 5.3, in its own environment

The rest of the repository runs Python 3.11 with bpy 5.0.1 (root `pyproject.toml`). bpy 5.3.0 wheels need
Python 3.13, so this product has its own uv project in [`env/`](env/pyproject.toml) with its own lock. Nothing
in it imports the root project. 5.3 adds what the film uses beyond 5.0.1: Geometry Nodes bundles and the XPBD
physics solver.

```bash
uv sync --project projects/highland/products/showcase/env --frozen
uv run --project projects/highland/products/showcase/env --frozen --no-sync \
  python projects/highland/products/showcase/proto.py          # proof frames -> build/highland/showcase/proof/
uv run bm run highland/showcase check                          # shot list check (bpy-free, root env)
```

**Grease Pencil needs EGL, even under Cycles.** Headless Blender composites Grease Pencil through the GPU module,
so without `libEGL.so.1` the process aborts. Software EGL works: `apt-get install libegl1 libegl-mesa0
libgl1-mesa-dri libgbm1`, then it renders with harmless `EGL_BAD_MATCH` warnings. RunPod's NVIDIA driver
provides EGL natively. Freestyle needs nothing extra.

## Proof frames (2026-11-25, CPU, 960 × 540, 16 samples)

- Ink: frames 20 and 60 of the draw-on, all six slab outlines from the model.
- Truth: the same camera in shaded, line, clay and provenance looks.

They are in `build/` (git-ignored). Illustrative, not a contract document.
