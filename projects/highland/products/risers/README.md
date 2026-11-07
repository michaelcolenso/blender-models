# Highland domestic-water risers and mains

**What it produces:** two separate models of the building's domestic water distribution, from the P1 garage
main through the R1 Corridor 108 header to every riser and floor takeoff up to R5:

- **existing** (`risers-existing.spec.json`): the system as drawn in the October 2007 plumbing set;
- **proposed** (`risers-proposed.spec.json`): a PEX-A replacement installed alongside the live system, then cut
  over one stack at a time. Every proposed element is **assumed**, and none of it is engineered.

Each spec builds to a `.blend`, a `.glb` (with `cie_id`, `cie_status`, `cie_system`, `phase` on every object) and
four labelled review renders. Deliverables: [../../deliverables/risers](../../deliverables/risers/README.md).

**Illustrative, not a contract document.** Drawing-traced, not a survey of installed piping.

## Sources

Registered in [source-manifest.json](source-manifest.json). The PDFs stay in `projects/highland/sources/`.

| Document | Used for | Status in the model |
|---|---|---|
| RL-REVISED Highland Condos Plumbing 10-29-07, P2.01–P2.07 | Riser positions (vector markups), main and header routes (linework) | XY **provisional**, ±12 in at risers, ±18 in on runs |
| same set, P3.02 riser diagram (NTS) | Stack topology, branch groups, pipe sizes | sizes **confirmed** where labelled; never scaled |
| A2.03 (04-02-07) grid dimension strings | Registration of every P2.0x sheet | grid **confirmed**; fit residual ≤ 0.28 in |
| A3.11 (04-02-07) | Floor elevations P1 342.00 … R5 394.25 ft | datums **confirmed** |
| S3.8 (04-02-07) | R1 drop-slab soffit 351.21 ft (bounds the garage main) | reference only |

How the trace works:

- The plumbing sheets carry vector PDF markups that follow the sheet legend: green "continuous riser or riser
  going up", orange "riser going down", and cyan, magenta and lime for CW, HW and HWC.
- `extract.py` finds the grid bubbles on each sheet and fits them to the A2.03 dimension strings. Every P2.0x
  sheet comes out at 0.750 pt per inch (true 1/8" scale). It then transforms each riser box into grid inches
  (x east of grid 7, y north of grid E).
- `takeoff.py` averages the boxes at each stack across floors. Stacks agree within 2–8.5 in floor to floor.
  Crops at every stack and floor are in [source-review/](source-review/) so the trace can be checked without
  the PDF.

## What is modeled (existing)

- **P1 garage main** 4" CW, 3" HW, 1½" HWC from the plant tie, east along the garage ceiling, then up at the
  main riser. CW in the garage is heat traced and insulated (P2.02 note).
- **R1 header** 3" CW/HW, 1¼" HWC, running north–south in the Corridor 108 ceiling, with balancing and
  isolation valves at each stack base (P3.02 symbols; valve types not reviewed).
- **Five triple stacks** A, B, C, E and F, plus a **1" CW hose-bibb riser** D:
  - Sizes step from 2"/2"/¾" to 2"/1½"/¾" to 1"/1"/½" per P3.02.
  - A, C and E offset at the R4 ceiling (P2.06 DN/UP pairs).
  - F stops at R4.
- **Branch groups:** 24 floor branch groups (stubs; the unit routing continues per P4.0x and is not traced
  here), slab penetrations at every floor, and the 1½" drop to Units 106/107 (continued in
  [highland/water](../water/README.md)).

## What is assumed

- **Pipe elevations.** No drawing gives them. Floor takeoffs sit at floor + 108 in, matching the Unit 107
  study. The garage main sits at 350.5 ft.
- **Separation.** CW/HW/HWC run at 4 in spacing.
- **Branch stubs.** 24 in long, pointing away from the corridor.
- **Existing material.** CPVC, per the owner's report; not verified.
- **Context.** The slab outlines are the grid extents, not the real slab edges.
- **Proposed design.** The PEX-A routes are offset 10 in from the existing ones; chase and ceiling space is not
  verified. Sizes are the same nominal as existing, pending engineer resizing, because PEX-A has a smaller
  bore. The 4" CW main is **copper** (owner decision 2026-11-06, type not specified), because PEX-A is not
  made above 3".
- **Proposed work items.** Openings (one 24 × 96 in chase opening per stack per floor, plus a 24 in corridor
  ceiling strip), firestops, riser clamps, cutover ties, new floor isolation valves and the stack order are
  illustrative.

## Flags (unresolved)

1. **Units 106/107 drop HW:** P2.03 labels 1½", P3.02 shows 1¼" (same issue date). **Resolved** (owner,
   2026-11-06): 1½" governs, as modeled.
2. **Stack numbers:** P3.02's 01–05 are not tied to plan locations. Only F ↔ 03 is matched (both stop at R4).
3. **04 stack R1 branch:** P3.02 implies 23 branch groups. The model has 24 because which of A/B/C/E lacks an R1
   branch is unknown.
4. **R4 offsets:** routed as straight runs between the DN and UP boxes. The real offset route is not drawn on the
   markups.

## Photoreal work sequence

`photoreal.py` renders the R1 Corridor 108 header in five phases, each from two cameras (wide and detail):
before, open (protection plus a 24 in ceiling strip), install (PEX-A alongside the live CPVC), cutover (test
gauge; the existing header cut and capped north of the C branch) and restore. The pipe routes, sizes and
the C and D branch takeoffs come from the two specs, clipped to one 32 ft corridor bay.

Everything else in the scene is **assumed** and illustrative:

- **Corridor geometry:** 6 ft wide (the A2.03 label), centred on the header, with an 8'-6" ceiling and a 10 in slab.
- **Finishes and fittings:** finishes, doors, sconces, hangers at 48 in, a continuous PEX support channel,
  ProPEX-style tees, a firestop at the corridor wall, floor protection, the ladder and the work light.
- **Not shown:** ceiling framing above the board.

The finishes are procedural, so no textures are downloaded. No site photos will be used (owner, 2026-11-06),
so the carpet, wall paint, doors, lighting and ceiling type stay assumed and generic. Each still carries a
phase caption and the "illustrative, not a contract document" strip.

- CPU preview (this laptop or CI runner): `uv run bm run highland/risers photoreal`, 1280 × 720, 64 samples.
- Full quality on RunPod: `bash projects/highland/products/risers/runpod_photoreal.sh all`, 3840 × 2160 at
  512 samples, plus the `.blend`.

## Run

```bash
uv run bm run highland/risers extract    # needs the plumbing PDF in sources/ (restore notes in source-manifest.json)
uv run bm run highland/risers takeoff    # specs + 12 document checks (bpy-free)
uv run bm run highland/risers build      # bpy: .blend, .glb, review renders, reports in build/highland/risers/
uv run bm run highland/risers photoreal  # CPU preview stills of the work sequence (build/highland/risers/photoreal/)
uv run bm run highland/risers package    # review and photoreal JPEGs, reports into the deliverable folder
uv run bm run highland/risers check      # what CI runs: regenerate both specs, no diff
```
