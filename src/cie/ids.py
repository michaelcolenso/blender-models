"""Stable semantic identifier helpers."""

from __future__ import annotations

import re

_SLUG = re.compile(r"[^a-z0-9]+")


def slug(value: str) -> str:
    value = _SLUG.sub("-", value.strip().lower()).strip("-")
    if not value:
        raise ValueError("identifier component cannot be empty")
    return value


def semantic_id(project: str, kind: str, *parts: str) -> str:
    """Build a readable deterministic ID independent of Blender object names."""
    components = [slug(project), slug(kind), *(slug(p) for p in parts)]
    return ":".join(components)
