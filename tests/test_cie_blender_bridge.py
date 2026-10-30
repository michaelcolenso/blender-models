import importlib.util
import json
from pathlib import Path


def _load_bridge():
    path = Path(__file__).parents[1] / "projects/meydenbauer-b/state/tag_blender_semantics.py"
    spec = importlib.util.spec_from_file_location("meydenbauer_semantic_bridge", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_pipe_object_map_matches_model_naming_and_is_unique():
    root = Path(__file__).parents[1] / "projects/meydenbauer-b"
    spec_data = json.loads((root / "products/underslab/meydenbauer-b.spec.json").read_text())
    mapping = _load_bridge().pipe_object_map(spec_data)

    assert len(mapping) == 136
    assert len({metadata["cie_id"] for metadata in mapping.values()}) == 136
    assert "B-104-R000" in mapping
    assert mapping["B-104-R000"]["cie_id"].startswith("meydenbauer-b:pipe:b-104:")
    assert all(metadata["cie_source"] == "P1.02" for metadata in mapping.values())
