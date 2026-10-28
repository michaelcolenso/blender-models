"""House builder: walls from plan takeoff, openings, roof from hip/gable pieces, attic/gable ends.

Frame: inches. X from party-wall centerline (+ right unit), Y from rear wall face toward
the front. Blender: x = X, y = -Y (front faces -Y), z up, 1 unit = 1 m.
"""
import json, math
from pathlib import Path

import bpy, bmesh
from mathutils import Vector

IN = 0.0254
SOLVER = "MANIFOLD"


def P(X, Y, Z=0.0):
    return Vector((X * IN, -Y * IN, Z * IN))


def _link(o, coll):
    for c in o.users_collection:
        c.objects.unlink(o)
    coll.objects.link(o)
    return o


def mesh_from_bm(name, bm, coll):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); coll.objects.link(o)
    return o


def prism_from_rings(name, rings, z0, z1, coll):
    """Extrude polygon rings (outer + holes, even-odd) between z0 and z1 via a filled curve."""
    cu = bpy.data.curves.new(name, "CURVE"); cu.dimensions = "2D"; cu.fill_mode = "BOTH"
    for ring in rings:
        sp = cu.splines.new("POLY"); sp.points.add(len(ring) - 1)
        for i, (X, Y) in enumerate(ring):
            sp.points[i].co = (X * IN, -Y * IN, 0, 1)
        sp.use_cyclic_u = True
    cu.extrude = (z1 - z0) * IN / 2
    o = bpy.data.objects.new(name, cu); coll.objects.link(o)
    o.location.z = (z0 + z1) / 2 * IN
    bpy.context.view_layer.objects.active = o
    for ob in bpy.context.selected_objects:
        ob.select_set(False)
    o.select_set(True)
    bpy.ops.object.convert(target="MESH")
    o = bpy.context.object
    bm = bmesh.new(); bm.from_mesh(o.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(o.data); bm.free()
    return o


def box_obj(name, x0, y0, z0, x1, y1, z1, coll):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1)
    for v in bm.verts:
        v.co = Vector(((x0 if v.co.x < 0 else x1) * IN, -(y0 if v.co.y < 0 else y1) * IN,
                       (z0 if v.co.z < 0 else z1) * IN))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return mesh_from_bm(name, bm, coll)


def roof_piece(name, p, z_eave, z_bottom, dz, coll, grow=0.0):
    """Convex solid of one hip or gable piece. Rect in feet (X0,Y0,X1,Y1); pitch rise/12.
    dz shifts the roof surface vertically (inches); grow shrinks(-)/grows the rect (inches)."""
    X0, Y0, X1, Y1 = [v * 12 for v in p["rect"]]
    X0 -= grow; Y0 -= grow; X1 += grow; Y1 += grow
    if grow < 0 and p["kind"] == "gable":
        # inner (cutting) solid runs 24 in past both gable ends so the shell stays open there;
        # the vertical gable-end wall comes from the attic fill at the wall plane
        if p["ridge"] == "x":
            X0 -= 24 - grow; X1 += 24 - grow
        else:
            Y0 -= 24 - grow; Y1 += 24 - grow
    r = p["pitch"] / 12.0
    ze = z_eave + dz + (-grow * r if grow < 0 else 0)
    W, D = X1 - X0, Y1 - Y0
    pts = [(X0, Y0), (X1, Y0), (X1, Y1), (X0, Y1)]
    verts = [P(x, y, z_bottom) for x, y in pts] + [P(x, y, ze) for x, y in pts]
    if p["kind"] == "hip":
        if W >= D:
            h = r * D / 2; yc = (Y0 + Y1) / 2
            ridge = [(X0 + D / 2, yc), (X1 - D / 2, yc)]
        else:
            h = r * W / 2; xc = (X0 + X1) / 2
            ridge = [(xc, Y0 + W / 2), (xc, Y1 - W / 2)]
    else:  # gable: ridge along 'ridge' axis over full length
        if p["ridge"] == "x":
            h = r * D / 2; yc = (Y0 + Y1) / 2; ridge = [(X0, yc), (X1, yc)]
        else:
            h = r * W / 2; xc = (X0 + X1) / 2; ridge = [(xc, Y0), (xc, Y1)]
    verts += [P(x, y, ze + h) for x, y in ridge]
    bm = bmesh.new()
    for v in verts:
        bm.verts.new(v)
    bmesh.ops.convex_hull(bm, input=bm.verts)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return mesh_from_bm(name, bm, coll), ze + h


def set_mat(o, m):
    """Single-material assignment that survives boolean-created empty slots."""
    o.data.materials.clear(); o.data.materials.append(m)
    for poly in o.data.polygons:
        poly.material_index = 0


def boolean(target, cutter, op):
    m = target.modifiers.new("b", "BOOLEAN"); m.operation = op; m.object = cutter; m.solver = SOLVER
    bpy.context.view_layer.objects.active = target
    bpy.ops.object.modifier_apply(modifier=m.name)


def union_all(name, objs, coll):
    base = objs[0]; base.name = name
    for o in objs[1:]:
        boolean(base, o, "UNION"); bpy.data.objects.remove(o)
    return base


def mirror_pieces(pieces):
    out = []
    for p in pieces:
        out.append(p)
        if p.get("mirror"):
            X0, Y0, X1, Y1 = p["rect"]; q = dict(p); q["rect"] = [-X1, Y0, -X0, Y1]; q["id"] = p["id"] + "_L"
            out.append(q)
    return out


def mirror_openings(ops):
    out = []
    for o in ops:
        out.append(o)
        if o.get("mirror", True):
            q = dict(o); q["x0"], q["x1"] = -o["x1"], -o["x0"]; q["id"] = o["id"] + "_L"
            if o["axis"] == "y":
                q["face"] = -o.get("face", 1)
            out.append(q)
    return out


def build(el, spec_dir, material, coll_for):
    """Returns list of (meta dict, object)."""
    built = []
    tk = json.loads((spec_dir / el["takeoff"]).read_text())
    H = el["plate_height_in"]
    meta = lambda i, trade, status, src, **k: dict(id=i, trade=trade, status=status, source=src, **k)

    # --- walls: rectangle decomposition of the plan wall mask (right half + mirror) ---
    # Boolean-free: openings are cut by splitting boxes, so the result is exact and robust.
    wc = coll_for("walls")
    ops = mirror_openings(el["openings"])
    WT = el.get("ext_wall_t_in", 6.5)
    boxes = []
    for x0, y0, x1, y1 in tk["wall_rects"]:
        boxes.append([x0, y0, 0, x1, y1, H]); boxes.append([-x1, y0, 0, -x0, y1, H])
    for o in ops:  # infill across each opening (door/garage gaps are true gaps in the mask)
        if o["axis"] == "x":
            yc = (o["y0"] + o["y1"]) / 2; boxes.append([o["x0"] - 1, yc - WT / 2, 0, o["x1"] + 1, yc + WT / 2, H])
        else:
            xc = (o["x0"] + o["x1"]) / 2; boxes.append([xc - WT / 2, o["y0"] - 1, 0, xc + WT / 2, o["y1"] + 1, H])
    for xw in el.get("extra_walls", []):
        for sgn in ((1, -1) if xw.get("mirror", True) else (1,)):
            x0, x1 = sorted((xw["x0"] * sgn, xw["x1"] * sgn)); boxes.append([x0, xw["y0"], 0, x1, xw["y1"], H])

    def minus(bx, c):
        if not all(bx[i] < c[i + 3] and c[i] < bx[i + 3] for i in range(3)):
            return [bx]
        out, b = [], list(bx)
        for i in range(3):  # peel slabs outside the cutter along x, then y, then z
            if b[i] < c[i]:
                p = list(b); p[i + 3] = c[i]; out.append(p); b[i] = c[i]
            if b[i + 3] > c[i + 3]:
                p = list(b); p[i] = c[i + 3]; out.append(p); b[i + 3] = c[i + 3]
        return out  # remaining b is inside the cutter -> dropped

    for o in ops:
        t = 10
        if o["axis"] == "x":
            yc = (o["y0"] + o["y1"]) / 2; c = [o["x0"], yc - t, o["sill"], o["x1"], yc + t, o["head"]]
        else:
            xc = (o["x0"] + o["x1"]) / 2; c = [xc - t, o["y0"], o["sill"], xc + t, o["y1"], o["head"]]
        boxes = [q for bx in boxes for q in minus(bx, c)]
    bm = bmesh.new()
    for x0, y0, z0, x1, y1, z1 in boxes:
        if min(x1 - x0, y1 - y0, z1 - z0) <= 1e-6:
            continue
        g = bmesh.ops.create_cube(bm, size=1)
        for v in g["verts"]:
            v.co = Vector(((x0 if v.co.x < 0 else x1) * IN, -(y0 if v.co.y < 0 else y1) * IN,
                           (z0 if v.co.z < 0 else z1) * IN))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    walls = mesh_from_bm("walls", bm, wc)
    set_mat(walls, material("siding"))
    built.append((meta("walls", "walls", "provisional", el["walls_source"], boxes=len(boxes)), walls))

    # --- windows / doors / garage doors (inserts) ---
    oc = coll_for("openings")
    for o in ops:
        ax = o["axis"]; kind = o["kind"]
        x0, x1, y0, y1 = o["x0"], o["x1"], o["y0"], o["y1"]
        if ax == "x":
            yc = (y0 + y1) / 2; a0, a1 = x0, x1
        else:
            xc = (x0 + x1) / 2; a0, a1 = y0, y1
        def slab(nm, b0, b1, z0, z1, off, th, mat):
            if ax == "x":
                ob = box_obj(nm, b0, yc + off - th / 2, z0, b1, yc + off + th / 2, z1, oc)
            else:
                ob = box_obj(nm, xc + off - th / 2, b0, z0, xc + off + th / 2, b1, z1, oc)
            set_mat(ob, material(mat)); return ob
        f = 2.0  # frame width in
        parts = []
        if kind in ("window", "door"):
            parts.append(slab(o["id"] + "_glass", a0, a1, o["sill"], o["head"], 0, 0.5,
                              "glass" if kind == "window" or o.get("glazed") else "door"))
            # frame: head, sill, jambs, mullions
            parts.append(slab(o["id"] + "_fh", a0, a1, o["head"] - f, o["head"], 0, 3, "trim"))
            parts.append(slab(o["id"] + "_fs", a0, a1, o["sill"], o["sill"] + f, 0, 3, "trim"))
            n = max(1, round((a1 - a0) / o.get("unit_w", 32)))
            for k in range(n + 1):
                c = a0 + (a1 - a0) * k / n
                parts.append(slab(f"{o['id']}_m{k}", max(a0, c - f / 2), min(a1, c + f / 2), o["sill"], o["head"], 0, 3, "trim"))
        elif kind == "garage":
            parts.append(slab(o["id"] + "_panel", a0, a1, o["sill"], o["head"], 0, 2, "garage_door"))
            for k in range(1, 4):
                z = o["sill"] + (o["head"] - o["sill"]) * k / 4
                parts.append(slab(f"{o['id']}_seam{k}", a0, a1, z - 0.3, z + 0.3, -0.8 if ax == "x" else 0.8, 0.8, "trim"))
        # exterior trim casing around opening (1x4 / 1x6 fiber-cement trim per AH500 notes)
        # placed on the exterior face side; face side determined by 'face' (+1/-1 in Y or X)
        s = o.get("face", 1); off = s * (o.get("wall_t", 6) / 2 + 0.5)
        tw = 5.5 if kind != "garage" else 3.5
        parts.append(slab(o["id"] + "_ct", a0 - tw, a1 + tw, o["head"], o["head"] + tw, off, 1, "trim"))
        parts.append(slab(o["id"] + "_cl", a0 - tw, a0, o["sill"] - (tw if kind == "window" else 0), o["head"], off, 1, "trim"))
        parts.append(slab(o["id"] + "_cr", a1, a1 + tw, o["sill"] - (tw if kind == "window" else 0), o["head"], off, 1, "trim"))
        if kind == "window":
            parts.append(slab(o["id"] + "_cs", a0 - tw, a1 + tw, o["sill"] - tw, o["sill"], off, 1.5, "trim"))
        for ob in parts:
            built.append((meta(ob.name, "openings", o.get("status", "provisional"), o.get("source", el["walls_source"]),
                               basis=o.get("basis")), ob))

    # --- slab ---
    fp = tk["footprint"]
    sc = coll_for("foundation")
    for side, ring in (("R", fp), ("L", [(-x, y) for x, y in reversed(fp)])):
        s_ = prism_from_rings("slab_" + side, [ring], -el.get("slab_t_in", 6), 0, sc)
        set_mat(s_, material("concrete"))
        built.append((meta(s_.name, "foundation", "provisional", el["walls_source"]), s_))

    # --- roof ---
    rc = coll_for("roof")
    pieces = mirror_pieces(el["roof"]["pieces"])
    ze, soffit, t = el["roof"]["eave_surface_z_in"], el["roof"]["soffit_z_in"], el["roof"]["thickness_in"]
    outer, inner, ridges = [], [], {}
    for p in pieces:
        o1, ztop = roof_piece("ro_" + p["id"], p, ze, soffit, 0, rc); outer.append(o1); ridges[p["id"]] = ztop
        o2, _ = roof_piece("ri_" + p["id"], p, ze, soffit - 200, -t, rc, grow=-1.5); inner.append(o2)
    ro = union_all("roof", outer, rc)
    ri = union_all("roof_inner", inner, rc)
    # attic / gable-end walls: inner roof mass inside the wall footprint, above the plate
    fprings = [fp, [(-x, y) for x, y in reversed(fp)]]
    att = []
    for i, ring in enumerate(fprings):
        a = prism_from_rings(f"attic_{i}", [ring], H - 0.5, 400, rc)
        boolean(a, ri, "INTERSECT"); att.append(a)
    boolean(ro, ri, "DIFFERENCE"); bpy.data.objects.remove(ri)
    set_mat(ro, material("shingles"))
    built.append((meta("roof", "roof", "provisional", el["roof"]["source"]), ro))
    for a in att:
        set_mat(a, material("gable_panel"))
        built.append((meta(a.name, "roof", "provisional", el["roof"]["source"]), a))
    # soffit
    sof = [box_obj("sof_" + p["id"], *(v * 12 for v in p["rect"][:2]), soffit - 1,
                   *(v * 12 for v in p["rect"][2:]), soffit, rc) for p in pieces]
    so = union_all("soffit", sof, rc); set_mat(so, material("trim"))
    built.append((meta("soffit", "roof", "provisional", el["roof"]["source"]), so))
    return built, ridges
