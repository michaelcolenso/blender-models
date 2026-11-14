"""bm route-qa: route-table checks and the QA board (bpy-free)."""
import json
from pathlib import Path

import pytest

from bmodels import route_qa
from bmodels.paths import ROOT

B101 = ROOT / "projects/meydenbauer-b/products/vdc-recovery/snapshots/b101/data"
ROUTES = B101 / "b101_route_controls_calibrated_v2.csv"
FITTINGS = B101 / "B101_demolition_fitting_schedule_v4.csv"
HEAD = "unit,system,role,parent_role,point_seq,nominal_in,x_ft,y_ft,scope_status\n"
GOOD = HEAD + ("U,main,m,,1,4,0,0,NEW\nU,main,m,,2,4,20,0,NEW\n"
               "U,branch,b,m,1,2,10,6,NEW; FIELD VERIFY\nU,branch,b,m,2,2,10,0,NEW; FIELD VERIFY\n")


def levels(report):
    return {c["name"]: c["level"] for c in report["checks"]}


def qa(tmp_path, text, *extra):
    src = tmp_path / "routes.csv"
    src.write_text(text)
    code = route_qa.main([str(src), "--out", str(tmp_path / "board"), *extra])
    return code, json.loads((tmp_path / "board.json").read_text())


def test_b101_tables_pass_and_match_the_recorded_lengths(tmp_path):
    code = route_qa.main([str(ROUTES), "--fittings", str(FITTINGS), "--x-dir", "down", "--y-dir", "left",
                          "--out", str(tmp_path / "b101")])
    rep = json.loads((tmp_path / "b101.json").read_text())
    assert code == 0 and rep["verdict"] == "pass"
    lengths = {r["key"]: r["plan_length_ft"] for r in rep["routes"]}
    # docs/b101_calibration_report.md: new 4-inch main 27.40 ft, retained prior ABS 26.83 ft
    assert lengths["B101/main_4/new_wet_core_main"] == pytest.approx(27.40, abs=0.005)
    assert lengths["B101/prior_abs_4/remain_kitchen_dining"] == pytest.approx(26.83, abs=0.005)
    assert rep["fittings"] == 33 and levels(rep)["fittings"] == "pass"
    assert levels(rep)["connectivity"] == "warn"  # 'main_4 upstream tie' names no role or system
    assert (tmp_path / "b101.png").stat().st_size > 10_000
    assert route_qa.main([str(ROUTES), "--strict", "--out", str(tmp_path / "strict")]) == 1


def test_good_table_passes(tmp_path):
    code, rep = qa(tmp_path, GOOD)
    assert code == 0 and set(levels(rep).values()) == {"pass"}
    assert [r["field_verify"] for r in rep["routes"]] == [False, True]


@pytest.mark.parametrize("text, check", [
    (GOOD.replace("U,branch,b,m,2,2,10,0", "U,branch,b,m,2,2,10,0.5"), "connectivity"),   # stops short of the main
    (GOOD.replace("U,branch,b,m,2,2,10,0", "U,branch,b,m,3,2,10,0"), "sequence"),         # gap in point_seq
    (GOOD.replace("10,6,NEW; FIELD VERIFY", "10,6,"), "status"),                          # no scope_status
    (GOOD + "U,main,dup,,1,4,5,0,NEW\nU,main,dup,,2,4,12,0,NEW\n", "duplicates"),          # 7 ft modelled twice
])
def test_defects_fail(tmp_path, text, check):
    code, rep = qa(tmp_path, text)
    assert code == 1 and levels(rep)[check] == "fail"


def test_fitting_off_route_fails(tmp_path):
    fit = tmp_path / "fit.csv"
    fit.write_text("id,component,demo_status,x_ft,y_ft\nJ1,wye,REMOVE,10,0\nJ2,wye,REMOVE,10,9\n")
    code, rep = qa(tmp_path, GOOD, "--fittings", str(fit))
    assert code == 1 and "J2 is 3.00 ft" in rep["checks"][-1]["detail"] and "J1" not in rep["checks"][-1]["detail"]


def sheet(tmp_path, to_page):
    """A one-page PDF with the GOOD routes drawn at a known plan->page transform."""
    pymupdf = pytest.importorskip("pymupdf")
    doc = pymupdf.open()
    page = doc.new_page(width=800, height=600)
    for a, b in (((0, 0), (20, 0)), ((10, 6), (10, 0))):
        page.draw_line(to_page(*a), to_page(*b), width=2)
    pdf = tmp_path / "sheet.pdf"
    doc.save(pdf)
    return pdf


def test_sheet_registration_and_ink(tmp_path):
    to_page = lambda x, y: (100 + 18 * x, 400 - 18 * y)  # 18 pt/ft, y up the page
    pdf = sheet(tmp_path, to_page)
    ctl = [f"{x},{y}={to_page(x, y)[0]},{to_page(x, y)[1]}" for x, y in ((0, 0), (20, 0), (10, 6), (20, 6))]
    args = ["--pdf", str(pdf), "--page", "1"]
    code, rep = qa(tmp_path, GOOD, *args, *[v for c in ctl for v in ("--control", c)])
    assert code == 0 and levels(rep)["registration"] == "pass"
    assert rep["registration"]["pt_per_ft"] == [18.0, 18.0] and rep["ink_agreement"] == 1.0
    # three controls fit exactly: say so instead of passing
    code, rep = qa(tmp_path, GOOD, *args, *[v for c in ctl[:3] for v in ("--control", c)])
    assert code == 0 and levels(rep)["registration"] == "warn"
    # one control 2 ft out: the fit must fail, not average it away
    bad = ctl[:3] + [f"20,6={to_page(22, 6)[0]},{to_page(22, 6)[1]}"]
    code, rep = qa(tmp_path, GOOD, *args, *[v for c in bad for v in ("--control", c)])
    assert code == 1 and levels(rep)["registration"] == "fail"
    # routes shifted 3 ft off the linework: registration still passes, ink agreement drops
    shifted = GOOD.replace(",0,0,NEW", ",0,3,NEW").replace(",20,0,NEW", ",20,3,NEW").replace("10,0,NEW", "10,3,NEW")
    code, rep = qa(tmp_path, shifted, *args, *[v for c in ctl for v in ("--control", c)])
    assert rep["ink_agreement"] < 0.5


def test_cli_lists_route_qa():
    from bmodels import cli
    assert cli.TOOLS["route-qa"] == "route_qa" and Path(route_qa.__file__).name == "route_qa.py"
