"""Adapt the existing Meydenbauer underslab artifacts into canonical CIE state.

This is intentionally an adapter, not a rewrite of takeoff/schedule/logistics.
The production artifacts remain authoritative for their calculations; this module
adds stable identity, provenance, relationships and a common state envelope.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from cie.ids import semantic_id
from cie.model import Activity, Claim, Confidence, Element, Evidence, ProjectState, Quantity, Relationship, Scenario, Status
from cie.validate import assert_valid_project_state

PROJECT = "meydenbauer-b"
ROOT = Path(__file__).parents[1]
PRODUCT = ROOT / "products" / "underslab"
DELIVERABLE = ROOT / "deliverables" / "underslab"
OUT = Path(__file__).with_name("project-state.generated.json")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def build() -> ProjectState:
    spec = _load(PRODUCT / "meydenbauer-b.spec.json")
    takeoff = _load(DELIVERABLE / "takeoff.json")
    schedule = _load(PRODUCT / "meydenbauer-b.schedule.json")
    logistics = _load(PRODUCT / "meydenbauer-b.logistics.json")

    evidence: list[Evidence] = []
    evidence_by_source: dict[str, str] = {}
    for source in spec["sources"]:
        source_key = source["id"]
        eid = semantic_id(PROJECT, "evidence", source_key)
        evidence.append(
            Evidence(
                id=eid,
                kind="source_document",
                source=source.get("doc", source_key),
                locator=source_key,
                description=source.get("note") or source.get("rev"),
                checksum=source.get("sha256"),
            )
        )
        evidence_by_source[source_key] = eid

    p102 = evidence_by_source["P1.02"]
    sor = evidence_by_source["SOR"]
    trench_detail = evidence_by_source["10/P5.1"]
    allowance_evidence = evidence_by_source["BF-A1"]

    system_id = semantic_id(PROJECT, "system", "underslab-waste")
    elements: list[Element] = [
        Element(
            id=system_id,
            kind="system",
            name="Building B under-slab waste re-pipe",
            project_id=PROJECT,
            source_ids=(p102,),
            status=Status.PROVISIONAL,
            geometry_ref="deliverables/underslab/Meydenbauer-B-underslab.glb",
        )
    ]
    relationships: list[Relationship] = []
    quantities: list[Quantity] = []
    activities: list[Activity] = []
    claims: list[Claim] = []

    route_claim = Claim(
        id=semantic_id(PROJECT, "claim", "route-basis"),
        subject_id=system_id,
        predicate="route_basis",
        value="vector extraction from P1.02",
        evidence_ids=(p102,),
        status=Status.PROVISIONAL,
        confidence=Confidence.MEDIUM,
        rationale="Plan position is calibrated to the drawing grid; field stack locations remain to be verified.",
    )
    depth_claim = Claim(
        id=semantic_id(PROJECT, "claim", "poc-invert-depth"),
        subject_id=system_id,
        predicate="poc_invert_depth_ft",
        value=None,
        evidence_ids=(p102, sor),
        status=Status.UNKNOWN,
        confidence=Confidence.NONE,
        rationale="P1.02 says MATCH EX. I.E.; no POC invert elevations are documented.",
    )
    trench_claim = Claim(
        id=semantic_id(PROJECT, "claim", "typical-trench-width"),
        subject_id=system_id,
        predicate="typical_trench_width_ft",
        value=2.0,
        evidence_ids=(trench_detail,),
        status=Status.CONFIRMED,
        confidence=Confidence.HIGH,
    )
    allowance_claim = Claim(
        id=semantic_id(PROJECT, "claim", "slab-allowance"),
        subject_id=system_id,
        predicate="slab_allowance_sf",
        value=float(takeoff["inputs"]["allowance_7_sf"]),
        evidence_ids=(allowance_evidence,),
        status=Status.CONFIRMED,
        confidence=Confidence.HIGH,
    )
    claims.extend([route_claim, depth_claim, trench_claim, allowance_claim])

    spec_units = {unit["unit"]: unit for unit in spec["units"]}
    takeoff_units = {unit["unit"]: unit for unit in takeoff["units"]}
    schedule_units = {unit["unit"]: unit for unit in schedule["units"]}

    pipe_count = 0
    for unit_name in schedule["order"]:
        unit_id = semantic_id(PROJECT, "unit", unit_name)
        elements.append(
            Element(
                id=unit_id,
                kind="unit",
                name=unit_name,
                project_id=PROJECT,
                parent_id=system_id,
                source_ids=(p102,),
                status=Status.PROVISIONAL,
            )
        )
        relationships.append(
            Relationship(
                id=semantic_id(PROJECT, "relationship", "contains", unit_name),
                kind="contains",
                from_id=system_id,
                to_id=unit_id,
            )
        )

        unit_spec = spec_units[unit_name]
        for index, edge in enumerate(unit_spec["edges"], start=1):
            pipe_count += 1
            a, b = edge["a"], edge["b"]
            pipe_id = semantic_id(PROJECT, "pipe", unit_name, a, b)
            elements.append(
                Element(
                    id=pipe_id,
                    kind="pipe",
                    name=f"{unit_name} {edge['nominal_in']}in ABS {index:03d}",
                    project_id=PROJECT,
                    parent_id=unit_id,
                    source_ids=(p102,),
                    status=Status.PROVISIONAL,
                    properties={
                        "unit": unit_name,
                        "node_a": a,
                        "node_b": b,
                        "nominal_in": edge["nominal_in"],
                        "fixtures_served": edge.get("fixtures_served", 0),
                        "semantic_index": index,
                    },
                    geometry_ref=f"cie:{pipe_id}",
                )
            )
            relationships.append(
                Relationship(
                    id=semantic_id(PROJECT, "relationship", "contains", unit_name, "pipe", str(index)),
                    kind="contains",
                    from_id=unit_id,
                    to_id=pipe_id,
                )
            )
            quantities.append(
                Quantity(
                    id=semantic_id(PROJECT, "quantity", unit_name, "pipe", str(index), "length"),
                    element_id=pipe_id,
                    measure="pipe_length",
                    value=float(edge["length_ft"]),
                    unit="LF",
                    source_claim_ids=(route_claim.id,),
                )
            )

        tq = takeoff_units[unit_name]
        quantities.extend(
            [
                Quantity(
                    id=semantic_id(PROJECT, "quantity", unit_name, "pipe-total"),
                    element_id=unit_id,
                    measure="pipe_length",
                    value=float(tq["pipe_lf"]),
                    unit="LF",
                    source_claim_ids=(route_claim.id,),
                ),
                Quantity(
                    id=semantic_id(PROJECT, "quantity", unit_name, "connections"),
                    element_id=unit_id,
                    measure="connections",
                    value=float(tq["connections"]),
                    unit="EA",
                    source_claim_ids=(route_claim.id,),
                ),
            ]
        )

        sq = schedule_units[unit_name]
        previous: str | None = None
        for phase_index, (phase, duration) in enumerate(zip(schedule["phases"], sq["days"], strict=True), start=1):
            activity_id = semantic_id(PROJECT, "activity", unit_name, f"{phase_index:02d}")
            activities.append(
                Activity(
                    id=activity_id,
                    name=f"{unit_name} — {phase}",
                    phase=phase,
                    element_ids=(unit_id,),
                    duration_working_days=float(duration),
                    predecessor_ids=(previous,) if previous else (),
                    assumptions=(schedule["status"],),
                )
            )
            previous = activity_id

        route = logistics["routes"][unit_name]
        route_id = semantic_id(PROJECT, "logistics-route", unit_name, "haul-out")
        elements.append(
            Element(
                id=route_id,
                kind="logistics_route",
                name=f"{unit_name} haul-out via {route['entry']}",
                project_id=PROJECT,
                parent_id=unit_id,
                status=Status.ASSUMED,
                properties={
                    "entry": route["entry"],
                    "points_ft": route["out_ft"],
                    "basis": logistics["status"],
                },
            )
        )
        relationships.append(
            Relationship(
                id=semantic_id(PROJECT, "relationship", "uses-route", unit_name),
                kind="uses_logistics_route",
                from_id=unit_id,
                to_id=route_id,
            )
        )
        quantities.append(
            Quantity(
                id=semantic_id(PROJECT, "quantity", unit_name, "haul-distance"),
                element_id=route_id,
                measure="one_way_haul_distance",
                value=float(route["out_length_ft"]),
                unit="FT",
            )
        )

    scenarios: list[Scenario] = []
    for name, description, width, pit, deep_width in takeoff["inputs"]["scenarios"]:
        scenarios.append(
            Scenario(
                id=semantic_id(PROJECT, "scenario", name),
                name=name,
                description=description,
                inputs={
                    "trench_width_ft": width,
                    "connection_pit_ft": pit,
                    "deep_cut_width_ft": deep_width,
                },
            )
        )

    quantities.append(
        Quantity(
            id=semantic_id(PROJECT, "quantity", "pipe-total"),
            element_id=system_id,
            measure="new_abs_length",
            value=sum(float(unit["pipe_lf"]) for unit in takeoff["units"]),
            unit="LF",
            source_claim_ids=(route_claim.id,),
        )
    )

    state = ProjectState(
        schema_version="0.1.0",
        project_id=PROJECT,
        name="101 Meydenbauer, Building B",
        evidence=evidence,
        claims=claims,
        elements=elements,
        relationships=relationships,
        quantities=quantities,
        activities=activities,
        scenarios=scenarios,
        metadata={
            "scope": "under-slab waste re-pipe",
            "adapter_status": "live-artifact-adapter",
            "pipe_element_count": pipe_count,
            "working_days": schedule["working_days"],
            "calendar_days_approx": schedule["calendar_days_approx"],
            "schedule_status": schedule["status"],
            "logistics_status": logistics["status"],
        },
    )
    assert_valid_project_state(state)
    return state


def main() -> None:
    state = build()
    OUT.write_text(json.dumps(state.to_dict(), indent=2) + "\n")
    print(f"wrote {OUT} ({state.metadata['pipe_element_count']} pipe elements)")


if __name__ == "__main__":
    main()
