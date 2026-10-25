# Meydenbauer B 4D cutaway — design

Date: 2026-10-25
Status: awaiting review (no implementation until this file is approved)
Repo: `michaelcolenso/blender-models`
Base: `origin/main` at `e266b3d` (PR #21 already merged: `hide_vanished`, vanity merge, wide-shot crop checks, clean master + `--from-video` HUD)
Film: `projects/meydenbauer-b/animate.py` on top of `realism.py` / P2.1 walls

## 1. Problem

The 1080p30 RunPod master (PR #20) uses `ghost_material()` on `Walls (P2.1)`, headers/sills, and glazing. Alpha-blended white walls plus furniture stack transparent bounces; PR #21 hid vanished objects so the 2 s / 30 s black patches are gone, but the walls still read as a milky ghost instead of an executive poché model. Under-slab trench and ABS compete with vertical clutter.

This slice restyles **existing** P2.1 walls and plumbing fixtures. It does not add Geometry Nodes, a new camera edit, or a new takeoff.

## 2. Goal

One 32 s / 30 fps / 960-frame master where:

- Partition walls are **opaque clay**, clipped at **32 inches AFF**, with a **static dark poché cap**.
- Non-plumbing furniture does not render.
- Toilets, vanities, tubs, showers stay solid 3D and keep the existing Phase 02 lift / Phase 08 drop.
- Vertical waste/vent stacks stay full height (not clipped).
- HUD stays a 2D overlay on a **clean** 3D plate (PR #21 `*-clean.mp4` / `--from-video`).

Audience for this master: forensic/method readability. Estimator / board / resident copy is HUD-only and out of this spec.

## 3. Non-goals (explicit)

Out of this slice, each needs its own spec later:

- Live Boolean slicer or Geometry Nodes `GN_UnderSlab_RePipe`
- Phase 02 wall-height raise to 6'-0" for zip-wall theatre
- 2D CAD floorplan decal on the wood (needs a committed P2.1 raster; sources/ is gitignored)
- 3-layer sub-slab plinth (concrete / aggregate / native soil)
- 4-shot camera switcher, saw-kerf laser, vapor-barrier unroll, sonar scan, 3D city-test badge
- 60 fps, 4K, EEVEE Next
- Freestyle as a hard requirement (see §6.3)

Do not invent Ram-Board, zipper graphics, or beds that P2.1 does not already instance. If a collection does not exist at build time, skip it; do not fabricate a mesh to satisfy this document.

## 4. Provenance

| Layer | Source | Status | This slice |
| --- | --- | --- | --- |
| Walls | P2.1 double lines | provisional | restyle + clip; do not move plan |
| Wall height 9'-0" | assumed (P2.1 CH tags are room ceilings, not wall construction) | assumed | clip at 2'-8"; do not change `WALL_TOP` in `realism.py` |
| Clip height 32" AFF | this film design, not a drawing | assumed | label in HUD disclaimer |
| Tubs/showers | P2.1 symbols | provisional | keep 3D, solid porcelain |
| Toilets / vanities | P2.1 / illustrative props | mixed | keep 3D if the object exists after `cleanup()` |
| Dust walls 6-mil | typical practice | assumed | leave as-is; do not raise architectural cut |
| Furniture (beds, sofas, tables) | illustrative | assumed | hide from render |
| Pipe / trench / slab | existing takeoff | unchanged | do not rebuild |

HUD disclaimer must include: walls clipped at 32" AFF for readability; clip is not a construction joint.

## 5. Architecture

Keep the existing pipeline. Do not add a second builder.

```
realism.py --no-render     -> occupancy .blend (unchanged geometry)
animate.py build()         -> sequence: replace ghost_walls(), add cap, hide furniture
animate.py render          -> PNG sequence, no HUD (already true)
anim_finish.py             -> HUD on frames or --from-video clean master
```

All cutaway behaviour lives in `animate.py` (and a small helper next to it if the file needs a split). `realism.py` still builds full-height walls at `WALL_TOP = 9.0` ft so still-frame realism views stay intact.

### 5.1 Components

1. **`clay_wall_material()`** — replaces `ghost_material()`.
   - Principled: Base Color `#F4F5F7` → RGB (0.956, 0.960, 0.969), Roughness 0.85. If the Principled node has `Specular IOR Level`, set 0.2; if it only has a 4.x `Specular` socket, set that to 0.2; if neither exists, skip.
   - Opaque surface. **No Transparent BSDF on walls.**
   - `visible_shadow = True` (ghost currently turns shadows off; clay casts).

2. **Clip method: mesh split once at build**, not a shader clip and not a modifier Boolean.
   - Cut at `CLIP_Z = (32/12) * FT` meters.
   - Shader-level Z-clip is **not** used in v1 (it reintroduces transparent bounces). If bisect fails, delete faces whose vertices all sit above `CLIP_Z`; do not add a Transparent BSDF.

3. **Static poché cap** — object `Walls poché cap (32 in AFF)`, collection with the walls.
   - Built once from the same Shapely wall polygons `realism.py` already uses (`I["walls"]`), extruded as a thin slab: top = `CLIP_Z`, thickness = 0.75 in (visual cap, not a spec thickness).
   - Material `#1E242B` RGB (0.118, 0.141, 0.169), roughness 0.9, opaque.
   - Cap does not animate except it inherits unit-wide vanish if a whole unit is hidden (it should not vanish while walls are visible).
   - Openings: cap is the wall polygon minus door/window holes already in `SHELL["walls"][*].holes_ft`. If a hole is missing, the cap may cover a door; that is accepted for v1 and listed in checks as a count, not a fail.

4. **Edge crease (not Freestyle-or-bust)**
   - Primary: inset the cap outline 1.5 px-equivalent as a curve/mesh with material `#3A4654`, 0.5 in width in world, sitting 0.1 in above the cap. That is resolution-independent.
   - Do not enable Freestyle/LineArt in the render harness. If the inset edge is invisible at 1080p, thicken to 0.75 in. Do not add a Grease Pencil LineArt object in v1.

5. **`hide_non_plumbing_furniture()`**
   - Name/collection allow-list for **keep 3D**: toilets, vanities, tubs, showers, lavs (objects produced by `realism.fixtures()` and any remaining `Props and fixtures` that match those kinds).
   - Everything else in `Props and fixtures (illustrative)` plus any object whose name starts with bed/sofa/table/chair/rug: `hide_render = True` for the whole sequence.
   - Do not delete; still-frame realism views use the same .blend build path without this hide if they skip `animate.stage`.

6. **Porcelain on plumbing fixtures**
   - New material: Base `#FFFFFF`, Roughness 0.15, clearcoat if the 5.x socket exists else leave default.
   - Assign to fixture meshes that currently share wall/ghost or wood. Vanities already merged in PR #21 — assign porcelain to the wet-side material slot only; cabinet body stays wood if two slots exist, else whole vanity porcelain is acceptable.

7. **Risers**
   - Do not put the clip shader on riser objects. Optional: mix a facing-fresnel with the existing ABS/cast-iron. Strength cap 3.0 to avoid fireflies (same rule as water-test emission).

### 5.2 Preferred wall implementation (mesh split)

At `ghost_walls()` replacement time:

1. Take object `Walls (P2.1)`.
2. Bisect at Z = CLIP_Z (bmesh `bisect_plane`, clear inner = above).
3. Lower solid keeps clay material, opaque, no transparent shader at all.
4. Discard or `hide_render` the upper chunk (do not leave it in the view layer).
5. Build the cap from the bisect cut edges (filled) **or** from Shapely as in 5.1.3 — Shapely is preferred so openings stay consistent with P2.1.

Headers/sills/glazing: glazing above 32" is gone with the upper wall; below-sill remnants hide with furniture rules. Object `Door and window headers / sills` is mostly above 32" — hide_render for the whole object in the film.

`Ceilings` already hidden in `cleanup()`. Leave that.

### 5.3 Data flow

- Clip height is a named constant `CLIP_INCHES = 32` in `animate.py`. One place.
- No per-frame Boolean. No Geometry Nodes tree.
- `hide_vanished` from PR #21 still runs. Clay + split means vanished walls should already be hidden; do not reintroduce Transparent BSDF on walls.
- Render samples, device, HUD: unchanged. `runpod_animate.sh` already defaults to 30 fps.

### 5.4 Error handling / checks

Extend `validate()` (or the existing 14 sequence checks) with:

1. No material named `Architectural ghost (walls)` remains assigned.
2. Object `Walls (P2.1)` exists; its material is opaque clay (no Transparent BSDF in that node tree).
3. Object `Walls poché cap (32 in AFF)` exists; its Z top is within 0.5 in of CLIP_Z.
4. At least one plumbing fixture object is still `hide_render == False` at frame 1 and frame 900 (reinstatement window).
5. Existing framing checks from PR #21 stay (building inside frame, clear of HUD bands).
6. ABS length check 312.74 LF unchanged.

Fail the build (`--no-render` exit 1) if 1–3 fail. 4 is a warning printed, not a fail, because fixture names vary.

## 6. Testing

Local, before any GPU rental:

1. `env -u PYTHONPATH -u PYTHONHOME PYTHONNOUSERSITE=1` + blender-models venv.
2. `animate.py --fps 30 --no-render` — all checks green.
3. One-frame smoke at `--seconds 2,10,18,30 --res 0.4 --samples 16`. Look at the four stills: clay not ghost, cap visible, no black patches, fixtures solid in 02/08, trench readable at 10 s.
4. If smoke fails, fix; do not rent.

GPU (only after explicit spend approval):

5. Quote from `runpod_animate.sh bench` with **2 workers**, using returned `costPerHr` not the GPU list price.
6. Full 960 at 30 fps / 128 spp / OPTIX. Pull **clean** master + HUD. Terminate the pod.
7. `ffprobe` 1920x1080, 30/1, nb_frames=960, duration=32.0; `ffmpeg -f null` silent; `blackdetect` empty.
8. Spot-check t=1, 13, 17, 29 as in PR #20.

## 7. Spend

A shader/material change **requires a new 3D render**. HUD-only would not; this is not HUD-only.

Do not create a pod in the implementation of this spec. Implementation ends at green local smoke. Rental is a separate approval with a printed ceiling (`MAX_HOURS`) and `costPerHr`.

## 8. Files expected to change (when implementation is approved)

- `projects/meydenbauer-b/animate.py` — replace `ghost_material` / `ghost_walls`; add cap builder, furniture hide, porcelain, checks.
- `projects/meydenbauer-b/anim_finish.py` — disclaimer string only if it currently claims ghosted walls.
- `deliverables/meydenbauer-b/anim/README.md` — one paragraph on the 32" clip.

Not in this change: `realism.py`, `runpod_animate.sh` (unless a comment is wrong), Geometry Nodes, new collections in the occupancy model.

## 9. Risks

- Bisect on a large wall mesh can fail at openings. Mitigation: Shapely cap + delete faces with Z > CLIP_Z by vertex Z rather than bisect if bisect produces holes.
- Opaque clay will hide some trench in the far units if the camera sits low. PR #21 already refit wide keys; smoke at 10 s must show trench. If it does not, raise the clip to 42" in this same constant — do not invent a second clip height without changing this spec.
- Porcelain on a two-slot vanity: if the wood slot is missing, the whole vanity goes white. Acceptable.

## 10. Decision log

- 2026-10-25: first slice is cutaway + materials (user).
- Audience pick timed out → one 32 s master; HUD variants later.
- Wall method timed out → recommended shader/mesh split + static cap (not live Boolean, not realism.py rebuild). User then said **Go** on that design.
- Phase 02 6' exception: deferred.
- Floorplan decal: deferred.
- PR #21 merged on main before this spec was written; implementation bases on that, not a rebase.
