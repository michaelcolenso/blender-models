"""Stamp canonical CIE IDs onto the existing Meydenbauer Blender scene.

Run with Blender's Python after the normal underslab build. It does not create or
move geometry. It maps the deterministic curve names emitted by build.py back to
the same spec edges used by the CIE artifact adapter, stamps custom properties,
and re-exports GLB with custom properties as glTF extras.

Usage:
  blender -b projects/meydenbauer-b/deliverables/underslab/Meydenbauer-B-underslab.blend \
    --python projects/meydenbauer-b/state/tag_blender_semantics.py
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from cie.ids import semantic_id

PROJECT = "meydenbauer-b"
ROOT = Path(__file__).parents[1]
SPEC_PATH = ROOT / "products" / "underslab" / "meydenbauer-b.spec.json"
GLB_PATH = ROOT / "deliverables" / "underslab" / "Meydenbauer-B-underslab.glb"


def pipe_object_map(spec: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Return Blender object name -> semantic metadata without importing bpy."""
    mapping: dict[str, dict[str, Any]] = {}
    for unit in spec["units"]:
        unit_name = unit["unit"]
        for index, edge in enumerate(unit["edges"]):
            object_name = f"{unit_name}-R{index:03d}"
            cie_id = semantic_id(PROJECT, "pipe", unit_name, edge["a"], edge["b"])
            mapping[object_name] = {
                "cie_id": cie_id,
                "cie_kind": "pipe",
                "cie_unit": unit_name,
                "cie_status": "provisional",
                "cie_source": "P1.02",
                "cie_node_a": edge["a"],
                "cie_node_b": edge["b"],
                "cie_nominal_in": edge["nominal_in"],
                "cie_length_ft": float(edge["length_ft"]),
            }
    return mapping


def main() -> None:
    import bpy

    spec = json.loads(SPEC_PATH.read_text())
    mapping = pipe_object_map(spec)
    missing: list[str] = []
    stamped = 0
    for object_name, metadata in mapping.items():
        obj = bpy.data.objects.get(object_name)
        if obj is None:
            missing.append(object_name)
            continue
        for key, value in metadata.items():
            obj[key] = value
        stamped += 1

    if missing:
        raise RuntimeError(f"semantic bridge: {len(missing)} expected pipe objects missing: {missing[:10]}")
    if stamped != len(mapping):
        raise RuntimeError(f"semantic bridge: stamped {stamped}, expected {len(mapping)}")

    scene = bpy.context.scene
    scene["cie_project_id"] = PROJECT
    scene["cie_schema_version"] = "0.1.0"
    scene["cie_pipe_count"] = stamped

    bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
    bpy.ops.export_scene.gltf(
        filepath=str(GLB_PATH),
        export_format="GLB",
        export_extras=True,
        export_yup=True,
    )
    print(f"CIE semantic bridge: stamped {stamped} pipes; exported {GLB_PATH}")


if __name__ == "__main__":
    main()
