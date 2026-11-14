"""Spec loading and provenance validation — no bpy, so it runs anywhere (bm check, CI planning)."""
from pathlib import Path

import yaml

FACE_ROT = {"+y": 0, "-x": 90, "-y": 180, "+x": -90}  # room items: facing direction -> yaw (deg)

STATUS_COLORS = {  # review renders: color by provenance, not by material
    "confirmed": (0.55, 0.72, 0.55, 1),
    "provisional": (0.95, 0.80, 0.25, 1),
    "assumed": (0.95, 0.45, 0.20, 1),
}
VALID_STATUS = set(STATUS_COLORS)

# What record a model reflects. Values avoid bare yes/no, which YAML 1.1 reads as booleans.
RECORD_KINDS = {"design_intent", "as_built", "field_photo", "field_survey", "mixed", "unknown"}
FIELD_VERIFIED = {"verified", "partial", "not_verified", "unknown"}
REVIEW_VERDICTS = {"pass", "fail", "n/a"}
ELEMENT_TYPES = {None, "detail", "house"}  # None = a plain box element
# Checks build.verify() acts on, and the modifier keys they read. Anything else is a typo that would
# otherwise be skipped silently and let the spec pass with fewer checks.
CHECK_KINDS = {"count", "overall", "extents_trade", "ridge", "between", "drawn", "gap"}
CHECK_MODIFIERS = {"element", "expect", "tol", "label", "source", "from", "to", "axis", "min", "warn_tol", "note"}


def _triple(v):
    return (isinstance(v, (list, tuple)) and len(v) == 3
            and all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in v))


def validate_checks(spec, errors):
    """Every element spec needs at least one document-driven check, and every check must be one verify() runs."""
    checks = spec.get("checks") or []
    if not isinstance(checks, list):
        fail("checks: must be a list", errors)
        return
    if not checks and not spec.get("qto_checks"):
        fail("checks: required; a spec with no document-driven check verifies only that the builder "
             "reproduced the spec", errors)
    for i, c in enumerate(checks):
        if not isinstance(c, dict) or not CHECK_KINDS & set(c):
            fail(f"checks[{i}]: needs one of {sorted(CHECK_KINDS)}", errors)
            continue
        unknown = set(c) - CHECK_KINDS - CHECK_MODIFIERS
        if unknown:
            fail(f"checks[{i}]: unknown key(s) {sorted(unknown)}", errors)


def fail(msg, errors):
    errors.append(msg)


def validate_record(spec, src_ids, errors):
    """basis_of_record is required: a model reflects a record, not the building. The optional
    assumptions, conflicts and review blocks must be well-formed when present."""
    b = spec.get("basis_of_record")
    if not isinstance(b, dict):
        fail("basis_of_record: required; state what record this model reflects "
             "(documents, kind, field_verified)", errors)
    else:
        docs = b.get("documents")
        if not isinstance(docs, str) or not docs.strip():  # YAML `documents:` with no value loads as None
            fail("basis_of_record.documents: required (the drawings/photos the model is built from)", errors)
        if b.get("kind") not in RECORD_KINDS:
            fail(f"basis_of_record.kind must be one of {sorted(RECORD_KINDS)}", errors)
        if b.get("field_verified") not in FIELD_VERIFIED:
            fail(f"basis_of_record.field_verified must be one of {sorted(FIELD_VERIFIED)}", errors)
    for i, a in enumerate(spec.get("assumptions") or []):  # assumed parameters not tied to one element
        if not isinstance(a, dict) or not a.get("id") or not a.get("basis"):
            fail(f"assumptions[{i}]: needs 'id' and 'basis'", errors)
    for i, c in enumerate(spec.get("conflicts") or []):
        if not isinstance(c, dict) or not c.get("topic") or not c.get("note"):
            fail(f"conflicts[{i}]: needs 'topic' and 'note'", errors)
        elif c.get("modeled_per") not in src_ids:
            fail(f"conflicts[{i}]: modeled_per must be a source id from 'sources' (the governing document)", errors)
    r = spec.get("review")
    if r is not None:
        if not isinstance(r, dict) or not r.get("date") or not r.get("by") or not r.get("views"):
            fail("review: needs 'date', 'by' and a non-empty 'views' list "
                 "(omit the block until the visual review has actually been done)", errors)
        else:
            for i, o in enumerate(r.get("overlays") or []):
                if not o.get("view") or o.get("verdict") not in REVIEW_VERDICTS:
                    fail(f"review.overlays[{i}]: needs 'view' and a verdict in {sorted(REVIEW_VERDICTS)}", errors)


def validate(spec):
    errors = []
    src_list = [s["id"] for s in spec.get("sources", [])]
    src_ids = set(src_list)
    for dup in sorted({s for s in src_list if src_list.count(s) > 1}, key=str):
        fail(f"sources: duplicate id '{dup}'", errors)
    validate_record(spec, src_ids, errors)
    validate_checks(spec, errors)
    if not spec.get("elements"):
        fail("elements: required and non-empty", errors)
    seen = set()
    for e in spec.get("elements") or []:
        eid = e.get("id", "?")
        if e.get("type") not in ELEMENT_TYPES:
            fail(f"{eid}: unknown type '{e.get('type')}' (use 'detail', 'house', or omit for a box element)", errors)
            continue
        if eid in seen:
            fail(f"{eid}: duplicate id", errors)
        seen.add(eid)
        if e.get("type") == "detail":
            for c in e.get("components", []):
                cid = c.get("id", "?")
                if c.get("status") not in VALID_STATUS:
                    fail(f"{eid}/{cid}: status must be one of {sorted(VALID_STATUS)}", errors)
                if c.get("status") in ("confirmed", "provisional") and c.get("source") not in src_ids:
                    fail(f"{eid}/{cid}: needs a source id from 'sources'", errors)
                if c.get("status") == "assumed" and not c.get("basis"):
                    fail(f"{eid}/{cid}: assumed component needs a 'basis'", errors)
                if "rect" not in c and "polygon" not in c:
                    fail(f"{eid}/{cid}: needs rect or polygon", errors)
            continue
        if e.get("type") == "house":
            for k in ("takeoff", "walls_source", "plate_height_in", "roof", "openings"):
                if k not in e:
                    fail(f"{eid}: missing '{k}'", errors)
            for o in e.get("openings", []):
                if o.get("status", "provisional") not in VALID_STATUS:
                    fail(f"{eid}/{o.get('id')}: status must be one of {sorted(VALID_STATUS)}", errors)
                if o.get("status", "provisional") in ("confirmed", "provisional") and o.get("source", e.get("walls_source")) not in src_ids:
                    fail(f"{eid}/{o.get('id')}: source not in 'sources'", errors)
                if o.get("status") == "assumed" and not o.get("basis"):
                    fail(f"{eid}/{o.get('id')}: assumed opening needs 'basis'", errors)
            for k in ("walls_source",):
                if e.get(k) not in src_ids:
                    fail(f"{eid}: {k} must reference a source id", errors)
            if e.get("roof", {}).get("source") not in src_ids:
                fail(f"{eid}: roof.source must reference a source id", errors)
            continue
        for k in ("size", "at", "status", "trade"):
            if k not in e:
                fail(f"{eid}: missing '{k}'", errors)
        if e.get("status") not in VALID_STATUS:
            fail(f"{eid}: status must be one of {sorted(VALID_STATUS)}", errors)
        if e.get("status") in ("confirmed", "provisional") and e.get("source") not in src_ids:
            fail(f"{eid}: status '{e.get('status')}' requires a source id from 'sources'", errors)
        if e.get("status") == "assumed" and not e.get("basis"):
            fail(f"{eid}: assumed elements need a 'basis' explaining the assumption", errors)
        for k in ("size", "at"):
            if k in e and not _triple(e[k]):
                fail(f"{eid}: '{k}' must be three numbers [x, y, z] in inches", errors)
        if _triple(e.get("size")) and any(v <= 0 for v in e["size"]):
            fail(f"{eid}: size values must be > 0", errors)
    return errors


def validate_room(spec):
    errs = []
    src = {s["id"] for s in spec["sources"]}
    validate_record(spec, src, errs)
    for gid, g in spec["groups"].items():
        if g.get("status") not in STATUS_COLORS:
            errs.append(f"group {gid}: bad status")
        if g.get("status") in ("confirmed", "provisional") and g.get("source") not in src:
            errs.append(f"group {gid}: needs source id")
        if g.get("status") == "assumed" and not g.get("basis"):
            errs.append(f"group {gid}: assumed needs basis")
        if "trade" not in g:
            errs.append(f"group {gid}: missing trade")
    ids = set()
    for it in spec["items"]:
        if it["id"] in ids:
            errs.append(f"{it['id']}: duplicate")
        ids.add(it["id"])
        if it["group"] not in spec["groups"]:
            errs.append(f"{it['id']}: unknown group {it['group']}")
        if it.get("faces") not in FACE_ROT:
            errs.append(f"{it['id']}: faces must be one of {list(FACE_ROT)}")
        if any(v <= 0 for v in it["size"]):
            errs.append(f"{it['id']}: size must be > 0")
    return errs


def load(path):
    return yaml.safe_load(Path(path).read_text())


def kind(spec):
    """Model type of a spec: room (photo-derived interior) or the element types it builds."""
    if "items" in spec:
        return "room"
    types = sorted({e.get("type") or "element" for e in spec.get("elements", [])})
    return "+".join(types) or "empty"


def check(spec):
    """Provenance and structure errors for any spec type (empty list = valid)."""
    return validate_room(spec) if "items" in spec else validate(spec)
