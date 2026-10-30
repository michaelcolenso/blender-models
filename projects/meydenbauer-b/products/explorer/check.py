"""CPU-only contract/drift checks; never rewrites tracked outputs."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

from bmodels.paths import ROOT

HERE = Path(__file__).resolve().parent
STATE = ROOT / "projects/meydenbauer-b/state"


def main():
    for script in [STATE / "build_from_artifacts.py", HERE / "time_model.py"]:
        subprocess.run([sys.executable, str(script), "--check"], check=True)
    state = json.loads((STATE / "project-state.json").read_text())
    timeline = state["metadata"]["timeline"]
    assert timeline["working_days"] == 81.5
    assert timeline["order"] == ["B-103", "B-102", "B-101", "B-104"]
    assert len(state["activities"]) == 32
    schedule_spec = importlib.util.spec_from_file_location("schedule", HERE.parent / "underslab/schedule.py")
    assert schedule_spec and schedule_spec.loader
    schedule = importlib.util.module_from_spec(schedule_spec)
    schedule_spec.loader.exec_module(schedule)
    takeoff = json.loads((ROOT / "projects/meydenbauer-b/deliverables/underslab/takeoff.json").read_text())
    assert schedule.build(takeoff) == json.loads((HERE.parent / "underslab/meydenbauer-b.schedule.json").read_text())
    app = (HERE / "app.js").read_text()
    assert "metadata.timeline" in app and "decisionAt(state, scenario)" in app
    for forbidden in ["686.0", "991.0", "700 SF", "excavation_cy_per_day", "projected_working_days"]:
        assert forbidden not in app, f"browser duplicates construction state: {forbidden}"
    subprocess.run(["node", "--input-type=module", "--check"], input=app, text=True, check=True)
    subprocess.run(["node", "--test", str(HERE / "view-state.test.mjs")], check=True)
    print(
        "EXPLORER CHECK PASS — canonical state, S2 schedule, scenario decisions, semantic bindings and time projection"
    )


if __name__ == "__main__":
    main()
