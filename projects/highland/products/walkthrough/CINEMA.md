# Highland cinematic film

A 29-second (plus end card), 2.39:1 owner film cut from the native Blender
walkthrough. It replaces the single continuous drone flight with nine composed
shots, a dusk exterior, an x-ray elevator section, graded picture, typography and
an original score. The doors, elevator rise and section are the same native
keyframes that `build_blender.py` validates; the edit only chooses where each
camera looks. The edit follows the archviz film skill
(`.claude/skills/archviz-film-upgrade/SKILL.md`).

| # | Shot | Film time | Native frames | Lens | Purpose |
|---|---|---|---|---|---|
| 01 | Arrival | 0.00–4.50 s | 1–108 | 24 mm, shifted | Dusk establishing view of the east frontage with title |
| 02 | Entry | 4.50–7.50 s | 66–137 | 28 mm | Push to the east glazing as the entry doors open |
| 03 | Lobby | 7.50–10.50 s | 150–221 | 24 mm | Lobby 110 toward the connector |
| 04 | Slats | 10.50–12.75 s | 222–275 | 50 mm f/2.8 | Insert along the walnut feature wall, focused at frame centre |
| 05 | Corridor 108 | 12.75–15.75 s | 200–271 | 24 mm | Slider past residence doors toward Elevator M1 |
| 06 | Elevator | 15.75–18.75 s | 280–351 | 26 mm | Symmetrical landing-door reveal |
| 07 | Section | 18.75–21.75 s | 378–449 | 35 mm | X-ray R1 to R2 rise with live datum readout |
| 08 | Corridor 208 | 21.75–24.75 s | 470–541 | 24 mm | Push toward Stair M1 |
| 09 | Release | 24.75–29.25 s | 1–108 | 24 mm, shifted | Back outside from the roof: a level descent from just above the roof, down the lit east facade to the street-level wide, fade to the end card |

Every camera is level and lens-shifted, so verticals stay vertical. The
exception is the section shot, which looks down at the cut building. Lenses stay
at 24–35 mm, except the 50 mm detail insert. Shot lengths are whole beats at
80 BPM, and the score's chord changes land on the cuts. The film no longer ends in
a corridor: shot 09 returns outside (compression and release). Native frames 1–146
are the only ones with the exterior shown, so shot 09 reuses the arrival's frames;
the entry doors begin to swing open from its frame 66, small in the wide view. Shot 09 starts about 5 ft above the roof plate, east of the street facade, and descends 55 ft to eye height while pulling back. The camera stays level and lens-shifted the whole way (no pitch-down dive), and it shows only modelled geometry: the roof, penthouses and facade from the exterior study, with no terrace staging. It is a drone-speed move, about 4 m/s on average with eased start and landing, faster than the interior sliders by design.
The skill asks for a sunlit release; this film is set at dusk, so the release is open
sky and the warmly lit facade, not sun. The street in front of the east facade is
only about 25 m wide (OSM massing across it starts at x = 2456 in), so the 24 mm
exterior cameras gain distance along the street, not across it: shot 01 arrives from
the south, shot 09 leaves to the north-east. `cinema.py --reuse` refuses to render a
prepared scene whose camera validation failed or is out of date.

Filler area, point and spot lights are hidden from camera and glossy rays
(`light_hygiene`), so they light surfaces without leaving hotspots on glass, doors
or wet paving; the fixtures still reflect through their emissive meshes. The scene
keeps persistent data between frames of one render process.

Review pass (2026-11-08), each change checked on proof frames before and after:

- Exterior: a brighter blue-hour sky (world strength 0.55 → 0.85) so the brick and mullions keep detail.
  Fewer, rougher puddles on the street, paving and site (`soften_puddles` for the scanned surfaces: mask
  threshold 0.57 → 0.66, puddle roughness 0.03 → 0.14; `dusk` for the plain ones: puddle roughness
  0.06 → 0.16 on about a tenth of the surface instead of half), so the street reads damp, not iced.
- OSM massing: dimmer window grid (gain 0.3 → 0.12) and a distance haze (`Camera Data` view distance,
  25–220 m), so the approximate neighbors read as a soft skyline instead of dark boxes.
- Lit apartments: each recess gets its own lamp colour and brightness, brighter toward the ceiling, instead of one
  flat peach panel repeated. Film v2 (`cinema_look.windows`) carries this further: 2500–3800 K, occupancy and blinds.
- Floor-projected wayfinding labels ("CORRIDOR 108", "LOBBY 110") are hidden in the film; the chapter
  titles carry the room names. They stay in the native walkthrough.
- X-ray section: the residence and stair doors and their jambs ghost with the walls, and their levers hide,
  instead of floating as solid walnut panels in the void.

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
- `cinema_look.py`: the film v2 look, called from `cinema.py` after its dusk, interior and x-ray passes. Each part
  has a CONFIG dict and copies a material to `<name> / v1 backup` before changing it:
  - blue hour: the camera sees a graded blue-hour sky, while the tinted HDRI keeps lighting the scene
    (Light Path > Is Camera Ray); 2900 K street lamps with downward pools; a thin atmosphere over the street;
  - lit windows: per-window colour (2500–3800 K), occupancy (about 28% off) and lowered blinds, with matching curtains;
  - interior: micro-bevels (under the bump, so wood grain survives) and slight roughness variation (not on metals,
    where it smeared reflections); entry glass at IOR 1.52 with a green-blue edge tint;
  - section: gold slab and shaft lines, faint bronze partition lines, a light fill on ghosted floors and ceilings.

  AgX glow, lens fringing and grain stay in `cinema_finish.py`, so they run once.
- `cinema_assets.py` and `assets/polyhaven-cinema.lock.json`: Poly Haven CC0 assets, locked
  by URL, size and MD5 and downloaded into `build/assets/polyhaven` (about 190 MB, not committed):
  - walnut veneer (doors, frames, slats, cab), plaster relief (walls, ceilings);
  - limestone tile (lobby and cab floors), brick (facade), wet asphalt and concrete pavers;
  - street trees, lobby plants, two lounge chairs and a side table, post-top street lamps, a hydrant.

  Textures are box-projected at their real-world size, so the procedural boxes need no UVs.
- `cinema_score.py`: original NumPy score and sound design. Felt-piano chords and a pad follow the cuts (no arpeggio
  since film v2); street air and wind outside, a warm room tone inside, faint footsteps on stone then carpet, a hum
  that rises in pitch with the cab, and a resolving chord on the end card.
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

uv run python projects/highland/products/walkthrough/cinema_assets.py           # CC0 assets, checksum-verified
uv run python projects/highland/products/walkthrough/cinema.py --validate --profile proof --step 12   # quick look
uv run python projects/highland/products/walkthrough/cinema.py --reuse --profile local                # all 702 frames
uv run python projects/highland/products/walkthrough/cinema_finish.py --profile local
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

- the dusk lighting, wet pavement, street lights, street atmosphere and lit windows (including their lamp colours, occupancy and blinds);
- the walnut slat wall and all other finishes, furnishings, hardware and planting;
- the street trees, street lamps and hydrant, which keep the study's tree positions but not its species;
- the elevator car, its door timing and the x-ray section;
- the neighboring massing (OSM, with approximate heights).

The film carries a persistent on-screen note and a full end-card statement.
