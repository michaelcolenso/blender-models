# Blender scene audit — upgraded 4D sequence

Audited file: `Meydenbauer_4D_Construction_Sequence_Upgraded.blend`  
Audit mode: read-only; no scene changes were saved.

## Scene configuration

| Setting | Current value |
|---|---|
| Scenes | 1 — `Meydenbauer_Photorealistic_Exterior` |
| Timeline | Frames 1–672 |
| Native frame rate | 12 fps |
| Native duration | 56 seconds |
| Render engine | Cycles, CPU-compatible |
| Native render size | 640×360 |
| Cycles sampling | 2 samples with denoising |
| Objects | 2,980 |
| Collections | 50 |
| Materials | 122, all node-based |
| Actions | 2,971 |
| F-curves / keyframes | 4,394 / 19,763 |
| Drivers / NLA tracks | None |
| VSE | Present but empty — 0 strips |

All keyframes use Bezier interpolation with AUTO_CLAMPED handles.

## Current phase timing

| Phase | Frames | Time | Primary mechanism |
|---|---:|---:|---|
| 01 Existing + investigation | 1–84 | 0–7 s | Exterior/X-ray dissolves, existing cast iron, eight animated sonar rings |
| 02 Staging + fixture removal | 85–168 | 7–14 s | Fixture/cabinet Z-lifts and fades; four rolling protection pathways |
| 03 Demolition + excavation | 169–252 | 14–21 s | Ghosted slab, hidden close-up obstructions, orange cut-line growth |
| 04 New ABS installation | 253–336 | 21–28 s | Sequential mesh-segment growth along coordinated routes |
| 05 Water test | 337–420 | 28–35 s | Cyan duplicate pipe network with animated emissive pulses |
| 06 Backfill + slab pourback | 421–504 | 35–42 s | Per-unit bedding, backfill, vapor barrier, and pourback scale animation |
| 07 Patching + finishes | 505–588 | 42–49 s | Cascading finish restoration and returning partitions |
| 08 Fixture reinstatement | 589–672 | 49–56 s | Fixture return, warm completion lights, exterior restoration |

Eight older `PHASE_...` markers remain at frames 1, 31, 61, 91, 121, 151, 181, and 211. They are legacy markers from the earlier sequence, not the active timing.

## Collection structure

| Root/group | Child collections and direct object counts |
|---|---|
| `00_Site_&_Context` | Building shell/stacks 52; garages 3; side sewer 5; staging 1 |
| `01_Structural_Base` | Slab 5; footings 4; precast walls 13; soil 1; stud partitions 24 |
| `02_Existing_Conditions_&_Demo` | Trench cutters 41; drywall cutouts 12; existing cast iron 33; retained ABS 2 |
| `03_New_Plumbing_DWV` | Firestop/sleeves 12; ABS branches/traps 34; under-slab mains/laterals 13; stack tie-ins/cleanouts 44 |
| `04_Trench_Backfill_&_Slab_Pourback` | Pourback 41; general backfill 41; bedding 82; rebar 3; vapor barrier 41 |
| `05_Wall_&_Floor_Substrates` | Gypsum patches 28; radiant coils 2; epoxy primer 4; nailers 24; waterproofing 4 |
| `06_Interior_Finishes_&_Fixtures` | Callout text 5; cabinets 16; fixtures 60; protection 8; unit finishes 3/4/3/2 |
| `ANIM_ABS_Extrusion` | 91 animated mesh segments |
| `ANIM_Construction_Effects` | 147 objects: cut effects, protection, grid, studio lights, camera, and target |
| `ANIM_Water_Test` | 47 cyan curve duplicates |
| Photorealistic groups | Architecture 670; fixtures/details 1,176; landscape 166; cameras/lighting 6 |
| Miscellaneous | One additional collection containing 3 objects |

## Plumbing and animation structure

- New ABS: 47 source curves across two DWV collections. These remain editable route references but are hidden as render objects.
- Visible installation geometry: 91 mesh segments generated from the coordinated routes.
- Demolition: 31 source cut curves and 54 animated cut-line mesh segments.
- Existing piping: 33 objects — 31 curves and 2 meshes — with rust material and demolition fades.
- Water testing: 47 curve duplicates with separate animated cyan emission.
- Restoration: 41 general-backfill, 82 bedding, 41 vapor-barrier, and 41 pourback objects.
- No curve-trim drivers remain; geometry growth replaces animated `bevel_factor_end`.

## Materials, camera, and lights

- 78 material actions.
- 74 animated fade mixes for architecture, partitions, slab, fixtures, finishes, interior details, and existing cast iron.
- Separate animated materials control ABS installation color/emission and the hydrostatic pulse.
- 2,885 objects have object-level actions: 2,883 use `hide_render`, 450 use scale, and 66 use location.
- Active camera: `Agency 4D Camera`, with depth of field, animated location/lens, and `TRACK_TO` targeting `CAMERA_Target`.
- Seven cameras exist in total.
- Seven lights have animated energy, including the studio rig and four warm completion lights; world background strength is animated.

## Important implementation notes

The file is timeline-driven rather than organized into eight separate phase scenes. The HUD and final 24 fps motion are produced outside Blender; the native scene is 12 fps at 640×360. The single scene’s VSE contains no strips.
