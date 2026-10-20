# Highland / uploaded drawing reconciliation 04

This bounded revision uses the three uploaded PDFs (19 sheets) to locate thirteen previously omitted candidates provisionally, reject one false R5 repeat, and record two footprint conflicts. The model has 189 opening records. North R2-R5 rows are reconstructed from six actual elevation openings per floor. South R1-R4 columns 03/04 move to successive returns so restored column 02 does not overlap them; unsupported column-03 balcony recesses/guards are removed.

All inherited plan polygons, floor/grid controls, roof and terrace geometry are preserved. Of 969 original architectural meshes, 863 remain identical; the revised file contains 998. Both native scenes, packed assets and the 432-frame dusk camera are retained. The prior revision 03 movie remains a separate older delivery; it is not a revision 04 render.

`decisions.json` records source picks and decisions. `prepare.py` produces `reconciled.spec.json`, the build specification. The native file is patched from revision 03 by reproducible code; it is never edited by hand. The builder imports only four pure mesh functions from the original exterior generator using its AST. It does not execute that script's scene setup.

Run from the repository root or the ZIP's `reproduction/` directory:

```bash
python projects/highland-drawings/prepare.py
python projects/highland-drawings/compare.py
HIGHLAND_BLENDER_PY=/workspace/.venvs/blender-models/bin/python
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=3 "$HIGHLAND_BLENDER_PY" projects/highland-drawings/build.py
"$HIGHLAND_BLENDER_PY" projects/highland-drawings/validate.py
"$HIGHLAND_BLENDER_PY" projects/highland-drawings/render.py --review
# Inspect the source picks, overlay and four native provenance views.
"$HIGHLAND_BLENDER_PY" projects/highland-drawings/render.py
python projects/highland-drawings/report.py
# Inspect the daylight image and every report page, then record exact hashes.
python projects/highland-drawings/package.py
```

Use a Python 3.11 environment with bpy 5.0.1 for native build/render/validation. Preparation/reporting additionally need NumPy, Pillow, PyMuPDF and ReportLab; DejaVu Sans must be installed. All dimensions are inches in the spec and meters in native meshes. Generated source-review details are 200 dpi; additional 300 dpi conflict crops were inspected during intake.

The comparison overlay exposes a maximum horizontal center discrepancy of 42.443 pixels on the inherited 1815-pixel-wide overview raster. That is a diagnostic residual, not source accuracy. It includes unresolved model/elevation registration and simplified-wall effects. Accepted candidates establish visible presence and provisional plan placement, not verified jamb dimensions. Sills, heads, complete sections and exterior guards remain assumed. The window schedule and A4/A5 profile details are absent.

The next architectural work is to reconcile the P1 enclosure against A2.02 and the southeast R5 return against A2.07/A3.01, then audit R1 north doors and the remaining north projection differences. Current drawings permit those follow-up investigations; no new upload is required to begin them. Keep their wider shell changes separate from this reviewable opening patch.
