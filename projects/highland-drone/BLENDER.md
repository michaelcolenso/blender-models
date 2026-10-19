# Native Highland Blender walkthrough

`build_blender.py` reconstructs the public interior directly as Blender meshes,
materials, lights, curves, text, constraints and animation. It loads the existing
Blender exterior study, then builds Lobby 110, the connector, Corridors 108/208,
the elevator cab and landing doors. The 624-frame timeline lasts 26 seconds at
24 fps. The soundtrack is packed into the scene as a sound strip.

The camera uses a **Follow Path** constraint on an editable Bezier curve and a
**Track To** constraint targeting an animated Empty. Its controls are sampled
from the cubic route in `flight.spec.json`. A Boolean section volume moves
through the east side during the elevator ascent, while animated material nodes
turn architectural surfaces into glass. The cab retains a solid rear panel and
floor. Entry hinges, elevator leaves, the car elevation, floor guidance curves
and section visibility are native keyframes; the scene needs no frame handler
or browser to animate.

## Open and render

Use Blender **5.0.1 or newer** for the delivered `.blend`. Play frames 1–624 or
render the active **Owner drone camera**. The file defaults to Cycles CPU,
540 × 960, 16 samples with denoising. A GPU can be selected in Blender if one is
available. Surface materials are procedural; the sound and CC0 Poly Haven HDRI
are packed. No paid add-ons or third-party botanical asset libraries are required.

New builds default to the **archviz** look. It adds individual curved leaves in
place of the original solid canopy meshes, warm apartment back panels and folded
curtains, stainless entry handrails, canopy accents, planters, a lobby console and
abstract art. Walnut uses fine vertically stretched grain; carpet has a fine
cross-weave and tile variation; stone has shallow grout and variable roughness.
Door accents use soft spot beams, not manufacturer IES photometry. The floor
trail is thinner and gently pulses. Camera look-ahead is smoothed, with a subtle 4 mm vertical drift inside the
corridors. Dense Bezier controls retain the checked route around corners. The
cab's wood feature stays in view until the section pullback starts, avoiding
a turn toward a blank wall inside the cab.
The return to Corridor 208 blends an upright bearing and pitch. The native
validation records its largest rotation step and rejects a jump above 10 degrees
per frame, preventing a sudden upward whip during re-entry.
The camera clearance checks still run against every film frame, including the
added lobby console and planter boxes.

The [archviz gallery](../../deliverables/highland-archviz/README.md) contains
the full upgraded film, phone previews, still comparisons and the matching
packed editable scene. The earlier study is retained as
`deliverables/highland-archviz/Highland-study-baseline.blend` so the before/after
review workflow continues to use the exact original baseline.

Rebuild with Python 3.11, `bpy==5.0.1`, NumPy and Pillow:

```bash
python projects/highland-drone/build_blender.py
python projects/highland-drone/build_blender.py --reuse --frames 1,212,319,397,529
```

Build the archviz review independently, preserving the previous study deliverable:

```bash
python projects/highland-drone/build_blender.py \
  --output build/highland-archviz/Highland-archviz.blend \
  --frames 1,160,319,529 --samples 24
```

`--look study` retains the simpler materials and original tree meshes. `--reuse`
opens an existing scene without rebuilding it; it does not apply a new look.
The HDRI source, license and checksum are recorded in [assets/sources.json](assets/sources.json).

`assemble_blender.py --review-only` adds the film captions to available review
frames without requiring the complete animation or encoding a movie.

Render and encode locally (FFmpeg and DejaVu fonts are also required):

```bash
python projects/highland-drone/build_blender.py --start 1 --end 624
python projects/highland-drone/assemble_blender.py
```

The **Highland native Blender film** Actions workflow divides the native Cycles
render into sixteen nonoverlapping 39-frame ranges, validates all 624 frames,
adds phone captions and a schematic location marker, then encodes H.264 with
stereo AAC. Draft quality uses 360 × 640 / 8 samples; phone quality uses
540 × 960 / 16 samples. Captions and the small map are added during assembly;
the architecture, in-scene signs, lighting and animation render inside Blender.

The workflow is registered on the delivery branch and accepts manual runs.
Leave `existing_run` blank for a complete render. To repair a sequence, supply a
prior run ID and the inclusive replacement-frame range, using the same quality
as the prior run. `existing_run` must contain the complete 624-frame base. Use
`prior_repair_run` to retain an earlier set of replacement frames when tuning
another sequence. Actions distributes the new range across sixteen workers,
renders from the current scene, overlays the earlier repair and then the current
replacements on the base, and validates and encodes the complete film. Source
frame artifacts are retained for seven days.

Phone-quality film assembly also runs `verify_blender_film.py`: it decodes every
frame, checks the 540 × 960 H.264/AAC profile and progressive-playback metadata,
looks for black camera views and frozen sections, measures soundtrack levels,
and makes a timestamped visual review sheet. Camera turns and chunk joins still
need visual inspection; a decoded-video check does not establish spatial accuracy.

The **Highland archviz still review** workflow renders four upgraded views and
four matching views from the previously published study, then packages phone
images, comparisons, validation and the editable scene. It runs on CPU without
a RunPod account or GPU credentials. It uses the preserved study baseline,
independently of the upgraded canonical film scene. Both the still and film
workflows support manual dispatch.

To publish a checked film artifact permanently, extract it and run:

```bash
python projects/highland-drone/package_archviz_film.py /path/to/artifact \
  --base-run BASE_RUN_ID --final-run FINAL_RUN_ID --render-commit COMMIT_SHA
```

When a final run replaces a range from an earlier run, also pass
`--replacement-frames FIRST_FRAME LAST_FRAME`. For a complete single run,
use the same ID for both run arguments and omit the replacement range.

The packager checks the video hash, native validation and playback report,
preserves the original study, updates the film and matching scene, and produces
a full-length silent GIF preview for the phone gallery. The render provenance
records any replaced frame range and the source Actions runs.

## Basis and validation

A2.03/A2.04 locate the public circulation. A3.11 establishes the 123-inch R1-to-R2
rise. The rounded interior wall faces, clear ceiling height, door details,
cab, lighting and finishes remain presentation assumptions. The scene contains
no residential unit interiors or new concealed-plumbing reconstruction. It
inherits the exterior study's unresolved facade details. Nearby OSM buildings
retain approximate registration and assumed heights; attribution is stored in
the scene and source specification.

The builder evaluates the constrained camera at every film frame and checks it
against the modeled walls and moving door leaves during the walkthrough.
The deliberate exterior section pullback is excluded from wall-clearance tests.
The generated validation JSON records actual path error and any intersections.
The film assembler checks that every frame is present, image sizes agree,
sampled images contain content, and the MP4 has the expected frame count,
duration, codec and stereo audio. These checks establish rendering consistency,
not the accuracy of undimensioned existing conditions.
