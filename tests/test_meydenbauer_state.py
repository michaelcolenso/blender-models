from projects.meydenbauer_b.state.build_project_state import build


def test_reference_state_carries_decision_signal():
    state = build()
    values = {(q.measure, q.scenario_id): q.value for q in state.quantities}
    scenarios = {s.name: s.id for s in state.scenarios}

    assert values[("new_abs_length", None)] == 312.75
    assert values[("slab_cut", scenarios["S2"])] == 686.0
    assert values[("slab_cut", scenarios["S3"])] == 991.0
    assert any(i.severity == "critical" and "POC" in i.title for i in state.issues)
