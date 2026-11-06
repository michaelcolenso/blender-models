# Highland | PEX-A riser and main replacement (proposed, illustrative)

**PASS** — 3/3 checks

## Basis of record
- Built from: RL-REVISED Highland Condos Plumbing 10-29-07 (P2.01-P2.07, P3.02); A2.03 and A3.11 (04-02-07); S3.8 (04-02-07)
- Record kind: `design_intent` · field verification: `not_verified`
- Note: Proposed parallel install and stack-by-stack cutover. Every new element is assumed; nothing here is engineered.
- ⚠️ Geometry reflects the record above, **not** a confirmed built condition.

## Provenance
- confirmed: 0
- provisional: 0
- assumed: 407

## Checks
- PASS CW network components (new): expected 1, got 1 (graph check of the proposed PEX-A network)
- PASS HW network components (new): expected 1, got 1 (graph check of the proposed PEX-A network)
- PASS HWC network components (new): expected 1, got 1 (graph check of the proposed PEX-A network)

## Source conflicts
- **Units 106/107 drop HW size**: modeled per `P2.03` (sources: P2.03 R1 plan: 1-1/2 in HW, P3.02 riser diagram: 1-1/4 in HW). Same issue (10-29-07). Resolved by owner decision 2026-11-06: 1-1/2 in governs (P2.03), as modeled.
- **P3.02 stack numbers vs plan locations**: modeled per `P2.03-P2.07` (sources: P3.02 riser diagram (NTS), P2.03-P2.07 riser markups). Plan stacks are named A-F by location. F is matched to P3.02 '03' because both stop one floor short of R5. A, B, C and E are not matched to 01, 02, 04 and 05.
- **04 stack R1 branch**: modeled per `P3.02` (sources: P3.02: 04 stack has four branch groups, highland/water spec: R1 continuation unresolved). This model gives A, B, C and E an R1 branch each (20 groups). P3.02 implies 19: one of the four has no R1 branch, and which one is unresolved.

## Assumptions
- `ceiling_takeoff_in` (parameter): Floor + 108 in. P3.02 draws each branch group at the ceiling of the floor it serves; the Unit 107 study (highland/water) holds overhead CW at floor + 108 in. No document gives riser takeoff heights.
- `main_elev_ft` (parameter): 350.5 ft. P1 garage main hung below the R1 slab; S3.8 gives the drop-slab soffit at 351.21 ft near Unit 107. The garage soffit along the main is not established.
- `triple_spacing_in` (parameter): 4.0 in c/c. Riser symbols are not drawn to scale.
- `branch_stub_in` (parameter): 24.0 in. Branches continue per the typical unit plans (P4.0x), which this model does not trace. Stub direction points away from Corridor 108.
- `existing_material` (parameter): CPVC, per the owner's report of failing CPVC (highland/installation). P0.01 material notes were not used; installed material is not field verified.

## Visual review
**NOT RECORDED.** Passing checks is not a visual review. Look at the review renders and overlays, then record the result in the spec's `review:` block.

## Renders
- `proposed-iso.png`
- `proposed-plan.png`
- `proposed-south.png`
- `proposed-east.png`

Pipes in review renders are drawn at 2.0x outside diameter for legibility.
