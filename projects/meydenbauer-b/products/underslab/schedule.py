"""Strawman unit-by-unit schedule for the Building B re-pipe, from the takeoff quantities.

Every rate below is an ASSUMPTION for the bid team to replace with its own crew plan; the
quantities come from takeoff.json (S2 trench, 3.5 ft tie-in invert). One unit at a time: a
unit finishes all eight phases before the next starts (user direction, 2026-10-26).

Documented constraints the sequence respects (shown in the film, not scheduled here):
  SOR general note 21  water and sewer restored to each unit by 5:00 PM daily (one sink, one toilet)
  SOR general note 13  48 h notice of shut-offs, weekdays only
  00 22 13 1.9         schedule broken out per fixture, with dates each bathroom is available
  00 22 13 1.9 B       work 8:00 AM to 5:00 PM, Monday to Friday

Writes meydenbauer-b.schedule.json. No Blender here; animate.py and anim_finish.py read it.

Usage: python projects/meydenbauer-b/products/underslab/schedule.py
"""
import json, math
from pathlib import Path

HERE = Path(__file__).resolve().parent
from bmodels.paths import ROOT  # noqa: E402  (repo root)

PHASES = ["01 Existing + investigation", "02 Staging + fixture removal", "03 Demolition + excavation",
          "04 New ABS installation", "05 Water test", "06 Backfill + slab pourback",
          "07 Patching + finishes", "08 Fixture reinstatement"]
ORDER = ["B-103", "B-102", "B-101", "B-104"]
ORDER_BASIS = ("B-103 first as the pilot (smallest network, 64.8 LF); B-104 last (largest, and its "
               "kitchen-stack run waits on RFI 4)")
RATES = {   # all assumed; edit and re-run
    "investigation_days": 1.0,        # camera scope, locate and mark, pothole at the tie-in
    "staging_days": 1.0,              # protection, dust walls, fixture removal
    "sawcut_sf_per_day": 150.0,       # saw-cut, break out and remove slab
    "excavation_cy_per_day": 8.0,     # hand excavation, hauled out through the unit in carts
    "abs_lf_per_day": 40.0,
    "days_per_connection": 0.15,      # fixture and stack tie-ins
    "water_test_days": 1.0,           # fill, hold, City of Bellevue inspection
    "backfill_cy_per_day": 12.0,
    "pour_days": 1.0,                 # vapor barrier, 5" pour-back, finish
    "cure_days": 3.0,                 # before floor finishes; verify the flooring maker's moisture limits
    "finish_sf_per_day": 80.0,        # tile and hardwood patch; patch area = 1.3 x slab cut
    "reset_days": 1.0,                # fixtures, punch, owner sign-off walk
    "slab_in": 4.0, "pourback_in": 5.0, "swell": 1.25,
}


def half(x):
    return max(0.5, math.ceil(x * 2 - 1e-9) / 2)


def unit_plan(u, R=RATES):
    c = u["cases"]["S2@3.5"]
    sf, cy, lf, n = c["slab_cut_sf"], c["excavation_bank_cy"], u["pipe_lf"], u["connections"]
    days = [
        half(R["investigation_days"]),
        half(R["staging_days"]),
        half(sf / R["sawcut_sf_per_day"] + cy / R["excavation_cy_per_day"]),
        half(lf / R["abs_lf_per_day"] + n * R["days_per_connection"]),
        half(R["water_test_days"]),
        half(cy / R["backfill_cy_per_day"] + R["pour_days"]),
        half(R["cure_days"] + 1.3 * sf / R["finish_sf_per_day"]),
        half(R["reset_days"]),
    ]
    out_cy = cy * R["swell"] + sf * R["slab_in"] / 12 / 27
    in_cy = cy + sf * R["pourback_in"] / 12 / 27          # bedding and backfill imported (assumed)
    return {"unit": u["unit"], "days": days, "cure_days": R["cure_days"],
            "quantities": {"slab_cut_sf": round(sf), "excavation_bank_cy": round(cy, 1), "pipe_lf": round(lf, 1),
                           "connections": n, "haul_out_cy": round(out_cy, 1), "haul_in_cy": round(in_cy, 1),
                           "concrete_cy": round(sf * R["pourback_in"] / 12 / 27, 1)}}


def build(takeoff=None):
    # Adapters can use the committed takeoff without a prior Blender/build pass.
    take = takeoff if takeoff is not None else json.loads((ROOT / "build/meydenbauer-b/takeoff.json").read_text())
    by = {u["unit"]: u for u in take["units"]}
    units, day = [], 0.0
    for name in ORDER:
        p = unit_plan(by[name])
        p["start_day"] = day
        p["phase_start_day"] = [day + sum(p["days"][:i]) for i in range(len(PHASES))]
        day += sum(p["days"])
        units.append(p)
    total = day
    return {"phases": PHASES, "order": ORDER, "order_basis": ORDER_BASIS, "rates": RATES,
            "status": "STRAWMAN: rates and order assumed; quantities from takeoff S2 @ 3.5 ft",
            "units": units, "working_days": total,
            "calendar_days_approx": math.ceil(total / 5 * 7),
            "constraints": ["SOR note 21: one sink and one toilet in service at 5:00 PM daily",
                            "SOR note 13: 48 h shut-off notice, weekdays only",
                            "00 22 13 1.9: work 8:00 AM-5:00 PM Mon-Fri; schedule by fixture and bathroom"]}


def windows(plan, unit_s=96.0, intro_s=2.5, outro_s=3.0, min_phase_s=1.5):
    """Screen time: proportional to working days, with a floor so 1-day phases stay legible
    (phases under the floor all get exactly the floor). Defaults: 101.5 s for 81.5 working days,
    1.1 s per day above the floor. Returns (dict unit -> [(t0, t1)] * 8 in seconds, total seconds)."""
    days = [d for u in plan["units"] for d in u["days"]]
    floored = [False] * len(days)
    while True:
        k = (unit_s - min_phase_s * sum(floored)) / sum(d for d, f in zip(days, floored) if not f)
        nxt = [f or d * k < min_phase_s for d, f in zip(days, floored)]
        if nxt == floored:
            break
        floored = nxt
    dur = iter(min_phase_s if f else d * k for d, f in zip(days, floored))
    W, t = {}, intro_s
    for u in plan["units"]:
        W[u["unit"]] = []
        for _ in u["days"]:
            d = next(dur)
            W[u["unit"]].append((t, t + d)); t += d
    return W, t + outro_s


def day_at(plan, W, t):
    """Working day reached at film time t (linear within each phase window); also the active
    (unit, phase index), or (None, None) in the intro and outro."""
    for u in plan["units"]:
        for i, (t0, t1) in enumerate(W[u["unit"]]):
            if t0 <= t < t1:
                return u["phase_start_day"][i] + (t - t0) / (t1 - t0) * u["days"][i], u["unit"], i
    first = plan["units"][0]["unit"]
    return (0.0 if t < W[first][0][0] else plan["working_days"]), None, None


def time_at_day(plan, W, unit, day):
    """Film time at which the unit's schedule reaches the given working day (inverse of day_at)."""
    u = next(u for u in plan["units"] if u["unit"] == unit)
    for i, (t0, t1) in enumerate(W[unit]):
        s0 = u["phase_start_day"][i]
        if s0 <= day <= s0 + u["days"][i]:
            return t0 + (day - s0) / u["days"][i] * (t1 - t0)
    raise ValueError(f"day {day} is outside {unit}")


if __name__ == "__main__":
    import sys
    plan = build()
    if len(sys.argv) == 3 and sys.argv[1] == "--frames":      # film length in frames at an fps (for shell scripts)
        print(round(windows(plan)[1] * int(sys.argv[2])))
        sys.exit()
    (HERE / "meydenbauer-b.schedule.json").write_text(json.dumps(plan, indent=1))
    for u in plan["units"]:
        q = u["quantities"]
        print(f'{u["unit"]}: days {u["days"]} = {sum(u["days"])}  out {q["haul_out_cy"]} CY  in {q["haul_in_cy"]} CY')
    print(f'total {plan["working_days"]} working days, about {plan["calendar_days_approx"]} calendar days (no holidays)')
    W, total_s = windows(plan)
    print(f"film {total_s:.1f} s; shortest phase {min(b - a for w in W.values() for a, b in w):.2f} s")
