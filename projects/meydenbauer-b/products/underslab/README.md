# 101 Meydenbauer, Building B — under-slab waste re-pipe bid model

KEAD project 25-048. Bid due **October 30, 2026, 5:00 PM** (Invitation to Bid 00 11 16 §1.3).

This model converts the bid set's foundation-level waste plan into measured quantities and a 3D
view of the slab cuts, trenches and pipe. Its purpose is the bid. It tests the **700 SF slab
allowance** (Bid Form Allowance No. 7, Addendum 1), measures pipe by size, and sizes the
excavation that will be hauled through occupied units. It is an estimating and coordination aid,
not a contract document.

Results, renders and draft RFIs: [projects/meydenbauer-b/deliverables/underslab](../../deliverables/underslab/README.md).

## Pipeline

```bash
uv sync --group pdf
# sources/ is git-ignored; put the bid set there first
uv run python projects/meydenbauer-b/products/underslab/prepare.py sources/meydenbauer/exhibit-a-bid-set.pdf
uv run python projects/meydenbauer-b/products/underslab/takeoff.py          # takeoff.json + workbook
uv run python projects/meydenbauer-b/products/underslab/build.py            # .blend, .glb, 8 renders (~11 min, 4 cores)
uv run python projects/meydenbauer-b/products/underslab/build.py --no-render   # model + checks only (~3 s)
```

| Step | Reads | Writes |
| --- | --- | --- |
| `prepare.py` | Exhibit A, page 6 (P1.02) | `meydenbauer-b.spec.json`, `build/meydenbauer-b/underlay_P1.02.png` |
| `takeoff.py` | spec | `build/meydenbauer-b/takeoff.json`, `Meydenbauer-B-underslab-takeoff.xlsx` |
| `build.py` | spec + takeoff | `.blend` (underlay packed), `.glb` (element properties as extras), `present-*.png`, `review-*.png`, `model-checks.json` |

4D films (construction-phase model in [REALISM.md](REALISM.md); results in
[projects/meydenbauer-b/deliverables/underslab/anim](../../deliverables/underslab/anim/README.md)):

```bash
uv run python projects/meydenbauer-b/products/underslab/schedule.py         # strawman unit-by-unit schedule (rates assumed)
uv run python projects/meydenbauer-b/products/underslab/logistics.py        # entries, staging, haul routes (assumed, SOR Fig 8)
uv run python projects/meydenbauer-b/products/underslab/animate.py --plan sequence --fps 30 --no-render   # .blend + 92 + 44 checks
uv run python projects/meydenbauer-b/products/underslab/animate.py --plan sequence --fps 30 --stills --res 0.4 --samples 12
PLAN=sequence bash projects/meydenbauer-b/products/underslab/runpod_animate.sh setup   # then bench, render 2, finish
```

| Step | Reads | Writes |
| --- | --- | --- |
| `schedule.py` | takeoff | `meydenbauer-b.schedule.json` (days per unit and phase, haul quantities) |
| `logistics.py` | shell, takeoff, schedule | `meydenbauer-b.logistics.json` (entries, site massing, routes, bins) |
| `animate.py` | realism scene + the two above | `Meydenbauer-B-4D.blend` (overview) or `Meydenbauer-B-4D-sequence.blend`, frames |
| `anim_finish.py` | frames or a clean master | MP4 with HUD, clean master, poster |

## Method

1. **Calibration.** P1.02 is a vector CAD plot at 9 pt/ft (1/8" = 1'-0" on a 36×24 sheet). The grid
   bubbles A–M measure 8.998 pt/ft against the dimension string total of 160'-5½". Rows 1–6
   measure 9.009 pt/ft against 66'-4". Origin is grid A/1. +x runs south along the building, and
   +y runs west.
2. **Routes.** New pipe is the 0.96 pt black pen on P1.02. Existing pipe to remain is dashed in
   another pen and is excluded. That exclusion covers the B-101 kitchen run, which was previously
   replaced. Strokes are grouped into four unit networks. Four drafting gaps of up to 2.4 pt were
   rejoined. Branch ends drawn up to 2.5 pt short of a trunk are snapped and noded. The 2-way
   cleanout symbol at each POC is drawn with the same pen, and its strokes are dropped.
3. **Reviewed table.** Keynote circles and riser hexagons are drawn as graphics, not text. Tie-ins
   and stack ends were therefore identified by eye. They are listed in `REVIEWED` in
   `prepare.py`, with the label each one comes from.
4. **Sizes.** Runs from the POC to a stack, and to the unit's most remote end, are the 4" building
   drain (P1.02 "4" WASTE, TYP."). Other branches take the largest fixture they serve: 3" for
   WC/WB per the "3"W UP" leaders, and 2" for LAV, SHR, TUB and KS per the "2"W UP" leaders and
   keynotes 4–7.
5. **Trench.** Each drawn route is widened to the 2'-0" typical trench in detail 10/P5.1. The
   minimum there is 1'-3". The union of these strips is the slab cut, so parallel runs are not
   double-counted. Scenarios:
   - **S1:** the trench alone.
   - **S2:** adds a 3'×3' working pit at each of the 30 fixture or stack connections (assumed).
   - **S3:** also widens the cut to 4'-0" wherever the trench reaches 4'-0" deep (assumed
     protective system).

   The first 18" from each POC is outside the footprint (SOR) and is excluded from slab SF.
6. **Depth.** POC inverts are not documented ("MATCH EX. I.E."). Each case uses one of the SOR's
   recorded depths: 2.5, 3.5 or 4.5 ft below the finished floor. Depth rises at ¼"/ft along the
   flow path. The trench bottom is 4" below the pipe (2/P5.0). Excavation is measured on a 3"
   grid inside the footprint, below an assumed 4" slab.

## Checks (`build.py` exits 1 on failure)

- Model run count equals the spec (136 runs).
- Tagged length equals the takeoff, and modelled plan length equals tagged length (312.75 LF).
- There are four POC cleanouts.
- Pipe centrelines lie within the expected depth band.

`prepare.py` also asserts four networks, full connectivity from each POC, and at most 2 ft of
unexplained looped strokes per unit. The 1.4 ft kept is the B-102 tub connection.

## Provenance

| Element | Status | Basis |
| --- | --- | --- |
| Route plan position | provisional | scaled from P1.02 vector linework; scale verified. KEAD calls the design diagrammatic and requires stack locations to be field verified. |
| Pipe size | provisional | P1.02 labels and keynotes, using the rule above |
| 4" and 6" OD | confirmed | SOR Figures 3–4 (Viterra ABS) |
| 2" and 3" OD | assumed | standard IPS OD |
| Trench width 2'-0" | confirmed | 10/P5.1 |
| Pits, deep widening, slab thickness, swell | assumed | see the workbook *Inputs* sheet |
| Pipe elevations and trench depths | assumed | SOR recorded range; actual inverts unknown |
| Slab extent (grid A–M × 1–6 rectangle) | assumed | massing only |
| Riser heights | assumed | stacks show the 36" minimum exposure (P1.01 vertical limits note) |

The underlay in the renders and `.blend` is KEAD's drawing. Keep it within the bid team.
