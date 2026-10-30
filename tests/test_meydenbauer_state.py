import importlib.util
import json
from pathlib import Path


def _load_builder():
    path = Path(__file__).parents[1] / "projects/meydenbauer-b/state/build_project_state.py"
    spec = importlib.util.spec_from_file_location("meydenbauer_state", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.build


def test_reference_state_carries_decision_signal():
    state = _load_builder()()
    values = {(q.measure, q.scenario_id): q.value for q in state.quantities}
    scenarios = {s.name: s.id for s in state.scenarios}
    assert values[("new_abs_length", None)] == 312.75
    assert values[("slab_cut", scenarios["S2"])] == 686.0
    assert values[("slab_cut", scenarios["S3"])] == 991.0
    assert any(i.severity == "critical" and "POC" in i.title for i in state.issues)


def test_committed_snapshot_matches_builder():
    root = Path(__file__).parents[1]
    expected = json.loads((root / "projects/meydenbauer-b/state/project-state.json").read_text())
    assert _load_builder()().to_dict() == expected
