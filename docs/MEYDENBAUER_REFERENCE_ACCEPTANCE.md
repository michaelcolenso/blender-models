# Meydenbauer Reference Acceptance

Status: Proposed v0.1
Purpose: Golden-reference acceptance contract for the Construction Intelligence Engine (CIE)

## 1. Why this exists

Architecture is cheap to describe. This document makes it expensive to fake.

CIE is accepted only when it can demonstrate construction reasoning end-to-end on the existing Meydenbauer under-slab re-pipe without weakening the checks already present in the project.

The tests below are product tests, not merely unit tests.

---

## 2. Reference facts to preserve

At the time this acceptance contract was written, the current Meydenbauer deliverables report:

- four ground-floor units: B-101 through B-104;
- approximately 312.75 LF of modeled new under-slab ABS;
- four POC cleanouts/tie-ins;
- approximately 105 LF of 2-inch, 33 LF of 3-inch and 175 LF of 4-inch pipe;
- S1 slab cut: 590 SF;
- S2 slab cut: 686 SF;
- S3 reference slab cut: 991 SF;
- allowance reference: 700 SF;
- S2 base excavation at the 3.5 ft POC-invert assumption: approximately 82.3 bank CY;
- 30 fixture/stack connections in the S2 pit assumption;
- B-104 is the largest unit by modeled pipe length and S2 slab area;
- the current strawman unit-by-unit sequence totals 81.5 working days before holidays and preconstruction;
- current unit order is B-103 -> B-102 -> B-101 -> B-104;
- the existing sequence build includes 92 unit-sequence checks and 44 framing checks.

These values are regression fixtures, not license to hard-code the result.

---

## 3. Acceptance A — Identity and evidence

### Test A1 — Select a modeled pipe

Given a known B-104 pipe element in the canonical state:

- it has a stable `cie_id`;
- Blender geometry carries that ID;
- exported GLB geometry can resolve that ID;
- Explorer selection resolves to exactly one canonical element.

**Pass:** all surfaces agree on identity.

### Test A2 — Trace to source

From the selected pipe, the user can navigate to its claim(s) and evidence locator(s), including the relevant P1.02 reference.

**Pass:** the source can be identified without searching README prose or source code.

### Test A3 — Separate plan and elevation confidence

The selected pipe can express different provenance states for plan position, size and elevation.

**Pass:** the UI does not imply that because a pipe is precisely drawn in 3D its elevation is field-verified.

---

## 4. Acceptance B — Quantity reconciliation

### Test B1 — Total pipe

Compile baseline state from source pipeline.

**Pass:** total new ABS reconciles to the current takeoff within existing project tolerance, approximately 312.75 LF.

### Test B2 — Unit totals

Reconcile B-101 through B-104 independently.

**Pass:** no project-level total can pass by offsetting errors between units.

### Test B3 — Pipe sizes

Reconcile 2-inch, 3-inch and 4-inch totals independently.

### Test B4 — POCs

**Pass:** exactly four intended POC cleanout/tie-in entities are represented in the reference state.

---

## 5. Acceptance C — Scenario reasoning

### Test C1 — S1

Apply S1 assumptions.

**Expected reference:** approximately 590 SF slab cut.

### Test C2 — S2

Apply S2 assumptions: S1 plus the modeled working pits at the configured connections.

**Expected reference:** approximately 686 SF slab cut, approximately 14 SF below the 700 SF allowance.

### Test C3 — S3

Apply the documented reference deep-trench scenario.

**Expected reference:** approximately 991 SF slab cut, approximately 291 SF above the 700 SF allowance.

### Test C4 — Explain delta

Ask the engine why S3 differs from S2.

**Pass:** response traverses the actual dependency chain rather than returning a canned sentence. It identifies the changed depth condition, the widening rule, affected trench geometry and resulting slab-area delta.

### Test C5 — No duplicate truth

Change an approved scenario input.

**Pass:** Explorer quantity, generated report and film annotation derive from the new state without manually editing three separate values.

---

## 6. Acceptance D — Spatial constructability

### Test D1 — Footing relationship

Select the footing/trench interaction issue.

**Pass:** affected trench segments highlight spatially and the inspector distinguishes record-drawing geometry from assumed pipe depth.

### Test D2 — Screening language

**Pass:** no UI or film copy upgrades the footing proximity analysis into an unsupported structural conclusion.

### Test D3 — B-104 conflict

Select the B-104 previously-replaced-run issue.

**Pass:** the conflicting evidence/interpretations and affected modeled run are linked in one review path.

---

## 7. Acceptance E — Construction sequence

### Test E1 — Existing before demolition

At the beginning of a unit sequence, existing work is present and new ABS is not installed.

### Test E2 — Demolition before new work

**Pass:** conflicting existing pipe is removed before new ABS reaches installed state.

### Test E3 — Test before cover

**Pass:** the modeled test/hold state occurs before backfill covers the system.

### Test E4 — Cure before finishes

Where cure is modeled, finish restoration does not precede it.

### Test E5 — Final restoration

At sequence completion, temporary protection/logistics overlays are removed and intended fixtures/finishes are restored.

### Test E6 — Existing regression checks

**Pass:** the migration preserves or intentionally supersedes the current 92 unit-sequence and 44 framing checks. Any reduction requires a documented reason and replacement coverage.

---

## 8. Acceptance F — Occupied-building logic

### Test F1 — Unit isolation

During unit-by-unit sequencing:

- earlier units read complete;
- active unit reads under construction;
- later units read untouched.

### Test F2 — Service issue visibility

Temporary sanitary-service assumptions and the 5 PM restoration requirement are visible as construction constraints, not buried in a disclaimer.

### Test F3 — B-102 WC uncertainty

The absence/uncertainty of the B-102 WC connection is represented as an issue.

**Pass:** the model does not fabricate a confident connection solely to make the animation tidy.

---

## 9. Acceptance G — Logistics

### Test G1 — Haul path

For an active unit, show the associated assumed entry and haul route to staging.

### Test G2 — Quantity relationship

The logistics calculation is connected to excavation/spoil quantities rather than a hand-entered trip count.

### Test G3 — Scenario sensitivity

If excavation volume changes under a scenario and the trip model depends on that volume, the calculated logistics quantities update.

---

## 10. Acceptance H — Explorer usability

Give a construction professional who has not worked on the code these tasks:

1. Find B-104's largest new waste run.
2. Determine what about it is documented versus assumed.
3. Identify the largest unresolved quantity risk.
4. Compare S2 and S3 to the 700 SF allowance.
5. Explain why S3 crosses the allowance.

### Pass criteria

- all five tasks completed without source-code access;
- no coaching about hidden UI controls;
- reviewer can cite the underlying evidence/assumption category in their explanation;
- reviewer does not mistake a scenario for a verified field condition.

Record completion time and confusion points. Optimize for comprehension, not clicks.

---

## 11. Acceptance I — Film

### Test I1 — Silent comprehension

Play the flagship film muted to a construction professional.

**Pass:** they can describe the broad scope, sequence and central depth/allowance risk.

### Test I2 — Numerical integrity

Extract every decision-relevant number displayed in the film.

**Pass:** each resolves to the canonical state used for that build.

### Test I3 — Assumption integrity

**Pass:** assumed/provisional conditions are not presented visually or verbally as verified field facts.

### Test I4 — Decision ending

**Pass:** the film ends on the material project decision/risk, not a generic beauty shot.

### Test I5 — Clean master

**Pass:** a clean master exists so editorial copy/HUD changes do not require rerendering unchanged 3D imagery.

---

## 12. Acceptance J — Failure behavior

### Test J1 — Broken reference

Delete or corrupt a referenced element/evidence ID in a test fixture.

**Pass:** validation fails loudly.

### Test J2 — Unsupported confirmed claim

Mark a decision-critical assumption as `confirmed` without evidence.

**Pass:** provenance lint fails.

### Test J3 — Quantity mismatch

Perturb a modeled pipe length beyond tolerance.

**Pass:** reconciliation fails and identifies the affected quantity/element set.

### Test J4 — Sequence violation

Force backfill before test completion in a fixture.

**Pass:** construction invariant fails.

---

## 13. Acceptance K — Generalization

After Meydenbauer passes, run Highland through the same semantic kernel.

### Pass

- core identity/provenance/element/relationship/quantity/activity/issue concepts survive;
- project-specific domestic-water concepts fit through typed extensions/attributes or justified schema additions;
- no core field is named after Meydenbauer units, waste piping, slab trenches or the 700 SF allowance;
- changes prompted by Highland improve the abstraction rather than special-case it.

---

## 14. Release gate

CIE v1 SHALL NOT be called complete because:

- the schema validates;
- the Explorer looks polished;
- the film looks cinematic;
- Blender renders successfully;
- the code is generalized.

It is complete when the following demonstration succeeds in one coherent system:

> Select a real construction element, trace it to evidence, expose the assumption that controls a material risk, change that assumption, propagate the consequences through geometry and quantities, understand the construction/logistics impact, and communicate the same result through an interactive model, a report and a film.

That is the reference standard.