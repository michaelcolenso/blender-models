# 200 W Highland — 90-second repipe animation

The released files below describe the original delivery. The corrected source rebuild now retains the exterior-first studio treatment and tracked callouts; see [REBUILD-NOTES.md](REBUILD-NOTES.md) for dependencies, verified scope and current commands.

## Watch and review

- **Highland-repipe-90s-4K.mp4** — 90 seconds, 3840 × 2160, 24 fps, H.264/AAC, with narration, original instrumental music, graphic cues and on-screen editorial captions.
- **Highland-repipe-90s-1080p.mp4** — smaller review copy with the same sequence and audio.
- **Highland-repipe-90s.srt** — narration captions, timed to the actual synthesized voice. A selectable subtitle track is also embedded in the movies.
- **Highland-repipe-storyboard.pdf** — eight representative frames from the delivered master.
- **storyboard/shot-01.png … shot-08.png** — the same eight frames at 3840 × 2160.
- **Highland-repipe-90s.blend** — editable 90-second assembly with two source-derived 3D scenes, animated cameras, pipe growth, test/cutover visibility, presentation flow markers, native text/graphics and audio.

Open the Blender file on its **MASTER - 90 seconds** scene. The timeline is frames 1–2160 at 24 fps. Eight scene strips occupy the exact requested ranges. Edit geometry/cameras in **3D - Unit B installation** or **3D - Shared distribution**. The original installation models are included separately and unchanged. Extract the whole ZIP before opening; keep the audio and opening-source image beside the project in their provided folders.

## Sequence

00:00–00:08 — source drawing and shared system, with Unit 101 / Unit 302 exception references.
00:08–00:18 — verify routes, services and access; show protection.
00:18–00:29 — reveal access and support coordination; identify the kitchen low-wall route.
00:29–00:45 — grow the new cold, hot and circulation-return distribution.
00:45–00:58 — complete branches and show the required test/inspection hold.
00:58–01:13 — depict isolation, connection, final checks, flushing and return balancing; flow appears at 01:07.
01:13–01:25 — change access to restoration boundaries and document retained service access.
01:25–01:30 — return to the shared system for the closing frame.

## Source fidelity and limits

This is a proposed installation-method animation, not a record of completed work or a construction design. Physical pipe paths, sizes and elevations, service boundaries, access locations, supports and restoration areas retain the assumptions of the original source model. The source plan issue is 29 October 2007. Existing conditions and governing revisions require confirmation.

The movie does not add a surveyed building shell, a verified existing CPVC network, individual fixture quantities, an approved firestop detail, test readings, actual shutdown durations or measured flow performance. Existing-condition information remains in the unchanged drawing context. Unit B / 106 is a pilot, not a route automatically applied to other unit types. Unit 101's irrigation drop and Unit 302's alternate-wall note remain explicit exceptions. The original source title says 200 W Highland while its location block says 202 W Highland; that discrepancy remains unresolved in the source handoff.

Camera moves, schematic highlights and flow particles are presentation elements. Particles indicate conceptual direction after the depicted transfer; they are not a hydraulic simulation. Assembly devices remain coordination symbols. Required testing/inspection is shown as a future release condition, without an assertion that a field test passed.

## Production resolution and audio

The delivered master and editorial graphics are 3840 × 2160 at 24 fps. Model imagery was rendered in Cycles CPU at 1600 × 900 and six native samples per second, then motion-interpolated to 24 fps and scaled for the 4K composition. The editable Blender rig contains full 24 fps camera and construction animation and can be re-rendered at a higher native spatial/temporal sampling rate. Normal-based analytical shading keeps the diagram clear without altering the source geometry.

Narration is locally synthesized using Piper's en_US-ljspeech-high voice, whose model card identifies the LJ Speech public-domain dataset. It is not a recording of a project representative. Instrumental music and transition cues are an original procedural composition. See audio/CREDITS.txt. Separate narration, score and combined WAV files are included for editing.

## Validation

See delivery-validation.json and blender-validation.json. Checks cover source-file hashes, unchanged geometry for 94 unit elements and 45 shared elements, exact shot ranges, pipe-reveal order, testing/cutover states, flow timing and motion, restoration order, native frame coverage, movie resolution/runtime/frame rate/codecs, audio timing, captions and storyboard image integrity. Visual inspection is recorded in VISUAL-REVIEW.md.

## Rebuild

Keep the original installation spec as the geometry authority and animation-spec.json as the production timeline. Python scripts require Blender bpy 5.0.1, Pillow, NumPy, OpenCV and FFmpeg; audio regeneration additionally needs Piper, SciPy and the referenced voice model. The supplied WAV files allow visual re-rendering without downloading voice weights. The scripts use the supplied animation-90s / installation folder relationship. In this prepared workspace:

```bash
/workspace/.venvs/blender-models/bin/python animate_highland.py --resume
/workspace/.venvs/highland-audio/bin/python compose_film.py --watch
/workspace/.venvs/blender-models/bin/python finalize_blender.py
python deliver_animation.py
```

The MP4 graphics and Blender graphics use the same event/timing data; their rasterization can differ slightly. The native Blender master renders scene strips directly. The delivered movie uses the interpolated render/compositing pipeline described above.
