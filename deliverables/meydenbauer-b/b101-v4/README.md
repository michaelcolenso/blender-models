# 101 Meydenbauer — B-101 Blender Handoff v4

> **CORE / SMALL-ATTACHMENT EDITION**
> This ZIP contains the complete executable Blender handoff but omits the heavy contract PDFs. Use `Meydenbauer_B101_Reference_Pack_v4.zip` separately when document review is needed.


## Purpose

This package is the executable handoff for the current **Building B / Unit B-101 underground DW replacement and demolition model**. It is designed to move the work into an environment that has a real Blender executable so the `bpy` build can be executed, saved, reopened, visually reviewed, and rendered.

The current model is a **coordination / 4D construction-phasing model**, not a surveyed as-built. Concealed routing, inverts, legacy fitting type, and final cut elevations remain field-verification items where the contract documents do not establish them.

## Fastest path

### macOS / Linux

```bash
cd Meydenbauer_B101_Blender_Handoff_v4
./run_blender.sh
```

To also render the demolition checkpoints:

```bash
./run_blender.sh --render-keyframes
```

If Blender is not on `PATH`:

```bash
BLENDER_BIN="/Applications/Blender.app/Contents/MacOS/Blender" ./run_blender.sh --render-keyframes
```

### Windows

From PowerShell:

```powershell
cd Meydenbauer_B101_Blender_Handoff_v4
.\run_blender.ps1
```

Or:

```bat
run_blender.bat --render-keyframes
```

If needed:

```powershell
$env:BLENDER_BIN = "C:\Program Files\Blender Foundation\Blender 4.5\blender.exe"
.\run_blender.ps1 --render-keyframes
```

## What a successful run produces

`output/Meydenbauer_B101_Demolition_v4.blend`

`output/build_validation_report.json`

`output/saved_blend_verification.json`

When `--render-keyframes` is enabled, `renders/` should contain PNGs for frames:

- 001 — existing
- 038 — remove/reinstall access items
- 050 — finish strip-out
- 061 — wall/stack exposure
- 068 — slab sawcut
- 076 — slab lift + vapor-barrier exposure
- 083 — excavation + exposed cast iron
- 089 — cast iron removed / clean trench

The launchers run the model twice in effect: first they build/save it from a factory startup, then they reopen the saved `.blend` in a new Blender process and run persistence checks. This catches a class of failures that a single in-memory build does not.

## Primary build script

`scripts/build_meydenbauer_b101_v4.py`

It contains the three modular passes:

1. Collections, grid, structural shell, slab Boolean trench cutters.
2. Existing/new plumbing, fittings, trench backfill/rebar layers.
3. Interior partitions, finishes, fixtures, detailed B-101 demolition, `PHASE_CONTROLLER` drivers.

Run control is exposed near the top of the script as `RUN_PASSES` and `VALIDATE_AFTER_RUN`.

## B-101 demolition detail currently modeled

The current v4 build includes:

- calibrated B-101 under-slab replacement routing;
- protected retained prior ABS repair zone;
- fixture/casework remove-and-reinstall proxies;
- finish strip-out access zones;
- wall/carrier/stack exposure;
- slab sawcuts, removable slab chunks, excavation volumes, vapor-barrier exposure;
- existing cast-iron removal geometry;
- 10 junction fitting bodies with field-verify fitting classification where concealed;
- plan-derived bend objects;
- first-floor P-trap demolition objects / conditions;
- two wall-hung WC carrier/flange demolition assemblies;
- explicit vertical and horizontal cut/disconnect locations;
- temporary support indicators around vertical cuts;
- demolition subphases driven by `PHASE_CONTROLLER["Demolition_Subphase"]`.

## Important model controls

- Coordinate system: X north→south, Y east→west, Z vertical.
- Slab top: Z = 0.
- Building A–M dimension chain: 160'-5 1/2".
- New replacement 6-inch lateral stops at 18 inches outside the east foundation face before switching to existing/context piping.
- B-101 prior ABS kitchen/dining repair remains protected and is not intentionally included in slab demolition.
- Vertical model cut targets use a coordination rule (`max(36 in, 10 x pipe diameter)`) but final cut elevations remain field verify.

## Required review before accepting the `.blend`

Read `BLENDER_REVIEW_CHECKLIST.md` and `KNOWN_UNCERTAINTIES.md`.

Do **not** accept the model solely because the Python script completes. The actual Blender review must confirm Boolean results, visibility drivers, object intersections, fitting orientation, cut/support locations, and the no-demo prior-ABS zone.

## Folder map

- `scripts/` — build, build runner, persistence validator, non-Blender preflight.
- `data/` — calibrated route controls and demolition fitting schedule.
- `qa/` — plan crops and visual route/demolition/fitting overlays.
- `sources/` — contract/source PDFs and original modeling brief.
- `docs/` — prior calibration/audit/modeling notes.
- `output/` — generated `.blend` and JSON reports.
- `renders/` — optional verification renders.
- `logs/` — terminal/Blender logs from the launchers.

## Status at handoff

Static Python compilation and model-data checks have been completed in the source environment. **The v4 `bpy` model has not yet been executed in Blender in this environment because no Blender executable was available.** The purpose of this package is to close that verification gap deterministically.
