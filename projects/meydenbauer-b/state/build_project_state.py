"""Build the first canonical CIE state for the Meydenbauer under-slab scope.

This is intentionally an adapter around verified project outputs. It does not replace
takeoff.py/schedule.py/animate.py yet. Wrap -> prove -> extract -> generalize.
"""

from __future__ import annotations

import json
from pathlib import Path

from src.cie.ids import semantic_id
from src.cie.model import Claim, Confidence, Element, Evidence, Issue, ProjectState, Quantity, Scenario, Status
from src.cie.validate import assert_valid_project_state

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).with_name("project-state.json")
PROJECT = "meydenbauer-b"


def build() -> ProjectState:
    p102 = Evidence(
        id=semantic_id(PROJECT, "evidence", "p1-02"),
        kind="drawing",
        source="Exhibit A / P1.02",
        locator="under-slab waste plan",
        description="New waste routes and sizes; routes diagrammatic and stacks field verified.",
    )
    detail = Evidence(
        id=semantic_id(PROJECT, "evidence", "p5-1-detail-10"),
        kind="drawing_detail",
        source="P5.1",
        locator="Detail 10",
        description='Typical 2\'-0" trench width.',
    )
    sor = Evidence(
        id=semantic_id(PROJECT, "evidence", "sor"),
        kind="scope",
        source="Statement of Requirements",
        locator="Initial Investigation / General Notes",
        description="Recorded depth range includes 2.5–4.5 ft; high water table noted.",
    )
    allowance = Evidence(
        id=semantic_id(PROJECT, "evidence", "allowance-7"),
        kind="bid_form",
        source="Bid Form / Addendum 1",
        locator="Allowance No. 7",
        description="700 SF slab allowance.",
    )

    system = Element(
        id=semantic_id(PROJECT, "system", "underslab-waste"),
        kind="system",
        name="Building B under-slab waste re-pipe",
        project_id=PROJECT,
        source_ids=(p102.id,),
        status=Status.PROVISIONAL,
        geometry_ref="deliverables/underslab/Meydenbauer-B-underslab.glb",
    )

    route_claim = Claim(
        id=semantic_id(PROJECT, "claim", "underslab-route-source"),
        subject_id=system.id,
        predicate="route_basis",
        value="scaled/extracted from P1.02",
        evidence_ids=(p102.id,),
        status=Status.PROVISIONAL,
        confidence=Confidence.MEDIUM,
        rationale="Drawing routes were extracted and visually reviewed; field conditions remain unverified.",
    )
    depth_claim = Claim(
        id=semantic_id(PROJECT, "claim", "poc-invert-depth"),
        subject_id=system.id,
        predicate="poc_invert_depth_ft",
        value=None,
        evidence_ids=(p102.id, sor.id),
        status=Status.UNKNOWN,
        confidence=Confidence.NONE,
        rationale='P1.02 says "MATCH EX. I.E."; no POC invert elevations are documented.',
    )
    trench_claim = Claim(
        id=semantic_id(PROJECT, "claim", "typical-trench-width"),
        subject_id=system.id,
        predicate="typical_trench_width_ft",
        value=2.0,
        evidence_ids=(detail.id,),
        status=Status.CONFIRMED,
        confidence=Confidence.HIGH,
    )
    allowance_claim = Claim(
        id=semantic_id(PROJECT, "claim", "slab-allowance"),
        subject_id=system.id,
        predicate="slab_allowance_sf",
        value=700,
        evidence_ids=(allowance.id,),
        status=Status.CONFIRMED,
        confidence=Confidence.HIGH,
    )

    scenarios = [
        Scenario(id=semantic_id(PROJECT, "scenario", "s1"), name="S1", description="2 ft trench only", inputs={"trench_width_ft": 2.0}),
        Scenario(id=semantic_id(PROJECT, "scenario", "s2"), name="S2", description="S1 plus 3x3 pits at 30 fixture/stack connections", inputs={"trench_width_ft": 2.0, "connection_pit_ft": [3, 3], "poc_invert_ft": 3.5}),
        Scenario(id=semantic_id(PROJECT, "scenario", "s3"), name="S3", description="4 ft cut wherever trench reaches 4 ft deep", inputs={"deep_cut_width_ft": 4.0, "poc_invert_ft": 4.5}),
    ]

    slab_values = {"s1": 590.0, "s2": 686.0, "s3": 991.0}
    excavation_values = {"s1": 72.0, "s2": 82.3, "s3": 158.0}
    quantities: list[Quantity] = [
        Quantity(id=semantic_id(PROJECT, "quantity", "pipe-length"), element_id=system.id, measure="new_abs_length", value=312.75, unit="LF", source_claim_ids=(route_claim.id,)),
    ]
    for scenario in scenarios:
        key = scenario.name.lower()
        quantities.extend([
            Quantity(id=semantic_id(PROJECT, "quantity", key, "slab-cut"), element_id=system.id, measure="slab_cut", value=slab_values[key], unit="SF", scenario_id=scenario.id, source_claim_ids=(trench_claim.id, depth_claim.id)),
            Quantity(id=semantic_id(PROJECT, "quantity", key, "excavation"), element_id=system.id, measure="excavation_bank", value=excavation_values[key], unit="CY", scenario_id=scenario.id, source_claim_ids=(depth_claim.id,)),
        ])

    issues = [
        Issue(id=semantic_id(PROJECT, "issue", "poc-depth"), title="POC inverts undocumented", description="Depth controls trench protection, slab disturbance, excavation and logistics.", severity="critical", element_ids=(system.id,), claim_ids=(depth_claim.id,)),
        Issue(id=semantic_id(PROJECT, "issue", "groundwater"), title="Groundwater basis unresolved", description="SOR notes a high water table; bid documents do not establish a dewatering allowance or unit price.", severity="high", element_ids=(system.id,)),
    ]

    state = ProjectState(
        schema_version="0.1.0",
        project_id=PROJECT,
        name="101 Meydenbauer, Building B",
        evidence=[p102, detail, sor, allowance],
        claims=[route_claim, depth_claim, trench_claim, allowance_claim],
        elements=[system],
        quantities=quantities,
        issues=issues,
        scenarios=scenarios,
        metadata={
            "scope": "under-slab waste re-pipe",
            "reference": "projects/meydenbauer-b/deliverables/underslab/README.md",
            "adapter_status": "bootstrap",
        },
    )
    assert_valid_project_state(state)
    return state


def main() -> None:
    state = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(state.to_dict(), indent=2) + "\n")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
