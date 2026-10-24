"""
101 Meydenbauer Condominiums — Building B Underground DW Re-Pipe
Three-pass Blender bpy generator for 4D construction phasing.

REVISION v4 — B-101 demolition fittings / carriers / cut locations
Extends the calibrated v3 selective-demolition model with existing fitting
assemblies, first-floor P-traps, wall-hung WC carriers/flanges, rule-based
vertical cut targets, prior-ABS/exterior disconnect planes, and temporary
pipe-support indicators. Concealed legacy fitting type and final cut position
remain explicitly FIELD_VERIFY rather than being presented as surveyed facts.

PASS 1
    Collections, Grid, Structural Shell, Slab Boolean Trench Cutters
PASS 2
    Existing & New ABS Plumbing Curves, Fittings, Trench Backfill/Rebar Layers
PASS 3
    Interior Room Partitions, Custom Finishes/Materials, Fixtures,
    PHASE_CONTROLLER animation drivers

SOURCE BASIS / MODELING INTENT
- Exhibit A plumbing bid set: P1.01 demolition, P1.02 foundation plan,
  P2.1 first-floor waste plan, P3.1/P3.2 enlarged plans, P5.0/P5.1 details.
- Addendum #1 (2026-10-16), Scope of Repair, Project Manual.
- User-supplied 4D modeling brief and finish schedule.

IMPORTANT MODEL CONTROL NOTE
The contract drawings explicitly require field verification of actual routing,
invert elevations, stack locations, and connection points before installation.
Accordingly, plumbing geometry below is generated from EDITABLE route-control
points in ROUTE_DATA rather than hidden hard-coded mesh coordinates. It is a
coordination/visualization model, not a substitute for verified as-built survey.

COORDINATE CONVENTION
- 1 Blender Unit = 1 foot (scene scale_length = 0.3048 m).
- X = North -> South along lettered grids (Unit B-101 at low X).
- Y = East -> West; east foundation face is near Y=0, lakeside west is +Y.
- Z = vertical; structural slab top = Z=0.

GRID RECONCILIATION
The permit sheets P1.01/P1.02 label the longitudinal sequence A through M.
The user's prose brief shifted labels after H (H->J ... M->N). This script uses
A..M to match the bid-set drawings. The rendered bid sheet dimension chain
shows H-I = 27'-6 1/2", giving a total A-M length of 160'-5 1/2".

TARGET BLENDER
Blender 4.x / 5.x, with compatibility fallbacks for Blender 3.6 LTS. Uses no external add-ons.
"""

from __future__ import annotations

import bpy
import math
from mathutils import Vector

# -----------------------------------------------------------------------------
# RUN CONTROL
# -----------------------------------------------------------------------------

RUN_PASSES = (1, 2, 3)   # Set to e.g. (1,), (2,), (3,), or (2, 3)
VALIDATE_AFTER_RUN = True

PROJECT_TAG = "MEYD_25-048"

# -----------------------------------------------------------------------------
# UNITS / DIMENSION HELPERS
# -----------------------------------------------------------------------------

INCH = 1.0 / 12.0


def ft(feet=0.0, inches=0.0):
    return float(feet) + float(inches) / 12.0


def inch(value):
    return float(value) / 12.0


def od_ft(nominal_in):
    """Schedule 40 ABS outside diameters used for visualization."""
    return {
        2: inch(2.375),
        3: inch(3.500),
        4: inch(4.500),   # source brief
        6: inch(6.625),   # Viterra / source brief
        8: inch(8.625),   # existing side-sewer context only
    }[int(nominal_in)]


SLAB_THICKNESS = inch(5.5)       # midpoint of 5"–6" documented range
EXT_WALL_THICKNESS = inch(8.0)
PRECAST_WALL_THICKNESS = inch(6.5)  # visualization midpoint of 5"–8"
PARTITION_THICKNESS = inch(4.5)
GROUND_FLOOR_HEIGHT = ft(8, 6)
STORY_HEIGHT = ft(9, 0)
PIPE_SLOPE = inch(0.25)          # ft drop per horizontal foot = 1/4" per foot
TRENCH_MAIN_W = ft(2, 0)
TRENCH_BRANCH_W = ft(1, 6)
TRENCH_DEPTH = ft(4, 6)
SIDE_SEWER_Y = -ft(20, 0)
SIDE_SEWER_Z = -ft(4, 0)  # representative context invert within documented 2.5-4.5 ft depth range
EAST_GARAGE_NEAR_FACE_Y = -ft(10, 0)

# -----------------------------------------------------------------------------
# GRID / BUILDING DATA — P1.01 / P1.02 dimensional chain
# -----------------------------------------------------------------------------

LONG_GRID_LABELS = list("ABCDEFGHIJKLM")
LONG_GRID_SPANS = [
    ft(31, 5), ft(3, 3), ft(8, 0), ft(3, 3),
    ft(27, 1), ft(7, 0), ft(7, 0), ft(27, 6.5),
    ft(3, 3), ft(8, 0), ft(3, 3), ft(31, 5),
]

# P1.01/P1.02 drawing chain: 1-2 6'-4", 2-3 19'-10", 3-4 19'-5",
# 4-5 14'-5", 5-6 6'-4". This supersedes the extra span accidentally
# included in the prose brief.
TRANS_GRID_LABELS = ["1", "2", "3", "4", "5", "6"]
TRANS_GRID_SPANS = [ft(6, 4), ft(19, 10), ft(19, 5), ft(14, 5), ft(6, 4)]


def cumulative_stations(labels, spans):
    stations = {labels[0]: 0.0}
    x = 0.0
    for i, span in enumerate(spans):
        x += span
        stations[labels[i + 1]] = x
    return stations


GX = cumulative_stations(LONG_GRID_LABELS, LONG_GRID_SPANS)
GY = cumulative_stations(TRANS_GRID_LABELS, TRANS_GRID_SPANS)
BUILDING_LENGTH = GX["M"]
BUILDING_WIDTH = GY["6"]

UNIT_RANGES = {
    "B101": (GX["A"], GX["E"]),
    "B102": (GX["E"], GX["H"]),
    "B103": (GX["H"], GX["L"]),
    "B104": (GX["L"], GX["M"]),
}

# -----------------------------------------------------------------------------
# COLLECTION HIERARCHY
# -----------------------------------------------------------------------------

COLLECTION_TREE = {
    "00_Site_&_Context": [
        "Bldg_B_Shell_&_Upper_Stacks",
        "East_Garages_&_Planter_Strip",
        "Side_Sewer_Main_6in",
        "Staging_Area",
    ],
    "01_Structural_Base": [
        "Subgrade_&_Soil",
        "Foundation_Footings",
        "Precast_Concrete_Walls",
        "Wood_Stud_Partitions",
        "Concrete_Slab_Unmodified",
    ],
    "02_Existing_Conditions_&_Demo": [
        "Ex_Cast_Iron_Pipes_DEMO",
        "Ex_Unit101_&_104_Prior_ABS_REMAIN",
        "Concrete_Slab_Trench_Cuts_DEMO",
        "Drywall_Cutouts_DEMO",
    ],
    "03_New_Plumbing_DWV": [
        "New_ABS_UnderSlab_4in_6in",
        "New_ABS_Branches_&_Traps",
        "New_Stack_TieIns_&_Cleanouts",
        "Firestop_&_Sleeves",
    ],
    "04_Trench_Backfill_&_Slab_Pourback": [
        "Pipe_Zone_Bedding",
        "General_Trench_Backfill",
        "Vapor_Barrier_Stegowrap",
        "Rebar_Dowels_&_Grid",
        "Concrete_Pourback",
    ],
    "05_Wall_&_Floor_Substrates": [
        "Wall_Framing_Nailers",
        "Gypsum_Board_Patches",
        "Vapor_Mitigating_Epoxy_Primer",
        "Radiant_Heating_Coils",
        "Waterproofing_Membrane",
    ],
    "06_Interior_Finishes_&_Fixtures": [
        "Unit_B101_Finishes",
        "Unit_B102_Finishes",
        "Unit_B103_Finishes",
        "Unit_B104_Finishes",
        "Cabinets_&_Countertops",
        "Plumbing_Fixtures",
        "Temporary_Protection",
        "As_Built_Callout_Overlay",
    ],
}

# -----------------------------------------------------------------------------
# ROUTE CONTROL DATA
# -----------------------------------------------------------------------------


def gx_between(a, b, t):
    """Interpolate an X station between lettered grids."""
    return GX[a] + (GX[b] - GX[a]) * float(t)


def gy_between(a, b, t):
    """Interpolate a Y station between numbered grids."""
    return GY[a] + (GY[b] - GY[a]) * float(t)


def _route_record(main_4, exit_xy, branches_3, branches_2, fixture_pts,
                  prior_abs_4=None, raised_floor_4=None, source_note="",
                  branch3_stubs=None, branch2_stubs=None):
    """Create one auditable route record used by all three passes."""
    tie_xy = (exit_xy[0], -ft(1, 6))  # scope boundary: 18 in beyond east foundation face
    lateral_6 = [exit_xy, tie_xy]
    lateral_6_context = [tie_xy, (exit_xy[0], SIDE_SEWER_Y)]
    rec = {
        "exit_x": exit_xy[0],
        "main_4": main_4,
        "lateral_6": lateral_6,
        "lateral_6_context": lateral_6_context,
        "branches_3": branches_3,
        "branches_2": branches_2,
        "branch3_stubs": branch3_stubs or {},
        "branch2_stubs": branch2_stubs or {},
        "fixture_pts": fixture_pts,
        "prior_abs_4": prior_abs_4 or [],
        "source_note": source_note,
        "field_verify": True,
    }
    if raised_floor_4:
        rec["raised_floor_4"] = raised_floor_4
    return rec


def unit_route_data():
    """
    P1.02/P3.1/P3.2 traced control points, expressed against the drawing grid.

    These are intentionally more literal than the first-pass schematic routes:
    - the 4 in to 6 in transition is at/near Grid 1 / east foundation face;
    - replacement 6 in laterals stop 18 in beyond the wall; existing 6 in context then continues to the 8 in SS main;
    - internal mains reproduce the major orthogonal/diagonal bends shown on P1.02;
    - B-101 and B-104 retained ABS is split out so new pipe does not duplicate it;
    - branch endpoints land on explicit main nodes so Pass 2 can force Z continuity.

    They are still coordination control points, not surveyed as-built inverts. The
    drawings explicitly require field verification before installation.
    """
    data = {}

    # ------------------------------------------------------------------ B-101 — calibrated against P1.02 / P3.1 / P1.01
    #
    # B-101 is intentionally treated as the calibration unit before the other
    # units are retraced. The bid drawings show two distinct 4-inch systems:
    #   (1) NEW replacement work: a near-straight wet-core main from the Grid-3
    #       laundry/tie-in north/east to the 4->6 transition at Grid 1; and
    #   (2) PRIOR ABS REMAIN: the previously repaired kitchen/dining leg from
    #       the kitchen back to that Grid-3 tie-in.
    #
    # The prior v2 route incorrectly converted the retained kitchen/dining leg
    # into a diagonal piece of the new main. These controls follow the drawn
    # topology instead. Exact inverts and as-found fitting locations remain
    # FIELD VERIFY items per P1.02/SOR.
    x_main = gx_between("A", "B", 0.74)

    j_exit = (x_main, GY["1"])
    j_lav_top = (x_main, 3.25)
    j_sh_upper = (x_main, 10.00)
    j_wc_common = (x_main, 12.00)
    j_bath_lower = (x_main, 13.25)
    j_prior_tie = (x_main, 27.40)

    # Retained prior 4-inch ABS: kitchen -> long dining run -> 45 -> Grid-3 tie.
    # Plan coordinates are traced from the dashed P3.1/P1.02 prior-repair line.
    b101_kitchen_4up = (38.85, 39.20)
    b101_prior_run = (24.20, 39.20)
    b101_prior_45 = (x_main, 38.20)

    data["B101"] = _route_record(
        # Upstream -> downstream. New replacement starts at the prior-ABS tie
        # and proceeds through the wet core to the exterior transition.
        main_4=[
            j_prior_tie,
            j_bath_lower,
            j_wc_common,
            j_sh_upper,
            j_lav_top,
            j_exit,
        ],
        exit_xy=j_exit,
        branches_3={
            # Unique common branch edges. Fixture stubs below attach to these
            # branches, avoiding duplicate coincident pipe geometry.
            "wc_common": [
                (15.10, 12.80),
                (22.45, 12.80),
                j_wc_common,
            ],
            "laundry": [
                (22.65, 27.40),
                j_prior_tie,
            ],
        },
        branch3_stubs={
            "wc_upper": {
                "parent": "wc_common",
                "points": [(14.90, 11.65), (16.05, 12.80)],
            },
            "wc_lower": {
                "parent": "wc_common",
                "points": [(13.35, 13.50), (14.35, 13.50), (15.10, 12.80)],
            },
        },
        branches_2={
            # Shared branch trunks are unique geometry; individual fixture
            # stubs connect to explicit nodes/segments on these trunks.
            "lav_top_common": [
                (16.10, 4.00),
                (19.30, 4.00),
                (22.50, 4.00),
                j_lav_top,
            ],
            "shower_upper": [
                (18.40, 10.80),
                (22.45, 10.80),
                j_sh_upper,
            ],
            "bath_lower_common": [
                (16.85, 14.00),
                (19.35, 14.00),
                (22.45, 14.00),
                j_bath_lower,
            ],
        },
        branch2_stubs={
            "lav_top_left": {
                "parent": "lav_top_common",
                "points": [(15.30, 0.35), (15.30, 3.20), (16.10, 4.00)],
            },
            "lav_top_right": {
                "parent": "lav_top_common",
                "points": [(18.50, 0.35), (18.50, 3.20), (19.30, 4.00)],
            },
            "shower_lower": {
                "parent": "bath_lower_common",
                "points": [(15.90, 15.45), (16.85, 14.00)],
            },
            "lav_lower": {
                "parent": "bath_lower_common",
                "points": [(19.35, 15.35), (19.35, 14.00)],
            },
        },
        fixture_pts={
            "WC_N": (14.90, 11.65),
            "SH_N": (18.40, 10.80),
            "LAV_N": (15.30, 0.35),
            "WC_S": (13.35, 13.50),
            "TUB_S": (15.90, 15.45),
            "LAV_S": (19.35, 15.35),
            "WB": (22.65, 27.40),
            "KS": b101_kitchen_4up,
            "WH": (GX["B"] - 0.65, 27.10),
        },
        prior_abs_4=[
            b101_kitchen_4up,
            b101_prior_run,
            b101_prior_45,
            j_prior_tie,
        ],
        source_note=(
            "B101 CALIBRATION: P1.02/P3.1/P1.01. New 4in main is wet-core "
            "Grid-3 tie to Grid-1 exit; prior kitchen/dining 4in ABS remains. "
            "Fixture branches traced to visible plan elbows; field verify inverts/fittings."
        ),
    )

    # ------------------------------------------------------------------ B-102
    x_exit = gx_between("F", "G", 0.18)
    j_exit = (x_exit, GY["1"])
    j_lav = (gx_between("E", "F", 0.86), gy_between("1", "2", 0.74))
    j_bath_n = (gx_between("E", "F", 0.83), gy_between("2", "3", 0.34))
    j_bath_s = (gx_between("E", "F", 0.80), gy_between("2", "3", 0.61))
    j_laundry = (gx_between("E", "F", 0.72), gy_between("3", "4", 0.06))
    j_kitchen = (gx_between("E", "F", 0.20), gy_between("3", "4", 0.68))
    data["B102"] = _route_record(
        main_4=[j_kitchen, j_laundry, j_bath_s, j_bath_n, j_lav, j_exit],
        exit_xy=j_exit,
        branches_3={
            "bath_n": [(gx_between("E", "F", 0.66), gy_between("2", "3", 0.28)), j_bath_n],
            "bath_s": [(gx_between("E", "F", 0.62), gy_between("2", "3", 0.53)), j_bath_s],
            "laundry": [(gx_between("E", "F", 0.68), gy_between("3", "4", 0.08)), j_laundry],
            "kitchen": [(gx_between("E", "F", 0.16), gy_between("3", "4", 0.72)), j_kitchen],
        },
        branches_2={
            "lav_n": [(gx_between("E", "F", 0.63), gy_between("1", "2", 0.15)), j_lav],
            "lav_s": [(gx_between("E", "F", 0.58), gy_between("2", "3", 0.48)), j_bath_s],
        },
        fixture_pts={
            "WC_N": (gx_between("E", "F", 0.67), gy_between("2", "3", 0.29)),
            "SH_N": (gx_between("E", "F", 0.63), gy_between("2", "3", 0.43)),
            "LAV_N": (gx_between("E", "F", 0.63), gy_between("1", "2", 0.15)),
            "WC_S": (gx_between("E", "F", 0.62), gy_between("2", "3", 0.53)),
            "TUB_S": (gx_between("E", "F", 0.72), gy_between("2", "3", 0.45)),
            "LAV_S": (gx_between("E", "F", 0.58), gy_between("2", "3", 0.48)),
            "WB": (gx_between("E", "F", 0.68), gy_between("3", "4", 0.08)),
            "KS": (gx_between("E", "F", 0.16), gy_between("3", "4", 0.72)),
            "WH": (gx_between("E", "F", 0.78), gy_between("3", "4", 0.10)),
        },
        source_note="P1.02 + P3.1 traced: diagonal bath-to-east main, laundry and kitchen stack connections",
    )

    # ------------------------------------------------------------------ B-103
    x_exit = gx_between("H", "I", 0.10)
    j_exit = (x_exit, GY["1"])
    j_lav = (x_exit, gy_between("1", "2", 0.76))
    j_bath_n = (x_exit, gy_between("2", "3", 0.30))
    j_bath_s = (x_exit, gy_between("2", "3", 0.56))
    j_laundry = (gx_between("H", "I", 0.46), gy_between("3", "4", 0.07))
    data["B103"] = _route_record(
        main_4=[j_laundry, j_bath_s, j_bath_n, j_lav, j_exit],
        exit_xy=j_exit,
        branches_3={
            "bath_n": [(gx_between("H", "I", 0.31), gy_between("2", "3", 0.28)), j_bath_n],
            "bath_s": [(gx_between("H", "I", 0.38), gy_between("2", "3", 0.52)), j_bath_s],
            "laundry": [(gx_between("H", "I", 0.47), gy_between("3", "4", 0.08)), j_laundry],
        },
        branches_2={
            "lav_n": [(gx_between("H", "I", 0.29), gy_between("1", "2", 0.15)), j_lav],
            "lav_s": [(gx_between("H", "I", 0.42), gy_between("2", "3", 0.44)), j_bath_s],
        },
        fixture_pts={
            "WC_N": (gx_between("H", "I", 0.35), gy_between("2", "3", 0.29)),
            "SH_N": (gx_between("H", "I", 0.30), gy_between("2", "3", 0.39)),
            "LAV_N": (gx_between("H", "I", 0.29), gy_between("1", "2", 0.15)),
            "WC_S": (gx_between("H", "I", 0.43), gy_between("2", "3", 0.50)),
            "TUB_S": (gx_between("H", "I", 0.31), gy_between("2", "3", 0.56)),
            "LAV_S": (gx_between("H", "I", 0.42), gy_between("2", "3", 0.44)),
            "WB": (gx_between("H", "I", 0.47), gy_between("3", "4", 0.08)),
            "KS": (gx_between("H", "I", 0.72), gy_between("3", "4", 0.72)),
            "WH": (gx_between("H", "I", 0.61), gy_between("3", "4", 0.12)),
        },
        raised_floor_4=[
            (gx_between("H", "I", 0.72), gy_between("3", "4", 0.72), ft(0, 5)),
            (gx_between("J", "K", 0.70), gy_between("3", "4", 0.72), ft(0, 5)),
            (gx_between("J", "K", 0.70), gy_between("3", "4", 0.10), ft(0, 5)),
            (gx_between("J", "K", 0.70), gy_between("3", "4", 0.10), -ft(1, 8)),
        ],
        source_note="P1.02 + P3.2 traced: H-side east lateral; B-103 raised-floor 4in kitchen route retained as editable 3D path",
    )

    # ------------------------------------------------------------------ B-104
    x_exit = gx_between("L", "M", 0.31)
    j_exit = (x_exit, GY["1"])
    j_lav = (x_exit, gy_between("1", "2", 0.76))
    j_bath_n = (x_exit, gy_between("2", "3", 0.30))
    j_bath_s = (x_exit, gy_between("2", "3", 0.55))
    j_laundry = (x_exit, gy_between("3", "4", 0.08))
    j_kitchen = (gx_between("K", "L", 0.72), gy_between("3", "4", 0.68))
    b104_prior_start = (gx_between("J", "K", 0.82), gy_between("3", "4", 0.73))
    data["B104"] = _route_record(
        main_4=[j_kitchen, j_laundry, j_bath_s, j_bath_n, j_lav, j_exit],
        exit_xy=j_exit,
        branches_3={
            "bath_n": [(gx_between("L", "M", 0.42), gy_between("2", "3", 0.28)), j_bath_n],
            "bath_s": [(gx_between("L", "M", 0.38), gy_between("2", "3", 0.52)), j_bath_s],
            "laundry": [(gx_between("K", "L", 0.88), gy_between("3", "4", 0.08)), j_laundry],
        },
        branches_2={
            "lav_n": [(gx_between("L", "M", 0.42), gy_between("1", "2", 0.15)), j_lav],
            "lav_s": [(gx_between("L", "M", 0.21), gy_between("2", "3", 0.46)), j_bath_s],
        },
        fixture_pts={
            "WC_N": (gx_between("L", "M", 0.40), gy_between("2", "3", 0.29)),
            "SH_N": (gx_between("L", "M", 0.29), gy_between("2", "3", 0.36)),
            "LAV_N": (gx_between("L", "M", 0.42), gy_between("1", "2", 0.15)),
            "WC_S": (gx_between("L", "M", 0.38), gy_between("2", "3", 0.52)),
            "TUB_S": (gx_between("L", "M", 0.30), gy_between("2", "3", 0.63)),
            "LAV_S": (gx_between("L", "M", 0.21), gy_between("2", "3", 0.46)),
            "WB": (gx_between("K", "L", 0.88), gy_between("3", "4", 0.08)),
            "KS": b104_prior_start,
            "WH": (gx_between("L", "M", 0.12), gy_between("3", "4", 0.11)),
        },
        prior_abs_4=[b104_prior_start, j_kitchen],
        source_note="P1.02 + P3.2 traced: L-side east lateral, bath/laundry main, retained B-104 kitchen/family ABS repair",
    )

    return data


ROUTE_DATA = unit_route_data()

# Retained 4 in ABS is kept as its own route so Pass 1 does not cut it again and
# Pass 2 does not draw a duplicate new pipe over it.
PRIOR_ABS_REMAIN = {
    unit: d["prior_abs_4"] for unit, d in ROUTE_DATA.items() if d.get("prior_abs_4")
}

# -----------------------------------------------------------------------------
# GENERAL HELPERS
# -----------------------------------------------------------------------------


def tag(obj, pass_id, source=""):
    obj["MEYD_PROJECT"] = PROJECT_TAG
    obj["MEYD_PASS"] = int(pass_id)
    if source:
        obj["MEYD_SOURCE"] = source
    return obj


def scene_setup():
    scene = bpy.context.scene
    scene.unit_settings.system = 'IMPERIAL'
    scene.unit_settings.length_unit = 'FEET'
    scene.unit_settings.scale_length = 0.3048  # 1 BU = 1 ft
    scene.render.fps = 24
    scene.frame_start = 1
    scene.frame_end = 240
    scene["MEYD_Project"] = "25-048 — 101 Meydenbauer Underground DW Re-Pipe"
    scene["MEYD_Coordinate_System"] = "X North→South, Y East→West, Z up; slab top Z=0"
    scene["MEYD_Route_Status"] = "P1.02/P3.1/P3.2 traced control points; verify field routing/inverts before construction use"
    scene["MEYD_Slab_Thickness_Assumption_in"] = 5.5
    scene["MEYD_Grid_Length_ft"] = BUILDING_LENGTH
    scene["MEYD_Grid_Width_ft"] = BUILDING_WIDTH
    scene["MEYD_SideSewer_Main_Nominal_in"] = 8
    scene["MEYD_Replacement_Lateral_Nominal_in"] = 6
    return scene


def get_coll(name):
    return bpy.data.collections.get(name)


def ensure_collection(name, parent=None):
    coll = bpy.data.collections.get(name)
    if coll is None:
        coll = bpy.data.collections.new(name)
    if parent is None:
        if coll.name not in bpy.context.scene.collection.children:
            try:
                bpy.context.scene.collection.children.link(coll)
            except RuntimeError:
                pass
    else:
        if coll.name not in parent.children:
            try:
                parent.children.link(coll)
            except RuntimeError:
                pass
    return coll


def ensure_collection_tree():
    for parent_name, children in COLLECTION_TREE.items():
        parent = ensure_collection(parent_name)
        for child_name in children:
            ensure_collection(child_name, parent)


def relink_object(obj, collection):
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    collection.objects.link(obj)


def clear_pass(pass_id):
    for obj in list(bpy.data.objects):
        if obj.get("MEYD_PROJECT") == PROJECT_TAG and obj.get("MEYD_PASS") == pass_id:
            bpy.data.objects.remove(obj, do_unlink=True)


def delete_named_object(name):
    obj = bpy.data.objects.get(name)
    if obj:
        bpy.data.objects.remove(obj, do_unlink=True)


def ensure_material(name, color, roughness=0.55, metallic=0.0, alpha=1.0,
                    emission=None, emission_strength=0.0):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf is None:
        nodes.clear()
        bsdf = nodes.new("ShaderNodeBsdfPrincipled")
        out = nodes.new("ShaderNodeOutputMaterial")
        mat.node_tree.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    bsdf.inputs["Base Color"].default_value = (*color[:3], 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    if "Alpha" in bsdf.inputs:
        bsdf.inputs["Alpha"].default_value = alpha
    if emission and "Emission Color" in bsdf.inputs:
        bsdf.inputs["Emission Color"].default_value = (*emission[:3], 1.0)
        bsdf.inputs["Emission Strength"].default_value = emission_strength
    elif emission and "Emission" in bsdf.inputs:  # Blender 3.x
        bsdf.inputs["Emission"].default_value = (*emission[:3], 1.0)
        if "Emission Strength" in bsdf.inputs:
            bsdf.inputs["Emission Strength"].default_value = emission_strength
    mat.diffuse_color = (*color[:3], alpha)
    if alpha < 1.0:
        try:
            mat.surface_render_method = 'DITHERED'
        except Exception:
            try:
                mat.blend_method = 'BLEND'
                mat.use_screen_refraction = True
            except Exception:
                pass
    return mat


def ensure_marble_material(name, base=(0.82, 0.82, 0.80), vein=(0.18, 0.20, 0.22)):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    noise = nt.nodes.new("ShaderNodeTexNoise")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    bump = nt.nodes.new("ShaderNodeBump")
    noise.inputs["Scale"].default_value = 2.2
    noise.inputs["Detail"].default_value = 7.0
    noise.inputs["Roughness"].default_value = 0.7
    ramp.color_ramp.elements[0].color = (*base, 1)
    ramp.color_ramp.elements[1].color = (*vein, 1)
    ramp.color_ramp.elements[0].position = 0.38
    ramp.color_ramp.elements[1].position = 0.62
    bump.inputs["Strength"].default_value = 0.12
    bump.inputs["Distance"].default_value = 0.03
    bsdf.inputs["Roughness"].default_value = 0.28
    nt.links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    nt.links.new(noise.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat


def ensure_wood_material(name, light=(0.54, 0.36, 0.20), dark=(0.18, 0.09, 0.035)):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    wave = nt.nodes.new("ShaderNodeTexWave")
    noise = nt.nodes.new("ShaderNodeTexNoise")
    mix = nt.nodes.new("ShaderNodeMixRGB")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    wave.wave_type = 'BANDS'
    wave.bands_direction = 'X'
    wave.inputs["Scale"].default_value = 5.0
    wave.inputs["Distortion"].default_value = 7.0
    wave.inputs["Detail"].default_value = 4.0
    noise.inputs["Scale"].default_value = 3.0
    mix.blend_type = 'MULTIPLY'
    mix.inputs["Fac"].default_value = 0.35
    ramp.color_ramp.elements[0].color = (*dark, 1)
    ramp.color_ramp.elements[1].color = (*light, 1)
    bsdf.inputs["Roughness"].default_value = 0.42
    nt.links.new(wave.outputs["Color"], mix.inputs[1])
    nt.links.new(noise.outputs["Fac"], mix.inputs[2])
    nt.links.new(mix.outputs["Color"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat


def _node_group_socket(group, in_out, socket_type, name):
    # Blender 4.x interface API vs Blender 3.x input/output API.
    try:
        return group.interface.new_socket(name=name, in_out=in_out, socket_type=socket_type)
    except Exception:
        if in_out == 'INPUT':
            return group.inputs.new(socket_type, name)
        return group.outputs.new(socket_type, name)


def ensure_xray_group():
    group = bpy.data.node_groups.get("MEYD_XRAY_SHADER")
    if group:
        return group
    group = bpy.data.node_groups.new("MEYD_XRAY_SHADER", "ShaderNodeTree")
    _node_group_socket(group, 'INPUT', 'NodeSocketColor', 'Color')
    _node_group_socket(group, 'INPUT', 'NodeSocketFloat', 'Roughness')
    _node_group_socket(group, 'INPUT', 'NodeSocketFloat', 'Alpha')
    _node_group_socket(group, 'OUTPUT', 'NodeSocketShader', 'Shader')

    n_in = group.nodes.new("NodeGroupInput")
    n_out = group.nodes.new("NodeGroupOutput")
    bsdf = group.nodes.new("ShaderNodeBsdfPrincipled")
    trans = group.nodes.new("ShaderNodeBsdfTransparent")
    mix = group.nodes.new("ShaderNodeMixShader")
    group.links.new(n_in.outputs["Color"], bsdf.inputs["Base Color"])
    group.links.new(n_in.outputs["Roughness"], bsdf.inputs["Roughness"])
    group.links.new(trans.outputs["BSDF"], mix.inputs[1])
    group.links.new(bsdf.outputs["BSDF"], mix.inputs[2])
    group.links.new(n_in.outputs["Alpha"], mix.inputs[0])
    group.links.new(mix.outputs[0], n_out.inputs["Shader"])
    return group


def ensure_xray_material(name, color, roughness=0.6):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    group_node = nt.nodes.new("ShaderNodeGroup")
    group_node.node_tree = ensure_xray_group()
    group_node.name = "XRAY_SHADER"
    group_node.inputs["Color"].default_value = (*color[:3], 1)
    group_node.inputs["Roughness"].default_value = roughness
    group_node.inputs["Alpha"].default_value = 1.0
    nt.links.new(group_node.outputs["Shader"], out.inputs["Surface"])
    try:
        mat.surface_render_method = 'DITHERED'
    except Exception:
        try:
            mat.blend_method = 'BLEND'
            mat.show_transparent_back = True
        except Exception:
            pass
    mat.diffuse_color = (*color[:3], 1)
    return mat


def ensure_material_library():
    mats = {}
    mats["concrete"] = ensure_xray_material("MAT_Concrete_Shell_Xray", (0.48, 0.50, 0.52), 0.78)
    mats["precast"] = ensure_xray_material("MAT_Precast_Xray", (0.62, 0.64, 0.66), 0.72)
    mats["soil"] = ensure_material("MAT_Subgrade_Soil", (0.20, 0.10, 0.045), 0.95)
    mats["footing"] = ensure_material("MAT_Foundation_Concrete", (0.43, 0.44, 0.45), 0.85)
    mats["grid"] = ensure_material("MAT_Grid", (0.05, 0.25, 0.70), 0.45, emission=(0.05,0.15,0.5), emission_strength=0.2)
    mats["rust"] = ensure_material("MAT_Existing_CastIron_Rust", (0.20, 0.055, 0.018), 0.72, metallic=0.68)
    mats["abs"] = ensure_material("MAT_ABS_Schedule40_Black", (0.008, 0.008, 0.010), 0.20)
    mats["abs_prior"] = ensure_material("MAT_ABS_Prior_Remain", (0.025, 0.035, 0.045), 0.25)
    mats["copper"] = ensure_material("MAT_Copper_Tracer", (0.70, 0.24, 0.06), 0.28, metallic=0.78)
    mats["cut"] = ensure_material("MAT_Trench_Cutter", (0.85, 0.04, 0.02), 0.35, alpha=0.22)
    mats["gravel"] = ensure_material("MAT_Gravel_Bedding", (0.37, 0.33, 0.27), 0.94)
    mats["pipezone"] = ensure_material("MAT_PipeZone_Backfill", (0.48, 0.41, 0.29), 0.92, alpha=0.58)
    mats["backfill"] = ensure_material("MAT_General_Backfill", (0.30, 0.23, 0.16), 0.95, alpha=0.48)
    mats["stego"] = ensure_material("MAT_StegoWrap_15mil", (0.95, 0.45, 0.02), 0.30, alpha=0.72)
    mats["rebar"] = ensure_material("MAT_Rebar_Steel", (0.18, 0.19, 0.20), 0.55, metallic=0.85)
    mats["pourback"] = ensure_material("MAT_Concrete_Pourback_KIM", (0.56, 0.58, 0.59), 0.76)
    mats["firestop"] = ensure_material("MAT_Firestop_Red", (0.72, 0.015, 0.01), 0.48)
    mats["steel"] = ensure_material("MAT_Sleeve_Steel", (0.28, 0.30, 0.32), 0.28, metallic=0.92)
    mats["gypsum"] = ensure_material("MAT_Gypsum_TypeX", (0.82, 0.79, 0.72), 0.82)
    mats["wood_stud"] = ensure_wood_material("MAT_Wood_Stud", (0.60, 0.43, 0.24), (0.28, 0.14, 0.05))
    mats["primer"] = ensure_material("MAT_Vapor_Mitigating_Epoxy_Primer", (0.55, 0.37, 0.12), 0.48, alpha=0.70)
    mats["waterproof"] = ensure_material("MAT_TCNA_Waterproofing", (0.02, 0.42, 0.55), 0.34, alpha=0.72)
    mats["radiant"] = ensure_material("MAT_Radiant_Heating_Coil", (0.90, 0.12, 0.02), 0.30, emission=(1.0,0.08,0.01), emission_strength=1.2)
    mats["glass"] = ensure_material("MAT_Glass", (0.70, 0.90, 0.96), 0.08, alpha=0.22)
    mats["white"] = ensure_material("MAT_Porcelain_White", (0.93, 0.93, 0.91), 0.22)
    mats["nickel"] = ensure_material("MAT_Nickel_Bronze", (0.34, 0.30, 0.22), 0.26, metallic=0.75)
    mats["water"] = ensure_material("MAT_Water_Test_Blue", (0.01, 0.18, 0.75), 0.08, alpha=0.58)
    mats["protection"] = ensure_material("MAT_Temp_Dust_Poly", (0.90, 0.93, 0.90), 0.22, alpha=0.25)
    return mats


def set_material(obj, mat):
    if obj.data and hasattr(obj.data, "materials"):
        obj.data.materials.clear()
        obj.data.materials.append(mat)


def create_box(name, dims, loc, collection, mat=None, pass_id=1, rotation_z=0.0, source=""):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc, rotation=(0, 0, rotation_z))
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dims
    relink_object(obj, collection)
    tag(obj, pass_id, source)
    if mat:
        set_material(obj, mat)
    return obj


def create_polygon_prism(name, xy_points, z0, height, collection, mat=None, pass_id=1, source=""):
    verts = [(x, y, z0) for x, y in xy_points] + [(x, y, z0 + height) for x, y in xy_points]
    n = len(xy_points)
    # Normalize cap winding so top/bottom normals oppose one another instead of
    # duplicating the same winding. This matters for clean shading/export and
    # avoids non-manifold-looking bay/slab prisms.
    signed_area = 0.5 * sum(
        xy_points[i][0] * xy_points[(i + 1) % n][1]
        - xy_points[(i + 1) % n][0] * xy_points[i][1]
        for i in range(n)
    )
    if signed_area >= 0.0:  # CCW plan polygon
        bottom = tuple(reversed(range(n)))
        top = tuple(range(n, 2*n))
    else:                   # CW plan polygon
        bottom = tuple(range(n))
        top = tuple(reversed(range(n, 2*n)))
    faces = [bottom, top]
    for i in range(n):
        j = (i + 1) % n
        face = (i, j, n+j, n+i) if signed_area >= 0.0 else (j, i, n+i, n+j)
        faces.append(face)
    mesh = bpy.data.meshes.new(name + "_MESH")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    tag(obj, pass_id, source)
    if mat:
        set_material(obj, mat)
    return obj


def create_curve(name, points, bevel_depth, collection, mat=None, pass_id=2, cyclic=False, source=""):
    curve = bpy.data.curves.new(name + "_CURVE", type='CURVE')
    curve.dimensions = '3D'
    curve.resolution_u = 8
    curve.bevel_resolution = 4
    curve.bevel_depth = bevel_depth
    spl = curve.splines.new('POLY')
    spl.points.add(len(points) - 1)
    for p, co in zip(spl.points, points):
        p.co = (co[0], co[1], co[2], 1.0)
    spl.use_cyclic_u = cyclic
    obj = bpy.data.objects.new(name, curve)
    collection.objects.link(obj)
    tag(obj, pass_id, source)
    if mat:
        set_material(obj, mat)
    return obj


def create_curve_bundle(name, polylines, bevel_depth, collection, mat=None, pass_id=2, source=""):
    curve = bpy.data.curves.new(name + "_CURVE", type='CURVE')
    curve.dimensions = '3D'
    curve.resolution_u = 3
    curve.bevel_resolution = 2
    curve.bevel_depth = bevel_depth
    for points in polylines:
        if len(points) < 2:
            continue
        spl = curve.splines.new('POLY')
        spl.points.add(len(points) - 1)
        for p, co in zip(spl.points, points):
            p.co = (co[0], co[1], co[2], 1.0)
    obj = bpy.data.objects.new(name, curve)
    collection.objects.link(obj)
    tag(obj, pass_id, source)
    if mat:
        set_material(obj, mat)
    return obj


def cylinder_between(name, a, b, radius, collection, mat=None, pass_id=2, vertices=24, source=""):
    a, b = Vector(a), Vector(b)
    vec = b - a
    length = vec.length
    if length <= 1e-6:
        return None
    mid = (a + b) * 0.5
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=length, location=mid)
    obj = bpy.context.object
    obj.name = name
    obj.rotation_mode = 'QUATERNION'
    obj.rotation_quaternion = vec.to_track_quat('Z', 'Y')
    relink_object(obj, collection)
    tag(obj, pass_id, source)
    if mat:
        set_material(obj, mat)
    return obj


def create_text(name, body, loc, collection, size=0.75, rotation=(0, 0, 0), pass_id=1, mat=None, source=""):
    data = bpy.data.curves.new(name + "_TEXT", type='FONT')
    data.body = body
    data.align_x = 'CENTER'
    data.align_y = 'CENTER'
    data.size = size
    obj = bpy.data.objects.new(name, data)
    obj.location = loc
    obj.rotation_euler = rotation
    collection.objects.link(obj)
    tag(obj, pass_id, source)
    if mat:
        set_material(obj, mat)
    return obj


def make_segment_box(name, p0, p1, width, z_center, height, collection, mat, pass_id, source="", end_extension=0.0):
    a = Vector((p0[0], p0[1], z_center))
    b = Vector((p1[0], p1[1], z_center))
    v = b - a
    length = math.hypot(v.x, v.y)
    if length < 1e-6:
        return None
    direction = Vector((v.x / length, v.y / length, 0.0))
    ext = max(0.0, float(end_extension))
    a = a - direction * ext
    b = b + direction * ext
    v = b - a
    length = math.hypot(v.x, v.y)
    angle = math.atan2(v.y, v.x)
    mid = (a + b) * 0.5
    return create_box(name, (length, width, height), mid, collection, mat, pass_id, angle, source)


def segment_length_2d(a, b):
    return math.hypot(b[0] - a[0], b[1] - a[1])


def polyline_length_2d(points2d):
    return sum(segment_length_2d(points2d[i], points2d[i + 1]) for i in range(len(points2d) - 1))


def sloped_points(points2d, start_z=-ft(2, 2), slope=PIPE_SLOPE, end_z=None):
    """
    Apply continuous fall along path order (upstream -> downstream).

    If end_z is supplied, compute the upstream start elevation so the final
    point lands exactly at end_z. This is used to keep branches, mains, and
    laterals physically connected instead of merely close in plan.
    """
    if len(points2d) < 1:
        return []
    if end_z is not None:
        start_z = float(end_z) + polyline_length_2d(points2d) * slope
    out = []
    z = float(start_z)
    prev = None
    for xy in points2d:
        if prev is not None:
            z -= segment_length_2d(prev, xy) * slope
        out.append((xy[0], xy[1], z))
        prev = xy
    if end_z is not None and out:
        # Avoid accumulated floating point drift at network tie points.
        out[-1] = (out[-1][0], out[-1][1], float(end_z))
    return out


def z_at_polyline_xy(points3d, xy, tol=1e-5):
    """Return Z at an XY point lying on a 3D polyline; exact nodes are preferred."""
    x, y = xy
    for px, py, pz in points3d:
        if abs(px - x) <= tol and abs(py - y) <= tol:
            return pz
    p = Vector((x, y))
    for a3, b3 in zip(points3d, points3d[1:]):
        a = Vector((a3[0], a3[1])); b = Vector((b3[0], b3[1]))
        ab = b - a
        denom = ab.length_squared
        if denom <= 1e-12:
            continue
        t = max(0.0, min(1.0, (p - a).dot(ab) / denom))
        q = a + ab * t
        if (p - q).length <= tol:
            return a3[2] + (b3[2] - a3[2]) * t
    return None


def compute_unit_network_3d(d):
    """Resolve one unit's editable plan controls into a connected 3D gravity network."""
    ctx6_pts = sloped_points(d["lateral_6_context"], end_z=SIDE_SEWER_Z, slope=PIPE_SLOPE)
    lat6_pts = sloped_points(d["lateral_6"], end_z=ctx6_pts[0][2], slope=PIPE_SLOPE)
    main4_pts = sloped_points(d["main_4"], end_z=lat6_pts[0][2], slope=PIPE_SLOPE)

    branch3 = {}
    for role, pts in d["branches_3"].items():
        target_z = z_at_polyline_xy(main4_pts, pts[-1])
        if target_z is None:
            raise RuntimeError(f"3in branch {role} does not terminate on main_4 control polyline")
        branch3[role] = sloped_points(pts, end_z=target_z, slope=PIPE_SLOPE)

    branch2 = {}
    for role, pts in d["branches_2"].items():
        target_z = z_at_polyline_xy(main4_pts, pts[-1])
        if target_z is None:
            raise RuntimeError(f"2in branch {role} does not terminate on main_4 control polyline")
        branch2[role] = sloped_points(pts, end_z=target_z, slope=PIPE_SLOPE)

    # Optional fixture stubs attach to an already-solved same-size branch.
    # This lets plan topology use true tees/common branches instead of
    # duplicating coincident pipe runs merely to keep every fixture editable.
    branch3_stubs = {}
    for role, spec in d.get("branch3_stubs", {}).items():
        parent_role = spec["parent"]
        pts = spec["points"]
        parent = branch3.get(parent_role)
        if parent is None:
            raise RuntimeError(f"3in stub {role} parent branch {parent_role!r} not found")
        target_z = z_at_polyline_xy(parent, pts[-1])
        if target_z is None:
            raise RuntimeError(f"3in stub {role} does not terminate on parent {parent_role}")
        branch3_stubs[role] = sloped_points(pts, end_z=target_z, slope=PIPE_SLOPE)

    branch2_stubs = {}
    for role, spec in d.get("branch2_stubs", {}).items():
        parent_role = spec["parent"]
        pts = spec["points"]
        parent = branch2.get(parent_role)
        if parent is None:
            raise RuntimeError(f"2in stub {role} parent branch {parent_role!r} not found")
        target_z = z_at_polyline_xy(parent, pts[-1])
        if target_z is None:
            raise RuntimeError(f"2in stub {role} does not terminate on parent {parent_role}")
        branch2_stubs[role] = sloped_points(pts, end_z=target_z, slope=PIPE_SLOPE)

    prior = []
    if d.get("prior_abs_4"):
        prior = sloped_points(d["prior_abs_4"], end_z=main4_pts[0][2], slope=PIPE_SLOPE)

    return {
        "context6": ctx6_pts,
        "lateral6": lat6_pts,
        "main4": main4_pts,
        "branch3": branch3,
        "branch2": branch2,
        "branch3_stubs": branch3_stubs,
        "branch2_stubs": branch2_stubs,
        "prior4": prior,
    }


def trench_segment_pipe_data(unit, p0, p1, role):
    """Return representative pipe center Z and nominal size for one trench segment."""
    net = compute_unit_network_3d(ROUTE_DATA[unit])
    if role == "main":
        routes = [(net["main4"], 4)]
    elif role == "branch3":
        routes = [(pts, 3) for pts in net["branch3"].values()]
        routes += [(pts, 3) for pts in net.get("branch3_stubs", {}).values()]
    else:
        routes = [(pts, 2) for pts in net["branch2"].values()]
        routes += [(pts, 2) for pts in net.get("branch2_stubs", {}).values()]

    def same_xy(a, b, tol=1e-5):
        return abs(a[0]-b[0]) <= tol and abs(a[1]-b[1]) <= tol

    for pts3, dia in routes:
        for a, b in zip(pts3, pts3[1:]):
            if (same_xy(a, p0) and same_xy(b, p1)) or (same_xy(a, p1) and same_xy(b, p0)):
                return ((a[2] + b[2]) * 0.5, dia)
    # Defensive fallback; validation will flag if this occurs.
    return (-ft(2, 8) if role == "main" else -ft(2, 4), 4 if role == "main" else (3 if role == "branch3" else 2))


def route_segments_for_trench():
    segs = []
    for unit, d in ROUTE_DATA.items():
        # Slab sawcutting stops at the east foundation face. The replacement 6 in
        # lateral continues 18 in outside, but that segment is not under Building B's slab.
        routes = [(d["main_4"], TRENCH_MAIN_W, "main")]
        for pts in d["branches_3"].values():
            routes.append((pts, TRENCH_BRANCH_W, "branch3"))
        for pts in d["branches_2"].values():
            routes.append((pts, TRENCH_BRANCH_W, "branch2"))
        for spec in d.get("branch3_stubs", {}).values():
            routes.append((spec["points"], TRENCH_BRANCH_W, "branch3"))
        for spec in d.get("branch2_stubs", {}).values():
            routes.append((spec["points"], TRENCH_BRANCH_W, "branch2"))
        for pts, width, role in routes:
            for i in range(len(pts) - 1):
                segs.append({"unit": unit, "p0": pts[i], "p1": pts[i+1], "width": width, "role": role})
    return segs


TRENCH_SEGMENTS = route_segments_for_trench()

# -----------------------------------------------------------------------------
# PASS 1 — COLLECTIONS / GRID / STRUCTURAL SHELL / BOOLEAN CUTTERS
# -----------------------------------------------------------------------------


def build_grid(mats):
    coll = ensure_collection("Bldg_B_Shell_&_Upper_Stacks", get_coll("00_Site_&_Context"))
    z = inch(1)
    # Letter grids: vertical in Y.
    for label in LONG_GRID_LABELS:
        x = GX[label]
        create_curve(
            f"GRID_{label}", [(x, -ft(3), z), (x, BUILDING_WIDTH + ft(3), z)],
            inch(0.18), coll, mats["grid"], 1, source="P1.01/P1.02 grid"
        )
        create_text(f"GRID_LABEL_{label}", label, (x, -ft(4.5), ft(0, 1)), coll,
                    size=0.8, rotation=(0,0,0), pass_id=1, mat=mats["grid"], source="P1.01/P1.02")
    # Numbered grids: vertical in X.
    for label in TRANS_GRID_LABELS:
        y = GY[label]
        create_curve(
            f"GRID_{label}", [(-ft(3), y, z), (BUILDING_LENGTH + ft(3), y, z)],
            inch(0.18), coll, mats["grid"], 1, source="P1.01/P1.02 grid"
        )
        create_text(f"GRID_LABEL_{label}", label, (-ft(4.5), y, ft(0, 1)), coll,
                    size=0.8, rotation=(0,0,0), pass_id=1, mat=mats["grid"], source="P1.01/P1.02")


def build_site_context(mats):
    shell_coll = get_coll("Bldg_B_Shell_&_Upper_Stacks")
    garage_coll = get_coll("East_Garages_&_Planter_Strip")
    stage_coll = get_coll("Staging_Area")

    # Low-detail upper floor slabs for 3-story context.
    for level in (1, 2):
        z = level * STORY_HEIGHT
        obj = create_box(f"BldgB_UpperFloor_{level+1}", (BUILDING_LENGTH, BUILDING_WIDTH, inch(4)),
                         (BUILDING_LENGTH/2, BUILDING_WIDTH/2, z), shell_coll, mats["precast"], 1,
                         source="3-story Building B context")
        obj.display_type = 'WIRE'

    # East garages separated by ~10 ft planter strip. Split for visual readability.
    garage_depth = ft(18)
    gap = ft(2)
    module_len = (BUILDING_LENGTH - 2*gap) / 3.0
    for i in range(3):
        x0 = gap + i * module_len
        create_box(
            f"East_Garage_Block_{i+1}",
            (module_len - gap, garage_depth, ft(10)),
            (x0 + (module_len-gap)/2, EAST_GARAGE_NEAR_FACE_Y - garage_depth/2, ft(5)),
            garage_coll, mats["precast"], 1, source="SOR: garages ~10 ft east of Building B"
        )

    # Approx. 1,000 sf staging area (25x40) east of garages.
    stage = create_box("Staging_Area_1000SF", (ft(40), ft(25), inch(2)),
                       (BUILDING_LENGTH - ft(30), -ft(55), inch(1)), stage_coll,
                       ensure_material("MAT_Staging", (0.16,0.22,0.20), 0.8), 1,
                       source="4D brief: ~1,000 sf fenced staging area")
    stage["AREA_SF"] = 1000.0
    stage["PHASE_ROLE"] = "TEMP"


def build_structural_shell(mats):
    soil_coll = get_coll("Subgrade_&_Soil")
    footing_coll = get_coll("Foundation_Footings")
    precast_coll = get_coll("Precast_Concrete_Walls")
    slab_coll = get_coll("Concrete_Slab_Unmodified")

    # Soil volume, deliberately oversized around footprint.
    create_box("Subgrade_Soil_Mass", (BUILDING_LENGTH + ft(12), BUILDING_WIDTH + ft(18), TRENCH_DEPTH + ft(1)),
               (BUILDING_LENGTH/2, BUILDING_WIDTH/2 - ft(2), -(TRENCH_DEPTH+ft(1))/2 - SLAB_THICKNESS),
               soil_coll, mats["soil"], 1, source="SOR excavation depth 2.5–4.5 ft")

    # Main slab-on-grade.
    slab = create_box("BuildingB_SOG_5p5in", (BUILDING_LENGTH, BUILDING_WIDTH, SLAB_THICKNESS),
                      (BUILDING_LENGTH/2, BUILDING_WIDTH/2, -SLAB_THICKNESS/2),
                      slab_coll, mats["concrete"], 1, source="P1.01/P5.1: existing 5–6 in slab")
    slab["THICKNESS_RANGE_IN"] = "5–6"

    # West/lakeside bay projections — schematic plan context, separate from main slab.
    for unit, (x0, x1) in UNIT_RANGES.items():
        w = x1 - x0
        bx0 = x0 + w*0.20
        bx1 = x1 - w*0.20
        y0 = BUILDING_WIDTH
        y1 = BUILDING_WIDTH + ft(5)
        poly = [(bx0, y0), (bx0 + ft(3), y1), (bx1 - ft(3), y1), (bx1, y0)]
        create_polygon_prism(f"{unit}_West_Bay_Slab", poly, -SLAB_THICKNESS, SLAB_THICKNESS,
                             slab_coll, mats["concrete"], 1, source="P1/P2 plan bay-window projection context")

    # Exterior walls, ground-floor shell.
    wall_h = GROUND_FLOOR_HEIGHT
    create_box("East_Exterior_Wall", (BUILDING_LENGTH, EXT_WALL_THICKNESS, wall_h),
               (BUILDING_LENGTH/2, -EXT_WALL_THICKNESS/2, wall_h/2), precast_coll, mats["precast"], 1,
               source="Building B shell")
    create_box("West_Exterior_Wall", (BUILDING_LENGTH, EXT_WALL_THICKNESS, wall_h),
               (BUILDING_LENGTH/2, BUILDING_WIDTH + EXT_WALL_THICKNESS/2, wall_h/2), precast_coll, mats["precast"], 1)
    create_box("North_Exterior_Wall", (EXT_WALL_THICKNESS, BUILDING_WIDTH, wall_h),
               (-EXT_WALL_THICKNESS/2, BUILDING_WIDTH/2, wall_h/2), precast_coll, mats["precast"], 1)
    create_box("South_Exterior_Wall", (EXT_WALL_THICKNESS, BUILDING_WIDTH, wall_h),
               (BUILDING_LENGTH + EXT_WALL_THICKNESS/2, BUILDING_WIDTH/2, wall_h/2), precast_coll, mats["precast"], 1)

    # Demising/structural lines and stair/elevator core walls.
    for label in ("E", "H", "L"):
        create_box(f"Precast_Demising_{label}", (PRECAST_WALL_THICKNESS, BUILDING_WIDTH, wall_h),
                   (GX[label], BUILDING_WIDTH/2, wall_h/2), precast_coll, mats["precast"], 1,
                   source="P1/P2 plan unit separation")

    # Two core zones corresponding to C-D and J-K grids.
    for left, right, name in (("C", "D", "Core_N"), ("J", "K", "Core_S")):
        x0, x1 = GX[left], GX[right]
        create_box(f"{name}_EastWall", (PRECAST_WALL_THICKNESS, ft(22), wall_h),
                   (x0, ft(11), wall_h/2), precast_coll, mats["precast"], 1, source="record/permit plan core")
        create_box(f"{name}_WestWall", (PRECAST_WALL_THICKNESS, ft(22), wall_h),
                   (x1, ft(11), wall_h/2), precast_coll, mats["precast"], 1, source="record/permit plan core")
        create_box(f"{name}_CrossWall", (x1-x0, PRECAST_WALL_THICKNESS, wall_h),
                   ((x0+x1)/2, ft(22), wall_h/2), precast_coll, mats["precast"], 1, source="record/permit plan core")

    # Perimeter strip footings + core footings.
    foot_depth = ft(1, 0)
    foot_w = ft(2, 0)
    create_box("Footing_East", (BUILDING_LENGTH, foot_w, foot_depth),
               (BUILDING_LENGTH/2, 0, -SLAB_THICKNESS-foot_depth/2), footing_coll, mats["footing"], 1)
    create_box("Footing_West", (BUILDING_LENGTH, foot_w, foot_depth),
               (BUILDING_LENGTH/2, BUILDING_WIDTH, -SLAB_THICKNESS-foot_depth/2), footing_coll, mats["footing"], 1)
    create_box("Footing_North", (foot_w, BUILDING_WIDTH, foot_depth),
               (0, BUILDING_WIDTH/2, -SLAB_THICKNESS-foot_depth/2), footing_coll, mats["footing"], 1)
    create_box("Footing_South", (foot_w, BUILDING_WIDTH, foot_depth),
               (BUILDING_LENGTH, BUILDING_WIDTH/2, -SLAB_THICKNESS-foot_depth/2), footing_coll, mats["footing"], 1)


def build_upper_stack_context(mats):
    coll = get_coll("Bldg_B_Shell_&_Upper_Stacks")
    z0 = 0.0
    z1 = STORY_HEIGHT * 3.0
    for unit, d in ROUTE_DATA.items():
        pts = d["fixture_pts"]
        stack_defs = [
            ("4in", pts["WC_N"], 4),
            ("3inA", pts["WC_S"], 3),
            ("3inB", pts["WB"], 3),
        ]
        for role, (x,y), dia in stack_defs:
            obj = create_curve(f"CTX_{unit}_STACK_{role}", [(x,y,z0),(x,y,z1)], od_ft(dia)/2,
                               coll, mats["rust"], 1, source="P1.01 stack note: 4x4in + 8x3in apparent stacks")
            obj.display_type = 'WIRE'
            obj["NOMINAL_DIAMETER_IN"] = dia


def build_trench_cutters(mats):
    coll = get_coll("Concrete_Slab_Trench_Cuts_DEMO")
    total_plan_area = 0.0
    for idx, seg in enumerate(TRENCH_SEGMENTS, 1):
        length = segment_length_2d(seg["p0"], seg["p1"])
        total_plan_area += length * seg["width"]
        # Extend cutters slightly above slab top to avoid coplanar Boolean faces.
        cutter_top = inch(1.0)
        cutter_bottom = -TRENCH_DEPTH
        cutter_h = cutter_top - cutter_bottom
        obj = make_segment_box(
            f"TrenchCutter_{seg['unit']}_{idx:03d}", seg["p0"], seg["p1"], seg["width"],
            (cutter_top + cutter_bottom)/2, cutter_h, coll, mats["cut"], 1,
            source="P1.02/P3 route + ~700 SF allowance; verify field route",
            end_extension=seg["width"] * 0.55
        )
        if obj:
            obj.display_type = 'WIRE'
            obj.hide_render = True
            obj["TRENCH_ROLE"] = seg["role"]

    # Non-destructive Boolean collection operand.
    slab = bpy.data.objects.get("BuildingB_SOG_5p5in")
    if slab:
        old = slab.modifiers.get("MEYD_Trench_Difference")
        if old:
            slab.modifiers.remove(old)
        mod = slab.modifiers.new("MEYD_Trench_Difference", 'BOOLEAN')
        mod.operation = 'DIFFERENCE'
        try:
            mod.solver = 'EXACT'
        except Exception:
            pass
        try:
            mod.operand_type = 'COLLECTION'
            mod.collection = coll
        except Exception as exc:
            # Do not silently degrade to a single cutter: that produces a
            # plausible-looking but materially wrong slab. Blender 3.6+ supports
            # collection Boolean operands, so failure here should be explicit.
            raise RuntimeError(
                "MEYD trench Boolean requires a collection operand; refusing single-cutter fallback"
            ) from exc
        mod.show_viewport = False
        mod.show_render = False
        try:
            mod["MEYD_PHASE_ROLE"] = "TRENCH_BOOLEAN"
        except Exception:
            pass
    bpy.context.scene["MEYD_Est_TrenchPlanArea_sf_before_overlap"] = round(total_plan_area, 1)


def run_pass1():
    print("\n=== MEYDENBAUER PASS 1 ===")
    scene_setup()
    ensure_collection_tree()
    clear_pass(1)
    mats = ensure_material_library()
    build_grid(mats)
    build_site_context(mats)
    build_structural_shell(mats)
    build_upper_stack_context(mats)
    build_trench_cutters(mats)
    print(f"Pass 1 complete. Building grid: {BUILDING_LENGTH:.3f} ft x {BUILDING_WIDTH:.3f} ft")

# -----------------------------------------------------------------------------
# PASS 2 — EXISTING / NEW DWV / FITTINGS / TRENCH LAYERS
# -----------------------------------------------------------------------------


def create_pipe_route(name, points2d, nominal_in, collection, mat, pass_id=2,
                      start_z=-ft(2,2), end_z=None, slope=PIPE_SLOPE, source=""):
    pts3 = sloped_points(points2d, start_z=start_z, end_z=end_z, slope=slope)
    obj = create_curve(name, pts3, od_ft(nominal_in)/2, collection, mat, pass_id, source=source)
    obj["NOMINAL_DIAMETER_IN"] = nominal_in
    obj["SLOPE_IN_PER_FT"] = round(slope*12.0, 4)
    return obj, pts3


def _create_pipe_3d(name, pts3, nominal_in, collection, mat, pass_id=2, source="", phase_role=None):
    obj = create_curve(name, pts3, od_ft(nominal_in)/2, collection, mat, pass_id, source=source)
    obj["NOMINAL_DIAMETER_IN"] = nominal_in
    obj["SLOPE_IN_PER_FT"] = round(PIPE_SLOPE*12.0, 4)
    if phase_role:
        obj["PHASE_ROLE"] = phase_role
    return obj


def create_existing_and_new_pipes(mats):
    ex_coll = get_coll("Ex_Cast_Iron_Pipes_DEMO")
    prior_coll = get_coll("Ex_Unit101_&_104_Prior_ABS_REMAIN")
    new_main_coll = get_coll("New_ABS_UnderSlab_4in_6in")
    branch_coll = get_coll("New_ABS_Branches_&_Traps")
    tie_coll = get_coll("New_Stack_TieIns_&_Cleanouts")
    sewer_coll = get_coll("Side_Sewer_Main_6in")  # legacy collection name from requested hierarchy

    # Existing 8 in side sewer trunk under the east garages. P1.02 shows the
    # building laterals as 6 in waste tying to this existing 8 in SS main.
    main = create_curve("EX_Side_Sewer_Main_8in",
                        [(-ft(8), SIDE_SEWER_Y, SIDE_SEWER_Z),
                         (BUILDING_LENGTH+ft(8), SIDE_SEWER_Y, SIDE_SEWER_Z)],
                        od_ft(8)/2, sewer_coll, mats["rust"], 2,
                        source="P1.02/P3: existing 8in SS main under garages")
    main["PHASE_ROLE"] = "REMAIN"
    main["NOMINAL_DIAMETER_IN"] = 8

    for unit, d in ROUTE_DATA.items():
        net = compute_unit_network_3d(d)

        # Existing 6 in lateral context from the 18 in scope boundary to the
        # existing 8 in side sewer. Anchor at the representative side-sewer Z.
        ctx6_pts = net["context6"]
        ctx6 = _create_pipe_3d(f"EX_{unit}_6in_LATERAL_REMAIN", ctx6_pts, 6, sewer_coll,
                               mats["rust"], 2,
                               source="SOR/P1.02: existing 6in lateral outside 18in replacement limit",
                               phase_role="REMAIN")
        ctx6["SCOPE_STATUS"] = "EXISTING_REMAIN_OUTSIDE_18IN_LIMIT"

        # Replacement 6 in segment and connected 4 in under-slab main.
        lat6_pts = net["lateral6"]
        main4_pts = net["main4"]

        # Retained prior ABS ties exactly to the upstream end of the new main.
        if d.get("prior_abs_4"):
            prior_pts3 = net["prior4"]
            prior = _create_pipe_3d(f"{unit}_Prior_4in_ABS_REMAIN", prior_pts3, 4, prior_coll,
                                    mats["abs_prior"], 2,
                                    source="P3.1/P3.2: prior Schedule 40 ABS repair to remain",
                                    phase_role="REMAIN")
            prior["SCOPE_STATUS"] = "PRIOR_ABS_REMAIN"

        # Existing cast iron to be demolished follows the same verified-plan
        # control network as the replacement, excluding retained ABS segments.
        _create_pipe_3d(f"EX_CI_{unit}_MAIN4", main4_pts, 4, ex_coll, mats["rust"], 2,
                        source="Like-for-like existing route representation; field verify")
        _create_pipe_3d(f"EX_CI_{unit}_LAT6_REPLACE", lat6_pts, 6, ex_coll, mats["rust"], 2,
                        source="Existing 6in segment within 18in replacement limit; field verify")

        # New replacement main and 6 in exterior segment.
        new4 = _create_pipe_3d(f"NEW_ABS_{unit}_4in_MAIN", main4_pts, 4, new_main_coll,
                               mats["abs"], 2,
                               source="P1.02/P3.1/P3.2 traced new Sch40 ABS",
                               phase_role="NEW_ABS")
        new6 = _create_pipe_3d(f"NEW_ABS_{unit}_6in_LATERAL_18IN_LIMIT", lat6_pts, 6,
                               new_main_coll, mats["abs"], 2,
                               source="P1.02/SOR: new 6in to 18in beyond foundation, then tie to existing lateral",
                               phase_role="NEW_ABS")
        new4["ROUTE_SOURCE_NOTE"] = d.get("source_note", "")
        new6["ROUTE_SOURCE_NOTE"] = d.get("source_note", "")

        # Branches are anchored to the Z of their explicit main junction. This
        # fixes the previous version's floating/disconnected branch elevations.
        for role, pts in d["branches_3"].items():
            pts3 = net["branch3"][role]
            _create_pipe_3d(f"EX_CI_{unit}_BR3_{role}", pts3, 3, ex_coll, mats["rust"], 2,
                            source="Existing branch route from P1.02/P3; field verify")
            obj = _create_pipe_3d(f"NEW_ABS_{unit}_3in_{role}", pts3, 3, branch_coll,
                                  mats["abs"], 2, source="P1.02/P3 traced 3in branch",
                                  phase_role="NEW_ABS")
            if role in ("laundry", "kitchen"):
                create_p_trap_if_applicable(unit, role, pts3[0], 3, branch_coll, mats)

        for role, pts in d["branches_2"].items():
            pts3 = net["branch2"][role]
            _create_pipe_3d(f"EX_CI_{unit}_BR2_{role}", pts3, 2, ex_coll, mats["rust"], 2,
                            source="Existing lavatory/fixture branch route from P1.02/P3; field verify")
            _create_pipe_3d(f"NEW_ABS_{unit}_2in_{role}", pts3, 2, branch_coll,
                            mats["abs"], 2, source="P1.02/P3 traced 2in branch",
                            phase_role="NEW_ABS")
            if not role.endswith("_common"):
                create_p_trap_if_applicable(unit, role, pts3[0], 2, branch_coll, mats)

        # Fixture stubs tee into explicit parent branches. These are unique
        # edges, not duplicate full fixture-to-main routes.
        for role, spec in d.get("branch3_stubs", {}).items():
            pts3 = net["branch3_stubs"][role]
            _create_pipe_3d(f"EX_CI_{unit}_BR3_STUB_{role}", pts3, 3, ex_coll, mats["rust"], 2,
                            source="Existing fixture stub traced from P3; field verify")
            _create_pipe_3d(f"NEW_ABS_{unit}_3in_STUB_{role}", pts3, 3, branch_coll, mats["abs"], 2,
                            source="P3 traced 3in fixture stub", phase_role="NEW_ABS")

        for role, spec in d.get("branch2_stubs", {}).items():
            pts3 = net["branch2_stubs"][role]
            _create_pipe_3d(f"EX_CI_{unit}_BR2_STUB_{role}", pts3, 2, ex_coll, mats["rust"], 2,
                            source="Existing fixture stub traced from P3; field verify")
            _create_pipe_3d(f"NEW_ABS_{unit}_2in_STUB_{role}", pts3, 2, branch_coll, mats["abs"], 2,
                            source="P3 traced 2in fixture stub", phase_role="NEW_ABS")
            create_p_trap_if_applicable(unit, role, pts3[0], 2, branch_coll, mats)

        # B-103 4 in sanitary route in the raised-floor assembly remains an
        # explicit 3D editable path rather than being forced into the slab model.
        if "raised_floor_4" in d:
            obj = create_curve("NEW_ABS_B103_4in_RAISED_FLOOR", d["raised_floor_4"], od_ft(4)/2,
                               new_main_coll, mats["abs"], 2,
                               source="P3.2 / 4D brief: B103 4in sanitary in raised floor assembly")
            obj["PHASE_ROLE"] = "NEW_ABS"
            obj["NOMINAL_DIAMETER_IN"] = 4
            obj["FIELD_VERIFY"] = True

        # Copper tracer wire alongside only the replacement nonmetallic 6 in segment.
        tracer = [(x + inch(3), y, z + inch(1)) for x,y,z in lat6_pts]
        tr = create_curve(f"TracerWire_{unit}", tracer, inch(0.06), new_main_coll, mats["copper"], 2,
                          source="4D brief: insulated copper tracer wire at new underground nonmetallic pipe")
        tr["PHASE_ROLE"] = "NEW_ABS"

        place_unit_fittings(unit, d, main4_pts, lat6_pts, tie_coll, mats)


def create_p_trap_if_applicable(unit, role, start_pt, nominal_in, coll, mats):
    x,y,z = start_pt
    r = ft(0, 4)
    points = [
        (x, y, z + ft(0,8)),
        (x, y, z + ft(0,2)),
        (x + r, y, z),
        (x + 2*r, y, z + ft(0,3)),
    ]
    obj = create_curve(f"PTRAP_{unit}_{role}", points, od_ft(nominal_in)/2, coll, mats["abs"], 2,
                       source="First-floor p-trap replacement scope")
    obj["PHASE_ROLE"] = "NEW_ABS"


def place_unit_fittings(unit, d, main4_pts, lat6_pts, coll, mats):
    # 4 in -> 6 in transition at the east foundation face / Grid 1.
    transition_pt = lat6_pts[0]
    x,y,z = transition_pt
    # Short horizontal fitting aligned with the east-west lateral. The prior
    # script accidentally modeled this coupling vertically through the slab.
    cyl = cylinder_between(f"{unit}_6in_TransitionCoupling",
                           (x,y-inch(5),z), (x,y+inch(5),z), od_ft(6)*0.62,
                           coll, mats["abs"], 2, source="P1.02: 4in waste to 6in waste transition; match existing I.E.")
    if cyl:
        cyl["PHASE_ROLE"] = "NEW_ABS"

    # Exterior cleanout at the 18 in scope boundary, with 12x12 concrete pad.
    cleanout_x, cleanout_y, cleanout_z = lat6_pts[-1]
    cleanout = create_curve(f"{unit}_Zurn_Z1450_6in_Cleanout",
                            [(cleanout_x, cleanout_y, cleanout_z), (cleanout_x, cleanout_y, ft(0,2))],
                            od_ft(6)/2, coll, mats["abs"], 2,
                            source="4D brief / SOR: exterior 6in cleanout at replacement limit")
    cleanout["PHASE_ROLE"] = "NEW_ABS"
    pad = create_box(f"{unit}_Cleanout_12x12_Pad", (ft(1), ft(1), inch(4)),
                     (cleanout_x, cleanout_y, inch(2)), coll, mats["pourback"], 2,
                     source="12x12 concrete cleanout pad")
    pad["PHASE_ROLE"] = "NEW_ABS"

    # Base-of-stack 4" cleanout / wye indicators at three apparent stack zones.
    fixture_pts = d["fixture_pts"]
    for idx, key in enumerate(("WC_N", "WC_S", "WB"), 1):
        sx, sy = fixture_pts[key]
        nominal = 4 if idx == 1 else 3
        # vertical tie-in to 10 pipe diameters above slab minimum (visualized 36" min too).
        top = max(ft(3,0), 10 * inch(nominal))
        riser = create_curve(f"{unit}_StackTieIn_{idx}_{nominal}in",
                             [(sx,sy,-ft(1,0)), (sx,sy,top)], od_ft(nominal)/2,
                             coll, mats["abs"], 2, source="P1.01/P5.1 stack tie-in vertical exposure")
        riser["PHASE_ROLE"] = "NEW_ABS"
        # cleanout plug representation
        bpy.ops.mesh.primitive_uv_sphere_add(segments=20, ring_count=10, radius=od_ft(nominal)*0.58,
                                             location=(sx, sy, inch(6)))
        co = bpy.context.object
        co.name = f"{unit}_BaseOfStack_Cleanout_{idx}"
        relink_object(co, coll)
        tag(co, 2, "Base-of-stack cleanout")
        set_material(co, mats["nickel"])
        co["PHASE_ROLE"] = "NEW_ABS"

        # Firestop/sleeve ring at slab/wall penetration.
        fire_coll = get_coll("Firestop_&_Sleeves")
        bpy.ops.mesh.primitive_torus_add(major_radius=od_ft(nominal)*0.66,
                                        minor_radius=inch(0.12), major_segments=32, minor_segments=8,
                                        location=(sx,sy,inch(0.1)))
        ring = bpy.context.object
        ring.name = f"{unit}_Firestop_Collar_{idx}"
        relink_object(ring, fire_coll)
        tag(ring, 2, "P5.1 UL-listed firestop penetration")
        set_material(ring, mats["firestop"])
        ring["PHASE_ROLE"] = "NEW_ABS"


def build_trench_layers(mats):
    bed_coll = get_coll("Pipe_Zone_Bedding")
    gen_coll = get_coll("General_Trench_Backfill")
    vapor_coll = get_coll("Vapor_Barrier_Stegowrap")
    rebar_coll = get_coll("Rebar_Dowels_&_Grid")
    pour_coll = get_coll("Concrete_Pourback")

    # Build from same trench control segments as Pass 1 so cut and restoration stay coordinated.
    rebar_lines = []
    transverse_lines = []
    dowel_lines = []

    for idx, seg in enumerate(TRENCH_SEGMENTS, 1):
        p0, p1 = seg["p0"], seg["p1"]
        length = segment_length_2d(p0, p1)
        if length < 1e-4:
            continue
        # Use the connected network elevation rather than a generic fixed depth.
        pipe_z, pipe_dia = trench_segment_pipe_data(seg["unit"], p0, p1, seg["role"])
        pipe_r = od_ft(pipe_dia)/2

        # 4" bedding.
        bed_t = inch(4)
        bed_center = pipe_z - pipe_r - bed_t/2
        o = make_segment_box(f"Bedding_{seg['unit']}_{idx:03d}", p0, p1, seg["width"],
                             bed_center, bed_t, bed_coll, mats["gravel"], 2,
                             source="P5.0/P5.1: min 4in bedding")
        if o:
            o["PHASE_ROLE"] = "BEDDING"

        # Pipe-zone fill from bedding top to 12" above pipe top.
        zone_bottom = bed_center + bed_t/2
        zone_top = pipe_z + pipe_r + ft(1,0)
        zone_h = max(inch(2), zone_top-zone_bottom)
        o = make_segment_box(f"PipeZone_{seg['unit']}_{idx:03d}", p0, p1, seg["width"],
                             zone_bottom + zone_h/2, zone_h, bed_coll, mats["pipezone"], 2,
                             source="P5.0: pipe zone to 12in above top of pipe")
        if o:
            o["PHASE_ROLE"] = "BACKFILL"

        # General backfill to slab underside.
        gen_bottom = zone_top
        gen_top = -SLAB_THICKNESS
        gen_h = max(inch(2), gen_top - gen_bottom)
        o = make_segment_box(f"GeneralBackfill_{seg['unit']}_{idx:03d}", p0, p1, seg["width"],
                             gen_bottom + gen_h/2, gen_h, gen_coll, mats["backfill"], 2,
                             source="P5.0: compacted 6–8in lifts to slab")
        if o:
            o["PHASE_ROLE"] = "BACKFILL"

        # Vapor barrier sheet lapped wider than cut.
        o = make_segment_box(f"Stego15mil_{seg['unit']}_{idx:03d}", p0, p1, seg["width"] + ft(1,0),
                             -SLAB_THICKNESS - inch(0.03), inch(0.06), vapor_coll, mats["stego"], 2,
                             source="P5.1 / brief: 15-mil StegoWrap Class A")
        if o:
            o["PHASE_ROLE"] = "BACKFILL"

        # Concrete pourback to slab top.
        o = make_segment_box(f"Pourback_{seg['unit']}_{idx:03d}", p0, p1, seg["width"],
                             -SLAB_THICKNESS/2, SLAB_THICKNESS, pour_coll, mats["pourback"], 2,
                             source="P5.1 / Addendum: 3000 psi patch with crystalline additive")
        if o:
            o["PHASE_ROLE"] = "POURBACK"

        # Rebar grid: #4 bars at <=12 in O.C., 1.5 in clear. Every other
        # transverse bar is extended 4 in beyond each trench edge as an epoxy dowel.
        a, b = Vector((p0[0],p0[1],0)), Vector((p1[0],p1[1],0))
        direction = (b-a).normalized()
        perp = Vector((-direction.y, direction.x, 0))
        zbar = -inch(1.75)  # 1.5 in top cover + #4 radius

        clear_half = max(inch(2), seg["width"]/2 - inch(1.75))
        clear_width = clear_half * 2.0
        lane_intervals = max(1, math.ceil(clear_width / ft(1,0)))
        for lane in range(lane_intervals + 1):
            u = lane / lane_intervals
            offset = -clear_half + clear_width * u
            aa = a + perp * offset
            bb = b + perp * offset
            rebar_lines.append([(aa.x,aa.y,zbar),(bb.x,bb.y,zbar)])

        # ceil(), not floor(), keeps spacing at or below 12 in.
        count = max(1, math.ceil(length / ft(1,0)))
        for j in range(count+1):
            t = j / count
            c = a.lerp(b,t)
            if j % 2 == 0:
                half = seg["width"]/2 + inch(4)
                target = dowel_lines
            else:
                half = clear_half
                target = transverse_lines
            aa = c - perp*half
            bb = c + perp*half
            target.append([(aa.x,aa.y,zbar),(bb.x,bb.y,zbar)])

    rb1 = create_curve_bundle("Rebar_Longitudinal_#4_12in_MAX", rebar_lines, inch(0.25), rebar_coll,
                              mats["rebar"], 2, source="P5.1/brief: #4 longitudinal grid <=12in OC")
    rb1["PHASE_ROLE"] = "BACKFILL"
    rb2 = create_curve_bundle("Rebar_Transverse_#4_12in_MAX", transverse_lines, inch(0.25), rebar_coll,
                              mats["rebar"], 2, source="P5.1/brief: #4 transverse grid <=12in OC")
    rb2["PHASE_ROLE"] = "BACKFILL"
    rb3 = create_curve_bundle("Rebar_Epoxy_Dowels_#4_EveryOther", dowel_lines, inch(0.25), rebar_coll,
                              mats["rebar"], 2, source="P5.1/brief: every other #4 transverse bar, 4in min epoxy embed")
    rb3["PHASE_ROLE"] = "BACKFILL"


def run_pass2():
    print("\n=== MEYDENBAUER PASS 2 ===")
    scene_setup()
    ensure_collection_tree()
    clear_pass(2)
    mats = ensure_material_library()
    create_existing_and_new_pipes(mats)
    build_trench_layers(mats)
    print("Pass 2 complete. Existing/new DWV and restoration layers generated.")

# -----------------------------------------------------------------------------
# PASS 3 — PARTITIONS / FINISHES / FIXTURES / PHASE CONTROLLER
# -----------------------------------------------------------------------------


def create_wall_segment(name, a, b, thickness, height, coll, mat, pass_id=3, source=""):
    p0, p1 = (a[0], a[1]), (b[0], b[1])
    return make_segment_box(name, p0, p1, thickness, height/2, height, coll, mat, pass_id, source)


def build_interior_partitions(mats):
    coll = get_coll("Wood_Stud_Partitions")
    # Plan-informed wet-core / laundry / kitchen partitions. Exact openings are schematic.
    for unit, (x0,x1) in UNIT_RANGES.items():
        w = x1-x0
        xc = (x0+x1)/2
        lines = [
            ((x0+w*0.12, ft(5)), (x0+w*0.12, ft(29))),
            ((x1-w*0.12, ft(5)), (x1-w*0.12, ft(29))),
            ((x0+w*0.12, ft(20)), (x1-w*0.12, ft(20))),
            ((x0+w*0.30, ft(29)), (x0+w*0.30, ft(37))),
            ((x1-w*0.30, ft(29)), (x1-w*0.30, ft(37))),
            ((xc, ft(5)), (xc, ft(20))),
        ]
        for i,(a,b) in enumerate(lines,1):
            o = create_wall_segment(f"PART_{unit}_{i:02d}", a,b,PARTITION_THICKNESS,GROUND_FLOOR_HEIGHT,
                                    coll,mats["gypsum"],3,source="P2/P3 room layout approximation")
            if o:
                o["PHASE_ROLE"] = "PARTITION"


def create_finish_materials(mats):
    # Unit B-101
    mats["PT6"] = ensure_marble_material("MAT_PT6_Evolution_Ivory", (0.80,0.77,0.68), (0.55,0.51,0.43))
    mats["PT7"] = ensure_material("MAT_PT7_2x2_Shower_Mosaic", (0.78,0.76,0.70), 0.34)
    mats["PT8"] = ensure_marble_material("MAT_PT8_Bernini_Bianco", (0.92,0.91,0.87), (0.52,0.54,0.57))
    mats["C1"] = ensure_material("MAT_C1_SoftSand_ToneBlue_Carpet", (0.33,0.40,0.43), 0.97)
    # B-102
    mats["PT10"] = ensure_material("MAT_PT10_Daltile_WhiteOctagon", (0.88,0.89,0.87), 0.35)
    mats["PT11"] = ensure_material("MAT_PT11_CashmereBlue_Penny", (0.22,0.48,0.58), 0.38)
    mats["PT12"] = ensure_material("MAT_PT12_ElegantBeige", (0.69,0.62,0.52), 0.40)
    mats["GT1"] = ensure_material("MAT_GT1_OceanSparkle_SkyBlue", (0.12,0.55,0.73), 0.16, alpha=0.88)
    mats["NS3"] = ensure_marble_material("MAT_NS3_Statuario_Honed", (0.90,0.90,0.89), (0.30,0.33,0.37))
    mats["PT9"] = ensure_material("MAT_PT9_Meta_LightGray_2x2", (0.57,0.58,0.59), 0.48)
    mats["NS2_PLUVIUM"] = ensure_material("MAT_NS2_Pental_Pluvium_Gesso", (0.70,0.70,0.66), 0.42)
    mats["EHF1"] = ensure_wood_material("MAT_EHF1_European_WhiteOak", (0.72,0.62,0.48), (0.40,0.30,0.18))
    mats["SAGE"] = ensure_material("MAT_B102_Sage_Seafoam_Wall", (0.46,0.62,0.52), 0.78)
    mats["VANITY_DARK"] = ensure_material("MAT_B102_DarkGray_Vanity", (0.10,0.12,0.13), 0.42)
    # B-103
    mats["PT1"] = ensure_material("MAT_PT1_Shen_WhiteShades", (0.83,0.84,0.82), 0.40)
    mats["PT2"] = ensure_material("MAT_PT2_Shower_Mosaic", (0.63,0.65,0.63), 0.45)
    mats["PT3"] = ensure_marble_material("MAT_PT3_BlackAtlantis", (0.08,0.08,0.09), (0.32,0.32,0.31))
    mats["PT4"] = ensure_material("MAT_PT4_Nobleza_Astorga", (0.47,0.40,0.34), 0.48)
    mats["PT5"] = ensure_wood_material("MAT_PT5_Emser_Cabin_Yosemite", (0.49,0.33,0.22), (0.17,0.09,0.045))
    # B-104
    mats["EHF2"] = ensure_wood_material("MAT_EHF2_Brentwood_BeechwoodOak", (0.54,0.39,0.24), (0.24,0.14,0.07))
    mats["CAB1"] = ensure_material("MAT_CAB1_DeWils_JustWhite", (0.90,0.89,0.85), 0.38)
    mats["CAB2"] = ensure_wood_material("MAT_CAB2_DeWils_ShadowGray", (0.30,0.29,0.28), (0.13,0.12,0.11))
    mats["QCT1"] = ensure_marble_material("MAT_QCT1_Pental_Borghini", (0.90,0.88,0.84), (0.40,0.36,0.32))
    mats["QCT2"] = ensure_marble_material("MAT_QCT2_Statuario", (0.93,0.93,0.92), (0.33,0.36,0.40))
    mats["CT1"] = ensure_material("MAT_CT1_TorrentWhite_4x16", (0.92,0.93,0.91), 0.24)
    mats["CT2"] = ensure_material("MAT_CT2_CottonGloss_3x12", (0.93,0.92,0.89), 0.20)
    mats["NS1"] = ensure_material("MAT_NS1_Rockwood_Limestone", (0.52,0.47,0.40), 0.54)
    return mats


def floor_patch(name, x0,x1,y0,y1, mat, coll, thickness=inch(0.18), z=inch(0.10), source=""):
    obj = create_box(name, (x1-x0,y1-y0,thickness), ((x0+x1)/2,(y0+y1)/2,z), coll, mat,3,source=source)
    obj["PHASE_ROLE"] = "FINISH"
    return obj


def build_finish_zones(mats):
    finish_map = {
        "B101": ("Unit_B101_Finishes", [
            ("GuestBath_PT6", 0.05,0.46, 0,16, "PT6"),
            ("MasterBath_PT8",0.54,0.95, 0,16, "PT8"),
            ("Master_Carpet_C1",0.54,0.95,16,26,"C1"),
        ]),
        "B102": ("Unit_B102_Finishes", [
            ("GuestBath_PT10",0.05,0.46,0,17,"PT10"),
            ("MasterBath_NS3",0.54,0.95,0,17,"NS3"),
            ("Hall_NS2",0.32,0.68,17,31,"NS2_PLUVIUM"),
            ("Bedrooms_EHF1",0.05,0.95,31,45,"EHF1"),
        ]),
        "B103": ("Unit_B103_Finishes", [
            ("Bath_PT1",0.05,0.95,0,17,"PT1"),
            ("Laundry_PT4",0.55,0.95,17,29,"PT4"),
            ("HallStudy_PT5",0.05,0.95,29,49,"PT5"),
        ]),
        "B104": ("Unit_B104_Finishes", [
            ("Bath_NS2",0.05,0.95,0,18,"NS2_PLUVIUM"),
            ("Hardwood_EHF2",0.05,0.95,18,BUILDING_WIDTH,"EHF2"),
        ]),
    }
    for unit,(coll_name,zones) in finish_map.items():
        coll = get_coll(coll_name)
        x0,x1 = UNIT_RANGES[unit]
        w=x1-x0
        for name,rx0,rx1,y0,y1,mat_key in zones:
            floor_patch(f"{unit}_{name}", x0+w*rx0,x0+w*rx1,y0,y1,mats[mat_key],coll,
                        source="Addendum custom finish schedule / 4D brief")


def build_floor_substrates(mats):
    primer_coll = get_coll("Vapor_Mitigating_Epoxy_Primer")
    water_coll = get_coll("Waterproofing_Membrane")
    radiant_coll = get_coll("Radiant_Heating_Coils")

    for unit in UNIT_RANGES:
        x0,x1 = UNIT_RANGES[unit]
        w=x1-x0
        # Primer strips in east wet areas.
        p = floor_patch(f"{unit}_EpoxyPrimer_WetArea", x0+w*0.05,x1-w*0.05,0,ft(20),mats["primer"],primer_coll,
                        thickness=inch(0.05),z=inch(0.02),source="Addendum: vapor-mitigating epoxy primer")
        p["PHASE_ROLE"] = "SUBSTRATE"
        wm = floor_patch(f"{unit}_TCNA_Waterproofing",x0+w*0.08,x1-w*0.08,0,ft(18),mats["waterproof"],water_coll,
                         thickness=inch(0.04),z=inch(0.06),source="Addendum/TCNA waterproofing + crack isolation")
        wm["PHASE_ROLE"] = "SUBSTRATE"

    for unit in ("B102","B104"):
        x0,x1=UNIT_RANGES[unit]; w=x1-x0
        polylines=[]
        y0,y1=ft(2),ft(16)
        x_start=x0+w*0.12; x_end=x1-w*0.12
        x=x_start; direction=1
        spacing=inch(6)
        while x <= x_end:
            if direction>0:
                polylines.append([(x,y0,inch(0.12)),(x,y1,inch(0.12))])
            else:
                polylines.append([(x,y1,inch(0.12)),(x,y0,inch(0.12))])
            x += spacing
            direction*=-1
        coil = create_curve_bundle(f"{unit}_220V_Radiant_Coil",polylines,inch(0.07),radiant_coll,mats["radiant"],3,
                                   source="Addendum/brief: heated coil flooring system")
        coil["PHASE_ROLE"]="SUBSTRATE"


def build_wall_patches(mats):
    nailer_coll=get_coll("Wall_Framing_Nailers")
    gyp_coll=get_coll("Gypsum_Board_Patches")
    cut_coll=get_coll("Drywall_Cutouts_DEMO")
    for unit,d in ROUTE_DATA.items():
        for i,key in enumerate(("WC_N","WC_S","WB"),1):
            x,y=d["fixture_pts"][key]
            # Generic demo cutout is suppressed for B101 because the calibrated
            # demolition model below owns its wall/carrier/stack exposure geometry.
            if unit != "B101":
                cut=create_box(f"{unit}_DrywallCutout_{i}",(ft(2.5),inch(0.3),ft(4)),(x,y,ft(2)),cut_coll,
                               ensure_material("MAT_DemoCutout",(0.9,0.05,0.02),0.4,alpha=0.25),3,
                               source="P1.01: lower wall exposure at stacks")
                cut["PHASE_ROLE"]="DEMO_CUTOUT"
            for s in (-1,1):
                n=create_box(f"{unit}_Nailer_{i}_{s}",(inch(1.5),inch(3.5),ft(4)),(x+s*ft(1.0),y,ft(2)),
                             nailer_coll,mats["wood_stud"],3,source="UL patch nailer")
                n["PHASE_ROLE"]="SUBSTRATE"
            # Single/double layer patch alternation to represent UL U305/U334 contexts.
            layers=1 if i%2 else 2
            for layer in range(layers):
                g=create_box(f"{unit}_GypsumPatch_{i}_L{layer+1}",(ft(2.5),inch(0.625),ft(4)),
                             (x,y+layer*inch(0.64),ft(2)),gyp_coll,mats["gypsum"],3,
                             source="UL U305/U334 5/8in Type X/Firecore patch")
                g["PHASE_ROLE"]="SUBSTRATE"
            seal=create_curve(f"{unit}_FireSeal_{i}",[(x-ft(1.2),y+inch(0.4),ft(0.1)),(x+ft(1.2),y+inch(0.4),ft(0.1))],
                              inch(0.07),gyp_coll,mats["firestop"],3,source="Red acoustical/fire sealant")
            seal["PHASE_ROLE"]="SUBSTRATE"


def primitive_to_collection(obj,name,coll,mat,source="fixture"):
    obj.name=name
    relink_object(obj,coll)
    tag(obj,3,source)
    if mat:
        set_material(obj,mat)
    obj["PHASE_ROLE"]="FIXTURE"
    return obj


def make_toilet(name,loc,coll,mats,floor_mounted=False):
    x,y,z=loc
    # Bowl.
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, location=(x,y,z+ft(1.25)))
    bowl=primitive_to_collection(bpy.context.object,name+"_BOWL",coll,mats["white"],"WC-1 Kohler Veil representation")
    bowl.scale=(0.72,0.95,0.52)
    if floor_mounted:
        bpy.ops.mesh.primitive_cube_add(size=1,location=(x,y-ft(0.45),z+ft(1.55)))
        tank=primitive_to_collection(bpy.context.object,name+"_TANK",coll,mats["white"],"Alternate #1 floor-mounted WC")
        tank.dimensions=(ft(1.3),ft(0.55),ft(1.6))
    return bowl


def make_tub(name,loc,coll,mats,new_variant=False):
    x,y,z=loc
    tub=create_box(name,(ft(5),ft(2.5),ft(1.5)),(x,y,z+ft(0.75)),coll,mats["white"],3,
                   source="BT-1 Kohler Villager 60in cast-iron tub representation")
    tub["PHASE_ROLE"]="FIXTURE_ALT2" if new_variant else "FIXTURE"
    return tub


def make_lav(name,loc,coll,mats):
    x,y,z=loc
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24,ring_count=12,location=(x,y,z+ft(2.6)))
    obj=primitive_to_collection(bpy.context.object,name,coll,mats["white"],"LAV-1 Kohler Caxton representation")
    obj.scale=(0.8,0.55,0.20)
    return obj


def make_shower(name,loc,coll,mats):
    x,y,z=loc
    pan=create_box(name+"_PAN",(ft(3),ft(3),inch(3)),(x,y,z+inch(1.5)),coll,mats["white"],3,
                   source="SH-1 alcove shower")
    pan["PHASE_ROLE"]="FIXTURE"
    glass=create_box(name+"_GLASS",(inch(0.25),ft(3),ft(6)),(x-ft(1.5),y,z+ft(3)),coll,mats["glass"],3,
                     source="Frameless shower enclosure")
    glass["PHASE_ROLE"]="FIXTURE"


def make_washer(name,loc,coll,mats):
    x,y,z=loc
    body=create_box(name,(ft(2.3),ft(2.5),ft(3.2)),(x,y,z+ft(1.6)),coll,
                    ensure_material("MAT_Appliance_White",(0.82,0.84,0.84),0.26),3,
                    source="LG WM4000HWA representation")
    body["PHASE_ROLE"]="FIXTURE"


def make_water_heater(name,loc,coll,mats):
    x,y,z=loc
    bpy.ops.mesh.primitive_cylinder_add(vertices=32,radius=inch(10.125),depth=ft(4.02),location=(x,y,z+ft(2.01)))
    obj=primitive_to_collection(bpy.context.object,name,coll,
                                ensure_material("MAT_WH_Gray",(0.66,0.67,0.68),0.45),"Rheem 40-gal electric WH")
    return obj


def make_kitchen_sink(name,loc,coll,mats):
    x,y,z=loc
    sink=create_box(name,(ft(2.7),ft(1.8),inch(8)),(x,y,z+ft(3)),coll,
                    ensure_material("MAT_Stainless",(0.32,0.34,0.35),0.22,metallic=0.9),3,
                    source="KS-1 Grohe 31815SD0 representation")
    sink["PHASE_ROLE"]="FIXTURE"


def build_fixtures_and_casework(mats):
    fix_coll=get_coll("Plumbing_Fixtures")
    case_coll=get_coll("Cabinets_&_Countertops")
    for unit,d in ROUTE_DATA.items():
        pts=d["fixture_pts"]
        # Use plan points as center locations; orientation is schematic.
        make_toilet(f"{unit}_WC1_N",(*pts["WC_N"],0),fix_coll,mats,False)
        make_toilet(f"{unit}_WC1_S",(*pts["WC_S"],0),fix_coll,mats,False)
        make_toilet(f"{unit}_WC_ALT1_Floor_N",(pts["WC_N"][0]+ft(1.5),pts["WC_N"][1],0),fix_coll,mats,True)
        make_toilet(f"{unit}_WC_ALT1_Floor_S",(pts["WC_S"][0]+ft(1.5),pts["WC_S"][1],0),fix_coll,mats,True)
        make_lav(f"{unit}_LAV_N",(*pts["LAV_N"],0),fix_coll,mats)
        make_lav(f"{unit}_LAV_S",(*pts["LAV_S"],0),fix_coll,mats)
        make_shower(f"{unit}_SH_N",(*pts["SH_N"],0),fix_coll,mats)
        make_tub(f"{unit}_BT_EXISTING",(*pts["TUB_S"],0),fix_coll,mats,False)
        make_tub(f"{unit}_BT_ALT2_NEW",(pts["TUB_S"][0]+ft(0.3),pts["TUB_S"][1]+ft(0.3),0),fix_coll,mats,True)
        make_washer(f"{unit}_WB1",(*pts["WB"],0),fix_coll,mats)
        make_water_heater(f"{unit}_WH1",(*pts["WH"],0),fix_coll,mats)
        make_kitchen_sink(f"{unit}_KS1",(*pts["KS"],0),fix_coll,mats)

        # Basic vanities / kitchen base cabinets.
        for key in ("LAV_N","LAV_S"):
            x,y=pts[key]
            mat=mats.get("VANITY_DARK",mats["wood_stud"]) if unit=="B102" else mats["wood_stud"]
            c=create_box(f"{unit}_{key}_Vanity",(ft(3),ft(1.8),ft(2.7)),(x,y+ft(0.8),ft(1.35)),case_coll,mat,3,
                         source="Vanity/casework restoration representation")
            c["PHASE_ROLE"]="CASEWORK"
        kx,ky=pts["KS"]
        kmat=mats["CAB1"] if unit=="B104" else mats["wood_stud"]
        qmat=mats["QCT1"] if unit=="B104" else mats["white"]
        cab=create_box(f"{unit}_Kitchen_BaseCab",(ft(8),ft(2),ft(2.8)),(kx,ky+ft(1),ft(1.4)),case_coll,kmat,3,
                       source="Kitchen base cabinet restoration")
        cab["PHASE_ROLE"]="CASEWORK"
        top=create_box(f"{unit}_Kitchen_Countertop",(ft(8.2),ft(2.15),inch(1.25)),(kx,ky+ft(1),ft(2.86)),case_coll,qmat,3,
                       source="Countertop restoration")
        top["PHASE_ROLE"]="CASEWORK"



# -----------------------------------------------------------------------------
# B-101 DETAILED SELECTIVE DEMOLITION MODEL — calibrated to P1.01 / P3.1 / SOR
# -----------------------------------------------------------------------------

B101_DEMO_COLLECTION_NAMES = [
    "B101_DEMO_00_Protection_&_Containment",
    "B101_DEMO_01_Remove_&_Reinstall",
    "B101_DEMO_02_Finish_Stripout",
    "B101_DEMO_03_Wall_&_Stack_Exposure",
    "B101_DEMO_04_Slab_Sawcut",
    "B101_DEMO_05_Slab_Removal_Chunks",
    "B101_DEMO_06_Excavation_&_Vapor_Exposure",
    "B101_DEMO_07_Cast_Iron_Removal",
    "B101_DEMO_07A_Existing_Fittings_Removal",
    "B101_DEMO_07B_PTraps_&_Fixture_Waste",
    "B101_DEMO_07C_WC_Carriers_&_Flanges",
    "B101_DEMO_07D_Cut_Locations_&_Supports",
    "B101_DEMO_99_Field_Verify_Overlays",
]


def ensure_b101_demo_collections():
    parent = get_coll("02_Existing_Conditions_&_Demo") or ensure_collection("02_Existing_Conditions_&_Demo")
    return {name: ensure_collection(name, parent) for name in B101_DEMO_COLLECTION_NAMES}


def ensure_b101_demo_materials():
    return {
        "protect": ensure_material("MAT_DEMO_Protect_Blue", (0.02, 0.30, 0.92), 0.28, alpha=0.20,
                                   emission=(0.02,0.15,0.55), emission_strength=0.35),
        "salvage": ensure_material("MAT_DEMO_RemoveReinstall_Yellow", (0.96, 0.62, 0.02), 0.32, alpha=0.46),
        "finish": ensure_material("MAT_DEMO_FinishStrip_Orange", (0.96, 0.22, 0.02), 0.38, alpha=0.44),
        "wall": ensure_material("MAT_DEMO_WallExposure_Magenta", (0.90, 0.02, 0.34), 0.30, alpha=0.40),
        "sawcut": ensure_material("MAT_DEMO_Sawcut_Black", (0.01, 0.01, 0.01), 0.72,
                                  emission=(0.55,0.03,0.01), emission_strength=0.30),
        "slab": ensure_material("MAT_DEMO_SlabChunk", (0.46, 0.44, 0.41), 0.88),
        "soil": ensure_material("MAT_DEMO_ExcavatedSoil", (0.33, 0.19, 0.08), 0.94, alpha=0.48),
        "vapor": ensure_material("MAT_DEMO_ExistingVapor_Preserve", (0.98, 0.72, 0.02), 0.28, alpha=0.45,
                                 emission=(1.0,0.50,0.0), emission_strength=0.25),
        "field": ensure_material("MAT_DEMO_FieldVerify_Red", (0.92, 0.02, 0.02), 0.30, alpha=0.18,
                                 emission=(0.75,0.01,0.01), emission_strength=0.55),
        "fitting": ensure_material("MAT_DEMO_ExistingCI_Fitting", (0.19, 0.105, 0.055), 0.88, metallic=0.28),
        "carrier": ensure_material("MAT_DEMO_WC_CarrierSteel", (0.23, 0.26, 0.29), 0.42, metallic=0.72),
        "support": ensure_material("MAT_DEMO_TempPipeSupport", (0.93, 0.48, 0.02), 0.34, metallic=0.48),
        "cutplane": ensure_material("MAT_DEMO_PipeCutPlane", (0.98, 0.02, 0.015), 0.25,
                                    emission=(1.0,0.01,0.0), emission_strength=1.35),
        "flange": ensure_material("MAT_DEMO_WallFlange", (0.42,0.43,0.44), 0.28, metallic=0.82),
        "text": ensure_material("MAT_DEMO_Text", (0.05,0.05,0.05), 0.65),
    }


def _set_demo_props(obj, role, action, status="REMOVE", field_verify=False, reinstall=False):
    if obj is None:
        return None
    obj["PHASE_ROLE"] = role
    obj["DEMO_ACTION"] = action
    obj["DEMO_STATUS"] = status
    obj["FIELD_VERIFY"] = bool(field_verify)
    obj["REMOVE_AND_REINSTALL"] = bool(reinstall)
    obj["UNIT"] = "B101"
    return obj


def _b101_trench_segments():
    return [seg for seg in TRENCH_SEGMENTS if seg["unit"] == "B101"]


def _animate_demo_proxy_to_storage(obj, frame_start=38, frame_end=48, dx=0.0, dy=ft(7), dz=ft(0.8)):
    if obj is None:
        return
    obj.keyframe_insert(data_path="location", frame=frame_start)
    obj.location.x += dx
    obj.location.y += dy
    obj.location.z += dz
    obj.keyframe_insert(data_path="location", frame=frame_end)


def _animate_slab_chunk_lift(obj, index, frame_start=68, frame_end=76):
    if obj is None:
        return
    obj.keyframe_insert(data_path="location", frame=frame_start)
    obj.location.z += ft(1.25) + (index % 3) * ft(0.20)
    obj.location.x += (-1 if index % 2 else 1) * ft(0.45)
    obj.keyframe_insert(data_path="location", frame=frame_end)


def _segment_edge_points(p0, p1, half_width, z):
    dx, dy = p1[0]-p0[0], p1[1]-p0[1]
    L = math.hypot(dx, dy)
    if L < 1e-8:
        return []
    nx, ny = -dy/L, dx/L
    return [
        [(p0[0]+nx*half_width, p0[1]+ny*half_width, z),
         (p1[0]+nx*half_width, p1[1]+ny*half_width, z)],
        [(p0[0]-nx*half_width, p0[1]-ny*half_width, z),
         (p1[0]-nx*half_width, p1[1]-ny*half_width, z)],
    ]



def _v3(v):
    return Vector((float(v[0]), float(v[1]), float(v[2])))


def _unit_vec(a, b):
    v = _v3(b) - _v3(a)
    if v.length <= 1e-8:
        return Vector((0.0, 0.0, 0.0))
    return v.normalized()


def _point_from(p, direction, distance):
    q = _v3(p) + Vector(direction) * float(distance)
    return (q.x, q.y, q.z)


def _turn_angle_deg(a, b, c):
    vin = _unit_vec(a, b)
    vout = _unit_vec(b, c)
    if vin.length == 0 or vout.length == 0:
        return 0.0
    dot = max(-1.0, min(1.0, vin.dot(vout)))
    return math.degrees(math.acos(dot))


def _closest_parent_tangent(parent_pts, join_pt):
    jp = _v3(join_pt)
    best = None
    for i in range(len(parent_pts)-1):
        a,b = _v3(parent_pts[i]), _v3(parent_pts[i+1])
        ab = b-a
        if ab.length <= 1e-8:
            continue
        t = max(0.0, min(1.0, (jp-a).dot(ab) / ab.dot(ab)))
        q = a + ab*t
        dist = (jp-q).length
        if best is None or dist < best[0]:
            best = (dist, ab.normalized(), i, t)
    return best[1] if best else Vector((0.0,1.0,0.0))


def _make_demo_hub(name, a, b, nominal_in, coll, mat, source, role="DEMO_CI"):
    obj = cylinder_between(name, a, b, od_ft(nominal_in)*0.59, coll, mat, 3, vertices=28, source=source)
    if obj:
        _set_demo_props(obj, role, "REMOVE EXISTING CAST-IRON FITTING", status="REMOVE", field_verify=True)
        obj["NOMINAL_DIAMETER_IN"] = nominal_in
        obj["EXISTING_FITTING_GEOMETRY"] = "INFERRED_FROM_PLAN_TOPOLOGY"
    return obj


def _make_existing_wye(name, join_pt, parent_tangent, branch_tangent, parent_dia, branch_dia, coll, dm, fitting_class):
    jp = _v3(join_pt)
    Lp = max(ft(0,7), od_ft(parent_dia)*1.8)
    Lb = max(ft(0,7), od_ft(branch_dia)*2.0)
    pt = Vector(parent_tangent).normalized()
    bt = Vector(branch_tangent).normalized()
    parts=[]
    parts.append(_make_demo_hub(name+"_P_A", tuple(jp-pt*Lp), tuple(jp), parent_dia, coll, dm["fitting"],
                                "SOR fittings: wye / combination wye + 1/8 bend / sanitary tee as applicable"))
    parts.append(_make_demo_hub(name+"_P_B", tuple(jp), tuple(jp+pt*Lp), parent_dia, coll, dm["fitting"],
                                "SOR fittings: approved vertical-horizontal fitting; exact existing type field verify"))
    parts.append(_make_demo_hub(name+"_BR", tuple(jp-bt*Lb), tuple(jp), branch_dia, coll, dm["fitting"],
                                "Existing branch fitting represented from plan topology; exact fitting field verify"))
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, radius=od_ft(parent_dia)*0.62, location=jp)
    body=bpy.context.object
    body.name=name+"_BODY"
    body.scale.z=0.82
    relink_object(body,coll); tag(body,3,"Existing cast-iron junction fitting; exact as-found fitting type field verify")
    set_material(body,dm["fitting"])
    _set_demo_props(body,"DEMO_CI","REMOVE EXISTING CAST-IRON JUNCTION FITTING",status="REMOVE",field_verify=True)
    body["FITTING_CLASS"] = fitting_class
    body["FITTING_TYPE_STATUS"] = "INFERRED / FIELD VERIFY"
    body["PARENT_NOMINAL_IN"] = parent_dia
    body["BRANCH_NOMINAL_IN"] = branch_dia
    return [p for p in parts if p] + [body]


def _make_existing_bend(name, a, b, c, nominal_in, coll, dm):
    ang = _turn_angle_deg(a,b,c)
    if ang < 5.0:
        return None
    vin = _unit_vec(b,a)
    vout = _unit_vec(b,c)
    leg = max(ft(0,7), od_ft(nominal_in)*2.2)
    p0 = _point_from(b, vin, leg)
    p2 = _point_from(b, vout, leg)
    obj=create_curve(name,[p0,b,p2],od_ft(nominal_in)*0.59,coll,dm["fitting"],3,
                     source="Existing CI bend inferred from P3.1 route geometry; exact fitting/radius field verify")
    _set_demo_props(obj,"DEMO_CI","REMOVE EXISTING CAST-IRON BEND",status="REMOVE",field_verify=True)
    obj["NOMINAL_DIAMETER_IN"] = nominal_in
    obj["PLAN_TURN_DEG"] = round(ang,1)
    if 35 <= ang <= 55:
        fit="1/8 BEND / 45 DEG APPROX"
    elif 75 <= ang <= 105:
        fit="1/4 BEND / 90 DEG APPROX"
    else:
        fit="BEND — ANGLE FIELD VERIFY"
    obj["FITTING_CLASS"] = fit
    obj["FITTING_TYPE_STATUS"] = "PLAN-INFERRED / FIELD VERIFY"
    return obj


def _make_existing_ptrap(name, fixture_xy, nominal_in, coll, dm, kind="FLOOR", conditional=False):
    x,y = fixture_xy
    if kind == "LAV":
        z_top, z_weir, z_low = ft(1,8), ft(1,3), ft(0,11)
        pts=[(x,y,z_top),(x,y,z_weir),(x+ft(0,4),y,z_low),(x+ft(0,8),y,z_weir),(x+ft(0,11),y,z_weir)]
    elif kind == "KITCHEN":
        z_top, z_weir, z_low = ft(1,7), ft(1,2), ft(0,10)
        pts=[(x,y,z_top),(x,y,z_weir),(x+ft(0,4),y,z_low),(x+ft(0,8),y,z_weir),(x+ft(1,0),y,z_weir)]
    else:
        z_top, z_weir, z_low = -inch(2), -inch(8), -ft(1,0)
        pts=[(x,y,z_top),(x,y,z_weir),(x+ft(0,4),y,z_low),(x+ft(0,8),y,z_weir),(x+ft(1,0),y,z_weir)]
    obj=create_curve(name,pts,od_ft(nominal_in)*0.56,coll,dm["fitting"],3,
                     source="SOR WP#1 includes first-floor p-traps; exact existing trap geometry/elevation field verify")
    action="CONDITIONAL REMOVE EXISTING P-TRAP — PRIOR REPAIR AREA" if conditional else "REMOVE EXISTING P-TRAP"
    _set_demo_props(obj,"DEMO_CI",action,status="CONDITIONAL" if conditional else "REMOVE",field_verify=True)
    obj["NOMINAL_DIAMETER_IN"] = nominal_in
    obj["FIXTURE_KIND"] = kind
    obj["APPROX_GEOMETRY"] = True
    obj["SCOPE_COMPONENT"] = "FIRST-FLOOR P-TRAP"
    if conditional:
        obj["PRIOR_REPAIR_EXCEPTION_COORDINATION"] = True
    return obj


def _make_wc_carrier(name, xy, coll, dm):
    x,y=xy
    parts=[]
    rail_dx=ft(0,9)
    rail_h=ft(4,0)
    rail_z=rail_h/2
    for side,dx in (("L",-rail_dx),("R",rail_dx)):
        parts.append(create_box(f"{name}_Rail_{side}",(inch(2),inch(3),rail_h),(x+dx,y,rail_z),coll,dm["carrier"],3,
                     source="Existing wall-hung WC carrier — generic coordination representation"))
    for label,z in (("Lower",ft(0,10)),("Mid",ft(2,0)),("Upper",ft(3,7))):
        parts.append(create_box(f"{name}_Crossbar_{label}",(ft(1,8),inch(2),inch(2)),(x,y,z),coll,dm["carrier"],3,
                     source="Existing wall-hung WC carrier — generic coordination representation"))
    parts.append(create_box(f"{name}_CarrierBody",(ft(1,4),inch(5),ft(2,4)),(x,y+inch(1),ft(2,5)),coll,dm["carrier"],3,
                    source="Existing concealed carrier body; manufacturer/type varies by unit"))
    outlet=cylinder_between(f"{name}_4in_WasteOutlet",(x,y-inch(8),ft(1,0)),(x,y+inch(8),ft(1,0)),od_ft(4)*0.55,
                            coll,dm["fitting"],3,source="SOR: wall-hung carrier and wall flange included in replacement")
    if outlet: parts.append(outlet)
    bpy.ops.mesh.primitive_torus_add(major_radius=od_ft(4)*0.62,minor_radius=inch(0.16),major_segments=32,minor_segments=8,
                                     location=(x,y-inch(8),ft(1,0)),rotation=(math.pi/2,0,0))
    flange=bpy.context.object; flange.name=f"{name}_WallFlange"
    relink_object(flange,coll); tag(flange,3,"Existing WC wall flange — remove with carrier/waste connection")
    set_material(flange,dm["flange"]); parts.append(flange)
    for o in parts:
        _set_demo_props(o,"DEMO_CI","REMOVE EXISTING WALL-HUNG WC CARRIER / FLANGE",status="REMOVE_REINSTALL_FIXTURE",field_verify=True)
        o["CARRIER_GEOMETRY"]="GENERIC — EXISTING MANUFACTURER VARIES"
    return parts


def _make_cut_ring(name, loc, nominal_in, coll, dm, orientation="HORIZONTAL", action="CUT EXISTING PIPE", confidence="RULE_BASED"):
    rot=(0,0,0) if orientation=="HORIZONTAL" else (math.pi/2,0,0)
    bpy.ops.mesh.primitive_torus_add(major_radius=od_ft(nominal_in)*0.66,minor_radius=inch(0.12),
                                     major_segments=36,minor_segments=8,location=loc,rotation=rot)
    ring=bpy.context.object; ring.name=name
    relink_object(ring,coll); tag(ring,3,"Demolition cut plane / disconnect marker")
    set_material(ring,dm["cutplane"])
    _set_demo_props(ring,"DEMO_CI_MARKER",action,status="CUT",field_verify=True)
    ring["NOMINAL_DIAMETER_IN"] = nominal_in
    ring["CUT_LOCATION_BASIS"] = confidence
    return ring


def _make_vertical_cut_support(name, xy, nominal_in, cut_z, coll, dm):
    x,y=xy
    z0=-ft(1,0)
    stack=cylinder_between(f"{name}_ExistingVerticalRemoval",(x,y,z0),(x,y,cut_z),od_ft(nominal_in)*0.53,
                           coll,dm["fitting"],3,source="SOR: expose/remove sufficient vertical stack for full fitting installation")
    if stack:
        _set_demo_props(stack,"DEMO_CI","REMOVE EXISTING VERTICAL WASTE SECTION",status="REMOVE",field_verify=True)
        stack["NOMINAL_DIAMETER_IN"] = nominal_in
        stack["MODEL_CUT_ELEV_IN_ABOVE_SLAB"] = round(cut_z*12,1)
    ring=_make_cut_ring(f"{name}_TopCutPlane",(x,y,cut_z),nominal_in,coll,dm,"HORIZONTAL",
                        action="TOP CUT — EXISTING VERTICAL STACK",confidence="MAX(36IN EXPOSURE, 10x PIPE DIAMETER) — FINAL FIELD VERIFY")
    for label,z in (("Below",max(inch(6),cut_z-inch(8))),("Above",cut_z+inch(8))):
        bpy.ops.mesh.primitive_torus_add(major_radius=od_ft(nominal_in)*0.66,minor_radius=inch(0.10),
                                         major_segments=28,minor_segments=7,location=(x,y,z))
        clamp=bpy.context.object; clamp.name=f"{name}_TempSupport_{label}"
        relink_object(clamp,coll); tag(clamp,3,"SOR: support piping above/below cut locations")
        set_material(clamp,dm["support"])
        _set_demo_props(clamp,"DEMO_CI_MARKER","TEMPORARY PIPE SUPPORT AT CUT",status="TEMPORARY",field_verify=True)
        clamp["SUPPORT_REQUIRED_BY_SOR"] = True
    return stack,ring


def build_b101_demolition_fittings(d, net, colls, dm):
    c_fit=colls["B101_DEMO_07A_Existing_Fittings_Removal"]
    c_trap=colls["B101_DEMO_07B_PTraps_&_Fixture_Waste"]
    c_car=colls["B101_DEMO_07C_WC_Carriers_&_Flanges"]
    c_cut=colls["B101_DEMO_07D_Cut_Locations_&_Supports"]
    fitting_count=0; bend_count=0; trap_count=0; carrier_count=0; cut_count=0
    main=net["main4"]
    for dia,grp in ((3,net["branch3"]),(2,net["branch2"])):
        for role,pts in grp.items():
            join=pts[-1]
            # The laundry branch lands at the calibrated prior-ABS / CI boundary.
            # Do not invent a demolition fitting inside the protected prior repair;
            # show that interface separately as FIELD VERIFY.
            if dia == 3 and role == "laundry":
                bpy.ops.mesh.primitive_uv_sphere_add(segments=20, ring_count=10, radius=od_ft(4)*0.72, location=join)
                iface=bpy.context.object; iface.name="B101_DEMO_Laundry_PriorABS_Interface_FIELD_VERIFY"
                relink_object(iface,colls["B101_DEMO_99_Field_Verify_Overlays"]); tag(iface,3,"P1.01 prior repair tie / laundry connection; exact fitting and demolition limit field verify")
                set_material(iface,dm["field"])
                _set_demo_props(iface,"DEMO_FIELD_VERIFY","VERIFY LAUNDRY / PRIOR-ABS / EXISTING-CI INTERFACE BEFORE DEMOLITION",status="FIELD_VERIFY",field_verify=True)
                continue
            ptan=_closest_parent_tangent(main,join)
            btan=_unit_vec(pts[-1],pts[-2])
            _make_existing_wye(f"B101_DEMO_CI_Wye_{dia}to4_{role}",join,ptan,btan,4,dia,c_fit,dm,
                               "WYE / COMBINATION WYE + 1/8 BEND — EXACT EXISTING TYPE FIELD VERIFY")
            fitting_count+=1
    for dia,stubgrp,parentgrp,specsrc in (
        (3,net.get("branch3_stubs",{}),net["branch3"],d.get("branch3_stubs",{})),
        (2,net.get("branch2_stubs",{}),net["branch2"],d.get("branch2_stubs",{}))):
        for role,pts in stubgrp.items():
            parent_name=specsrc[role]["parent"]
            parent=parentgrp[parent_name]
            join=pts[-1]
            ptan=_closest_parent_tangent(parent,join)
            btan=_unit_vec(pts[-1],pts[-2])
            _make_existing_wye(f"B101_DEMO_CI_Wye_{dia}in_{role}",join,ptan,btan,dia,dia,c_fit,dm,
                               "WYE / SANITARY TEE AS APPLICABLE — EXACT EXISTING TYPE FIELD VERIFY")
            fitting_count+=1
    routes=[]
    routes += [("MAIN4",4,net["main4"])]
    routes += [(f"BR3_{r}",3,p) for r,p in net["branch3"].items()]
    routes += [(f"BR2_{r}",2,p) for r,p in net["branch2"].items()]
    routes += [(f"BR3STUB_{r}",3,p) for r,p in net.get("branch3_stubs",{}).items()]
    routes += [(f"BR2STUB_{r}",2,p) for r,p in net.get("branch2_stubs",{}).items()]
    routes += [("LAT6",6,net["lateral6"])]
    for rname,dia,pts in routes:
        for i in range(1,len(pts)-1):
            if _turn_angle_deg(pts[i-1],pts[i],pts[i+1]) >= 5.0:
                _make_existing_bend(f"B101_DEMO_CI_Bend_{rname}_{i:02d}",pts[i-1],pts[i],pts[i+1],dia,c_fit,dm)
                bend_count+=1
    trap_specs=[
        ("LavTopLeft",(15.30,0.35),2,"LAV",False),
        ("LavTopRight",(18.50,0.35),2,"LAV",False),
        ("ShowerUpper",d["fixture_pts"]["SH_N"],2,"FLOOR",False),
        ("TubLower",d["fixture_pts"]["TUB_S"],2,"FLOOR",False),
        ("LavLower",d["fixture_pts"]["LAV_S"],2,"LAV",False),
        ("Laundry",d["fixture_pts"]["WB"],2,"FLOOR",False),
        ("Kitchen",d["fixture_pts"]["KS"],2,"KITCHEN",True),
    ]
    for label,xy,dia,kind,cond in trap_specs:
        _make_existing_ptrap(f"B101_DEMO_ExistingPTrap_{label}",xy,dia,c_trap,dm,kind,cond)
        trap_count+=1
    for label,key in (("North","WC_N"),("South","WC_S")):
        _make_wc_carrier(f"B101_DEMO_WCCarrier_{label}",d["fixture_pts"][key],c_car,dm)
        carrier_count+=1
    vertical_cut_specs=[
        ("WC_N_4in",d["fixture_pts"]["WC_N"],4),
        ("WC_S_4in",d["fixture_pts"]["WC_S"],4),
        ("UpperWetCore_3in",d["main_4"][3],3),
        ("LowerWetCore_3in",d["main_4"][1],3),
        ("Laundry_3in",d["fixture_pts"]["WB"],3),
    ]
    for label,xy,dia in vertical_cut_specs:
        cut_z=max(ft(3,0),inch(dia*10.0))
        _make_vertical_cut_support(f"B101_DEMO_Cut_{label}",xy,dia,cut_z,c_cut,dm)
        cut_count+=1
    prior_join=net["main4"][0]
    _make_cut_ring("B101_DEMO_Cut_PriorABS_Tie",prior_join,4,c_cut,dm,"VERTICAL",
                   action="CUT / DISCONNECT EXISTING CI AT RETAINED PRIOR-ABS TIE",
                   confidence="PLAN-CALIBRATED TIE — FINAL AS-FOUND LOCATION FIELD VERIFY")
    cut_count+=1
    ext_join=net["lateral6"][-1]
    _make_cut_ring("B101_DEMO_Cut_Exterior6in_18inLimit",ext_join,6,c_cut,dm,"VERTICAL",
                   action="CUT / DISCONNECT EXISTING 6IN AT +18IN REPLACEMENT LIMIT",
                   confidence="SOR SCOPE LIMIT — MATCH EXISTING I.E. FIELD VERIFY")
    cut_count+=1
    note=create_text("B101_DEMO_FittingConfidence_Note",
        "B-101 EXISTING FITTINGS / CUTS\nTOPOLOGY & SCOPE = CONTRACT-DOCUMENT BASED\n"
        "LEGACY FITTING TYPE / INVERT / FINAL CUT = FIELD VERIFY\n"
        "CUT TARGETS: >=36IN EXPOSURE; 10xD WHERE GOVERNING",
        (ft(7),ft(7),ft(5,6)),colls["B101_DEMO_99_Field_Verify_Overlays"],size=0.48,pass_id=3,mat=dm["text"],
        source="SOR vertical exposure / fitting / support requirements")
    _set_demo_props(note,"DEMO_FIELD_VERIFY","FITTING/CUT CONFIDENCE NOTE",status="REFERENCE",field_verify=True)
    scene=bpy.context.scene
    scene["MEYD_B101_Demo_ExistingJunctionFittings_count"] = fitting_count
    scene["MEYD_B101_Demo_ExistingBends_count"] = bend_count
    scene["MEYD_B101_Demo_PTraps_count"] = trap_count
    scene["MEYD_B101_Demo_WCCarriers_count"] = carrier_count
    scene["MEYD_B101_Demo_CutLocations_count"] = cut_count


def build_b101_demolition_model(mats):
    """Build construction-realistic B-101 selective demolition layers.

    Source intent:
    - P1.01: protect prior-repair ABS / do not demolish slab or pipe in repair zone;
      selectively remove DWV, fixtures, wall exposure, sawcut slab only as required.
    - SOR WP#1: fixtures/cabinets/appliances are generally remove-and-reinstall for access.
    - SOR notes: complete existing pipe removal unless Engineer approves abandonment;
      expose and preserve existing vapor barrier for transition to new system.
    - 02 41 19: systematic, neat sawcut demolition; protect items to remain and utilities.

    Geometry remains a coordination model: concealed wall limits, inverts, exact finish
    removal, and structural cutting are FIELD VERIFY items.
    """
    colls = ensure_b101_demo_collections()
    dm = ensure_b101_demo_materials()
    d = ROUTE_DATA["B101"]
    net = compute_unit_network_3d(d)
    segs = _b101_trench_segments()

    c_protect = colls["B101_DEMO_00_Protection_&_Containment"]
    c_salvage = colls["B101_DEMO_01_Remove_&_Reinstall"]
    c_finish = colls["B101_DEMO_02_Finish_Stripout"]
    c_wall = colls["B101_DEMO_03_Wall_&_Stack_Exposure"]
    c_saw = colls["B101_DEMO_04_Slab_Sawcut"]
    c_chunk = colls["B101_DEMO_05_Slab_Removal_Chunks"]
    c_exc = colls["B101_DEMO_06_Excavation_&_Vapor_Exposure"]
    c_ci = colls["B101_DEMO_07_Cast_Iron_Removal"]
    c_fit = colls["B101_DEMO_07A_Existing_Fittings_Removal"]
    c_trap = colls["B101_DEMO_07B_PTraps_&_Fixture_Waste"]
    c_carrier = colls["B101_DEMO_07C_WC_Carriers_&_Flanges"]
    c_cuts = colls["B101_DEMO_07D_Cut_Locations_&_Supports"]
    c_field = colls["B101_DEMO_99_Field_Verify_Overlays"]

    # ------------------------------------------------------------------ PROTECTION / CONTAINMENT
    # Tight containment just west of the work zone. Exact partition location is field coordinated.
    dust = create_box(
        "B101_DEMO_DustContainment",
        (UNIT_RANGES["B101"][1]-UNIT_RANGES["B101"][0], inch(1.0), GROUND_FLOOR_HEIGHT),
        ((UNIT_RANGES["B101"][0]+UNIT_RANGES["B101"][1])/2, ft(30.0), GROUND_FLOOR_HEIGHT/2),
        c_protect, mats.get("protection", dm["protect"]), 3,
        source="02 41 19 / SOR: temporary enclosure and dust protection; exact field location coordinated"
    )
    _set_demo_props(dust, "DEMO_PROTECT", "TEMPORARY DUST CONTAINMENT", status="TEMPORARY", field_verify=True)
    walkoff = create_box(
        "B101_DEMO_WalkoffMat", (ft(4),ft(7),inch(0.20)),
        (GX["E"]-ft(3),ft(31.5),inch(0.10)), c_protect,
        ensure_material("MAT_DEMO_WalkoffMat",(0.06,0.06,0.06),0.95), 3,
        source="02 41 19 / containment: protected access and dust-control walkoff mat"
    )
    _set_demo_props(walkoff,"DEMO_PROTECT","TEMPORARY WALK-OFF MAT",status="TEMPORARY",field_verify=True)

    # Broad prior-repair protection envelope from P1.01 cloud. Do not pretend this is surveyed.
    no_demo = create_box(
        "B101_DEMO_PriorRepair_NoDemo_Envelope",
        (ft(25.0), ft(16.0), inch(0.6)),
        (ft(32.0), ft(35.5), inch(0.35)),
        c_protect, dm["protect"], 3,
        source="P1.01: existing 4in Sch40 ABS previous repair; do not demolish slab or piping within indicated area; field verify extents"
    )
    _set_demo_props(no_demo, "DEMO_PROTECT", "PROTECT PRIOR ABS REPAIR / NO SLAB DEMO", status="REMAIN", field_verify=True)
    no_demo["DO_NOT_DEMOLISH"] = True

    # Route-specific protection strip around retained ABS.
    for i,(a,b) in enumerate(zip(d["prior_abs_4"], d["prior_abs_4"][1:]),1):
        o = make_segment_box(
            f"B101_DEMO_PriorABS_ProtectStrip_{i:02d}", a, b, ft(3.0), inch(0.45), inch(0.35),
            c_protect, dm["protect"], 3,
            source="P1.01/P3.1 prior ABS remain; 3ft visualization buffer only, field verify repair extents"
        )
        _set_demo_props(o, "DEMO_PROTECT", "PROTECT RETAINED ABS", status="REMAIN", field_verify=True)

    # Foundation crossing / structural no-cut warning volume. Existing opening/sleeve is field verified.
    fx = d["exit_x"]
    structural = create_box(
        "B101_DEMO_Foundation_NoCut_FieldVerify",
        (ft(4.0), inch(8.0), ft(2.5)),
        (fx, 0.0, ft(0.5)), c_field, dm["field"], 3,
        source="P1.01: no cutting/coring structural members; coordinate structural concrete and existing penetration"
    )
    _set_demo_props(structural, "DEMO_FIELD_VERIFY", "STRUCTURAL CROSSING — VERIFY BEFORE CUTTING", status="PROTECT", field_verify=True)
    structural["DO_NOT_CUT_STRUCTURE"] = True

    # ------------------------------------------------------------------ REMOVE / REINSTALL ACCESS ITEMS
    # These are access envelopes, not disposal quantities. They animate to protected storage.
    removal_specs = [
        ("WC_N", d["fixture_pts"]["WC_N"], (ft(2.0), ft(2.5), ft(3.0)), "WATER CLOSET + WALL CARRIER", True),
        ("WC_S", d["fixture_pts"]["WC_S"], (ft(2.0), ft(2.5), ft(3.0)), "WATER CLOSET + WALL CARRIER", True),
        ("SH_N", d["fixture_pts"]["SH_N"], (ft(3.0), ft(3.0), ft(6.5)), "SHOWER / ENCLOSURE AS REQUIRED", True),
        ("TUB_S", d["fixture_pts"]["TUB_S"], (ft(5.0), ft(2.5), ft(2.0)), "BATHTUB / ENCLOSURE AS REQUIRED", True),
        ("LAV_TOP_L", (15.30,0.35), (ft(3.0), ft(2.0), ft(3.0)), "LAVATORY + CABINET AS REQUIRED", True),
        ("LAV_TOP_R", (18.50,0.35), (ft(3.0), ft(2.0), ft(3.0)), "LAVATORY + CABINET AS REQUIRED", True),
        ("LAV_S", d["fixture_pts"]["LAV_S"], (ft(3.0), ft(2.0), ft(3.0)), "LAVATORY + CABINET AS REQUIRED", True),
        ("LAUNDRY", d["fixture_pts"]["WB"], (ft(5.0), ft(3.0), ft(4.0)), "WASHER / DRYER MOVE & REINSTALL", True),
    ]
    for i,(key,(x,y),dims,label,reinstall) in enumerate(removal_specs,1):
        obj = create_box(
            f"B101_DEMO_RemoveReinstall_{key}", dims, (x,y,dims[2]/2), c_salvage, dm["salvage"], 3,
            source="SOR WP#1: remove/move and reinstall existing fixture/cabinet/appliance as required for DW access"
        )
        _set_demo_props(obj, "DEMO_SALVAGE", label, status="REMOVE_REINSTALL", reinstall=reinstall)
        obj["ACCESS_ONLY"] = True
        _animate_demo_proxy_to_storage(obj, dx=(i%3-1)*ft(0.8), dy=ft(7.0)+(i%2)*ft(0.8), dz=ft(0.5))

    # Kitchen cabinet is conditional in B-101 because the calibrated prior ABS area remains.
    kx,ky = d["fixture_pts"]["KS"]
    kfield = create_box(
        "B101_DEMO_KitchenCabinet_Access_Conditional", (ft(8),ft(2.2),ft(3)),
        (kx,ky+ft(1.0),ft(1.5)), c_field, dm["protect"], 3,
        source="SOR says remove/reinstall sink cabinet as required; P1.01 prior-repair area is no-demo, so B101 cabinet access remains conditional"
    )
    _set_demo_props(kfield, "DEMO_FIELD_VERIFY", "KITCHEN CABINET ACCESS — ONLY IF REQUIRED", status="CONDITIONAL", field_verify=True, reinstall=True)

    # ------------------------------------------------------------------ FINISH STRIP-OUT
    finish_raw_area = 0.0
    for i,seg in enumerate(segs,1):
        # Finish access strip slightly wider than slab sawcut for controlled edge removal.
        width = seg["width"] + ft(0.50)
        length = segment_length_2d(seg["p0"],seg["p1"])
        finish_raw_area += length * width
        obj = make_segment_box(
            f"B101_DEMO_FinishStrip_{i:02d}_{seg['role']}", seg["p0"], seg["p1"], width,
            inch(0.12), inch(0.24), c_finish, dm["finish"], 3,
            source="Selective finish removal over access trench; exact finish limits field measured / allowance-controlled"
        )
        _set_demo_props(obj, "DEMO_FINISH", "REMOVE FINISH ASSEMBLY TO ACCESS SLAB", status="REMOVE", field_verify=True)
        obj["FINISH_LIMIT"] = "ACCESS STRIP — FINAL TILE/WALL RESTORATION LIMITS BY FIELD MEASURE / ALLOWANCES"

    # Allowance quantities are references, not forced geometry.
    allowance_text = (
        "B-101 FINISH DEMO / RESTORATION ALLOWANCE REFERENCE\n"
        "PT-6: 253 SF | PT-7: 25 SF | PT-8: 105 SF | C-1: 60 SF\n"
        "Remove tile/adhesive/mortar/membrane to bare substrate where included.\n"
        "MODEL ACCESS STRIPS DO NOT FORCE THESE ALLOWANCE QUANTITIES."
    )
    t = create_text("B101_DEMO_FinishAllowance_Note", allowance_text,
                    (ft(6),ft(20),inch(1.0)), c_field, size=0.55, pass_id=3, mat=dm["text"],
                    source="Addendum #1 01 21 00 / 01 22 00 B101 finish allowances")
    _set_demo_props(t, "DEMO_FIELD_VERIFY", "FINISH ALLOWANCE REFERENCE", status="REFERENCE", field_verify=True)

    # ------------------------------------------------------------------ WALL / STACK EXPOSURE
    # Vertical exposure is minimum 36in, and at least 10 pipe diameters where required.
    access_specs = [
        ("UpperWC_Carrier", d["fixture_pts"]["WC_N"], 4, ft(3.0)),
        ("LowerWC_Carrier", d["fixture_pts"]["WC_S"], 4, ft(3.0)),
        ("WetCore_Main", (d["main_4"][3][0], d["main_4"][3][1]), 4, ft(3.0)),
        ("Laundry_Tie", d["main_4"][0], 3, ft(2.5)),
    ]
    for name,(x,y),dia,width in access_specs:
        h = max(ft(3.0), inch(dia*10.0))
        # Main wet-core wall is modeled as running east-west / Y direction: thin X, wide Y.
        obj = create_box(
            f"B101_DEMO_WallExposure_{name}", (inch(0.75), width, h),
            (x,y,h/2), c_wall, dm["wall"], 3,
            source="P1.01/SOR: minimum 36in vertical exposure and minimum 10 pipe diameters for horizontal tie-in"
        )
        _set_demo_props(obj, "DEMO_WALL", f"REMOVE GYPSUM / EXPOSE {dia}IN VERTICAL CONNECTION", status="REMOVE_PATCH", field_verify=True)
        obj["MIN_EXPOSURE_IN"] = round(h*12.0,1)

    # ------------------------------------------------------------------ SLAB SAWCUT + REMOVAL CHUNKS
    raw_slab_area = 0.0
    raw_sawcut_length = 0.0
    raw_exc_cf = 0.0
    for i,seg in enumerate(segs,1):
        p0,p1,width = seg["p0"],seg["p1"],seg["width"]
        L = segment_length_2d(p0,p1)
        raw_slab_area += L * width
        raw_sawcut_length += 2.0 * L

        for e,edge in enumerate(_segment_edge_points(p0,p1,width/2,inch(0.08)),1):
            saw = create_curve(
                f"B101_DEMO_Sawcut_{i:02d}_E{e}", edge, inch(0.06), c_saw, dm["sawcut"], 3,
                source="P1.01 / 02 41 19: neat-line sawcut; small saw/grinding methods, not hammer/chop"
            )
            _set_demo_props(saw, "DEMO_SAWCUT", "SAWCUT SLAB EDGE", status="CUT")

        chunk = make_segment_box(
            f"B101_DEMO_SlabChunk_{i:02d}_{seg['role']}", p0,p1,width,
            -SLAB_THICKNESS/2, SLAB_THICKNESS, c_chunk, dm["slab"], 3,
            source="P1.01: sawcut and remove slab only as required for plumbing demolition"
        )
        _set_demo_props(chunk, "DEMO_SLAB_CHUNK", "LIFT / REMOVE SAWCUT SLAB", status="REMOVE")
        if chunk:
            chunk["SLAB_THICKNESS_IN"] = round(SLAB_THICKNESS*12,2)
            _animate_slab_chunk_lift(chunk,i)

        # Excavation volume follows pipe depth + bedding, clamped to documented 2.5–4.5ft range.
        pipe_z, nominal = trench_segment_pipe_data("B101", p0, p1, seg["role"])
        pipe_bottom = pipe_z - od_ft(nominal)/2
        exc_bottom = pipe_bottom - ft(0,6)
        exc_bottom = min(-ft(2,6), max(-ft(4,6), exc_bottom))
        top = -SLAB_THICKNESS
        depth = top - exc_bottom
        if depth > 0:
            raw_exc_cf += L * width * depth
            ex = make_segment_box(
                f"B101_DEMO_Excavation_{i:02d}_{seg['role']}", p0,p1,width,
                (top+exc_bottom)/2, depth, c_exc, dm["soil"], 3,
                source="SOR: excavate to expose/remove under-slab DW; depth based on model pipe + 6in bedding, field verify"
            )
            _set_demo_props(ex, "DEMO_EXCAVATION", "EXCAVATE TRENCH", status="REMOVE_SOIL", field_verify=True)
            ex["MODEL_BOTTOM_ELEV_FT"] = round(exc_bottom,3)
            ex["NOMINAL_PIPE_IN"] = nominal

        # Existing vapor barrier is exposed/preserved at trench footprint rather than treated as wholesale demo.
        vb = make_segment_box(
            f"B101_DEMO_ExistingVapor_Expose_{i:02d}", p0,p1,width+ft(0.5),
            -SLAB_THICKNESS-inch(0.04), inch(0.04), c_exc, dm["vapor"], 3,
            source="SOR Note 4: identify existing vapor barrier during demolition and preserve to greatest extent possible"
        )
        _set_demo_props(vb, "DEMO_VAPOR_EXPOSE", "EXPOSE / IDENTIFY / PRESERVE EXISTING VAPOR BARRIER", status="PRESERVE", field_verify=True)
        vb["DO_NOT_WHOLESALE_DEMOLISH"] = True

    # Exterior 18in connection excavation: soil only, no modeled slab removal in planter strip.
    lat = d["lateral_6"]
    ext = make_segment_box(
        "B101_DEMO_Exterior_18in_Connection_Pit", lat[0],lat[1],ft(4.0),-ft(2.25),ft(4.5),
        c_exc, dm["soil"], 3,
        source="SOR/P1.01: replace to at least 18in beyond foundation; connection outside slab, planter excavation preferred where possible"
    )
    _set_demo_props(ext, "DEMO_EXCAVATION", "EXTERIOR HAND EXCAVATION / 18IN TIE-IN", status="REMOVE_SOIL", field_verify=True)
    ext["NO_SLAB_REMOVAL_MODELED"] = True

    # ------------------------------------------------------------------ EXISTING CAST IRON REMOVAL / CUT POINTS
    # Pass 2 already builds the existing B101 cast-iron network. Reclassify it so
    # the detailed demo subphase removes it before Phase 4.
    for obj in bpy.data.objects:
        if obj.name.startswith("EX_CI_B101_"):
            obj["PHASE_ROLE"] = "DEMO_CI"
            obj["DEMO_ACTION"] = "CUT INTO MANAGEABLE SECTIONS / COMPLETE REMOVAL"
            obj["DEMO_STATUS"] = "REMOVE"
            obj["FIELD_VERIFY"] = True

    # Detailed existing fitting/carrier/P-trap/cut-location demolition model.
    build_b101_demolition_fittings(d, net, colls, dm)

    # Prior ABS remain label.
    label = create_text(
        "B101_DEMO_PriorABS_Label",
        "PRIOR 4IN ABS REPAIR — REMAIN\nDO NOT DEMOLISH SLAB OR PIPE\nFIELD VERIFY LIMITS / TIE-IN",
        (ft(31),ft(35),inch(1.1)), c_field, size=0.62, pass_id=3, mat=dm["text"],
        source="P1.01 explicit prior repair protection note"
    )
    _set_demo_props(label,"DEMO_FIELD_VERIFY","PRIOR ABS PROTECTION NOTE",status="REMAIN",field_verify=True)

    # Store auditable model quantities. These are model-derived raw quantities before overlap,
    # not contract measurements and not a substitute for field measurement.
    scene=bpy.context.scene
    scene["MEYD_B101_Demo_RawSlabArea_sf_before_overlap"] = round(raw_slab_area,1)
    scene["MEYD_B101_Demo_RawFinishStripArea_sf_before_overlap"] = round(finish_raw_area,1)
    scene["MEYD_B101_Demo_RawSawcutEdge_lf"] = round(raw_sawcut_length,1)
    scene["MEYD_B101_Demo_RawExcavation_cf_before_overlap"] = round(raw_exc_cf,1)
    scene["MEYD_B101_Demo_RawExcavation_cy_before_overlap"] = round(raw_exc_cf/27.0,2)
    scene["MEYD_B101_Demo_Note"] = "Raw model quantities before overlap; field measure governs. Prior repair no-demo zone excluded from trench generation."


def build_temporary_protection(mats):
    coll=get_coll("Temporary_Protection")
    # Dust partitions across unit depth separating wet/east work from living zones.
    for unit,(x0,x1) in UNIT_RANGES.items():
        if unit == "B101":
            continue  # detailed B101 demolition model owns containment/protection
        wall=create_box(f"{unit}_DustPartition",(x1-x0-inch(6),inch(0.1),GROUND_FLOOR_HEIGHT),
                        ((x0+x1)/2,ft(32),GROUND_FLOOR_HEIGHT/2),coll,mats["protection"],3,
                        source="Phase 2 floor-to-ceiling dustproof partition")
        wall["PHASE_ROLE"]="TEMP"
        mat=create_box(f"{unit}_WalkoffMat",(ft(3),ft(6),inch(0.2)),(x0+ft(3),ft(33),inch(0.1)),coll,
                       ensure_material("MAT_Walkoff",(0.08,0.08,0.08),0.92),3,source="Temporary walk-off mat")
        mat["PHASE_ROLE"]="TEMP"


def build_investigation_visuals(mats):
    """Phase-1 borescope / RF-locator visualization based on SOR investigation narrative."""
    coll=get_coll("Ex_Cast_Iron_Pipes_DEMO")
    probe_mat=ensure_material("MAT_Borescope_Locator",(0.02,0.85,0.95),0.18,
                              emission=(0.02,0.9,1.0),emission_strength=4.0)

    # Interior camera path: representative B-104 toilet branch into the same
    # connected route network used for the modeled waste piping, then through
    # the 18 in replacement limit to the existing side sewer.
    d=ROUTE_DATA["B104"]
    net=compute_unit_network_3d(d)
    wcx,wcy=d["fixture_pts"]["WC_S"]
    wc_branch=net["branch3"].get("bath_s", [])
    if wc_branch:
        interior_pts=[(wcx,wcy, wc_branch[0][2] + inch(2))]
        interior_pts.extend(wc_branch[1:])
    else:
        # Defensive fallback for future route-table edits.
        interior_pts=[(wcx,wcy,-ft(2,6))]
    # Continue downstream along the main from the branch junction, then the
    # replacement/existing laterals. Avoid duplicate XY/Z nodes.
    junction_xy=wc_branch[-1][:2] if wc_branch else None
    if junction_xy:
        start_idx=next((i for i,p in enumerate(net["main4"]) if p[:2]==junction_xy),0)
        interior_pts.extend(net["main4"][start_idx+1:])
    interior_pts.extend(net["lateral6"][1:])
    interior_pts.extend(net["context6"][1:])
    p1=create_curve("Borescope_Interior_WestToEast_Path",interior_pts,inch(0.08),coll,probe_mat,3,
                    source="SOR investigation: camera inserted from unit toilet west-to-east")
    p1["PHASE_ROLE"]="INVESTIGATION"
    p1.data.use_path=True
    p1.data.path_duration=30

    bpy.ops.mesh.primitive_uv_sphere_add(segments=20,ring_count=10,radius=inch(2.0),location=interior_pts[0])
    m1=primitive_to_collection(bpy.context.object,"Borescope_Interior_Locator",coll,probe_mat,"RF locator marker")
    m1["PHASE_ROLE"]="INVESTIGATION"
    c=m1.constraints.new('FOLLOW_PATH'); c.target=p1; c.use_fixed_location=True; c.forward_axis='FORWARD_X'; c.up_axis='UP_Z'
    c.offset_factor=0.0; c.keyframe_insert(data_path="offset_factor",frame=1)
    c.offset_factor=1.0; c.keyframe_insert(data_path="offset_factor",frame=30)

    # Exterior camera path: Building C cleanout side-sewer trace, south-to-north.
    side_pts=[(BUILDING_LENGTH+ft(15),SIDE_SEWER_Y,-ft(4,0)),(BUILDING_LENGTH*0.72,SIDE_SEWER_Y,-ft(4,0)),
              (BUILDING_LENGTH*0.35,SIDE_SEWER_Y,-ft(4,0)),(-ft(15),SIDE_SEWER_Y,-ft(4,0))]
    p2=create_curve("Borescope_SideSewer_SouthToNorth_Path",side_pts,inch(0.08),coll,probe_mat,3,
                    source="SOR investigation: second camera from Building C cleanout south-to-north")
    p2["PHASE_ROLE"]="INVESTIGATION"
    p2.data.use_path=True; p2.data.path_duration=30
    bpy.ops.mesh.primitive_uv_sphere_add(segments=20,ring_count=10,radius=inch(2.0),location=side_pts[0])
    m2=primitive_to_collection(bpy.context.object,"Borescope_SideSewer_Locator",coll,probe_mat,"RF locator marker")
    m2["PHASE_ROLE"]="INVESTIGATION"
    c2=m2.constraints.new('FOLLOW_PATH'); c2.target=p2; c2.use_fixed_location=True; c2.forward_axis='FORWARD_X'; c2.up_axis='UP_Z'
    c2.offset_factor=0.0; c2.keyframe_insert(data_path="offset_factor",frame=1)
    c2.offset_factor=1.0; c2.keyframe_insert(data_path="offset_factor",frame=30)


def build_test_visuals(mats):
    coll=get_coll("New_Stack_TieIns_&_Cleanouts")
    for unit,d in ROUTE_DATA.items():
        # Blue water proxy follows the exact connected main used by Pass 2,
        # rather than an independently sloped duplicate that can float above it.
        pts=compute_unit_network_3d(d)["main4"]
        water=create_curve(f"{unit}_WP2_WaterTest",pts,od_ft(4)*0.30,coll,mats["water"],3,
                           source="Phase 5 water-test visualization")
        water["PHASE_ROLE"]="WATER_TEST"
        # Test plug at fixture-end of main.
        p=pts[0]
        bpy.ops.mesh.primitive_cylinder_add(vertices=24,radius=od_ft(4)*0.45,depth=inch(2),location=p)
        plug=primitive_to_collection(bpy.context.object,f"{unit}_TestPlug",coll,
                                     ensure_material("MAT_TestPlug",(0.12,0.15,0.18),0.5),"WP2 test plug visualization")
        plug["PHASE_ROLE"]="WATER_TEST"


def build_asbuilt_overlay(mats):
    coll=get_coll("As_Built_Callout_Overlay")
    for unit,d in ROUTE_DATA.items():
        x=d["exit_x"]
        t=create_text(f"CALL_{unit}_EXIT",f"{unit}\n6\" LATERAL → 8\" SS\nVERIFY I.E. ±2\"",(x,-ft(5),ft(2)),coll,
                      size=0.65,rotation=(math.radians(75),0,0),pass_id=3,mat=mats["grid"],
                      source="Final as-built callout overlay")
        t["PHASE_ROLE"]="ASBUILT"
    note=create_text("CALL_GENERAL_VERIFY","AS-BUILT CONTROL\nFIELD VERIFY ROUTES / INVERTS / FITTINGS",
                     (BUILDING_LENGTH/2,BUILDING_WIDTH+ft(8),ft(5)),coll,size=1.2,
                     rotation=(math.radians(75),0,0),pass_id=3,mat=mats["grid"],source="WP3 documentation overlay")
    note["PHASE_ROLE"]="ASBUILT"


def build_camera_and_lights(mats):
    # A useful default 3/4 view; does not replace user's shot/camera work.
    coll=ensure_collection("00_Site_&_Context")
    bpy.ops.object.camera_add(location=(BUILDING_LENGTH*0.70,-ft(95),ft(92)))
    cam=bpy.context.object; cam.name="MEYD_ISO_CAMERA"; relink_object(cam,coll); tag(cam,3,"Default 3/4 coordination camera")
    target=Vector((BUILDING_LENGTH*0.52,BUILDING_WIDTH*0.42,-ft(0.5)))
    direction=target-cam.location
    cam.rotation_euler=direction.to_track_quat('-Z','Y').to_euler()
    cam.data.lens=50
    bpy.context.scene.camera=cam

    bpy.ops.object.light_add(type='SUN',location=(BUILDING_LENGTH/2,-ft(20),ft(70)))
    sun=bpy.context.object; sun.name="MEYD_SUN"; relink_object(sun,coll); tag(sun,3,"Visualization light")
    sun.rotation_euler=(math.radians(35),math.radians(-20),math.radians(25)); sun.data.energy=2.0

    bpy.ops.object.light_add(type='AREA',location=(BUILDING_LENGTH/2,BUILDING_WIDTH/2,ft(70)))
    area=bpy.context.object; area.name="MEYD_AREA_FILL"; relink_object(area,coll); tag(area,3,"Visualization light")
    area.data.energy=2500; area.data.shape='RECTANGLE'; area.data.size=ft(100); area.data.size_y=ft(60)
    area.rotation_euler=(0,0,0)

# ----------------------------- PHASE DRIVERS ----------------------------------


def remove_drivers_targeting_controller():
    controller=bpy.data.objects.get("PHASE_CONTROLLER")
    # Object animation-data includes object properties + modifier properties.
    for obj in bpy.data.objects:
        ad=obj.animation_data
        if not ad or not ad.drivers:
            continue
        for fc in list(ad.drivers):
            remove=False
            for v in fc.driver.variables:
                for t in v.targets:
                    if controller is not None and t.id == controller:
                        remove=True
                    elif t.id is not None and getattr(t.id,"name","") == "PHASE_CONTROLLER":
                        remove=True
            if remove:
                try:
                    if fc.array_index >= 0:
                        obj.driver_remove(fc.data_path,fc.array_index)
                    else:
                        obj.driver_remove(fc.data_path)
                except Exception:
                    try: obj.driver_remove(fc.data_path)
                    except Exception: pass
    # Material node-tree drivers.
    for mat in bpy.data.materials:
        nt=mat.node_tree if mat.use_nodes else None
        if not nt or not nt.animation_data or not nt.animation_data.drivers:
            continue
        for fc in list(nt.animation_data.drivers):
            remove=False
            for v in fc.driver.variables:
                for t in v.targets:
                    if controller is not None and t.id == controller:
                        remove=True
                    elif t.id is not None and getattr(t.id,"name","") == "PHASE_CONTROLLER":
                        remove=True
            if remove:
                try: nt.driver_remove(fc.data_path,fc.array_index)
                except Exception:
                    try: nt.driver_remove(fc.data_path)
                    except Exception: pass


def add_driver(owner, data_path, controller, expression, array_index=None, variables=None):
    try:
        fc=owner.driver_add(data_path) if array_index is None else owner.driver_add(data_path,array_index)
    except TypeError:
        fc=owner.driver_add(data_path)
    drv=fc.driver
    drv.type='SCRIPTED'
    drv.expression=expression
    try:
        drv.variables.clear()
    except Exception:
        while len(drv.variables):
            drv.variables.remove(drv.variables[0])
    variables=variables or {"phase":"Construction_Phase"}
    for var_name,prop_name in variables.items():
        v=drv.variables.new(); v.name=var_name; v.type='SINGLE_PROP'
        targ=v.targets[0]; targ.id=controller; targ.data_path=f'["{prop_name}"]'
    return fc


def visibility_driver(obj, controller, visible_expr, extra_vars=None):
    # hide = NOT visible. Boolean driver expression uses Python-compatible logic.
    expr=f"not ({visible_expr})"
    vars={"phase":"Construction_Phase"}
    if extra_vars: vars.update(extra_vars)
    errors=[]
    for prop in ("hide_viewport","hide_render"):
        try:
            add_driver(obj,prop,controller,expr,variables=vars)
        except Exception as exc:
            errors.append(f"{prop}: {type(exc).__name__}: {exc}")
    if errors:
        # Surface driver failures to validation instead of silently leaving an
        # object visible in every phase.
        obj["MEYD_DRIVER_ERROR"]=" | ".join(errors)
    elif "MEYD_DRIVER_ERROR" in obj:
        del obj["MEYD_DRIVER_ERROR"]


def attach_phase_drivers(controller):
    for obj in bpy.data.objects:
        if obj.get("MEYD_PROJECT") != PROJECT_TAG:
            continue
        role=obj.get("PHASE_ROLE","")
        name=obj.name
        if role == "DEMO_PROTECT":
            visibility_driver(obj,controller,"phase>=2 and phase<=3")
        elif role == "DEMO_SALVAGE":
            visibility_driver(obj,controller,"phase==2 and demo<=1",{"demo":"Demolition_Subphase"})
        elif role == "DEMO_FINISH":
            visibility_driver(obj,controller,"phase==2 and demo>=1 and demo<=2",{"demo":"Demolition_Subphase"})
        elif role == "DEMO_WALL":
            visibility_driver(obj,controller,"phase==3 and demo>=3 and demo<=5",{"demo":"Demolition_Subphase"})
        elif role == "DEMO_SAWCUT":
            visibility_driver(obj,controller,"phase==3 and demo>=4 and demo<=5",{"demo":"Demolition_Subphase"})
        elif role == "DEMO_SLAB_CHUNK":
            visibility_driver(obj,controller,"phase==3 and demo>=4 and demo<6",{"demo":"Demolition_Subphase"})
        elif role == "DEMO_EXCAVATION":
            visibility_driver(obj,controller,"phase==3 and demo>=5",{"demo":"Demolition_Subphase"})
        elif role == "DEMO_VAPOR_EXPOSE":
            visibility_driver(obj,controller,"phase==3 and demo>=5",{"demo":"Demolition_Subphase"})
        elif role == "DEMO_CI":
            visibility_driver(obj,controller,"phase<=2 or (phase==3 and demo<7)",{"demo":"Demolition_Subphase"})
        elif role == "DEMO_CI_MARKER":
            visibility_driver(obj,controller,"phase==3 and demo>=6 and demo<7",{"demo":"Demolition_Subphase"})
        elif role == "DEMO_FIELD_VERIFY":
            visibility_driver(obj,controller,"phase>=2 and phase<=3")
        elif role == "REMAIN":
            visibility_driver(obj,controller,"phase>=1")
        elif role == "NEW_ABS":
            visibility_driver(obj,controller,"phase>=4")
        elif role == "BEDDING":
            visibility_driver(obj,controller,"phase>=4")
        elif role in ("BACKFILL","POURBACK"):
            visibility_driver(obj,controller,"phase>=6")
        elif role == "SUBSTRATE":
            visibility_driver(obj,controller,"phase>=7")
        elif role == "PARTITION":
            visibility_driver(obj,controller,"phase>=1")
        elif role == "FINISH":
            visibility_driver(obj,controller,"phase<=2 or phase>=7")
        elif role == "CASEWORK":
            visibility_driver(obj,controller,"phase==1 or phase==8")
        elif role == "TEMP":
            visibility_driver(obj,controller,"phase>=2 and phase<=7")
        elif role == "DEMO_CUTOUT":
            visibility_driver(obj,controller,"phase==3")
        elif role == "WATER_TEST":
            visibility_driver(obj,controller,"phase==5")
        elif role == "INVESTIGATION":
            visibility_driver(obj,controller,"phase==1")
        elif role == "ASBUILT":
            visibility_driver(obj,controller,"phase==8")
        elif role == "FIXTURE_ALT2":
            visibility_driver(obj,controller,"phase==8 and alt2>0.5",{"alt2":"Alternate_2_New_Bathtubs"})
        elif role == "FIXTURE":
            if "WC_ALT1" in name:
                visibility_driver(obj,controller,"phase==8 and alt1>0.5",{"alt1":"Alternate_1_Floor_Mounted_Toilets"})
            elif "WC1_" in name:
                visibility_driver(obj,controller,"phase==1 or (phase==8 and alt1<0.5)",{"alt1":"Alternate_1_Floor_Mounted_Toilets"})
            elif "BT_EXISTING" in name:
                visibility_driver(obj,controller,"phase==1 or (phase==8 and alt2<0.5)",{"alt2":"Alternate_2_New_Bathtubs"})
            else:
                visibility_driver(obj,controller,"phase==1 or phase==8")
        elif name.startswith("EX_CI_"):
            visibility_driver(obj,controller,"phase<=3")

    # Explicit existing cast-iron collection objects (older role-less objects).
    ex_coll=get_coll("Ex_Cast_Iron_Pipes_DEMO")
    if ex_coll:
        for obj in ex_coll.objects:
            if obj.get("PHASE_ROLE") == "DEMO_CI":
                continue
            visibility_driver(obj,controller,"phase<=3")

    # Trench cutter guides viewport only during demolition; never render.
    cut_coll=get_coll("Concrete_Slab_Trench_Cuts_DEMO")
    if cut_coll:
        for obj in cut_coll.objects:
            try: add_driver(obj,"hide_viewport",controller,"phase!=3")
            except Exception: pass
            obj.hide_render=True

    # Slab Boolean turns on at Phase 3 and stays on; pourback visually fills cut at Phase 6.
    slab=bpy.data.objects.get("BuildingB_SOG_5p5in")
    if slab:
        mod=slab.modifiers.get("MEYD_Trench_Difference")
        if mod:
            for prop in ("show_viewport","show_render"):
                try:
                    add_driver(mod,prop,controller,"(phase>3) or (phase==3 and demo>=5)",
                               variables={"phase":"Construction_Phase","demo":"Demolition_Subphase"})
                except Exception: pass

    # X-ray structural materials during Phase 1 only.
    for mat_name in ("MAT_Concrete_Shell_Xray","MAT_Precast_Xray"):
        mat=bpy.data.materials.get(mat_name)
        if not mat or not mat.use_nodes: continue
        node=mat.node_tree.nodes.get("XRAY_SHADER")
        if node and "Alpha" in node.inputs:
            try:
                add_driver(node.inputs["Alpha"],"default_value",controller,"0.28 if phase==1 else 1.0")
            except Exception:
                pass


def create_phase_controller():
    delete_named_object("PHASE_CONTROLLER")
    coll=ensure_collection("00_Site_&_Context")
    bpy.ops.object.empty_add(type='PLAIN_AXES',location=(BUILDING_LENGTH/2,-ft(8),ft(6)))
    ctrl=bpy.context.object
    ctrl.name="PHASE_CONTROLLER"
    ctrl.empty_display_size=ft(3)
    relink_object(ctrl,coll)
    tag(ctrl,3,"4D construction phase controller")
    ctrl["Construction_Phase"]=1
    ui=ctrl.id_properties_ui("Construction_Phase"); ui.update(min=1,max=8,soft_min=1,soft_max=8,description="1 Existing; 2 Staging; 3 Demo; 4 New ABS; 5 Test; 6 Backfill; 7 Finishes; 8 Final")
    ctrl["Alternate_1_Floor_Mounted_Toilets"]=False
    ctrl["Alternate_2_New_Bathtubs"]=False
    ctrl["Demolition_Subphase"] = 0
    dui = ctrl.id_properties_ui("Demolition_Subphase")
    dui.update(min=0,max=7,soft_min=0,soft_max=7,description="0 protect/stage; 1 remove/reinstall access items; 2 finish strip; 3 wall exposure; 4 sawcut; 5 slab removal; 6 excavation/expose CI; 7 CI removal/clean trench")

    # Detailed B-101 demolition subphase, keyed within Phases 2 and 3.
    demo_keys = {31:0, 38:1, 50:2, 61:3, 68:4, 76:5, 83:6, 89:7, 91:7}
    for frame, sub in demo_keys.items():
        ctrl["Demolition_Subphase"] = sub
        ctrl.keyframe_insert(data_path='["Demolition_Subphase"]', frame=frame)

    # Keyframe integer phase every 30 frames, stepped/constant.
    phase_starts={1:1,2:31,3:61,4:91,5:121,6:151,7:181,8:211}
    for phase,frame in phase_starts.items():
        ctrl["Construction_Phase"]=phase
        ctrl.keyframe_insert(data_path='["Construction_Phase"]',frame=frame)
    if ctrl.animation_data and ctrl.animation_data.action:
        action = ctrl.animation_data.action
        data_path = '["Construction_Phase"]'
        try:
            # Blender 4.4+/5.x layered Action API. This safely locates the F-Curve
            # for the controller datablock without assuming a legacy action layout.
            if hasattr(action, "fcurve_ensure_for_datablock"):
                fc = action.fcurve_ensure_for_datablock(ctrl, data_path, index=0)
                for kp in fc.keyframe_points:
                    kp.interpolation = 'CONSTANT'
            else:
                for fc in action.fcurves:
                    if fc.data_path == data_path:
                        for kp in fc.keyframe_points:
                            kp.interpolation = 'CONSTANT'
        except Exception:
            # Blender 3.x / early 4.x fallback.
            try:
                for fc in action.fcurves:
                    for kp in fc.keyframe_points:
                        kp.interpolation = 'CONSTANT'
            except Exception:
                pass

    # Force demolition subphase keys to stepped interpolation as well.
    try:
        action = ctrl.animation_data.action if ctrl.animation_data else None
        data_path = '["Demolition_Subphase"]'
        if action:
            if hasattr(action, "fcurve_ensure_for_datablock"):
                fc = action.fcurve_ensure_for_datablock(ctrl, data_path, index=0)
                for kp in fc.keyframe_points: kp.interpolation = 'CONSTANT'
            else:
                for fc in action.fcurves:
                    if fc.data_path == data_path:
                        for kp in fc.keyframe_points: kp.interpolation = 'CONSTANT'
    except Exception:
        pass

    # Timeline markers.
    scene=bpy.context.scene
    for marker in list(scene.timeline_markers):
        if marker.name.startswith("PHASE_"):
            scene.timeline_markers.remove(marker)
    names={1:"Existing + Investigation",2:"Staging + Fixture Removal",3:"Demo + Excavation",
           4:"New ABS Installation",5:"WP2 Water Test",6:"Backfill + Pourback",
           7:"Patching + Finishes",8:"Fixture Reinstall + As-Built"}
    for phase,frame in phase_starts.items():
        scene.timeline_markers.new(f"PHASE_{phase:02d}_{names[phase]}",frame=frame)
    demo_names={38:"Remove-Reinstall Access Items",50:"Finish Stripout",61:"Wall-Stack Exposure",
                68:"Sawcut Slab",76:"Lift Slab + Vapor Exposure",83:"Excavate + Expose CI",89:"Remove CI + Clean Trench"}
    for frame,label in demo_names.items():
        scene.timeline_markers.new(f"B101_DEMO_{frame:03d}_{label}",frame=frame)
    ctrl["Construction_Phase"]=1
    ctrl["Demolition_Subphase"]=0
    scene.frame_set(1)
    return ctrl


def run_pass3():
    print("\n=== MEYDENBAUER PASS 3 ===")
    scene_setup()
    ensure_collection_tree()
    remove_drivers_targeting_controller()
    clear_pass(3)
    mats=ensure_material_library()
    mats=create_finish_materials(mats)
    build_interior_partitions(mats)
    build_floor_substrates(mats)
    build_finish_zones(mats)
    build_wall_patches(mats)
    build_fixtures_and_casework(mats)
    build_b101_demolition_model(mats)
    build_temporary_protection(mats)
    build_investigation_visuals(mats)
    build_test_visuals(mats)
    build_asbuilt_overlay(mats)
    build_camera_and_lights(mats)
    ctrl=create_phase_controller()
    attach_phase_drivers(ctrl)
    print("Pass 3 complete. PHASE_CONTROLLER + 8-phase driver rig generated.")

# -----------------------------------------------------------------------------
# VALIDATION / REPORTING
# -----------------------------------------------------------------------------


def validate_route_controls_static():
    """Validate source-control geometry without requiring evaluated Blender meshes."""
    issues = []
    expected_length = ft(160, 5.5)
    if abs(BUILDING_LENGTH - expected_length) > 1e-6:
        issues.append(f"Grid total mismatch: expected 160'-5.5\"; got {BUILDING_LENGTH:.4f} ft")

    for unit, d in ROUTE_DATA.items():
        # Plan controls inside the Building B footprint, except the intentional
        # 18 in exterior replacement segment and side-sewer context.
        for group_name, routes in (
            ("main_4", [d["main_4"]]),
            ("branches_3", list(d["branches_3"].values()) + [v["points"] for v in d.get("branch3_stubs", {}).values()]),
            ("branches_2", list(d["branches_2"].values()) + [v["points"] for v in d.get("branch2_stubs", {}).values()]),
        ):
            for route in routes:
                for x, y in route:
                    if not (-1e-6 <= x <= BUILDING_LENGTH + 1e-6 and -1e-6 <= y <= BUILDING_WIDTH + 1e-6):
                        issues.append(f"{unit} {group_name} control outside footprint: {(x,y)}")

        if d["main_4"][-1] != d["lateral_6"][0]:
            issues.append(f"{unit}: main_4 does not terminate at lateral_6 start")
        if abs(d["lateral_6"][-1][1] + ft(1,6)) > 1e-6:
            issues.append(f"{unit}: replacement lateral does not stop 18 in outside foundation")
        if d["lateral_6"][-1] != d["lateral_6_context"][0]:
            issues.append(f"{unit}: replacement lateral does not connect to existing lateral context")
        if abs(d["lateral_6_context"][-1][1] - SIDE_SEWER_Y) > 1e-6:
            issues.append(f"{unit}: existing lateral context does not reach side-sewer station")

        try:
            net = compute_unit_network_3d(d)
        except Exception as exc:
            issues.append(f"{unit}: network solve failed: {exc}")
            continue

        # Connected gravity-flow checks.
        if abs(net["main4"][-1][2] - net["lateral6"][0][2]) > 1e-6:
            issues.append(f"{unit}: 4in/6in transition Z is disconnected")
        if abs(net["lateral6"][-1][2] - net["context6"][0][2]) > 1e-6:
            issues.append(f"{unit}: replacement/existing 6in tie Z is disconnected")
        if abs(net["context6"][-1][2] - SIDE_SEWER_Z) > 1e-6:
            issues.append(f"{unit}: side-sewer context does not land at representative invert")

        route_groups = [net["main4"], net["lateral6"], net["context6"]]
        route_groups += list(net["branch3"].values()) + list(net["branch2"].values())
        route_groups += list(net.get("branch3_stubs", {}).values()) + list(net.get("branch2_stubs", {}).values())
        for route in route_groups:
            for a, b in zip(route, route[1:]):
                if b[2] > a[2] + 1e-7:
                    issues.append(f"{unit}: adverse slope found between {a} and {b}")
                    break

        # The documented investigations reported average 2.5–4.5 ft depths.
        # Flag only if our modeled under-slab controls leave that broad envelope.
        under_slab = net["main4"] + net["lateral6"]
        for route in (list(net["branch3"].values()) + list(net["branch2"].values()) +
                      list(net.get("branch3_stubs", {}).values()) + list(net.get("branch2_stubs", {}).values())):
            under_slab += route
        depths = [-p[2] for p in under_slab]
        if depths and (min(depths) < ft(2,4) or max(depths) > ft(4,6)):
            issues.append(
                f"{unit}: modeled under-slab depth range {min(depths):.2f}-{max(depths):.2f} ft "
                "falls outside the broad documented/assumed envelope"
            )

    return issues


def validate_model():
    issues=validate_route_controls_static()
    # Collections.
    required=[]
    for p,children in COLLECTION_TREE.items():
        required.append(p); required.extend(children)
    missing=[n for n in required if bpy.data.collections.get(n) is None]
    if missing: issues.append("Missing collections: "+", ".join(missing))

    # Stack count.
    stack_count=len([o for o in bpy.data.objects if o.name.startswith("CTX_") and "STACK" in o.name])
    if stack_count not in (0,12):
        issues.append(f"Expected 12 context stacks after Pass 1; found {stack_count}")

    # Boolean.
    slab=bpy.data.objects.get("BuildingB_SOG_5p5in")
    if slab and not slab.modifiers.get("MEYD_Trench_Difference"):
        issues.append("Slab exists but trench Boolean modifier is missing")

    # Phase controller / visibility-driver integrity.
    if 3 in RUN_PASSES and bpy.data.objects.get("PHASE_CONTROLLER") is None:
        issues.append("Pass 3 requested but PHASE_CONTROLLER is missing")
    driver_errors=[o.name for o in bpy.data.objects if o.get("MEYD_DRIVER_ERROR")]
    if driver_errors:
        issues.append("Visibility driver failures: " + ", ".join(driver_errors[:12]) +
                      (" ..." if len(driver_errors)>12 else ""))

    if 3 in RUN_PASSES:
        demo_ctrl=bpy.data.objects.get("PHASE_CONTROLLER")
        if demo_ctrl is not None and "Demolition_Subphase" not in demo_ctrl:
            issues.append("PHASE_CONTROLLER missing Demolition_Subphase")
        slab_chunks=[o for o in bpy.data.objects if o.name.startswith("B101_DEMO_SlabChunk_")]
        excav=[o for o in bpy.data.objects if o.name.startswith("B101_DEMO_Excavation_")]
        if not slab_chunks: issues.append("B101 detailed demolition has no slab removal chunks")
        if not excav: issues.append("B101 detailed demolition has no excavation volumes")
        if bpy.data.objects.get("B101_DEMO_PriorRepair_NoDemo_Envelope") is None:
            issues.append("B101 prior-repair no-demo protection envelope missing")
        if bpy.data.objects.get("B101_DEMO_WCCarrier_North_CarrierBody") is None:
            issues.append("B101 demolition fitting model missing north WC carrier")
        if bpy.data.objects.get("B101_DEMO_WCCarrier_South_CarrierBody") is None:
            issues.append("B101 demolition fitting model missing south WC carrier")
        if bpy.data.objects.get("B101_DEMO_Cut_PriorABS_Tie") is None:
            issues.append("B101 demolition fitting model missing prior-ABS tie cut marker")
        if bpy.data.objects.get("B101_DEMO_Cut_Exterior6in_18inLimit") is None:
            issues.append("B101 demolition fitting model missing exterior +18in cut marker")
        ptraps=[o for o in bpy.data.objects if o.name.startswith("B101_DEMO_ExistingPTrap_")]
        if len(ptraps) < 7:
            issues.append(f"B101 demolition fitting model expected 7 P-traps/conditional traps; found {len(ptraps)}")
        fitting_bodies=[o for o in bpy.data.objects if o.name.startswith("B101_DEMO_CI_Wye_") and o.name.endswith("_BODY")]
        if len(fitting_bodies) < 10:
            issues.append(f"B101 demolition fitting model expected >=10 junction fitting bodies; found {len(fitting_bodies)}")
        bend_objs=[o for o in bpy.data.objects if o.name.startswith("B101_DEMO_CI_Bend_")]
        if len(bend_objs) < 6:
            issues.append(f"B101 demolition fitting model expected >=6 plan bends; found {len(bend_objs)}")
        # No trench segment is intentionally generated from prior_abs_4; the only common point
        # should be the calibrated tie at main_4[0].
        d101=ROUTE_DATA["B101"]
        if d101.get("prior_abs_4") and d101["prior_abs_4"][-1] != d101["main_4"][0]:
            issues.append("B101 prior ABS does not terminate exactly at new-main tie")

    print("\n=== MEYDENBAUER VALIDATION ===")
    print(f"Grid: {BUILDING_LENGTH:.3f} ft N-S x {BUILDING_WIDTH:.3f} ft E-W")
    print(f"Pass-generated objects: {len([o for o in bpy.data.objects if o.get('MEYD_PROJECT')==PROJECT_TAG])}")
    print(f"Context stacks: {stack_count}")
    raw_area = sum(segment_length_2d(seg["p0"], seg["p1"]) * seg["width"] for seg in TRENCH_SEGMENTS)
    print(f"Trench raw plan area before overlap: {bpy.context.scene.get('MEYD_Est_TrenchPlanArea_sf_before_overlap', round(raw_area,1))} sf")
    if "MEYD_B101_Demo_RawSlabArea_sf_before_overlap" in bpy.context.scene:
        print(f"B101 demo raw slab area before overlap: {bpy.context.scene['MEYD_B101_Demo_RawSlabArea_sf_before_overlap']} sf")
        print(f"B101 demo raw finish access strip area before overlap: {bpy.context.scene['MEYD_B101_Demo_RawFinishStripArea_sf_before_overlap']} sf")
        print(f"B101 demo raw excavation volume before overlap: {bpy.context.scene['MEYD_B101_Demo_RawExcavation_cy_before_overlap']} CY")
    if "MEYD_B101_Demo_ExistingJunctionFittings_count" in bpy.context.scene:
        print(f"B101 demo junction fittings: {bpy.context.scene['MEYD_B101_Demo_ExistingJunctionFittings_count']}")
        print(f"B101 demo plan bends: {bpy.context.scene['MEYD_B101_Demo_ExistingBends_count']}")
        print(f"B101 demo P-traps/conditional traps: {bpy.context.scene['MEYD_B101_Demo_PTraps_count']}")
        print(f"B101 demo WC carriers: {bpy.context.scene['MEYD_B101_Demo_WCCarriers_count']}")
        print(f"B101 demo cut locations: {bpy.context.scene['MEYD_B101_Demo_CutLocations_count']}")
    print("Allowance benchmark (not a forced geometry target): 700 sf")
    print("Route source: P1.02/P3.1/P3.2 plan-traced controls; field verification required by drawings")
    if issues:
        print("VALIDATION WARNINGS:")
        for i in issues: print(" -",i)
    else:
        print("Validation checks passed.")
    return issues


def main():
    for p in RUN_PASSES:
        if p==1: run_pass1()
        elif p==2: run_pass2()
        elif p==3: run_pass3()
        else: print(f"Skipping unknown pass {p}")
    if VALIDATE_AFTER_RUN:
        validate_model()
    print("\nDone. Save the .blend under a new revision after review of route/invert control points.")


if __name__ == "__main__":
    main()
