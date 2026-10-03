# Blender Project — Instructions

Purpose: build dimensionally accurate, realistic 3D models of Michael's restoration and defect-repair projects (occupied multifamily) from construction drawings, details and specs, using Blender driven by Python. Site photos may supply `provisional` dimensions inside a drawing-based model; photo-only geometry is out of scope for now (`field-parapet-*.yaml` are illustrative sketches from one photo, almost entirely assumed). Accuracy first, realism second. A model is finished only when every dimension traces to a source or is labeled as assumed, the automated checks pass, and the renders have been looked at.

Operator procedure with exact commands: **RUNBOOK.md**.

## Pipeline (always in this order)

1. **Intake.** Inventory every source: sheet number, detail number, revision/date, scale, photo IDs. Read drawings at full resolution (rasterize PDFs with `pdftoppm -r 200+`; crop into details). Note scale bars and "NTS" details.
2. **Takeoff.** Extract every dimension, member size, spacing, elevation, and count into the model spec. Use actual lumber sizes (2x10 = 1½ × 9¼), not nominal. Never scale an NTS detail. Never infer a dimension from a partial drawing and call it documented.
3. **Model spec** (`specs/<project>-<area>.yaml`). The spec is the single source of truth; geometry is never hand-edited in Blender without the spec changing too. Every element carries:
   - `status: confirmed` — dimension shown on a document (`source` required)
   - `status: provisional` — derived: scaled from a drawing with a scale bar, or measured from a photo against a known reference (`source` required; note the reference and expected tolerance)
   - `status: assumed` — not in any document (`basis` required, e.g. "code-minimum", "typical", "massing only")
   - Document-driven `checks`: counts, overall extents, clear gaps, spacing, elevations — each with its `source`.
   - `basis_of_record` (required; the build fails without it): `documents` (what the model is built from), `kind` (`design_intent | as_built | field_photo | field_survey | mixed | unknown`), `field_verified` (`verified | partial | not_verified | unknown`), optional `note`. A model reflects the record, not the building.
   - `assumptions:` (optional): assumed modeling parameters that aren't tied to one element (a wall thickness, a massing thickness, a color scheme), each with `id` and `basis`. They print in the report's Assumed list.
   - `conflicts:` (when sources disagree): `topic`, `modeled_per` (the governing source id), `note`, optional `sources`.
   - `review:` (added only after the visual review is actually done): `date`, `by`, `views`, optional `overlays` (`view`, `edge_pct`, `verdict` = `pass | fail | n/a`, `note`) and `note`.
4. **Build.** `python tools/build.py specs/<name>.yaml [--realistic]` (bpy, headless). One collection per trade; trades stay separate. Inches in the spec; Blender stores meters, displays imperial.
5. **Verify.** The builder fails (exit 1) on: missing source/basis, count or extent mismatch, gap mismatch, or a blank render. Then look at the review renders myself — plan, front, side, iso — colored by provenance (green confirmed, yellow provisional, orange assumed). Where a drawing elevation exists, compare the ortho render against it at the same scale. "Checks passed" and "looked right" are both required; report which were done. Record the visual review in the spec's `review:` block; until then `report.md` says **NOT RECORDED**. Re-record it after any spec change that affects geometry.
6. **Realism pass** (only after geometry is verified). PBR materials by real product where known; realistic lighting via Cycles. Realism never changes geometry.
7. **Quantities.** Every house build writes `<name>_takeoff.xlsx` (tools/qto.py): openings schedule, siding + gable panel net of openings by elevation, casing and corner-board LF, roof area by pitch, squares (waste is a yellow input), ridge/hip/valley/eave/rake LF, and an Elements sheet of stable IDs for trackers. Measured values are blue inputs with method + status; everything derived is a live formula. Reconcile against any documented quantity (Cottage A: plan roof area 3,935.7 vs 3,935 sf on AH202).
8. **Deliver.** `.blend` (editable), `.glb` (phone/web viewing, carries element metadata), review renders, `report.md`. List every assumed element in the handoff.

## Plan-set method (proven on QP Cottage A, 2026-09-27)

- **Calibrate every sheet from its own dimension strings** before measuring anything: find the tick marks of a long dimension and compute pt/ft (AH201: 39'-0" ticks 702 pt apart = 18.0 pt/ft = true 1/4"). Never trust the title-block scale alone.
- **Rasterize at an exact scale** (2 px/in plans, 1–2 px/in elevations). Walls drawn as hollow outlines are found as thin enclosed white cores (half-width 2.5–7.5 px); window glazing splits the band into strips under 2.3 px half-width.
- **Every extracted opening must appear on an elevation** or it is rejected (tubs, showers, garage-door lines and revision clouds all produce false openings). Record rejected candidates in the spec.
- **Revision clouds and tags break linework** — look for missing wall where a cloud crosses, trace it manually, and add it as an `extra_walls` entry with its reason.
- **Mirror-image units:** extract the cleaner half and mirror, but first measure the match (Cottage A: 94% of walls within 1½"). Working default, an assumption set 2026-10-02 from one project (n = 1), not a code or contract requirement: below 90% of walls matching within 1½", stop and escalate; otherwise list the non-matching walls in the spec header as documented differences.
- **Roofs:** union of convex hip/gable pieces taken from the eave outline on the roof plan; verify predicted ridge/hip positions against the drawn ones and ridge heights against elevations.
- **Walls are built boolean-free** (rectangle decomposition, openings cut by box splitting). Roof unions use Blender's **Manifold** boolean solver — the Exact solver fails on the coplanar faces that roofs inevitably have.
- **Overlay check:** `tools/overlay.py` renders the model orthographically at the drawing's scale and overlays it on the elevation; report the edge-agreement % and look at the image.

## Model types

- **detail** — one construction section (rake, eave, balcony edge, window head) as callout-sized components swept along a short path; 1/16" intent. `tools/detail.py`.
- **house** — plan-extracted shell (walls, openings, roof) + quantity takeoff. `tools/house.py`, `tools/qto.py`.
- **element / building** — not built yet: parametric components (balcony, stair) and multi-level buildings with repeated units.
All types share: provenance on every element, failing checks, CI rebuild.

## Accuracy rules

- Never present an assumed or provisional element as documented. Review renders always show provenance colors; realistic renders shared outside the team must carry a note if any assumed elements are visible.
- **Record vs. building.** Every spec states `basis_of_record`. A design-intent set (CD set, permit set) is not an as-built record, and a model of it is not evidence of what is behind a wall or how something was installed. Until `field_verified: verified`, say so wherever the model is used. For defect and existing-conditions work, treat design-intent geometry as context, not as the existing condition.
- Photos: state the reference object used for scale (brick course, CMU, door, siding exposure, known member size), the camera angle limits, and the resulting tolerance. Photo-only geometry is at best `provisional`.
- Conflicts between sources (drawing vs. photo vs. spec): model per the governing document, flag the conflict in the report — don't average or silently pick.
- Existing-conditions models (defect repair) and proposed-repair models are separate scenes or separate specs. Don't merge them.
- Models are illustrative/coordination tools, not contract documents. Any render used in a scope, PCO, or resident notice gets that label. Every PNG from `tools/build.py` carries it automatically (a strip under the image: illustrative label, record kind, field-verification status, and the provenance legend or the count of assumed elements). Animations, USDZ and SketchUp output do not carry it yet: label them by hand when shared.

## Occupied-building use cases

Resident notices (what's happening at their unit), access and sequencing diagrams, protection/staging/egress layouts, and PCO backup showing concealed conditions. For these, include the relevant occupied-building elements (egress paths, protection, staging area, work zone) as their own collection, marked by source like everything else.

## Presentation outputs

Sequence animations (MP4, animated USDZ) and the SketchUp file are presentations of a recommended order or of a model, not additional sources of geometry. Commands and limits are in RUNBOOK.md. Label them as illustrative when shared; `tools/build.py` does not stamp them.

## Where these docs live

The repo files `INSTRUCTIONS.md` and `RUNBOOK.md` are canonical; `README.md` only points to them. The Claude project holds copies (`claude/INSTRUCTIONS.md`, `claude/RUNBOOK.md`) for sessions. Sync them from the repo only after a change has merged to main; each time, add a stamp line under the title giving the first 12 characters of the repo file's SHA-256 and the sync date. Copies synced before 2026-10-02 have no stamp. To check for drift: `sha256sum INSTRUCTIONS.md | cut -c1-12` should equal the stamp. If it doesn't, the repo wins; re-sync the copy.

## Environment facts (verified 2026-09-27)

- `pip install bpy==5.0.1` works on Python 3.11 in Claude's Linux workspace; build + checks for a small spec run in seconds.
- Headless has no GPU: **Workbench and EEVEE render blank frames** — use Cycles on CPU only. Cameras need explicit rotation (track-to constraints are not evaluated before headless renders).
- Exports confirmed working: .blend, .glb, .obj, .stl, .fbx, .usdz. SVG import add-on present. IFC (Bonsai) not installed — unverified.
- Cycles realistic render: ~2 min for 4 review views + 1 realistic view at 1600×1200 on 2 CPU cores. EEVEE took 45 s for a trivial scene and still returned blank.

## CI

GitHub Actions (`.github/workflows/build-models.yaml`) rebuilds on pull requests and on pushes to main when `specs/**` or `tools/**` change, fails the run if any check fails, writes each report to the job summary, and uploads `build/` as an artifact. A PR that touches `tools/` rebuilds every spec; otherwise only the changed specs. A push to a non-main branch does not run CI, so open a PR to get a result. Docs-only changes don't trigger it. Claude does the takeoff and spec edits; CI makes the geometry reproducible and blocks unsourced or inconsistent changes.

Claude's token can't write workflow files: edit `.github/workflows/*` in the GitHub web UI.

**Open defect (found 2026-10-02):** both `paths:` lists in the workflow name `.github/workflows/build-models.yml`, but the file is `.yaml`, so edits to the workflow itself never trigger a run. Fix in the web UI: change that string to `.github/workflows/build-models.yaml` in both lists (`pull_request` and `push`).

## Working style

Ask once, batched, only for what can't be read from the documents (e.g. a missing detail, which revision governs). Otherwise take the next step and mark assumptions. Don't claim a model is accurate beyond what its sources support.
