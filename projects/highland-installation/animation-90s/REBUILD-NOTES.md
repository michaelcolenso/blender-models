# Corrected replacement scripts

The supplied four-script proposal was integrated with the existing studio treatment. The governing installation geometry and both original gate scripts remain unchanged. The released 90-second films remain separate from this rebuild review.

The corrections are concrete:

- The film still begins outside the supplied exterior model, with a one-second dissolve into shared distribution. The native master retains eight chapter scene strips at their original frame ranges; an editable meta group supplies the exterior reveal.
- One camera rig spans the unit chapters. It preserves the reviewed kitchen/service focus moves and continuous 0.38°/s drift, including the 00:29 and 00:58 boundaries.
- Pipes retain Principled Roughness 0.25 and Coat Weight 0.5, physical studio lighting, short-range receiver AO and AgX. The plate remains #F7F6F2, the return orange and proposed access dashed amber.
- Callouts use camera projections at every output frame. The kitchen anchor is the source `CW-04` endpoint; `A03` remains wet-wall access. Labels describe proposed operations and required testing; restoration is not presented as an approved rated-assembly detail.
- Native callouts live inside one meta group. Their animation does not turn thousands of changing coordinates into separate editorial channel roles. The tested maximum channel is 63, including nested strips.
- Flow-marker positions are keyed every frame. Markers and return pulses remain gated until 01:07; the installation highlight is explicitly labeled as assembly.
- Quiet graphic ticks follow access, assembly and cutover timing and duck under narration. They are presentation cues, not actual telemetry. `--reuse-narration` preserves the supplied narration without needing voice-model weights.
- Render caches include the model, scripts, settings and blueprint fingerprints. Clip encodes use a temporary file and must pass exact frame-count checks before becoming reusable.

## Dependencies

Keep `animation-90s`, `installation` and `studio-upgrade` as sibling folders under `projects/highland-installation`. The studio module, 400-DPI drawing, HDRI and exterior study are required inputs. The corrected rebuild archive includes this directory structure and the editable review. These are integrations with the existing project; four Python files alone do not contain all the media and studio assets.

Python 3.11 with bpy 5.0.1 runs the Blender steps. Pillow, NumPy and OpenCV run composition; FFmpeg/FFprobe and DejaVu Sans are system dependencies. ReportLab supports the unchanged delivery packager. Piper and SciPy are needed to regenerate speech; the supplied narration can be reused without voice weights.

## Preview and verify

Run from `projects/highland-installation/animation-90s` in a working copy:

```bash
/workspace/.venvs/highland-audio/bin/python prepare_animation.py
/workspace/.venvs/highland-audio/bin/python make_audio.py --reuse-narration
/workspace/.venvs/blender-models/bin/python animate_highland.py --preview --width 960 --samples 4
/workspace/.venvs/highland-audio/bin/python compose_film.py --previews
/workspace/.venvs/blender-models/bin/python finalize_blender.py
/workspace/.venvs/blender-models/bin/python verify_presentation.py
```

The eight preview times are 00:01.5, 00:13, 00:23.5, 00:42.5, 00:55.5, 01:09, 01:20 and 01:28. These are individual 960 × 540 / four-sample Cycles renders composed into 4K storyboard frames. They are not a newly rendered movie. Expect minutes on a CPU, rather than a guaranteed 15-second pass.

`finalize_blender.py` remains byte-for-byte unchanged. Its SHA-256 comparisons cover 94 unit and 45 shared objects; all assertions at t=28, 30, 44, 55, 61, 63, 66, 68, 69 and 80 and all eight scene-strip bounds remain active. `verify_presentation.py` adds 51 checks, including every exported anchor, camera continuity, source resolution, callout start timing and recursive channel limits.

## Complete the full film rebuild

After preview acceptance, the same scripts render a fresh complete sequence:

```bash
/workspace/.venvs/blender-models/bin/python animate_highland.py --resume
/workspace/.venvs/highland-audio/bin/python compose_film.py
/workspace/.venvs/blender-models/bin/python finalize_blender.py
/workspace/.venvs/blender-models/bin/python verify_presentation.py
/workspace/.venvs/highland-audio/bin/python deliver_animation.py
python package_rebuild.py --destination /path/to/delivery
```

The default is 1600 × 900 model imagery, 16 Cycles samples and six native frames per second, interpolated to a 3840 × 2160 / 24 fps composition. Native 4K/24 fps requires changing the render settings and clearing incompatible caches; the studio guide covers the production path. H.264 cannot guarantee byte-exact paper RGB.

Do not reuse old frames merely because their names or file sizes match. Move incompatible generated frame/clip directories aside when a fingerprint changes. The unchanged `deliver_animation.py` must run against the new complete movie and native-frame coverage before reporting its full delivery gates as passed. Its original ZIP file list predates the studio dependencies; `package_rebuild.py` adds the complete tree and hashes without modifying those gates. Add `--review` when packaging only the verified editable rig and stills.

The review included here verifies the new source rig, eight stills, native master composition and audio. A fresh full-length export was not run for this code review, so new full-movie delivery checks are not claimed. The previously delivered 90-second studio review remains available in the parent delivery folder.
