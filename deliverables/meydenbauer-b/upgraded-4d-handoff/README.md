# Meydenbauer Building B — upgraded 4D handoff

Commit date: 2026-10-25  
Website version: `a6fe0f4`  
Handoff source commit: `a6fe0f4` (`Upgraded cinematic construction sequence`)

This directory documents the upgraded 101 Meydenbauer Building B coordination handoff and identifies the exact binary deliverables by size and SHA-256 hash.

## Delivered work

- Hyper-realistic exterior and X-ray coordination model for units B101–B104
- 56-second, eight-phase cinematic construction sequence
- Continuous camera choreography and procedural construction animation
- Sequential ABS route growth, demolition cut tracing, water-test pulses, backfill, pourback, finish restoration, and fixture reinstatement
- Model-tracked callouts and an eight-phase progress timeline
- Professional narration, ambient score, and transition sound
- Comprehensive project takeoff and separate Bellevue Q1 2027 open-shop pricing workbook

## Key output files cataloged here

| Deliverable | Format |
|---|---|
| `Meydenbauer_4D_Construction_Sequence_Upgraded.mp4` | 1280×720, 24 fps, H.264/AAC, 55.968 seconds |
| `Meydenbauer_4D_Construction_Sequence_Upgraded.blend` | Editable animated Blender source |
| `Meydenbauer_Photorealistic_Coordination_Model.glb` | Interactive photorealistic coordination model |
| `Meydenbauer_Photorealistic_Coordination_Source.blend` | Editable static photorealistic source |
| `Meydenbauer_Comprehensive_Project_Takeoff.xlsx` | 126-line comprehensive project takeoff |
| `Meydenbauer_Bellevue_Q1_2027_Priced_Takeoff.xlsx` | Separate Q1 2027 priced ROM budget |
| `Meydenbauer_Waste_Repipe_Bid_Set.pdf` | Contract coordination reference |

## Binary-file note

The current GitHub connector used for this commit accepts text payloads only. The large binary deliverables are therefore cataloged in `asset-manifest.json` and `asset-manifest.sha256` rather than committed through an encoding path that could corrupt them. Use a local Git client or Git LFS to add the binary files themselves.

## Verification summary

- Native Blender scene: frames 1–672 at 12 fps
- Delivered MP4: 1,343 video frames, 24 fps, 55.958 seconds
- Audio: AAC, integrated loudness −16.1 LUFS, true peak −1.3 dBFS
- Blender audit: 2,980 objects, 50 collections, 122 node materials, 2,971 actions, 4,394 f-curves, 19,763 keyframes
- No animation drivers or NLA tracks remain
- All audited keyframes use Bezier interpolation with AUTO_CLAMPED handles
- The final handoff download points to the upgraded 16,918,114-byte MP4
