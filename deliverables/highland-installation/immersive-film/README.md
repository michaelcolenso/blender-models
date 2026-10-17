# Highland — full-frame architectural film

The installation now fills the 16:9 frame. Unboxed serif titles appear beside the current work, settle with a soft upward movement, and fade to leave room for the action. The exterior opens the film; a gentle editorial focus move follows the first distribution runs. The view opens again for the completed system. Short contextual lines replace the previous sidebar, bullets, title frames and progress rules.

- **Highland-repipe-immersive-90s-1080p.mp4** — the complete 90-second cut, 1920 × 1080 at 24 fps, with the approved narration/score and optional selectable narration captions.
- **Highland-immersive-editable.blend** — opens on **MASTER - Immersive film**. The full-frame model plate, title placement, timing, opacity and focus moves are editable. The three source-derived 3D scenes retain their piping and camera animations.
- **Highland-immersive-editable.zip** — portable source tree, model plate, audio, fonts, scripts, design settings, editable file and governing installation references. Keep the folder structure intact.
- **Highland-immersive-storyboard.png** — ten frames decoded from the actual movie.

The saved master uses the clean model movie as its picture layer. Edit the retained 3D scenes and re-render them when changing modeled work. The frame has no presentation inset, surrounding border, sidebar or progress rail. A compact color key and the required conceptual-status footer remain discreetly visible.

The film reuses the validated **960 × 540 Cycles plate, four samples and two native scene frames per second, motion-interpolated to 24 fps**, with new 1080p typography and editorial reframing. This is a 1080p review, not a new native 4K geometry render. The approved compressed audio payload is unchanged. Source geometry, original sequencing and field-verification requirements are preserved; graphic arrival glimmers do not depict water flow. The test remains required future work and service transfer remains conceptual.

The font pair is Noto Serif Display and Noto Sans, supplied with its license. Positions and timing are in **design.json**. All drawing geometry and engineering assumptions remain governed by the supplied installation specification.

From this script folder, with the supplied environment or equivalent dependencies:

```bash
/workspace/.venvs/highland-audio/bin/python compose_immersive.py --previews
/workspace/.venvs/highland-audio/bin/python compose_immersive.py
/workspace/.venvs/blender-models/bin/python build_editable.py
python validate_delivery.py
```

The archive includes `output/media/` so the film can be re-exported without the earlier working caches. Python needs Pillow; Blender steps need bpy 5.0.1. FFmpeg and FFprobe are system dependencies. Validation covers runtime, frame count, codecs, unchanged audio, readable picture bounds, smooth focus changes, full-frame layout and the editable source. The original gate scripts remain unchanged.
