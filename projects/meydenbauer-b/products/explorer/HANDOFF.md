# B-103 Explorer continuation — 2026-11-15

Continued from the November 14 P2.1 architectural walkthrough on `aede91b`.
This is the current Explorer handoff; B-101 v4 notes under `vdc-recovery/snapshots/`
remain historical records.

## Completed in this continuation

- Reproduced an initial walk view dominated by a nearby wall in Chromium.
- Entry now searches for a safe spawn facing a clear 3 m walking path within
  the navigation guard. It respects doors left closed on a previous visit;
  confined spaces fall back to a safe spawn.
- Walk camera uses a 65° field of view and restores the orbit setting on exit.
- A container ResizeObserver keeps the canvas and camera aspect synchronized
  when entering/leaving the mobile walk layout.
- Added regression cases for clear entry paths, closed-door reentry and
  confined-space fallback.

## Validation

- `uv run --no-sync bm run meydenbauer-b/explorer check`: PASS, 17 Node tests,
  canonical state and timeline projection match their generators.
- `uv run --no-sync bm check`: PASS, 94 Python tests and 40 subtests;
  specs, metadata and Markdown links pass. Four existing Blender API
  deprecation warnings.
- `uv run --no-sync bm check-products`: PASS, 10/10 products.
- Chromium desktop (1440 × 1000): visually reviewed orbit, walk and X-ray;
  exercised timeline at day 7 and return to orbit. No page JavaScript errors.
- Chromium touch emulation (390 × 844): walk canvas matches its 390 × 380
  container; exit restores the 312 × 360 orbit container. Timeline remains
  usable while walking. This is emulation, not a physical-device test.

Review captures and temporary browser scripts are local build artifacts under
`build/meydenbauer-b/explorer-review/`; regenerate them when the app changes.
Run the app from the repository root with
`uv run --no-sync python -m http.server 8765`, then open
`http://localhost:8765/projects/meydenbauer-b/products/explorer/index.html`.

## Remaining work

- Open illustrative door leaves can cross the initial view. Their swung panels
  do not participate in physical collision; only closed door gaps block walking.
  Check door usability and whether closing a door can overlap the player before
  claiming a physical door simulation.
- The navigation guard still comes from plumbing extents, not verified B-103
  apartment boundaries. Any boundary replacement needs source-backed room/unit
  attribution before changing the guard.
- Heights, hinges and swings remain illustrative; construction phases remain
  canonical schematic overlays. Stage-specific demolition/installation meshes,
  gravity, stairs and trench-edge collision are still absent.
- Repeat the five professional-review tasks in
  [the reference acceptance](../../../../docs/MEYDENBAUER_REFERENCE_ACCEPTANCE.md#10-acceptance-h--explorer-usability)
  with a reviewer. Automated/browser checks do not establish that acceptance.

Changes are local and uncommitted. No publication or deployment was performed.
