"""Build the Highland riser specs in Blender: .blend, .glb, provenance review renders, report.

  python build.py [--spec existing|proposed|both] [--no-render] [--samples N]

Reads only the committed *.spec.json (written by takeoff.py). One object per spec element, with
cie-style custom properties (id, status, system, role) so the GLB can be inspected. Review renders
color by provenance status; pipes are drawn at 2x outside diameter for legibility only.
"""
import argparse
import json
import math
import os
import sys
from pathlib import Path

import bpy  # isort: skip  (must precede bmesh)
import bmesh  # isort: skip
from mathutils import Matrix, Vector

from bmodels.paths import BUILD
from bmodels.record import record_md, conflicts_md, review_md, assumptions_md, stamp_render
from bmodels.spec import STATUS_COLORS

HERE = Path(__file__).parent
OUT = Path(os.environ.get("BM_BUILD") or BUILD / "highland" / "risers")
IN = 0.0254
DISPLAY_OD_MULT = 2.0
SYSTEM_COLORS = {"CW": (0.10, 0.35, 0.85, 1), "HW": (0.85, 0.12, 0.10, 1), "HWC": (0.95, 0.55, 0.05, 1)}
FOOTPRINT_IN = (-195, -690, 1041, 1110)  # grid 6..10 x H..A; context only (assumed simplification)


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    _mats.clear()
    sc = bpy.context.scene
    sc.unit_settings.system = "IMPERIAL"
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.view_settings.view_transform = "Standard"
    world = bpy.data.worlds.new("world"); sc.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.93, 0.94, 0.96, 1)
    world.node_tree.nodes["Background"].inputs[1].default_value = 0.9


_mats = {}


def mat(name, rgba, alpha=1.0):
    key = (name, alpha)
    if key in _mats:
        return _mats[key]
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = rgba
    b.inputs["Roughness"].default_value = 0.55
    if alpha < 1:
        b.inputs["Alpha"].default_value = alpha
    m.diffuse_color = rgba
    _mats[key] = m
    return m


def v(p):
    return Vector((p[0] * IN, p[1] * IN, p[2] * IN))


def add_cyl(bm, a, b, r, seg=12):
    a, b = Vector(a), Vector(b); d = b - a
    if d.length < 1e-6:
        return
    geom = bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=r, radius2=r, depth=d.length)
    rot = d.normalized().to_track_quat("Z", "Y").to_matrix().to_4x4()
    bmesh.ops.transform(bm, matrix=Matrix.Translation((a + b) / 2) @ rot, verts=geom["verts"])


def add_sphere(bm, c, r):
    geom = bmesh.ops.create_uvsphere(bm, u_segments=12, v_segments=8, radius=r)
    bmesh.ops.translate(bm, vec=Vector(c), verts=geom["verts"])


def add_box(bm, c, size):
    geom = bmesh.ops.create_cube(bm, size=1)
    bmesh.ops.scale(bm, vec=Vector(size), verts=geom["verts"])
    bmesh.ops.translate(bm, vec=Vector(c), verts=geom["verts"])


def obj_from(bm, name, material, coll, props):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); coll.objects.link(ob)
    me.materials.append(material)
    for k, val in props.items():
        if val is not None:
            ob[k] = val if isinstance(val, (int, float, str)) else json.dumps(val)
    return ob


def element_mesh(e, mult):
    bm = bmesh.new()
    k = e["kind"]
    if k == "pipe":
        r = (e["nominal_in"] + 0.125) / 2 * IN * mult
        pts = [v(p) for p in e["points"]]
        for a, b in zip(pts, pts[1:]):
            add_cyl(bm, a, b, r)
        for p in pts[1:-1]:
            add_sphere(bm, p, r * 1.15)
    elif k in ("valve", "tie"):
        s = (e.get("nominal_in", 1) + 1.5) * IN * (1.4 if k == "valve" else 1.0)
        (add_box(bm, v(e["at"]), (s, s, s * 1.3)) if k == "valve" else add_sphere(bm, v(e["at"]), s * 0.7))
    elif k in ("penetration", "firestop", "clamp"):
        r = e.get("radius_in", 6) * IN * (1.0 if k != "clamp" else 0.7)
        c = v(e["at"]); h = (8 if k == "penetration" else 2) * IN
        add_cyl(bm, c - Vector((0, 0, h / 2)), c + Vector((0, 0, h / 2)), r, seg=20)
    elif k == "opening":
        if "points" in e:  # ceiling strip
            a, b = v(e["points"][0]), v(e["points"][1]); d = b - a
            n = Vector((-d.y, d.x, 0)).normalized() * e["width_in"] * IN / 2
            verts = [bm.verts.new(p) for p in (a - n, b - n, b + n, a + n)]
        else:      # chase face, vertical
            c = v(e["at"]); w = e["width_in"] * IN / 2; h = e["height_in"] * IN
            verts = [bm.verts.new(c + Vector(o)) for o in ((-w, 0, 0), (w, 0, 0), (w, 0, h), (-w, 0, h))]
        bm.faces.new(verts)
    elif k == "note":
        return None
    return bm


def build_scene(spec, label, mode, mult):
    coll = bpy.data.collections.new(label); bpy.context.scene.collection.children.link(coll)
    ctx = bpy.data.collections.new(label + "-context"); bpy.context.scene.collection.children.link(ctx)
    x0, y0, x1, y1 = FOOTPRINT_IN
    edge = mat("context-level", (0.45, 0.47, 0.50, 1))
    corners = [(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)]
    for lv, ft in spec["levels_ft"].items():
        if lv in ("P2",):
            continue
        z = (ft - 342.0) * 12
        bm = bmesh.new()
        for a, b in zip(corners, corners[1:]):
            add_cyl(bm, v((*a, z)), v((*b, z)), 1.5 * IN, seg=6)
        obj_from(bm, f"level-{lv}", edge, ctx, {"cie_type": "context", "cie_status": "assumed",
                                                "basis": f"grid 6-10 x A-H outline at {lv} {ft} ft (A3.11); not the slab edge"})
        txt = bpy.data.curves.new(f"label-{lv}", "FONT"); txt.body = f"{lv}  {ft:.2f} ft"; txt.size = 0.9
        t = bpy.data.objects.new(f"label-{lv}", txt); ctx.objects.link(t)
        t.location = v((x0 + 10, y0 + 10, z + 6)); t.data.materials.append(edge)
    counts = {}
    for e in spec["elements"]:
        bm = element_mesh(e, mult)
        if bm is None:
            continue
        counts[e["status"]] = counts.get(e["status"], 0) + 1
        if mode == "review":
            m = mat("status-" + e["status"], STATUS_COLORS[e["status"]], alpha=0.5 if e["kind"] == "opening" else 1)
        else:
            m = mat("sys-" + e.get("system", "x"), SYSTEM_COLORS.get(e.get("system"), (0.6, 0.6, 0.6, 1)),
                    alpha=0.5 if e["kind"] == "opening" else 1)
        obj_from(bm, e["id"], m, coll, {"cie_id": e["id"], "cie_type": e["kind"], "cie_status": e["status"],
                                        "cie_system": e.get("system"), "role": e.get("role"), "material": e.get("material"),
                                        "nominal_in": e.get("nominal_in"), "phase": e.get("phase"),
                                        "source": e.get("source"), "basis": e.get("basis")})
    return coll, counts


def ghost(spec):
    coll = bpy.data.collections.new("existing-ghost"); bpy.context.scene.collection.children.link(coll)
    m = mat("ghost", (0.55, 0.55, 0.58, 1), alpha=0.35)
    for e in spec["elements"]:
        if e["kind"] == "pipe":
            obj_from(element_mesh(e, DISPLAY_OD_MULT), "ghost-" + e["id"], m, coll, {"cie_type": "ghost"})


def camera(name, loc, rot_deg, ortho=None, lens=35):
    cam = bpy.data.cameras.new(name)
    if ortho:
        cam.type = "ORTHO"; cam.ortho_scale = ortho
    else:
        cam.lens = lens
    ob = bpy.data.objects.new(name, cam); bpy.context.scene.collection.objects.link(ob)
    ob.location = loc; ob.rotation_euler = [math.radians(a) for a in rot_deg]
    return ob


def lights():
    sun = bpy.data.lights.new("sun", "SUN"); sun.energy = 3.0
    ob = bpy.data.objects.new("sun", sun); bpy.context.scene.collection.objects.link(ob)
    ob.rotation_euler = (math.radians(50), math.radians(10), math.radians(35))


def render_views(name, spec, counts, samples):
    sc = bpy.context.scene
    sc.cycles.samples = samples
    sc.render.resolution_x, sc.render.resolution_y = 1600, 1000
    cx, cy, cz = 400 * IN, 345 * IN, 370 * IN  # model centre
    views = {
        "iso": camera("cam-iso", (cx + 26, cy - 26, cz + 20), (60, 0, 45), lens=32),
        "plan": camera("cam-plan", (cx, 326 * IN, 80), (0, 0, 0), ortho=54),
        "south": camera("cam-south", (cx, cy - 80, cz), (90, 0, 0), ortho=34),
        "east": camera("cam-east", (cx + 80, cy, cz), (90, 0, 90), ortho=34),
    }
    paths = []
    for vname, cam in views.items():
        sc.camera = cam
        path = OUT / f"{name}-{vname}.png"
        sc.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        from PIL import Image, ImageStat
        st = ImageStat.Stat(Image.open(path).convert("L"))
        assert st.stddev[0] > 3, f"blank render {path}"
        stamp_render(path, spec, counts)
        paths.append(path.name)
    return paths


def report(name, spec, counts, renders):
    res = spec.get("checks", [])
    ok = all(c["pass"] for c in res)
    md = [f"# {spec['project']}", "",
          f"**{'PASS' if ok else 'FAIL'}** — {sum(c['pass'] for c in res)}/{len(res)} checks" if res else
          "No document checks on this spec (proposed; see the existing spec).",
          *record_md(spec), "", "## Provenance",
          *[f"- {k}: {counts.get(k, 0)}" for k in ("confirmed", "provisional", "assumed")],
          "", "## Checks", *[f"- {'PASS' if c['pass'] else 'FAIL'} {c['check']}: expected {c['expected']}, "
                             f"got {c['actual']} ({c['source']})" for c in res],
          *conflicts_md(spec, []), "", "## Assumptions", *assumptions_md(spec), *review_md(spec),
          "", "## Renders", *[f"- `{r}`" for r in renders],
          "", f"Pipes in review renders are drawn at {DISPLAY_OD_MULT}x outside diameter for legibility."]
    (OUT / f"{name}-report.md").write_text("\n".join(md) + "\n")
    (OUT / f"{name}-report.json").write_text(json.dumps({"spec": name, "pass": ok, "checks": res, "counts": counts,
                                                          "renders": renders}, indent=1) + "\n")
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", default="both", choices=["existing", "proposed", "both"])
    ap.add_argument("--no-render", action="store_true")
    ap.add_argument("--samples", type=int, default=16)
    a = ap.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:])
    OUT.mkdir(parents=True, exist_ok=True)
    ok = True
    for name in (["existing", "proposed"] if a.spec == "both" else [a.spec]):
        spec = json.loads((HERE / f"risers-{name}.spec.json").read_text())
        reset(); lights()
        coll, counts = build_scene(spec, name, "review", DISPLAY_OD_MULT)
        if name == "proposed":  # existing system as a grey ghost for comparison
            ghost(json.loads((HERE / "risers-existing.spec.json").read_text()))
        renders = [] if a.no_render else render_views(name, spec, counts, a.samples)
        ok &= report(name, spec, counts, renders)
        # deliverable geometry at true outside diameter, colored by system
        reset(); lights()
        build_scene(spec, name, "system", 1.0)
        bpy.ops.wm.save_as_mainfile(filepath=str(OUT / f"highland-risers-{name}.blend"), compress=True)
        bpy.ops.export_scene.gltf(filepath=str(OUT / f"highland-risers-{name}.glb"), export_extras=True,
                                  export_apply=True)
        print(name, counts, "renders:", renders)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
