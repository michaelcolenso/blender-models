# Building B: construction-phase realism model

A planning model for the bid team, not for owners or residents. It shows what the crew will face
in the ground-floor units: the saw-cut slab, the open trench at its modelled depth in soil, the
bedding and new ABS, the record footings where the trench meets them, and the occupied-unit
conditions around the work.

Rendered views: [deliverables/meydenbauer-b/realism](../../deliverables/meydenbauer-b/realism/).

## Pipeline

```bash
uv run python projects/meydenbauer-b/shell.py sources/meydenbauer/exhibit-a-bid-set.pdf   # walls, openings, rooms, tubs (P2.1)
uv run python projects/meydenbauer-b/structure.py        # record footings + trench clash table
uv run python projects/meydenbauer-b/assets.py           # Poly Haven CC0 textures/props, MD5-checked
uv run python projects/meydenbauer-b/realism.py --no-render   # .blend + checks (about 10 s)
uv run python projects/meydenbauer-b/realism.py --only b104_kitchen_run --samples 32 --res 0.6
bash projects/meydenbauer-b/runpod_render.sh setup && bash projects/meydenbauer-b/runpod_render.sh render final
```

`shell.py` and `exb_overlay.py` need the PDFs in the git-ignored `sources/` folder.
`structure.py`, `realism.py` and the RunPod script need only the committed JSON.

## Sources and what each layer is

| Layer | Source | Status |
| --- | --- | --- |
| New waste routes and sizes | P1.02 vector linework; scale verified | provisional |
| Walls, door and window openings | P2.1 double lines, paired 3–13 in apart; scale verified | provisional |
| Room ceiling heights | P2.1 room tags (KEAD Matterport), for example `CH: 8' - 5"` | confirmed |
| Tubs and showers | P2.1 fixture symbols; type from the nearest P1.02 end | provisional |
| Exterior and core footings | Exhibit B FPB1/FPB2, registered to the grid; 2'-6" wide, bottom 3'-4" below FF | provisional; the record set is "for reference only" |
| Trench plan | S2 footprint: 2'-0" (10/P5.1) plus 3'×3' pits | plan confirmed, pits assumed |
| Trench and pipe depth | tie-in invert 3.5 ft, falling ¼"/ft | **assumed** |
| Slab 4", vapor barrier, soil | not documented | **assumed** |
| Finishes | room type; B-104 per the Addendum 1 custom finish schedule (EHF-2 oak, NS-2 12×24 porcelain, NS-1 mosaic) | assumed by room |
| Ram Board within 5 ft of the work; poly dust walls 3.5 ft out; spring poles; LED work lights | typical practice | **assumed** layout |
| Props: cement bags, buckets, tools, pulled toilets | Poly Haven CC0 and procedural | illustrative |

Wall extraction check: 8 of the 20 rooms that carry a measured area close within 6% of it.
The other 12 open onto glazing or merge across a gap the extraction did not close. Walls are
good enough for views and protection layout, but not for measuring rooms.

Window sill and head heights come from the listing photo of the west elevation and are assumed.
The kitchen cabinet run was left out because no drawing shows it.

## Structure check (structure.py)

The record set shows a 2'-6"-wide strip footing under every exterior wall, with its bottom at
3'-4" below the finished floor (D2 sections 10 and 11). The table uses the S2 trench and a
tie-in invert of 3.5 ft.

| Unit | Tie-in crossing (detailed, A-A/P5.1) | Other trench over the footing | Trench below the footing bottom within 1.5 ft of it |
| --- | ---: | ---: | ---: |
| B-101 | 5.2 LF | 5.3 LF | 14.3 LF |
| B-102 | 6.0 LF | 7.0 LF | 7.9 LF |
| B-103 | 6.0 LF | 7.9 LF | 14.7 LF |
| B-104 | 4.9 LF | 6.5 LF | 7.5 LF |

At a 2.5 ft invert, nothing goes below the footing bottom. At 4.5 ft, B-104's 4" run to the
kitchen stack also passes the lower stair-core footing for 8.5 LF.

The lav risers stand at the exterior wall. That puts them over the footing's inside projection,
so the lav branches must run on top of or beside the footing to reach them. This is a screening
check against hand-drafted record drawings and is not a structural finding. Each conflict needs
the SOR Note 5 structural protocol before cutting.

## Checks

`realism.py` exits 1 if:

- the modelled pipe length differs from the takeoff (312.74 LF);
- the soil boolean fails;
- any camera stands inside a wall.

Renders get a caption band naming every assumed layer.
