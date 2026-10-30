import importlib.util
from pathlib import Path

import pytest


def _load_builder():
    path = Path(__file__).parents[1] / "projects/meydenbauer-b/state/build_project_state.py"
    spec = importlib.util.spec_from_file_location("meydenbauer_state", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.build


def test_reference_state_carries_decision_signal():
    state = _load_builder()()
    values = {(q.measure, q.scenario_id): q.value for q in state.quantities if ":system:" in q.element_id}
    scenarios = {s.name: s.id for s in state.scenarios}
    assert values[("new_abs_length", None)] == pytest.approx(312.75, abs=0.02)
    assert values[("slab_cut", scenarios["S2"])] == pytest.approx(686.1152567048161)
    assert values[("slab_cut", scenarios["S3"])] == pytest.approx(990.957844619837)
    assert any(i.severity == "critical" and "POC" in i.title for i in state.issues)
