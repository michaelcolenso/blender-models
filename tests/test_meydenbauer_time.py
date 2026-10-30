"""Deterministic CPU-only checks of the actual state adapter and browser reducer."""

import importlib.util
import json
import struct
import subprocess
from pathlib import Path

import pytest

from cie.validate import assert_valid_project_state

ROOT = Path(__file__).parents[1]
SITE = ROOT / "projects/meydenbauer-b"
EXPLORER = SITE / "products/explorer"


def load(path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_canonical_snapshot_and_schedule_projection_are_deterministic():
    state = load(SITE / "state/build_from_artifacts.py").build()
    assert_valid_project_state(state)
    data = state.to_dict()
    assert data == json.loads((SITE / "state/project-state.json").read_text())
    assert load(EXPLORER / "time_model.py").build_projection(data) == json.loads(
        (EXPLORER / "time-state.json").read_text()
    )
    takeoff = json.loads((SITE / "deliverables/underslab/takeoff.json").read_text())
    schedule = load(SITE / "products/underslab/schedule.py").build(takeoff)
    assert schedule == json.loads((SITE / "products/underslab/meydenbauer-b.schedule.json").read_text())
    timeline = data["metadata"]["timeline"]
    assert timeline["working_days"] == 81.5
    assert timeline["order"] == ["B-103", "B-102", "B-101", "B-104"]
    previous = None
    for unit in timeline["units"]:
        assert len(unit["phases"]) == 8
        for phase in unit["phases"]:
            activity = next(a for a in data["activities"] if a["id"] == phase["activity_id"])
            assert activity["predecessor_ids"] == ([previous] if previous else [])
            assert activity["duration_working_days"] == phase["end_day"] - phase["start_day"]
            previous = activity["id"]


def test_every_scenario_quantity_and_decision_comes_from_takeoff():
    state = load(SITE / "state/build_from_artifacts.py").build().to_dict()
    takeoff = json.loads((SITE / "deliverables/underslab/takeoff.json").read_text())
    decisions = state["metadata"]["decisions"]
    for scenario in state["scenarios"]:
        case = scenario["inputs"]["takeoff_case"]
        for raw, measure in [("slab_cut_sf", "slab_cut"), ("excavation_bank_cy", "excavation_bank")]:
            per_unit = [
                q
                for q in state["quantities"]
                if q["scenario_id"] == scenario["id"] and q["measure"] == measure and ":unit:" in q["element_id"]
            ]
            assert len(per_unit) == 4
            assert sum(q["value"] for q in per_unit) == pytest.approx(takeoff["totals"][case][raw])
            total = next(
                q
                for q in state["quantities"]
                if q["scenario_id"] == scenario["id"] and q["measure"] == measure and ":system:" in q["element_id"]
            )
            assert total["value"] == pytest.approx(takeoff["totals"][case][raw])
            assert total["source_claim_ids"]
        d = decisions[scenario["id"]]
        assert d["delta"] == pytest.approx(d["allowance"] - d["value"])
        if scenario["name"] != "S2":
            assert d["working_days"] is None
            assert d["schedule_status"] == "not_calculated"
    assert decisions["meydenbauer-b:scenario:s2"]["within_allowance"]
    assert not decisions["meydenbauer-b:scenario:s3"]["within_allowance"]


def test_glb_name_bindings_cover_all_canonical_pipes_without_blender():
    state = load(SITE / "state/build_from_artifacts.py").build().to_dict()
    glb = (SITE / "deliverables/underslab/Meydenbauer-B-underslab.glb").read_bytes()
    length = struct.unpack_from("<I", glb, 12)[0]
    nodes = json.loads(glb[20 : 20 + length])["nodes"]
    names = {n["name"] for n in nodes}
    bindings = state["metadata"]["geometry_bindings"]
    pipes = [e for e in state["elements"] if e["kind"] == "pipe"]
    assert len(pipes) == 136
    assert {b["element_id"] for b in bindings.values() if b["role"] == "pipe"} == {e["id"] for e in pipes}
    assert set(bindings) <= names


def test_browser_boundary_and_scenario_contracts():
    subprocess.run(["node", "--test", str(EXPLORER / "view-state.test.mjs")], check=True, cwd=ROOT)


def test_takeoff_change_propagates_without_inventing_s3_schedule(monkeypatch):
    adapter = load(SITE / "state/build_from_artifacts.py")
    baseline = adapter.build().to_dict()
    original_load = adapter._load

    def changed_load(path):
        data = original_load(path)
        if path.name == "takeoff.json":
            # Actual upstream case change, not a changed display constant.
            data["units"][0]["cases"]["S3@4.5"]["slab_cut_sf"] += 10
            data["units"][0]["cases"]["S3@4.5"]["excavation_bank_cy"] += 2
        return data

    monkeypatch.setattr(adapter, "_load", changed_load)
    changed = adapter.build().to_dict()
    sid = "meydenbauer-b:scenario:s3"
    before, after = baseline["metadata"]["decisions"][sid], changed["metadata"]["decisions"][sid]
    assert after["value"] == pytest.approx(before["value"] + 10)
    assert after["excavation_bank_cy"] == pytest.approx(before["excavation_bank_cy"] + 2)
    assert after["delta"] == pytest.approx(before["delta"] - 10)
    assert after["working_days"] is None
    assert changed["metadata"]["timeline"] == baseline["metadata"]["timeline"]
