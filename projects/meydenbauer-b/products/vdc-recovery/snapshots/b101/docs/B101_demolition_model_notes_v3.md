# B-101 Detailed Demolition Model — v3

## What is modeled

The v3 Blender generator adds a source-grounded selective-demolition sequence for Unit B-101 on top of the calibrated B-101 plumbing route. It separates **remove/reinstall access work**, **finish strip-out**, **wall/stack exposure**, **slab sawcut**, **slab lift-out**, **excavation/vapor-barrier exposure**, and **existing cast-iron removal**.

The retained prior 4-inch ABS kitchen/dining repair is explicitly modeled as a **protected no-demolition zone**. The model does not generate trench demolition along that retained route.

## Demolition subphases

0. Protection / containment
1. Remove and store access items for reinstallation
2. Strip finishes needed for access
3. Open walls / expose carriers and vertical connections
4. Sawcut slab
5. Lift slab chunks / expose existing vapor barrier
6. Excavate and expose existing cast iron
7. Cut/remove cast iron and leave trench ready for new ABS

The `PHASE_CONTROLLER` now includes `Demolition_Subphase` (0–7) and timeline markers within Phases 2 and 3.

## Modeled B-101 access quantities

These are geometry QA values, **not contract payment quantities**. Field measurement governs.

- Replacement route length used for slab access: **70.5 LF**
- Raw slab-cut area before overlapping segments are reconciled: **119.5 SF**
- Plan-union slab-cut area from the calibrated controls: **104.8 SF**
- Raw finish-access strip area before overlap: **154.7 SF**
- Plan-union finish-access strip area: **129.2 SF**
- Slab thickness modeled: **5.5 in** (midpoint of documented 5–6 in range)
- Exterior replacement limit: **18 in beyond east foundation face**

The Addendum B-101 finish allowances (253 SF PT-6, 25 SF PT-7, 105 SF PT-8, 60 SF C-1) are carried as **reference metadata/callouts**, not forced into geometric demolition extents because the documents require field measurement of actual replacement areas.

## Important source-driven distinctions

- Toilets, tubs/showers/enclosures, lavatory cabinets, and laundry appliances are generally modeled **remove-and-reinstall**, not discard.
- The kitchen cabinet access is modeled **conditional** in B-101 because P1.01 identifies the prior kitchen/dining ABS repair as a no-demolition area; remove/reinstall only if field access actually requires it.
- Existing cast iron is modeled for **complete removal**. Abandonment is not represented as the default.
- Existing vapor barrier is modeled as **expose / identify / preserve**, with new vapor-barrier restoration handled later.
- Foundation/structural crossing is a **field-verify / no-cut warning volume**; the model does not authorize structural cutting.

## Static verification

- compile_source_exists: **PASS**
- demo_subphase: **PASS**
- prior_no_demo: **PASS**
- remove_reinstall: **PASS**
- slab_chunks: **PASS**
- vapor_preserve: **PASS**
- ci_reclass: **PASS**
- boolean_sequenced: **PASS**
- generic_b101_temp_skipped: **PASS**
- generic_b101_cutout_suppressed: **PASS**

Python compilation also passed. Blender dependency-graph/Boolean/driver execution still requires an actual Blender run.
