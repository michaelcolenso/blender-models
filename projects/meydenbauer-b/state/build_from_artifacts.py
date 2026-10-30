"""Adapt the existing Meydenbauer underslab artifacts into canonical CIE state.

This is intentionally an adapter, not a rewrite of takeoff/schedule/logistics.
The production artifacts remain authoritative for their calculations; this module
adds stable identity, provenance, relationships and a common state envelope.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any

from cie.ids import semantic_id
from cie.model import (
    Activity,
    Claim,
    Confidence,
    Element,
    Evidence,
    Issue,
    ProjectState,
    Quantity,
    Relationship,
    Scenario,
    Status,
)
from cie.scenario import aggregate_unit_case, allowance_delta
from cie.validate import assert_valid_project_state

PROJECT = "meydenbauer-b"
ROOT = Path(__file__).parents[1]
PRODUCT = ROOT / "products" / "underslab"
DELIVERABLE = ROOT / "deliverables" / "underslab"
OUT = Path(__file__).with_name("project-state.json")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def build() -> ProjectState:
    spec = _load(PRODUCT / "meydenbauer-b.spec.json")
    takeoff = _load(DELIVERABLE / "takeoff.json")
    module_spec = importlib.util.spec_from_file_location("meydenbauer_schedule", PRODUCT / "schedule.py")
    assert module_spec and module_spec.loader
    schedule_module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(schedule_module)
    schedule = schedule_module.build(takeoff)
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

    geometry_bindings = {}
    previous: str | None = None
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

        trench_id = semantic_id(PROJECT, "trench", unit_name)
        elements.append(
            Element(
                id=trench_id,
                kind="trench",
                name=f"{unit_name} S2 trench overlay",
                project_id=PROJECT,
                parent_id=unit_id,
                source_ids=(p102, trench_detail),
                status=Status.ASSUMED,
                properties={
                    "unit": unit_name,
                    "basis": "S2 schematic envelope; working pits and 3.5 ft POC invert assumed, not verified excavation.",
                },
            )
        )
        geometry_bindings[f"{unit_name}-trench-0"] = {"element_id": trench_id, "role": "trench"}
        geometry_bindings[f"{unit_name}-outside-0"] = {"element_id": trench_id, "role": "trench"}
        unit_spec = spec_units[unit_name]
        for index, edge in enumerate(unit_spec["edges"], start=1):
            pipe_count += 1
            a, b = edge["a"], edge["b"]
            pipe_id = semantic_id(PROJECT, "pipe", unit_name, a, b)
            geometry_bindings[f"{unit_name}-R{index - 1:03d}"] = {"element_id": pipe_id, "role": "pipe"}
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

    # Keep the schedule's S2 @ 3.5 ft baseline. The S3 decision case includes
    # the deeper 4.5 ft invert; S1 uses 3.5 ft so width/pit effects remain comparable.
    cases = {"S1": "S1@3.5", "S2": "S2@3.5", "S3": "S3@4.5"}
    measures = {"slab_cut_sf": ("slab_cut", "SF"), "excavation_bank_cy": ("excavation_bank", "CY")}
    scenarios: list[Scenario] = []
    decisions = {}
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
                    "poc_invert_ft": float(cases[name].split("@")[1]),
                    "takeoff_case": cases[name],
                },
            )
        )

    for scenario in scenarios:
        case_key = cases[scenario.name]
        totals = aggregate_unit_case(takeoff["units"], case_key, tuple(measures))
        for target, values in [(system_id, totals)] + [
            (semantic_id(PROJECT, "unit", u["unit"]), u["cases"][case_key]) for u in takeoff["units"]
        ]:
            for raw, (measure, unit) in measures.items():
                quantities.append(
                    Quantity(
                        id=semantic_id(PROJECT, "quantity", scenario.name, target.split(":")[-1], measure),
                        element_id=target,
                        measure=measure,
                        value=float(values[raw]),
                        unit=unit,
                        scenario_id=scenario.id,
                        source_claim_ids=(route_claim.id, trench_claim.id, depth_claim.id),
                    )
                )
        decision = allowance_delta(totals["slab_cut_sf"], allowance_claim.value)
        decisions[scenario.id] = {
            **decision,
            "excavation_bank_cy": totals["excavation_bank_cy"],
            "takeoff_case": case_key,
            "schedule_status": "baseline_strawman" if scenario.name == "S2" else "not_calculated",
            "working_days": schedule["working_days"] if scenario.name == "S2" else None,
            "schedule_basis": schedule["status"]
            if scenario.name == "S2"
            else "Not calculated: timeline remains S2 baseline; no S1/S3 duration or delta asserted.",
            "claim_ids": [allowance_claim.id, trench_claim.id, depth_claim.id],
            "quantity_ids": [q.id for q in quantities if q.element_id == system_id and q.scenario_id == scenario.id],
        }

    # Presentation states describe the existing schematic GLB. They do not simulate
    # removal, testing acceptance, or continuous pipe installation quantities.
    labels = [
        "investigation",
        "protected",
        "excavated",
        "installing",
        "testing",
        "backfilled",
        "finishing",
        "reinstating",
    ]
    colors = ["#aeb5bf", "#d4ba76", "#d98b61", "#55c6df", "#b898f4", "#b49b74", "#8ec3a7", "#b4db7b"]
    opacity = [0.12, 0.18, 0.3, 1.0, 1.0, 0.45, 0.6, 0.85]
    timeline_units = []
    for u in schedule["units"]:
        unit_id = semantic_id(PROJECT, "unit", u["unit"])
        phases = []
        for i, name in enumerate(schedule["phases"]):
            start = u["phase_start_day"][i]
            phases.append(
                {
                    "activity_id": semantic_id(PROJECT, "activity", u["unit"], f"{i + 1:02d}"),
                    "name": name,
                    "start_day": start,
                    "end_day": start + u["days"][i],
                    "duration_days": u["days"][i],
                    "construction_state": labels[i],
                    "styles": {
                        "pipe": {"color": colors[i], "opacity": opacity[i]},
                        "trench": {"color": colors[i], "opacity": [0.05, 0.1, 0.75, 0.6, 0.5, 0.22, 0.1, 0.05][i]},
                    },
                }
            )
        timeline_units.append(
            {
                "unit": u["unit"],
                "element_id": unit_id,
                "start_day": u["start_day"],
                "end_day": phases[-1]["end_day"],
                "phases": phases,
            }
        )
    timeline = {
        "baseline_scenario_id": semantic_id(PROJECT, "scenario", "S2"),
        "status": schedule["status"],
        "working_days": schedule["working_days"],
        "calendar_days_approx": schedule["calendar_days_approx"],
        "order": schedule["order"],
        "constraints": schedule["constraints"],
        "rates": schedule["rates"],
        "units": timeline_units,
        "future_style": {"color": "#79818a", "opacity": 0.08},
        "complete_styles": {
            "pipe": {"color": "#a9c489", "opacity": 0.85},
            "trench": {"color": "#a9c489", "opacity": 0.05},
        },
        "visual_basis": "Schematic phase overlay on S2 geometry; colors/opacity show sequence, not verified installed quantities or test acceptance.",
    }
    issues = [
        Issue(
            id=semantic_id(PROJECT, "issue", "poc-depth"),
            title="POC inverts undocumented",
            description="Depth controls trench protection, slab disturbance, excavation and logistics.",
            severity="critical",
            element_ids=(system_id,),
            claim_ids=(depth_claim.id,),
        ),
        Issue(
            id=semantic_id(PROJECT, "issue", "groundwater"),
            title="Groundwater basis unresolved",
            description="SOR notes a high water table; dewatering scope and schedule effects remain unresolved.",
            severity="high",
            element_ids=(system_id,),
            claim_ids=(depth_claim.id,),
        ),
    ]

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
        issues=issues,
        scenarios=scenarios,
        metadata={
            "timeline": timeline,
            "decisions": decisions,
            "geometry_bindings": geometry_bindings,
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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    state = build()
    content = json.dumps(state.to_dict(), indent=2) + "\n"
    if args.check:
        if OUT.read_text() != content:
            raise SystemExit("canonical state drift; regenerate with build_from_artifacts.py")
        print("ok canonical artifact state")
        return
    OUT.write_text(content)
    print(f"wrote {OUT} ({state.metadata['pipe_element_count']} pipe elements)")


if __name__ == "__main__":
    main()
