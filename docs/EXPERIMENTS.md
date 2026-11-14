# Experiment log

This repo is a testbed. An experiment that leaves outputs but no conclusion has to be run again, so every
product and every workflow trial gets one entry here: what was tried, what it cost, and whether to keep it.

Rules:

- One entry per experiment, added when it ends, not when it starts.
- The verdict is the owner's call. Agents fill in the facts and leave the verdict blank.
- Costs are measured or marked `not recorded`; never estimated after the fact as if measured.
- `keep` means it goes into the repeatable workflow. `kill` means stop maintaining it (delete or archive).
  `fold` means the idea survives but moves into `src/bmodels/`.

## Template

```markdown
### <date> <site>/<product or trial name>
- **Question:** what this was meant to find out.
- **Inputs:** documents and their quality (sheet count, dimensioned or NTS, photos).
- **Method:** the path taken, in one or two lines.
- **Cost:** hours of attention, compute (CPU/GPU hours, RunPod spend), number of iterations.
- **Result:** what came out, and how it was verified (checks, visual review, field measurement).
- **Used by:** who outside saw or used it, and what decision it informed. `nobody yet` is a valid answer.
- **Verdict:** keep | kill | fold, and one sentence why.
```

## Existing work, verdicts pending

Facts are from each `product.yaml`. Cost, use and verdict were not recorded at the time.

| Experiment | What it tried | Verdict | Why |
|---|---|---|---|
| highland/water | Unit 107 domestic-water pipe model from P3.02/P4.01, 3D viewer and review | | |
| highland/risers | Existing risers and mains traced from drawings, proposed PEX-A replacement, review renders | | |
| highland/exterior | Exterior massing study from drawings and photos | | |
| highland/exterior-reconciliation | Source controls and native Blender rebuild compared with historical delivery records | | |
| highland/installation | Repipe installation method model, 90-second film, immersive and studio cuts | | |
| highland/repipe | Parallel-install, unit-by-unit cutover sequence (interactive page and MP4) | | |
| highland/walkthrough | Lobby-to-corridor walkthrough: drone tour, native Blender film, archviz stills, RunPod cinema cut | | |
| meydenbauer-b/underslab | Under-slab waste re-pipe bid model: takeoff, slab allowance, realism views, 4D films | | |
| meydenbauer-b/agency-film | 75-second presentation film of the re-pipe approach | | |
| meydenbauer-b/explorer | Evidence-first interactive explorer on the CIE state | | |
| meydenbauer-b/b101-review | B-101 v4 acceptance review and v4.1 revision | | |
| meydenbauer-b/vdc-recovery | Recovered VDC and B101 v4 data reconciled against canonical state | | |
| spec pipeline (`bm build`) | YAML spec → verified model, review renders, report; 6 specs across 4 small sites | | |
| CIE kernel (`src/cie/`) | One canonical state feeding takeoff, model, explorer and film; Meydenbauer only so far | | |

## Entries

None yet. The first should be the cold run in [COLD_RUN.md](COLD_RUN.md).
