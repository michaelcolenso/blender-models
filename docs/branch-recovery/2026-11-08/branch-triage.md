# Branch and issue triage — November 8, 2026

**Inventory only. Nothing was deleted, merged, retagged or force-pushed.** Every disposition below is a
proposal for the owner. Convention and restore procedure: [BRANCH_RECOVERY.md](../../BRANCH_RECOVERY.md).

## Basis

- `origin/main` at `db72f54` (Merge pull request #63). Remote state fetched with `git fetch origin --prune`.
- Branches, PRs and issues read through the GitHub REST API (`gh api repos/michaelcolenso/blender-models/...`);
  GraphQL is not available from this environment, so `gh pr list` / `gh issue list` were not used.
- Behind/ahead = `git rev-list --left-right --count origin/main...origin/<branch>`.
  Unique patches = `git cherry origin/main origin/<branch>`: `+` is a patch not in main, `-` is a patch whose
  equivalent is already in main. Merge commits are not counted.
- **Not checked:** external links, third-party automation, or branch protection rules that may reference these branches.

## Result

- 34 remote branches: `main` plus 33 others.
- **Open issues: 0** (the REST issues endpoint returned only PR #64).
- **Open PRs: 1** — #64 `highland/cinema-film-v2` → `main`.
- 21 branches are ancestors of main, 1 more has all its patches in main, 10 carry patches not in main (4 already decided by the owner on 2026-11-05), 1 has the open PR.
- 44 `archive/2026-11-03/*` tags remain on origin and must stay (see BRANCH_RECOVERY.md). They cover only the original
  44 branch tips of November 3; the branches below created after that date have no archive tag, but the 21
  ancestors need none because main already contains their history.

## Keep or decide (11)

| Branch | Tip | Last commit | Behind / ahead of main | Unique patches (`+`/`-`) | PRs | Proposed disposition |
|---|---|---|---|---|---|---|
| `continue/highland-drawing-reconciliation` | `516ef7b` | 2026-10-22 | 153 / 10 | 10 / 0 | #17 merged→continue/highland-roof-geometry, #16 merged→continue/highland-roof-geometry, #15 merged→continue/highland-roof-geometry | Keep: carries patches not in main; owner decides (see [BRANCH_RECOVERY.md](../../BRANCH_RECOVERY.md)) |
| `continue/highland-exterior-daylight` | `3785f7f` | 2026-10-20 | 153 / 3 | 3 / 0 | #10 closed unmerged→handoff/highland-exterior-2026-10-20 | Keep: carries patches not in main; owner decides (see [BRANCH_RECOVERY.md](../../BRANCH_RECOVERY.md)) |
| `continue/highland-roof-geometry` | `bddd5b8` | 2026-10-21 | 153 / 13 | 10 / 0 | #13 closed unmerged→continue/highland-exterior-daylight | Keep: carries patches not in main; owner decides (see [BRANCH_RECOVERY.md](../../BRANCH_RECOVERY.md)) |
| `deliver/highland-archviz-film` | `0322d7d` | 2026-10-19 | 158 / 1 | 1 / 0 | #7 merged→main | Owner decision 2026-11-05: **retired**. Branch still present; recoverable from `archive/2026-11-03/`. Candidate to delete on owner approval |
| `docs/meydenbauer-cutaway-design` | `8488002` | 2026-10-25 | 132 / 1 | 1 / 0 | #22 closed unmerged→main | Owner decision 2026-11-05: **retired**. Branch still present; recoverable from `archive/2026-11-03/`. Candidate to delete on owner approval |
| `feat/render-scenes-actions` | `deaf6ea` | 2026-10-19 | 162 / 2 | 1 / 1 | #6 merged→main | Owner decision 2026-11-05: **retired**. Branch still present; recoverable from `archive/2026-11-03/`. Candidate to delete on owner approval |
| `handoff/highland-exterior-2026-10-20` | `fab3bd0` | 2026-10-20 | 153 / 2 | 2 / 0 | #9 closed unmerged→main | Keep: carries patches not in main; owner decides (see [BRANCH_RECOVERY.md](../../BRANCH_RECOVERY.md)) |
| `highland/cinema-film-v2` | `286acc0` | 2026-11-08 | 0 / 1 | 1 / 0 | #64 open→main | Keep: open PR |
| `improve-docs-and-reports` | `03dc8a1` | 2026-10-02 | 174 / 1 | 1 / 0 | none | Owner decision 2026-11-05: **ported**. Branch still present; recoverable from `archive/2026-11-03/`. Candidate to delete on owner approval |
| `meydenbauer/4d-fixes` | `87d21bf` | 2026-10-28 | 133 / 3 | 3 / 0 | #21 merged→main | Keep: carries patches not in main; owner decides (see [BRANCH_RECOVERY.md](../../BRANCH_RECOVERY.md)) |
| `meydenbauer/b101-v4-executed` | `70fc8d6` | 2026-10-24 | 141 / 1 | 1 / 0 | none | Keep: carries patches not in main; owner decides (see [BRANCH_RECOVERY.md](../../BRANCH_RECOVERY.md)) |

Four of these (`improve-docs-and-reports`, `feat/render-scenes-actions`, `deliver/highland-archviz-film`,
`docs/meydenbauer-cutaway-design`) were already ported or retired by owner decision on 2026-11-05
([BRANCH_RECOVERY.md, Remaining triage](../../BRANCH_RECOVERY.md#remaining-triage)); the branches were left in place.
The other six unmerged branches (`continue/*` ×3, `handoff/highland-exterior-2026-10-20`, `meydenbauer/4d-fixes`,
`meydenbauer/b101-v4-executed`) are not decided in the "Remaining triage" section; Highland and Meydenbauer recovery
sections of that document cover their content, but I did not re-verify that mapping here. They need an owner decision.

## Proposed retirements (22)

| Branch | Tip | Last commit | Behind / ahead of main | Unique patches (`+`/`-`) | PRs | Proposed disposition |
|---|---|---|---|---|---|---|
| `chore/branch-consolidation-2026-11-03` | `89da1a7` | 2026-11-03 | 62 / 0 | 0 / 0 | #40 merged→main | Candidate to retire: tip is an ancestor of main |
| `chore/doctor-chromium-libs` | `56006dd` | 2026-11-05 | 25 / 0 | 0 / 0 | #55 merged→main | Candidate to retire: tip is an ancestor of main |
| `chore/scenario-blender-skills` | `888add7` | 2026-11-05 | 28 / 0 | 0 / 0 | #52 merged→main | Candidate to retire: tip is an ancestor of main |
| `ci/product-dependency-checks` | `5369d23` | 2026-11-04 | 50 / 0 | 0 / 0 | #44 merged→main | Candidate to retire: tip is an ancestor of main |
| `claude/quirky-bell-1ayvkb` | `2a4ebb1` | 2026-11-08 | 1 / 0 | 0 / 0 | #63 merged→main | Candidate to retire: tip is an ancestor of main |
| `deliver/highland-reconciliation-package` | `eb177b0` | 2026-11-05 | 44 / 0 | 0 / 0 | #46 merged→main | Candidate to retire: tip is an ancestor of main |
| `feat/basis-of-record` | `adde094` | 2026-11-05 | 32 / 0 | 0 / 0 | #51 merged→main | Candidate to retire: tip is an ancestor of main |
| `feat/highland-risers` | `0b81f33` | 2026-11-06 | 14 / 1 | 0 / 1 | #58 merged→main | Candidate to retire after owner review: every unique patch is already in main (`git cherry` all `-`) |
| `feat/highland-structural-ceilings` | `a0eb557` | 2026-11-03 | 57 / 0 | 0 / 0 | #42 merged→main | Candidate to retire: tip is an ancestor of main |
| `feat/highland-water-deliverables-refresh` | `d4b8b10` | 2026-11-04 | 53 / 0 | 0 / 0 | #43 merged→main | Candidate to retire: tip is an ancestor of main |
| `feat/prores-plate-split` | `799c2cb` | 2026-11-05 | 45 / 0 | 0 / 0 | #47 merged→main | Candidate to retire: tip is an ancestor of main |
| `highland/cinema-archviz-pass` | `9577d2b` | 2026-11-06 | 7 / 0 | 0 / 0 | #61 merged→main | Candidate to retire: tip is an ancestor of main |
| `highland/cinema-yaw-wrap-fix` | `a417c76` | 2026-11-08 | 5 / 0 | 0 / 0 | #62 merged→main | Candidate to retire: tip is an ancestor of main |
| `highland/water-publish-p1` | `aeabd36` | 2026-11-05 | 24 / 0 | 0 / 0 | #54 merged→main | Candidate to retire: tip is an ancestor of main |
| `highland/water-viewer-manifest-revert` | `1b0118a` | 2026-11-06 | 19 / 0 | 0 / 0 | #56 merged→main | Candidate to retire: tip is an ancestor of main |
| `highland/water-viewer-p1` | `230f2d9` | 2026-11-05 | 26 / 0 | 0 / 0 | #53 merged→main | Candidate to retire: tip is an ancestor of main |
| `meydenbauer/b101-v4-review` | `5bc99bc` | 2026-11-06 | 16 / 0 | 0 / 0 | #57 merged→main | Candidate to retire: tip is an ancestor of main |
| `meydenbauer/recovery-close-out` | `1322be3` | 2026-11-05 | 33 / 0 | 0 / 0 | #50 merged→main | Candidate to retire: tip is an ancestor of main |
| `meydenbauer/vdc-scope-import` | `3e07353` | 2026-11-05 | 35 / 0 | 0 / 0 | #49 merged→main | Candidate to retire: tip is an ancestor of main |
| `recover/highland-native-builder` | `1274314` | 2026-11-05 | 48 / 0 | 0 / 0 | #45 merged→main | Candidate to retire: tip is an ancestor of main |
| `recover/highland-source-controls` | `305329f` | 2026-11-04 | 60 / 0 | 0 / 0 | #41 merged→main | Candidate to retire: tip is an ancestor of main |
| `recover/meydenbauer-vdc-b101-sources` | `049a101` | 2026-11-05 | 41 / 0 | 0 / 0 | #48 merged→main | Candidate to retire: tip is an ancestor of main |

For `feat/highland-risers` (patch already in main, but the tip is not an ancestor), create
`archive/2026-11-08/feat/highland-risers` before any deletion so the exact tip stays recoverable.

## If the owner approves retirement

Follow the November 3 method: re-verify each tip SHA immediately before acting, delete with an explicit expected SHA
per branch in one push, then re-read the remote refs. This document authorizes nothing.

## Re-check

Re-run the inventory before acting; open PRs and branch tips change. Issues were empty on this date; there is
no issue backlog to triage.
