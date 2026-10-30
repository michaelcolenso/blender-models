from __future__ import annotations

"""Generate the Explorer's time + decision projection from authoritative product outputs.

No construction rates live here. schedule.py owns the strawman rates/order; takeoff/state own
scenario quantities. This module only projects those sources into browser-friendly JSON.
"""
import importlib.util
import json
from pathlib import Path

from bmodels.paths import ROOT

HERE = Path(__file__).resolve().parent
STATE = ROOT / "projects/meydenbauer-b/state/project-state.json"
SCHEDULE_PY = ROOT / "projects/meydenbauer-b/products/underslab/schedule.py"
OUT = HERE / "time-state.json"


def _load_schedule_module():
    spec = importlib.util.spec_from_file_location("meydenbauer_schedule", SCHEDULE_PY)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)
    return mod


def build_projection() -> dict:
    state = json.loads(STATE.read_text())
    schedule = _load_schedule_module().build()
    allowance = next(c["value"] for c in state["claims"] if c["predicate"] == "slab_allowance")
    quantities = {(q.get("scenario_id"), q["measure"]): q["value"] for q in state["quantities"]}

    scenarios = {}
    baseline_exc = quantities[("meydenbauer-b:scenario:s2", "excavation_bank")]
    baseline_days = schedule["working_days"]
    # Duration sensitivity is an explicit projection, not a replacement schedule: only the excavation
    # delta is propagated through the schedule's published excavation production rate.
    excavation_rate = schedule["rates"]["excavation_cy_per_day"]
    for scenario in state["scenarios"]:
        sid = scenario["id"]
        slab = quantities.get((sid, "slab_cut"))
        excavation = quantities.get((sid, "excavation_bank"))
        delta_days = 0.0 if excavation is None else (excavation - baseline_exc) / excavation_rate
        scenarios[sid] = {
            "name": scenario["name"],
            "slab_cut_sf": slab,
            "excavation_bank_cy": excavation,
            "allowance_sf": allowance,
            "allowance_delta_sf": None if slab is None else slab - allowance,
            "projected_working_days": round(baseline_days + delta_days, 2),
            "schedule_basis": "S2 strawman + excavation delta / published excavation rate",
        }

    units = []
    for u in schedule["units"]:
        phases = []
        for i, name in enumerate(schedule["phases"]):
            start = u["phase_start_day"][i]
            duration = u["days"][i]
            phases.append({"name": name, "start_day": start, "end_day": start + duration, "duration_days": duration})
        units.append({"unit": u["unit"], "start_day": u["start_day"], "end_day": u["start_day"] + sum(u["days"]), "phases": phases})

    return {
        "status": schedule["status"],
        "working_days": schedule["working_days"],
        "calendar_days_approx": schedule["calendar_days_approx"],
        "order": schedule["order"],
        "units": units,
        "scenarios": scenarios,
    }


if __name__ == "__main__":
    OUT.write_text(json.dumps(build_projection(), indent=2) + "\n")
    print(f"wrote {OUT.relative_to(ROOT)}")
