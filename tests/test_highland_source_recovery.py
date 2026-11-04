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
