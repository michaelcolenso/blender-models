# Building B: 4D sequences (bid team only)

Two films from one Blender build, [animate.py](../../../projects/meydenbauer-b/animate.py):

- **Unit-by-unit sequence** (`--plan sequence`, new). The units go one at a time on a strawman
  schedule. Each phase gets screen time in proportion to its working days, and the film shows the
  haul routes to the staging area and the occupied-unit service rules.
- **Overview** (`--plan overview`, the 2026-10-25 film). All four units work at once in
  8 × 4 s phases.

## Unit-by-unit sequence

The order is B-103 → B-102 → B-101 → B-104, and the film runs 101.5 s for 81.5 working days.
Above a 1.5 s floor, each phase gets 1.1 s per working day, so the 1-day phases stay readable.
The HUD has a working-day counter and a Gantt of all four units with a playhead. So a long phase
is long on screen, and the 3-day cure inside "07 Patching + finishes" plays as time passing.

| File | What it is |
| --- | --- |
| [seqproxy-30.mp4](seqproxy-30.mp4) | Timing check: every 6th frame (5 fps), rendered on CPU at 480×270 with 8 samples, then upscaled to 960×540 under the HUD. It is a preview, not the film. |
| [seqproxy-30-poster.png](seqproxy-30-poster.png) | B-104 demolition on the haul shot, the longest haul |
| [Meydenbauer-B-4D-sequence.blend](Meydenbauer-B-4D-sequence.blend) | Editable scene (Git LFS). The timeline has 32 markers, one per unit and phase. |

### Strawman schedule and haul

All values below are assumptions. They come from
[schedule.py](../../../projects/meydenbauer-b/schedule.py) and
[logistics.py](../../../projects/meydenbauer-b/logistics.py).

- **Quantities** are the takeoff's S2 case at a 3.5 ft tie-in invert.
- **Rates** are in `RATES`: saw-cut 150 SF/day, hand excavation 8 CY/day, ABS 40 LF/day plus
  0.15 day per connection, a 3-day cure, and finish patching at 80 SF/day.
- **Haul out** is bank CY × 1.25 swell, plus the 4" slab.
- **Haul in** is bedding and backfill imported, plus the 5" pour-back.

Replace the rates with your crew plan and re-run the two scripts. The film, HUD and checks follow.

| Unit | Order | Working days by phase (01–08) | Total | Screen time | Out (CY loose) | Route | One way | 10-yd bins | In, total (CY) | of which concrete (CY) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| B-103 | 1 | 1 / 1 / 3.5 / 3 / 1 / 3 / 5.5 / 1 | 19 | 22.5 s | 24.4 | J-K core | 243 ft | 3 | 20.4 | 2.2 |
| B-102 | 2 | 1 / 1 / 4 / 3.5 / 1 / 3 / 6 / 1 | 20.5 | 24.1 s | 28.3 | C-D core | 152 ft | 3 | 23.6 | 2.7 |
| B-101 | 3 | 1 / 1 / 3.5 / 3 / 1 / 3 / 5.5 / 1 | 19 | 22.5 s | 25.2 | C-D core | 148 ft | 3 | 21 | 2.3 |
| B-104 | 4 | 1 / 1 / 5 / 4 / 1 / 3.5 / 6.5 / 1 | 23 | 26.9 s | 33.4 | J-K core | 229 ft | 4 | 27.9 | 3.3 |

The total is 81.5 working days, which is 115 calendar days at 5 working days a week. There are no
holidays and no preconstruction time: no submittals, permit, mock-up or mobilization. Out of
that, 111 CY loose goes out and 93 CY comes in, 10.5 CY of it concrete. At 4 CF a barrow (assumed), that is about 754
trips out and 629 in.

Why this order (assumed):

- **B-103 first, as the pilot.** It is the smallest network, at 64.8 LF.
- **B-104 last.** It is the largest, and its kitchen-stack run waits on RFI 4.

### What the film shows, and on what basis

| Shown | Basis | Status |
| --- | --- | --- |
| Staging pad (~1,000 SF, fenced), with a roll-off bin and a bedding/backfill stockpile on it | SOR Fig 8 and general note 10. Pad position and size are read off the aerial at about 4 px/ft. | Assumed, not to scale. Bin size (10 yd) and stockpile assumed. |
| Garages, drive, site base | SOR Fig 8; SOR puts the garages about 10 ft east of Building B | Assumed massing |
| Haul out (amber dashes) in demolition and excavation; haul in (cyan) in backfill and pour-back | Route: work area → the unit's core entry → planter strip → north of the garages → drive → staging | Assumed path |
| One core entry in use at a time: J-K for B-103 and B-104, C-D for B-102 and B-101 | 00 22 13 §1.14.B, "limit building access to a single entry at ground level". P2.1 shows X-hatched cores at grid C-D and J-K in recesses of the east face. 01 50 00 permits use of the existing stairs and prohibits the elevators. | Reading of 1.14.B assumed. See bid clarification 2. |
| A toilet and a lav stay in each unit, with a green ring that pulses at the end of every working day | SOR note 21: "at least one sink and one toilet are available for use within the unit" by 5:00 PM daily | Which pair, and the nightly method, are assumed. B-102 has no WC end on P1.02, so it keeps a lav only. |
| Stack ends on a temporary bypass (yellow-green) while the unit's line is open (phases 03–06) | P2.1 scope note: "maintain continuous sanitary service to occupied units and shall provide temporary bypass systems". P1.01 demolition note 3 says the same for unaffected units. The SOR says the upper floors share the stacks. | Drawn as a graphic, not a route. Method assumed. |
| Phase actions inside each unit | Same as the overview (below), mapped onto each unit's window | As below |

Checks, run on every build (`animate.py` exits 1 on failure):

- **92 sequence checks**, 23 per unit, including:
  - the unit's own order: fixtures out before demolition, the service pair kept, no ABS before
    the cast iron is gone, full during the hold, drained before backfill, no finishes before the
    cure ends, restored at the end;
  - its haul routes and bypasses shown, then removed;
  - every later unit untouched and every earlier unit finished, while each unit works.
- **44 framing checks.** Each of the 22 shots keeps its subject inside the frame and clear of the
  HUD, at the start and the end of its hold.
- The film length matches the schedule, and the ABS length matches the takeoff (312.74 LF).

### Render the film

```bash
PLAN=sequence bash projects/meydenbauer-b/runpod_animate.sh setup    # build + checks
PLAN=sequence bash projects/meydenbauer-b/runpod_animate.sh bench    # prints the projected hours
PLAN=sequence bash projects/meydenbauer-b/runpod_animate.sh render 2
PLAN=sequence bash projects/meydenbauer-b/runpod_animate.sh finish   # HUD, MP4, clean master
```

The film is 3,045 frames at 30 fps, 3.2 times the 960-frame overview, so check `bench` before
committing pod time. `FPS=24` cuts the frame count by a fifth. As with the overview, keep the
clean master so HUD changes stay a CPU job (`hud` stage).

## Overview (all units at once)

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

### What each phase shows, and from where

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

### Assumed

- Depths: tie-in invert 3.5 ft. The existing pipe uses the new profile.
- Slab 4" and soil.
- Layout of protection and containment.
- Fixture shapes and the vanity size.
- Studio lighting, and the camera path through ghosted walls.

All four units are shown working at once. The SOR requires phased work so units stay occupied,
so this film shows the work in each unit, not the schedule. The unit-by-unit sequence above
shows the schedule.
