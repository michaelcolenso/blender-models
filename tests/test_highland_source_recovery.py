"""Reject regressions that would erase the archived Highland recovery boundaries."""

import copy
import importlib.util
import json
import shutil

import pytest

from bmodels.paths import ROOT

PRODUCT = ROOT / "projects/highland/products/exterior-reconciliation"
spec = importlib.util.spec_from_file_location("highland_source_check", PRODUCT / "check.py")
check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check)


def test_archived_source_and_report_are_reproducible_without_pdfs_or_blender():
    assert check.build_report() == json.loads(check.REPORT.read_text())


def test_changed_snapshot_is_rejected_without_rewriting_it(tmp_path):
    shutil.copytree(PRODUCT, tmp_path / "product")
    snapshot = tmp_path / "product/snapshots/reconciled.spec.json"
    snapshot.write_bytes(snapshot.read_bytes() + b" ")
    before = snapshot.read_bytes()
    with pytest.raises(ValueError, match="Snapshot size drift"):
        check.verify_snapshot(tmp_path / "product")
    assert snapshot.read_bytes() == before


@pytest.mark.parametrize("change, message", [
    ("north", "Deferred north opening geometry changed"),
    ("pair", "contiguous interface"),
    ("terrace", "Terrace overlaps enclosed room"),
    ("guard", "Guard crosses room"),
    ("certainty", "must remain assumed"),
    ("scale", "calibration does not reconcile"),
])
def test_recovery_rejects_semantic_regressions_even_without_fingerprint_checks(change, message):
    records = copy.deepcopy(check.verify_snapshot()[1])
    model = records["reconciled.spec.json"]
    if change == "north":
        next(row for row in model["openings"] if row["id"] == "north-R1-01")["u"] += 1
    elif change == "pair":
        next(row for row in model["openings"] if row["id"] == "south-R5-08")["u"] += 1
    elif change == "terrace":
        model["terrace_review"]["surfaces"][0]["polygon"] = [[800, 800], [810, 800], [810, 810], [800, 810]]
    elif change == "guard":
        model["terrace_review"]["guards"][0]["path"] = [[800, 800], [810, 800]]
    elif change == "certainty":
        model["openings"][0]["status"] = "confirmed"
    elif change == "scale":
        model["drawing_reconciliation"]["calibration"]["R5"]["pixels_per_inch_by_span"][0] += 0.01
    with pytest.raises(ValueError, match=message):
        check.audit_geometry(records)


def test_sources_are_optional_but_wrong_present_source_and_strict_missing_source_fail(tmp_path):
    registry = ROOT / "projects/highland/sources/manifest.json"
    (tmp_path / "manifest.json").write_bytes(registry.read_bytes())
    assert all(row.startswith("MISSING") for row in check.verify_sources(tmp_path))
    with pytest.raises(ValueError, match="Missing source PDF"):
        check.verify_sources(tmp_path, require_sources=True)
    name = json.loads(registry.read_text())["documents"][0]["file"]
    (tmp_path / name).write_bytes(b"wrong PDF")
    with pytest.raises(ValueError, match="does not match recorded source"):
        check.verify_sources(tmp_path)


BUILDER = PRODUCT / "builder"


def test_builder_inputs_are_recorded_and_verbatim_files_are_unchanged():
    import hashlib

    inputs = json.loads((BUILDER / "inputs.json").read_text())
    rows = {row["file"]: row for row in inputs["files"]}
    assert {path.relative_to(BUILDER).as_posix() for path in BUILDER.rglob("*")
            if path.is_file() and path.name not in {"inputs.json", "release-assets.json", "paths.py", "verify.py"}
            and "__pycache__" not in path.parts} == set(rows)
    for name, row in rows.items():
        if row["state"] == "verbatim":
            data = (BUILDER / name).read_bytes()
            assert (len(data), hashlib.sha256(data).hexdigest()) == (row["bytes"], row["sha256"]), name
    # Only path handling was ported; the geometry modules stay byte-identical.
    assert {n for n, r in rows.items() if r["state"] == "ported"} == {
        "build.py", "validate.py", "check_terraces.py", "render.py"}


def test_builder_reads_only_current_layout_paths():
    # paths.py names the old locations in comments only; the ported modules must not.
    for name in ("build.py", "validate.py", "check_terraces.py", "render.py"):
        text = (BUILDER / name).read_text()
        assert "parents[2]" not in text and "deliverables/highland-drawings" not in text, name
        assert "projects/highland-drawings" not in text and "/home/" not in text, name


def test_base_scene_release_record_matches_the_historical_base_hash():
    manifest = json.loads((BUILDER / "release-assets.json").read_text())
    historical = json.loads((BUILDER / "inputs/historical-geometry-validation.json").read_text())
    assert [a["sha256"] for a in manifest["assets"]] == [historical["base_native_sha256"]]
    native = json.loads((ROOT / "projects/highland/deliverables/exterior-reconciliation/native-check.json").read_text())
    assert native["status"] == "PASS" and native["base_scene_sha256"] == historical["base_native_sha256"]
    assert native["architecture_mesh_hashes_identical_to_historical"] == len(historical["after"]) == 960


def test_published_files_are_the_validated_ones():
    deliver = ROOT / "projects/highland/deliverables/exterior-reconciliation"
    manifest = json.loads((PRODUCT / "release-assets.json").read_text())
    by_name = {a["name"]: a["sha256"] for a in manifest["assets"]}
    delivery = json.loads((deliver / "delivery-validation.json").read_text())
    assert delivery["status"] == "PASS"
    assert by_name["Highland-drawing-reconciled.blend"] == delivery["native_sha256"]
    assert by_name["Highland-drawing-reconciled.glb"] == delivery["glb_sha256"]
    native = json.loads((deliver / "native-check.json").read_text())
    renders = json.loads((deliver / "render-records.json").read_text())
    assert renders["architecture_inventory_sha256"] == native["architecture_inventory_sha256"]
    assert all(p.stat().st_size < 1_000_000 for p in (deliver / "previews").iterdir())
