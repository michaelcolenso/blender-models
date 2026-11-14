# Cold run: the repeatability test

One project, started from nothing, timed, with the reuse counted. It answers whether the workflow in
[METHOD.md](METHOD.md) is repeatable or whether each project is still a custom build.

## Choosing the project

- Not Highland or Meydenbauer, and not a site already in `projects/`.
- One scope and one drawing set. A single repair detail or one unit's piping is enough.
- Somewhere you can physically measure afterwards. Without field access the run cannot produce an accuracy
  number, only a speed number.
- Source PDFs go in `projects/<site>/sources/` (git-ignored); only `manifest.json` is committed.

## Rules during the run

- Start from `uv run bm new <site>`. Follow the `model-from-drawings` skill and METHOD.md as written.
- Copying code from another site's product folder is allowed, and every copy is logged. That log is the list
  of what belongs in `src/bmodels/`.
- Every place the documented workflow was wrong, missing or had to be worked around gets one line in the
  friction log. Do not fix the docs mid-run; fix them after.
- No film or presentation work until stage 5 is closed.
- Stop the clock when waiting on a person or a render; record attention time and wall time separately.

## Stages and what to record

| # | Stage | Done when | Attention (h) | Wall (h) | Notes |
|---|---|---|---|---|---|
| 1 | Intake: manifest, sheet inventory, governing revision | `sources/manifest.json` committed | | | |
| 2 | Calibration: each sheet from its own dimension strings | calibration residuals recorded per sheet | | | |
| 3 | Spec: elements with provenance, checks with sources | `bm check` passes | | | |
| 4 | Build and verify | `bm build <site>` shows `PASS` | | | |
| 5 | Visual review against the drawings | `review:` block recorded in the spec | | | |
| 6 | Takeoff or other decision output | quantities with their source and method | | | |
| 7 | Field check | at least five dimensions measured on site | | | |
| 8 | One visualization or tool from the verified model | handed to one outside person | | | |

## Result table (commit this filled in)

| Measure | Value |
|---|---|
| Site and scope | |
| Documents (sheets, dimensioned or NTS, photos) | |
| Attention hours, stages 1 to 6 | |
| Wall hours, stages 1 to 6 | |
| Elements: confirmed / provisional / assumed | |
| Document-driven checks passing | |
| Code reused unchanged from `src/bmodels/` (modules) | |
| Code copied from product folders (files, lines) | |
| New code written (lines) | |
| Friction-log entries | |
| Field deltas: each measured dimension, model value, field value, difference | |
| Largest and median absolute field delta (in) | |
| Assumed items upgraded or corrected by the field check | |
| Outside person who used the stage-8 output, and what they did with it | |

## Reading the result

- **Repeatable** if stages 1 to 6 needed no copied product code and the friction log is short. Then the next
  investment is speed and visualization.
- **Not yet repeatable** if most of the time went to code copied or rewritten. Then promote that code into
  `src/bmodels/` and run again on another project before building anything else.
- **Not accurate enough** if field deltas exceed what the tolerances in the spec claimed. Then the calibration
  and provenance steps need work before any output is shown as more than a sketch.
- **Stop condition:** if two cold runs give field deltas no better than reading the PDFs directly, the model
  is not adding accuracy, and the takeoff and document-reconciliation scripts are the useful part.

Add the outcome as an entry in [EXPERIMENTS.md](EXPERIMENTS.md).
