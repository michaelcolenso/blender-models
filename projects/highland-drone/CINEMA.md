# Highland cinematic film

A 30-second, 2.39:1 owner film cut from the native Blender walkthrough. It
replaces the single continuous drone flight with eight composed shots, a dusk
exterior, an x-ray elevator section, graded picture, typography and an original
score. The doors, elevator rise and section are the same native keyframes that
`build_blender.py` validates; the edit only chooses where each camera looks.

| # | Shot | Film time | Native frames | Lens | Purpose |
|---|---|---|---|---|---|
| 01 | Arrival | 0.00–4.50 s | 1–108 | 20 mm, shifted | Dusk establishing view of the east frontage with title |
| 02 | Entry | 4.50–7.50 s | 66–137 | 28 mm | Push to the east glazing as the entry doors open |
| 03 | Lobby | 7.50–10.50 s | 150–221 | 20 mm | Lobby 110 toward the connector |
| 04 | Slats | 10.50–12.75 s | 222–275 | 50 mm f/2 | Insert along the walnut feature wall |
| 05 | Corridor 108 | 12.75–15.75 s | 200–271 | 24 mm | Slider past residence doors toward Elevator M1 |
| 06 | Elevator | 15.75–18.75 s | 280–351 | 26 mm | Symmetrical landing-door reveal |
| 07 | Section | 18.75–21.75 s | 378–449 | 35 mm | X-ray R1 to R2 rise with live datum readout |
| 08 | Corridor 208 | 21.75–26.25 s | 470–577 | 20 mm | Push toward Stair M1, fade to the end card |

Every camera is level and lens-shifted, so verticals stay vertical. The
exception is the section shot, which looks down at the cut building. Shot
lengths are whole beats at 80 BPM, and the score's chord changes land on the cuts.

## Files

- `cinema.shots.json`: the edit. Camera keys use plan inches in the exterior study's
  coordinate system, plus lens, shift, aperture, focus point, label and exposure trim.
- `cinema.py`: opens the validated walkthrough scene and adds the following:
  - dusk sky, lit windows and wet pavement;
  - scanned materials and models (below), lever hardware and an elevator call station;
  - windows on the neighboring massing, calmer luminaires and the lobby slat wall;
  - the x-ray section treatment and one camera per shot.

  It saves `Highland-cinema.blend`, renders frames per shot (resumable) and validates
  camera clearance and smoothness at every film frame.
- `cinema_assets.py` and `assets/polyhaven-cinema.lock.json`: Poly Haven CC0 assets, locked
  by URL, size and MD5 and downloaded into `build/assets/polyhaven` (about 190 MB, not committed):
  - walnut veneer (doors, frames, slats, cab), plaster relief (walls, ceilings);
  - limestone tile (lobby and cab floors), brick (facade), wet asphalt and concrete pavers;
  - street trees, lobby plants, two lounge chairs and a side table, post-top street lamps, a hydrant.

  Textures are box-projected at their real-world size, so the procedural boxes need no UVs.
- `cinema_score.py`: original NumPy score and sound design. The chords follow the cuts.
  The door swing, landing chime, cab run and arrival ding come from native scene frames.
- `cinema_finish.py`: Lanczos upscale (when needed), halation, S-curve, split-tone,
  lens aberration, vignette, grain, scope letterbox, titles, chapter labels,
  section gauge and end card. It masters audio with two-pass `loudnorm` to −16 LUFS / −1.5 dBTP
  and encodes two-pass 10 Mbit/s H.264. It also writes stills, a shot sheet, a GIF and checks.

## Rebuild

Python 3.11 from the repo-wide uv lock. `bpy==5.0.1` needs NumPy 1.26, so the lock pins
`opencv-python-headless` 4.10 (later releases pull NumPy 2) and one environment covers the
scene, score and finish.

```bash
uv sync --group vision

uv run python projects/highland-drone/cinema_assets.py           # CC0 assets, checksum-verified
uv run python projects/highland-drone/cinema.py --validate --profile proof --step 12   # quick look
uv run python projects/highland-drone/cinema.py --reuse --profile local                # all 630 frames
uv run python projects/highland-drone/cinema_finish.py --profile local
```

| Profile | Render size | Max samples | Where | Use |
|---|---|---|---|---|
| `proof` | 640 × 268 | 8 | CPU, ~8 s/frame | Framing checks |
| `local` | 1280 × 536 | 20 | 4-core CPU, ~35–60 s/frame (~8 h) | CPU fallback, upscaled 1.5× in finishing |
| `final` | 1920 × 804 | 128 | GPU (`--device OPTIX`) | Native 1080p master |
| `uhd` | 3840 × 1608 | 96 | GPU | 4K master (`cinema_finish.py --master 2160`) |

GPU rendering on RunPod, with a benchmark that projects the run time, is in [RUNPOD.md](RUNPOD.md).
`--worker k/n` splits frames across parallel processes; `--bench` times one frame per shot.

`cinema.py` builds and validates the base walkthrough itself when its report is missing,
failed or stale. `--shots`, `--step` and `--only` render subsets, and existing frames
are skipped, so an interrupted render resumes where it stopped. Each frame folder is
bound to the prepared scene and its settings (`SCENE.json`). After any change to the
scene code, assets or cameras, frames from the old scene are moved aside, not reused.

## What is illustrative

The floor datums (R1 353.00 / R2 363.25 ft) and the circulation rectangles come
from the sources listed in `README.md`. Everything else seen in this film is a
presentation treatment and must not be read as documented:

- the dusk lighting, wet pavement, street lights and lit windows;
- the walnut slat wall and all other finishes, furnishings, hardware and planting;
- the street trees, street lamps and hydrant, which keep the study's tree positions but not its species;
- the elevator car, its door timing and the x-ray section;
- the neighboring massing (OSM, with approximate heights).

The film carries a persistent on-screen note and a full end-card statement.
