# b101-review

**What it produces:** an acceptance review of the recovered B-101 demolition model (v4), plus a v4.1
revision that fixes the two blockers found in review. It is an experimental workflow exercise: results are
model checks and a visual review, not a coordination sign-off. Images and the acceptance table are in
[../../deliverables/b101-review](../../deliverables/b101-review/).

**Sources:** the recovered v4 package in [vdc-recovery/snapshots/b101](../vdc-recovery/snapshots/b101/).
Its route basis is P1.01/P1.02/P3.1 and the 10-16-2026 Addendum, all plan-traced and FIELD_VERIFY (198
tagged objects). The contract PDFs are not in the repo, so this review checks the model against its own
package and checklist, not against the drawings.

## How it works

`build.py` copies the snapshot to `build/meydenbauer-b/b101-review/pkg`, applies
[`b101_v4_1.patch`](b101_v4_1.patch), then runs the package's own scripts with bpy:

1. strict build of passes 1–3 (`--fail-on-warning`), save, and eight keyframe renders on CPU Cycles;
2. `verify_saved_blend.py` on the reopened file;
3. `extended_runtime_qa.py` (drivers, slab Boolean versus cutter union on a 3-inch grid, no-demo envelope
   overlap, fitting counts, saved routes).

The snapshot is never edited, so the recovery hashes `vdc-recovery` checks stay valid.

## What the patch changes (v4 → v4.1)

| Change | Why | Basis |
|---|---|---|
| Clip trench cutters at the south edge of `B101_DEMO_PriorRepair_NoDemo_Envelope` (y = 27.5 ft) | v4's cutter end extensions (0.55 × trench width) carried `TrenchCutter_B101_001` and `_008` about 0.9 ft past the prior-ABS tie (23.25, 27.4) into the no-demo area: 38 of 6,400 grid samples, ~2.4 sf | **Assumed**: the envelope edge is the cut limit. The envelope itself is a broad, unsurveyed FIELD_VERIFY box |
| Add `MEYD_B101_REVIEW_CAMERA` (orthographic, framed on B-101) as the scene camera; hide upper-floor slabs, east/north walls, garages, context stacks and soil mass from **renders only** | `MEYD_ISO_CAMERA` looks through the upper floors, whose X-ray material goes opaque after Phase 1 by design, so frames 038–089 showed only a grey slab | Presentation only; no geometry change. `MEYD_ISO_CAMERA` is kept |
| Runner: render with Cycles first | EEVEE needs libEGL and aborts headless here | Environment only |

## Run

```bash
uv run bm run meydenbauer-b/b101-review build    # bpy, ~4 min on CPU
uv run bm run meydenbauer-b/b101-review check    # CI: patch applies, patched scripts compile (no bpy)
```

## Limits

- Built and checked on Blender 5.0.1 (bpy module). The package was written for 4.3.2; it ran without changes
  beyond the patch, but other 5.x differences were not looked for.
- The envelope clip only handles its south edge, the only edge the B-101 route reaches. A route change that
  approaches another edge would need the clip extended.
- Annotation text in the renders overlaps and is hard to read; excavation/vapor overlays persist at frame
  089, so it is a phasing view, not a literal empty trench. Neither was changed.
- Route calibration (checklist C) was not re-checked against the drawings; the QA boards and overlays it
  names were not recovered.
