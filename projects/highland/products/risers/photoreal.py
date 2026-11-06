"""Photoreal work-sequence stills: the R1 Corridor 108 header, before, during and after a PEX-A repipe.

  python photoreal.py [--phases before,open,install,cutover,restore] [--samples 64] [--width 1280 --height 720]
                      [--device CPU|CUDA|OPTIX] [--save-blend]

Pipe geometry comes from risers-existing.spec.json and risers-proposed.spec.json, clipped to one corridor
bay, so the stills show the same routes the coordination model does. Everything else in the scene is
illustrative and assumed: corridor width (6 ft, A2.03 label; centered on the header), 8'-6" ceiling, 10 in
slab, finishes, doors, lights, hangers, floor protection and equipment. Replace the finishes from site photos
when they are in projects/highland/sources/ (see README).
Every still carries the "illustrative, not a contract document" strip.
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
from bmodels.record import stamp_render

HERE = Path(__file__).parent
OUT = Path(os.environ.get("BM_BUILD") or BUILD / "highland" / "risers") / "photoreal"
IN = 0.0254
PHASES = ["before", "open", "install", "cutover", "restore"]
CAPTION = {
    "before": "Corridor 108 today: the domestic-water header runs above this ceiling",
    "open": "Protect the floor, open a 24 in ceiling strip, expose the existing CPVC header",
    "install": "Hang the new PEX-A header alongside the live system",
    "cutover": "Test the new header, then cut over each stack branch during a scheduled shutdown",
    "restore": "Patch, tape and paint the ceiling; remove protection",
}

# Corridor bay (inches, model frame). All assumed except where noted.
HEADER_X = 735                       # traced header centreline (P2.03), provisional
WL, WR = HEADER_X - 36, HEADER_X + 36  # 6 ft corridor (A2.03 label), centred on the header: assumed
Y0, Y1 = 250, 640                    # bay shown; includes the C and D branch tees
FZ = (353.0 - 342.0) * 12            # R1 floor, A3.11
CZ = FZ + 102                        # 8'-6" ceiling: assumed
SZ = (363.25 - 342.0) * 12 - 10      # R2 slab soffit: 10 in slab assumed
OPEN_X = (HEADER_X + 5 - 12, HEADER_X + 5 + 12)  # ceiling strip, as the proposed spec
OPEN_Y = (300, 600)                   # length opened in this bay
CUT_Y = (382, 394)                    # existing header cut just north of the C branch tee at cutover


def v(x, y, z):
    return Vector((x * IN, y * IN, z * IN))


# ---------------------------------------------------------------- materials ---------------------
def principled(name, color, rough=0.5, metal=0.0, spec=0.5, coat=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    b.inputs["Specular IOR Level"].default_value = spec
    b.inputs["Coat Weight"].default_value = coat
    return m, b, m.node_tree


def bump(tree, bsdf, scale, strength, detail=8.0, distance=0.002, kind="noise"):
    n = tree.nodes.new("ShaderNodeTexNoise" if kind == "noise" else "ShaderNodeTexVoronoi")
    n.inputs["Scale"].default_value = scale
    if kind == "noise":
        n.inputs["Detail"].default_value = detail
    tc = tree.nodes.new("ShaderNodeTexCoord")
    tree.links.new(tc.outputs["Object"], n.inputs["Vector"])
    bp = tree.nodes.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = strength; bp.inputs["Distance"].default_value = distance
    tree.links.new(n.outputs["Fac" if kind == "noise" else "Distance"], bp.inputs["Height"])
    tree.links.new(bp.outputs["Normal"], bsdf.inputs["Normal"])
    return n


def mottle(tree, bsdf, c0, c1, scale):
    n = tree.nodes.new("ShaderNodeTexNoise"); n.inputs["Scale"].default_value = scale; n.inputs["Detail"].default_value = 6
    tc = tree.nodes.new("ShaderNodeTexCoord"); tree.links.new(tc.outputs["Object"], n.inputs["Vector"])
    r = tree.nodes.new("ShaderNodeValToRGB")
    r.color_ramp.elements[0].color = (*c0, 1); r.color_ramp.elements[1].color = (*c1, 1)
    tree.links.new(n.outputs["Fac"], r.inputs["Fac"]); tree.links.new(r.outputs["Color"], bsdf.inputs["Base Color"])


def materials():
    M = {}
    M["paint"], b, t = principled("wall paint (eggshell)", (0.80, 0.77, 0.72), rough=0.62); bump(t, b, 900, 0.04)
    M["ceiling"], b, t = principled("ceiling paint (flat)", (0.86, 0.86, 0.84), rough=0.85); bump(t, b, 700, 0.03)
    M["patch"], b, t = principled("ceiling patch (new paint)", (0.88, 0.88, 0.86), rough=0.8); bump(t, b, 700, 0.025)
    M["gyp_raw"], b, t = principled("gypsum board, taped", (0.83, 0.83, 0.80), rough=0.9); bump(t, b, 300, 0.05)
    M["gyp_core"], b, t = principled("gypsum core (cut edge)", (0.93, 0.92, 0.88), rough=0.97); bump(t, b, 2500, 0.3)
    M["concrete"], b, t = principled("concrete soffit", (0.52, 0.51, 0.49), rough=0.92)
    mottle(t, b, (0.42, 0.41, 0.40), (0.60, 0.59, 0.56), 40); bump(t, b, 120, 0.25)
    M["carpet"], b, t = principled("corridor carpet", (0.18, 0.20, 0.23), rough=0.95, spec=0.2)
    mottle(t, b, (0.13, 0.15, 0.18), (0.26, 0.27, 0.30), 180); bump(t, b, 1500, 0.6, distance=0.004)
    b.inputs["Sheen Weight"].default_value = 0.6
    M["base"], *_ = principled("rubber base", (0.07, 0.07, 0.07), rough=0.6)
    M["door"], b, t = principled("door, wood veneer", (0.42, 0.26, 0.14), rough=0.45, coat=0.2)
    w = t.nodes.new("ShaderNodeTexWave"); w.inputs["Scale"].default_value = 6; w.inputs["Distortion"].default_value = 8
    w.bands_direction = "Z"
    r = t.nodes.new("ShaderNodeValToRGB"); r.color_ramp.elements[0].color = (0.30, 0.17, 0.08, 1)
    r.color_ramp.elements[1].color = (0.52, 0.33, 0.18, 1)
    t.links.new(w.outputs["Fac"], r.inputs["Fac"]); t.links.new(r.outputs["Color"], b.inputs["Base Color"])
    M["frame"], *_ = principled("hollow metal frame, painted", (0.24, 0.24, 0.25), rough=0.4, metal=0.2)
    M["brass"], *_ = principled("brass", (0.80, 0.60, 0.32), rough=0.28, metal=1.0)
    M["cpvc"], b, t = principled("CPVC (existing)", (0.80, 0.70, 0.50), rough=0.32, spec=0.6)
    mottle(t, b, (0.74, 0.64, 0.45), (0.84, 0.75, 0.56), 30)
    M["cpvc_cap"], *_ = principled("CPVC cap (cut and capped)", (0.66, 0.55, 0.36), rough=0.3)
    M["pex_CW"], *_ = principled("PEX-A, blue", (0.03, 0.16, 0.62), rough=0.38, spec=0.6)
    M["pex_HW"], *_ = principled("PEX-A, red", (0.62, 0.03, 0.02), rough=0.38, spec=0.6)
    M["pex_HWC"], *_ = principled("PEX-A, white", (0.86, 0.86, 0.84), rough=0.38, spec=0.6)
    M["ring"], *_ = principled("expansion ring, white", (0.92, 0.92, 0.9), rough=0.5)
    M["galv"], b, t = principled("galvanized steel", (0.62, 0.64, 0.65), rough=0.42, metal=1.0)
    mottle(t, b, (0.55, 0.57, 0.58), (0.70, 0.71, 0.72), 60)
    M["firestop"], *_ = principled("firestop sealant, red", (0.55, 0.06, 0.05), rough=0.7)
    M["ramboard"], b, t = principled("floor protection board", (0.55, 0.42, 0.28), rough=0.9)
    mottle(t, b, (0.50, 0.38, 0.25), (0.60, 0.47, 0.32), 25)
    M["tape"], *_ = principled("painter's tape", (0.12, 0.35, 0.75), rough=0.7)
    M["ladder"], *_ = principled("fiberglass ladder", (0.85, 0.65, 0.05), rough=0.45)
    M["alu"], *_ = principled("aluminum", (0.8, 0.8, 0.82), rough=0.3, metal=1.0)
    M["black"], *_ = principled("black plastic", (0.03, 0.03, 0.03), rough=0.5)
    M["gauge"], *_ = principled("gauge face", (0.95, 0.95, 0.93), rough=0.3)
    for name, color, strength in (("sconce", (1.0, 0.86, 0.68), 1.2), ("worklight", (0.95, 0.97, 1.0), 12.0)):
        m = bpy.data.materials.new(name); m.use_nodes = True
        nodes = m.node_tree.nodes; nodes.clear()
        e = nodes.new("ShaderNodeEmission"); e.inputs["Color"].default_value = (*color, 1); e.inputs["Strength"].default_value = strength
        o = nodes.new("ShaderNodeOutputMaterial"); m.node_tree.links.new(e.outputs[0], o.inputs[0])
        M[name] = m
    return M


# ---------------------------------------------------------------- geometry ----------------------
class Scene:
    def __init__(self):
        self.objects = []  # (object, phases)

    def link(self, ob, phases):
        bpy.context.scene.collection.objects.link(ob)
        self.objects.append((ob, set(phases)))
        return ob

    def box(self, name, x0, y0, z0, x1, y1, z1, mat, phases=PHASES, bevel=0.0):
        bm = bmesh.new()
        g = bmesh.ops.create_cube(bm, size=1)
        bmesh.ops.scale(bm, vec=((x1 - x0) * IN, (y1 - y0) * IN, (z1 - z0) * IN), verts=g["verts"])
        bmesh.ops.translate(bm, vec=v((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2), verts=g["verts"])
        if bevel:
            bmesh.ops.bevel(bm, geom=bm.edges[:], offset=bevel * IN, segments=2, affect="EDGES")
        me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
        me.materials.append(mat)
        return self.link(bpy.data.objects.new(name, me), phases)

    def tube(self, name, pts, r, mat, phases=PHASES, fillet=0.0, res=10):
        pts = rounded(pts, fillet, r) if fillet else pts
        cu = bpy.data.curves.new(name, "CURVE"); cu.dimensions = "3D"
        cu.bevel_depth = r * IN; cu.bevel_resolution = res // 2; cu.use_fill_caps = True
        sp = cu.splines.new("POLY"); sp.points.add(len(pts) - 1)
        for p, q in zip(sp.points, pts):
            p.co = (*v(*q), 1)
        cu.materials.append(mat)
        ob = self.link(bpy.data.objects.new(name, cu), phases)
        return ob

    def cyl(self, name, a, b, r, mat, phases=PHASES, seg=24):
        a, b = v(*a), v(*b); d = b - a
        bm = bmesh.new()
        g = bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=r * IN, radius2=r * IN, depth=d.length)
        rot = d.normalized().to_track_quat("Z", "Y").to_matrix().to_4x4()
        bmesh.ops.transform(bm, matrix=Matrix.Translation((a + b) / 2) @ rot, verts=g["verts"])
        for f in bm.faces:
            f.smooth = True
        me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free(); me.materials.append(mat)
        return self.link(bpy.data.objects.new(name, me), phases)


def rounded(pts, R, r):
    """Replace interior corners with arcs (PEX is bent, not elbowed): bend radius R inches."""
    out = [pts[0]]
    for a, b, c in zip(pts, pts[1:], pts[2:]):
        A, B, C = Vector(a), Vector(b), Vector(c)
        u, w = (A - B), (C - B)
        if u.length < 1e-6 or w.length < 1e-6:
            continue
        ang = u.angle(w)
        if abs(ang - math.pi) < 1e-3:
            out.append(b); continue
        t = min(R / math.tan(ang / 2), u.length / 2, w.length / 2)
        p0 = B + u.normalized() * t; p1 = B + w.normalized() * t
        for k in range(9):
            s = k / 8
            out.append(tuple((1 - s) ** 2 * p0 + 2 * (1 - s) * s * B + s * s * p1))
    out.append(pts[-1])
    return out


def clip(points, x_rng, y_rng, cut=None):
    """Polyline pieces inside the bay; optionally remove a y interval (the cutover cut)."""
    def inside(p):
        return x_rng[0] <= p[0] <= x_rng[1] and y_rng[0] <= p[1] <= y_rng[1]
    samples = []
    for a, b in zip(points, points[1:]):
        n = max(2, int((Vector(b) - Vector(a)).length / 2))
        samples += [tuple(a[i] + (b[i] - a[i]) * k / n for i in range(3)) for k in range(n)]
    samples.append(tuple(points[-1]))
    pieces, cur = [], []
    for p in samples:
        ok = inside(p) and not (cut and cut[0] < p[1] < cut[1] and abs(p[0] - HEADER_X) < 12)
        if ok:
            cur.append(p)
        elif cur:
            pieces.append(cur); cur = []
    if cur:
        pieces.append(cur)
    return [simplify(c) for c in pieces if len(c) > 1]


def simplify(pts):
    out = [pts[0]]
    for p, q in zip(pts[1:], pts[2:]):
        d1 = Vector(p) - Vector(out[-1]); d2 = Vector(q) - Vector(p)
        if d1.length and d2.length and d1.normalized().dot(d2.normalized()) > 0.9999:
            continue
        out.append(p)
    out.append(pts[-1])
    return out


def od(nominal):  # CTS outside diameter (CPVC and PEX-A share CTS OD)
    return nominal + 0.125


# ---------------------------------------------------------------- build ------------------------
def corridor(S, M):
    S.box("floor-carpet", WL - 6, Y0 - 120, FZ - 2, WR + 6, Y1 + 60, FZ, M["carpet"])
    S.box("slab-R2", WL - 60, Y0 - 120, SZ, WR + 60, Y1 + 60, SZ + 10, M["concrete"])
    for side, (x0, x1) in {"W": (WL - 5, WL), "E": (WR, WR + 5)}.items():
        S.box(f"wall-{side}", x0, Y0 - 120, FZ, x1, Y1 + 60, CZ, M["paint"])
        S.box(f"wall-{side}-above", x0, Y0 - 120, CZ, x1, Y1 + 60, SZ, M["gyp_raw"])
        xb = x1 if side == "W" else x0 - 0.5
        S.box(f"base-{side}", xb, Y0 - 120, FZ, xb + 0.5, Y1 + 60, FZ + 4, M["base"])
    S.box("end-wall", WL - 5, Y1 + 60, FZ, WR + 5, Y1 + 65, SZ, M["paint"])
    for k, (side, y) in enumerate((("W", 330), ("E", 425), ("W", 525), ("E", 610))):
        x = WL if side == "W" else WR
        s = 1 if side == "W" else -1
        S.box(f"door-{k}", min(x, x + s * 0.75), y - 18, FZ + 0.5, max(x, x + s * 0.75), y + 18, FZ + 84, M["door"], bevel=0.1)
        for (a, b) in ((y - 20, y - 18), (y + 18, y + 20)):
            S.box(f"frame-{k}-{a}", min(x, x + s * 1.0), a, FZ, max(x, x + s * 1.0), b, FZ + 86, M["frame"], bevel=0.1)
        S.box(f"frame-{k}-head", min(x, x + s * 1.0), y - 20, FZ + 84, max(x, x + s * 1.0), y + 20, FZ + 86, M["frame"], bevel=0.1)
        S.cyl(f"lever-{k}", (x + s * 0.8, y + 14, FZ + 38), (x + s * 3.0, y + 14, FZ + 38), 0.35, M["brass"])
        S.cyl(f"lever-{k}-h", (x + s * 3.0, y + 14, FZ + 38), (x + s * 3.0, y + 9.5, FZ + 38), 0.35, M["brass"])
    # wall sconces (illustrative), one area light each
    for k, y in enumerate((330, 430, 530, 630)):
        side = "E" if k % 2 else "W"
        x = WR - 2.5 if side == "E" else WL + 2.5
        S.box(f"sconce-{k}", x - 2, y - 5, FZ + 64, x + 2, y + 5, FZ + 74, M["sconce"], bevel=0.3)
        L = bpy.data.lights.new(f"sconce-light-{k}", "AREA"); L.energy = 12; L.color = (1.0, 0.82, 0.62)
        L.shape = "RECTANGLE"; L.size = 4 * IN; L.size_y = 8 * IN
        ob = bpy.data.objects.new(L.name, L); ob.location = v(x, y, FZ + 69)
        ob.rotation_euler = (math.pi, 0, 0)  # up-light: washes the wall and ceiling
        S.link(ob, PHASES)
    # recessed downlights (illustrative), off-centre so they clear the opening strip
    for k, y in enumerate(range(270, Y1 + 60, 96)):
        x = WL + 14
        S.cyl(f"downlight-trim-{k}", (x, y, CZ - 0.05), (x, y, CZ + 0.2), 3.2, M["frame"])
        S.cyl(f"downlight-lens-{k}", (x, y, CZ - 0.1), (x, y, CZ - 0.05), 2.6, M["sconce"])
        L = bpy.data.lights.new(f"downlight-{k}", "AREA"); L.energy = 22; L.color = (1.0, 0.86, 0.70)
        L.shape = "DISK"; L.size = 5 * IN
        ob = bpy.data.objects.new(L.name, L); ob.location = v(x, y, CZ - 0.3)
        S.link(ob, PHASES)
    # ceiling: two side bands everywhere; the strip over the headers is removed while open
    S.box("ceiling-W", WL, Y0 - 120, CZ, OPEN_X[0], Y1 + 60, CZ + 0.625, M["ceiling"])
    S.box("ceiling-E", OPEN_X[1], Y0 - 120, CZ, WR, Y1 + 60, CZ + 0.625, M["ceiling"])
    S.box("ceiling-strip-S", OPEN_X[0], Y0 - 120, CZ, OPEN_X[1], OPEN_Y[0], CZ + 0.625, M["ceiling"])
    S.box("ceiling-strip-N", OPEN_X[0], OPEN_Y[1], CZ, OPEN_X[1], Y1 + 60, CZ + 0.625, M["ceiling"])
    S.box("ceiling-strip-original", OPEN_X[0], OPEN_Y[0], CZ, OPEN_X[1], OPEN_Y[1], CZ + 0.625, M["ceiling"], ["before"])
    S.box("ceiling-strip-patch", OPEN_X[0], OPEN_Y[0], CZ, OPEN_X[1], OPEN_Y[1], CZ + 0.625, M["patch"], ["restore"])
    for side, x in (("W", OPEN_X[0]), ("E", OPEN_X[1] - 0.05)):  # exposed cut edges of the board
        S.box(f"cut-edge-{side}", x, OPEN_Y[0], CZ, x + 0.05, OPEN_Y[1], CZ + 0.625, M["gyp_core"], ["open", "install", "cutover"])
    # ceiling framing above the board is not shown (type not established)


def pipes(S, M, existing, proposed):
    xr = (WL - 4, WR + 4)
    for e in existing["elements"]:
        if e["kind"] != "pipe" or not (e["id"].startswith(("header-", "stack-C-feed", "stack-D-feed"))):
            continue
        r = od(e["nominal_in"]) / 2
        for phases, cut in ((["before", "open", "install"], None), (["cutover", "restore"], CUT_Y)):
            for k, piece in enumerate(clip(e["points"], xr, (Y0 - 120, Y1 + 60), cut if e["id"].startswith("header") else None)):
                S.tube(f"ex-{e['id']}-{phases[0]}-{k}", piece, r, M["cpvc"], phases)
                for p in piece[1:-1]:  # socket fittings at elbows
                    S.cyl(f"ex-fit-{e['id']}-{p}", (p[0], p[1], p[2] - r * 1.3), (p[0], p[1], p[2] + r * 1.3), r * 1.25, M["cpvc"], phases)
                if cut and e["id"].startswith("header"):
                    for end in (piece[0], piece[-1]):
                        if CUT_Y[0] - 1 <= end[1] <= CUT_Y[1] + 1:
                            S.cyl(f"cap-{e['id']}-{end[1]}", (end[0], end[1] - 1.2, end[2]), (end[0], end[1] + 1.2, end[2]),
                                  r * 1.22, M["cpvc_cap"], phases)
        # hangers: clevis + rod to the slab every 48 in on the header
        if e["id"].startswith("header-"):
            x = e["points"][1][0]
            y = Y0 - 100
            while y < Y1 + 50:
                z = e["points"][1][2]
                S.cyl(f"rod-{e['id']}-{y}", (x, y, z + r), (x, y, SZ), 0.19, M["galv"], seg=8)
                S.cyl(f"clevis-{e['id']}-{y}", (x, y - 0.6, z - r - 0.2), (x, y + 0.6, z - r - 0.2), 0.3, M["galv"], seg=8)
                y += 48
    for e in proposed["elements"]:
        if e["kind"] != "pipe" or not e["id"].startswith(("new-header-", "new-stack-C-feed", "new-stack-D-feed")):
            continue
        r = od(e["nominal_in"]) / 2
        mat = M["pex_" + e["system"]]
        for k, piece in enumerate(clip(e["points"], xr, (Y0 - 120, Y1 + 60))):
            S.tube(f"pex-{e['id']}-{k}", piece, r, mat, ["install", "cutover", "restore"], fillet=6 * od(e["nominal_in"]))
        if e["id"].startswith("new-header-"):
            x = e["points"][1][0]; z = e["points"][1][2]
            # continuous half-round support channel under the PEX, clevis + rod at 48 in
            S.box(f"channel-{e['id']}", x - r * 0.9, Y0 - 120, z - r - 0.08, x + r * 0.9, Y1 + 60, z - r - 0.02, M["galv"],
                  ["install", "cutover", "restore"])
            y = Y0 - 76
            while y < Y1 + 50:
                S.cyl(f"nrod-{e['id']}-{y}", (x, y, z + r), (x, y, SZ), 0.19, M["galv"], ["install", "cutover", "restore"], seg=8)
                S.cyl(f"nclev-{e['id']}-{y}", (x, y - 0.6, z - r - 0.3), (x, y + 0.6, z - r - 0.3), 0.32, M["galv"],
                      ["install", "cutover", "restore"], seg=8)
                y += 48
    # ProPEX-style tees and rings at the new branch take-offs
    for e in proposed["elements"]:
        if e["kind"] == "pipe" and e["id"].startswith(("new-stack-C-feed", "new-stack-D-feed")):
            p = e["points"][0]; r = od(e["nominal_in"]) / 2
            if Y0 - 120 < p[1] < Y1 + 60:
                S.box(f"tee-{e['id']}", p[0] - r * 1.4, p[1] - r * 1.4, p[2] - r * 1.4, p[0] + r * 1.4, p[1] + r * 1.4,
                      p[2] + r * 1.4, M["brass"], ["install", "cutover", "restore"], bevel=0.15)
                for dy in (-r * 1.6, r * 1.6):
                    S.cyl(f"ring-{e['id']}-{dy}", (p[0], p[1] + dy - 0.3, p[2]), (p[0], p[1] + dy + 0.3, p[2]), r * 1.18,
                          M["ring"], ["install", "cutover", "restore"])
    # firestop at the corridor-wall penetrations of the new branches (rated corridor wall assumed)
    for e in proposed["elements"]:
        if e["kind"] == "pipe" and e["id"].startswith(("new-stack-C-feed", "new-stack-D-feed")):
            p = e["points"][0]; r = od(e["nominal_in"]) / 2
            if Y0 - 120 < p[1] < Y1 + 60:
                S.cyl(f"fs-{e['id']}", (WL + 0.2, p[1], p[2]), (WL - 0.4, p[1], p[2]), r + 0.6, M["firestop"],
                      ["install", "cutover", "restore"])


def work_kit(S, M):
    ph = ["open", "install", "cutover"]
    S.box("protection", WL + 0.5, Y0 - 100, FZ, WR - 0.5, Y1 + 40, FZ + 0.12, M["ramboard"], ph)
    for x in (WL + 0.5, WR - 2.5):
        S.box(f"tape-{x}", x, Y0 - 100, FZ + 0.12, x + 2, Y1 + 40, FZ + 0.16, M["tape"], ph)
    # A-frame ladder under the opening
    lx, ly, h = HEADER_X - 6, 395, 72
    for s in (-1, 1):
        for dx in (-9, 9):
            S.cyl(f"rail-{s}-{dx}", (lx + dx, ly + s * 16, FZ), (lx + dx * 0.8, ly + s * 2, FZ + h), 0.75, M["ladder"], ph, seg=10)
    for k in range(1, 5):
        z = FZ + k * h / 5; t = k / 5
        S.box(f"step-{k}", lx - 8, ly - 16 * (1 - t) - 1.5, z - 0.6, lx + 8, ly - 16 * (1 - t) + 1.5, z + 0.6, M["alu"], ph)
    S.box("ladder-top", lx - 9, ly - 3, FZ + h, lx + 9, ly + 3, FZ + h + 1.5, M["black"], ph)
    # LED work light on a tripod, aimed at the opening
    wx, wy = WR - 14, 360
    for a in (0, 120, 240):
        S.cyl(f"tripod-{a}", (wx + 10 * math.cos(math.radians(a)), wy + 10 * math.sin(math.radians(a)), FZ),
              (wx, wy, FZ + 54), 0.4, M["black"], ph, seg=8)
    S.box("worklight-head", wx - 5, wy - 1.5, FZ + 54, wx + 5, wy + 1.5, FZ + 61, M["black"], ph, bevel=0.3)
    S.box("worklight-lens", wx - 4.5, wy + 1.5, FZ + 54.5, wx + 4.5, wy + 1.6, FZ + 60.5, M["worklight"], ph)
    L = bpy.data.lights.new("worklight", "AREA"); L.energy = 160; L.color = (0.95, 0.97, 1.0); L.size = 9 * IN
    ob = bpy.data.objects.new("worklight", L); ob.location = v(wx, wy + 2, FZ + 58)
    ob.rotation_euler = (math.radians(150), math.radians(-12), 0)  # up into the opening
    S.link(ob, ph)
    # test gauge on the new header (cutover): a gate, not a passed test
    hx = HEADER_X + 10; z = (353.0 - 342.0) * 12 + 108
    S.cyl("gauge-stem", (hx, 430, z), (hx, 430, z - 5), 0.3, M["brass"], ["cutover"])
    S.cyl("gauge-body", (hx - 0.6, 430, z - 7.5), (hx + 0.6, 430, z - 7.5), 1.25, M["black"], ["cutover"])
    S.cyl("gauge-face", (hx - 0.65, 430, z - 7.5), (hx - 0.7, 430, z - 7.5), 1.1, M["gauge"], ["cutover"])


def camera_and_world(width, height):
    sc = bpy.context.scene
    cams = {}
    for name, loc, rot, lens in (("wide", (HEADER_X - 22, 222, FZ + 58), (90 + 11, 0, -6), 15),
                                 ("detail", (HEADER_X - 16, 300, FZ + 62), (90 + 42, 0, -12), 19)):
        cam = bpy.data.cameras.new(name); cam.lens = lens; cam.sensor_width = 36
        ob = bpy.data.objects.new(name, cam); sc.collection.objects.link(ob)
        ob.location = v(*loc); ob.rotation_euler = [math.radians(a) for a in rot]
        cams[name] = ob
    w = bpy.data.worlds.new("world"); sc.world = w; w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (0.02, 0.02, 0.025, 1)
    w.node_tree.nodes["Background"].inputs[1].default_value = 0.3
    sc.render.engine = "CYCLES"; sc.render.resolution_x = width; sc.render.resolution_y = height
    sc.view_settings.view_transform = "AgX"; sc.view_settings.look = "AgX - Medium High Contrast"
    sc.view_settings.exposure = -0.3
    sc.cycles.use_denoising = True; sc.cycles.denoiser = "OPENIMAGEDENOISE"
    sc.cycles.use_adaptive_sampling = True; sc.cycles.adaptive_threshold = 0.02
    sc.cycles.max_bounces = 8; sc.cycles.caustics_reflective = False; sc.cycles.caustics_refractive = False
    return cams


def configure_device(backend):
    sc = bpy.context.scene; sc.cycles.device = "CPU"
    if backend == "CPU":
        return
    prefs = bpy.context.preferences.addons["cycles"].preferences
    prefs.compute_device_type = backend; prefs.get_devices()
    used = [d.name for d in prefs.devices if setattr(d, "use", d.type == backend) or d.type == backend]
    if not used:
        raise SystemExit(f"No {backend} device found; refusing to fall back to CPU")
    sc.cycles.device = "GPU"; print("Cycles devices:", used, flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--phases", default=",".join(PHASES))
    ap.add_argument("--samples", type=int, default=64)
    ap.add_argument("--width", type=int, default=1280); ap.add_argument("--height", type=int, default=720)
    ap.add_argument("--device", default="CPU", choices=["CPU", "CUDA", "OPTIX"])
    ap.add_argument("--save-blend", action="store_true")
    ap.add_argument("--cameras", default="wide,detail")
    a = ap.parse_args()
    existing = json.loads((HERE / "risers-existing.spec.json").read_text())
    proposed = json.loads((HERE / "risers-proposed.spec.json").read_text())
    bpy.ops.wm.read_factory_settings(use_empty=True)
    M = materials(); S = Scene()
    corridor(S, M); pipes(S, M, existing, proposed); work_kit(S, M)
    cams = camera_and_world(a.width, a.height); configure_device(a.device)
    bpy.context.scene.cycles.samples = a.samples
    OUT.mkdir(parents=True, exist_ok=True)
    if a.save_blend:
        bpy.ops.wm.save_as_mainfile(filepath=str(OUT / "corridor-108-work-sequence.blend"), compress=True)
    spec = {**proposed, "project": "Highland | Corridor 108 header repipe (PEX-A), illustrative"}
    from PIL import Image, ImageDraw, ImageFont, ImageStat
    shots = [(ph, c) for ph in PHASES if ph in a.phases.split(",") for c in a.cameras.split(",")]
    for ph, cname in shots:
        for ob, phases in S.objects:
            ob.hide_render = ph not in phases
        bpy.context.scene.camera = cams[cname]
        path = OUT / f"{PHASES.index(ph) + 1:02d}-{ph}-{cname}.png"
        bpy.context.scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        assert ImageStat.Stat(Image.open(path).convert("L")).stddev[0] > 4, f"blank render {path}"
        im = Image.open(path).convert("RGB"); d = ImageDraw.Draw(im)
        try:
            f = ImageFont.truetype("DejaVuSans.ttf", max(16, a.height // 36))
        except OSError:
            f = ImageFont.load_default()
        text = f"{PHASES.index(ph) + 1}/5  {CAPTION[ph]}"
        pad = a.height // 60
        while d.textlength(text, font=f) > a.width - 6 * pad and f.size > 10:
            f = ImageFont.truetype("DejaVuSans.ttf", f.size - 1) if hasattr(f, "path") else f
            if not hasattr(f, "path"):
                break
        tw = d.textlength(text, font=f)
        d.rectangle([0, a.height - 3 * pad - f.size, tw + 4 * pad, a.height], fill=(15, 15, 18))
        d.text((2 * pad, a.height - 2 * pad - f.size), text, fill=(240, 240, 240), font=f)
        im.save(path)
        stamp_render(path, spec, {"assumed": sum(not ob.hide_render for ob, _ in S.objects)}, mode="presentation")
        print("rendered", path.name, flush=True)

if __name__ == "__main__":
    main()
