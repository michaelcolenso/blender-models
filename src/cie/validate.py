"""Referential and provenance validation for canonical project state."""

from __future__ import annotations

from collections import Counter

from .model import ProjectState, Status


class ValidationError(ValueError):
    pass


def _unique(label: str, ids: list[str]) -> list[str]:
    duplicates = sorted(k for k, n in Counter(ids).items() if n > 1)
    return [f"duplicate {label} id: {item}" for item in duplicates]


def validate_project_state(state: ProjectState) -> list[str]:
    """Return all validation errors; empty means the state is internally coherent."""
    errors: list[str] = []
    groups = {
        "evidence": state.evidence,
        "claim": state.claims,
        "element": state.elements,
        "relationship": state.relationships,
        "quantity": state.quantities,
        "activity": state.activities,
        "issue": state.issues,
        "scenario": state.scenarios,
    }
    for label, records in groups.items():
        errors.extend(_unique(label, [r.id for r in records]))

    evidence_ids = {x.id for x in state.evidence}
    claim_ids = {x.id for x in state.claims}
    element_ids = {x.id for x in state.elements}
    activity_ids = {x.id for x in state.activities}
    scenario_ids = {x.id for x in state.scenarios}
    subject_ids = evidence_ids | element_ids | activity_ids | scenario_ids

    for claim in state.claims:
        if claim.subject_id not in subject_ids:
            errors.append(f"claim {claim.id} has missing subject {claim.subject_id}")
        for ref in claim.evidence_ids:
            if ref not in evidence_ids:
                errors.append(f"claim {claim.id} has missing evidence {ref}")
        if claim.status == Status.CONFIRMED and not claim.evidence_ids:
            errors.append(f"confirmed claim {claim.id} has no evidence")

    for element in state.elements:
        if element.parent_id and element.parent_id not in element_ids:
            errors.append(f"element {element.id} has missing parent {element.parent_id}")
        for ref in element.source_ids:
            if ref not in evidence_ids:
                errors.append(f"element {element.id} has missing source {ref}")

    for rel in state.relationships:
        if rel.from_id not in element_ids:
            errors.append(f"relationship {rel.id} has missing from element {rel.from_id}")
        if rel.to_id not in element_ids:
            errors.append(f"relationship {rel.id} has missing to element {rel.to_id}")

    for qty in state.quantities:
        if qty.element_id not in element_ids:
            errors.append(f"quantity {qty.id} has missing element {qty.element_id}")
        if qty.scenario_id and qty.scenario_id not in scenario_ids:
            errors.append(f"quantity {qty.id} has missing scenario {qty.scenario_id}")
        for ref in qty.source_claim_ids:
            if ref not in claim_ids:
                errors.append(f"quantity {qty.id} has missing source claim {ref}")

    for activity in state.activities:
        for ref in activity.element_ids:
            if ref not in element_ids:
                errors.append(f"activity {activity.id} has missing element {ref}")
        for ref in activity.predecessor_ids:
            if ref not in activity_ids:
                errors.append(f"activity {activity.id} has missing predecessor {ref}")

    for issue in state.issues:
        for ref in issue.element_ids:
            if ref not in element_ids:
                errors.append(f"issue {issue.id} has missing element {ref}")
        for ref in issue.claim_ids:
            if ref not in claim_ids:
                errors.append(f"issue {issue.id} has missing claim {ref}")

    return errors


def assert_valid_project_state(state: ProjectState) -> None:
    errors = validate_project_state(state)
    if errors:
        raise ValidationError("invalid project state:\n- " + "\n- ".join(errors))
