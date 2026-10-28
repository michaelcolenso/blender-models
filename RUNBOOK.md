# Runbook: Drawing set → verified Blender model + quantity takeoff

**Owner:** Michael Colenso | **Frequency:** As needed (one run per building / drawing set)
**Last updated:** 2026-09-27 | **Last run:** 2026-09-27 (QP Cottage Duplex A, `specs/qp-cottage-a.yaml`)
**Scope today:** vector-PDF plan sets (CAD-plotted). Single-story, orthogonal walls, hip/gable roofs.
**Not yet supported:** scanned/raster drawings, photos or field measurements as geometry sources,
multi-story, curved or skewed walls. Don't force those through this pipeline — flag them.

## Purpose

Turn a drawing set into (1) a Blender model whose geometry is checked against the drawings, (2) a
quantity takeoff workbook, and (3) review renders — every element tagged with the sheet it came
from and whether it is **documented**, **provisional** (measured from a drawing at a verified
scale) or **assumed**. The model is a coordination/estimating tool, not a contract document.

Time for a first building like Cottage A: ~2–3 h of operator time; builds take ~2 min
(review renders) or ~6 min (with realistic renders) on 2 CPU cores.

## Prerequisites

- [ ] Access to `github.com/michaelcolenso/blender-models` (private).
- [ ] Python **3.11 exactly** (bpy 5.0.x wheels are cp311 only). Linux or macOS. No GPU needed.
- [ ] The drawing set as a **vector** PDF. Test: `pdftotext -f N -l N set.pdf - | head` returns dimension
      text such as `39-0`. If it returns nothing, the set is scanned — stop (see Escalation).
- [ ] Sheets needed: dimensioned floor plan, roof plan, all exterior elevations, window/door schedule,
      and the sheet that states plate/truss-bearing height (elevation or framing plan).
- [ ] `pdftoppm` (poppler) for previews.

## Procedure

Paths below are from the repo root. `PDF=sources/<project>.pdf` throughout.

### Step 1 — Set up

```bash
git clone https://github.com/michaelcolenso/blender-models && cd blender-models
uv sync --group pdf --group vision     # downloads Python 3.11 + the locked deps into .venv
mkdir -p sources takeoff && cp /path/to/set.pdf sources/<project>.pdf   # sources/ is git-ignored
```
**Expected:** `uv run python -c "import bpy; print(bpy.app.version_string)"` prints `5.0.1`.
**If it fails:** on Linux install `libx11-6 libxrender1 libxfixes3 libxi6 libxext6 libxkbcommon0 libsm6 libice6 libgl1`.

### Step 2 — Inventory the set

```bash
uv run bm calibrate sheets $PDF
pdftoppm -r 72 -f <page> -l <page> -png $PDF preview    # at 72 dpi, 1 pixel = 1 PDF point
```
**Expected:** each page's own sheet number (title block) and drawing titles; find the floor plan, roof plan,
elevations and schedules. A page with `-` and no titles has no text layer (raster) — those sheets can't be
extracted. The cover/index page may show a referenced sheet number instead of its own.
Record each sheet in the spec's `sources:` list (sheet number, title, revision/date).
**If it fails:** no text on the plan/roof/elevation pages → scanned set → stop (Escalation).

### Step 3 — Calibrate the plan sheet from its own dimensions

```bash
uv run bm calibrate scale $PDF --page <plan page> --text "<overall dim, e.g. 78-0>" --feet 78
uv run bm calibrate scale $PDF --page <plan page> --text "<another dim, e.g. 39-0>" --feet 39
```
**Expected:** both give the same pt/ft (Cottage A: 18.000 = ¼"). Must agree within 0.1%.
**If it fails:** "no bracketing ticks" → the string uses dots/arrows, try another string. Disagreement →
one string is not-to-scale or mislabeled; use strings that agree and note it.

### Step 4 — Find the extraction window and origin

1. Open `preview-*.png` from Step 2 (pixels = points). Read the plan's bounding box in points → `--clip x0,y0,x1,y1`
   (include the building, exclude title block and schedules).
2. Centre (party wall / symmetry line) from the overall-width ticks printed in Step 3:
   ```bash
   python src/bmodels/calibrate.py plan $PDF --page <p> --clip <clip> --pt-per-ft <pt/ft> --left-tick-pt <L> --right-tick-pt <R>
   ```
3. `--rear-px` = `(rear wall face y in points − clip y0) × 24 / pt_per_ft`. Pick the rear face of the section
   you want as Y = 0 (Cottage A: 156).

### Step 5 — Extract walls and openings

```bash
uv run bm extract $PDF --page <p> --clip <clip> --pt-per-ft <pt/ft> \
  --center-px <cx> --rear-px <ry> --half right --out takeoff/<project>.json
```
**Expected:** `walls rings=… windows=… doors=…` and `takeoff/<project>_review.png`
(walls black, window candidates orange `W#`, door candidates blue `D#`, labelled with X,Y in inches).
Use `--half right` only for mirror-image units (see Step 6); otherwise `--half all` is not implemented yet — escalate.
**If it fails:** walls missing in the review image → see Troubleshooting (clouds, tags, dimension clutter).

### Step 6 — Review the extraction (do not skip)

- [ ] **Mirror check** (duplexes): confirm the two units are true mirrors before using `--half`. Look at the plan;
      if in doubt, escalate — Cottage A measured 94% of walls within 1½".
- [ ] **Every opening candidate must appear on an elevation.** For each W#/D#, find it on the matching
      elevation; accept (copy to spec `openings:`) or reject (list in a spec comment with reason).
      Typical false candidates: tubs/showers, garage-door lines, revision clouds, the party-wall FEC cabinet.
- [ ] **Holes:** look for walls missing under revision clouds, tags or text. Add each as `extra_walls:` with
      a comment saying why (see `specs/qp-cottage-a.yaml`).

### Step 7 — Heights and roof

1. Elevation scale: `calibrate.py scale` on an elevation string or use the sheet's stated scale (Cottage A AH500: 9 pt/ft).
2. **Plate height** from the documented elevations (FF and truss-bearing lines) → `plate_height_in` (documented).
3. **Window/door heads and sills**: measure on the elevation (see `src/bmodels/overlay.py` raster at 1 px/in) → provisional.
   Nominal sizes come from the window schedule → put the mark (`mark: A`) on each opening.
4. **Roof eave outline:**
   ```bash
   python src/bmodels/calibrate.py outline $PDF --page <roof plan page> --clip <roof clip> --pt-per-ft <pt/ft> \
     --origin-x-pt <centre x pt> --origin-y-pt <rear eave y pt>
   ```
   Take the closed loop of segments (ignore stray section-cut lines drawn at the same weight). Convert Y to the
   plan frame (Cottage A: roof Y − 2.0 ft, because the rear eave sits 2'-0" behind the rear wall).
5. **Roof pieces:** decompose the outline into rectangles: one `hip` per main mass, `gable` for each gable with
   `ridge: x|y` and its gable end at the outline edge. Pitches from the roof plan (documented). Then confirm the
   model's predicted ridge/hip positions land on the drawn ridge/hip lines (Cottage A: within 0.4').
6. Eave height (`eave_surface_z_in`) and soffit from the elevation → provisional.

### Step 8 — Write the spec and checks

Copy `specs/qp-cottage-a.yaml` → `specs/<project>.yaml` and fill it in. Required checks:
- wall extents vs overall dimension strings (documented),
- plate height (documented),
- eave outline extents (roof plan),
- ridge heights vs elevation (provisional, tol 2"),
- `qto_checks.plan_area_sf` if the set states a roof area anywhere (venting calcs often do).

### Step 9 — Build locally

```bash
uv run bm build specs/<project>.yaml              # ~2 min, review renders
uv run bm build specs/<project>.yaml --realistic  # ~6 min, adds hero renders
```
**Expected:** `**PASS** — n/n checks`, exit code 0, and in `build/<project>/`: `.blend`, `.glb`,
`_review_{iso,plan,front,side}.png`, `_takeoff.xlsx`, `report.md`.
**If it fails:** the report names the failing check — fix the spec, never loosen a tolerance to pass.

### Step 10 — Overlay the model on the elevations

```bash
uv run bm calibrate elev $PDF --page <elev page> --clip <elevation clip> --pt-per-ft <pt/ft> \
  --plate-in <plate height> --half-width-in <half of wall-face-to-wall-face width>
uv run bm overlay build/<project>/<project>.blend --pdf $PDF --page <elev page> --clip <clip> \
  --pt-per-ft <pt/ft> --view front|rear|right --floor-row <row> --center-col <col> --out build/<project>/overlay_<view>.png
```
**Expected:** ≥ 80% edge agreement (Cottage A: front 82%, rear 87%) **and** a visual check that windows, doors,
eaves, ridges and gables sit on the drawing's lines. The % alone is not proof.
**If it fails:** misaligned horizontally → wrong `--center-col` (re-run `calibrate.py elev`); an element off →
fix that element in the spec; `side` views need the building's Y-centre (not automated yet).

### Step 11 — Review the takeoff

Open `build/<project>/<project>_takeoff.xlsx`:
- [ ] Opening counts per elevation match the drawings.
- [ ] Any documented quantity reconciles (roof area, window count).
- [ ] Set the **roof waste %** (yellow cell) to your standard.
- [ ] Sanity-check gable panel sf per elevation against a hand estimate (a known past bug counted an interior plane).

### Step 12 — Commit and let CI rebuild

```bash
git add specs/<project>.yaml takeoff/<project>.json && git commit -m "Model <project>" && git push
```
**Expected:** Actions run "Build & verify models" goes green; the job summary shows each `report.md`;
artifact `models-<sha>` contains the build folder (kept 30 days).
**If it fails:** open the run → "Build, verify, render" step log → the failing check is printed.

## Detail mode (sections: rake, eave, balcony edge, window head …)

Use when the source is a **section detail**, not a plan. Spec type `detail` (example: `specs/qp-rake-ah700-12.yaml`).

1. **Pick a true section at a stated scale.** Reject NTS / perspective sketches for geometry (AT401/4 rake is NTS — used only for sequence).
2. **Verify the detail scale** from a dimension string inside the detail:
   `uv run bm calibrate scale $PDF --page 8 --text "1-6" --feet 1.5` (AH700/12: 106.5 pt/ft vs 108 nominal — sheet plots 1.4% small; always use the measured value).
3. **Section frame:** X horizontal from a named face (e.g. fascia outer face = 0), Z plumb from a named plane (e.g. underside of roof sheathing = 0). Write that in the spec header.
4. **One component per callout**, sized by the callout's **actual** dimensions (5/4x10 = 1 × 9¼; 1x6 = ¾ × 5½), positioned from the drawing. Thicknesses stated elsewhere (wall types, structural notes) cite that sheet. Anything drawn but not called out = provisional with a `basis`; anything not drawn = assumed.
5. **Checks:** every dimension string in the detail as a `between:` check (hard); measured drawn sizes as `drawn:` checks (warn only — they test the *drawing* against its callouts; a ⚠️ means the drawing and the callout disagree, e.g. fascia drawn 10.1" deep vs 9¼" called out).
6. `path:` length and `pitch:` (rake follows the roof slope). `peel:` / `cutaway_step_in:` are presentation only — the near end stays a true section.
7. Build with `--realistic` for the labeled cutaway; then
   `uv run bm detail-overlay build/<n>/<n>.blend --pdf $PDF --page <p> --clip <clip> --pt-per-ft <measured> --origin-pt <x,y of X=0,Z=0> --out build/<n>/overlay_section.png`
   Judge by eye: the % counts model outline beyond the detail's break lines as misses, so it understates fit.

## SketchUp output (on request, from a Claude chat session)

The Trimble SketchUp connector is available to Claude in chat, **not in CI**, and its plan has a save quota
(30 saves; check `saves_remaining` in the save result). Use it for the human-facing file, not every build.
1. `uv run bm skp specs/<x>-existing.yaml specs/<x>-proposed.yaml` → code for `build_model` (clean: true).
2. Add scenes "1 Existing" / "2 Proposed" (hide the other layer), style, model camera; `save_model`.
3. Download the .skp from the returned URL (follow the redirect) and deliver it. The file's thumbnail shows all
   layers; the scene tabs switch Existing/Proposed.
Limits: solid colors only (no textures), no booleans (openings by construction), 30-min idle session timeout.

## Sequence animation (existing → proposed, captioned)

Add a `sequence:` block to the proposed spec (steps with caption / remove / install / seconds; `weave` for
shingles + step flashing course by course; `extras` / `initial_show` / `initial_hide` for partial tear-off).
`uv run bm animate-sequence specs/<x>-existing.yaml specs/<x>-proposed.yaml --out build/<x>-sequence/<x>`
→ `<x>.mp4` (captioned, any phone) + `<x>.usdz` (same timeline as transform animation, AR-seated).
Test first with `--test-frames 10,150,236`. Full render ≈ 6 s/frame on 2 CPU cores (Cycles; Workbench/EEVEE
render blank headless). The sequence is presentation of a recommended order — label it that way when shared.

**Whole buildings (type: house):** add a `sequence:` block to the house spec — steps with `caption`,
`objects` (glob patterns on built object names: `slab_*`, `walls`, `attic_*`, `roof`, `soffit`, opening ids such as
`rear_A*`, `garage_*`), `motion` (`drop` / `rise` / `grow`), `seconds`, and `stagger: opening` to install one
opening (glass, frame, mullions, casing) at a time. Build the model first, then
`uv run bm animate-house specs/<name>.yaml --out build/<name>-sequence/<name>-sequence`.
The script stops if a step matches nothing and warns about objects in no step. The camera does one elevated
orbit starting front-left. Cottage A: 271 frames, ≈9 s/frame at 960×540 with 8 samples ≈ 40 min, so run it
with `nohup … &` and poll the log. Both animators share `src/bmodels/anim_common.py` for captions, which shrink to fit
the frame width and keep the step counter in sync with the caption on screen.

## Verification (definition of done)

- [ ] Local build and CI both PASS.
- [ ] Overlays reviewed for every elevation you have (front and rear at minimum).
- [ ] Every opening in the spec appears on an elevation; rejected candidates are listed.
- [ ] Every `assumed` item has a `basis`; the report's "Assumed" list read and accepted.
- [ ] Takeoff reconciled to any documented quantity; waste % set.
- [ ] Handoff states what is not modeled (pergolas, bay roofs, gutters, interior, etc.).

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Render is a flat grey image; "render not blank" check fails | Workbench/EEVEE need a GPU | Builder uses Cycles CPU; don't change the engine |
| All cameras look straight down | Track-to constraints not evaluated headless | Cameras use explicit rotation; keep it |
| Roof boolean produces geometry below grade / volume shrinks | Exact solver on coplanar faces | `house.SOLVER = "MANIFOLD"` |
| Objects render white though materials are set | Boolean left empty material slot 0 | Use `set_mat()`, never `materials.append()` |
| Wall missing where a revision cloud or tag crosses | Cloud arcs split the wall band | Add `extra_walls` entry traced from the review PNG |
| Whole wall run missing on one unit | Dimension/extension lines inside the wall band | Extract the cleaner half and mirror, or add `extra_walls` |
| False window in a bathroom / garage | Tub, shower or garage-door line | Reject: not on any elevation |
| Gable "hipped" (shingled triangle at gable end) | Inner roof solid closed the gable end | Inner gable pieces extend 24" past ends (already in `roof_piece`) |
| Overlay shifted sideways | Wrong centre column | `calibrate.py elev`; don't use mirror-symmetry guesses |
| Gable panel sf far too high | Interior plane counted | Party-wall plane is excluded in `qto.gable_areas`; check for other interior planes |
| CI can't push workflow changes from Claude | Token lacks `workflow` scope | Edit `.github/workflows/*` in the GitHub web UI |
| CI doesn't trigger on workflow-only edits | Path filter says `.yml`, file is `.yaml` | Fix the filter in the web UI |

## Rollback

Specs and takeoffs are plain files: `git revert <sha>` and push. Build outputs are not committed; previous
CI artifacts remain downloadable for 30 days. Nothing in this pipeline writes outside the repo.

## Escalation

| Situation | Contact | Method |
|---|---|---|
| Scanned/raster set, photos-only, multi-story, skewed walls | Michael (owner) | Needs a new extraction method — don't hand-build around it |
| Units not true mirrors | Michael | Decide: extract both halves (needs `--half all`) or accept documented differences |
| Documented dimensions disagree with each other | Michael → architect of record | Model per governing sheet, record the conflict in the spec |
| Check fails and the drawing supports the model | Michael | Update the check's source/tolerance only with a written reason |

## History

| Date | Run by | Notes |
|---|---|---|
| 2026-09-30 | Claude | Cottage A build-up animation (src/bmodels/animate_house.py): 6 steps, 22.6 s, MP4 + animated USDZ. Walls mesh includes interior partitions traced from AH201 — the caption says so. |
| 2026-09-27 | Claude | Rake detail AH700/12 (detail mode): 16 components, 2 documented dims pass, drawing-vs-callout warnings on fascia depth and wall sheathing. |
| 2026-09-27 | Claude (with Michael) | QP Cottage Duplex A (2017 CD set, AH201/AH202/AH500/SH202). Right unit mirrored; 5 false openings rejected; 3 walls under a revision cloud traced manually; roof plan area 3,935.7 vs 3,935 sf documented; overlays 82% / 87%. |
