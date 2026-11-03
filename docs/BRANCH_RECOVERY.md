# Branch consolidation and recovery

## First phase completed — November 3, 2026

The original 44 remote branch tips were preserved under
`archive/2026-11-03/<original-branch-name>` tags before cleanup. These are Git
history snapshots, not independent backups of Git LFS payloads, release assets,
or ignored source documents. Do not remove the archive tags during recovery.

33 branches were removed in one atomic push with an explicit expected SHA for
each deletion: 27 ancestors of main, four workflow branches whose trees equal
their merge-base trees, and two film branches whose unique patches are already
in main (`git cherry` reports `-`). All 44 remote archive tags were checked
against the snapshot before deletion. Remote refs were checked again afterward:
all 33 candidates were absent and the other 11 original branches were unchanged.
No open PRs existed at cleanup. A search of current repository Markdown and
workflow files found no matching GitHub tree/blob links to the cleanup branch
prefixes; external links and third-party automation were not exhaustively audited.
Main remains at `b46c1c7c96238ab43e9cb2bc736fb023f7421dfb`.

Records:

- [Original branch tips](branch-recovery/2026-11-03/branch-snapshot.json)
- [Verified cleanup candidates](branch-recovery/2026-11-03/cleanup-candidates.json)
- [Cleanup result and remaining original branches](branch-recovery/2026-11-03/cleanup-result.json)
- [Complete recovery path inventories](branch-recovery/2026-11-03/recovery-inventory.json)

The inventories use each source's merge base with main and do not imply every
listed file should be imported. They supersede the GitHub API's truncated file
lists: Highland has 352 changed paths, VDC 473, and B101 81. VDC has three
unique commits and is 83 commits behind main. This record's own PR branch is
additional to the 11 original branches retained.

To restore a retired branch, select its exact entry in the snapshot, verify the
archive tag resolves to that SHA, then use `git push origin
refs/tags/archive/2026-11-03/<name>:refs/heads/<name>`. Restoration must not
overwrite an existing branch. Fetch the archive tag first in another clone.

## Recovery 1: Highland drawing reconciliation

Start the implementation branch from current main. The source snapshot is
`archive/2026-11-03/continue/highland-roof-geometry` at
`bddd5b8fb4085677028108754ef82a722bc0b17c`. It already contains
`continue/highland-drawing-reconciliation`; do not integrate both independently.
The three extra roof commits are merges with no net file change relative to the
drawing tip. Preserve the handoff/daylight/drawing branches until acceptance.

The latest drawing handoff identifies `projects/highland-drawings/reconciled.spec.json`
as its geometry source. Recover that source and its decision/control records
before presentation assets. The historical `validate.py` checks 192 openings,
14 P1 openings, 34 R5 openings, protected north meshes, source hashes and camera
controls. These are inherited assertions to rerun, not newly verified results.

Port in these reviewable slices:

1. Recover source specs, provenance, decision ledgers and protected geometry
   controls into the current `projects/highland/` layout. Keep reference PDFs in
   ignored `sources/` with manifest locators/hashes. Do not copy old `requirements.txt`.
2. Adapt build/validation imports and paths to `bmodels.paths.ROOT`, add a
   declared product with a CPU check, and reconcile it with the existing exterior
   product. Preserve the distinction between geometry changes and presentation.
3. Rebuild native geometry and review source/render pairs. Then package accepted
   outputs in current deliverables; new files over 1 MB belong in Releases.

Acceptance must preserve the handoff's deferred north work and documented
residuals. The 192-opening inventory is not a dimensional accuracy certificate.
Do not reopen owner-deferred north audits or promote assumed guards, glazing
profiles, waterproofing or P1 below-grade details to confirmed geometry.

## Recovery 2: Meydenbauer VDC and B101

Preserve both source snapshots:

- VDC: `archive/2026-11-03/meydenbauer/4d-fixes`,
  `87d21bf145100fe7d95f3aeba7db95b822aa5764`.
- B101: `archive/2026-11-03/meydenbauer/b101-v4-executed`,
  `70fc8d60ef50006c27222ad7fbd50bf519815cac`.

The VDC CSV lists eight serial project-wide phases totaling 29 working days,
January 4–February 11, 2027, and retimes an existing 672-frame animation. Main's
Explorer chains eight activities per unit across four units on an assumed
81.5-working-day S2 baseline. These are structurally different schedules.
Their scope, resource and occupancy assumptions must be compared before their
durations can be treated as alternatives. S1/S3 durations remain not calculated
in the merged Explorer; do not restore the superseded excavation-only duration
sensitivity from closed PR #38.

First recover the small schedule, element, issue, takeoff and route-control data
for inspection. Reconcile identifiers (`vdc_element_id` versus `cie_id`), units,
final-frame quantity methods, evidence and scope coverage against canonical CIE
state. Keep reported VDC slope deviations and unknown slopes explicit. The VDC
README's model and validation claims have not been independently rerun here.

The B101 package contains calibrated route controls and demolition/fitting QA.
Compare these to the main takeoff/spec before importing quantities or replacing
routes. Reuse useful validators; avoid a second canonical state store. Package
large saved models through Releases only after inspecting their external assets.

## Remaining triage

Keep the unique video work on `feat/render-scenes-actions`, packaging helper on
`deliver/highland-archviz-film`, cutaway design, and old report improvements for
focused review. Their old layouts make whole-branch merges inappropriate.

## Validation and future branch practice

At the cleanup baseline, `uv run --no-sync bm check` passed all repository checks,
39 tests and 23 subtests. No historical model builds, product rebuilds or visual
reviews are implied by that result. Recovery PRs must follow [AGENTS.md](../AGENTS.md),
including product checks and model/render inspection where applicable.

Use a fresh branch per follow-up, normally targeting main. A stack needs an
explicit integration PR to main. Preserve delivery milestones through tags and
Releases; stop adding commits to branches after their PRs merge. Main protection
and automatic branch deletion are recommendations; repository settings were not
changed in this phase.
