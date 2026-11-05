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


def test_only_the_decided_vdc_data_enters_canonical_state():
    report = json.loads((ROOT / "projects/meydenbauer-b/deliverables/vdc-recovery/reconciliation.json").read_text())
    assert report["identifiers"]["vdc_ids_in_canonical"] == 0
    state = json.loads((ROOT / "projects/meydenbauer-b/state/project-state.json").read_text())
    assert "PLM-B10" not in json.dumps(state)  # no VDC element identities, only unit-level quantities
    claims = {c["id"].split(":")[-1]: c for c in state["claims"]}
    vdc = claims["vdc-scope-quantities"]
    assert (vdc["status"], vdc["confidence"]) == ("assumed", "low")
    adopted = [q for q in state["quantities"] if q["source_claim_ids"] == [vdc["id"]]]
    assert len(adopted) == 40 and {q["element_id"].split(":")[1] for q in adopted} == {"unit"}
    assert not {q["measure"] for q in adopted} & {"pipe_length", "slab_cut", "excavation_bank", "new_abs_length"}
    assert claims["b103-raised-floor-route-scope"]["value"] is False
    assert claims["schedule-basis"]["value"].startswith("canonical")
    assert state["metadata"]["working_days"] == 81.5  # schedule unchanged by the VDC data


def test_raised_floor_route_contributes_nothing(monkeypatch):
    spec = importlib.util.spec_from_file_location("vdc_scope", PRODUCT / "scope_import.py")
    scope = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(scope)
    rows, _ = scope.scope_quantities()
    monkeypatch.setattr(scope, "RAISED_FLOOR", "no-such-route")
    assert scope.scope_quantities()[0] == rows  # nothing on that route is an adopted item type
    assert not any(m == "pipe_sleeves_new" for _, m, _, _ in rows)
