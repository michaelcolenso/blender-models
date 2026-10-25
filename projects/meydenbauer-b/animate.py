"""8-phase 4D construction sequence of the Building B under-slab re-pipe (bid-team planning film).

Builds on realism.build() (the construction-phase scene) and adds what the sequence needs:
existing cast iron from the demolition plan (meydenbauer-b.existing.json), removable slab,
finish and soil plugs over the trenches, a 5" pour-back, toilets and vanities at their P1.02
connections, new ABS that grows from each tie-in upstream at 1/4"/ft, a water-test fill, a
dark studio stage with a 3-point light rig, and a baked camera move. Every timed change is
an object property or transform keyframe (Bezier, auto-clamped), so the .blend stays editable.

Phases (4 s each; 240 frames at 60 fps):
  01 Existing + investigation   02 Staging + fixture removal   03 Demolition + excavation
  04 New ABS installation       05 Water test                  06 Backfill + slab pourback
  07 Patching + finishes        08 Fixture reinstatement

Usage:
  python projects/meydenbauer-b/animate.py --no-render                 # build, check, save .blend
  python projects/meydenbauer-b/animate.py --stills                    # 8 check frames (one per phase)
  python projects/meydenbauer-b/animate.py --frames 1:1920:8 --res 0.33 --samples 8 --tag proxy
  python projects/meydenbauer-b/animate.py --device OPTIX --samples 128 --worker 0/2   # RunPod
"""
import argparse, json, math, sys, time
from pathlib import Path

import bpy, bmesh
import numpy as np
from bpy_extras import anim_utils
from shapely.geometry import LineString, Polygon, box
from shapely.ops import unary_union

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import realism as R  # noqa: E402

OUT = ROOT / "build" / "meydenbauer-b" / "anim"
EXIST = json.loads((HERE / "meydenbauer-b.existing.json").read_text())
PHASES = ["01 Existing + investigation", "02 Staging + fixture removal", "03 Demolition + excavation",
          "04 New ABS installation", "05 Water test", "06 Backfill + slab pourback",
          "07 Patching + finishes", "08 Fixture reinstatement"]
PHASE_S = 4.0                       # seconds per phase
TRANS_S = 0.75                      # standard transition (45 frames at 60 fps)
POURBACK = 5 / 12                   # 10/P5.1: pour-back the thicker of existing or 5"
LIFT_FIXTURE = 1.5 / R.FT           # 1.5 m
LIFT_FINISH = 0.5 / R.FT            # 0.5 m
UNIT_ORDER = ["B-101", "B-102", "B-103", "B-104"]
STUDIO_BG = (0.0033, 0.0052, 0.0080)    # #0B1017 in linear RGB

# Camera key poses: (seconds, camera xyz ft, target xyz ft, lens mm). The wide keys (0, 4, 8, 27, 32 s)
# are fitted so the whole building clears the HUD bands; validate() re-checks it every build. Plan frame as everywhere:
# x south along the building, y west, z up from finished floor.
CAMERA = [
    (0.0, (-22.9, 185.3, 152.8), (72.5, 30.6, -2), 35),
    (4.0, (18.9, 179.8, 129.5), (76.6, 32.2, -2), 35),
    (8.0, (53.2, 175.9, 133.2), (79.7, 30.1, -2), 35),
    (11.0, (146, 76, 66), (132, 28, -2), 35),
    (14.0, (160, 56, 52), (134, 24, -3), 35),
    (17.0, (156, 18, 50), (133, 24, -3), 35),
    (20.0, (138, -2, 58), (126, 28, -2.5), 35),
    (23.0, (176, 30, 84), (108, 30, -2), 35),
    (27.0, (239.4, 173.7, 178.3), (95.1, 29.4, -2), 35),
    (32.0, (168.8, 183.9, 137.1), (87.6, 31.0, -2), 35),
]


# ------------------------------------------------------------------------------------------ timing

class Clock:
    def __init__(self, fps):
        self.fps = fps
        self.end = int(round(len(PHASES) * PHASE_S * fps))

    def f(self, s):
        return int(round(s * self.fps)) + 1

    def phase_frame(self, i, s=0.0):
        return self.f(i * PHASE_S + s)


def key(o, prop, frame, value):
    """Keyframe a custom float property (Bezier, auto-clamped handles)."""
    o[prop] = float(value)
    o.keyframe_insert(f'["{prop}"]', frame=frame)


def key_z(o, frame, z_ft):
    o.location.z = z_ft * R.FT
    o.keyframe_insert("location", index=2, frame=frame)


def key_scale(o, frame, s, axes=(0, 1, 2)):
    for a in axes:
        o.scale[a] = s
    for a in axes:
        o.keyframe_insert("scale", index=a, frame=frame)


def fcurves(o):
    ad = o.animation_data
    if not ad or not ad.action:
        return []
    cb = anim_utils.action_get_channelbag_for_slot(ad.action, ad.action_slot)
    return list(cb.fcurves) if cb else []


# ------------------------------------------------------------------------------------------ materials

_augmented = set()


def augment(m, glow=None, water=False, sweep=None):
    """Wrap a material's surface: + glow emission (object property 'glow'), + water emission
    ('water', with a travelling wave), + sweep band (world x), then mix to transparent by the
    object property 'vanish' (missing property = 0 = fully visible)."""
    if m.name in _augmented:
        return m
    _augmented.add(m.name)
    n, l = m.node_tree.nodes, m.node_tree.links
    out = next(x for x in n if x.type == "OUTPUT_MATERIAL" and x.is_active_output)
    src = out.inputs["Surface"].links[0].from_socket

    def attr(name):
        a = n.new("ShaderNodeAttribute"); a.attribute_type = "OBJECT"; a.attribute_name = name
        return a.outputs["Fac"]

    def add_emission(color, strength_socket):
        em = n.new("ShaderNodeEmission"); em.inputs["Color"].default_value = (*color, 1)
        l.new(strength_socket, em.inputs["Strength"])
        ad = n.new("ShaderNodeAddShader"); l.new(src, ad.inputs[0]); l.new(em.outputs[0], ad.inputs[1])
        return ad.outputs[0]

    def mul(a, b_value=None, b_socket=None):
        mm = n.new("ShaderNodeMath"); mm.operation = "MULTIPLY"
        l.new(a, mm.inputs[0])
        if b_socket is not None:
            l.new(b_socket, mm.inputs[1])
        else:
            mm.inputs[1].default_value = b_value
        return mm.outputs[0]
    if glow:
        color, k = glow
        src = add_emission(color, mul(attr("glow"), k))
    if water:
        tc = n.new("ShaderNodeTexCoord")
        wv = n.new("ShaderNodeTexWave"); wv.wave_type = "BANDS"; wv.bands_direction = "DIAGONAL"
        wv.inputs["Scale"].default_value = 0.6; wv.inputs["Distortion"].default_value = 0.0
        ph = n.new("ShaderNodeValue"); ph.name = "water_phase"; ph.label = "water_phase (keyframed)"
        l.new(tc.outputs["Object"], wv.inputs["Vector"]); l.new(ph.outputs[0], wv.inputs["Phase Offset"])
        pulse = n.new("ShaderNodeMapRange"); pulse.inputs["To Min"].default_value = 0.45
        l.new(wv.outputs["Fac"], pulse.inputs["Value"])
        src = add_emission((0.10, 0.55, 1.0), mul(mul(attr("water"), b_socket=pulse.outputs["Result"]), 9.0))
    if sweep:
        color, k, width_ft = sweep
        geo = n.new("ShaderNodeNewGeometry"); sep = n.new("ShaderNodeSeparateXYZ")
        l.new(geo.outputs["Position"], sep.inputs["Vector"])
        sx = n.new("ShaderNodeValue"); sx.name = "sweep_x"; sx.label = "sweep_x m (keyframed)"
        d = n.new("ShaderNodeMath"); d.operation = "SUBTRACT"
        l.new(sep.outputs["X"], d.inputs[0]); l.new(sx.outputs[0], d.inputs[1])
        ab = n.new("ShaderNodeMath"); ab.operation = "ABSOLUTE"; l.new(d.outputs[0], ab.inputs[0])
        band = n.new("ShaderNodeMapRange"); band.inputs["From Min"].default_value = 0
        band.inputs["From Max"].default_value = width_ft * R.FT
        band.inputs["To Min"].default_value = 1; band.inputs["To Max"].default_value = 0
        l.new(ab.outputs[0], band.inputs["Value"])
        src = add_emission(color, mul(band.outputs["Result"], k))
    t = n.new("ShaderNodeBsdfTransparent")
    mix = n.new("ShaderNodeMixShader")
    l.new(attr("vanish"), mix.inputs["Fac"]); l.new(src, mix.inputs[1]); l.new(t.outputs[0], mix.inputs[2])
    l.new(mix.outputs[0], out.inputs["Surface"])
    return m


def ghost_material():
    """Ghosted walls: mostly transparent, white rim at grazing angles (Layer Weight > Facing).
    No refraction, so it costs transparent bounces only, not glass noise."""
    m = bpy.data.materials.new("Architectural ghost (walls)"); m.use_nodes = True
    n, l = m.node_tree.nodes, m.node_tree.links
    out = n["Material Output"]; b = n["Principled BSDF"]
    b.inputs["Base Color"].default_value = (0.82, 0.86, 0.92, 1); b.inputs["Roughness"].default_value = 0.35
    lw = n.new("ShaderNodeLayerWeight"); lw.inputs["Blend"].default_value = 0.25
    rim = n.new("ShaderNodeMapRange"); rim.inputs["To Min"].default_value = 0.025; rim.inputs["To Max"].default_value = 0.45
    l.new(lw.outputs["Facing"], rim.inputs["Value"])
    em = n.new("ShaderNodeEmission"); em.inputs["Color"].default_value = (0.75, 0.85, 1.0, 1)
    k = n.new("ShaderNodeMath"); k.operation = "MULTIPLY"; k.inputs[1].default_value = 0.25
    l.new(lw.outputs["Facing"], k.inputs[0]); l.new(k.outputs[0], em.inputs["Strength"])
    ad = n.new("ShaderNodeAddShader"); l.new(b.outputs[0], ad.inputs[0]); l.new(em.outputs[0], ad.inputs[1])
    t = n.new("ShaderNodeBsdfTransparent")
    mix = n.new("ShaderNodeMixShader")
    amt = n.new("ShaderNodeValue"); amt.name = "ghost_amount"; amt.label = "ghost_amount (keyframed)"
    amt.outputs[0].default_value = 1.0
    op = n.new("ShaderNodeMath"); op.operation = "MULTIPLY"
    l.new(rim.outputs["Result"], op.inputs[0]); l.new(amt.outputs[0], op.inputs[1])
    inv = n.new("ShaderNodeMath"); inv.operation = "SUBTRACT"; inv.inputs[0].default_value = 1.0
    l.new(op.outputs[0], inv.inputs[1]); l.new(inv.outputs[0], mix.inputs["Fac"])
    l.new(ad.outputs[0], mix.inputs[1]); l.new(t.outputs[0], mix.inputs[2]); l.new(mix.outputs[0], out.inputs["Surface"])
    return m


def cast_iron_material():
    m = bpy.data.materials.new("Existing cast iron (rusted)"); m.use_nodes = True
    n, l = m.node_tree.nodes, m.node_tree.links
    b = n["Principled BSDF"]; b.inputs["Metallic"].default_value = 0.8; b.inputs["Roughness"].default_value = 0.7
    tc = n.new("ShaderNodeTexCoord")
    nz = n.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 45; nz.inputs["Detail"].default_value = 12
    l.new(tc.outputs["Object"], nz.inputs["Vector"])
    ramp = n.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (0.10, 0.045, 0.02, 1); ramp.color_ramp.elements[1].color = (0.36, 0.15, 0.05, 1)
    l.new(nz.outputs["Fac"], ramp.inputs["Fac"]); l.new(ramp.outputs["Color"], b.inputs["Base Color"])
    bp = n.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = 0.5
    l.new(nz.outputs["Fac"], bp.inputs["Height"]); l.new(bp.outputs["Normal"], b.inputs["Normal"])
    return m


# ------------------------------------------------------------------------------------------ scene

def cleanup():
    """Strip the still-frame dressing that the sequence replaces."""
    drop = [o for o in bpy.data.objects if o.name.startswith(("Lawn", "Sun (", "Pulled toilet"))]
    work = bpy.data.collections["New waste piping and bedding"]
    drop += [o for o in work.objects if not o.name.startswith("Pipe bedding")]
    ceil = bpy.data.collections["Ceilings"]
    drop += [o for o in ceil.objects if o.type == "LIGHT"]
    for o in drop:
        bpy.data.objects.remove(o, do_unlink=True)
    ceil.hide_render = True
    ceil.hide_viewport = True


def stage(M):
    sc = bpy.context.scene
    w = bpy.data.worlds.new("Studio"); sc.world = w; w.use_nodes = True
    w.node_tree.nodes["Background"].inputs["Color"].default_value = (*STUDIO_BG, 1)
    w.node_tree.nodes["Background"].inputs["Strength"].default_value = 1.0
    floor = principled("Studio floor", (0.012, 0.015, 0.02), 0.35)
    bm = bmesh.new()
    R.prism(bm, box(-200, -200, 360, 260), -R.GROUND - 0.01, -R.GROUND - 0.05)
    R.obj("Studio floor", bm, floor, sc.collection)
    rig = R.coll("Studio light rig")
    for name, loc, energy, color, size in [
        ("Key (warm)", (190, -40, 150), 6.0e4, (1.0, 0.86, 0.70), 60),
        ("Rim (cool)", (-60, 140, 90), 4.5e4, (0.62, 0.78, 1.0), 50),
        ("Fill (overhead)", (82, 30, 190), 2.2e4, (0.95, 0.97, 1.0), 120),
    ]:
        ld = bpy.data.lights.new(name, "AREA"); ld.energy = energy; ld.color = color
        ld.shape = "DISK"; ld.size = size * R.FT
        lo = bpy.data.objects.new(name, ld); rig.objects.link(lo)
        lo.location = R.P(*loc)
        lo.rotation_euler = (R.P(82, 30, -3) - lo.location).to_track_quat("-Z", "Y").to_euler()


def principled(name, rgb, rough):
    return R.principled(name, rgb, rough)


def ghost_walls(M):
    g = ghost_material()
    for name in ("Walls (P2.1)", "Door and window headers / sills", "Glazing"):
        o = bpy.data.objects.get(name)
        if o:
            o.data.materials.clear(); o.data.materials.append(g)
            o.visible_shadow = False


def plugs(M, I, c):
    """Removable pieces over the trench: slab, finish, soil; plus the new pour-back."""
    trench = I["trench"]; env = I["env"]
    out = {"slab": [], "finish": [], "soil": [], "pour": []}
    tile = unary_union([Polygon(r["ring_ft"]).buffer(0) for r in R.SHELL["rooms"] if r["name"] in ("BATH", "LAUNDRY")] +
                       [box(*f["box_ft"][0], *f["box_ft"][1]) for f in R.SHELL["fixtures"] if f["kind"] == "SHR"])
    pour_mat = R.assets.pbr(R.principled("Pour-back concrete (new)", (1, 1, 1), 0.7), DATA, "brushed_concrete",
                            tint=(1.18, 1.17, 1.13), rough=(0.55, 0.85), bump=0.1, scale=0.5, variation=0.4)
    for unit in UNIT_ORDER:
        x0, x1 = R.UNITS[unit]
        ub = box(x0, -30, x1, 100)
        for i, p in enumerate(R.polys(trench.intersection(env).intersection(ub))):
            out["slab"].append(R.solid(f"{unit} slab cut-out {i}", p, 0.0, -R.SLAB, M["slab"], c, unit=unit,
                                       status="assumed", basis="saw-cut along the S2 trench footprint; 4\" assumed"))
            out["pour"].append(R.solid(f"{unit} pour-back {i}", p, 0.0, -POURBACK, pour_mat, c, unit=unit,
                                       status="provisional", source="10/P5.1: thicker of existing or 5\" min"))
        band = trench.buffer(0.5, join_style="mitre").intersection(R.unit_floor(I, unit))
        for i, p in enumerate(R.polys(band)):
            mat = M["tile"] if p.intersection(tile).area > 0.5 * p.area else M["wood"]
            out["finish"].append(R.solid(f"{unit} finish patch {i}", p, R.FINISH, 0.0, mat, c, unit=unit,
                                         status="assumed", basis="finish removed 6\" past the saw-cut (assumed)"))
        soil = trench.intersection(ub).buffer(-0.003)
        if not soil.is_empty:
            o = R.solid(f"{unit} trench soil", soil, -R.SLAB, R.trench_bottom, M["soil"], c, densify=0.75, unit=unit)
            zmin = min(v.co.z for v in o.data.vertices)
            for v in o.data.vertices:
                v.co.z -= zmin
            o.location.z = zmin
            o["zmin_ft"] = zmin / R.FT
            out["soil"].append(o)
    return out


def existing_pipes(M, c):
    ci = cast_iron_material()
    objs = []
    for i, r in enumerate(EXIST["runs"]):
        od = R.OD_IN.get(r["nominal_in"], 4.5) * 1.06
        cu = bpy.data.curves.new(f'{r["unit"]} existing CI {i:02d}', "CURVE"); cu.dimensions = "3D"
        cu.bevel_depth = od / 24 * R.FT; cu.bevel_resolution = 4; cu.use_fill_caps = True
        sp = cu.splines.new("POLY"); sp.points.add(len(r["points_ft"]) - 1)
        for pt, (x, y) in zip(sp.points, r["points_ft"]):
            pt.co = (*R.P(x, y, R.trench_bottom(x, y) + R.BEDDING + od / 24), 1)
        o = bpy.data.objects.new(cu.name, cu); c.objects.link(o); o.data.materials.append(ci)
        o["unit"] = r["unit"]; o["status"] = "provisional"; o["source"] = "P1.01 hatched demolition centreline"
        o["basis"] = "depth assumed = new pipe profile; OD display only"
        objs.append(o)
    return objs, ci


def route_marks(c):
    """Locate-and-mark paint along the P1.01 routes on the finished floor (investigation phase)."""
    m = R.principled("Locate marking paint", (1.0, 0.45, 0.05), 0.6)
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Emission Color"].default_value = (1.0, 0.42, 0.04, 1); b.inputs["Emission Strength"].default_value = 3.0
    augment(m)
    out = []
    for i, r in enumerate(EXIST["runs"]):
        cu = bpy.data.curves.new(f'{r["unit"]} route mark {i:02d}', "CURVE"); cu.dimensions = "3D"
        cu.bevel_depth = 0.07 * R.FT; cu.bevel_resolution = 2
        sp = cu.splines.new("POLY"); sp.points.add(len(r["points_ft"]) - 1)
        for pt, (x, y) in zip(sp.points, r["points_ft"]):
            pt.co = (*R.P(x, y, R.FINISH + 0.03), 1)
        o = bpy.data.objects.new(cu.name, cu); c.objects.link(o); o.data.materials.append(m)
        o["x_min"] = min(x for x, _ in r["points_ft"]); o["unit"] = r["unit"]
        out.append(o)
    return out


def new_pipes(M, c):
    """New ABS per P1.02, each run oriented downstream -> upstream so bevel_factor_end grows it."""
    abs_m = R.principled("New ABS DWV (anim)", (0.018, 0.018, 0.02), 0.2)
    augment(abs_m, glow=((0.1, 0.95, 1.0), 14.0), water=True)
    runs, nodes, lf = [], [], 0.0
    for u in R.SPEC["units"]:
        N = u["nodes"]
        zc = lambda k, nom: -(R.TIE_DEPTH - R.SLOPE * N[k]["flow_ft"]) + R.OD_IN[nom] / 24
        deg = {}
        for i, e in enumerate(u["edges"]):
            nom = e["nominal_in"]
            a, b = (e["a"], e["b"]) if N[e["a"]]["flow_ft"] <= N[e["b"]]["flow_ft"] else (e["b"], e["a"])
            cu = bpy.data.curves.new(f'{u["unit"]}-R{i:03d}', "CURVE"); cu.dimensions = "3D"
            cu.bevel_depth = R.OD_IN[nom] / 24 * R.FT; cu.bevel_resolution = 6; cu.use_fill_caps = True
            sp = cu.splines.new("POLY"); sp.points.add(1)
            sp.points[0].co = (*R.P(*N[a]["xy_ft"], zc(a, nom)), 1)
            sp.points[1].co = (*R.P(*N[b]["xy_ft"], zc(b, nom)), 1)
            o = bpy.data.objects.new(cu.name, cu); c.objects.link(o); o.data.materials.append(abs_m)
            o["nominal_in"] = nom; o["length_ft"] = round(e["length_ft"], 3); o["status"] = "provisional"
            o["flow_lo"] = N[a]["flow_ft"]; o["flow_hi"] = N[b]["flow_ft"]; o["unit"] = u["unit"]
            runs.append(o); lf += e["length_ft"]
            for k in (a, b):
                deg.setdefault(k, []).append(nom)
        for k, noms in deg.items():
            if len(noms) < 2:
                continue
            nom = max(noms)
            bpy.ops.mesh.primitive_uv_sphere_add(radius=R.OD_IN[nom] / 24 * 1.18 * R.FT, segments=20, ring_count=12,
                                                 location=R.P(*N[k]["xy_ft"], zc(k, nom)))
            s = bpy.context.object; s.name = f'{u["unit"]} fitting'; R.move(s, c); s.data.materials.append(abs_m)
            s["flow"] = N[k]["flow_ft"]; nodes.append(s)
        for e in u["ends"]:
            if e["kind"] == "TEE":
                continue
            k = e["node"]; x, y = N[k]["xy_ft"]
            nom = 4 if e["kind"] == "STACK-4" else 3 if e["kind"] in ("STACK-3", "WC", "WB") else 2
            z0 = zc(k, nom); top = 3.0 if e["kind"].startswith("STACK") else 0.35
            bpy.ops.mesh.primitive_cylinder_add(radius=R.OD_IN[nom] / 24 * R.FT, depth=(top - z0) * R.FT,
                                                location=R.P(x, y, (top + z0) / 2), vertices=24)
            s = bpy.context.object; s.name = f'{u["unit"]} {e["kind"]} riser'; R.move(s, c); s.data.materials.append(abs_m)
            s["flow"] = N[k]["flow_ft"]; nodes.append(s)
            bpy.ops.mesh.primitive_cylinder_add(radius=R.OD_IN[nom] / 24 * R.FT * 1.15, depth=0.14 * R.FT,
                                                location=R.P(x, y, top + 0.07), vertices=24)
            cap = bpy.context.object; cap.name = f'{u["unit"]} test plug'; R.move(cap, c)
            cap.data.materials.append(augment(M["cap"]))
            cap["is_cap"] = 1; nodes.append(cap)
    return runs, nodes, lf


def fixtures(M, I, c):
    """Toilets and vanities at the P1.02 WC / LAV connections (geometry illustrative)."""
    out = []
    toilet = R.make_toilet(M)
    for m in toilet.data.materials:
        augment(m)
    for mname in ("cabinet", "quartz"):
        augment(M[mname])
    for u in R.SPEC["units"]:
        N = u["nodes"]
        for e in u["ends"]:
            if e["kind"] not in ("WC", "LAV"):
                continue
            x, y = N[e["node"]]["xy_ft"]
            wpt, n_in = R.nearest_wall(I["walls"], (x, y))
            yaw = math.atan2(-n_in[1], n_in[0])
            if e["kind"] == "WC":
                t = toilet.copy(); t.data = toilet.data; c.objects.link(t)
                t.location = R.P(x, y, R.FINISH); t.rotation_euler = (0, 0, yaw)
                t.name = f'{u["unit"]} toilet'; t["unit"] = u["unit"]; out.append(t)
            else:
                ctr = (wpt[0] + n_in[0] * 0.9, wpt[1] + n_in[1] * 0.9)
                d = (-n_in[1], n_in[0])
                ls = LineString([(ctr[0] - d[0] * 1.0, ctr[1] - d[1] * 1.0), (ctr[0] + d[0] * 1.0, ctr[1] + d[1] * 1.0)])
                body = ls.buffer(0.85, cap_style="flat")
                bm = bmesh.new(); R.prism(bm, body, 2.75, R.FINISH)
                R.prism(bm, ls.buffer(0.92, cap_style="flat").buffer(0.04, join_style="mitre"), 2.9, 2.75)
                # one object, two materials, so the top fades with the cabinet
                v = R.obj(f'{u["unit"]} vanity', bm, [M["cabinet"], M["quartz"]], c, unit=u["unit"], status="assumed",
                          basis="vanity 24x21 in with quartz top at the LAV connection; size assumed")
                R.set_face_materials(v, lambda ctr, n: 1 if ctr[2] > 2.749 else 0)
                v["unit"] = u["unit"]; out.append(v)
    bpy.data.objects.remove(toilet)
    return out


def bath_lights(c):
    lights = []
    for r in R.SHELL["rooms"]:
        if r["name"] != "BATH" or not r["ch_ft"]:
            continue
        q = Polygon(r["ring_ft"]).representative_point()
        ld = bpy.data.lights.new("Bath light", "POINT"); ld.energy = 0.0; ld.color = (1.0, 0.80, 0.58)
        ld.shadow_soft_size = 0.25
        lo = bpy.data.objects.new("Bath light", ld); c.objects.link(lo)
        lo.location = R.P(q.x, q.y, r["ch_ft"] - 0.6)
        lights.append(lo)
    return lights


# ------------------------------------------------------------------------------------------ choreography

def choreograph(clk, S):
    T = TRANS_S
    ph = lambda i, s=0.0: clk.phase_frame(i, s)
    dur = lambda s: max(1, int(round(s * clk.fps)))
    uidx = lambda o: UNIT_ORDER.index(o["unit"]) if "unit" in o else 0

    # 01 investigation: x-ray windows over the trench routes and a sonar sweep along the cast iron
    for o in S["slab"] + S["finish"] + S["soil"]:
        key(o, "vanish", ph(0, 0.5), 0); key(o, "vanish", ph(0, 1.25), 0.82)
        key(o, "vanish", ph(0, 3.1), 0.82); key(o, "vanish", ph(0, 3.85), 0)
    sx = S["ci_mat"].node_tree.nodes["sweep_x"]
    for f, x in ((ph(0, 0.8), -20), (ph(0, 3.4), 180)):
        sx.outputs[0].default_value = x * R.FT
        sx.outputs[0].keyframe_insert("default_value", frame=f)
    sweep_t = lambda x: 0.8 + (x + 20) / 200 * 2.6          # when the sweep passes plan x
    for o in S["marks"]:
        s0 = sweep_t(o["x_min"])
        key(o, "vanish", 1, 1); key(o, "vanish", ph(0, s0), 1); key(o, "vanish", ph(0, s0 + 0.35), 0)
        u0 = 0.5 + 0.15 * uidx(o)
        key(o, "vanish", ph(2, u0), 0); key(o, "vanish", ph(2, u0 + 0.3), 1)
    ga = bpy.data.materials["Architectural ghost (walls)"].node_tree.nodes["ghost_amount"].outputs[0]
    for f, v in ((ph(2, 0.3), 1.0), (ph(2, 1.8), 0.35), (ph(5, 1.0), 0.35), (ph(5, 2.5), 1.0)):
        ga.default_value = v; ga.keyframe_insert("default_value", frame=f)
    for o in S["pour"]:
        key(o, "vanish", 1, 1)

    # 02 staging: protection in, props in, work lights on, fixtures lifted out
    for o in S["protection"]:
        key(o, "vanish", ph(1, 0.0), 1); key(o, "vanish", ph(1, 0.2 + T), 0)
    for e in S["props"]:
        key_scale(e, ph(1, 0.4), 0.0); key_scale(e, ph(1, 0.4 + T), 1.0)
    for lo in S["work_lights"]:
        lo.data.energy = 0; lo.data.keyframe_insert("energy", frame=ph(1, 0.9))
        lo.data.energy = 220; lo.data.keyframe_insert("energy", frame=ph(1, 0.9 + T))
    for o in S["fixtures"]:
        s0 = 1.0 + 0.25 * uidx(o)
        key_z(o, ph(1, s0), 0); key(o, "vanish", ph(1, s0), 0)
        key_z(o, ph(1, s0 + T), LIFT_FIXTURE); key(o, "vanish", ph(1, s0 + T), 1)

    # 03 demolition + excavation: saw-cut glow, cut-outs lifted away, soil dug down
    for o in S["slab"]:
        s0 = 0.5 + 0.15 * uidx(o)
        key(o, "glow", ph(2, 0.1), 0); key(o, "glow", ph(2, 0.45), 1)
        key(o, "glow", ph(2, s0 + T), 0)
    for o in S["slab"] + S["finish"]:
        s0 = 0.5 + 0.15 * uidx(o)
        key_z(o, ph(2, s0), 0); key(o, "vanish", ph(2, s0), 0)
        key_z(o, ph(2, s0 + T), 3.28); key(o, "vanish", ph(2, s0 + T), 1)
    for o in S["soil"]:
        s0 = 1.3 + 0.2 * uidx(o)
        key_scale(o, ph(2, s0), 1.0, axes=(2,)); key_scale(o, ph(2, s0 + 1.6), 0.03, axes=(2,))
        key(o, "vanish", ph(2, s0 + 1.6), 0); key(o, "vanish", ph(2, s0 + 1.9), 1)

    # 04 new ABS: cast iron out, bedding in, pipe grows from each tie-in upstream with a cyan front
    for o in S["ci"]:
        key_z(o, ph(3, 0.0), 0); key(o, "vanish", ph(3, 0.0), 0)
        key_z(o, ph(3, T), 0.8); key(o, "vanish", ph(3, T), 1)
    key(S["bedding"], "vanish", ph(3, 0.0), 1); key(S["bedding"], "vanish", ph(3, 0.6), 0)
    fmax = max(o["flow_hi"] for o in S["abs"])
    k = 2.6 / fmax                                  # seconds per foot of flow path
    t_at = lambda flow: ph(3, 0.95 + k * flow)
    for o in S["abs"]:
        a, b = t_at(o["flow_lo"]), max(t_at(o["flow_hi"]), t_at(o["flow_lo"]) + 1)
        o.data.bevel_factor_end = 0.0; o.data.keyframe_insert("bevel_factor_end", frame=a)
        o.data.bevel_factor_end = 1.0; o.data.keyframe_insert("bevel_factor_end", frame=b)
        key(o, "vanish", a - 1, 1); key(o, "vanish", a, 0)
        key(o, "glow", a - 1, 0); key(o, "glow", a, 1); key(o, "glow", b, 1); key(o, "glow", b + dur(0.5), 0)
    for o in S["nodes"]:
        if "is_cap" in o:
            continue
        f = t_at(o["flow"])
        key(o, "vanish", f - 1, 1); key(o, "vanish", f, 0)
        key(o, "glow", f, 1); key(o, "glow", f + dur(0.5), 0)

    # 05 water test: plugs in, fill from the tie-in up, hold, drain, plugs out
    caps = [o for o in S["nodes"] if "is_cap" in o]
    for o in caps:
        key(o, "vanish", 1, 1); key(o, "vanish", ph(4, 0.0), 1); key(o, "vanish", ph(4, 0.3), 0)
        key(o, "vanish", ph(4, 3.6), 0); key(o, "vanish", ph(4, 3.95), 1)
    kf = 1.7 / fmax
    for o in S["abs"]:
        f0 = ph(4, 0.35 + kf * o["flow_lo"])
        key(o, "water", f0 - 1, 0); key(o, "water", f0 + dur(0.25), 1)
        key(o, "water", ph(4, 3.3), 1); key(o, "water", ph(4, 3.8), 0)
    wp = S["abs_mat"].node_tree.nodes["water_phase"]
    for f, v in ((ph(4, 0.0), 0.0), (ph(4, 4.0), 40.0)):
        wp.outputs[0].default_value = v; wp.outputs[0].keyframe_insert("default_value", frame=f)

    # 06 backfill + pour-back: soil rises to the pour-back underside, new concrete drops in
    for o in S["soil"]:
        s0 = 0.1 + 0.2 * uidx(o)
        z0 = o["zmin_ft"]
        target = (-POURBACK - z0) / (-R.SLAB - z0)
        key(o, "vanish", ph(5, s0) - 1, 1); key(o, "vanish", ph(5, s0), 0)
        key_scale(o, ph(5, s0), 0.03, axes=(2,)); key_scale(o, ph(5, s0 + 1.5), target, axes=(2,))
    for o in S["pour"]:
        x = o.bound_box[0][0] / R.FT
        s0 = 2.0 + 0.9 * x / 160
        key(o, "vanish", ph(5, s0), 1); key_z(o, ph(5, s0), 1.0)
        key(o, "vanish", ph(5, s0 + T), 0); key_z(o, ph(5, s0 + T), 0)

    # 07 finishes: patches cascade down from +0.5 m with a fade-in, south along the building
    for o in S["finish"]:
        x = sum(v[0] for v in o.bound_box) / 8 / R.FT
        s0 = 0.3 + 2.2 * max(0.0, x) / 165
        key_z(o, ph(6, 0.0), LIFT_FINISH); key(o, "vanish", ph(6, s0), 1); key_z(o, ph(6, s0), LIFT_FINISH)
        key_z(o, ph(6, s0 + T), 0); key(o, "vanish", ph(6, s0 + T), 0)

    # 08 reinstatement: protection out, fixtures back, bath lights up
    for o in S["protection"]:
        key(o, "vanish", ph(7, 0.0), 0); key(o, "vanish", ph(7, T), 1)
    for e in S["props"]:
        key_scale(e, ph(7, 0.0), 1.0); key_scale(e, ph(7, T), 0.0)
    for lo in S["work_lights"]:
        lo.data.energy = 220; lo.data.keyframe_insert("energy", frame=ph(7, 0.0))
        lo.data.energy = 0; lo.data.keyframe_insert("energy", frame=ph(7, T))
    for o in S["fixtures"]:
        s0 = 0.6 + 0.25 * uidx(o)
        key_z(o, ph(7, s0), LIFT_FIXTURE); key(o, "vanish", ph(7, s0), 1)
        key_z(o, ph(7, s0 + T), 0); key(o, "vanish", ph(7, s0 + T), 0)
    for lo in S["bath_lights"]:
        lo.data.energy = 0; lo.data.keyframe_insert("energy", frame=ph(7, 1.8))
        lo.data.energy = 90; lo.data.keyframe_insert("energy", frame=ph(7, 2.8))


def hide_vanished(clk):
    """Hide an object from render on every frame where it is fully faded (vanish >= 0.999).
    A fully transparent surface still costs a transparent bounce per crossing; behind several
    ghosted walls the rays run out of bounces and render black. Children inherit the parent's
    visibility (a vanity top fades with its cabinet). Returns the number of objects keyed."""
    n = 0
    for o in bpy.data.objects:
        fc = next((c for c in fcurves(o) if c.data_path == '["vanish"]'), None)
        if fc is None:
            continue
        hidden = [fc.evaluate(f) >= 0.999 for f in range(1, clk.end + 1)]
        targets = [o] + list(o.children_recursive)
        for t in targets:
            prev = None
            for f, h in enumerate(hidden, start=1):
                if h != prev:
                    t.hide_render = h
                    t.keyframe_insert("hide_render", frame=f)
                    prev = h
        n += 1
    return n


def camera_rig(clk):
    """Camera + Camera_Target empty, path baked per frame (Catmull-Rom through the key poses)."""
    sc = bpy.context.scene
    cam = bpy.data.cameras.new("Sequence camera"); cam.lens = 35; cam.clip_start = 0.1; cam.clip_end = 500
    cam.dof.use_dof = True; cam.dof.aperture_fstop = 5.6
    co = bpy.data.objects.new("Sequence camera", cam); sc.collection.objects.link(co)
    tgt = bpy.data.objects.new("Camera_Target", None); sc.collection.objects.link(tgt)
    tgt.empty_display_type = "SPHERE"; tgt.empty_display_size = 0.5
    cam.dof.focus_object = tgt
    co.rotation_mode = "QUATERNION"
    ts = np.array([k[0] for k in CAMERA]); cp = np.array([k[1] for k in CAMERA], float); tp = np.array([k[2] for k in CAMERA], float)

    def catmull(P, s):
        i = int(np.clip(np.searchsorted(ts, s, side="right") - 1, 0, len(ts) - 2))
        u = (s - ts[i]) / (ts[i + 1] - ts[i])
        u = u * u * (3 - 2 * u) * 0.35 + u * 0.65            # slight ease at each key
        p0, p1, p2, p3 = P[max(i - 1, 0)], P[i], P[i + 1], P[min(i + 2, len(P) - 1)]
        return 0.5 * ((2 * p1) + (-p0 + p2) * u + (2 * p0 - 5 * p1 + 4 * p2 - p3) * u * u + (-p0 + 3 * p1 - 3 * p2 + p3) * u ** 3)
    prev = None
    for f in range(1, clk.end + 1):
        s = (f - 1) / clk.fps
        c = R.P(*catmull(cp, s)); t = R.P(*catmull(tp, s))
        q = (t - c).to_track_quat("-Z", "Y")
        if prev is not None and prev.dot(q) < 0:
            q.negate()
        prev = q.copy()
        co.location = c; co.rotation_quaternion = q; tgt.location = t
        co.keyframe_insert("location", frame=f); co.keyframe_insert("rotation_quaternion", frame=f)
        tgt.keyframe_insert("location", frame=f)
    for o in (co, tgt):
        for fc in fcurves(o):
            for kp in fc.keyframe_points:
                kp.interpolation = "LINEAR"
    sc.camera = co
    return co


# ------------------------------------------------------------------------------------------ build

DATA = None


def build(fps):
    global DATA
    _augmented.clear()
    stats = R.build(None)
    DATA = R.assets.fetch()
    cleanup()
    M = {m: bpy.data.materials[n] for m, n in [
        ("slab", "Slab concrete (CC0 scan)"), ("soil", "Excavated soil (CC0 scan)"), ("wood", "EHF engineered oak (CC0 scan)"),
        ("tile", "NS-2 porcelain 12x24 (procedural)"), ("gravel", "Pipe bedding gravel (CC0 scan)"),
        ("cabinet", "CAB-1 painted shaker"), ("quartz", "Quartz counter (CC0 scan)"), ("porcelain", "Vitreous china"),
        ("cap", "Test cap")]}
    augment(M["slab"], glow=((1.0, 0.38, 0.05), 12.0))
    for m in ("soil", "wood", "tile", "gravel", "porcelain"):
        augment(M[m])
    I = R.plan_inputs(None)
    c_seq = R.coll("Sequence (animated)")
    S = plugs(M, I, c_seq)
    for o in S["pour"]:
        augment(o.data.materials[0])
    S["ci"], S["ci_mat"] = existing_pipes(M, c_seq)
    augment(S["ci_mat"], sweep=((1.0, 0.55, 0.12), 25.0, 12.0))
    S["marks"] = route_marks(c_seq)
    S["abs"], S["nodes"], lf = new_pipes(M, c_seq)
    S["abs_mat"] = bpy.data.materials["New ABS DWV (anim)"]
    S["bedding"] = bpy.data.objects["Pipe bedding (2/P5.0)"]
    S["fixtures"] = fixtures(M, I, c_seq)
    temp = bpy.data.collections["Temporary protection and dust control"]
    S["protection"] = [o for o in temp.objects if o.type in ("MESH", "CURVE")]
    for o in S["protection"]:
        for m in o.data.materials:
            augment(m)
    S["work_lights"] = [o for o in temp.objects if o.type == "LIGHT"]
    props_c = bpy.data.collections["Props and fixtures (illustrative)"]
    S["props"] = [o for o in props_c.objects if o.type == "EMPTY" or o.name.startswith("5-gal")]
    S["bath_lights"] = bath_lights(c_seq)
    ghost_walls(M)
    stage(M)
    clk = Clock(fps)
    sc = bpy.context.scene
    sc.render.fps = fps; sc.frame_start = 1; sc.frame_end = clk.end
    for i, name in enumerate(PHASES):
        sc.timeline_markers.new(name, frame=clk.phase_frame(i))
    choreograph(clk, S)
    stats.update(hidden_when_faded=hide_vanished(clk))
    camera_rig(clk)
    stats.update(pipe_lf_anim=lf)
    return clk, S, stats


WIDE_SHOTS = (0.5, 2.0, 4.0, 6.0, 28.0, 30.0, 31.9)    # seconds that must show the whole building
FRAME_SAFE = (0.02, 0.98, 0.11, 0.86)                  # x0, x1, y0, y1 (normalized, y up): clear of the HUD bands


def framing(clk):
    """Projected bounds of the building envelope (slab to wall top) at each wide shot."""
    from bpy_extras.object_utils import world_to_camera_view
    sc = bpy.context.scene
    env = Polygon(R.SHELL["envelope_ft"])
    pts = [R.P(x, y, z) for x, y in env.exterior.coords for z in (-R.GROUND, R.WALL_TOP)]
    out = []
    for s_ in WIDE_SHOTS:
        sc.frame_set(clk.f(s_))
        v = [world_to_camera_view(sc, sc.camera, p) for p in pts]
        out.append((s_, (min(q.x for q in v), max(q.x for q in v), min(q.y for q in v), max(q.y for q in v))))
    return out


def validate(clk, S, stats):
    sc = bpy.context.scene
    errs = []
    if abs(stats["pipe_lf_anim"] - R.TAKE["totals"]["pipe_lf"]) > 0.05:
        errs.append(f'ABS length {stats["pipe_lf_anim"]:.2f} != takeoff')
    at = lambda i, s: clk.phase_frame(i, s)
    checks = [
        (at(0, 0.2), lambda: all(o.get("vanish", 0) < 0.01 for o in S["fixtures"]), "fixtures in place at start"),
        (at(0, 2.0), lambda: all(o["vanish"] > 0.8 for o in S["soil"]), "x-ray during investigation"),
        (at(2, 0.1), lambda: all(o["vanish"] > 0.99 for o in S["fixtures"]), "fixtures out before demolition"),
        (at(1, 0.0), lambda: all(o["vanish"] < 0.01 for o in S["marks"]), "routes marked by end of investigation"),
        (at(3, 0.0), lambda: all(o["vanish"] > 0.99 for o in S["marks"]), "marks gone with the slab"),
        (at(3, 0.9), lambda: all(o.data.bevel_factor_end < 1e-3 for o in S["abs"]), "no ABS before installation"),
        (at(3, 0.9), lambda: all(o["vanish"] > 0.99 for o in S["ci"]), "cast iron gone before ABS"),
        (at(4, 0.0), lambda: all(o.data.bevel_factor_end > 0.999 for o in S["abs"]), "all ABS installed by the test"),
        (at(4, 3.0), lambda: all(o["water"] > 0.99 for o in S["abs"]), "system full during hold"),
        (at(5, 0.0), lambda: all(o["water"] < 0.01 for o in S["abs"]), "drained before backfill"),
        (at(3, 0.5), lambda: all(o.scale.z < 0.05 for o in S["soil"]), "trenches excavated"),
        (at(6, 0.0), lambda: all(o["vanish"] < 0.01 for o in S["pour"]), "pour-back placed"),
        (clk.end, lambda: all(o["vanish"] < 0.01 and abs(o.location.z) < 1e-4 for o in S["fixtures"] + S["finish"]),
         "fixtures and finishes restored"),
        (clk.end, lambda: all(o["vanish"] > 0.99 for o in S["protection"]), "protection removed"),
    ]
    for f, test, label in checks:
        sc.frame_set(f)
        if not test():
            errs.append(f"frame {f}: {label}")
    for s_, box_ in framing(clk):
        if not (FRAME_SAFE[0] <= box_[0] and box_[1] <= FRAME_SAFE[1] and FRAME_SAFE[2] <= box_[2] and box_[3] <= FRAME_SAFE[3]):
            errs.append(f"t={s_:.1f}s: building leaves the safe frame {[round(v, 3) for v in box_]}")
    res = {"ok": not errs, "errors": errs, "frames": clk.end, "fps": clk.fps, "pipe_lf": round(stats["pipe_lf_anim"], 2),
           "existing_ci_runs": len(S["ci"]), "fixtures": len(S["fixtures"]), "checks": len(checks),
           "framing_checks": len(WIDE_SHOTS), "hidden_when_faded": stats.get("hidden_when_faded")}
    print("CHECKS", json.dumps(res), flush=True)
    if errs:
        sys.exit(1)
    return res


def render_frames(frames, res, samples, device, tag, worker):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    prefs = bpy.context.preferences.addons["cycles"].preferences
    if device != "CPU":
        prefs.compute_device_type = device; prefs.get_devices()
        for d in prefs.devices:
            d.use = d.type == device
        sc.cycles.device = "GPU"
    sc.cycles.samples = samples; sc.cycles.use_denoising = True; sc.cycles.denoiser = "OPENIMAGEDENOISE"
    sc.cycles.max_bounces = 6; sc.cycles.transparent_max_bounces = 24; sc.cycles.sample_clamp_indirect = 6
    sc.render.use_persistent_data = True
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.view_settings.view_transform = "AgX"; sc.view_settings.look = "AgX - Medium High Contrast"
    k, n = worker
    out = OUT / "frames" / tag; out.mkdir(parents=True, exist_ok=True)
    todo = [f for i, f in enumerate(frames) if i % n == k and not (out / f"{f:04d}.png").exists()]
    t0 = time.time()
    for j, f in enumerate(todo):
        sc.frame_set(f)
        tmp = out / f"{f:04d}.tmp.png"; sc.render.filepath = str(tmp)
        t = time.time(); bpy.ops.render.render(write_still=True); tmp.rename(out / f"{f:04d}.png")
        print(f"FRAME {f} {time.time() - t:.1f}s ({j + 1}/{len(todo)}, {time.time() - t0:.0f}s)", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fps", type=int, default=60)
    ap.add_argument("--no-render", action="store_true")
    ap.add_argument("--stills", action="store_true", help="one check frame per phase (2 s into each)")
    ap.add_argument("--frames", default="", help="start:end:step")
    ap.add_argument("--res", type=float, default=1.0, help="scale on 1920x1080")
    ap.add_argument("--samples", type=int, default=128)
    ap.add_argument("--device", default="CPU", choices=["CPU", "CUDA", "OPTIX"])
    ap.add_argument("--tag", default="final")
    ap.add_argument("--worker", default="0/1")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    clk, S, stats = build(a.fps)
    validate(clk, S, stats)
    if a.no_render:
        bpy.ops.file.pack_all()
        bpy.ops.wm.save_as_mainfile(filepath=str(OUT / "Meydenbauer-B-4D.blend"), compress=True)
        print("SAVED", OUT / "Meydenbauer-B-4D.blend")
        return
    if a.stills:
        frames, tag = [clk.phase_frame(i, 2.0) for i in range(len(PHASES))], a.tag if a.tag != "final" else "stills"
    else:
        s0, s1, st = (int(v) for v in (a.frames or f"1:{clk.end}:1").split(":"))
        frames, tag = list(range(s0, s1 + 1, st)), a.tag
    res = (int(1920 * a.res) // 2 * 2, int(1080 * a.res) // 2 * 2)
    k, n = (int(v) for v in a.worker.split("/"))
    render_frames(frames, res, a.samples, a.device, f"{tag}-{a.fps}", (k, n))


if __name__ == "__main__":
    main()
