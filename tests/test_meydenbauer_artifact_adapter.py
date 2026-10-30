import importlib.util
from pathlib import Path


def _load_builder():
    path = Path(__file__).parents[1] / "projects/meydenbauer-b/state/build_from_artifacts.py"
    spec = importlib.util.spec_from_file_location("meydenbauer_artifact_state", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.build


def test_artifact_adapter_preserves_reference_quantities_and_sequence():
    state = _load_builder()()

    pipes = [element for element in state.elements if element.kind == "pipe"]
    assert len(pipes) == 136
    assert len({pipe.id for pipe in pipes}) == 136

    pipe_total = next(q for q in state.quantities if q.measure == "new_abs_length")
    assert abs(pipe_total.value - 312.75) < 0.02

    b104 = next(element for element in state.elements if element.kind == "unit" and element.name == "B-104")
    b104_activities = [activity for activity in state.activities if b104.id in activity.element_ids]
    assert len(b104_activities) == 8
    assert sum(activity.duration_working_days or 0 for activity in b104_activities) == 23.0

    b104_route = next(
        element
        for element in state.elements
        if element.kind == "logistics_route" and element.properties.get("entry") == "J-K" and element.parent_id == b104.id
    )
    haul = next(q for q in state.quantities if q.element_id == b104_route.id and q.measure == "one_way_haul_distance")
    assert haul.value == 229.0


def test_pipe_ids_are_geometry_bridge_ready():
    state = _load_builder()()
    pipes = [element for element in state.elements if element.kind == "pipe"]
    assert all(pipe.geometry_ref == f"cie:{pipe.id}" for pipe in pipes)
    assert all(pipe.properties["node_a"] and pipe.properties["node_b"] for pipe in pipes)
