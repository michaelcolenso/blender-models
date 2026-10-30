# Construction Intelligence Specification

Status: Proposed v0.1
Reference implementation: 101 Meydenbauer, Building B
Repository: `michaelcolenso/blender-models`

## 0. Thesis

This repository is not primarily a collection of Blender scenes. It is an evidence-to-construction system.

Given drawings, specifications, scope documents, record information, field observations and explicit assumptions, the system SHALL produce an inspectable construction state from which geometry, quantities, scenarios, schedules, logistics, reports, web experiences and films can be generated.

The core product is not a render. The core product is a defensible chain:

`evidence -> claim -> element -> relationship -> quantity -> activity -> decision`

Blender is one renderer of that state. A spreadsheet, GLB, browser, report and film are other renderers. None is independently authoritative.

The system exists to answer five questions about anything it shows:

1. What is it?
2. Where did we get it?
3. How certain are we?
4. What does it affect?
5. What changes if the underlying assumption changes?

If an output cannot answer those questions where they materially affect a decision, it is incomplete.

---

## 1. Product definition

### 1.1 Working name

**Construction Intelligence Engine (CIE)** is the internal architectural name. It is intentionally descriptive, not a final commercial brand.

### 1.2 Primary job

Turn fragmented construction evidence into a spatially and temporally coherent, machine-readable model that exposes scope, quantity, sequence, logistics, uncertainty and risk.

### 1.3 Primary users

Initial users are estimators, project managers, superintendents, VDC/BIM practitioners and technically sophisticated owners/designers who need to understand a construction decision rather than merely view a model.

### 1.4 Reference question

The canonical Meydenbauer demonstration SHALL answer:

> Does the 700 SF slab allowance reasonably cover the under-slab waste re-pipe, and what conditions could cause it not to?

The system must make the answer inspectable rather than merely state it.

### 1.5 Non-goals

CIE is not, in v1:

- a Revit replacement;
- a general-purpose BIM authoring platform;
- a Procore replacement;
- a CPM scheduling suite;
- an estimating ERP;
- a generic IFC editor;
- an autonomous design authority;
- a system that disguises assumptions as facts;
- a photorealistic rendering product whose data model exists only to support animation.

---

## 2. Governing principles

### P1 — Evidence before geometry

No decision-relevant geometry is considered trustworthy merely because it exists in 3D. Geometry must be traceable to evidence, a derivation, or an explicit assumption.

### P2 — Uncertainty is first-class data

`assumed`, `provisional`, `confirmed`, `conflicted` and `unknown` are states the system must preserve and render. Uncertainty SHALL NOT be flattened into a generic disclaimer.

### P3 — One construction state, many views

The film, web explorer, takeoff, model, report and schedule SHALL derive from the same canonical state or from reproducible transforms of it.

### P4 — Decisions outrank detail

Model detail is justified when it changes understanding, quantity, sequence, constructability, logistics, risk or communication. Decorative detail has lower priority.

### P5 — Derived claims are reproducible

A quantity or conclusion that matters to a decision must identify the inputs and method from which it was derived.

### P6 — Scenarios are deltas, not duplicate projects

Alternative conditions SHALL be represented as controlled overrides to a baseline state. S1/S2/S3 must not become three drifting copies of the model.

### P7 — The model may be wrong; the system must make wrongness discoverable

A high-quality CIE project is not one with zero assumptions. It is one in which assumptions, conflicts and unverified conditions can be found before they surprise the field team.

### P8 — Presentation and verification are separate concerns

A beautiful frame may simplify visual information, but it may not silently alter the underlying construction state.

---

## 3. System architecture

```text
PROJECT EVIDENCE
  drawings | specifications | scope | record docs | field observations | user inputs
        |
        v
EVIDENCE REGISTRY
  immutable source identity + locator + extraction + revision
        |
        v
CLAIM GRAPH
  statements about dimensions, materials, routes, requirements, conflicts, assumptions
        |
        v
CONSTRUCTION STATE
  elements + relationships + quantities + activities + logistics + issues + scenarios
        |
        +----------------+----------------+----------------+----------------+
        v                v                v                v                v
     BLENDER            GLB             WEB            REPORTS          FILM
     authoring       distribution      explorer        takeoff         narrative
```

### 3.1 Canonical artifact

Every project SHALL be compilable to:

`projects/<project>/state/project-state.json`

This file is the portable canonical snapshot for downstream consumers.

It SHALL be validated against:

`schema/project-state.schema.json`

The canonical snapshot need not contain heavyweight binary geometry. It SHALL contain stable references to geometry assets and stable element IDs that those assets preserve.

### 3.2 Compiler model

Project-specific extraction code MAY remain specialized. The stable boundary is the canonical state.

```text
prepare/extract -> normalize -> validate -> derive -> scenario -> emit
```

The architecture therefore does not require all projects to use identical source-processing code. It requires them to emit the same semantic contract.

---

## 4. Identity model

### 4.1 Stable IDs

Every decision-relevant entity SHALL have a stable, human-readable ID.

Recommended grammar:

`<PROJECT>-<TYPE>-<LOCATION>-<SYSTEM>-<SEQUENCE>`

Examples:

- `MEY-ELEM-B104-WASTE-0042`
- `MEY-EVID-P102-0001`
- `MEY-ISSUE-POC-DEPTH-01`
- `MEY-ACT-B103-EXCAVATE`

IDs SHALL survive regeneration unless the semantic identity of the object changes.

Blender object names, GLB node names, spreadsheet row IDs and browser selections SHALL preserve or map to this ID.

### 4.2 Identity is not geometry

Changing tessellation, curve resolution, material, camera, collection or render engine MUST NOT create a new semantic entity ID.

---

## 5. Core entities

### 5.1 Evidence

Evidence represents an authoritative or observational source.

Required fields:

- `id`
- `kind`: `drawing | specification | scope | record_drawing | field_photo | field_note | calculation | user_input | external_rule`
- `title`
- `revision`
- `source_path`
- `locator`
- `date`
- `authority`
- `hash` where practical

Optional fields include sheet number, page, detail, keynote, bounding box, image crop, URL and extraction method.

Evidence is immutable within a compiled state. A revised document creates a new evidence record or revision identity.

### 5.2 Claim

A claim is a normalized statement derived from evidence or explicitly introduced as an assumption.

Examples:

- `P1.02 depicts a 4-inch waste run between POC-04 and stack A.`
- `Trench width is 2'-0".`
- `POC invert is assumed 3.5 ft below F.F.`
- `P1.01 and P3.2 conflict regarding the B-104 kitchen run.`

Fields:

- `id`
- `subject_id`
- `predicate`
- `value`
- `unit`
- `status`
- `evidence_ids[]`
- `method`
- `notes`

### 5.3 Element

An element is a physical or spatial construction entity.

Examples: pipe run, fixture, footing, slab region, trench segment, riser, wall, protection zone, staging pad, haul route.

Required fields:

- `id`
- `type`
- `name`
- `project_id`
- `location`
- `system`
- `status`
- `evidence_ids[]`
- `claim_ids[]`
- `geometry_ref`
- `attributes`

### 5.4 Relationship

Relationships create the project graph.

Required types include:

- `connects_to`
- `serves`
- `contains`
- `intersects`
- `depends_on`
- `derived_from`
- `demolishes`
- `replaces`
- `restores`
- `precedes`
- `conflicts_with`
- `located_in`
- `affects`

A relationship MAY carry geometry or quantity metadata, such as intersection length.

### 5.5 Quantity

A quantity is a derived or measured value, never an orphan number.

Fields:

- `id`
- `metric`
- `value`
- `unit`
- `element_ids[]`
- `scenario_id`
- `method`
- `input_claim_ids[]`
- `status`

The system SHALL distinguish measured, calculated and assumed inputs.

### 5.6 Activity

An activity represents construction state transition over time.

Fields:

- `id`
- `name`
- `location`
- `phase`
- `duration`
- `duration_unit`
- `predecessor_ids[]`
- `element_effects[]`
- `resource_assumptions[]`
- `evidence_ids[]`
- `status`

An `element_effect` expresses state such as `existing -> demolished`, `hidden -> installed`, `open -> tested`, or `protected -> restored`.

### 5.7 Logistics object

Logistics entities include access points, haul paths, staging zones, bins, stockpiles, temporary bypasses and protection routes.

They SHALL support distance, capacity and trip calculations where relevant.

### 5.8 Issue

An issue is a decision-relevant unresolved condition, conflict, risk or information request.

Fields:

- `id`
- `title`
- `kind`: `unknown | conflict | assumption | constructability | commercial | schedule | safety | coordination`
- `severity`
- `status`
- `description`
- `affected_element_ids[]`
- `affected_quantity_ids[]`
- `evidence_ids[]`
- `resolution`
- `decision_owner`

### 5.9 Scenario

A scenario is a named set of overrides.

Fields:

- `id`
- `name`
- `baseline_id`
- `overrides[]`
- `rationale`
- `status`

For Meydenbauer:

- S1: 2'-0" trench only.
- S2: S1 + 3'x3' working pits at connections.
- S3: depth-sensitive widening to 4'-0" where the trench reaches the configured deep-trench threshold.

---

## 6. Provenance and confidence

### 6.1 Status vocabulary

Every material claim SHALL use one of:

- `confirmed` — directly supported by controlling evidence or verified observation.
- `provisional` — interpreted from evidence that is diagrammatic, incomplete or requires field verification.
- `assumed` — introduced deliberately to permit analysis.
- `conflicted` — controlling sources disagree.
- `unknown` — information is required but unavailable.
- `derived` — calculated from other traceable claims; confidence inherits from its inputs.

### 6.2 No confidence theater

CIE SHALL NOT invent pseudo-precise confidence percentages. The categorical state plus source trail is preferred.

### 6.3 Propagation

Derived outputs SHALL inherit the weakest material dependency unless a derivation explicitly eliminates that uncertainty.

Example: slab-cut area derived from a provisional route and assumed pit dimensions cannot be presented as unqualified confirmed fact.

### 6.4 Visual language

The renderer SHALL support an evidence mode in which status is visible without opening metadata.

Exact colors are presentation-layer decisions, but the distinctions MUST be perceptually separable and accompanied by labels or legends.

---

## 7. Geometry contract

### 7.1 Geometry requirements

Decision-relevant geometry SHALL:

- preserve semantic element IDs;
- use project units consistently;
- expose world transforms deterministically;
- distinguish existing, demolition, temporary and new work;
- support spatial queries needed by project calculations;
- be reproducible from source state where practical.

### 7.2 Blender contract

Blender is both an authoring environment and a high-end renderer.

Every semantic Blender object or collection SHALL carry custom properties at minimum:

- `cie_id`
- `cie_type`
- `cie_status`
- `cie_system`
- `cie_location`

Optional properties MAY cache source IDs, activity IDs and quantity IDs for debugging.

Blender SHALL NOT become the sole store for provenance or quantities.

### 7.3 GLB contract

Exported GLB nodes SHALL preserve `cie_id` and enough metadata to join against `project-state.json`.

The web application SHALL treat GLB geometry as a visualization asset and canonical state as the semantic authority.

---

## 8. Construction state and time

### 8.1 State machine

Elements SHALL support state transitions appropriate to their type.

Example trench lifecycle:

`unaffected -> located -> sawcut -> opened -> excavated -> active_work -> inspected/tested -> backfilled -> poured -> finished -> restored`

Example pipe lifecycle:

`existing -> demolition_pending -> removed`

and

`not_installed -> installing -> installed -> testing -> accepted_for_backfill`

### 8.2 Invariants

Project code SHALL be able to assert construction invariants.

Examples:

- new ABS cannot be visible as installed before conflicting existing cast iron is removed;
- backfill cannot cover a system that has not completed the required test state;
- finish restoration cannot precede concrete cure where cure is modeled;
- an occupied-unit service requirement cannot silently disappear during a phase.

The existing Meydenbauer sequence checks are the reference pattern and SHALL be retained during migration.

### 8.3 Time mapping

Film time and construction time are distinct.

Activities use construction durations. A narrative renderer maps those durations to screen time according to an explicit pacing policy. The mapping SHALL NOT mutate schedule truth.

---

## 9. Scenario engine

### 9.1 Requirement

A user SHALL be able to change a scenario input and regenerate affected quantities and geometry without cloning the project.

### 9.2 Dependency graph

Scenario propagation SHALL be dependency-based.

Meydenbauer example:

```text
POC invert
  -> pipe profile
  -> trench depth
  -> protection/widening condition
  -> trench footprint
  -> slab cut SF
  -> excavation CY
  -> loose spoil CY
  -> haul trips
  -> imported backfill
  -> production duration where quantity-driven
  -> film/explorer state
```

### 9.3 Explainability

Every changed derived quantity SHALL be able to answer `why did this change?` with the chain of overridden input and derivation steps.

---

## 10. Web Explorer specification

### 10.1 Purpose

The Explorer is not a generic model viewer. It is the primary interactive interrogation surface for the construction state.

### 10.2 Required modes

#### Model mode

Navigate and select spatial entities.

#### Evidence mode

Render elements by provenance status. Selecting an element exposes its evidence and claims.

#### Time mode

Scrub construction time. Model state, logistics and activity context update together.

#### Scenario mode

Switch or edit approved scenario inputs and display deltas in quantities and affected geometry.

#### Risk mode

Suppress low-risk context and expose unresolved issues, conflicts, assumptions and their affected elements.

### 10.3 Selection panel

Selecting an element SHALL show, when applicable:

- identity;
- type/system/location;
- dimensions and quantity;
- provenance status;
- evidence links;
- assumptions;
- connected elements;
- affected activities;
- scenario sensitivity;
- issues;
- validation state.

### 10.4 Bid-decision panel

The Meydenbauer Explorer SHALL include a dedicated slab-allowance decision view comparing S1/S2/S3 against the 700 SF allowance.

### 10.5 Deep linking

A selected entity or issue SHOULD have a stable URL state so it can be shared in review.

---

## 11. Film specification

### 11.1 Purpose

The flagship film SHALL communicate a construction decision, not merely demonstrate a model.

### 11.2 Meydenbauer narrative

Target duration: approximately 84 seconds.

Narrative spine:

1. establish Building B;
2. align source drawing to model;
3. reveal existing and proposed under-slab systems;
4. establish total scope;
5. explain trench anatomy;
6. expose footing interaction;
7. show one representative unit construction cycle;
8. show occupied-building logistics and temporary service;
9. compress the unit-by-unit schedule;
10. compare S1/S2/S3 against the allowance;
11. end on the decision: route quantity is tight but plausible; depth is the material uncertainty.

### 11.3 Film truth contract

Numbers displayed in the film SHALL be injected from canonical state at build/finish time, not manually typed into compositing code where avoidable.

### 11.4 Visual hierarchy

Default world: restrained architectural context.

Visual emphasis is reserved for semantic meaning: existing work, demolition, new work, temporary work, active operation, uncertainty and decision thresholds.

The film SHOULD avoid persistent dashboard clutter. Information appears when it advances the argument.

### 11.5 Clean master

The pipeline SHALL retain a clean master without editorial HUD so text and annotations can be revised without GPU rerender where the underlying imagery is unchanged.

---

## 12. Validation

### 12.1 Validation layers

A project build SHALL support:

1. schema validation;
2. referential-integrity validation;
3. quantity reconciliation;
4. geometry invariants;
5. construction-sequence invariants;
6. scenario invariants;
7. framing/presentation checks where deterministic;
8. provenance completeness checks.

### 12.2 Fail loudly

Decision-critical validation failures SHALL cause the build to exit non-zero.

Warnings MAY be used for incomplete but explicitly represented uncertainty.

### 12.3 Provenance completeness

Every decision-critical quantity SHALL identify its derivation and material input claims.

Every decision-critical element SHALL have evidence, an explicit assumption, or an explicit `unknown` state.

### 12.4 Golden reference

Meydenbauer SHALL be maintained as a golden reference fixture. Known totals and scenario outcomes are acceptance checks, not constants to be copied into production logic.

Reference values at spec creation include:

- 136 modeled runs/check population in the current underslab model;
- approximately 312.75 LF total new ABS;
- four POCs;
- S1 slab cut 590 SF;
- S2 slab cut 686 SF;
- S3 slab cut 991 SF at the documented reference scenario;
- S2 base excavation approximately 82.3 bank CY;
- unit-by-unit strawman duration 81.5 working days before preconstruction/holidays;
- existing sequence and framing checks SHALL continue to pass until intentionally superseded.

---

## 13. Security and evidence handling

Project evidence may contain proprietary bid documents, resident information or restricted imagery.

The state model SHALL support evidence metadata without requiring source documents to be published with public deliverables.

Public Explorer builds SHALL be capable of stripping:

- private source paths;
- restricted document crops;
- resident/personally identifying information;
- internal commercial notes;
- confidential cost data.

A public model may retain a source label such as `P1.02 / keynote 1` without distributing the underlying sheet.

---

## 14. Repository target structure

```text
schema/
  project-state.schema.json

src/cie/
  ids.py
  model.py
  validate.py
  graph.py
  scenarios.py
  emit.py

web/explorer/
  ...

docs/
  CONSTRUCTION_INTELLIGENCE_SPEC.md
  IMPLEMENTATION_PLAN.md
  MEYDENBAUER_REFERENCE_ACCEPTANCE.md

projects/<project>/
  project.yaml
  evidence/
    registry.json
  state/
    project-state.json
  products/
    ...
  deliverables/
    explorer/
    film/
    reports/
```

This is a target architecture, not permission to move working files prematurely.

---

## 15. Compatibility strategy

The current Meydenbauer pipeline is working software and SHALL be treated as an asset.

Migration SHALL initially adapt existing `prepare.py`, takeoff, build, schedule, logistics and animation outputs into canonical state rather than rewriting them wholesale.

Only after the state contract is proven should duplicated logic be pulled into shared CIE modules.

Rule: **wrap, prove, then extract.**

---

## 16. Definition of done for v1

CIE v1 exists when the following end-to-end demonstration works:

1. Open Meydenbauer in the Explorer.
2. Select a B-104 waste element.
3. See its identity, size, length, unit, status and source.
4. Navigate from that element to its source claim/evidence reference.
5. See whether its plan position and elevation are confirmed, provisional, assumed or unknown.
6. Select the POC-depth issue.
7. Change the approved scenario input from the 3.5 ft base condition to 4.5 ft.
8. Recompute affected pipe profile, trench depth, widening, slab cut, excavation and logistics quantities.
9. Explain the delta through the dependency graph.
10. See affected geometry change in the Explorer.
11. See the 700 SF allowance comparison update.
12. Scrub the associated construction sequence without violating state invariants.
13. Generate the flagship film from the same state.
14. Reconcile the model/takeoff totals and pass all decision-critical checks.
15. Run a second project through the schema and identify any Meydenbauer-specific assumptions that leaked into the core.

If this demonstration requires manually reconciling separate truths in Blender, spreadsheets and web code, v1 is not done.

---

## 17. Strategic test

Before adding a feature, ask:

> Does this make construction evidence more spatially legible, more traceable, more testable, or more useful to a decision?

If not, it is probably outside the core.

The ambition is not to make Blender smarter.

The ambition is to make construction reasoning executable.