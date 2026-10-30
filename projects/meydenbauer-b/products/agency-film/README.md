# agency-film: Building B presentation film

**What it produces:** a 74.5-second, 1920×1080 / 24 fps film with a 2.39:1 letterboxed picture,
titled *Home, Uninterrupted*. It shows the proposed under-slab re-pipe of Building B as a sequence of
plan graphics, hero stills and existing GPU footage. It has scratch narration, an original score and
a sidecar caption track. The outputs are in [../../deliverables/agency-film](../../deliverables/agency-film/README.md).

**Audience (assumed):** the owner, the board and the property manager at a bid interview or a
resident-facing briefing. Every picture frame carries "Illustrative, not a contract document."

**Sources:** nothing is re-measured here. All geometry and numbers come from the
[underslab](../underslab/README.md) product:

| Used for | From | Status |
| --- | --- | --- |
| Plan graphic: walls, envelope | `meydenbauer-b.shell.json` (P2.1) | provisional |
| Plan graphic: routes, tie-ins, 312 LF counter | `meydenbauer-b.spec.json` (P1.02); `--check` asserts 312.74 LF against the takeoff | provisional (KEAD: diagrammatic, field verify) |
| Footage, shots 05/06/08/10 | 2026-10-25 RunPod film `deliverables/underslab/runpod/…1080p30.mp4`, cropped to 2.39:1 to remove its HUD and played at 0.8× | as that film |
| Hero stills H0–H4 | `deliverables/underslab/anim/Meydenbauer-B-4D.blend` with new cameras ([hero_shots.json](hero_shots.json)); CPU Cycles, 20 spp + OIDN | as that scene (depths, protection, fixtures assumed) |
| VO and super claims | each shot's `claims` in [film.json](film.json) (SOR, P1.01, P1.02, 10/P5.1) | cited as the underslab product cites them; the bid set was not re-read for this film |

## Script

| # | Time | Picture | VO | Super |
| --- | --- | --- | --- | --- |
| 01 | 0:00 | Title card | — | |
| 02 | 0:05 | Plan draws on, units labelled | Under four occupied homes in Building B, the cast-iron waste line is being replaced. | 4 homes / 1 slab |
| 03 | 0:12.5 | Routes draw from each tie-in | Three hundred twelve feet of new pipe, routed under kitchens and baths. | 0 → 312 LF |
| 04 | 0:19.5 | H0 *before*, slow push | This work happens inside people's homes, so it is planned around the people who live there. | |
| 05 | 0:25.5 | GPU: staging and protection | Lines are located, floors protected, and dust walls go up. Then, a narrow saw-cut trench, two feet wide. | |
| 06 | 0:30.5 | GPU: demolition and excavation | (continues) | 2'-0" typical trench, 10/P5.1 |
| 07 | 0:35.5 | H2 *during*, match-cut | New Schedule 40 ABS goes in, sloped a quarter inch per foot. | 1/4" per ft, Sch 40 ABS |
| 08 | 0:41.5 | GPU: water test | Every line is filled and held for a water test before anything is covered. | Water test, City of Bellevue standards |
| 09 | 0:46.5 | H3 water held, drift | — | |
| 10 | 0:50 | GPU: backfill and pour-back | Then backfill, new concrete, and finishes patched to match. | 5" concrete pour-back |
| 11 | 0:55 | H4 *after*, match-cut | And at the end of every working day, each home has a working toilet and sink. | Every day by 5:00 PM |
| 12 | 1:02 | H1 wide, pull-out | Phased unit by unit, so residents stay home throughout. | |
| 13 | 1:08 | End card and disclaimer | — | |

H0, H2 and H4 use one camera on the same frame of B-104, so the cut runs before → during → after.

## Run

```bash
git lfs pull --include="projects/meydenbauer-b/deliverables/underslab/**"
uv run bm run meydenbauer-b/agency-film stills    # 5 stills, ~8 min each on 4 CPU cores
uv sync --group audio                             # Piper voice weights: see film.py narration()
uv run bm run meydenbauer-b/agency-film audio     # VO, score, mix.wav; rewrites Meydenbauer-B-film.srt
uv run bm run meydenbauer-b/agency-film video     # ~10 min; MP4, poster, contact sheet in build/meydenbauer-b/agency-film/
uv run bm run meydenbauer-b/agency-film check     # what CI runs
```

To change a line or a shot, edit `film.json`, then re-run `audio` and `video`. `audio` fails if a
line no longer fits before the next line starts. `check` fails if the captions drift from the VO,
if a VO line has no `claims`, or if the plan length moves off the takeoff.

## Limits: read before showing it to anyone

- **The narration is a scratch track.** It is synthetic Piper TTS on LJ Speech, a public-domain
  dataset. Book a voice actor for any external use, and keep the caption timings as the record.
- **No new motion was rendered.** CPU Cycles runs at about 105 s per 1280-wide frame, so the new
  shots are stills with 2-D camera moves. The moving 3-D footage is the 2026-10-25 RunPod film,
  which shows all four units working at once. The film says "phased unit by unit" over a picture
  of simultaneous work. A unit-by-unit GPU render (`PLAN=sequence runpod_animate.sh`) would close
  that gap.
- **The score is original procedural audio** written in `film.py`. It is not licensed music.
- **The work sequence, protection layout, depths and fixtures are assumed,** as in the 4D scenes.
  The routes are diagrammatic, per KEAD.
- **No firm branding is included.** The end card names the project only. Add a logo or contact
  card only from your own brand assets.
