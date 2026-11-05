# B-101 Demolition Fittings / Cut Locations — v4

## Scope added
This revision extends the calibrated B-101 selective-demolition model with fitting-level demolition objects while preserving the prior ABS repair zone.

### Existing DW fittings
- 10 modeled junction fitting bodies on the demolition network.
- Junction geometry is modeled as wye / combination-wye / sanitary-tee style coordination geometry according to the connected plan topology.
- Exact legacy fitting type is tagged `FIELD_VERIFY` because the bid drawings show routing/topology but do not identify every concealed existing fitting.
- 7 plan-derived bend assemblies are modeled at actual route-direction changes. The calibrated routes produce approximately 43–45 degree turns at these locations.

### First-floor traps
Seven demolition/coordination trap objects are modeled:
1. Upper bath lavatory — left
2. Upper bath lavatory — right
3. Upper shower
4. Lower tub/shower
5. Lower lavatory
6. Laundry
7. Kitchen — conditional coordination object because the B-101 kitchen/dining under-slab ABS repair is protected and its exact repair transition remains field-verify

Trap geometry is deliberately coordination-level. The Scope of Repair requires first-floor p-traps to be included, but the documents do not establish surveyed trap elevations or exact legacy manufacturers/configurations.

### Wall-hung toilet carriers / flanges
Two existing carrier assemblies are modeled at the calibrated B-101 WC locations. Each includes:
- carrier frame rails
- crossbars
- generic concealed carrier body
- 4-inch waste outlet
- wall flange / escutcheon-style ring

The geometry is explicitly tagged generic because the Scope states that existing wall-mounted water closets are of various manufacture.

### Pipe cuts and temporary support
Seven cut/disconnect locations are represented:
- WC North 4-inch vertical: model target 40 inches above slab
- WC South 4-inch vertical: model target 40 inches above slab
- Upper wet-core 3-inch vertical: model target 36 inches above slab
- Lower wet-core 3-inch vertical: model target 36 inches above slab
- Laundry 3-inch vertical: model target 36 inches above slab
- prior-ABS / existing-CI tie: plan-calibrated disconnect, final as-found location field verify
- exterior 6-inch lateral: disconnect at the documented 18-inch replacement limit beyond the foundation

The vertical targets use `max(36 inches, 10 x nominal pipe diameter)` as a coordination target based on the demolition/vertical-exposure requirements. Final cut elevations remain `FIELD_VERIFY` and subject to code / Engineer direction.

Each modeled vertical cut includes temporary support rings above and below the cut to represent the SOR requirement to support piping around cut locations.

## Important protection boundary
The laundry branch lands at the calibrated prior-ABS / existing-CI interface. v4 does **not** invent a removable cast-iron wye inside that protected prior repair. Instead it creates `B101_DEMO_Laundry_PriorABS_Interface_FIELD_VERIFY` and relies on field verification before demolition.

## Source basis
- Exhibit A, P1.01 — B-101 demolition / prior repair remain limits
- Exhibit A, P3.1 — B-101 enlarged plumbing topology
- Addendum #1 Scope of Repair pages 7–10 — remove/replace existing DW piping/fittings, first-floor p-traps, wall-hung WC carriers, vertical exposure, approved wye/combination-wye + 1/8 bend / sanitary-tee fittings, cleanouts, and support above/below cuts
- Section 02 41 19 Selective Demolition — systematic selective demolition, neat cutting, protection of construction to remain

## Verification performed here
- Python AST parse: PASS
- `python -m py_compile`: PASS
- Static presence checks for fitting builders, carriers, P-traps, cut/support assemblies, prior-ABS tie, exterior 18-inch cut, and laundry field-verification interface: PASS
- Blender runtime evaluation: NOT RUN in this environment because no Blender executable is installed
