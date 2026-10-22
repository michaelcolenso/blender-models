# Highland / drawing reconciliation 06

The remaining R5 enclosure/openings, terrace/coping/guard arrangement and whole-building day/dusk review were completed in that order. The 14-vertex enclosure distinguishes rooms from west terraces; 28 non-north R5 openings were rechecked. Five walking terraces and the gravel planter are separate, with five exposed-edge guard paths and three band paths. The south MO/MJ pair has a shared interface; MJ corrects the prior MU transcription. P1 remains as reconciled in revision 05. The inventory remains 192 openings.

North stair/MU and R1 entries are deferred. The 42.443-pixel north diagnostic remains explicit, as do the R5 non-north plan/elevation differences and preserved north tie-in offsets. Source XY is provisional. Complete window/cornice/coping/guard profiles, drainage, waterproofing, sill/head dimensions and context remain assumed or undeveloped. This is not a verified as-built or construction model. See [HANDOFF.md](HANDOFF.md) for exact residuals and remaining assumptions.

`prepare.py` produces the single geometry source `reconciled.spec.json`. The builder patches revision 03 reproducibly; geometry is not hand-edited in Blender. `r5-completion.json` and `terrace-review.json` supersede historical revision 05 R5 limits in `shell-reconciliation.json`. Source decisions are recorded separately for openings, P1/southeast patch, full R5, terraces and presentation. The three PDFs (19 sheets) remain under `references/`; every plan is registered independently to its dimensioned grids.

Run from the repository root, or the archive's `reproduction/` directory:

```bash
python projects/highland-drawings/prepare.py
python projects/highland-drawings/compare.py
HIGHLAND_BLENDER_PY=/workspace/.venvs/blender-models/bin/python
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=3 "$HIGHLAND_BLENDER_PY" projects/highland-drawings/build.py
"$HIGHLAND_BLENDER_PY" projects/highland-drawings/validate.py
"$HIGHLAND_BLENDER_PY" projects/highland-drawings/render.py --review --views north,south,east,west,plan,iso,r5-return,r5-plan,r5-southwest,terrace-plan
# Inspect source evidence and all ten native provenance views before presentation.
"$HIGHLAND_BLENDER_PY" projects/highland-drawings/render.py
"$HIGHLAND_BLENDER_PY" projects/highland-drawings/render.py --dusk
"$HIGHLAND_BLENDER_PY" projects/highland-drawings/render.py --dusk-review
python projects/highland-drawings/check_renders.py
python projects/highland-drawings/report.py
# Inspect both stills, dusk endpoints and every report page; record their hashes.
python projects/highland-drawings/package.py
```

Preparation supports `--stage r5`, `--stage terraces` and default `--stage presentation`. Intermediate proofs are retained; the final independent validator protects 99 stage-1 enclosure/roof meshes, 815 revision 05 meshes and 97 north meshes. Native rendering/validation use Python 3.11 with bpy 5.0.1. Preparation/reporting also need NumPy, Pillow, PyMuPDF, ReportLab and DejaVu Sans. Specification dimensions are inches; mesh coordinates are meters. No new geometry dependency was added.

The integrated checks cover real saved meshes, protected controls, frames in both axes and wall-normal placement, overlapping voids, polygon simplicity, actual slab outlines/areas/levels, split roof coverage, coping tops/joints, terrace-room/guard intersections, dressing transforms, packed images, exported architecture and all 432 saved dusk camera frames. Eleven render-workflow tests pass without skips; the catalog resolves five shots. Source measurements remain provisional regardless of floating-point readback agreement.

The delivery contains ten current provenance views, fresh native daylight/dusk stills and two dusk camera endpoints. Revision 05 P1 views are retained as historical evidence; stage-specific images are in named subfolders. Exact inspected hashes are in `visual-review.json`. The editable archive includes the original PDFs, base native and reproduction inputs. Revision 03's film remains separate; this refresh does not include a new movie.
