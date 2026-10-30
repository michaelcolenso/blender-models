# Meydenbauer canonical construction state

This directory is the migration seam between the existing Meydenbauer production pipeline and the Construction Intelligence Engine.

`build_project_state.py` wraps verified values from the current under-slab deliverable in the canonical semantic model. It deliberately does **not** replace the existing extraction, takeoff, scheduling, logistics or Blender code yet.

The first state encodes the decision chain behind the slab allowance: drawing evidence, unknown POC depth, confirmed typical trench width, S1/S2/S3 scenarios, slab-cut/excavation quantities and unresolved risk.

Next: replace bootstrap constants with adapters reading `takeoff.json`, schedule/logistics outputs and per-run metadata; then emit individual pipe/trench/fixture/structure elements with stable IDs.
