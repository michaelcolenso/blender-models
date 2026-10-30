"""Canonical semantic types for the Construction Intelligence Engine.

Keep this module dependency-light. Blender, web applications and project-specific
extractors should depend on these concepts rather than on one another.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class Status(str, Enum):
    CONFIRMED = "confirmed"
    PROVISIONAL = "provisional"
    ASSUMED = "assumed"
    UNKNOWN = "unknown"


class Confidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NONE = "none"


@dataclass(frozen=True)
class Evidence:
    id: str
    kind: str
    source: str
    locator: str | None = None
    description: str | None = None
    checksum: str | None = None


@dataclass(frozen=True)
class Claim:
    id: str
    subject_id: str
    predicate: str
    value: Any
    evidence_ids: tuple[str, ...] = ()
    status: Status = Status.UNKNOWN
    confidence: Confidence = Confidence.NONE
    rationale: str | None = None


@dataclass(frozen=True)
class Element:
    id: str
    kind: str
    name: str
    project_id: str
    parent_id: str | None = None
    source_ids: tuple[str, ...] = ()
    status: Status = Status.UNKNOWN
    properties: dict[str, Any] = field(default_factory=dict)
    geometry_ref: str | None = None


@dataclass(frozen=True)
class Relationship:
    id: str
    kind: str
    from_id: str
    to_id: str
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Quantity:
    id: str
    element_id: str
    measure: str
    value: float
    unit: str
    scenario_id: str | None = None
    source_claim_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class Activity:
    id: str
    name: str
    phase: str
    element_ids: tuple[str, ...] = ()
    duration_working_days: float | None = None
    predecessor_ids: tuple[str, ...] = ()
    assumptions: tuple[str, ...] = ()


@dataclass(frozen=True)
class Issue:
    id: str
    title: str
    description: str
    severity: str
    element_ids: tuple[str, ...] = ()
    claim_ids: tuple[str, ...] = ()
    resolution_status: str = "open"


@dataclass(frozen=True)
class Scenario:
    id: str
    name: str
    description: str
    inputs: dict[str, Any] = field(default_factory=dict)
    derived_from: str | None = None


@dataclass(frozen=True)
class ConstructionState:
    activity_id: str | None = None
    working_day: float | None = None
    element_states: dict[str, str] = field(default_factory=dict)


@dataclass
class ProjectState:
    schema_version: str
    project_id: str
    name: str
    evidence: list[Evidence] = field(default_factory=list)
    claims: list[Claim] = field(default_factory=list)
    elements: list[Element] = field(default_factory=list)
    relationships: list[Relationship] = field(default_factory=list)
    quantities: list[Quantity] = field(default_factory=list)
    activities: list[Activity] = field(default_factory=list)
    issues: list[Issue] = field(default_factory=list)
    scenarios: list[Scenario] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
