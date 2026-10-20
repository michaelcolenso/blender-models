# 200 W Highland Drive, Seattle — continuation handoff

Prepared October 20, 2026. Scope: the whole building exterior.

The revised model, daylight still and 18-second dusk movie are delivered. The next useful step is a more faithful, convincing exterior still: reconcile the remaining opening conflicts, fit the camera to the supplied photograph, then improve materials and landscape. Finish that still before spending more time on another animation.

## Open these first

Files below are at the top level of the handoff ZIP. In the current workspace they are in `/workspace/blender-models/deliverables/highland-refined/`.

| File | Purpose |
| --- | --- |
| `Highland-revised-daylight-and-film.blend` | Current editable model. Blender 5.0.1; sky packed; no external image dependency. |
| `Highland-photo-and-drawing-comparison.pdf` | Four-page photo, elevation, plan and storyboard review. Read before changing geometry. |
| `Highland-daylight-revised.png` | Current Cycles still, 1920 × 1280. |
| `Highland-dusk-approach-and-rise-18s.mp4` | Current movie, 1920 × 1080, 24 fps, 432 frames, H.264 / BT.709. |
| `Highland-revised-exterior.glb` | Portable geometry companion. Generic viewers simplify procedural materials. |
| `element-provenance.csv` | Every mesh/curve element with status, source and assumption basis. |
| `unresolved-openings.csv` | All sixteen unresolved candidates with elevation, level and ledger reference. |

The Blender scenes are **Daylight reference comparison** and **Dusk exterior film**. The native dusk camera has the complete move saved as keyframes. Use a new revision for changes so the delivered files remain available for comparison.

The earlier `deliverables/highland-cinematic/Highland-dusk-4K.png` is a visual reference from the older 165-opening model. Use the revised Blender scene above as the starting point for continued work.

## What has been done

- Restored ten omitted south opening candidates. Current inventory: 175 modeled openings.
- Reassigned visible south openings to the appropriate registered plan bays. Exact jamb positions remain assumed.
- Removed continuous pale floor bands through the brick fields; developed wider center panes and denser balcony infill.
- Added an illustrative terrace edge, steps, selected balcony furniture, plants, vehicles and neighboring context.
- Extended the assumed ground beneath the background context to remove the terrain edge visible during the rise.
- Retained the original registered plan polygons, dimensioned grid, six floor elevations and roof/parapet controls.
- Delivered a source comparison, packed native scene, tagged GLB, review images, camera coordinates and reproduction sources.

## Work to do next

1. **Reconcile the remaining opening conflicts.** There are eight south candidates and eight north candidates. Each is listed in `unresolved-openings.csv`; the governing records are `rejected_candidates` in `exterior-revised.spec.json`. Compare the floor-plan returns with the matching elevations. Resolve each with a source, or retain an explicit unresolved reason. Do not add openings simply to reach a target count.
2. **Match one daylight view to the photograph.** Use `user-photo-02.jpg` as the main corner reference. Fit the camera to the building silhouette and roof/floor lines before judging façade alignment. Compare window widths, mullions, recess depth, cornices and the terrace. The current side-by-side panels are qualitative; no measured camera fit or dimensional tolerance has been established.
3. **Improve the still.** The current output reads as a 3D study. Focus on brick scale/color, glazing/reflections, depth in the balcony recesses, natural planting and believable immediate context. Materials, terrace dimensions, landscape and surrounding façades remain illustrative. Keep those changes separate from source-derived architectural corrections.
4. **Update the film after the still is settled.** The existing movie has simpler lighting/materials than Cycles, reduced foliage and visible aliasing on thin rail infill. Improve anti-aliasing and background context. For a Cycles movie, benchmark a few representative frames on the intended hardware before committing to all 432 frames.

The next useful delivery is one stronger daylight still, the updated source comparison, a short change ledger and the revised editable model. Then carry that revision through to the dusk movie.

## Source limits and controls

The original architectural PDF is absent from this workspace. Available inputs are the registered original specification, drawing crops and two owner-supplied photographs in `projects/highland-exterior/source-review/`. Original sheets, a window schedule, clearer north/return photographs and a reliable scale reference would improve the next reconciliation.

Relevant crops include A2.03/A2.04 plan returns and A3.01 opening patterns. `user-photo-02.jpg` is the main corner appearance reference; `user-photo-01.jpg` provides an additional street/return view. Neither photograph has an independently calibrated scale here.

Preserve the registered polygons and datum controls unless a documented source supports a correction. Floor elevations are 342.00, 353.00, 363.25, 373.50, 383.75 and 394.25 ft. The 103 ft X and 150 ft Y grid spans are grid controls, not overall building dimensions. Specs use inches; Blender geometry uses meters.

Complete components retain assumed geometry even where an individual datum is documented. Orange provenance is intentional. The model is illustrative; it is not a verified as-built, quantity takeoff or construction dimension source.

## Files that drive the model

Paths in this section are relative to `/workspace/blender-models/`, or to `reproduction/` after extracting the ZIP.

| File | Role |
| --- | --- |
| `projects/highland-exterior/exterior.spec.json` | Original registered source study. |
| `projects/highland-refined/prepare.py` | Encodes the south-opening corrections and generates the revised spec and ledger. |
| `projects/highland-refined/exterior-revised.spec.json` | Generated current geometry specification, including unresolved candidates. |
| `projects/highland-refined/revision-ledger.json` | Before/after opening records and appearance changes. |
| `projects/highland-exterior/build.py` | Builds the source-tagged base exterior from the selected spec. |
| `projects/highland-refined/presentation.json` | Revised base paths, presentation camera, materials/context settings and expected opening count. |
| `projects/highland-cinematic/build.py` | Presentation builder. Pass the revised config explicitly. |
| `projects/highland-refined/detail-spec.json` | Assumed terrace/context detail and daylight/film camera controls. |
| `projects/highland-refined/detail.py` | Creates the two final native scenes, exports GLB and renders the daylight still. |
| `projects/highland-refined/viewer.js` | Real-time film materials, foliage simplification, lighting and camera playback. |
| `projects/highland-refined/render-film.cjs` | Local Chromium capture and FFmpeg encoding. |
| `projects/highland-refined/README.md` | Full build/review/package sequence and attribution. |

Change the generating inputs as well as the resulting scene. Running `prepare.py` replaces the generated revised JSON; editing that JSON alone will not survive regeneration. Do not run the cinematic builder with its default config for this revision: that selects the earlier model.

## Start without rebuilding

Open the packed Blender file and inspect both scenes. Compare the daylight view against the source photograph and the review PDF. Read the opening ledger and element inventory. No render jobs were left running at delivery.

Current Blender Python is `/workspace/.venvs/blender-models/bin/python` with `bpy==5.0.1`. The system Python has Pillow and ReportLab for the PDF/package scripts. On a new machine, configure Python 3.11 with those packages. Film capture also needs Node, pinned npm dependencies, local Chromium and FFmpeg. The Chromium path is currently `/usr/bin/chromium`.

The delivered daylight render took roughly five minutes on this CPU. Movie capture took about 29 minutes for 432 frames. These are observations from this environment, not performance guarantees. Headless Workbench/EEVEE produced blank output in this environment; use Cycles for native Blender rendering.

## Rebuild the native revision when needed

Run from the repository root. In an extracted handoff, use `reproduction/` as the root and set `HIGHLAND_BLENDER_PY` to your Blender-enabled Python.

```bash
cd /workspace/blender-models
HIGHLAND_BLENDER_PY=/workspace/.venvs/blender-models/bin/python

python projects/highland-refined/prepare.py

HIGHLAND_SPEC_PATH=projects/highland-refined/exterior-revised.spec.json \
HIGHLAND_OUT_DIR=build/highland-refined \
"$HIGHLAND_BLENDER_PY" projects/highland-exterior/build.py --build-only

"$HIGHLAND_BLENDER_PY" projects/highland-cinematic/build.py \
  --config projects/highland-refined/presentation.json \
  --output-dir build/highland-refined/presentation --build-only

"$HIGHLAND_BLENDER_PY" projects/highland-refined/detail.py
"$HIGHLAND_BLENDER_PY" projects/highland-refined/render-review.py
"$HIGHLAND_BLENDER_PY" projects/highland-refined/validate-scene.py
```

For a scene/export refresh without the daylight render, use `detail.py --build-only`. For seven movie review frames, use `node projects/highland-refined/render-film.cjs --review-only` after installing dependencies. Review those before running the full capture. The remaining movie/report/package commands are in `README.md`.

Scripts write to the existing output paths. Copy/version the delivered files before a rebuild. A changed model requires fresh scene validation, review images, camera checks and a new visual-review record; the old review record only covers the delivered revision.

## Checks already completed

| Check | Delivered result |
| --- | --- |
| Native readback | Both scenes present; sky packed; no external image dependency; source/basis tags present on all mesh/curve geometry. |
| Architecture protection | Presentation/detail passes preserve 955 protected architectural meshes from the revised base. This is a consistency check, not an as-built certificate. |
| Source controls | Registered polygons, levels, grid dimensions and roof controls unchanged. |
| Shared builder regression | Original defaults reproduce 1,103 original architectural meshes with zero vertex delta. |
| Camera | Full architectural bounding box stays in frame throughout all 432 native camera frames. |
| Encoded movie | 432 decoded and distinct frames; 1920 × 1080; 24 fps; exactly 18 seconds. |
| Visual review | Daylight/source views, all four PDF pages, seven camera positions and opening/middle/closing decoded movie frames inspected. Thin rail aliasing remains. |
| Original editable archive | 75 files; CRC check passed. A separate manifest covers the handoff ZIP. |

Evidence is in `delivery-validation.json`, `scene-readback.json`, `revision-validation.json`, `builder-regression.json`, `visual-review.json` and `archive-validation.json`. Read `film-validation.json` for the rendering method and the delivered color-conversion record.

## Workspace state and attribution

Repository branch: `handoff/highland-exterior-2026-10-20`. The handoff includes the revised shared builder, cinematic/refined generators, documents and individual render/model files. The branch starts from the current repository main; it preserves the separately published owner-tour and plumbing/repipe work. Check `git status` when resuming rather than assuming this chat's earlier uncommitted state still applies.

The complete ZIP is a repository release asset because it exceeds GitHub's per-file Git limit: https://github.com/michaelcolenso/blender-models/releases/tag/highland-exterior-handoff-2026-10-20. The repository is private, so the next person needs access. Keep unrelated projects intact.

The ZIP includes the available source crops, photographs, generators, configs and sky asset under `reproduction/`. The earlier architectural PDF is not included. Sky: Poly Haven, Kloofendal 48d Partly Cloudy, CC0. Neighborhood footprints: OpenStreetMap contributors, ODbL 1.0. Heights and façade appearance are approximate. Full attribution links are in `README.md`.

**First action for the next person:** open the revised Blender file and comparison PDF, inspect the sixteen unresolved opening records, then develop one better photo-matched daylight still.
