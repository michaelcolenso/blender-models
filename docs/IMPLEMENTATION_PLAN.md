# Construction Intelligence Engine — Implementation Plan

Status: Proposed v0.1
Depends on: `docs/CONSTRUCTION_INTELLIGENCE_SPEC.md`
Reference project: 101 Meydenbauer, Building B

## 0. Delivery strategy

Build this as a sequence of **vertical proofs**, not horizontal infrastructure layers.

Each milestone must leave Meydenbauer more useful than before. Avoid a long rewrite in which the current bid model stops working while a generalized framework is constructed underneath it.

Governing migration rule:

> **Wrap -> prove -> extract -> generalize.**

The current takeoff, model, schedule, logistics and animation pipeline remains operational until its replacement has passed the same or stronger checks.

---

## 1. Success condition

The first release is successful when one project can move through this chain without separate sources of truth:

```text
source evidence
  -> normalized claims
  -> canonical project state
  -> scenario derivation
  -> geometry + quantities + activities + issues
  -> Blender / GLB / Explorer / report / film
```

The signature demonstration is the Meydenbauer depth question:

`POC depth change -> trench condition -> slab SF -> excavation -> logistics -> schedule implication -> visual decision`

If that chain is real, the architecture is real.

---

## 2. Workstream map

| Workstream | Outcome | Depends on |
|---|---|---|
| A. Semantic kernel | stable IDs + typed state + validation | none |
| B. Meydenbauer adapter | existing pipeline emits canonical state | A |
| C. Scenario graph | S1/S2/S3 and depth deltas propagate | A, B |
| D. Blender/GLB bridge | semantic IDs survive visual pipeline | A, B |
| E. Explorer | interactive evidence/quantity/time/risk UI | B, C, D |
| F. Flagship film | 84s decision narrative from same state | B, C, D |
| G. Generalization | second project proves core is not Meydenbauer-specific | A–F |

Workstreams overlap only after their contracts are stable enough to avoid churn.

---

# Milestone 0 — Baseline and freeze

## Goal

Capture what works today before touching architecture.

## Tasks

- Record current `main` commit as the migration baseline.
- Run or document the current Meydenbauer build sequence.
- Snapshot current takeoff totals, model checks, animation checks and known deliverables.
- Inventory all values currently duplicated across `prepare.py`, `takeoff.py`, `build.py`, `schedule.py`, `logistics.py`, `animate.py` and `anim_finish.py`.
- Identify manually typed film/HUD quantities that should eventually come from canonical state.
- Identify every existing object metadata field in the `.glb` and Blender scene.

## Deliverable

`projects/meydenbauer-b/state/baseline.json`

This is not canonical state. It is a migration comparison fixture.

## Acceptance

- Current production scripts remain unchanged.
- Baseline contains the known approximately 312.75 LF total and current model-check population.
- Current 4D checks are enumerated so migration cannot silently weaken them.

## Stop/go question

Can we prove after each later milestone that we have not lost a currently working capability?

---

# Milestone 1 — Semantic kernel

## Goal

Create the smallest shared library capable of representing the specification without importing Blender.

## New files

```text
src/cie/__init__.py
src/cie/ids.py
src/cie/model.py
src/cie/validate.py
src/cie/graph.py
schema/project-state.schema.json
tests/cie/test_ids.py
tests/cie/test_validation.py
```

## Tasks

### 1.1 Stable IDs

Implement deterministic ID helpers. Do not derive IDs from Blender object names or array indexes.

### 1.2 Typed model

Represent at minimum:

- Project
- Evidence
- Claim
- Element
- Relationship
- Quantity
- Activity
- LogisticsObject
- Issue
- Scenario

Prefer standard-library dataclasses or the repository's existing dependency philosophy over introducing a large framework solely for validation.

### 1.3 JSON Schema

Create Draft 2020-12-compatible schema for the portable state artifact.

### 1.4 Referential integrity

Validate that all referenced IDs exist and types are sensible.

### 1.5 Provenance lint

Add rules:

- decision-critical elements require evidence, explicit assumption, or unknown status;
- derived quantities require input claims or a documented method;
- `confirmed` claims require evidence;
- `conflicted` claims require at least two conflicting sources/claims or an explicit conflict note.

## Acceptance

A synthetic miniature project compiles, validates and round-trips through JSON with deterministic ordering.

## PR size

One focused PR. No Blender changes.

---

# Milestone 2 — Meydenbauer adapter

## Goal

Emit canonical state from existing Meydenbauer outputs without rewriting the production algorithms.

## New files

```text
projects/meydenbauer-b/products/underslab/state_adapter.py
projects/meydenbauer-b/evidence/registry.json
projects/meydenbauer-b/state/project-state.json
```

## Tasks

### 2.1 Evidence registry

Register the controlling inputs already cited by the project: P1.01, P1.02, P2.1, P3.2, P5.0/P5.1, SOR, Addendum 1, record structural drawings and relevant bid-form requirements.

Do not publish restricted source documents merely to populate the registry. Store locators and source identity.

### 2.2 Claims

Normalize the claims currently embedded in README prose and Python constants:

- route/size interpretations;
- trench width;
- slab thickness assumption;
- POC depth assumptions;
- pit assumptions;
- deep-trench widening assumption;
- swell factor;
- service requirements;
- access restriction;
- B-104 scope conflict;
- groundwater condition;
- footing geometry and structural-screening assumptions.

### 2.3 Elements

Map existing pipe runs, POCs, risers, fixtures, trenches, footings, protection zones, entries, staging and haul routes to stable IDs.

### 2.4 Quantities

Import existing takeoff outputs as derived quantities with methods and dependencies, not copied display strings.

### 2.5 Activities

Adapt schedule output to canonical activities and element effects.

### 2.6 Issues

Encode the current RFIs/clarifications as first-class issues and connect them to affected elements/quantities.

## Acceptance

- Canonical state validates.
- Total modeled ABS reconciles to current takeoff within the existing tolerance.
- Four POCs reconcile.
- S1/S2/S3 reference quantities reconcile.
- Unit totals reconcile.
- Existing production files remain the computational authority during this milestone.

## Stop/go question

Can a developer understand the Meydenbauer bid risk by reading `project-state.json` without opening Blender?

---

# Milestone 3 — Dependency and scenario engine

## Goal

Make uncertainty executable.

## New files

```text
src/cie/scenarios.py
src/cie/derive.py
tests/cie/test_scenarios.py
```

## Tasks

### 3.1 Dependency representation

Represent derived values as named derivations with declared input claim/quantity IDs.

### 3.2 Scenario overrides

Support overrides without mutating baseline state.

Example:

```json
{
  "claim_id": "MEY-CLAIM-POC-DEPTH-BASE",
  "value": 4.5,
  "unit": "ft"
}
```

### 3.3 Delta computation

Return:

- changed inputs;
- changed derived quantities;
- affected elements;
- affected activities;
- affected issues;
- human-readable dependency path.

### 3.4 Meydenbauer depth chain

Implement the reference chain from POC depth through trench/slab/excavation/logistics.

Do not force schedule duration to change unless the existing rate model actually consumes the changed quantity.

### 3.5 Scenario regression tests

Reference tests SHALL include the current S1/S2/S3 outcomes.

## Acceptance

One CLI command can produce baseline and alternate state snapshots and explain why slab cut changed.

Suggested interface:

```bash
python -m cie scenario \
  projects/meydenbauer-b/state/project-state.json \
  --scenario S3 \
  --explain MEY-QTY-SLAB-CUT
```

Exact CLI syntax may change; capability may not.

---

# Milestone 4 — Blender and GLB semantic bridge

## Goal

Make visual geometry a faithful view of canonical construction entities.

## Tasks

### 4.1 Custom properties

Add `cie_id`, `cie_type`, `cie_status`, `cie_system`, `cie_location` to semantic objects during generation.

### 4.2 ID preservation

Verify exported GLB nodes retain a stable join key.

### 4.3 State-driven presentation

Create a small adapter that can apply visual states from canonical data:

- normal architectural mode;
- evidence/provenance mode;
- demolition/new/temporary mode;
- issue isolation mode.

### 4.4 No material explosion

Do not create a unique Blender material for every semantic state/entity. Use a bounded material system and object/node metadata.

### 4.5 Regression

Run existing Blender model checks and animation sequence checks after metadata integration.

## Acceptance

Given an element selected in a GLB viewer, its `cie_id` resolves to exactly one canonical element. Given the same ID in Blender, it resolves to the same semantic object.

---

# Milestone 5 — Explorer alpha

## Goal

Build the first useful construction-intelligence interface.

## Technical direction

Use a lightweight web stack that fits the repository owner's existing strengths. SvelteKit + Three.js is a strong default unless repository constraints argue otherwise. Keep the state engine framework-neutral.

## Layout

Three primary zones:

1. filter/mode rail;
2. large 3D viewport;
3. evidence/decision inspector;

Timeline occupies the bottom when Time mode is active.

## Slice 5A — Selection

- load GLB;
- load canonical state;
- map node -> `cie_id`;
- click/select;
- show identity, quantity, status and evidence metadata;
- isolate/hide/focus.

This is the first browser milestone worth deploying.

## Slice 5B — Evidence mode

- color by provenance status;
- filter assumed/provisional/conflicted/unknown;
- show claim and source locator;
- deep-link selected entity.

## Slice 5C — Risk mode

- issue list ranked by materiality;
- selecting issue highlights affected geometry and quantities;
- B-104 conflict, POC depth, groundwater, bypass/service and B-102 WC path are reference cases.

## Slice 5D — Scenario mode

- S1/S2/S3 toggle;
- show baseline vs scenario delta;
- animate changed trench footprint rather than replacing the whole scene;
- allowance gauge at 700 SF;
- excavation/logistics quantities update from scenario state.

## Slice 5E — Time mode

- scrub construction time;
- apply element state transitions;
- show current activity and unit;
- show haul/bypass overlays only when active;
- compact Gantt/playhead on demand.

## Performance target

Initial interaction should remain fluid on a modern laptop and usable on a recent phone. Optimize semantic usefulness before cinematic browser rendering.

## Acceptance

A reviewer can discover the slab-depth risk without being told where to click.

Conduct a five-task usability test:

1. Find B-104's largest new waste run.
2. Determine its evidence status.
3. Find the biggest unresolved quantity risk.
4. Compare S2 with S3.
5. Explain why the allowance changes.

A technically competent construction user should complete these without source-code knowledge.

---

# Milestone 6 — Flagship film rebuild

## Goal

Produce an approximately 84-second film that looks expensive because it communicates unusually well, not because it contains gratuitous effects.

## Narrative plan

### Shot 01 — Building / 0–5s

Restrained architectural hero. Establish project and occupied-building context.

### Shot 02 — Evidence lock / 5–11s

P1.02 aligns to the model/grid. Drawing recedes; interpreted routes persist.

### Shot 03 — X-ray / 11–17s

Descend through slab. Existing cast iron and new ABS become the visual subject.

### Shot 04 — Scope / 17–25s

Reveal all four units and inject canonical totals.

### Shot 05 — Anatomy / 25–34s

Exploded B-104 trench assembly. Make demolition, excavation, bedding, pipe, backfill and restoration spatially obvious.

### Shot 06 — Structure / 34–43s

Reveal footing/trench relationship. Label the structural check as screening, not a structural conclusion.

### Shot 07 — Pilot unit / 43–55s

B-103 construction cycle. Protection -> demo -> excavation -> install -> test -> restore.

### Shot 08 — Occupancy/logistics / 55–64s

Pull out to haul path, staging and temporary service logic while untouched units remain legible.

### Shot 09 — Time / 64–72s

Compress B-103 -> B-102 -> B-101 -> B-104. Display schedule duration from state.

### Shot 10 — Scenario / 72–80s

S1 -> S2 -> S3 trench geometry. A 700-SF reference plane/graphic remains fixed while modeled area changes.

### Shot 11 — Decision / 80–84s

End on the decision rather than a logo orbit:

`THE DRAWN ROUTE ISN'T THE RISK. DEPTH IS.`

Follow with restrained project identification and provenance disclaimer.

## Film engineering tasks

- Separate camera choreography from construction state changes.
- Inject all decision numbers from canonical state.
- Retain clean master.
- Create shot-level framing assertions.
- Add render-quality tiers: proxy, review, final.
- Keep current RunPod benchmark/render/finish workflow until a better executor is proven.
- Prefer compositing for typography/HUD so copy changes do not trigger GPU rerenders.

## Visual direction

- architectural white/charcoal world;
- minimal persistent UI;
- controlled depth of field only where it improves hierarchy;
- physically plausible light;
- no ghost-wall soup;
- opaque/poché sectional language preferred to stacked alpha transparency;
- semantic accent colors reserved for meaning;
- camera motion motivated by explanation;
- transitions created by construction state, not generic motion graphics.

## Acceptance

Mute the film. A construction professional should still understand the broad argument.

Play audio/text only. The argument should remain factually defensible.

Every displayed quantity must reconcile to the canonical state used for the render.

---

# Milestone 7 — Decision report

## Goal

Prove the canonical state can produce a non-3D deliverable.

Generate a concise bid/constructability report from the same state containing:

- scope totals;
- scenario table;
- unresolved issues;
- provenance summary;
- schedule/logistics assumptions;
- high-materiality decision points;
- selected stills generated from known camera IDs.

This prevents the architecture from becoming accidentally Blender-centric.

---

# Milestone 8 — Second-project generalization

## Goal

Attack the abstraction with a project that is materially different.

Recommended candidate: Highland, because its domestic-water riser/corridor-main problem introduces different systems, vertical distribution, valves, hangers, expansion behavior, unit branches and hold-point communication.

## Method

Do not start by refactoring CIE to fit Highland.

First write a Highland adapter against the existing schema. Record every point of friction.

Classify each friction as:

- legitimate missing universal concept;
- project-specific concept that belongs in `attributes` or an extension;
- bad Meydenbauer assumption embedded in core;
- presentation-only difference.

Only then change the core schema.

## Acceptance

At least 80% of the semantic kernel is reused unchanged, and any schema expansion can be explained without reference to a single Meydenbauer-specific implementation detail.

---

# Milestone 9 — Project compiler UX

## Goal

Make the architecture operable rather than artisanal.

Target command family:

```bash
bm validate meydenbauer-b
bm build meydenbauer-b
bm scenario meydenbauer-b S3
bm explorer meydenbauer-b
bm film meydenbauer-b --quality review
bm report meydenbauer-b
```

This can initially be Python entry points. Do not build a sophisticated CLI framework before the commands are useful.

Desired build summary:

```text
Meydenbauer B
Evidence        PASS
State           PASS
References      PASS
Geometry        PASS
Takeoff         PASS
Sequence        PASS
Scenarios       PASS
Issues          6 open
GLB             PASS
Explorer        READY
Film            READY
```

---

## 3. PR sequence

Keep reviewable boundaries.

1. `cie: add semantic kernel and schema`
2. `meydenbauer: emit canonical project state`
3. `cie: add scenario dependency engine`
4. `meydenbauer: preserve semantic IDs through Blender and GLB`
5. `explorer: add model selection and evidence inspector`
6. `explorer: add risk and scenario modes`
7. `explorer: add construction timeline`
8. `meydenbauer: rebuild flagship film from canonical state`
9. `report: generate decision report from canonical state`
10. `highland: validate CIE schema on second project`
11. `cie: extract justified shared abstractions`
12. `cli: expose project compiler workflow`

Do not combine all twelve into a mega-PR.

---

## 4. Engineering traps to avoid

### Trap: premature universal BIM ontology

Use a compact construction-oriented schema plus extensible attributes. Do not recreate IFC.

### Trap: Blender as database

Custom properties are joins, not canonical storage.

### Trap: web app reimplements engineering math

Scenario calculations belong in the state/derivation layer. Browser code consumes results or invokes the same deterministic logic.

### Trap: provenance as UI decoration

Provenance must exist in the data before a color legend exists.

### Trap: film forks truth

No manually maintained duplicate quantity table in animation code.

### Trap: assumptions hidden in constants

A constant that materially affects a decision should become a named claim/input with status and source/rationale.

### Trap: rewriting working code for elegance

Do not replace verified Meydenbauer algorithms until the replacement is demonstrably better and regression-tested.

### Trap: confusing cinematic realism with construction truth

Visual realism can be assumed for presentation; decision-relevant construction conditions must be labeled and traceable.

---

## 5. External validation

The project is not validated by its author liking it.

Use four independent tests:

### Quantity reconciliation

A competent estimator can reproduce selected totals from the stated assumptions within expected tolerance.

### Evidence audit

A reviewer can trace sampled decision-critical claims back to the cited source/locator.

### Construction review

A PM/superintendent can identify where the model is assumed versus documented and can challenge an assumption without reverse-engineering code.

### Usability test

A new reviewer can answer the five Explorer tasks without coaching.

Later, measure business outcomes: faster scope comprehension, fewer missed clarifications, reduced takeoff reconciliation time, better bid interviews and fewer field surprises.

---

## 6. First 10 working sessions

This is the recommended immediate execution sequence.

**Session 1:** baseline current Meydenbauer outputs and duplicated values.

**Session 2:** implement stable IDs + minimal semantic dataclasses.

**Session 3:** write JSON Schema + referential/provenance validation.

**Session 4:** build evidence registry and normalize Meydenbauer claims.

**Session 5:** adapt pipe/trench/fixture/footing elements and reconcile takeoff.

**Session 6:** adapt schedule/logistics/issues; emit first complete `project-state.json`.

**Session 7:** implement scenario overrides and the POC-depth dependency chain.

**Session 8:** preserve `cie_id` through Blender -> GLB and prove round-trip selection.

**Session 9:** build Explorer selection/evidence vertical slice.

**Session 10:** implement the S1/S2/S3 allowance view. Stop and review the product before adding Time mode or rebuilding the film.

That review is deliberate. If the Explorer cannot make the depth/allowance problem startlingly clear after Session 10, fix the model and interaction before adding more surface area.

---

## 7. Definition of implementation success

The strongest demo is not a reel of beautiful shots.

It is this:

1. Click a pipe.
2. Show the drawing claim behind it.
3. Reveal that its elevation depends on an unknown field condition.
4. Change the condition.
5. Watch the trench geometry change.
6. Watch slab cut and excavation quantities update.
7. Watch the allowance cross from acceptable to exceeded.
8. Show the logistics/schedule consequences.
9. Press play.
10. The cinematic film tells the same story from the same state.

When that works, the repository has crossed the line from scripted visualization into executable construction reasoning.