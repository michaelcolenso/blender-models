# Building B: 8-phase 4D sequence (bid team only)

A 32-second construction sequence of the under-slab re-pipe across all four ground-floor units,
with a push-in on B-104. Built and keyframed in Blender by
[projects/meydenbauer-b/animate.py](../../../projects/meydenbauer-b/animate.py). The HUD and
encoding come from [anim_finish.py](../../../projects/meydenbauer-b/anim_finish.py).

| File | What it is |
| --- | --- |
| [proxy-60.mp4](proxy-60.mp4) | Timing check: every 6th frame (10 fps), 480×270, 6 samples, rendered on CPU. It is a preview, not the film. |
| [proxy-60-poster.png](proxy-60-poster.png) | A water-test frame from the proxy |
| [Meydenbauer-B-4D.blend](Meydenbauer-B-4D.blend) | Editable scene (Git LFS). The timeline has eight phase markers; every timed change is a keyframe. |

For the full film (1920×1080, 30 fps, 960 frames, 128 samples), run
[runpod_animate.sh](../../../projects/meydenbauer-b/runpod_animate.sh) on one RTX 4090:
`setup`, then `bench` (it prints the projected hours), then `render 2`, then `finish`. Setting
`FPS=60` doubles the frames for the same 32 seconds. The 2026-10-25 RunPod film is in
[../runpod](../runpod/).

`finish` also writes a clean master with no HUD (`final-30-clean.mp4`). Commit it before stopping
the pod. After that, changing a phase note, the disclaimer or the progress bar is
`runpod_animate.sh hud`, a CPU job of minutes that needs no re-render.

Fixed after the 2026-10-25 render, and checked on every build:

- **Black patches.** At 2 s and 30 s, faded objects behind many ghost-wall layers rendered black.
  Fully faded objects are now hidden from render (490 objects keyed).
- **Wide-shot crop.** The wide shots cropped B-101. All seven wide shots must now keep the whole
  building inside the frame and clear of the HUD bands.
- **Vanity tops.** The tops did not fade with their cabinets.

## What each phase shows, and from where

| Phase | Shown | Source |
| --- | --- | --- |
| 01 Existing + investigation | Floor windows over the routes; a sweep runs along the existing cast iron and paints orange locate marks | Routes: P1.01 hatched demolition centrelines (56 runs, all within 2 ft of a new run). Material: cast iron per the SOR. |
| 02 Staging + fixture removal | Ram Board, poly dust walls, work lights and staged materials appear; 15 toilets and vanities lift out | P1.01 keynote 10. Fixtures sit at the P1.02 WC and LAV connections; their geometry is assumed. |
| 03 Demolition + excavation | Saw-cut edges glow; slab and finish cut-outs lift away; soil is dug down to the cast iron | S2 trench footprint (10/P5.1 2'-0" plus pits) |
| 04 New ABS installation | Cast iron removed; bedding placed; ABS grows from each tie-in upstream with a cyan front, fittings and risers appearing as it reaches them | P1.02 routes and sizes; bedding 2/P5.0 |
| 05 Water test | Test plugs in; the system fills from the tie-in upward, holds, then drains | SOR WP #2: leak test per City of Bellevue standards, no air test. A drain water test is a fill and hold, not a flow, so the fill is animated that way. |
| 06 Backfill + slab pourback | Soil rises to the pour-back underside; new 5" concrete drops in | 10/P5.1 |
| 07 Patching + finishes | Finish patches cascade into place along the building | SOR WP #1 and Allowances 1–6; finishes assigned by room type |
| 08 Fixture reinstatement | Protection removed; fixtures set back; bathroom lights come up | |

Checks, run on every build: ABS length equals the takeoff (312.74 LF), and 14 sequence-order
assertions pass. Examples:

- no ABS appears before the cast iron is gone;
- the system is full during the hold and drained before backfill;
- finishes and fixtures are fully restored at the end;
- protection is removed at the end.

## Assumed

- Depths: tie-in invert 3.5 ft. The existing pipe uses the new profile.
- Slab 4" and soil.
- Layout of protection and containment.
- Fixture shapes and the vanity size.
- Studio lighting, and the camera path through ghosted walls.

All four units are shown working at once. The SOR requires phased work so units stay occupied,
so this film shows the work in each unit, not the schedule.
