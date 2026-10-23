"""Blender model of the Building B under-slab re-pipe: slab with trench cut-outs, trenches to the
modelled invert profile, new ABS runs by size, stack/fixture risers and POC cleanouts.

Geometry comes only from meydenbauer-b.spec.json (prepare.py) and build/meydenbauer-b/takeoff.json
(takeoff.py); no PDF parsing here. Writes .blend, .glb and review renders to build/meydenbauer-b.

Usage: python projects/meydenbauer-b/build.py [--no-render] [--samples 48]
"""
import argparse, json, math, sys
from pathlib import Path

import bpy, bmesh
import numpy as np
from mathutils import Vector
from shapely.geometry import Polygon, box as sbox

HERE = Path(__file__).parent
ROOT = HERE.parent.parent
OUT = ROOT / "build" / "meydenbauer-b"
SPEC = json.loads((HERE / "meydenbauer-b.spec.json").read_text())
TAKE = json.loads((OUT / "takeoff.json").read_text())

FT = 0.3048
TIE_DEPTH = 3.5                     # base case POC invert, ft below finished floor (assumed; SOR 2.5-4.5)
SLOPE = TAKE["inputs"]["slope_ft_per_ft"]
BEDDING = TAKE["inputs"]["bedding_ft"]
SLAB = TAKE["inputs"]["slab_ft"]
OD_IN = {2: 2.375, 3: 3.5, 4: 4.5}
SLAB_BOX = (-1.0, 0.0, 161.5, 66.33)     # grid A-M x 1-6 rectangle, massing only (assumed)
STACK_UP_FT = 3.0                        # P1.01 vertical limits note: 36" min vertical exposure
FIXTURE_UP_FT = 0.6                      # stub through slab (illustrative)

STATUS = {"confirmed": (0.55, 0.72, 0.55), "provisional": (0.95, 0.80, 0.25), "assumed": (0.95, 0.45, 0.20)}
SIZE_COL = {2: (0.10, 0.45, 0.95), 3: (0.10, 0.70, 0.25), 4: (0.85, 0.12, 0.10)}


def P(x, y, z=0.0):
    """Plan feet (x south along the building, y west) and depth-up feet -> Blender metres.
    Blender +Y points east so a top view reads like the sheet (north at left)."""
    return Vector((x * FT, -y * FT, z * FT))


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    s = bpy.context.scene
    s.unit_settings.system = "IMPERIAL"; s.unit_settings.length_unit = "FEET"


def coll(name, parent=None):
    c = bpy.data.collections.new(name)
    (parent or bpy.context.scene.collection).children.link(c)
    return c


def material(name, rgb, rough=0.6, alpha=1.0, image=None):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; b = nt.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb, 1); b.inputs["Roughness"].default_value = rough
    if alpha < 1:
        b.inputs["Alpha"].default_value = alpha
        m.surface_render_method = "BLENDED" if hasattr(m, "surface_render_method") else m.blend_method
    if image:
        tex = nt.nodes.new("ShaderNodeTexImage"); tex.image = bpy.data.images.load(str(image))
        tex.interpolation = "Cubic"
        mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = "RGBA"; mix.blend_type = "MULTIPLY"
        mix.inputs["Factor"].default_value = 1.0
        mix.inputs["A"].default_value = (*rgb, 1)
        nt.links.new(tex.outputs["Color"], mix.inputs["B"])
        nt.links.new(mix.outputs["Result"], b.inputs["Base Color"])
    return m


def tag(obj, **props):
    for k, v in props.items():
        obj[k] = v if isinstance(v, (int, float, str)) else json.dumps(v)


def mesh_obj(name, bm, mat, c, **props):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); c.objects.link(ob)
    ob.data.materials.append(mat); tag(ob, **props)
    return ob


def ring_area(ring):
    return 0.5 * sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(ring, ring[1:] + ring[:1]))


def fill_rings(bm, rings, z_of):
    """Fill nested rings (first = outer) at heights z_of(x, y) with scanfill; returns faces."""
    edges = []
    for ring in rings:
        vs = [bm.verts.new(P(x, y, z_of(x, y))) for x, y in ring]
        edges += [bm.edges.new((a, b)) for a, b in zip(vs, vs[1:] + vs[:1])]
    res = bmesh.ops.triangle_fill(bm, use_beauty=True, use_dissolve=False, edges=edges)
    return res["geom"]


def clean(ring):
    ring = [tuple(p) for p in ring]
    if ring[0] == ring[-1]:
        ring = ring[:-1]
    out = []
    for p in ring:
        if not out or math.dist(p, out[-1]) > 1e-3:
            out.append(p)
    return out


def depth_samples(u):
    N = u["nodes"]; pts = []
    for e in u["edges"]:
        a, b = N[e["a"]], N[e["b"]]
        n = max(2, int(e["length_ft"] / 0.25) + 1)
        for t in np.linspace(0, 1, n):
            pts.append((a["xy_ft"][0] + (b["xy_ft"][0] - a["xy_ft"][0]) * t,
                        a["xy_ft"][1] + (b["xy_ft"][1] - a["xy_ft"][1]) * t,
                        TIE_DEPTH - SLOPE * (a["flow_ft"] + (b["flow_ft"] - a["flow_ft"]) * t)))
    return np.array(pts)


def build(mode):
    reset()
    root = bpy.context.scene.collection
    c_slab = coll("Existing slab (massing, assumed)")
    c_trench = coll("Trench S2 (2'-0\" typ + 3' pits)")
    c_pipe = coll("New ABS waste (P1.02)")
    c_riser = coll("Risers and POC cleanouts")
    c_label = coll("Labels")
    review = mode == "review"
    under = ROOT / SPEC["underlay"]["file"]

    m_slab = material("slab", (0.86, 0.86, 0.84), 0.9, image=under)
    m_soil = material("trench", STATUS["assumed"] if review else (0.50, 0.33, 0.18), 0.95, alpha=0.6)
    m_out = material("outside", (0.35, 0.45, 0.25), 0.95)
    m_pipe = {k: material(f"ABS {k}in", STATUS["provisional"] if review else SIZE_COL[k], 0.35) for k in OD_IN}
    m_riser = material("riser", STATUS["assumed"] if review else (0.08, 0.08, 0.08), 0.35)
    m_label = material("label", (0.05, 0.05, 0.05), 0.5)

    # --- slab: rectangle with every S2 trench footprint cut out; top face carries the P1.02 underlay
    x0, y0, x1, y1 = SLAB_BOX
    outer = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    inner = sbox(x0 + 0.05, y0 + 0.05, x1 - 0.05, y1 - 0.05)     # holes may not touch the slab edge
    holes = []
    for u in TAKE["units"]:
        for r in u["footprint_S2"]:
            g = Polygon(r).buffer(0).intersection(inner)
            holes += [clean(list(q.exterior.coords)) for q in getattr(g, "geoms", [g]) if q.area > 0.01]
    bm = bmesh.new()
    fill_rings(bm, [outer] + holes, lambda x, y: 0.0)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    uv = bm.loops.layers.uv.new("UVMap")
    bx0, by0, bx1, by1 = SPEC["underlay"]["ft_box"]
    for f in bm.faces:
        if f.normal.z < 0:
            f.normal_flip()
        for lp in f.loops:
            x, y = lp.vert.co.x / FT, -lp.vert.co.y / FT
            lp[uv].uv = ((x - bx0) / (bx1 - bx0), 1 - (y - by0) / (by1 - by0))
    slab = mesh_obj("Slab-on-grade (massing)", bm, m_slab, c_slab, status="assumed",
                    basis="extent = grid A-M x 1-6 rectangle; thickness not documented (4\" assumed)",
                    underlay="P1.02 Waste Plumbing Foundation Plan (KEAD), plotted scale verified")
    sol = slab.modifiers.new("thickness", "SOLIDIFY"); sol.thickness = SLAB * FT; sol.offset = -1

    # --- trenches: walls from slab top down to the local trench bottom (invert + bedding)
    for u in TAKE["units"]:
        su = next(s for s in SPEC["units"] if s["unit"] == u["unit"])
        samp = depth_samples(su)

        def bottom(x, y):
            i = int(((samp[:, 0] - x) ** 2 + (samp[:, 1] - y) ** 2).argmin())
            return -(samp[i, 2] + BEDDING)
        for j, ring in enumerate(u["footprint_S2"]):
            ring = clean(ring)
            if ring_area(ring) < 0:
                ring = ring[::-1]
            bm = bmesh.new()
            top = [bm.verts.new(P(x, y, 0.0)) for x, y in ring]
            bot = [bm.verts.new(P(x, y, bottom(x, y))) for x, y in ring]
            n = len(ring)
            for i in range(n):
                bm.faces.new((top[i], top[(i + 1) % n], bot[(i + 1) % n], bot[i]))
            bm.faces.new(bot[::-1])
            bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4])
            bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
            mesh_obj(f'{u["unit"]}-trench-{j}', bm, m_soil, c_trench, unit=u["unit"], status="assumed",
                     basis="plan = drawn route widened to 2'-0\" (10/P5.1) + 3'x3' pits (assumed); depth = POC invert 3.5 ft (assumed) less 1/4\"/ft + 4\" bedding (2/P5.0)")
        for j, ring in enumerate(u.get("outside_S2", [])):
            ring = clean(ring)
            bm = bmesh.new()
            fill_rings(bm, [ring], lambda x, y: 0.02)
            mesh_obj(f'{u["unit"]}-outside-{j}', bm, m_out, c_trench, unit=u["unit"], status="assumed",
                     basis="first 18\" from the POC lies outside the footprint (SOR) — landscape, not slab")

    # --- pipes: one bevelled curve per run, centreline = invert + OD/2
    for su in SPEC["units"]:
        N = su["nodes"]
        z = lambda k, nom: -(TIE_DEPTH - SLOPE * N[k]["flow_ft"]) + OD_IN[nom] / 24
        for i, e in enumerate(su["edges"]):
            nom = e["nominal_in"]
            cu = bpy.data.curves.new(f'{su["unit"]}-R{i:03d}', "CURVE"); cu.dimensions = "3D"
            cu.bevel_depth = OD_IN[nom] / 24 * FT; cu.bevel_resolution = 4; cu.use_fill_caps = True
            sp = cu.splines.new("POLY"); sp.points.add(1)
            for pt, k in zip(sp.points, (e["a"], e["b"])):
                pt.co = (*P(*N[k]["xy_ft"], z(k, nom)), 1)
            ob = bpy.data.objects.new(cu.name, cu); c_pipe.objects.link(ob)
            ob.data.materials.append(m_pipe[nom])
            tag(ob, unit=su["unit"], nominal_in=nom, od_in=OD_IN[nom], length_ft=round(e["length_ft"], 2),
                status="provisional", source="P1.02 linework (plan); elevation assumed",
                material="ABS Sch 40 solid wall (P0.2 15050.2, SOR)")
        # risers at ends + 2-way cleanout at POC
        for e in su["ends"]:
            if e["kind"] == "TEE":
                continue
            k = e["node"]; x, y = N[k]["xy_ft"]
            nom = 4 if e["kind"] == "STACK-4" else 3 if e["kind"] in ("STACK-3", "WC", "WB") else 2
            zb = -(TIE_DEPTH - SLOPE * N[k]["flow_ft"]) + OD_IN[nom] / 24
            up = STACK_UP_FT if e["kind"].startswith("STACK") else FIXTURE_UP_FT
            bpy.ops.mesh.primitive_cylinder_add(radius=OD_IN[nom] / 24 * FT, depth=(up - zb) * FT,
                                                location=P(x, y, (up + zb) / 2), vertices=20)
            ob = bpy.context.object; ob.name = f'{su["unit"]}-{e["kind"]}-{k}'
            for c in ob.users_collection:
                c.objects.unlink(ob)
            c_riser.objects.link(ob); ob.data.materials.append(m_riser)
            tag(ob, unit=su["unit"], kind=e["kind"], status="assumed",
                basis="riser height illustrative; stacks show the 36\" min exposure zone (P1.01 vertical limits note)",
                label_basis=e["basis"])
        x, y = su["tie_in"]["xy_ft"]
        bpy.ops.mesh.primitive_cylinder_add(radius=6.625 / 24 * FT, depth=(TIE_DEPTH + 0.3) * FT,
                                            location=P(x, y, (0.3 - TIE_DEPTH) / 2), vertices=24)
        ob = bpy.context.object; ob.name = f'{su["unit"]}-POC-2way-cleanout'
        for c in ob.users_collection:
            c.objects.unlink(ob)
        c_riser.objects.link(ob); ob.data.materials.append(m_riser)
        tag(ob, unit=su["unit"], status="provisional", basis="keynote 1 P1.02: 4\" to 6\" with 2-way surface cleanout; invert assumed")

    # --- labels
    for su, cx in zip(SPEC["units"], (20, 62, 100, 140)):
        bpy.ops.object.text_add(location=P(cx, 50, 0.05))
        t = bpy.context.object; t.data.body = su["unit"]; t.data.size = 5 * FT; t.data.align_x = "CENTER"
        t.data.extrude = 0.01
        for c in t.users_collection:
            c.objects.unlink(t)
        c_label.objects.link(t); t.data.materials.append(m_label)
    return c_label


def lights_and_world():
    s = bpy.context.scene
    w = bpy.data.worlds.new("world"); s.world = w; w.use_nodes = True
    w.node_tree.nodes["Background"].inputs["Color"].default_value = (0.92, 0.94, 0.97, 1)
    w.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.9
    sun = bpy.data.lights.new("sun", "SUN"); sun.energy = 3.0; sun.angle = math.radians(8)
    so = bpy.data.objects.new("sun", sun); s.collection.objects.link(so)
    so.rotation_euler = (math.radians(35), math.radians(10), math.radians(-30))


def camera(name, loc, look, ortho=None, lens=40):
    cam = bpy.data.cameras.new(name)
    if ortho:
        cam.type = "ORTHO"; cam.ortho_scale = ortho
    else:
        cam.lens = lens
    cam.clip_start = 0.05; cam.clip_end = 500
    ob = bpy.data.objects.new(name, cam); bpy.context.scene.collection.objects.link(ob)
    ob.location = loc
    d = (look - loc).normalized()
    ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    return ob


def render(cam, path, res, samples):
    s = bpy.context.scene
    s.camera = cam; s.render.engine = "CYCLES"; s.cycles.device = "CPU"; s.cycles.samples = samples
    s.cycles.use_denoising = True
    s.render.resolution_x, s.render.resolution_y = res
    s.render.film_transparent = False
    s.view_settings.view_transform = "Standard"
    s.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    caption(path)
    print("rendered", path.name)


def caption(path):
    """Legend + provenance note under every render (repo rule: assumed elements must be labelled)."""
    from PIL import Image, ImageDraw, ImageFont
    im = Image.open(path).convert("RGB"); w, h = im.size
    try:
        f = ImageFont.truetype("DejaVuSans.ttf", 19); fb = ImageFont.truetype("DejaVuSans-Bold.ttf", 20)
    except OSError:
        f = fb = ImageFont.load_default()
    note = ("Estimating/coordination aid, not a contract document. Plan from bid set P1.02 (scale verified); "
            "depths ASSUMED (POC invert 3.5 ft, 1/4\"/ft); stacks to be field verified.")
    probe = ImageDraw.Draw(im)
    lines, cur = [], ""
    for word in note.split(" "):
        if probe.textlength((cur + " " + word).strip(), font=f) > w - 32:
            lines.append(cur); cur = word
        else:
            cur = (cur + " " + word).strip()
    lines.append(cur)
    band = 76 + 26 * len(lines)
    out = Image.new("RGB", (w, h + band), (255, 255, 255)); out.paste(im, (0, 0))
    d = ImageDraw.Draw(out)
    review = path.name.startswith("review")
    d.text((16, h + 10), "101 Meydenbauer Bldg B — new under-slab waste (P1.02) and S2 trench footprint", font=fb, fill=(20, 20, 20))
    x = 16
    keys = ([("provisional: route plan position (P1.02)", STATUS["provisional"]), ("assumed: depth, trench, risers", STATUS["assumed"])]
            if review else [("4\" ABS", SIZE_COL[4]), ("3\" ABS", SIZE_COL[3]), ("2\" ABS", SIZE_COL[2]),
                            ("trench 2'-0\" + 3' pits", (0.50, 0.33, 0.18)), ("outside footprint (18\")", (0.35, 0.45, 0.25))])
    for label, rgb in keys:
        d.rectangle([x, h + 44, x + 22, h + 62], fill=tuple(int(c * 255) for c in rgb))
        d.text((x + 30, h + 42), label, font=f, fill=(30, 30, 30)); x += 40 + int(d.textlength(label, font=f))
    for i, line in enumerate(lines):
        d.text((16, h + 74 + 26 * i), line, font=f, fill=(150, 40, 20))
    out.save(path)


def views():
    mid = P(80, 33, 0)
    plan_t = camera("plan_top", P(80, 33, 200), P(80, 33.001, 0), ortho=172 * FT)
    iso = camera("iso_building", P(-30, 105, 85), P(76, 20, -3), lens=30)
    units = {}
    for su in SPEC["units"]:
        xs = [n["xy_ft"][0] for n in su["nodes"].values()]; ys = [n["xy_ft"][1] for n in su["nodes"].values()]
        cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
        S = max(max(xs) - min(xs), max(ys) - min(ys)) + 10       # frame the whole unit network
        units[su["unit"]] = camera(f"iso_{su['unit']}", P(cx - 0.55 * S, cy + 0.75 * S, 0.7 * S),
                                   P(cx, cy - 1, -2.5), lens=30)
    return plan_t, iso, units, mid


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-render", action="store_true")
    ap.add_argument("--samples", type=int, default=48)
    ap.add_argument("--only", default="")
    args = ap.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:])
    OUT.mkdir(parents=True, exist_ok=True)
    only = set(filter(None, args.only.split(",")))
    for mode in ("present", "review"):
        build(mode)
        lights_and_world()
        plan_t, iso, units, _ = views()
        checks = validate()
        if mode == "present":
            bpy.ops.file.pack_all()
            bpy.ops.wm.save_as_mainfile(filepath=str(OUT / "Meydenbauer-B-underslab.blend"))
            bpy.ops.export_scene.gltf(filepath=str(OUT / "Meydenbauer-B-underslab.glb"), export_extras=True,
                                      export_apply=True)
            (OUT / "model-checks.json").write_text(json.dumps(checks, indent=1))
        if args.no_render:
            continue
        jobs = [("plan", plan_t, (2400, 1100)), ("iso", iso, (1800, 1100))]
        if mode == "present":
            jobs += [(f"iso-{k}", c, (1500, 1000)) for k, c in units.items()]
        for key, cam, res in jobs:
            if only and key not in only:
                continue
            render(cam, OUT / f"{mode}-{key}.png", res, args.samples)


def validate():
    """Model-vs-spec checks: run count, total LF, size split, tie-in count, depth band."""
    errs = []
    pipes = [o for o in bpy.data.objects if o.type == "CURVE"]
    n_spec = sum(len(u["edges"]) for u in SPEC["units"])
    if len(pipes) != n_spec:
        errs.append(f"run count {len(pipes)} != spec {n_spec}")
    lf = sum(o["length_ft"] for o in pipes)
    if abs(lf - TAKE["totals"]["pipe_lf"]) > 0.05:
        errs.append(f"pipe LF {lf:.2f} != takeoff {TAKE['totals']['pipe_lf']:.2f}")
    model_lf = 0.0
    for o in pipes:
        a, b = (Vector(p.co[:3]) for p in o.data.splines[0].points)
        model_lf += math.hypot((b - a).x, (b - a).y) / FT
    if abs(model_lf - lf) > 0.1:
        errs.append(f"modelled plan length {model_lf:.2f} != tagged {lf:.2f}")
    pocs = [o for o in bpy.data.objects if o.name.endswith("POC-2way-cleanout")]
    if len(pocs) != 4:
        errs.append(f"{len(pocs)} POC cleanouts, expected 4")
    zs = [Vector(p.co[:3]).z / FT for o in pipes for p in o.data.splines[0].points]
    if not (-TIE_DEPTH - 0.01 < min(zs) and max(zs) < -0.9):
        errs.append(f"pipe centreline elevations {min(zs):.2f}..{max(zs):.2f} ft outside the expected band")
    result = {"ok": not errs, "errors": errs, "runs": len(pipes), "pipe_lf": round(lf, 2),
              "pipe_centreline_z_ft": [round(min(zs), 2), round(max(zs), 2)]}
    print("checks:", json.dumps(result))
    if errs:
        sys.exit(1)
    return result


if __name__ == "__main__":
    main()
