# Construction Intelligence Engine kernel

The kernel is intentionally small and dependency-light. It defines semantic identity, evidence-backed claims, construction elements, relationships, quantities, activities, issues, scenarios and validation.

Project-specific code belongs outside this package. Blender and web consumers should consume canonical state rather than import each other's implementation details.

Current schema version: `0.1.0`.

The immediate proof target is not generic BIM interoperability. It is the Meydenbauer decision chain: a selectable construction element must be traceable to evidence and assumptions, and a scenario change must propagate to quantities and eventually geometry, schedule, logistics, Explorer and film.
