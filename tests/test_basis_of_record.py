"""Every spec states its basis of record; reports and renders carry it. No bpy needed."""

import copy

import pytest
from PIL import Image

from bmodels import record, spec
from bmodels.paths import ROOT

BASE = {
    "project": "T",
    "basis_of_record": {"documents": "Sheet S1", "kind": "design_intent", "field_verified": "not_verified"},
    "sources": [{"id": "S1", "ref": "Sheet S1", "type": "drawing"}],
    "elements": [{"id": "a", "trade": "framing", "size": [1, 1, 1], "at": [0, 0, 0],
                  "status": "confirmed", "source": "S1"}],
}


def errors(**changes):
    s = copy.deepcopy(BASE)
    for k, v in changes.items():
        if v is None:
            s.pop(k, None)
        else:
            s[k] = v
    return spec.check(s)


def test_valid_spec_passes():
    assert errors() == []


def test_basis_of_record_is_required():
    assert any("basis_of_record: required" in e for e in errors(basis_of_record=None))


@pytest.mark.parametrize("field,value", [("kind", "drawing"), ("field_verified", True), ("documents", " ")])
def test_basis_of_record_fields_are_checked(field, value):
    b = dict(BASE["basis_of_record"], **{field: value})
    assert any(f"basis_of_record.{field}" in e for e in errors(basis_of_record=b))


def test_conflict_must_name_a_governing_source():
    assert any("modeled_per" in e for e in errors(conflicts=[{"topic": "x", "note": "y", "modeled_per": "S9"}]))
    assert errors(conflicts=[{"topic": "x", "note": "y", "modeled_per": "S1"}]) == []


def test_review_block_needs_date_by_views():
    assert any(e.startswith("review:") for e in errors(review={"date": "2026-11-05"}))
    assert errors(review={"date": "2026-11-05", "by": "MC", "views": ["iso"]}) == []


def test_assumptions_need_basis():
    assert any("assumptions[0]" in e for e in errors(assumptions=[{"id": "x"}]))


def test_room_specs_are_checked_too():
    room = {"project": "R", "sources": [{"id": "P1"}], "groups": {}, "items": []}
    assert any("basis_of_record" in e for e in spec.check(room))


def test_every_committed_spec_and_template_is_valid():
    paths = sorted(ROOT.glob("projects/*/specs/*.yaml")) + sorted(ROOT.glob("templates/project/specs/*.yaml"))
    assert paths
    for p in paths:
        import yaml
        assert spec.check(yaml.safe_load(p.read_text().replace("{{name}}", "x"))) == [], p


def test_report_sections():
    md = "\n".join(record.record_md(BASE) + record.conflicts_md(BASE, []) + record.review_md(BASE))
    assert "## Basis of record" in md and "not** a confirmed built condition" in md
    assert "None recorded." in md
    assert "**NOT RECORDED.**" in md


def test_stamp_appends_strip_below_image(tmp_path):
    p = tmp_path / "x_review_iso.png"
    Image.new("RGB", (400, 300), (10, 200, 10)).save(p)
    record.stamp_render(p, BASE, {"confirmed": 1}, "review")
    im = Image.open(p)
    assert im.size[0] == 400 and im.size[1] > 300
    assert im.getpixel((200, 150)) == (10, 200, 10)  # geometry area untouched
