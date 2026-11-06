"""Highland domestic-water risers and mains: takeoff -> existing and proposed specs (no bpy, no PDF).

Reads source-review/plan-marks.json (written by extract.py from the governing plumbing set) and the
picks below; writes risers-existing.spec.json and risers-proposed.spec.json. `--check` is the CI
step: regenerate both and let `git diff --exit-code` catch drift.

Coordinates: inches, x east of grid 7, y north of grid E, z above the P1 floor (342.00 ft).
Element status is the weakest of its plan position, elevation and size statuses.
"""
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).parent
MARKS = json.loads((HERE / "source-review" / "plan-marks.json").read_text())
RANK = {"confirmed": 2, "provisional": 1, "assumed": 0}

# --- documented datums ----------------------------------------------------------------------
LEVELS_FT = {"P2": 332.0, "P1": 342.0, "R1": 353.0, "R2": 363.25, "R3": 373.5, "R4": 383.75, "R5": 394.25}
DATUM_SRC = "A3.11 building sections 01/02, 04-02-07 (labeled floor elevations)"
Z0_FT = LEVELS_FT["P1"]
FLOORS = ["R1", "R2", "R3", "R4", "R5"]

# --- assumptions (no drawing gives domestic-water pipe elevations) --------------------------
CEILING_TAKEOFF_IN = 108   # branch groups at floor + 9 ft, i.e. above an assumed 8'-6" ceiling
MAIN_ELEV_FT = 350.5       # P1 garage main, hung below the R1 slab
TRIPLE_SPACING_IN = 4.0    # CW / HW / HWC centre-to-centre in a stack or header
BRANCH_STUB_IN = 24.0
ASSUMPTIONS = [
    {"id": "ceiling_takeoff_in", "basis": f"Floor + {CEILING_TAKEOFF_IN} in. P3.02 draws each branch group at the "
     "ceiling of the floor it serves; the Unit 107 study (highland/water) holds overhead CW at floor + 108 in. "
     "No document gives riser takeoff heights."},
    {"id": "main_elev_ft", "basis": f"{MAIN_ELEV_FT} ft. P1 garage main hung below the R1 slab; S3.8 gives the "
     "drop-slab soffit at 351.21 ft near Unit 107. The garage soffit along the main is not established."},
    {"id": "triple_spacing_in", "basis": f"{TRIPLE_SPACING_IN} in c/c. Riser symbols are not drawn to scale."},
    {"id": "branch_stub_in", "basis": f"{BRANCH_STUB_IN} in. Branches continue per the typical unit plans "
     "(P4.0x), which this model does not trace. Stub direction points away from Corridor 108."},
    {"id": "existing_material", "basis": "CPVC, per the owner's report of failing CPVC (highland/installation). "
     "P0.01 material notes were not used; installed material is not field verified."},
]

# --- traced picks ---------------------------------------------------------------------------
# Stack seeds: the riser box nearest each seed (within 40 in) on every listed level is averaged.
# Group mapping to P3.02's 01-05 is by floor count only (see flags).
STACKS = {
    "A": {"seed": (559, 804), "levels": ["R1", "R2", "R3"], "offset_at": "R4", "to_seed": (555, 747), "top": "R5"},
    "B": {"seed": (782, 761), "levels": ["R1", "R2", "R3", "R4", "R5"], "top": "R5"},
    "C": {"seed": (682, 358), "levels": ["R1", "R2", "R3"], "offset_at": "R4", "to_seed": (680, 475), "top": "R5"},
    "E": {"seed": (812, -113), "levels": ["R1", "R2", "R3"], "offset_at": "R4", "to_seed": (789, 193), "top": "R5"},
    "F": {"seed": (595, -230), "levels": ["R1", "R2", "R3", "R4"], "top": "R4", "profile": "03"},
    "D": {"seed": (679, 280), "levels": ["R1", "R2", "R3", "R4", "R5"], "top": "R5", "hose_bibb": True},
}
TRACE_TOL_IN = 12  # riser box centre vs riser symbol, plus raster picking
# Header and main routes traced from P2.03 / P2.02 linework (0.87 and 1.07 in per review pixel).
HEADER_X = 735
MAIN_RISER = (641, 819)
PLANT_TIE = (-32, 915)
MAIN_Y = 915
ROUTE_TOL_IN = 18
DROP_106_107 = (661, -113)

# Sizes (nominal in) by riser segment, ceiling to ceiling. P3.02 riser diagram is NTS: sizes only.
P302 = "P3.02 domestic water riser diagram, PDF page 13, 10-29-07"
PROFILES = {
    "typical": [  # 01/02/04/05: groups at R1..R5 ceilings
        ("R1", "R2", (2, 2, 0.75), "confirmed", P302 + ': "2"CW, HW & 3/4"HWC" at the header connection'),
        ("R2", "R3", (2, 2, 0.75), "provisional", P302 + ": unlabeled; continues the size below"),
        ("R3", "R4", (2, 1.5, 0.75), "confirmed", P302 + ': "2"CW, 1-1/2"HW & 3/4"HWC"'),
        ("R4", "R5", (1, 1, 0.5), "confirmed", P302 + ' "1"CW, HW & 1/2"HWC"; P2.06 R4 label at stack A'),
    ],
    "03": [  # one floor shorter: groups at R1..R4 ceilings
        ("R1", "R2", (2, 2, 0.75), "confirmed", P302 + ': "2"CW, HW & 3/4"HWC" ("03 stack)'),
        ("R2", "R3", (2, 1.5, 0.75), "confirmed", P302 + ': "2"CW, 1-1/2"HW & 3/4"HWC" ("03 stack)'),
        ("R3", "R4", (1, 1, 0.5), "confirmed", P302 + ': "1"CW, HW & 1/2"HWC" ("03 stack)'),
    ],
}
SYSTEMS = ("CW", "HW", "HWC")
HEADER_SIZE = ((3, 3, 1.25), "confirmed", P302 + ' "3"CW, HW & 1-1/4"HWC"; P2.03 Corridor 108 label (same)')
MAIN_SIZE = ((4, 3, 1.5), "confirmed", P302 + ' "4"CW, 3"HW & 1-1/2"HWC"; P2.02 and P2.03 riser labels (same)')
DROP_SIZE = ((1.5, 1.5, 0.75), "confirmed", 'P2.03 R1 riser label "1-1/2"CW, 1-1/2"HW & 3/4"HWC DN" (conflicts with P3.02)')

FLAGS = [
    {"topic": "Units 106/107 drop HW size", "modeled_per": "P2.03",
     "sources": ["P2.03 R1 plan: 1-1/2 in HW", "P3.02 riser diagram: 1-1/4 in HW"],
     "note": "Same issue (10-29-07). Modeled per the plan label at the riser; the engineer should confirm."},
    {"topic": "P3.02 stack numbers vs plan locations", "modeled_per": "P2.03-P2.07",
     "sources": ["P3.02 riser diagram (NTS)", "P2.03-P2.07 riser markups"],
     "note": "Plan stacks are named A-F by location. F is matched to P3.02 '03' because both stop one floor "
             "short of R5. A, B, C and E are not matched to 01, 02, 04 and 05."},
    {"topic": "04 stack R1 branch", "modeled_per": "P3.02",
     "sources": ["P3.02: 04 stack has four branch groups", "highland/water spec: R1 continuation unresolved"],
     "note": "This model gives A, B, C and E an R1 branch each (20 groups). P3.02 implies 19: one of the four "
             "has no R1 branch, and which one is unresolved."},
]


def z_ft(ft):
    return round((ft - Z0_FT) * 12, 2)


def ceil_z(level):
    return z_ft(LEVELS_FT[level]) + CEILING_TAKEOFF_IN


def sheet_for(level):
    return next((s, v) for s, v in MARKS["sheets"].items() if v["level"] == level)


def locate(seed, level):
    sheet, info = sheet_for(level)
    near = [b for b in info["riser_boxes"] if math.dist(b["center_in"], seed) <= 40]
    if not near:
        return None
    b = min(near, key=lambda b: math.dist(b["center_in"], seed))
    return {"sheet": sheet, "kind": b["kind"], "xy": b["center_in"], "size_in": b["size_in"]}


def stack_xy(seed, levels):
    hits = [h for lv in levels if (h := locate(seed, lv))]
    assert hits, seed
    x = sum(h["xy"][0] for h in hits) / len(hits); y = sum(h["xy"][1] for h in hits) / len(hits)
    spread = max(math.dist(h["xy"], (x, y)) for h in hits)
    return (round(x, 1), round(y, 1)), hits, round(spread, 1)


def worst(*s):
    return min(s, key=RANK.get)


class Spec:
    def __init__(self, scene):
        self.scene, self.elements = scene, []

    def add(self, **e):
        e.setdefault("scene", self.scene)
        st = [e[k] for k in ("xy_status", "z_status", "size_status") if k in e]
        e["status"] = worst(*st) if st else e["status"]
        # element-level provenance summarises the per-aspect fields
        src = [e[k] for k in ("xy_source", "z_source", "datum_source", "size_source") if e.get(k)]
        bas = [e[k] for k in ("xy_basis", "z_basis", "size_basis") if e.get(k)]
        if src and not e.get("source"):
            e["source"] = "; ".join(dict.fromkeys(src))
        if bas and not e.get("basis"):
            e["basis"] = "; ".join(dict.fromkeys(bas))
        if e["status"] != "confirmed":
            assert e.get("source") or e.get("basis"), e["id"]
        self.elements.append(e)
        return e


def lateral(direction, i, n=3, s=TRIPLE_SPACING_IN):
    """Kept for call sites; separation is applied once per system in OFF (see run())."""
    return (0, 0)


# Each system's whole network is translated by a constant vector, so parallel runs stay
# TRIPLE_SPACING_IN apart in either plan direction and every joint stays exact.
OFF = {s: ((i - 1) * TRIPLE_SPACING_IN, -(i - 1) * TRIPLE_SPACING_IN, 0.0) for i, s in enumerate(SYSTEMS)}


def build_existing():
    sp = Spec("existing")
    stacks = {}
    hdr_z = ceil_z("R1")
    main_z = z_ft(MAIN_ELEV_FT)
    zb = {"z_status": "assumed", "z_basis": "assumptions: ceiling_takeoff_in", "datum_source": DATUM_SRC}
    route = {"xy_status": "provisional", "xy_source": "P2.03 R1 plan linework, Corridor 108",
             "xy_tolerance_in": ROUTE_TOL_IN}

    def run(id_, system, pts, size, size_status, size_source, role, xy=None, z=None, terminal=False):
        o = OFF[system]
        return sp.add(id=id_, kind="pipe", system=system, role=role,
                      points=[[round(p[0] + o[0], 2), round(p[1] + o[1], 2), round(float(p[2]), 2)] for p in pts],
                      nominal_in=size, size_status=size_status, size_source=size_source,
                      material="CPVC", material_status="assumed", terminal=terminal, **(xy or route), **(z or zb))

    # P1 garage main: plant tie -> east -> riser to the R1 header.
    msz, mst, msrc = MAIN_SIZE
    mz = {"z_status": "assumed", "z_basis": "assumptions: main_elev_ft", "datum_source": DATUM_SRC}
    mxy = {"xy_status": "provisional", "xy_source": "P2.02 P1 plan linework (garage) and riser box at the main",
           "xy_tolerance_in": ROUTE_TOL_IN}
    for i, s in enumerate(SYSTEMS):
        dx, dy = lateral("x", i)
        a = (PLANT_TIE[0], MAIN_Y + dy, main_z); b = (MAIN_RISER[0] + dx, MAIN_Y + dy, main_z)
        c = (MAIN_RISER[0] + dx, MAIN_RISER[1], main_z)
        run(f"main-{s}", s, [a, b, c], msz[i], mst, msrc, "P1 garage main", xy=mxy, z=mz)
        run(f"main-riser-{s}", s, [c, (c[0], c[1], hdr_z)], msz[i], mst, msrc, "main riser P1 ceiling to R1 header",
            xy={"xy_status": "provisional", "xy_source": "P2.02/P2.03 riser boxes at the main (P1 UP, R1 DN)",
                "xy_tolerance_in": TRACE_TOL_IN}, z={**mz, "z_basis": "assumptions: main_elev_ft, ceiling_takeoff_in"})
    sp.add(id="main-note-heat-trace", kind="note", status="confirmed", source='P2.02 note: "HEAT TRACE & INSULATE CW '
           'PIPING IN GARAGE TYP."', text="Garage CW is heat traced and insulated", at=[300, MAIN_Y + 30, main_z])

    # Stacks
    for sid, st in STACKS.items():
        xy, hits, spread = stack_xy(st["seed"], st["levels"])
        stacks[sid] = {"xy": xy, "evidence": hits, "spread_in": spread}
        if st.get("offset_at"):
            oxy, ohits, ospread = stack_xy(st["to_seed"], [st["offset_at"], st["top"]])
            stacks[sid].update(offset_xy=oxy, offset_evidence=ohits, offset_spread_in=ospread)

    # R1 header in Corridor 108 ceiling, with tees at each stack and the 106/107 drop.
    hsz, hst, hsrc = HEADER_SIZE
    south = min(stacks["F"]["xy"][1], stacks["E"]["xy"][1]) - 40
    for i, s in enumerate(SYSTEMS):
        dx, _ = lateral("y", i)
        pts = [(MAIN_RISER[0] + dx, MAIN_RISER[1], hdr_z), (HEADER_X + dx, MAIN_RISER[1], hdr_z),
               (HEADER_X + dx, south, hdr_z), (stacks["F"]["xy"][0] + dx, south, hdr_z)]
        run(f"header-{s}", s, pts, hsz[i], hst, hsrc, "R1 Corridor 108 header")

    def branch_to(sid, target, via):
        """Header tee -> stack base for each system."""
        for i, s in enumerate(SYSTEMS if not STACKS[sid].get("hose_bibb") else ("CW",)):
            d = lateral("x", i) if via == "x" else lateral("y", i)
            pts = [(p[0] + d[0], p[1] + d[1], hdr_z) for p in target]
            yield s, pts, i

    tees = {
        "A": [(MAIN_RISER[0], MAIN_RISER[1]), (MAIN_RISER[0], 865), (stacks["A"]["xy"][0], 865), stacks["A"]["xy"]],
        "B": [(HEADER_X, stacks["B"]["xy"][1]), stacks["B"]["xy"]],
        "C": [(HEADER_X, stacks["C"]["xy"][1]), stacks["C"]["xy"]],
        "D": [(HEADER_X, stacks["D"]["xy"][1]), stacks["D"]["xy"]],
        "E": [(HEADER_X, stacks["E"]["xy"][1]), stacks["E"]["xy"]],
        "F": [(stacks["F"]["xy"][0], south), stacks["F"]["xy"]],
    }
    for sid, path in tees.items():
        st = STACKS[sid]
        prof = "hb" if st.get("hose_bibb") else st.get("profile", "typical")
        size0 = (1,) if prof == "hb" else PROFILES[prof][0][2]
        for s, pts, i in branch_to(sid, path, "x"):
            run(f"stack-{sid}-feed-{s}", s, pts, size0[i], "confirmed" if prof != "hb" else "confirmed",
                PROFILES["typical"][0][4] if prof != "hb" else 'P2.04 "1"CW UP & DN" at HB-3; P3.02 1"',
                f"header to stack {sid}")
        # base valves (symbols on P3.02 at every stack base; types per legend not reviewed)
        bx, by = stacks[sid]["xy"]
        for i, s in enumerate(SYSTEMS if prof != "hb" else ("CW",)):
            dx, dy = lateral("x", i)
            sp.add(id=f"stack-{sid}-valve-{s}", kind="valve", system=s,
                   at=[bx + OFF[s][0], by + OFF[s][1], hdr_z + 8],
                   nominal_in=size0[i], valve="balancing" if s == "HWC" else "isolation",
                   xy_status="assumed", xy_basis="placed at the stack base; P3.02 is NTS",
                   z_status="assumed", z_basis="header elevation", size_status="provisional",
                   size_source=P302 + ": valve symbols at each stack base", source=P302)

    # Risers, floor takeoffs, R4 offsets, slab penetrations
    groups = 0
    for sid, st in STACKS.items():
        x, y = stacks[sid]["xy"]
        hb = st.get("hose_bibb")
        xyp = {"xy_status": "provisional", "xy_tolerance_in": TRACE_TOL_IN,
               "xy_source": "riser boxes " + ", ".join(f"{h['sheet']} {h['kind']}" for h in stacks[sid]["evidence"])}
        top = st["top"]
        if hb:
            segs = [(FLOORS[k], FLOORS[k + 1], (1,), "confirmed", 'P2.04 "1"CW UP & DN"; P3.02 1" hose-bibb line')
                    for k in range(len(FLOORS) - 1)]
        else:
            segs = PROFILES[st.get("profile", "typical")]
        sys_ = ("CW",) if hb else SYSTEMS
        for lo, hi, size, sst, ssrc in segs:
            z0 = ceil_z(lo) if not hb else (ceil_z(lo) if lo == "R1" else z_ft(LEVELS_FT[lo]) + 24)
            z1 = ceil_z(hi) if not hb else z_ft(LEVELS_FT[hi]) + 24
            off = st.get("offset_at") == hi or (st.get("offset_at") and FLOORS.index(lo) >= FLOORS.index(st["offset_at"]))
            cx, cy = stacks[sid]["offset_xy"] if off and FLOORS.index(lo) >= FLOORS.index(st["offset_at"]) else (x, y)
            for i, s in enumerate(sys_):
                dx, dy = lateral("x", i, len(sys_))
                run(f"riser-{sid}-{lo}-{hi}-{s}", s, [(cx + dx, cy + dy, z0), (cx + dx, cy + dy, z1)], size[i], sst,
                    ssrc, f"stack {sid} riser {lo} to {hi} ceiling" if not hb else f"hose-bibb riser {lo} to {hi}",
                    xy=xyp if (cx, cy) == (x, y) else {**xyp, "xy_source": "riser boxes " + ", ".join(
                        f"{h['sheet']} {h['kind']}" for h in stacks[sid]["offset_evidence"])},
                    z={**zb, "z_basis": "floor datums (confirmed) + assumptions: ceiling_takeoff_in"})
            # slab penetration at the upper floor
            sp.add(id=f"pen-{sid}-{hi}", kind="penetration", at=[cx, cy, z_ft(LEVELS_FT[hi])],
                   radius_in=6 if not hb else 3, xy_status="provisional", xy_source=xyp["xy_source"],
                   xy_tolerance_in=TRACE_TOL_IN, z_status="confirmed", z_source=DATUM_SRC,
                   basis="Sleeve and firestop condition not documented here and not field verified")
        if st.get("offset_at"):
            lv = st["offset_at"]; ox, oy = stacks[sid]["offset_xy"]
            for i, s in enumerate(SYSTEMS):
                dx, dy = lateral("x", i)
                run(f"offset-{sid}-{lv}-{s}", s, [(x + dx, y + dy, ceil_z(lv)), (ox + dx, oy + dy, ceil_z(lv))],
                    PROFILES["typical"][-1][2][i], "confirmed", PROFILES["typical"][-1][4],
                    f"stack {sid} offset at {lv} ceiling", xy={"xy_status": "provisional", "xy_tolerance_in": TRACE_TOL_IN,
                    "xy_source": f"P2.06 DN box at {sid} and UP box at the continuation; route between them assumed straight"})
        # floor branch takeoffs (continue per P4.0x typical unit plans)
        serve = FLOORS[:FLOORS.index(top) + 1]
        for lv in serve if not hb else FLOORS[1:]:
            groups += 0 if hb else 1
            bx, by = stacks[sid]["offset_xy"] if st.get("offset_at") and FLOORS.index(lv) >= FLOORS.index(st["offset_at"]) else (x, y)
            sign = -1 if bx < HEADER_X else 1
            z = ceil_z(lv) if not hb else z_ft(LEVELS_FT[lv]) + 24
            for i, s in enumerate(sys_):
                dx, dy = lateral("x", i, len(sys_))
                p0 = (bx + dx, by + dy, z)
                run(f"branch-{sid}-{lv}-{s}", s, [(p0[0], p0[1], z), p0, (p0[0] + sign * BRANCH_STUB_IN, p0[1], p0[2])],
                    0.75, "assumed", None, f"{'hose bibb' if hb else 'unit'} branch {lv} (continues per P4.0x)",
                    xy={"xy_status": "assumed", "xy_basis": "assumptions: branch_stub_in"}, terminal=True
                    )["size_basis"] = ("P3.02: 3/4 in to HB-3" if hb else
                                       'P3.02 "SEE TYPICAL UNIT DOMESTIC WATER PLUMBING PLANS FOR SIZES"; 3/4 in for display')

    # Units 106/107 drop to P1 (internal routing: highland/water)
    dsz, dst, dsrc = DROP_SIZE
    for i, s in enumerate(SYSTEMS):
        dx, dy = lateral("x", i)
        pts = [(HEADER_X + dx, DROP_106_107[1] + dy, hdr_z), (DROP_106_107[0] + dx, DROP_106_107[1] + dy, hdr_z),
               (DROP_106_107[0] + dx, DROP_106_107[1] + dy, CEILING_TAKEOFF_IN)]
        run(f"drop-106-107-{s}", s, pts, dsz[i], dst, dsrc, "drop to Units 106/107 (continues in highland/water)",
            xy={"xy_status": "provisional", "xy_source": "P2.03 orange DN box at the 106/107 drop", "xy_tolerance_in": TRACE_TOL_IN},
            terminal=True)
    return sp, stacks, groups


def build_proposed(existing, stacks):
    """Parallel PEX-A install, then cutover one stack at a time. Every new element is assumed."""
    sp = Spec("proposed")
    new_basis = "Proposed means and methods for discussion; not engineered, not a contract document"
    ex = {e["id"]: e for e in existing.elements}
    # one translation for the whole new network keeps every joint and tee exact
    PROPOSED_SHIFT = (10, 10, 0)
    shift = {k: PROPOSED_SHIFT for k in ("main", "header", "drop", "stack")}
    order = ["F", "E", "C", "B", "A", "D"]  # owner sequence not set; south to north for illustration
    for e in existing.elements:
        if e["kind"] != "pipe":
            continue
        fam = e["id"].split("-")[0]
        d = shift["main"] if fam == "main" else shift["header"] if fam == "header" else shift["drop"] if fam == "drop" else shift["stack"]
        nominal = e["nominal_in"]
        pex = nominal <= 3
        sid = e["id"].split("-")[1] if fam in ("riser", "branch", "stack", "offset") else None
        sp.add(id="new-" + e["id"], kind="pipe", system=e["system"], role=e["role"],
               points=[[p[0] + d[0], p[1] + d[1], p[2] + d[2]] for p in e["points"]],
               nominal_in=nominal, size_status="assumed",
               size_basis="Same nominal size as existing, pending engineer resizing: PEX-A (ASTM F876, CTS SDR 9) has a "
                          "smaller bore than CPVC or copper of the same nominal size",
               material="PEX-A" if pex else "TBD (PEX-A is not made above 3 in nominal)", material_status="assumed",
               xy_status="assumed", xy_basis=f"Parallel to the existing route, offset {d[:2]} in; chase and ceiling space "
                                              "not verified", z_status="assumed", z_basis="as existing",
               basis=new_basis, terminal=e.get("terminal", False), stack=sid,
               phase=("main" if fam in ("main",) else "header" if fam in ("header", "drop") else f"stack-{sid}"))
    # supports, firestops, cutover ties, access openings
    for e in existing.elements:
        if e["kind"] == "penetration":
            sid = e["id"].split("-")[1]
            d = shift["stack"]
            sp.add(id="firestop-" + e["id"][4:], kind="firestop", at=[e["at"][0] + d[0], e["at"][1] + d[1], e["at"][2]],
                   radius_in=e["radius_in"], status="assumed", basis="New slab penetration; requires a listed firestop "
                   "system for PEX-A in the rated floor assembly (system not selected)", stack=sid, phase=f"stack-{sid}")
            sp.add(id="clamp-" + e["id"][4:], kind="clamp", at=[e["at"][0] + d[0], e["at"][1] + d[1], e["at"][2] + 2],
                   status="assumed", basis="Riser clamp at each floor; PEX-A risers also need anchors and expansion "
                   "allowance (not designed)", stack=sid, phase=f"stack-{sid}")
        if e["kind"] == "pipe" and e["id"].startswith(("branch-", "drop-")):
            p = e["points"][-1]
            sid = e["id"].split("-")[1]
            sp.add(id="tie-" + e["id"], kind="tie", system=e["system"], at=[p[0] - 6 * (1 if p[0] > HEADER_X else -1), p[1], p[2]],
                   status="assumed", basis="Cutover tie: new branch joined to the existing branch downstream of the old "
                   "riser during a scheduled shutdown of that stack", stack=sid,
                   phase="header" if sid == "106" else f"stack-{sid}")
            if not e["id"].startswith("drop-"):
                sp.add(id="valve-" + e["id"], kind="valve", system=e["system"], at=[p[0] - 12 * (1 if p[0] > HEADER_X else -1), p[1], p[2]],
                       valve="isolation", status="assumed", basis="New floor-branch isolation valve (proposed improvement; "
                       "access panel location not set)", stack=sid, phase=f"stack-{sid}")
    for sid, info in stacks.items():
        st = STACKS[sid]; d = shift["stack"]
        serve = FLOORS[:FLOORS.index(st["top"]) + 1]
        for lv in serve:
            off = st.get("offset_at") and FLOORS.index(lv) >= FLOORS.index(st["offset_at"])
            x, y = info["offset_xy"] if off else info["xy"]
            z0 = z_ft(LEVELS_FT[lv])
            if lv == "R1":  # the riser starts at the R1 ceiling header: tie access is from below
                zc = ceil_z(lv) - 6
                sp.add(id=f"opening-{sid}-{lv}", kind="opening", surface="ceiling access panel",
                       points=[[x + d[0], y + d[1] - 12, zc], [x + d[0], y + d[1] + 12, zc]], width_in=24,
                       status="assumed", basis="24 x 24 in ceiling opening at the stack base for the riser and R1 "
                       "branch ties; ceiling at an assumed 8 ft 6 in", stack=sid, phase=f"stack-{sid}")
                continue
            sp.add(id=f"opening-{sid}-{lv}", kind="opening", surface="chase wall", at=[x + d[0], y + d[1] + 14, z0],
                   width_in=24, height_in=96, status="assumed",
                   basis="Drywall opening at the chase face, floor to ceiling, one per floor; face, size and finish "
                         "not established (needs a walk-through per unit)", stack=sid, phase=f"stack-{sid}")
    header = ex["header-HW"]["points"]
    for k, (a, b) in enumerate(zip(header, header[1:])):
        sp.add(id=f"opening-corridor-{k}", kind="opening", surface="corridor ceiling",
               points=[[a[0] + 5, a[1], a[2] - 6], [b[0] + 5, b[1], b[2] - 6]], width_in=24, status="assumed",
               basis="Continuous 24 in ceiling strip over both headers in Corridor 108, at an assumed 8 ft 6 in ceiling "
                     "(alternative: access panels at "
                     "joints); ceiling type not established", phase="header")
    sequence = [
        {"phase": "protect", "what": "Floor protection, dust walls and egress signage at each work area"},
        {"phase": "main", "what": "New garage main alongside the live main; heat trace and insulate CW (P2.02 note)"},
        {"phase": "header", "what": "Open Corridor 108 ceiling; new header alongside the live header; test"},
        *({"phase": f"stack-{s}", "what": f"Stack {s}: open chase per floor, install new riser, firestop, test, "
           "shut down stack, cut over floor branches, cap and abandon or remove the old riser"} for s in order),
        {"phase": "restore", "what": "Patch, tape and paint openings; reinstate ceilings; remove protection"},
    ]
    return sp, sequence


def basis_of_record():
    return {"documents": "RL-REVISED Highland Condos Plumbing 10-29-07 (P2.01-P2.07, P3.02); A2.03 and A3.11 "
                         "(04-02-07); S3.8 (04-02-07)",
            "kind": "design_intent", "field_verified": "not_verified",
            "note": "Drawing-traced domestic-water risers and mains. Not a survey of installed piping."}


def networks(elements):
    """Connected components per system: a pipe joins another where one of its points lies on the
    other's polyline (tees) or they share a point. Checks the modeled graph, not hydraulics."""
    out = {}
    for sysname in SYSTEMS:
        pipes = [e for e in elements if e["kind"] == "pipe" and e["system"] == sysname]
        parent = list(range(len(pipes)))

        def find(i):
            while parent[i] != i:
                parent[i] = parent[parent[i]]; i = parent[i]
            return i

        def on(p, poly):
            for a, b in zip(poly, poly[1:]):
                ab = [b[k] - a[k] for k in range(3)]; L = sum(c * c for c in ab)
                t = 0 if L == 0 else max(0, min(1, sum((p[k] - a[k]) * ab[k] for k in range(3)) / L))
                if math.dist(p, [a[k] + t * ab[k] for k in range(3)]) < 0.05:
                    return True
            return False

        for i, e in enumerate(pipes):
            for j, f in enumerate(pipes):
                if i < j and (on(e["points"][0], f["points"]) or on(e["points"][-1], f["points"])
                              or on(f["points"][0], e["points"]) or on(f["points"][-1], e["points"])):
                    parent[find(i)] = find(j)
        out[sysname] = len({find(i) for i in range(len(pipes))})
    return out


def checks(existing, stacks, groups):
    es = existing.elements
    risers = {e["id"].split("-")[1] for e in es if e["id"].startswith("riser-")}
    r5 = {e["id"].split("-")[1] for e in es if e["id"].startswith("riser-") and "-R5-" in e["id"] and e["system"] == "HW"}
    out = [
        {"check": "triple stacks", "expected": 5, "actual": len([s for s in risers if not STACKS[s].get("hose_bibb")]),
         "source": "P3.02 five stack groups (01-05); P2.04/P2.05 green riser boxes"},
        {"check": "hose-bibb risers", "expected": 1, "actual": len([s for s in risers if STACKS[s].get("hose_bibb")]),
         "source": 'P2.04 "1"CW UP & DN" at HB-3; P3.02 1" line to HB-3 at R2-R5'},
        {"check": "triple stacks reaching R5", "expected": 4, "actual": len(r5 - {"D"}),
         "source": "P2.07 R5 green riser boxes (four triple stacks plus hose bibb)"},
        {"check": "R4 offsets", "expected": 3, "actual": len({e["id"].split("-")[1] for e in es if e["id"].startswith("offset-")}),
         "source": "P2.06 orange DN boxes at A, C and E with UP boxes at the continuations"},
        {"check": "header size HW (in)", "expected": 3, "actual": next(e["nominal_in"] for e in es if e["id"] == "header-HW"),
         "source": P302},
        {"check": "main size CW (in)", "expected": 4, "actual": next(e["nominal_in"] for e in es if e["id"] == "main-CW"),
         "source": P302},
        {"check": "branch groups (modeled)", "expected": 24, "actual": groups,
         "source": "P3.02 groups 5+5+4+4+5=23, plus the unresolved 04 R1 branch (flag)"},
        {"check": "max grid registration residual (in)", "expected": "<= 1",
         "actual": max(v["grid_residual_in"] for v in MARKS["sheets"].values()), "source": "A2.03 grid strings"},
        {"check": "max stack trace spread (in)", "expected": f"<= {TRACE_TOL_IN}",
         "actual": max(max(v["spread_in"], v.get("offset_spread_in", 0)) for v in stacks.values()),
         "source": "riser boxes on P2.03-P2.07"},
    ]
    for sysname, n in networks(es).items():
        out.append({"check": f"{sysname} network components", "expected": 1, "actual": n,
                    "source": "every modeled run reaches the plant tie through tees (graph check only)"})
    for c in out:
        e, a = c["expected"], c["actual"]
        c["pass"] = (a <= float(e.split()[-1])) if isinstance(e, str) else a == e
    return out


def write(name, spec):
    path = HERE / name
    path.write_text(json.dumps(spec, indent=1) + "\n")
    return path


def main():
    existing, stacks, groups = build_existing()
    proposed, sequence = build_proposed(existing, stacks)
    res = checks(existing, stacks, groups)
    common = {"units": "inches", "frame": "x east of grid 7, y north of grid E, z above P1 floor (342.00 ft)",
              "levels_ft": LEVELS_FT, "levels_source": DATUM_SRC, "registration": {
                  s: {k: v[k] for k in ("page", "level", "pt_per_in", "grid_residual_in")} for s, v in MARKS["sheets"].items()},
              "basis_of_record": basis_of_record(), "conflicts": FLAGS, "assumptions": ASSUMPTIONS}
    ex = {"project": "Highland | domestic-water risers and mains (existing, drawing-traced)", **common,
          "stacks": {k: {"xy": v["xy"], **({"offset_xy": v["offset_xy"]} if "offset_xy" in v else {}),
                         "spread_in": v["spread_in"], "evidence": v["evidence"]} for k, v in stacks.items()},
          "checks": res, "elements": existing.elements}
    pr = {"project": "Highland | PEX-A riser and main replacement (proposed, illustrative)", **common,
          "basis_of_record": {**basis_of_record(), "note": "Proposed parallel install and stack-by-stack cutover. "
                              "Every new element is assumed; nothing here is engineered."},
          "strategy": "Parallel install alongside the live system, then one stack at a time cutover",
          "sequence": sequence,
          "checks": [{"check": f"{k} network components (new)", "expected": 1, "actual": n, "pass": n == 1,
                      "source": "graph check of the proposed PEX-A network"} for k, n in networks(proposed.elements).items()],
          "elements": proposed.elements}
    write("risers-existing.spec.json", ex); write("risers-proposed.spec.json", pr)
    failed = [c for c in res if not c["pass"]]
    count = lambda es: {k: sum(e["status"] == k for e in es) for k in RANK}  # noqa: E731
    print("existing", len(existing.elements), count(existing.elements), "| proposed", len(proposed.elements),
          count(proposed.elements))
    for c in res:
        print(("PASS" if c["pass"] else "FAIL"), c["check"], c["expected"], c["actual"])
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
