import json
from pathlib import Path

from cie.scenario import aggregate_unit_case, allowance_delta


def _takeoff():
    path = Path(__file__).parents[1] / "projects/meydenbauer-b/deliverables/underslab/takeoff.json"
    return json.loads(path.read_text())


def test_scenario_aggregation_uses_real_takeoff_cases():
    takeoff = _takeoff()
    measures = ("slab_cut_sf", "excavation_bank_cy", "spoil_loose_cy")

    s2 = aggregate_unit_case(takeoff["units"], "S2@3.5", measures)
    s3 = aggregate_unit_case(takeoff["units"], "S3@4.5", measures)

    assert round(s2["slab_cut_sf"]) == 686
    assert round(s3["slab_cut_sf"]) == 991
    assert s3["excavation_bank_cy"] > s2["excavation_bank_cy"]


def test_allowance_comparison_makes_crossing_explicit():
    takeoff = _takeoff()
    allowance = float(takeoff["inputs"]["allowance_7_sf"])
    s2 = aggregate_unit_case(takeoff["units"], "S2@3.5", ("slab_cut_sf",))
    s3 = aggregate_unit_case(takeoff["units"], "S3@4.5", ("slab_cut_sf",))

    base = allowance_delta(s2["slab_cut_sf"], allowance)
    deep = allowance_delta(s3["slab_cut_sf"], allowance)

    assert base["within_allowance"] is True
    assert 0 < base["delta"] < 20
    assert deep["within_allowance"] is False
    assert deep["delta"] < -250
