"""Small, deterministic scenario evaluation helpers.

The kernel does not own project-specific engineering formulas. It can, however,
normalize already-computed scenario cases from project adapters so downstream
surfaces do not need to understand each project's takeoff JSON shape.
"""
from __future__ import annotations

from typing import Any


def aggregate_unit_case(
    units: list[dict[str, Any]],
    case_key: str,
    measures: tuple[str, ...],
) -> dict[str, float]:
    """Sum named measures across unit-level case dictionaries.

    Raises rather than silently treating missing case data as zero. In construction
    intelligence, missing is not zero.
    """
    totals = {measure: 0.0 for measure in measures}
    for unit in units:
        unit_name = unit.get("unit", "<unknown>")
        cases = unit.get("cases")
        if not isinstance(cases, dict) or case_key not in cases:
            raise KeyError(f"{unit_name}: missing scenario case {case_key}")
        case = cases[case_key]
        for measure in measures:
            if measure not in case:
                raise KeyError(f"{unit_name}: {case_key} missing measure {measure}")
            totals[measure] += float(case[measure])
    return totals


def allowance_delta(value: float, allowance: float) -> dict[str, float | bool]:
    """Return a decision-oriented allowance comparison."""
    delta = allowance - value
    return {
        "value": float(value),
        "allowance": float(allowance),
        "delta": delta,
        "within_allowance": delta >= 0,
        "utilization": value / allowance if allowance else float("inf"),
    }
