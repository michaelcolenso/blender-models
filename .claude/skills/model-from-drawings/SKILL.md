---
name: model-from-drawings
description: Turn construction drawings, a detail, or site photos into a verified, provenance-tracked Blender model in this repo (new site or new spec). Use when asked to model a building, detail, wall section, room, or repair condition from PDFs or photos.
---

# Model from drawings or photos

Follow `docs/METHOD.md` (rules) and `docs/RUNBOOK.md` (exact commands). This is the order and the gates.

## 0. Orient
```bash
uv run bm doctor          # need: bpy for builds; sources present for intake
uv run bm list --json     # does the site already exist? which specs?
```
If bpy is missing locally, you can still write and validate specs (`bm check`), and CI builds them.

## 1. Site
New jobsite: `uv run bm new <site> --type element|detail --name "<display name>"`, then fill
`projects/<site>/project.yaml` (address, building type, scope). Put source PDFs/photos in
`projects/<site>/sources/` (never committed) and inventory each one in `sources/manifest.json`
(file, sha256, sheet ids, revision/date, scale, photo ids).

## 2. Pick the model type
- **detail**: one section (rake, eave, balcony edge, window head) → start from `templates/project/specs/detail.yaml`;
  example `projects/qp-cottage-a/specs/qp-rake-ah700-12.yaml`.
- **house**: plan-extracted shell + takeoff → RUNBOOK steps 2–11; example `projects/qp-cottage-a/specs/qp-cottage-a.yaml`.
- **element**: boxes per member (framing bay, deck) → `templates/project/specs/element.yaml`.
- **room**: photo-only interior → `projects/room-living-kitchen/specs/room-living-kitchen.yaml`.
- Existing condition and proposed repair → two specs (`<x>-existing.yaml`, `<x>-proposed.yaml`).

## 3. Takeoff into the spec (gates)
- Calibrate each sheet from its own dimension strings (`uv run bm calibrate scale …`); never trust the title block.
- Every element: `confirmed` + `source` (dimension on a document), `provisional` + `source` + how measured and
  tolerance, or `assumed` + `basis`. Actual lumber sizes. Never scale an NTS detail.
- Add document-driven `checks` (counts, overall extents, gaps, elevations) each with a `source`.
- Conflicting sources: model the governing one, write the conflict into `flags:`.

## 4. Build and verify
```bash
uv run bm check --no-tests                     # provenance errors without bpy
uv run bm build <site>/<spec> --no-render       # checks only, seconds
uv run bm build <site>/<spec>                   # + review renders in build/<site>/<spec>/
```
Read `build/<site>/<spec>/report.md`, then **look at** the review PNGs (plan/front/side/iso, provenance
colors). Where an elevation exists: `uv run bm overlay …` (RUNBOOK step 10) and report the edge agreement.
No local bpy: push a branch and read the `build-models` run instead.

## 5. Report back
State: checks passed (n/n), renders looked at (which), overlays (agreement %), every assumed element, and
what is not modeled. Never call provisional or assumed geometry documented.
