# Highland daylight revision 02

Continuation of the [20 October exterior handoff](../highland-refined/HANDOFF.md). The deliverable is one revised daylight still, a separate packed Blender scene, a four-page source comparison, and the camera/opening evidence in [deliverables/highland-daylight](../../deliverables/highland-daylight/README.md).

The camera uses nine manual correspondences on photo-02 and the existing simplified model. Fit residuals describe agreement with those interpreted points; they do not establish surveyed camera position or building accuracy. The optimizer fixes the principal point at the image center and assumes a 36 mm horizontal sensor and no lens distortion. Its bounds, source picks and residuals are retained.

The native revision keeps all 955 protected architectural mesh vertices, transforms and faces. No opening candidate was added. All 16 conflicts remain unresolved after rechecking outward-facing plan segments against the elevation registration and inspecting the available source crops. The inventory stays at 175 openings.

Presentation changes interpret photo-02: procedural sky illumination with an interpreted blue camera/reflection gradient, warmer brick with continuous world-scale courses, pale trim, more open curtains, reflective glass and layered terrace shrubs. Materials, species, shrub dimensions, site, neighboring facades and exact window/recess details remain assumed. Registered polygons, floor/grid controls and roof datums remain governed by the inherited spec. The original architectural PDF is absent.

Run from the repository root, with the handoff's original packed `.blend` available. Python 3.11 with NumPy/SciPy is used for the camera fit; Pillow and ReportLab for the report; Blender Python requires `bpy==5.0.1`. On a fresh machine, install `projects/highland-daylight/requirements.txt` into a Python 3.11 environment. No GPU or new network asset is required. The dependency ranges support rebuilding but do not promise identical pixels across versions or hardware.

```bash
python projects/highland-daylight/fit_camera.py
python projects/highland-daylight/audit_openings.py
/workspace/.venvs/blender-models/bin/python projects/highland-daylight/build.py --preview
# Inspect the draft, then render and save the final native model.
/workspace/.venvs/blender-models/bin/python projects/highland-daylight/build.py
python projects/highland-daylight/report.py
/workspace/.venvs/blender-models/bin/python projects/highland-daylight/validate.py
# Inspect the final image and every PDF page before recording visual-review.json.
python projects/highland-daylight/package.py
```

`--build-only` saves the native scene and GLB without rendering. The build always starts from the earlier packed handoff, so rerunning does not accumulate new objects. Configuration lives in `daylight.json`; manual photo correspondences live in `photo-landmarks.json`. Generated camera evidence lives in `camera-fit.json`. The new model has one daylight scene; the original two-scene model and its movie remain available in the earlier handoff. The GLB carries source/assumption metadata but simplifies procedural materials, lights and the sky; use Blender for the reference appearance.

Observed on this workspace: the half-resolution 16-sample draft took about one minute; the final 64-sample still plus GLB export took 862 seconds (about 14 minutes). These are CPU observations, not timing guarantees. Review a draft before starting the final render.

Next: reconcile the return openings from full original sheets or clearer photographs, then assess cornice/window differences visible in the source comparison. The dusk movie can follow the settled geometry and appearance after representative Cycles frame benchmarks.

The saved scene is also registered as `highland-daylight-photo-study` in `render/scenes.json` for repeatable GitHub Actions previews through the existing saved-scene workflow. That workflow renders the committed model, not the generating configuration; rebuild the native file before expecting a source change to appear there.

Source photo: supplied by the owner, capture metadata unknown. Inherited surrounding footprints: [OpenStreetMap contributors](https://www.openstreetmap.org/copyright), ODbL 1.0; heights and appearance are approximate. The original handoff's packed Poly Haven sky remains part of the source asset; this revision uses Blender's procedural daylight sky for illumination.
