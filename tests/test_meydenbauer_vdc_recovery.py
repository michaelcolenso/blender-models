"""The recovered VDC/B101 snapshots are byte-identical and the reconciliation report is current."""

import gzip
import importlib.util
import json
import shutil

import pytest

from bmodels.paths import ROOT

PRODUCT = ROOT / "projects/meydenbauer-b/products/vdc-recovery"
spec = importlib.util.spec_from_file_location("vdc_reconcile", PRODUCT / "reconcile.py")
reconcile = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reconcile)


def test_snapshots_match_recovery_record():
    recovery, data = reconcile.load_snapshots()
    assert len(data) == len(recovery["files"]) == 80
    assert all(p.stat().st_size < 1_000_000 for p in (PRODUCT / "snapshots").rglob("*") if p.is_file())


def test_changed_snapshot_is_rejected(tmp_path, monkeypatch):
    copy = tmp_path / "vdc-recovery"
    shutil.copytree(PRODUCT, copy, ignore=shutil.ignore_patterns("__pycache__"))
    target = copy / "snapshots/vdc/Meydenbauer_VDC_Schedule.csv"
    target.write_bytes(target.read_bytes().replace(b"29", b"28", 1) if b"29" in target.read_bytes() else target.read_bytes() + b" ")
    monkeypatch.setattr(reconcile, "HERE", copy)
    with pytest.raises(SystemExit, match="snapshot drift"):
        reconcile.load_snapshots()


def test_gzip_snapshot_is_deterministic_and_recorded_on_original_bytes():
    recovery = json.loads((PRODUCT / "recovery.json").read_text())
    (row,) = [r for r in recovery["files"] if r["stored"] == "gzip"]
    raw = gzip.decompress((PRODUCT / row["file"]).read_bytes())
    assert len(raw) == row["bytes"] > 1_000_000


def test_report_is_current_and_nothing_was_imported():
    report = json.loads((ROOT / "projects/meydenbauer-b/deliverables/vdc-recovery/reconciliation.json").read_text())
    assert report["identifiers"]["vdc_ids_in_canonical"] == 0
    assert report["schedule"]["comparable"] is False
    state = (ROOT / "projects/meydenbauer-b/state/project-state.json").read_text()
    assert "PLM-B10" not in state and "MEYD-BL-001" not in state
