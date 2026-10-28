"""Room builder: photo-derived interior (shell + furniture + lighting) from a YAML spec.

Usage:
    uv run bm room specs/room-living-kitchen.yaml [--out build/] [--no-render] [--quality draft|final]

Writes <out>/<name>/: .blend, .glb, review renders colored by provenance, realistic renders
(night = photo lighting, day = inspection lighting, hero views), photo-match camera render, report.md/json.
Exits 1 if validation or any check fails.  Spec units are inches; Blender stores meters.
"""
import argparse, json, math, sys
from pathlib import Path

import bpy
import bmesh
import yaml
from mathutils import Matrix, Vector

IN = 0.0254
from bmodels.spec import FACE_ROT, STATUS_COLORS, validate_room as validate  # noqa: F401  (validate used by main)

# ----------------------------------------------------------------------------- materials
_M = {}


def _bsdf(m):
    m.use_nodes = True
    return m.node_tree.nodes["Principled BSDF"]


def mat(key, color=(0.5, 0.5, 0.5), rough=0.6, metal=0.0, emit=None, emit_strength=0.0, spec=0.5, alpha=None):
    if key in _M:
        return _M[key]
    m = bpy.data.materials.new(key)
    b = _bsdf(m)
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    b.inputs["Specular IOR Level"].default_value = spec
    if emit:
        b.inputs["Emission Color"].default_value = (*emit, 1)
        b.inputs["Emission Strength"].default_value = emit_strength
    m.diffuse_color = (*color, 1)
    _M[key] = m
    return m


def _tex_chain(m, build):
    nt = m.node_tree
    return nt, nt.nodes, nt.nodes["Principled BSDF"]


def planks_mat():
    m = mat("floor_lvp", (0.20, 0.17, 0.15), 0.38)
    nt, N, b = _tex_chain(m, None)
    tc = N.new("ShaderNodeTexCoord")
    mp = N.new("ShaderNodeMapping"); mp.inputs["Scale"].default_value = (1 / (48 * IN), 1 / (7.25 * IN), 1)
    br = N.new("ShaderNodeTexBrick"); br.inputs["Scale"].default_value = 1.0
    br.inputs["Mortar Size"].default_value = 0.012; br.inputs["Mortar Smooth"].default_value = 0.1
    br.inputs["Bias"].default_value = 0.0; br.inputs["Brick Width"].default_value = 1.0; br.inputs["Row Height"].default_value = 1.0
    br.offset = 0.37; br.offset_frequency = 1; br.squash = 1.0
    br.inputs["Color1"].default_value = (0.24, 0.20, 0.17, 1)
    br.inputs["Color2"].default_value = (0.17, 0.145, 0.125, 1)
    br.inputs["Mortar"].default_value = (0.05, 0.045, 0.04, 1)
    ns = N.new("ShaderNodeTexNoise"); ns.inputs["Scale"].default_value = 60; ns.inputs["Detail"].default_value = 6
    mix = N.new("ShaderNodeMix"); mix.data_type = "RGBA"; mix.blend_type = "MULTIPLY"; mix.inputs[0].default_value = 0.35
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    nt.links.new(mp.outputs["Vector"], br.inputs["Vector"])
    nt.links.new(tc.outputs["Object"], ns.inputs["Vector"])
    nt.links.new(br.outputs["Color"], mix.inputs[6])
    nt.links.new(ns.outputs["Color"], mix.inputs[7])
    nt.links.new(mix.outputs[2], b.inputs["Base Color"])
    bump = N.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.15; bump.inputs["Distance"].default_value = 0.002
    nt.links.new(br.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    return m


def popcorn_mat():
    m = mat("ceiling_popcorn", (0.74, 0.72, 0.67), 0.95)
    nt, N, b = _tex_chain(m, None)
    tc = N.new("ShaderNodeTexCoord")
    v = N.new("ShaderNodeTexVoronoi"); v.inputs["Scale"].default_value = 220
    ns = N.new("ShaderNodeTexNoise"); ns.inputs["Scale"].default_value = 90; ns.inputs["Detail"].default_value = 8
    mix = N.new("ShaderNodeMix"); mix.data_type = "FLOAT"; mix.inputs[0].default_value = 0.5
    nt.links.new(tc.outputs["Object"], v.inputs["Vector"]); nt.links.new(tc.outputs["Object"], ns.inputs["Vector"])
    nt.links.new(v.outputs["Distance"], mix.inputs[2]); nt.links.new(ns.outputs["Fac"], mix.inputs[3])
    bump = N.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.3; bump.inputs["Distance"].default_value = 0.002
    nt.links.new(mix.outputs[0], bump.inputs["Height"]); nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    return m


def marble_mat():
    m = mat("marble", (0.86, 0.85, 0.82), 0.12)
    nt, N, b = _tex_chain(m, None)
    tc = N.new("ShaderNodeTexCoord")
    w = N.new("ShaderNodeTexWave"); w.inputs["Scale"].default_value = 5; w.inputs["Distortion"].default_value = 9; w.inputs["Detail"].default_value = 4
    ramp = N.new("ShaderNodeValToRGB"); ramp.color_ramp.elements[0].color = (0.62, 0.62, 0.62, 1); ramp.color_ramp.elements[1].color = (0.93, 0.92, 0.90, 1)
    nt.links.new(tc.outputs["Object"], w.inputs["Vector"]); nt.links.new(w.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], b.inputs["Base Color"])
    return m


def rug_mat():
    m = mat("rug", (0.55, 0.57, 0.60), 0.95)
    nt, N, b = _tex_chain(m, None)
    tc = N.new("ShaderNodeTexCoord")
    ns = N.new("ShaderNodeTexNoise"); ns.inputs["Scale"].default_value = 4; ns.inputs["Detail"].default_value = 3; ns.inputs["Distortion"].default_value = 1.2
    ramp = N.new("ShaderNodeValToRGB"); ramp.color_ramp.elements[0].color = (0.30, 0.34, 0.40, 1); ramp.color_ramp.elements[1].color = (0.70, 0.70, 0.68, 1)
    nt.links.new(tc.outputs["Object"], ns.inputs["Vector"]); nt.links.new(ns.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], b.inputs["Base Color"])
    return m


def tv_screen_mat():
    m = mat("tv_screen", (0.02, 0.02, 0.03), 0.2)
    nt, N, b = _tex_chain(m, None)
    tc = N.new("ShaderNodeTexCoord")
    g = N.new("ShaderNodeTexGradient"); g.gradient_type = "SPHERICAL"
    mp = N.new("ShaderNodeMapping"); mp.inputs["Location"].default_value = (0.5, 0.5, 0); mp.inputs["Scale"].default_value = (1, 1, 1)
    ramp = N.new("ShaderNodeValToRGB"); ramp.color_ramp.elements[0].color = (0.55, 0.68, 0.95, 1); ramp.color_ramp.elements[1].color = (0.30, 0.40, 0.75, 1)
    nt.links.new(tc.outputs["UV"], mp.inputs["Vector"]); nt.links.new(mp.outputs["Vector"], g.inputs["Vector"])
    nt.links.new(g.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], b.inputs["Emission Color"]); b.inputs["Emission Strength"].default_value = 1.1
    b.inputs["Base Color"].default_value = (0, 0, 0, 1)
    return m


def all_mats():
    mat("wall", (0.62, 0.60, 0.56), 0.9)
    mat("trim", (0.88, 0.87, 0.84), 0.5)
    planks_mat(); popcorn_mat(); marble_mat(); rug_mat(); tv_screen_mat()
    mat("leather", (0.075, 0.075, 0.07), 0.38, spec=0.6)
    mat("fabric_gray", (0.22, 0.22, 0.23), 0.95)
    mat("fabric_light", (0.50, 0.48, 0.45), 0.95)
    mat("fabric_cream", (0.72, 0.68, 0.60), 0.95)
    mat("fabric_blk", (0.015, 0.015, 0.015), 0.95)
    mat("wood_dark", (0.045, 0.04, 0.035), 0.5)
    mat("wood_cab", (0.20, 0.12, 0.08), 0.5)
    mat("wood_legs", (0.18, 0.11, 0.07), 0.55)
    mat("quartz", (0.88, 0.88, 0.86), 0.2)
    mat("stainless", (0.55, 0.56, 0.58), 0.32, metal=1.0)
    mat("blk_steel", (0.07, 0.07, 0.075), 0.3, metal=0.9)
    mat("glass_blk", (0.01, 0.01, 0.012), 0.08)
    mat("gold", (0.75, 0.55, 0.25), 0.25, metal=1.0)
    mat("pot_blk", (0.015, 0.015, 0.015), 0.5)
    mat("leaf", (0.035, 0.20, 0.06), 0.45)
    mat("stem", (0.05, 0.18, 0.05), 0.6)
    mat("carpet_gray", (0.42, 0.42, 0.43), 1.0)
    mat("basket", (0.55, 0.30, 0.10), 0.9)
    mat("canvas", (0.62, 0.60, 0.58), 0.8)
    mat("art_dark", (0.06, 0.06, 0.06), 0.5)
    mat("art_light", (0.70, 0.69, 0.66), 0.7)
    mat("frame_blk", (0.02, 0.02, 0.02), 0.4)
    mat("bulb", (1.0, 0.85, 0.55), 0.2, emit=(1.0, 0.75, 0.40), emit_strength=6.0)
    mat("lampshade", (0.9, 0.78, 0.55), 0.8, emit=(1.0, 0.72, 0.38), emit_strength=9.0)
    mat("undercab", (1, 0.8, 0.5), 0.5, emit=(1.0, 0.75, 0.4), emit_strength=8.0)
    mat("burner", (0.02, 0.02, 0.02), 0.5)
    mat("magnet", (0.85, 0.80, 0.70), 0.6)
    mat("paper", (0.9, 0.9, 0.88), 0.7)
    mat("wire", (0.02, 0.02, 0.02), 0.5)
    mat("plastic_wht", (0.85, 0.85, 0.85), 0.5)
    mat("door", (0.80, 0.78, 0.74), 0.55)
    mat("hall_dark", (0.05, 0.05, 0.05), 0.9)
    mat("orange", (0.8, 0.35, 0.05), 0.6)
    mat("book1", (0.6, 0.55, 0.45), 0.7)
    mat("book2", (0.15, 0.2, 0.3), 0.7)


# ----------------------------------------------------------------------------- mesh helpers
class Ctx:
    sc = None
    spec = None
    groups = None
    colls = {}
    built = []   # (name, obj, item_id, group)
    cur_item = None
    cur_group = None


def coll(name):
    if name not in Ctx.colls:
        c = bpy.data.collections.new(name)
        Ctx.sc.collection.children.link(c)
        Ctx.colls[name] = c
    return Ctx.colls[name]


def _finish(bm, name, loc, rot, material, smooth=False, group=None, tag=None):
    bmesh.ops.scale(bm, vec=(IN, IN, IN), verts=bm.verts)
    if smooth:      # smooth by angle: round the bevels, keep flat faces and caps flat
        for f_ in bm.faces:
            f_.smooth = True
        for e_ in bm.edges:
            if len(e_.link_faces) == 2 and e_.calc_face_angle(0.0) > math.radians(35):
                e_.smooth = False
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me)
    o.location = (loc[0] * IN, loc[1] * IN, loc[2] * IN)
    o.rotation_euler = tuple(math.radians(r) for r in rot)
    g = group or Ctx.cur_group
    meta = Ctx.groups[g]
    coll(meta["trade"]).objects.link(o)
    if material is not None:
        me.materials.append(material if not isinstance(material, str) else _M[material])
    o["status"] = meta["status"]
    o["group"] = g
    o["spec_id"] = tag or Ctx.cur_item or name
    for k in ("source", "basis"):
        if meta.get(k):
            o[k] = meta[k]
    Ctx.built.append((name, o, o["spec_id"], g))
    return o


def cube_bm(sx, sy, sz, bevel=0.0, seg=2):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co.x *= sx; v.co.y *= sy; v.co.z *= sz
    if bevel > 0:
        bmesh.ops.bevel(bm, geom=list(bm.edges), offset=min(bevel, min(sx, sy, sz) / 2.01), segments=seg, affect="EDGES")
    return bm


def cyl_bm(r1, r2, h, seg=32, ex=1.0, ey=1.0):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=seg, radius1=r1, radius2=r2, depth=h)
    for v in bm.verts:
        v.co.x *= ex; v.co.y *= ey
    return bm


def sph_bm(rx, ry, rz, seg=16, rings=10):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=rings, radius=1.0)
    for v in bm.verts:
        v.co.x *= rx; v.co.y *= ry; v.co.z *= rz
    return bm


def part(name, bm, material, c, smooth=False, rot=(0, 0, 0), group=None, tag=None):
    """c = (x, y, z) world center in inches."""
    return _finish(bm, name, c, rot, material, smooth, group, tag)


def box(name, material, x0, y0, z0, sx, sy, sz, **kw):
    return part(name, cube_bm(sx, sy, sz, kw.pop("bevel", 0), kw.pop("seg", 2)), material, (x0 + sx / 2, y0 + sy / 2, z0 + sz / 2), **kw)


class Frame:
    """Local frame for an item: center (cx, cy), rotation rz (deg). Local +y is the item's front."""

    def __init__(self, it):
        sx, sy, sz = it["size"]
        self.cx = it["at"][0] + sx / 2
        self.cy = it["at"][1] + sy / 2
        self.rz = FACE_ROT[it["faces"]] + it.get("yaw", 0)
        swap = it["faces"] in ("+x", "-x")
        self.w = sy if swap else sx      # local width (along local x)
        self.d = sx if swap else sy      # local depth (along local y)
        self.h = sz
        self.it = it
        self.at = it["at"]; self.size = it["size"]
        self.z0 = it["at"][2]          # builders use z relative to the item's base

    def W(self, x, y):
        a = math.radians(self.rz)
        return (self.cx + x * math.cos(a) - y * math.sin(a), self.cy + x * math.sin(a) + y * math.cos(a))

    def p(self, name, bm, material, x, y, z, rz=0, rot=(0, 0, 0), **kw):
        wx, wy = self.W(x, y)
        return part(name, bm, material, (wx, wy, z + self.z0), rot=(rot[0], rot[1], self.rz + rz + rot[2]), **kw)

    def b(self, name, material, x, y, z, sx, sy, sz, bevel=0.0, seg=2, rz=0, rot=(0, 0, 0), **kw):
        """box by local center-x, center-y, bottom z."""
        return self.p(name, cube_bm(sx, sy, sz, bevel, seg), material, x, y, z + sz / 2, rz=rz, rot=rot, smooth=bevel > 0, **kw)

    def c(self, name, material, x, y, z, r, h, r2=None, seg=24, **kw):
        return self.p(name, cyl_bm(r, r if r2 is None else r2, h, seg), material, x, y, z + h / 2, **kw)


def item(spec, iid):
    for it in spec["items"]:
        if it["id"] == iid:
            return it
    raise KeyError(f"spec item missing: {iid}")


# ----------------------------------------------------------------------------- shell
def build_shell(spec):
    R = spec["room"]; W, D, H, T = R["width_in"], R["depth_in"], R["ceiling_in"], R["wall_t_in"]
    hx0, hx1, HL = R["hall"]["x0"], R["hall"]["x1"], R["hall"]["length_in"]
    Ctx.cur_item = "shell"
    Ctx.cur_group = "shell_visible"
    box("floor", "floor_lvp", -T, -T, -1.0, W + 2 * T, D + 2 * T, 1.0, tag="floor")
    box("ceiling", "ceiling_popcorn", -T, -T, H, W + 2 * T, D + 2 * T, 1.0, tag="ceiling")
    box("floor_hall", "floor_lvp", hx0, D + T, -1.0, hx1 - hx0, HL + T, 1.0, tag="floor")
    box("ceiling_hall", "ceiling_popcorn", hx0, D + T, H, hx1 - hx0, HL + T, 1.0, tag="ceiling")
    box("wall_left_TV", "wall", -T, 0, 0, T, D + T, H, tag="wall_left")
    box("wall_right_kitchen", "wall", W, 0, 0, T, D + T, H, tag="wall_right")
    box("wall_art_a", "wall", -T, D, 0, hx0 + T, T, H, tag="wall_art")            # art wall x<hall
    box("wall_art_b", "wall", hx1, D, 0, W - hx1 + T, T, H, tag="wall_kitchen_end")
    Ctx.cur_group = "shell_unseen"
    w = box("wall_front_UNSEEN", "wall", -T, -T, 0, W + 2 * T, T, H, tag="wall_front")
    w["hide_in_views"] = True
    Ctx.cur_group = "hall"
    box("hall_wall_L", "wall", hx0 - T, D + T, 0, T, HL, H, tag="hall_wall_L")
    box("hall_wall_R", "wall", hx1, D + T, 0, T, HL, H, tag="hall_wall_R")
    Ctx.cur_group = "hall_unseen"
    box("hall_end_wall", "wall", hx0 - T, D + T + HL, 0, hx1 - hx0 + 2 * T, T, H, tag="hall_end")
    # end door (closed, dark in photo) + a side door on the hall's left wall (only its casing edge is visible)
    box("hall_end_door", "door", hx0 + 3, D + T + HL - 0.1, 0, 30, 1.75, 80, tag="hall_end_door")
    box("hall_end_door_dark", "hall_dark", hx0 + 1, D + T + HL - 0.2, 0, 34, 0.2, 82, tag="hall_end_door")
    box("hall_side_door", "door", hx0 + 0.0, D + T + 24, 0, 1.75, 30, 80, tag="hall_side_door")
    part("hall_side_knob", sph_bm(1.0, 1.0, 1.0, 12, 8), "gold", (hx0 + 3.5, D + T + 24 + 3.5, 36), tag="hall_side_door")
    # baseboard + casing
    Ctx.cur_group = "casing_base"
    bb, bh = 0.5, 3.5
    box("base_left", "trim", 0, 0, 0, bb, D, bh, tag="baseboard")
    box("base_art", "trim", 0, D - bb, 0, hx0, bb, bh, tag="baseboard")
    box("base_kitchen_end", "trim", hx1, D - bb, 0, W - hx1, bb, bh, tag="baseboard")
    box("base_right_a", "trim", W - bb, 0, 0, bb, 64, bh, tag="baseboard")
    box("base_hall_L", "trim", hx0, D + T, 0, bb, HL, bh, tag="baseboard")
    box("base_hall_R", "trim", hx1 - bb, D + T, 0, bb, HL, bh, tag="baseboard")
    cw = 2.25
    box("casing_L", "trim", hx0 - cw, D - 0.6, 0, cw, 0.6 + T + 0.6, 80, tag="casing")
    box("casing_R", "trim", hx1, D - 0.6, 0, cw, 0.6 + T + 0.6, 80, tag="casing")


# ----------------------------------------------------------------------------- living furniture
def build_sofa(spec):
    f = Frame(item(spec, "sofa")); w, d = f.w, f.d      # w = 90 along local x, d = 38 front/back
    Ctx.cur_item = "sofa"; Ctx.cur_group = "living"
    leg = 4.5
    for sx in (-1, 1):
        for sy in (-1, 1):
            f.c(f"sofa_leg", "wood_legs", sx * (w / 2 - 3), sy * (d / 2 - 3), 0, 1.0, leg, r2=0.7, seg=10)
    base_h = 8.5
    f.b("sofa_frame", "leather", 0, 0, leg, w, d, base_h, bevel=0.8)
    arm_w, arm_h = 7.0, 24.0
    for sx in (-1, 1):
        f.b("sofa_arm", "leather", sx * (w / 2 - arm_w / 2), 0, leg, arm_w, d, arm_h - leg, bevel=1.5, seg=3)
    back_d, back_h = 8.5, 32.0
    f.b("sofa_back", "leather", 0, -(d / 2 - back_d / 2), leg, w - 2 * arm_w + 0.2, back_d, back_h - leg, bevel=1.8, seg=3)
    Ctx.cur_group = "living_detail"
    inner = w - 2 * arm_w
    cw = inner / 3
    seat_d = d - back_d
    for i in range(3):
        cx = -inner / 2 + cw / 2 + i * cw
        f.b("seat_cushion", "leather", cx, back_d / 2, leg + base_h - 1.0, cw - 0.4, seat_d - 0.5, 6.0, bevel=1.6, seg=3)
    for i in range(3):
        cx = -inner / 2 + cw / 2 + i * cw
        f.b("back_cushion", "leather", cx, -(d / 2 - back_d - 3.0), leg + base_h + 3.0, cw - 1.0, 5.5, 14.0, bevel=1.6, seg=3, rot=(-10, 0, 0))
    # throw pillows (cream/beige) + folded throw on seat, plus a blanket draped over the near arm (photo)
    f.b("pillow_a", "fabric_cream", -22, -10.5, leg + base_h + 6, 18, 5, 17, bevel=2.0, seg=3, rot=(-18, 0, 12))
    f.b("pillow_b", "fabric_light", -14, -9.5, leg + base_h + 4.5, 16, 4.5, 16, bevel=2.0, seg=3, rot=(-20, 0, -8))
    f.b("pillow_c", "fabric_gray", 20, -10.5, leg + base_h + 5.5, 17, 5, 16, bevel=2.0, seg=3, rot=(-16, 0, -6))
    f.b("throw_arm", "fabric_cream", -w / 2 + 2.5, 3.0, arm_h - 4.0, 1.2, 15, 14, bevel=0.5, rot=(0, 0, 0))
    f.b("throw_arm_top", "fabric_cream", -w / 2 + 3.5, 3.0, arm_h - 0.2, 6.0, 14, 0.8, bevel=0.3)


def build_chaise(spec):
    f = Frame(item(spec, "chaise")); w, d = f.w, f.d
    Ctx.cur_item = "chaise"; Ctx.cur_group = "living"
    leg = 4.0
    for sx in (-1, 1):
        for sy in (-1, 1):
            f.c("chaise_leg", "wood_legs", sx * (w / 2 - 3), sy * (d / 2 - 3), 0, 1.0, leg, r2=0.7, seg=10)
    f.b("chaise_frame", "fabric_gray", 0, 0, leg, w, d, 10, bevel=1.0)
    f.b("chaise_back", "fabric_gray", 0, -(d / 2 - 4.5), leg, w, 9, f.h - leg, bevel=1.5, seg=3)
    f.b("chaise_arm", "fabric_gray", w / 2 - 3.5, 0, leg, 7, d, 20, bevel=1.5, seg=3)
    Ctx.cur_group = "living_detail"
    f.b("chaise_cushion", "fabric_gray", -3, 4.0, leg + 9, w - 14, d - 10, 5, bevel=1.5, seg=3)
    f.b("black_blanket", "fabric_blk", -8, 6, leg + 13.6, 30, 20, 2.6, bevel=1.0, seg=2, rot=(0, 0, 4))
    f.b("black_blanket_fold", "fabric_blk", 4, 7, leg + 15.5, 24, 14, 2.0, bevel=0.9, rot=(0, 0, -3))


def build_coffee_table(spec):
    it = item(spec, "coffee_table"); f = Frame(it); w, d = f.w, f.d   # local: w along x (24), d along y (44)... oval long axis = world y
    Ctx.cur_item = "coffee_table"; Ctx.cur_group = "living"
    top = it["size"][2]
    # oval marble top, long axis along world y (local y since faces +y)
    f.p("table_top", cyl_bm(w / 2, w / 2, 1.2, 48, ex=1.0, ey=d / w), "marble", 0, 0, top - 0.6, smooth=True)
    f.p("table_edge_gold", cyl_bm(w / 2 + 0.05, w / 2 + 0.05, 0.15, 48, ex=1.0, ey=d / w), "gold", 0, 0, top - 1.3)
    f.p("table_base", cyl_bm(w * 0.30, w * 0.38, top - 1.4, 32, ex=1.0, ey=d / w * 0.55), "gold", 0, 0, (top - 1.4) / 2, smooth=True)
    Ctx.cur_group = "living_detail"
    f.c("bowl", "wood_cab", 0, -12, top + 0.6, 5, 3, r2=3.5)
    f.c("bowl_fill", "fabric_light", 0, -12, top + 3.0, 4, 0.5)
    f.b("table_book", "book1", 0, 6, top + 0.6, 8, 11, 1.0, bevel=0.1)
    f.b("table_tray", "gold", 0, 14, top + 0.6, 6, 9, 0.7)
    f.c("candle", "plastic_wht", 3, 14, top + 1.3, 1.2, 4)
    f.c("can", "stainless", -4, 0, top + 0.6, 1.4, 4.7)
    f.b("remote", "frame_blk", 6, 16, top + 0.6, 1.6, 6, 0.6)


def build_rug(spec):
    it = item(spec, "rug"); Ctx.cur_item = "rug"; Ctx.cur_group = "living"
    x, y, z = it["at"]; sx, sy, sz = it["size"]
    box("rug", "rug", x, y, z, sx, sy, sz, tag="rug")


def build_tv(spec):
    con = item(spec, "tv_console"); fc = Frame(con); w, d = fc.w, fc.d
    Ctx.cur_item = "tv_console"; Ctx.cur_group = "living"
    fc.b("console_body", "wood_dark", 0, 0, 3, w, d, con["size"][2] - 3, bevel=0.6)
    for sx in (-1, 1):
        for sy in (-1, 1):
            fc.c("console_leg", "wood_dark", sx * (w / 2 - 2), sy * (d / 2 - 2), 0, 1.0, 3, seg=8)
    fc.b("console_lid_seam", "frame_blk", 0, d / 2 + 0.05, con["size"][2] - 4.5, w - 1, 0.1, 0.4)
    Ctx.cur_group = "living_detail"
    Ctx.cur_item = "tv_console"
    top = con["size"][2]
    fc.b("book_stack_a", "book1", 14, 0, top, 11, 8, 1.2)
    fc.b("book_stack_b", "book2", 14, 0, top + 1.2, 10, 7, 1.0)
    fc.b("console_item", "fabric_light", -16, 0, top, 5, 6, 3, bevel=1.0)
    tv = item(spec, "tv"); ft = Frame(tv); sx, sy, sz = tv["size"]
    w, h = ft.w, ft.h
    Ctx.cur_item = "tv"; Ctx.cur_group = "living"
    # panel (back shell + bezel), then the lit screen on the front face
    ft.b("tv_panel", "glass_blk", 0, 0, 0, w, sx, h, bevel=0.2)
    ft.b("tv_screen", "tv_screen", 0, sx / 2 + 0.02, 0.6, w - 1.2, 0.05, h - 1.2)
    Ctx.cur_group = "living_detail"      # stand hardware is not visible in P1
    ft.b("tv_stand_neck", "blk_steel", 0, 0, -3.8, 8, 2.0, 4.0)
    ft.b("tv_stand_foot", "blk_steel", 0, 0, -4.0, 22, 8, 0.5)


def build_armchair(spec):
    it = item(spec, "armchair"); f = Frame(it); w, d = f.w, f.d
    Ctx.cur_item = "armchair"; Ctx.cur_group = "living"
    leg = 7
    for sx in (-1, 1):
        for sy in (-1, 1):
            f.c("chair_leg", "wood_legs", sx * (w / 2 - 4), sy * (d / 2 - 4), 0, 1.0, leg + 1, r2=0.6, seg=10, rot=(sy * 7, -sx * 7, 0))
    f.b("chair_seat", "fabric_light", 0, 2, leg, w - 2, d - 6, 8, bevel=2.0, seg=3)
    f.b("chair_back", "fabric_light", 0, -(d / 2 - 4), leg + 2, w, 8, it["size"][2] - leg - 2, bevel=3.0, seg=3, rot=(-8, 0, 0))
    for sx in (-1, 1):
        f.b("chair_arm", "fabric_light", sx * (w / 2 - 2.5), 0, leg + 2, 5, d - 4, 10, bevel=2.0, seg=3)
    Ctx.cur_group = "living_detail"
    f.b("chair_throw", "fabric_light", -4, -6, leg + 8, 22, 4, 17, bevel=1.5, seg=2, rot=(-14, 0, 10), group="living_detail")
    f.b("chair_blanket_blue", "carpet_gray", 6, -9, leg + 14, 20, 8, 4, bevel=1.5, rot=(0, 0, 0))


def build_basket(spec):
    it = item(spec, "side_basket"); f = Frame(it)
    Ctx.cur_item = "side_basket"; Ctx.cur_group = "living_detail"
    h = it["size"][2]
    f.p("basket", cyl_bm(7.2, 7.5, h - 0.6, 28), "basket", 0, 0, (h - 0.6) / 2, smooth=True)       # stacked layers: no coplanar caps
    f.p("basket_ring", cyl_bm(7.5, 7.5, 0.4, 28), "wood_legs", 0, 0, h - 0.8)
    f.p("basket_item", cyl_bm(5.2, 5.2, 0.4, 24), "fabric_cream", 0, 0, h - 0.2)


def build_ottoman(spec):
    it = item(spec, "ottoman"); f = Frame(it); w, d = f.w, f.d
    Ctx.cur_item = "ottoman"; Ctx.cur_group = "living"
    top = it["size"][2]
    f.b("ottoman_body", "fabric_gray", 0, 0, 2, w, d, top - 2, bevel=1.6, seg=3)
    for sx in (-1, 1):
        for sy in (-1, 1):
            f.c("ottoman_leg", "wood_legs", sx * (w / 2 - 2), sy * (d / 2 - 2), 0, 0.9, 2, seg=8)
    Ctx.cur_group = "living_detail"
    # clutter (jacket/bag), box fan on top (photo)
    f.b("ottoman_jacket", "fabric_blk", -2, 4, top, 18, 14, 4.5, bevel=2.0, seg=2, rot=(0, 0, 14))
    f.b("ottoman_paper", "paper", 3, -4, top + 4.4, 10, 12, 0.5, rot=(0, 0, 8))
    f.p("fan_body", cyl_bm(4.2, 4.2, 2.0, 24), "carpet_gray", 0, 6, top + 9.5, rot=(90, 0, 0), smooth=True)
    f.p("fan_guard", cyl_bm(4.5, 4.5, 0.5, 24), "wire", 0, 7.2, top + 9.5, rot=(90, 0, 0))
    f.b("fan_stand", "blk_steel", 0, 6, top + 4.4, 2, 2, 3.2)


def build_lamp(spec):
    it = item(spec, "lamp_table"); f = Frame(it); w, d = f.w, f.d
    Ctx.cur_item = "lamp_table"; Ctx.cur_group = "living"
    top = 22.0                          # table height; spec size also includes the lamp (~14in)
    f.b("sidetable_top", "wood_dark", 0, 0, top - 1.2, w, d, 1.2, bevel=0.3)
    for sx in (-1, 1):
        for sy in (-1, 1):
            f.c("sidetable_leg", "wood_dark", sx * (w / 2 - 1.2), sy * (d / 2 - 1.2), 0, 0.7, top - 1.2, seg=8)
    f.c("lamp_base", "gold", 0, 0, top, 2.6, 2.0, r2=2.0)
    f.c("lamp_stem", "gold", 0, 0, top + 2, 0.5, 8)
    f.c("lamp_shade", "lampshade", 0, 0, top + 6, 5.2, 8.0, r2=4.0, seg=24)
    # light source is added by the lighting section at this location
    build_lamp.pos = (f.cx, f.cy, top + 10)


def build_cat_tree(spec):
    it = item(spec, "cat_tree"); f = Frame(it); w, d = f.w, f.d
    Ctx.cur_item = "cat_tree"; Ctx.cur_group = "living"
    f.b("ct_base", "carpet_gray", 0, 0, 0, w, d, 1.8, bevel=0.3)
    f.c("ct_post", "carpet_gray", 2.5, 2.5, 1.8, 2.0, 36.2)
    f.b("ct_house", "carpet_gray", -2, -2, 8, 11, 11, 10, bevel=0.4)
    f.b("ct_house_hole", "frame_blk", -2, 3.6, 10, 5, 0.2, 5.5)
    f.b("ct_platform", "carpet_gray", 2.5, 2.5, 38, 13, 13, 2.0, bevel=0.3)
    f.c("ct_post_low", "carpet_gray", -5, 3, 1.8, 1.2, 6)


def build_plant(spec):
    it = item(spec, "plant"); f = Frame(it)
    Ctx.cur_item = "plant"; Ctx.cur_group = "living"
    f.c("pot", "pot_blk", 0, 0, 0, 7.5, 12, r2=6.0, seg=28)
    f.c("soil", "wood_dark", 0, 0, 11.5, 6.5, 0.6)
    import random
    rnd = random.Random(7)
    for i in range(11):
        a = rnd.uniform(0, 2 * math.pi); r = rnd.uniform(1, 5)
        top = rnd.uniform(26, 42)
        sx, sy = r * math.cos(a), r * math.sin(a)
        f.c("stem", "stem", sx / 2, sy / 2, 11, 0.4, top - 11, seg=6)
        lx, ly = sx + math.cos(a) * 3.0, sy + math.sin(a) * 3.0
        rotz = math.degrees(a)
        f.p("leaf", sph_bm(5.8, 4.4, 0.35, 14, 8), "leaf", lx, ly, top, rot=(rnd.uniform(-25, 15), rnd.uniform(-20, 20), rotz), smooth=True)


def build_art(spec):
    Ctx.cur_group = "living"
    it = item(spec, "art_diptych"); f = Frame(it); Ctx.cur_item = "art_diptych"
    # two canvases, abstract grey swirls
    pw = 26.0
    for i, sy in enumerate((-1, 1)):
        f.b("diptych_canvas", "canvas", sy * (pw / 2 + 2), 0, 0, pw, 1.5, it["size"][2], bevel=0.1)
        f.b("diptych_frame", "frame_blk", sy * (pw / 2 + 2), 0.2, 0, pw + 0.8, 1.2, 0.8)
        f.b("diptych_stroke", "art_dark", sy * (pw / 2 + 2) + sy * 1, 0.8, 14 + i * 5, 20, 0.25, 4, rot=(0, 0, 0))
        f.b("diptych_stroke2", "art_light", sy * (pw / 2 + 2) - sy * 2, 0.8, 22 - i * 6, 14, 0.25, 3)
    it = item(spec, "art_sunburst"); f = Frame(it); Ctx.cur_item = "art_sunburst"
    f.b("sunburst_canvas", "canvas", 0, 0, 0, f.w, 1.5, it["size"][2], bevel=0.1)
    f.b("sunburst_frame_t", "frame_blk", 0, 0.0, it["size"][2] - 0.8, f.w + 1, 1.7, 0.8)
    f.b("sunburst_frame_b", "frame_blk", 0, 0.0, 0, f.w + 1, 1.7, 0.8)
    f.b("sunburst_frame_l", "frame_blk", -f.w / 2, 0.0, 0, 0.8, 1.7, it["size"][2])
    f.b("sunburst_frame_r", "frame_blk", f.w / 2, 0.0, 0, 0.8, 1.7, it["size"][2])
    cx, cz = 0, it["size"][2] * 0.46
    for k in range(28):                   # radiating dark strokes
        a = k * (360 / 28); ln = 10 + (k % 4) * 2.4
        f.p("sunburst_ray", cube_bm(0.55, 0.2, ln), "art_dark", math.sin(math.radians(a)) * ln / 2, 0.85, cz + math.cos(math.radians(a)) * ln / 2, rot=(0, -a, 0))
    f.p("sunburst_core", sph_bm(1.8, 0.4, 1.8, 12, 8), "art_dark", 0, 0.85, cz)
    it = item(spec, "frame_small"); f = Frame(it); Ctx.cur_item = "frame_small"
    f.b("frame_small", "frame_blk", 0, 0, 0, f.w, 1.0, it["size"][2])
    for i in range(3):
        f.b("frame_small_photo", "art_light", -5.8 + i * 5.8, 0.55, 1.2, 4.6, 0.1, 6.6)


# ----------------------------------------------------------------------------- kitchen
def build_kitchen(spec):
    Ctx.cur_group = "kitchen"
    it = item(spec, "fridge"); f = Frame(it); w, d = f.w, f.d; Ctx.cur_item = "fridge"
    bd = d - 1.5                      # body depth; door handles protrude the last 1.5in (size in spec includes handles)
    f.b("fridge_body", "blk_steel", 0, -d / 2 + bd / 2, 0, w, bd, it["size"][2], bevel=0.5)
    f.b("fridge_split", "frame_blk", 0, d / 2 - 1.5, 24.0, w - 1, 0.1, 0.5)
    for k, (zz, hl) in enumerate(((40, 22), (6, 10))):
        f.b("fridge_handle", "stainless", w / 2 - 3, d / 2 - 0.5, zz, 0.9, 1.0, hl)
        for pz in (zz + 1, zz + hl - 3):
            f.b("fridge_handle_post", "stainless", w / 2 - 3, d / 2 - 1.2, pz, 0.7, 0.6, 1.2)
    Ctx.cur_group = "living_detail"
    import random
    rnd = random.Random(11)
    for i in range(14):                # magnets / photos on the door (visible in photo)
        f.b("fridge_magnet", "magnet" if i % 3 else "paper", rnd.uniform(-w / 2 + 3, w / 2 - 6), d / 2 - 1.4, rnd.uniform(36, 62), rnd.uniform(1.0, 2.4), 0.15, rnd.uniform(1.0, 3.0))
    # items on top of fridge
    f.b("fridge_top_items", "fabric_light", -6, 0, it["size"][2], 8, 10, 4, bevel=1.0)
    Ctx.cur_group = "kitchen"
    it = item(spec, "range"); f = Frame(it); w, d = f.w, f.d; Ctx.cur_item = "range"
    bd, top = 24.0, 36.0              # body depth (flush to wall) and cooktop height; spec size adds handle projection + 5in backguard
    by = -d / 2 + bd / 2
    f.b("range_body", "stainless", 0, by, 0, w, bd, top - 0.1, bevel=0.3)
    f.b("range_cooktop", "glass_blk", 0, by, top - 0.15, w - 0.4, bd - 0.4, 0.15)
    for bx, byy, r in ((-6.5, -5.5, 3.2), (6.5, -5.5, 2.6), (-6.5, 6.5, 2.6), (6.5, 6.5, 3.6)):
        f.c("burner", "burner", bx, by + byy, top - 0.05, r, 0.25, seg=20)
    f.b("oven_window", "glass_blk", 0, by + bd / 2 + 0.02, 7, w - 7, 0.15, 14)
    f.b("oven_handle", "stainless", 0, d / 2 - 0.5, 22, w - 5, 1.0, 1.0)
    for sx_ in (-1, 1):
        f.b("oven_handle_post", "stainless", sx_ * (w / 2 - 4), by + bd / 2 + 0.6, 22.2, 0.7, 1.0, 0.6)
    f.b("control_panel", "blk_steel", 0, -d / 2 + 2.2, top, w, 4.4, it["size"][2] - top, bevel=0.2)
    Ctx.cur_group = "living_detail"
    f.c("pot_on_range", "stainless", -6, by + 6, top, 4.5, 6, seg=20)
    f.c("pan_on_range", "blk_steel", 6, by - 4, top, 5, 1.8, seg=20)
    Ctx.cur_group = "kitchen"
    it = item(spec, "micro_hood"); f = Frame(it); Ctx.cur_item = "micro_hood"
    f.b("microwave", "blk_steel", 0, 0, 0, f.w, f.d, it["size"][2], bevel=0.4)
    f.b("microwave_glass", "glass_blk", -2, f.d / 2 + 0.03, 3, f.w - 14, 0.15, it["size"][2] - 6)
    f.b("microwave_panel", "frame_blk", f.w / 2 - 5, f.d / 2 + 0.03, 3, 7, 0.15, it["size"][2] - 6)
    Ctx.cur_group = "kitchen_unseen"
    it = item(spec, "base_cabs"); f = Frame(it); Ctx.cur_item = "base_cabs"
    f.b("base_cabinets", "wood_cab", 0, 0, 0, f.w, f.d, it["size"][2], bevel=0.2)
    f.b("toe_kick", "frame_blk", 0, f.d / 2 - 0.5, 0, f.w, 0.6, 3.5)
    for i in range(3):
        f.b("cab_door_seam", "frame_blk", -f.w / 2 + (i + 1) * f.w / 4, f.d / 2 + 0.05, 4, 0.15, 0.1, it["size"][2] - 5)
    it = item(spec, "counter"); f = Frame(it); Ctx.cur_item = "counter"
    f.b("countertop", "quartz", 0, 0, 0, f.w, f.d, it["size"][2], bevel=0.2)
    f.b("backsplash", "quartz", 0, -f.d / 2 + 0.3, it["size"][2], f.w, 0.6, 4, tag="counter_backsplash")
    Ctx.cur_group = "living_detail"
    for i, (nm, mt, r, h, xx) in enumerate((("jar_a", "paper", 2.2, 7, -20), ("jar_b", "stainless", 1.8, 9, -10), ("kettle", "blk_steel", 3.2, 8, 8))):
        f.c(nm, mt, xx, 0, it["size"][2], r, h, seg=18)
    f.b("cutting_board", "wood_cab", 0, 14, it["size"][2], 11, 15, 0.8)
    Ctx.cur_group = "kitchen_unseen"
    it = item(spec, "upper_cabs"); f = Frame(it); Ctx.cur_item = "upper_cabs"
    f.b("upper_cabinets", "wood_cab", 0, 0, 0, f.w, f.d, it["size"][2], bevel=0.2)
    for i in range(4):
        f.b("upper_door_seam", "frame_blk", -f.w / 2 + (i + 1) * f.w / 5, f.d / 2 + 0.05, 1, 0.15, 0.1, it["size"][2] - 2)
    # under-cabinet light strip (lit warm in the photo)
    Ctx.cur_group = "kitchen"
    f.b("undercab_strip", "undercab", 0, 0, -0.4, f.w - 4, 2.0, 0.4, tag="undercab_strip")


# ----------------------------------------------------------------------------- ceiling / wall extras + string lights
def build_fx(spec):
    R = spec["room"]; W, D, H = R["width_in"], R["depth_in"], R["ceiling_in"]
    Ctx.cur_group = "lighting_fx"; Ctx.cur_item = "string_lights"
    # string lights: catenary segments along the left wall, hooks at the listed points
    hooks = [(24, 90), (82, 87), (136, 85), (184, 87)]
    bulbs = []
    for (ya, za), (yb, zb) in zip(hooks, hooks[1:]):
        n = 7
        for i in range(n + 1):
            t = i / n
            y = ya + (yb - ya) * t
            sag = 6.0 * 4 * t * (1 - t)
            z = za + (zb - za) * t - sag
            bulbs.append((y, z))
    pts = [(1.6, y, z) for y, z in bulbs]
    for (a, b) in zip(pts, pts[1:]):
        mid = tuple((p + q) / 2 for p, q in zip(a, b))
        v = Vector(b) - Vector(a)
        ln = v.length
        rot = v.to_track_quat("Z", "Y").to_euler()
        part("string_wire", cyl_bm(0.12, 0.12, ln, 6), "wire", mid, rot=tuple(math.degrees(r) for r in rot), tag="string_lights")
    for i, (x, y, z) in enumerate(pts):
        if i % 2 == 0:
            part("string_bulb", sph_bm(1.1, 1.1, 1.5, 12, 8), "bulb", (x, y, z - 1.7), smooth=True, tag="string_lights")
            part("string_socket", cyl_bm(0.5, 0.5, 1.0, 8), "wire", (x, y, z - 0.2), tag="string_lights")
    for hy, hz in hooks:
        part("string_hook", cyl_bm(0.3, 0.3, 1.2, 6), "wire", (0.6, hy, hz + 0.3), rot=(0, 90, 0), tag="string_lights")
    # ceiling items: round exhaust vent over kitchen, smoke detector near hall
    Ctx.cur_item = "ceiling_vent"
    part("ceiling_vent", cyl_bm(6.5, 6.5, 0.8, 32), "plastic_wht", (W - 14, 150, H - 0.4), tag="ceiling_vent")
    part("ceiling_vent_grille", cyl_bm(5.2, 5.2, 0.9, 32), "wall", (W - 14, 150, H - 0.5), tag="ceiling_vent")
    part("smoke_detector", cyl_bm(2.6, 2.6, 1.4, 24), "plastic_wht", (hx_mid(spec), 192, H - 0.7), tag="smoke_detector")


def hx_mid(spec):
    h = spec["room"]["hall"]
    return (h["x0"] - 6)


# ----------------------------------------------------------------------------- lighting + cameras
def add_light(kind, name, loc, energy, color, size=None, rot=None, spot=None):
    ld = bpy.data.lights.new(name, kind)
    ld.energy = energy; ld.color = color
    if kind == "AREA":
        ld.shape = "RECTANGLE"; ld.size, ld.size_y = size
    if kind == "POINT":
        ld.shadow_soft_size = size or 2.0 * IN
    o = bpy.data.objects.new(name, ld)
    o.location = tuple(v * IN for v in loc)
    if rot:
        o.rotation_euler = tuple(math.radians(r) for r in rot)
    coll("lighting").objects.link(o)
    return o


def build_lights(spec, mode):
    for o in [o for o in bpy.data.objects if o.type == "LIGHT"]:
        bpy.data.objects.remove(o, do_unlink=True)
    R = spec["room"]; W, D, H = R["width_in"], R["depth_in"], R["ceiling_in"]
    lx, ly, lz = build_lamp.pos
    tv = item(spec, "tv")
    if mode == "night":     # matches the photo: TV glow + one lamp + under-cabinet strip + faint hall spill
        add_light("POINT", "lamp", (lx, ly, lz), 60, (1.0, 0.70, 0.40), 1.5 * IN)
        add_light("AREA", "tv_glow", (tv["at"][0] + 12, tv["at"][1] + tv["size"][1] / 2, tv["at"][2] + 16), 45, (0.55, 0.65, 1.0), (0.9, 0.5), (0, 90, 0))
        add_light("AREA", "undercab", (W - 12, 160, 53), 18, (1.0, 0.72, 0.38), (0.6, 0.5), (180, 0, 0))
        add_light("AREA", "hall_spill", (130, D + 40, 60), 12, (1.0, 0.85, 0.65), (0.5, 0.3), (0, 90, 90))
        add_light("AREA", "string_glow", (6, 100, 82), 8, (1.0, 0.75, 0.45), (1.0, 1.0), (0, 90, 0))
    else:                   # inspection light: neutral, even, no mood
        add_light("AREA", "day_a", (90, 70, H - 2), 160, (1, 0.96, 0.9), (3.5, 3.0), (0, 0, 0))
        add_light("AREA", "day_b", (60, 150, H - 2), 130, (1, 0.96, 0.9), (3.5, 3.0), (0, 0, 0))
        add_light("AREA", "day_c", (150, 120, H - 2), 90, (1, 0.96, 0.9), (3.0, 3.0), (0, 0, 0))
        add_light("AREA", "day_hall", (130, D + 60, H - 2), 60, (1, 0.96, 0.9), (2.0, 2.0), (0, 0, 0))
    # world
    w = bpy.data.worlds.get("W") or bpy.data.worlds.new("W")
    w.use_nodes = True
    bg = w.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (0.02, 0.02, 0.025, 1) if mode == "night" else (0.25, 0.25, 0.26, 1)
    bg.inputs[1].default_value = 1.0
    Ctx.sc.world = w


def make_cam(name, loc, look_at=None, rot=None, lens=24, sensor=36, ortho=None):
    cd = bpy.data.cameras.new(name)
    cd.lens = lens; cd.sensor_width = sensor; cd.sensor_fit = "HORIZONTAL"
    cd.clip_start = 0.02; cd.clip_end = 80
    if ortho:
        cd.type = "ORTHO"; cd.ortho_scale = ortho * IN
    o = bpy.data.objects.new(name, cd)
    o.location = tuple(v * IN for v in loc)
    if rot is not None:
        o.rotation_euler = tuple(math.radians(r) for r in rot)
    else:
        d = (Vector(look_at) - Vector(loc))
        o.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    Ctx.sc.collection.objects.link(o)
    return o


def set_visibility(hide_names):
    for o in Ctx.sc.objects:
        if o.type == "MESH":
            o.hide_render = o.name in hide_names or (o.get("spec_id") in hide_names)


def render(cam, path, res, samples, engine_opts=None):
    sc = Ctx.sc
    sc.camera = cam
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.render.filepath = str(path)
    sc.cycles.samples = samples
    bpy.ops.render.render(write_still=True)


def img_stats(path):
    img = bpy.data.images.load(str(path))
    px = list(img.pixels)[:: 4 * 11]
    bpy.data.images.remove(img)
    mean = sum(px) / len(px)
    var = sum((p - mean) ** 2 for p in px) / len(px)
    return mean, var


# ----------------------------------------------------------------------------- verification
def bbox_in(objs):
    pts = [o.matrix_world @ Vector(c) for o in objs for c in o.bound_box]
    lo = [min(p[i] for p in pts) / IN for i in range(3)]
    hi = [max(p[i] for p in pts) / IN for i in range(3)]
    return lo, hi


def verify(spec):
    res = []
    tol = spec.get("tolerance_in", 0.25)
    by_item = {}
    for name, o, iid, g in Ctx.built:
        by_item.setdefault(iid, []).append(o)
    for c in spec["checks"]:
        k = c["kind"]
        if k == "size_match":
            for it in spec["items"]:
                objs = by_item.get(it["id"], [])
                if not objs:
                    res.append({"check": f"built {it['id']}", "ok": False, "expected": "objects", "actual": 0}); continue
                body = [o for o in objs if o["group"] != "living_detail"] or objs
                lo, hi = bbox_in(body)
                if it.get("yaw"):      # rotated item: check the center only (3in), not the axis-aligned box
                    cx = (lo[0] + hi[0]) / 2; cy = (lo[1] + hi[1]) / 2
                    ex = it["at"][0] + it["size"][0] / 2; ey = it["at"][1] + it["size"][1] / 2
                    res.append({"check": f"center {it['id']} (in)", "expected": [ex, ey], "actual": [round(cx, 1), round(cy, 1)], "ok": abs(cx - ex) <= 3 and abs(cy - ey) <= 3})
                    continue
                t = it.get("env_tol", tol)
                exp_lo = it["at"]; exp_hi = [a_ + s_ for a_, s_ in zip(it["at"], it["size"])]
                ok = all(abs(l - e) <= t for l, e in zip(lo, exp_lo)) and all(abs(h - e) <= t for h, e in zip(hi, exp_hi))
                res.append({"check": f"body {it['id']} min/max corner (in)" + (f" tol {t}" if t != tol else ""), "expected": [exp_lo, exp_hi],
                            "actual": [[round(v, 2) for v in lo], [round(v, 2) for v in hi]], "ok": ok})
        elif k == "room_extents":
            shell = [o for n, o, i, g in Ctx.built if g == "shell_visible" and i in ("floor", "ceiling", "wall_left", "wall_right")]
            R = spec["room"]
            W = R["width_in"]; D = R["depth_in"]; H = R["ceiling_in"]
            fl = next(o for n, o, i, g in Ctx.built if n == "floor"); ce = next(o for n, o, i, g in Ctx.built if n == "ceiling")
            wl = next(o for n, o, i, g in Ctx.built if n == "wall_left_TV"); wr = next(o for n, o, i, g in Ctx.built if n == "wall_right_kitchen")
            wf = next(o for n, o, i, g in Ctx.built if n == "wall_front_UNSEEN"); wa = next(o for n, o, i, g in Ctx.built if n == "wall_art_a")
            (l1, h1), (l2, h2) = bbox_in([wl]), bbox_in([wr])
            (l3, h3), (l4, h4) = bbox_in([wf]), bbox_in([wa])
            (l5, h5), (l6, h6) = bbox_in([fl]), bbox_in([ce])
            got = [round(l2[0] - h1[0], 2), round(l4[1] - h3[1], 2), round(l6[2] - h5[2], 2)]
            res.append({"check": "interior clear x,y,z (in)", "expected": c["expect"], "actual": got, "ok": all(abs(a - b) <= tol for a, b in zip(got, c["expect"]))})
        elif k == "gap":
            lo_a, hi_a = bbox_in(by_item[c["a"]]); lo_b, hi_b = bbox_in(by_item[c["b"]])
            ax = {"x": 0, "y": 1}[c["axis"]]
            it_a, it_b = item(spec, c["a"]), item(spec, c["b"])
            a_max = it_a["at"][ax] + it_a["size"][ax]; b_min = it_b["at"][ax]
            got = round(b_min - a_max if b_min >= a_max else it_a["at"][ax] - (it_b["at"][ax] + it_b["size"][ax]), 2)
            res.append({"check": f"gap {c['a']}→{c['b']} along {c['axis']} (in) — {c.get('note','')}", "expected": c["expect"], "actual": got, "ok": abs(got - c["expect"]) <= c.get("tol", tol)})
        elif k == "hall_width":
            a = next(o for n, o, i, g in Ctx.built if n == "hall_wall_L"); b = next(o for n, o, i, g in Ctx.built if n == "hall_wall_R")
            got = round(bbox_in([b])[0][0] - bbox_in([a])[1][0], 2)
            res.append({"check": "hall clear width (in)", "expected": c["expect"], "actual": got, "ok": abs(got - c["expect"]) <= c.get("tol", tol)})
        elif k == "no_overlap":
            boxes = {i: item(spec, i) for i in c["items"]}
            bad = []
            ids = list(boxes)
            for a in range(len(ids)):
                for b in range(a + 1, len(ids)):
                    A, B = boxes[ids[a]], boxes[ids[b]]
                    ov = all(A["at"][ax] < B["at"][ax] + B["size"][ax] and B["at"][ax] < A["at"][ax] + A["size"][ax] for ax in (0, 1))
                    if ov:
                        bad.append(f"{ids[a]}×{ids[b]}")
            res.append({"check": "footprints do not intersect", "expected": "none", "actual": bad or "none", "ok": not bad})
    # inside-room containment
    R = spec["room"]
    inside_bad = []
    for it in spec["items"]:
        x, y, z = it["at"]; sx, sy, sz = it["size"]
        if x < -0.01 or y < -0.01 or x + sx > R["width_in"] + 0.01 or y + sy > R["depth_in"] + 0.01 or z + sz > R["ceiling_in"]:
            inside_bad.append(it["id"])
    res.append({"check": "all items inside the room envelope", "expected": "none outside", "actual": inside_bad or "none", "ok": not inside_bad})
    return res


# ----------------------------------------------------------------------------- main
def build(spec):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    Ctx.sc = sc; Ctx.spec = spec; Ctx.groups = spec["groups"]; Ctx.colls = {}; Ctx.built = []; _M.clear()
    sc.unit_settings.system = "IMPERIAL"; sc.unit_settings.length_unit = "INCHES"
    all_mats()
    build_shell(spec)
    for fn in (build_sofa, build_chaise, build_coffee_table, build_rug, build_tv, build_armchair, build_basket, build_ottoman,
               build_lamp, build_cat_tree, build_plant, build_art, build_kitchen, build_fx):
        fn(spec)
    bpy.context.view_layer.update()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spec"); ap.add_argument("--out", default="build")
    ap.add_argument("--no-render", action="store_true")
    ap.add_argument("--quality", default="draft", choices=["draft", "final"])
    ap.add_argument("--only", default="", help="comma list of render names to run")
    a = ap.parse_args()
    sp = Path(a.spec)
    spec = yaml.safe_load(sp.read_text())
    name = sp.stem
    out = Path(a.out) / name; out.mkdir(parents=True, exist_ok=True)
    errs = validate(spec)
    if errs:
        print("SPEC INVALID:\n  " + "\n  ".join(errs)); sys.exit(1)
    build(spec)
    results = verify(spec)
    bad = [r for r in results if not r["ok"]]
    for r in results:
        print(("PASS " if r["ok"] else "FAIL ") + r["check"], "| expected", r["expected"], "| actual", r["actual"])
    sc = Ctx.sc
    n_obj = len([o for o in sc.objects if o.type == "MESH"])
    print(f"{n_obj} mesh objects, {len(bpy.data.materials)} materials")
    bpy.ops.wm.save_as_mainfile(filepath=str(out / f"{name}.blend"))
    sc.render.engine = "CYCLES"; sc.cycles.device = "CPU"
    sc.cycles.use_denoising = True
    files = []
    if not a.no_render:
        files = render_all(spec, out, name, a.quality, set(filter(None, a.only.split(","))))
    # glb (hide helper wall? keep everything; front wall flagged in custom props)
    try:
        bpy.ops.export_scene.gltf(filepath=str(out / f"{name}.glb"), export_format="GLB", export_extras=True, use_visible=False)
        glb = True
    except Exception as e:
        print("glb export failed:", e); glb = False
    write_report(spec, out, name, results, files, glb, n_obj)
    if bad:
        print(f"{len(bad)} CHECK(S) FAILED"); sys.exit(1)


FRONT = {"wall_front_UNSEEN"}


def render_all(spec, out, name, quality, only):
    sc = Ctx.sc
    R = spec["room"]; W, D, H = R["width_in"], R["depth_in"], R["ceiling_in"]
    draft = quality == "draft"
    S_REV, S_REAL = (12, 48) if draft else (24, 160)
    files = []

    def want(n):
        return not only or n in only

    # --- review renders, provenance colors (flat, no lights needed beyond the world)
    if any(want(n) for n in ("review_plan", "review_iso", "review_front")):
        originals = {o.name: list(o.data.materials) for o in sc.objects if o.type == "MESH"}
        for o in sc.objects:
            if o.type == "MESH":
                st = o.get("status", "assumed")
                key = f"prov_{st}"
                if key not in _M:
                    m = bpy.data.materials.new(key); b = _bsdf(m)
                    b.inputs["Base Color"].default_value = STATUS_COLORS[st]; b.inputs["Roughness"].default_value = 0.9
                    _M[key] = m
                o.data.materials.clear(); o.data.materials.append(_M[key])
        build_lights(spec, "day")
        for o in [o for o in bpy.data.objects if o.type == "LIGHT"]:      # review = flat sky-lit, no room lights
            bpy.data.objects.remove(o, do_unlink=True)
        sc.view_settings.view_transform = "Standard"; sc.view_settings.look = "None"; sc.view_settings.exposure = 0.0
        sc.world.node_tree.nodes["Background"].inputs[0].default_value = (0.95, 0.95, 0.95, 1)
        sc.world.node_tree.nodes["Background"].inputs[1].default_value = 1.2
        hide = FRONT | {"ceiling", "ceiling_hall"}
        set_visibility(hide)
        views = {
            "review_plan": (make_cam("c_plan", (W / 2, D / 2 + 40, 330), rot=(0, 0, 0), lens=24, ortho=300), (1200, 1350)),
            "review_iso": (make_cam("c_iso", (W / 2 + 60, -150, 190), look_at=(W / 2 - 10, D / 2 + 10, 20), lens=24), (1600, 1100)),
            "review_front": (make_cam("c_side", (-170, 110, 120), look_at=(W / 2, D / 2 + 20, 30), lens=26), (1600, 1100)),
        }
        # review_front hides the left wall too so we see the room from the TV side
        for vn, (cam, res) in views.items():
            if not want(vn):
                continue
            if vn == "review_front":
                set_visibility(hide | {"wall_left"})
            else:
                set_visibility(hide)
            f = out / f"{name}_{vn}.png"
            render(cam, f, res, S_REV); files.append(f.name)
        # restore materials
        for o in sc.objects:
            if o.type == "MESH":
                o.data.materials.clear()
                for m in originals[o.name]:
                    o.data.materials.append(m)

    # --- realistic: night (photo light) and day (inspection)
    sc.view_settings.view_transform = "AgX"; sc.view_settings.look = "AgX - Base Contrast"
    for mode in ("night", "day"):
        build_lights(spec, mode)
        sc.view_settings.exposure = 0.9 if mode == "night" else 0.0
        # photo match: ultra-wide, portrait, standing at the sofa's near end
        if mode == "night" and want("photomatch_night"):
            set_visibility(FRONT)
            cam = make_cam("c_photo", (104, 2, 56), rot=(95, 0, 3), lens=13, sensor=24)
            f = out / f"{name}_photomatch_{mode}.png"
            render(cam, f, (1125, 1500), S_REAL); files.append(f.name)
        # hero views from inside, wider lens
        if mode == "day":
            set_visibility(FRONT)
            heroes = {
                "view_tv_wall": ((150, 40, 58), (6, 118, 38), 20),
                "view_kitchen": ((40, 40, 58), (170, 110, 42), 22),
                "view_art_wall": ((60, 20, 56), (62, 200, 44), 24),
                "view_hall": ((100, 120, 56), (130, 320, 40), 22),
            }
            for vn, (loc, tgt, lens) in heroes.items():
                if want(vn):
                    cam = make_cam(vn, loc, look_at=tgt, lens=lens)
                    f = out / f"{name}_{vn}.png"
                    render(cam, f, (1200, 800), S_REAL); files.append(f.name)
        if mode == "night" and want("view_overall_night"):
            set_visibility(FRONT)
            cam = make_cam("c_over", (150, 40, 58), look_at=(40, 120, 36), lens=18)
            f = out / f"{name}_view_overall_night.png"
            render(cam, f, (1200, 800), S_REAL); files.append(f.name)
    set_visibility(set())
    # sanity: no blank render
    for fn in files:
        mean, var = img_stats(out / fn)
        if var < 1e-5:
            print("BLANK RENDER:", fn); sys.exit(1)
    return files


def write_report(spec, out, name, results, files, glb, n_obj):
    from collections import Counter
    cnt = Counter(o["status"] for _, o, _, _ in Ctx.built)
    lines = [f"# {spec['project']}", "",
             "**Photo-derived model. Illustrative only — not a measured survey and not a contract document.**", "",
             "## Provenance", f"- Objects: {n_obj}; by status: " + ", ".join(f"{k} {v}" for k, v in sorted(cnt.items())),
             "- Confirmed: **0** (no drawings or measurements exist for this room)",
             f"- Source P1: {spec['sources'][0]['ref']}",
             f"- Scale references: {spec['sources'][0]['scale_refs']}",
             f"- Limits: {spec['sources'][0]['limits']}", "",
             "## Groups", "| group | status | source / basis |", "|---|---|---|"]
    for g, m in spec["groups"].items():
        lines.append(f"| {g} | {m['status']} | {m.get('source') or m.get('basis')} {('— ' + m['note']) if m.get('note') else ''} |")
    lines += ["", "## Checks (internal consistency + builder fidelity; none are document-driven)", "| result | check | expected | actual |", "|---|---|---|---|"]
    for r in results:
        lines.append(f"| {'PASS' if r['ok'] else 'FAIL'} | {r['check']} | {r['expected']} | {r['actual']} |")
    lines += ["", "## Files", f"- {name}.blend (editable)", f"- {name}.glb ({'written' if glb else 'FAILED'})"] + [f"- {f}" for f in files]
    (out / "report.md").write_text("\n".join(lines) + "\n")
    (out / "report.json").write_text(json.dumps({"project": spec["project"], "checks": results, "files": files, "status_counts": dict(cnt)}, indent=2, default=str))


if __name__ == "__main__":
    main()
