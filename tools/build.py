"""Deterministic Blender model builder for construction takeoff specs.

Usage:
    python tools/build.py specs/<name>.yaml [--out build/] [--realistic]

Reads a YAML model spec (every element traced to a source or marked assumed),
builds it with bpy, verifies geometry against the spec, and writes:
    <out>/<name>/<name>.blend, .glb, review renders (PNG), report.md, report.json
Exits 1 if any check fails, so CI blocks bad specs.
"""
import argparse, json, math, sys
from pathlib import Path

import bpy
import yaml
from mathutils import Vector

IN = 0.0254  # spec units are inches; Blender works in meters internally
TOL_DEFAULT = 0.0625  # inches (1/16")

MATERIALS = {  # base color RGB, roughness — edit per project
    "pt_lumber": ((0.55, 0.45, 0.30), 0.8),
    "df_lumber": ((0.70, 0.55, 0.38), 0.7),
    "concrete": ((0.62, 0.62, 0.60), 0.9),
    "steel": ((0.45, 0.46, 0.48), 0.4),
    "galv_steel": ((0.70, 0.72, 0.74), 0.35),
    "gyp_board": ((0.92, 0.92, 0.90), 0.9),
    "membrane": ((0.15, 0.15, 0.16), 0.6),
    "siding": ((0.80, 0.78, 0.72), 0.7),
    "glass": ((0.60, 0.75, 0.80), 0.05),
    "default": ((0.8, 0.8, 0.8), 0.7),
    # house palette — colors ASSUMED (AH500: color scheme TBD); patterns visual only
    "siding": ((0.47, 0.50, 0.45), 0.8),
    "gable_panel": ((0.55, 0.57, 0.52), 0.8),
    "trim": ((0.90, 0.89, 0.85), 0.6),
    "shingles": ((0.16, 0.16, 0.17), 0.9),
    "door": ((0.30, 0.22, 0.16), 0.5),
    "garage_door": ((0.88, 0.87, 0.83), 0.5),
    "grass": ((0.20, 0.30, 0.12), 1.0),
}
PATTERN = {  # (axis, period_in, duty, bump_strength): procedural relief for realistic renders
    "siding": ("z", 7.0, 0.12, 0.6),        # lap siding, ~7 in exposure (visual only)
    "gable_panel": ("xy", 12.0, 0.10, 0.5), # 1x4 battens on panel (spacing visual only)
    "shingles": ("z", 1.7, 0.15, 0.4),      # course lines (visual only)
    "garage_door": ("z", 19.5, 0.03, 0.4),
}
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


def material(key):
    name = f"mat_{key}"
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    rgb, rough = MATERIALS.get(key, MATERIALS["default"])
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb, 1)
    b.inputs["Roughness"].default_value = rough
    m.diffuse_color = (*rgb, 1)
    if key == "glass":
        b.inputs["Transmission Weight"].default_value = 0.9
        b.inputs["Roughness"].default_value = 0.02
        b.inputs["Base Color"].default_value = (0.35, 0.45, 0.5, 1)
    if key in PATTERN:
        axis, per, duty, strength = PATTERN[key]
        nt = m.node_tree; N = nt.nodes
        tc = N.new("ShaderNodeTexCoord"); sep = N.new("ShaderNodeSeparateXYZ")
        nt.links.new(tc.outputs["Object"], sep.inputs[0])
        if axis == "xy":
            add = N.new("ShaderNodeMath"); add.operation = "ADD"
            nt.links.new(sep.outputs[0], add.inputs[0]); nt.links.new(sep.outputs[1], add.inputs[1]); src = add.outputs[0]
        else:
            src = sep.outputs[2]
        div = N.new("ShaderNodeMath"); div.operation = "DIVIDE"; div.inputs[1].default_value = per * 0.0254
        nt.links.new(src, div.inputs[0])
        fr = N.new("ShaderNodeMath"); fr.operation = "FRACT"; nt.links.new(div.outputs[0], fr.inputs[0])
        lt = N.new("ShaderNodeMath"); lt.operation = "LESS_THAN"; lt.inputs[1].default_value = duty
        nt.links.new(fr.outputs[0], lt.inputs[0])
        bump = N.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = strength
        bump.inputs["Distance"].default_value = 0.01
        inv = N.new("ShaderNodeMath"); inv.operation = "SUBTRACT"; inv.inputs[0].default_value = 1.0
        nt.links.new(lt.outputs[0], inv.inputs[1]); nt.links.new(inv.outputs[0], bump.inputs["Height"])
        nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    return m


def status_material(status):
    name = f"status_{status}"
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = STATUS_COLORS.get(status, (0.8, 0.8, 0.8, 1))
    b.inputs["Roughness"].default_value = 0.9
    return m


def image_is_blank(path):
    img = bpy.data.images.load(str(path))
    px = list(img.pixels)[::4 * 7]  # sample red channel
    bpy.data.images.remove(img)
    mean = sum(px) / len(px)
    var = sum((p - mean) ** 2 for p in px) / len(px)
    return var < 1e-4


def box(name, size_in, at_in, rot_z_deg, coll):
    sx, sy, sz = (v * IN for v in size_in)
    bpy.ops.mesh.primitive_cube_add(size=1)
    o = bpy.context.object
    o.name = name
    o.scale = (sx, sy, sz)
    bpy.ops.object.transform_apply(scale=True)
    # 'at' is the min corner; place origin there so rotation pivots at the corner
    o.data.transform(__import__("mathutils").Matrix.Translation((sx / 2, sy / 2, sz / 2)))
    o.location = tuple(v * IN for v in at_in)
    o.rotation_euler[2] = math.radians(rot_z_deg or 0)
    for c in o.users_collection:
        c.objects.unlink(o)
    coll.objects.link(o)
    return o


def build(spec, spec_dir=Path(".")):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = "IMPERIAL"
    sc.unit_settings.length_unit = "INCHES"
    colls = {}
    built = []
    def coll_for(trade):
        if trade not in colls:
            colls[trade] = bpy.data.collections.new(trade)
            sc.collection.children.link(colls[trade])
        return colls[trade]
    extra = {}
    for e in spec["elements"]:
        if e.get("type") == "house":
            sys.path.insert(0, str(Path(__file__).parent))
            import house
            hb, ridges = house.build(e, spec_dir, material, coll_for)
            extra["ridges"] = ridges
            for meta, o in hb:
                for k in ("status", "source", "trade", "basis"):
                    if meta.get(k) is not None:
                        o[k] = str(meta[k])
                o["spec_id"] = e["id"]
                built.append((dict(meta, spec_id=e["id"]), o))
            continue
        trade = e["trade"]
        if trade not in colls:
            colls[trade] = bpy.data.collections.new(trade)
            sc.collection.children.link(colls[trade])
        arr = e.get("array") or {"count": 1, "step": [0, 0, 0]}
        for i in range(arr["count"]):
            at = [a + i * s for a, s in zip(e["at"], arr["step"])]
            name = e["id"] if arr["count"] == 1 else f"{e['id']}.{i+1:02d}"
            o = box(name, e["size"], at, e.get("rot_z", 0), colls[trade])
            o.data.materials.append(material(e.get("material", "default")))
            for k in ("status", "source", "trade", "basis", "note"):
                if e.get(k) is not None:
                    o[k] = str(e[k])
            o["spec_id"] = e["id"]
            built.append((e, o))
    bpy.context.view_layer.update()  # refresh matrix_world before any measurement
    build.extra = extra
    return built


def verify(spec, built):
    results = []
    tol = spec.get("tolerance_in", TOL_DEFAULT)
    for e, o in built:  # builder fidelity: built dims == spec dims
        if "size" not in e:
            continue
        dims = [round(d / IN, 4) for d in o.dimensions]
        ok = all(abs(a - b) <= tol for a, b in zip(dims, e["size"]))
        results.append({"check": f"dims {o.name}", "expected": e["size"], "actual": dims, "ok": ok})
    counts = {}
    for e, _ in built:
        counts[e["id"]] = counts.get(e["id"], 0) + 1
    def extents(objs):
        ps = [o.matrix_world @ v.co for o in objs for v in o.data.vertices]
        lo_ = [min(p[i] for p in ps) / IN for i in range(3)]; hi_ = [max(p[i] for p in ps) / IN for i in range(3)]
        return [round(h - l, 2) for h, l in zip(hi_, lo_)], lo_, hi_
    pts = [o.matrix_world @ Vector(c) for _, o in built for c in o.bound_box if o.type == "MESH"]
    lo = [min(p[i] for p in pts) / IN for i in range(3)]
    hi = [max(p[i] for p in pts) / IN for i in range(3)]
    overall = [round(h - l, 4) for h, l in zip(hi, lo)]
    for c in spec.get("checks", []):  # document-driven checks
        if "count" in c:
            got = counts.get(c["element"], 0)
            results.append({"check": f"count {c['element']}", "expected": c["count"], "actual": got, "ok": got == c["count"], "source": c.get("source")})
        if "overall" in c:
            exp = c["overall"]
            ok = all(x is None or abs(a - x) <= c.get("tol", tol) for a, x in zip(overall, exp))
            results.append({"check": "overall extents (in)", "expected": exp, "actual": overall, "ok": ok, "source": c.get("source")})
        if "extents_trade" in c:
            objs = [o for e_, o in built if e_.get("trade") == c["extents_trade"] and o.type == "MESH"]
            got, _, _ = extents(objs); exp = c["expect"]
            ok = all(x is None or abs(a - x) <= c.get("tol", tol) for a, x in zip(got, exp))
            results.append({"check": f"{c['extents_trade']} extents (in) — {c.get('label','')}", "expected": exp, "actual": got, "ok": ok, "source": c.get("source")})
        if "ridge" in c:
            got = round(build.extra["ridges"][c["ridge"]], 2)
            results.append({"check": f"ridge {c['ridge']} height above FF (in) — {c.get('label','')}", "expected": c["expect"], "actual": got, "ok": abs(got - c["expect"]) <= c.get("tol", tol), "source": c.get("source")})
        if "gap" in c:  # clear distance along an axis between two element instances
            a = bpy.data.objects[c["from"]]; b = bpy.data.objects[c["to"]]; ax = "xyz".index(c["axis"])
            amax = max((a.matrix_world @ Vector(v))[ax] for v in a.bound_box) / IN
            bmin = min((b.matrix_world @ Vector(v))[ax] for v in b.bound_box) / IN
            got = round(bmin - amax, 4)
            results.append({"check": f"gap {c['from']}→{c['to']} {c['axis']}", "expected": c["gap"], "actual": got, "ok": abs(got - c["gap"]) <= c.get("tol", tol), "source": c.get("source")})
    return results, overall, (lo, hi)


def hero_views(ctr, span, lo, hi):
    """Eye-level 3/4 views (5'-6" eye height) from front-left and rear-right."""
    eye = 1.68
    d = span * 0.85
    return {"hero_front": (Vector((ctr.x - d * 0.55, lo.y - d * 0.75, eye)), "PERSP"),
            "hero_rear": (Vector((ctr.x + d * 0.55, hi.y + d * 0.75, eye)), "PERSP")}


def render_views(name, out, bounds, realistic):
    sc = bpy.context.scene
    lo, hi = [Vector(v) * IN for v in bounds]
    ctr = (lo + hi) / 2
    span = max((hi - lo).length, 0.5)
    sc.render.resolution_x, sc.render.resolution_y = 1600, 1200
    world = bpy.data.worlds.new("w"); sc.world = world
    world.color = (0.9, 0.9, 0.9)
    tgt = bpy.data.objects.new("target", None); tgt.location = ctr; sc.collection.objects.link(tgt)
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
    sun.data.energy = 4; sun.rotation_euler = (math.radians(50), 0, math.radians(30)); sc.collection.objects.link(sun)
    views = {
        "iso": (ctr + Vector((1, -1.2, 0.8)).normalized() * span * 1.6, "PERSP"),
        "plan": (ctr + Vector((0, 0, span * 2)), "ORTHO"),
        "front": (ctr + Vector((0, -span * 2, 0)), "ORTHO"),
        "side": (ctr + Vector((span * 2, 0, 0)), "ORTHO"),
    }
    files = []
    # Cycles on CPU only: Workbench/EEVEE need a GPU/EGL context and render
    # blank frames on headless runners (confirmed in testing).
    sc.render.engine = "CYCLES"; sc.cycles.device = "CPU"
    sc.view_settings.view_transform = "Standard"  # true colors; AgX washes out flat review colors
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.9, 0.9, 0.9, 1)
    world.node_tree.nodes["Background"].inputs[1].default_value = 0.35
    originals = {o.name: list(o.data.materials) for o in sc.objects if o.type == "MESH"}
    files = []
    for mode in ["review"] + (["realistic"] if realistic else []):
        for o in sc.objects:
            if o.type != "MESH":
                continue
            o.data.materials.clear()
            if mode == "review":
                o.data.materials.append(status_material(o.get("status")))
            else:
                for m in originals[o.name]:
                    o.data.materials.append(m)
        sc.cycles.samples = 16 if mode == "review" else 96
        vset = views if mode == "review" else hero_views(ctr, span, lo, hi)
        if mode == "realistic":
            sc.cycles.use_denoising = True
            sc.view_settings.view_transform = "AgX"; sc.view_settings.look = "AgX - Base Contrast"
            world.node_tree.nodes["Background"].inputs[0].default_value = (0.62, 0.74, 0.90, 1)
            world.node_tree.nodes["Background"].inputs[1].default_value = 0.6
            sun.data.energy = 3.0; sun.rotation_euler = (math.radians(50), 0, math.radians(-35))
            g = bpy.data.meshes.new("ground"); gv = 60.0
            g.from_pydata([(-gv, -gv, -0.16), (gv, -gv, -0.16), (gv, gv, -0.16), (-gv, gv, -0.16)], [], [(0, 1, 2, 3)])
            go = bpy.data.objects.new("ground", g); sc.collection.objects.link(go); g.materials.append(material("grass"))
        for vname, (loc, ptype) in vset.items():
            cd = bpy.data.cameras.new(f"{mode}_{vname}"); cd.type = ptype
            if ptype == "ORTHO":
                cd.ortho_scale = span * 1.15
            if vname.startswith("hero"):
                cd.lens = 35
            cam = bpy.data.objects.new(f"cam_{mode}_{vname}", cd); cam.location = loc
            sc.collection.objects.link(cam)
            # explicit rotation: constraints are not reliably evaluated before headless renders
            if vname == "plan":
                cam.rotation_euler = (0, 0, 0)  # looking straight down, +Y up on sheet
            else:
                cam.rotation_euler = (ctr - loc).to_track_quat("-Z", "Y").to_euler()
            sc.camera = cam
            f = out / f"{name}_{mode}_{vname}.png"
            sc.render.filepath = str(f)
            bpy.ops.render.render(write_still=True)
            files.append(f.name)
    return files


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spec"); ap.add_argument("--out", default="build")
    ap.add_argument("--realistic", action="store_true", help="add a Cycles render (slow on CPU)")
    ap.add_argument("--no-render", action="store_true")
    a = ap.parse_args()
    spec_path = Path(a.spec)
    spec = yaml.safe_load(spec_path.read_text())
    name = spec_path.stem
    out = Path(a.out) / name; out.mkdir(parents=True, exist_ok=True)

    errors = validate(spec)
    if errors:
        print("SPEC INVALID:\n  " + "\n  ".join(errors)); sys.exit(1)

    spec["_dir"], spec["_path"] = str(spec_path.parent), str(spec_path)
    built = build(spec, spec_path.parent)
    results, overall, bounds = verify(spec, built)
    qto_file = None
    if any(e.get("type") == "house" for e in spec["elements"]):
        import house, qto
        qto_file, q = qto.run(spec, built, out, house)
        chk = spec.get("qto_checks", {})
        if "plan_area_sf" in chk:
            c = chk["plan_area_sf"]; got = q["plan_area_sf"]
            results.append({"check": f"roof plan area (sf) — {c.get('label', '')}", "expected": c["expect"],
                            "actual": got, "ok": abs(got - c["expect"]) <= c["expect"] * c.get("tol_pct", 0.5) / 100,
                            "source": c.get("source")})
    renders = [] if a.no_render else render_views(name, out, bounds, a.realistic)
    for r in renders:  # guard against silent blank renders
        blank = image_is_blank(out / r)
        results.append({"check": f"render not blank {r}", "expected": True, "actual": not blank, "ok": not blank})
    bpy.ops.wm.save_as_mainfile(filepath=str((out / f"{name}.blend").resolve()))
    for o in [o for o in bpy.context.scene.objects if o.type != "MESH"]:
        o.hide_set(True)
    bpy.ops.export_scene.gltf(filepath=str(out / f"{name}.glb"), use_visible=True, export_extras=True)

    status_counts = {}
    for e, _ in built:
        status_counts[e["status"]] = status_counts.get(e["status"], 0) + 1
    failed = [r for r in results if not r["ok"]]
    report = {"spec": str(spec_path), "project": spec.get("project"), "blender": bpy.app.version_string,
              "overall_in": overall, "status_counts": status_counts, "checks": results,
              "renders": renders, "passed": not failed}
    (out / "report.json").write_text(json.dumps(report, indent=2))
    md = [f"# Model report — {name}", f"Blender {bpy.app.version_string} · overall extents (in): {overall}",
          f"Elements by provenance: {status_counts}", "",
          f"**{'PASS' if not failed else 'FAIL'}** — {len(results)-len(failed)}/{len(results)} checks", "",
          "| check | expected | actual | ok | source |", "|---|---|---|---|---|"]
    md += [f"| {r['check']} | {r['expected']} | {r['actual']} | {'✅' if r['ok'] else '❌'} | {r.get('source') or ''} |"
           for r in results if not r["check"].startswith(("dims ", "render ")) or not r["ok"]]
    assumed, seen = [], set()
    for e, _ in built:
        if e.get("status") == "assumed" and e.get("basis") and (e.get("spec_id"), e["basis"]) not in seen:
            seen.add((e.get("spec_id"), e["basis"])); assumed.append(e)
    prov = [e for e in spec["elements"] if e.get("type") == "house"]
    if assumed:
        md += ["", "## Assumed (not from documents)"] + [f"- `{e['id']}` — {e['basis']}" for e in assumed]
    (out / "report.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
