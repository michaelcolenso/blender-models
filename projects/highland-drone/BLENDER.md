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
available. All materials are procedural; the sound is packed. No paid add-ons or
third-party botanical asset libraries are required.

Rebuild with Python 3.11, `bpy==5.0.1`, NumPy and Pillow:

```bash
python projects/highland-drone/build_blender.py
python projects/highland-drone/build_blender.py --reuse --frames 1,212,319,397,529
```

`assemble_blender.py --review-only` adds the film captions to available review
frames without requiring the complete animation or encoding a movie.

Render and encode locally (FFmpeg and DejaVu fonts are also required):

```bash
python projects/highland-drone/build_blender.py --start 1 --end 624
python projects/highland-drone/assemble_blender.py
```

The **Highland native Blender film** Actions workflow divides the native Cycles
render into eight nonoverlapping 78-frame ranges, validates all 624 frames,
adds phone captions and a schematic location marker, then encodes H.264 with
stereo AAC. Draft quality uses 360 × 640 / 8 samples; phone quality uses
540 × 960 / 16 samples. Captions and the small map are added during assembly;
the architecture, in-scene signs, lighting and animation render inside Blender.

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
