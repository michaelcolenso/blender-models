# Highland / drawing reconciliation 05

This continuation traces the A2.02 P1 enclosure, audits all fourteen modeled P1 openings, and reconciles the southeast R5 return with its adjacent openings, slab, south roof plate and coping. OPEN-01 and OPEN-14 are provisionally placed without jamb clipping. The model has 192 openings: fifteen of the original sixteen candidates provisionally placed, one false R5 repeat rejected, and an additional P1 service door.

North R2-R5 meshes remain identical to revision 04. Their diagnostic center differences remain explicit, with a maximum of 42.443 pixels on the inherited overview raster. P1 ramp/structural details, R1 north entries, other R5 local steps, southeast tie-in residuals and the MO/MU split remain provisional or unaudited. See [HANDOFF.md](HANDOFF.md) for exact remaining work. This is not a verified as-built or construction model.

`decisions.json` preserves the revision 04 opening picks. `shell-decisions.json` adds the source picks for this continuation. `prepare.py` produces the single geometry specification, `reconciled.spec.json`, and exact source evidence. The builder patches revision 03 reproducibly; no native geometry is hand-edited. The cumulative ledger describes changes from revision 03, while `shell-reconciliation.json` isolates this continuation.

The source PDFs (19 sheets) remain under `references/`. Each affected plan is calibrated independently to the dimensioned grids. XY positions are provisional raster measurements. Sill/head sizes, complete frame/wall/coping sections, guards and site context remain assumed. Local source/model residuals are reported, not hidden by changing a global scale.

Run from the repository root, or from the archive's `reproduction/` directory:

```bash
python projects/highland-drawings/prepare.py
python projects/highland-drawings/compare.py
HIGHLAND_BLENDER_PY=/workspace/.venvs/blender-models/bin/python
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=3 "$HIGHLAND_BLENDER_PY" projects/highland-drawings/build.py
"$HIGHLAND_BLENDER_PY" projects/highland-drawings/validate.py
"$HIGHLAND_BLENDER_PY" projects/highland-drawings/render.py --review
# Inspect the source picks, overlays and seven native provenance views.
"$HIGHLAND_BLENDER_PY" projects/highland-drawings/render.py
python projects/highland-drawings/report.py
# Inspect the daylight image and every report page, then record exact hashes.
python projects/highland-drawings/package.py
```

Python 3.11 with bpy 5.0.1 is used for native build/render/validation. Preparation/reporting also need NumPy, Pillow, PyMuPDF and ReportLab; DejaVu Sans must be installed. Dimensions are inches in the specification and meters in meshes. Source detail renders are 200 dpi; additional 300-360 dpi crops were inspected for return jambs.

Repository-only regression checks use the existing fixtures: `"$HIGHLAND_BLENDER_PY" -m unittest discover -s tests -p test_render_workflow.py`. Their results are included in the archive.

Validation covers the exact mesh allowlist, protected north hashes, source links, both frame axes and wall-normal placement, unclipped jambs, overlapping voids, polygon simplicity, actual slab perimeter/area/levels, changed coping tops, packed images, all exported architecture and 432 saved dusk camera frames. Seven native provenance views, the daylight still and report are recorded in the visual review. The archive contains the original PDFs, base native scene and all reproduction inputs. Revision 03's movie remains a separate earlier delivery.
