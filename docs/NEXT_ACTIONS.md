# Next actions

Written 2026-11-13 after the repo audit. The repo is a testbed for one question: is there a repeatable workflow
from PDFs and scope documents to a verified model, and from that model to visualizations and project tools worth
using? Actions are ordered; each has an owner and a done-test. Tick them here as they close.

## 1. Owner settings (not doable from an agent session)

- [ ] **Make the repo private.** Settings → General → Danger zone → Change visibility.
- [ ] **After it is private, check three things:**
  - CI still green on the next push. `highland/exterior-reconciliation`'s `check` step runs `bm assets pull`,
    which today falls back to the public download URL. Before or right after the switch, add
    `GH_TOKEN: ${{ github.token }}` to the env of the "Product checks" step in
    `.github/workflows/build-models.yaml`, plus a top-level `permissions: contents: read`. Agent sessions
    cannot push workflow files (token lacks the `workflow` scope), so this is a local-clone or web-editor edit.
  - Actions minutes and LFS/release storage for a private repo on your plan (unverified here; read
    Settings → Billing). The film workflows fan out to 16 jobs per run.
  - Release download links in deliverable READMEs now need a GitHub login. Anyone outside who was sent a link
    needs the file sent another way.
- [ ] **Protect `main`:** require `Repo checks` and `Build & verify models`, block force-push. Whether this is
  available on a private repo depends on the plan (unverified).
- [ ] **Decide on history.** Private stops new exposure; it does not undo clones or forks made while public.
  If the drawings or bid model matter, check Insights → Forks and decide whether that is acceptable.

## 2. In the PR that added this file

- [x] Spec validator rejects: misspelled or unknown checks, specs with no checks or no elements, malformed
  `size`/`at`, unknown element types, duplicate source ids, unvalidated house-opening status. Tests added.
- [x] Duplicate `"siding"` key removed from `MATERIALS` (the first entry was dead; colours unchanged).
- [x] Experiment log and cold-run protocol: [EXPERIMENTS.md](EXPERIMENTS.md), [COLD_RUN.md](COLD_RUN.md).

## 3. Record what the experiments so far showed (owner, about an hour)

- [ ] Fill the verdict column in [EXPERIMENTS.md](EXPERIMENTS.md) for the twelve existing products: keep,
  kill, or fold into the shared pipeline, with one sentence why. Agents cannot write these; they are your
  judgment of what was worth it.

## 4. The cold run (the main experiment)

- [ ] Pick a third project that neither Highland nor Meydenbauer code was written for. Small is fine:
  one scope, one drawing set.
- [ ] Run [COLD_RUN.md](COLD_RUN.md) with the stopwatch and fill in its result table.
- [ ] Field-check at least five dimensions and record model-versus-field deltas.

Done when the result table is committed. That table is the first real measure of the workflow.

## 5. After the cold run, not before

- [ ] Promote whatever the cold run reused from product folders into `src/bmodels/`; list what it did not
  touch as deletion candidates.
- [ ] Decide `provisional` metadata: AGENTS.md and METHOD.md require a reference and tolerance, the validator
  still requires only `source`. Enforcing it needs real values for the existing specs, which only the
  documents can supply.
- [ ] One shared provenance check for product-local specs (Highland and Meydenbauer are outside `spec.check`).
- [ ] Ranges on takeoff quantities, derived from provenance and tolerance.
- [ ] CIE: run it on the cold-run project or shelve it. No more specification prose until then.

## Parked (do when they hurt)

Ruff in CI for `src/` and `tests/`; migrating the 68 tracked files over 1 MB to Releases; SHA-pinning the
remaining workflows and removing the dead `deliver/highland-owner-tour` trigger; executing
[branch-triage](branch-recovery/2026-11-08/branch-triage.md) (destructive, needs explicit approval);
`bm publish` overwrite guard; `qto` golden-value test.
