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


def fail(msg, errors):
    errors.append(msg)


def validate(spec):
    errors = []
    src_ids = {s["id"] for s in spec.get("sources", [])}
    seen = set()
    for e in spec.get("elements", []):
        eid = e.get("id", "?")
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
        if any(v <= 0 for v in e.get("size", [1, 1, 1])):
            fail(f"{eid}: size values must be > 0", errors)
    return errors


def validate_room(spec):
    errs = []
    src = {s["id"] for s in spec["sources"]}
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
