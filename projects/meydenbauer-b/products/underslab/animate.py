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

--plan sequence: the same eight phases one unit at a time (B-103, B-102, B-101, B-104), each
phase's screen time in proportion to its working days on the strawman schedule (schedule.py),
with the site logistics (logistics.py): haul routes out to the staging area and back, a roll-off
bin and a bedding stockpile, and the SOR note 21 service toilet and sink kept in each unit.

Usage:
  python projects/meydenbauer-b/products/underslab/animate.py --no-render                 # build, check, save .blend
  python projects/meydenbauer-b/products/underslab/animate.py --plan sequence --fps 30 --no-render
  python projects/meydenbauer-b/products/underslab/animate.py --stills                    # 8 check frames (one per phase)
  python projects/meydenbauer-b/products/underslab/animate.py --frames 1:1920:8 --res 0.33 --samples 8 --tag proxy
  python projects/meydenbauer-b/products/underslab/animate.py --device OPTIX --samples 128 --worker 0/2   # RunPod
"""
import argparse, json, math, sys, time
from pathlib import Path

import bpy, bmesh
import numpy as np
from bpy_extras import anim_utils
from mathutils import Vector
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union

HERE = Path(__file__).resolve().parent
from bmodels.paths import ROOT  # noqa: E402  (repo root)
sys.path.insert(0, str(HERE))
import realism as R  # noqa: E402
import schedule as SCHED  # noqa: E402

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
    def __init__(self, fps, total_s=None):
        self.fps = fps
        self.end = int(round((total_s or len(PHASES) * PHASE_S) * fps))

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
            s["flow"] = N[k]["flow_ft"]; s["unit"] = u["unit"]; nodes.append(s)
        for e in u["ends"]:
            if e["kind"] == "TEE":
                continue
            k = e["node"]; x, y = N[k]["xy_ft"]
            nom = 4 if e["kind"] == "STACK-4" else 3 if e["kind"] in ("STACK-3", "WC", "WB") else 2
            z0 = zc(k, nom); top = 3.0 if e["kind"].startswith("STACK") else 0.35
            bpy.ops.mesh.primitive_cylinder_add(radius=R.OD_IN[nom] / 24 * R.FT, depth=(top - z0) * R.FT,
                                                location=R.P(x, y, (top + z0) / 2), vertices=24)
            s = bpy.context.object; s.name = f'{u["unit"]} {e["kind"]} riser'; R.move(s, c); s.data.materials.append(abs_m)
            s["flow"] = N[k]["flow_ft"]; s["unit"] = u["unit"]; nodes.append(s)
            bpy.ops.mesh.primitive_cylinder_add(radius=R.OD_IN[nom] / 24 * R.FT * 1.15, depth=0.14 * R.FT,
                                                location=R.P(x, y, top + 0.07), vertices=24)
            cap = bpy.context.object; cap.name = f'{u["unit"]} test plug'; R.move(cap, c)
            cap.data.materials.append(augment(M["cap"]))
            cap["is_cap"] = 1; cap["unit"] = u["unit"]; nodes.append(cap)
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


def camera_objects():
    """Camera + Camera_Target empty (the DOF focus); the rigs bake their paths onto these."""
    sc = bpy.context.scene
    cam = bpy.data.cameras.new("Sequence camera"); cam.lens = 35; cam.clip_start = 0.1; cam.clip_end = 500
    cam.dof.use_dof = True; cam.dof.aperture_fstop = 5.6
    co = bpy.data.objects.new("Sequence camera", cam); sc.collection.objects.link(co)
    tgt = bpy.data.objects.new("Camera_Target", None); sc.collection.objects.link(tgt)
    tgt.empty_display_type = "SPHERE"; tgt.empty_display_size = 0.5
    cam.dof.focus_object = tgt
    co.rotation_mode = "QUATERNION"
    sc.camera = co
    return co, tgt


def bake_camera(clk, co, tgt, pose):
    """Key the camera and target on every frame from pose(seconds) -> (camera, target) in metres."""
    prev = None
    for f in range(1, clk.end + 1):
        c, t = pose((f - 1) / clk.fps)
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


def camera_rig(clk):
    """Overview path: Catmull-Rom through the CAMERA key poses, baked per frame."""
    co, tgt = camera_objects()
    ts = np.array([k[0] for k in CAMERA]); cp = np.array([k[1] for k in CAMERA], float); tp = np.array([k[2] for k in CAMERA], float)

    def catmull(P, s):
        i = int(np.clip(np.searchsorted(ts, s, side="right") - 1, 0, len(ts) - 2))
        u = (s - ts[i]) / (ts[i + 1] - ts[i])
        u = u * u * (3 - 2 * u) * 0.35 + u * 0.65            # slight ease at each key
        p0, p1, p2, p3 = P[max(i - 1, 0)], P[i], P[i + 1], P[min(i + 2, len(P) - 1)]
        return 0.5 * ((2 * p1) + (-p0 + p2) * u + (2 * p0 - 5 * p1 + 4 * p2 - p3) * u * u + (-p0 + 3 * p1 - 3 * p2 + p3) * u ** 3)
    bake_camera(clk, co, tgt, lambda s: (R.P(*catmull(cp, s)), R.P(*catmull(tp, s))))
    return co


# ------------------------------------------------------------------------------------------ sequence plan
# One unit at a time on the strawman schedule (schedule.py), with the site logistics (logistics.py).
# Each phase keeps the overview's actions, mapped in proportion onto that unit's window.

LOGISTICS = HERE / "meydenbauer-b.logistics.json"
SEQ_SAFE = (0.03, 0.97, 0.20, 0.80)     # x0, x1, y0, y1: clear of the sequence HUD (Gantt band, cards)
SEQ_VIEW = (0.3, -1.0, 1.15)             # plan-ft direction target -> camera: from the east, high (wide shots)
SEQ_VIEW_CLOSE = (0.25, -1.0, 1.5)       # steeper for the unit shots, over the garage massing
PUSH = 0.05                              # slow push-in over each shot
ROUTE_W = 1.4                            # ft, haul-route ribbon
FLOW_FT_S = 14.0                         # dash speed along a route, ft per second of film
PARK_X = -400.0                          # ft: the sweep band waits off the building between units
WORK_LIGHT_W = 220


def unit_of_x(x):
    for u, (x0, x1) in R.UNITS.items():      # north to south
        if x < x1:
            return u
    return u


def centre_ft(o):
    """Bounding-box centre in plan feet (x south, y west, z up)."""
    c = sum((o.matrix_world @ Vector(b) for b in o.bound_box), Vector()) / 8
    return c.x / R.FT, -c.y / R.FT, c.z / R.FT


def split_by_unit(o):
    """Replace a mesh that spans the building with one copy per unit, each keeping only the faces
    whose centre falls in that unit's x range (UNITS)."""
    out = []
    for u in R.UNITS:
        p = o.copy(); p.data = o.data.copy(); p.name = f"{u} {o.name}"
        for col in o.users_collection:
            col.objects.link(p)
        bm = bmesh.new(); bm.from_mesh(p.data)
        drop = [f for f in bm.faces if unit_of_x((o.matrix_world @ f.calc_center_median()).x / R.FT) != u]
        bmesh.ops.delete(bm, geom=drop, context="FACES")
        bm.to_mesh(p.data); bm.free()
        if p.data.polygons:
            p["unit"] = u; out.append(p)
        else:
            bpy.data.objects.remove(p)
    bpy.data.objects.remove(o)
    return out


def service_pairs(S):
    """SOR note 21: one toilet and one sink back in use in each unit by 5:00 PM daily. Kept here:
    the toilet nearest the tie-in and the lav nearest that toilet (assumed). They stay through the
    work on a nightly temporary connection (method assumed). B-102 has no WC end on P1.02, so it
    keeps a lav only; its toilet arrangement is a bid clarification."""
    keep = {}
    for u in R.SPEC["units"]:
        N = u["nodes"]
        tie = N[min(N, key=lambda k: N[k]["flow_ft"])]["xy_ft"]
        mine = [o for o in S["fixtures"] if o["unit"] == u["unit"]]
        wcs = [o for o in mine if " toilet" in o.name]
        lavs = [o for o in mine if " vanity" in o.name]
        pick, ref = [], tie
        if wcs:
            wc = min(wcs, key=lambda o: math.dist(centre_ft(o)[:2], tie)); pick.append(wc); ref = centre_ft(wc)[:2]
        if lavs:
            pick.append(min(lavs, key=lambda o: math.dist(centre_ft(o)[:2], ref)))
        for o in pick:
            o["service"] = 1
        keep[u["unit"]] = pick
    return keep


def service_markers(keep, c):
    m = R.principled("Service marker (in use by 5 PM)", (0.04, 0.5, 0.2), 0.4)
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Emission Color"].default_value = (0.2, 1.0, 0.45, 1); b.inputs["Emission Strength"].default_value = 0.8
    augment(m, glow=((0.2, 1.0, 0.45), 12.0))
    out = []
    for unit, objs in keep.items():
        for o in objs:
            x, y, _ = centre_ft(o)
            ring = Point(x, y).buffer(1.7).difference(Point(x, y).buffer(1.35))
            out.append(R.solid(f"{unit} service marker", ring, R.FINISH + 0.05, R.FINISH + 0.03, m, c, unit=unit,
                               status="assumed", basis="SOR note 21: one toilet and one sink in use by 5:00 PM daily"))
    return out


def dash_material(name, color):
    """Emission ribbon with dashes that travel along the UV u axis (u = feet along the route) as the
    object property 'flow' (ft) increases; fades with 'vanish' like everything else."""
    m = bpy.data.materials.new(name); m.use_nodes = True
    n, l = m.node_tree.nodes, m.node_tree.links
    n.remove(n["Principled BSDF"]); out = n["Material Output"]
    tc = n.new("ShaderNodeTexCoord"); sep = n.new("ShaderNodeSeparateXYZ"); l.new(tc.outputs["UV"], sep.inputs["Vector"])
    fa = n.new("ShaderNodeAttribute"); fa.attribute_type = "OBJECT"; fa.attribute_name = "flow"

    def op(kind, a, b=None, c=None):
        mm = n.new("ShaderNodeMath"); mm.operation = kind
        for i, v in enumerate((a, b, c)):
            if v is None:
                continue
            if isinstance(v, float):
                mm.inputs[i].default_value = v
            else:
                l.new(v, mm.inputs[i])
        return mm.outputs[0]
    dash = op("LESS_THAN", op("FRACT", op("DIVIDE", op("SUBTRACT", sep.outputs["X"], fa.outputs["Fac"]), 6.0)), 0.5)
    em = n.new("ShaderNodeEmission"); em.inputs["Color"].default_value = (*color, 1)
    l.new(op("MULTIPLY_ADD", dash, 7.0, 0.7), em.inputs["Strength"])
    l.new(em.outputs[0], out.inputs["Surface"])
    return augment(m)


def ribbon(name, pts, width, mat, c, **props):
    """Flat strip along a 3D polyline (plan ft), one quad per segment run past each corner by half
    the width; UV u = feet along the route."""
    bm = bmesh.new(); uvl = bm.loops.layers.uv.new()
    acc = 0.0
    for i, (a, b) in enumerate(zip(pts, pts[1:])):
        a, b = Vector(a), Vector(b)
        d = b - a; L = d.xy.length
        if L < 1e-6:
            continue
        t = Vector((d.x / L, d.y / L, 0)); nrm = Vector((-t.y, t.x, 0)) * width / 2
        lift = Vector((0, 0, 0.004 * (i % 2)))
        a2, b2 = a - t * width / 2 + lift, b + t * width / 2 + lift
        vs = [bm.verts.new(R.P(*p)) for p in (a2 - nrm, b2 - nrm, b2 + nrm, a2 + nrm)]
        f = bm.faces.new(vs)
        for lp, (u, v) in zip(f.loops, ((acc - width / 2, 0), (acc + L + width / 2, 0), (acc + L + width / 2, 1), (acc - width / 2, 1))):
            lp[uvl].uv = (u, v)
        acc += L
    o = R.obj(name, bm, mat, c, **props)
    o["length_ft"] = round(acc, 1)
    return o


def label(text, xy, z, size, c, mat):
    cu = bpy.data.curves.new(f"Label: {text}", "FONT"); cu.body = text; cu.size = size * R.FT
    cu.align_x = "CENTER"; cu.align_y = "CENTER"
    o = bpy.data.objects.new(cu.name, cu); c.objects.link(o)
    o.location = R.P(xy[0], xy[1], z); o.rotation_euler = (0, 0, math.pi)     # reads left to right from the east
    o.data.materials.append(mat)
    return o


def logistics(L, c):
    """Site massing east of Building B, the staging pad, roll-off bin, stockpile and haul routes,
    all as assumed in logistics.py (from SOR Fig 8; not to scale)."""
    g = L["grade_ft"]
    env = Polygon(R.SHELL["envelope_ft"])
    site = env.buffer(8, join_style="mitre")
    plate_m = R.principled("Site model base (graphite)", (0.022, 0.026, 0.034), 0.6)
    drive_m = R.principled("Drive (asphalt, model)", (0.045, 0.05, 0.06), 0.5)
    pad_m = R.principled("Staging pad (crushed rock, model)", (0.16, 0.13, 0.09), 0.85)
    edge_m = R.emitter("Staging fence line (amber)", (1.0, 0.55, 0.12), 2.5)
    bin_m = R.principled("Roll-off bin (steel)", (0.10, 0.17, 0.28), 0.45, metal=0.4)
    text_m = R.emitter("Site labels", (0.85, 0.9, 1.0), 1.4)
    for m in (plate_m, drive_m, pad_m, bin_m):
        augment(m)
    out = {"routes_out": [], "routes_in": []}
    R.solid("Site model base (east of Building B)", box(-30, -96, 186, -8).difference(site), g, -R.GROUND, plate_m, c,
            status="assumed", basis="context only; grade taken at the slab underside")
    ghost = bpy.data.materials["Architectural ghost (walls)"]
    for m in L["massing"]:
        p = Polygon(m["ring_ft"])
        if m["kind"] == "garage":
            o = R.solid(f'Garage massing ({m["id"]})', p, g + m["height_ft"], g, ghost, c, status="assumed",
                        basis="SOR Fig 8 aerial; footprint and height not to scale")
            o.visible_shadow = False
        elif m["kind"] == "drive":
            R.solid("SE 3rd St drive", p, g + 0.02, g, drive_m, c, status="assumed", basis="SOR Fig 8 aerial")
        else:
            R.solid("Staging area (SOR Fig 8)", p, g + 0.06, g, pad_m, c, status="assumed",
                    basis="SOR Fig 8 / note 10: ~1,000 SF designated by the Association; contractor fences it")
            R.solid("Staging fence line", p.exterior.buffer(0.25), g + 0.12, g + 0.06, edge_m, c, status="assumed")
            bm = bmesh.new()
            ring = p.exterior
            n = max(4, int(ring.length / 8))
            for k in range(n):
                q = ring.interpolate(k / n, normalized=True)
                R.prism(bm, Point(q.x, q.y).buffer(0.12, quad_segs=3), g + 6.0, g)
            R.obj("Staging fence posts (6 ft)", bm, R.principled("Fence post", (0.05, 0.05, 0.05), 0.5), c, status="assumed")
            label("STAGING  ~1,000 SF  (SOR FIG 8)", (p.centroid.x, p.centroid.y + 8.5), g + 0.08, 2.4, c, text_m)
    label("GARAGES", (60, -25), g + 10.05, 3.0, c, text_m)
    label("SE 3RD ST DRIVE", (100, -51), g + 0.05, 2.6, c, text_m)
    for k, e in L["entries"].items():
        x, y = e["door_ft"]
        label(f"{k} CORE ENTRY", (x, y - 3.2), g + 0.06, 1.6, c, text_m)
    # roll-off bin: open box, with a spoil heap that is keyed in z (origin at the bin floor)
    bp = Polygon(L["bin"]["ring_ft"]); hb = L["bin"]["height_ft"]
    bm = bmesh.new()
    R.prism(bm, bp.difference(bp.buffer(-0.25, join_style="mitre")), g + hb, g + 0.3)
    R.prism(bm, bp, g + 0.3, g)
    R.obj("Roll-off bin (10 yd, assumed)", bm, bin_m, c, status="assumed", basis="bin size and swaps assumed")
    heap = R.solid("Bin spoil", bp.buffer(-0.3, join_style="mitre"), g + hb - 0.25, g + 0.3, bpy.data.materials["Excavated soil (CC0 scan)"], c)
    zmin = min(v.co.z for v in heap.data.vertices)
    for v in heap.data.vertices:
        v.co.z -= zmin
    heap.location.z = zmin
    out["bin_heap"] = heap
    # bedding and backfill stockpile: a mound, keyed in scale (origin at its base)
    cx, cy = L["stockpile"]["centre_ft"]; r = L["stockpile"]["radius_ft"]; h = L["stockpile"]["height_ft"]
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=40, radius1=r * R.FT, radius2=0.25 * r * R.FT, depth=h * R.FT)
    bmesh.ops.translate(bm, verts=bm.verts, vec=(0, 0, h / 2 * R.FT))
    pile = R.obj("Bedding and backfill stockpile", bm, bpy.data.materials["Pipe bedding gravel (CC0 scan)"], c, status="assumed")
    pile.location = R.P(cx, cy, g)
    out["stockpile"] = pile
    out_m = dash_material("Haul route out (spoil)", (1.0, 0.55, 0.12))
    in_m = dash_material("Haul route in (bedding, backfill, concrete)", (0.15, 0.85, 1.0))
    for u, r_ in L["routes"].items():
        out["routes_out"].append(ribbon(f"{u} haul route out", r_["out_ft"], ROUTE_W, out_m, c, unit=u, status="assumed",
                                        basis=f'via the {r_["entry"]} core entry; path assumed'))
        out["routes_in"].append(ribbon(f"{u} haul route in", r_["in_ft"], ROUTE_W, in_m, c, unit=u, status="assumed"))
    return out


def stack_bypasses(c):
    """P2.1 scope note: "maintain continuous sanitary service to occupied units and provide temporary
    bypass systems"; P1.01 demolition note 3 likewise for unaffected units. The SOR says the upper
    floors share the stacks, so each P1.02 stack end (STACK-3/4) is shown on a temporary bypass to
    the unit's tie-in while that unit's line is open. Path and method assumed (a graphic, not a route)."""
    m = dash_material("Temporary stack bypass", (0.75, 1.0, 0.15))
    out = []
    for u in R.SPEC["units"]:
        tx, ty = u["tie_in"]["xy_ft"]
        for e in u["ends"]:
            if e["kind"].startswith("STACK"):
                sx, sy = u["nodes"][e["node"]]["xy_ft"]
                out.append(ribbon(f'{u["unit"]} {e["kind"]} bypass', [(sx, sy, R.FINISH + 0.12), (tx, ty, R.FINISH + 0.12)],
                                  0.9, m, c, unit=u["unit"], status="assumed",
                                  basis="P2.1 scope note and P1.01 demo note 3: temporary bypass; path and method assumed"))
    return out


def sequence_scene(S, L, c):
    """Make the building-wide pieces per unit, tag everything with its unit, add the service pairs
    and the site logistics."""
    S["bedding"] = split_by_unit(S["bedding"])
    temp = bpy.data.collections["Temporary protection and dust control"]
    for name in ("Ram Board floor protection", "Dust walls (6-mil poly)", "Spring poles"):
        o = bpy.data.objects.get(name)
        if o:
            split_by_unit(o)
    S["protection"] = [o for o in temp.objects if o.type in ("MESH", "CURVE")]
    for o in S["protection"] + S["work_lights"]:
        if "unit" not in o:
            o["unit"] = o.name.split(" ")[0] if o.name.split(" ")[0] in R.UNITS else unit_of_x(centre_ft(o)[0])
    for o in S["props"] + S["bath_lights"]:
        o["unit"] = unit_of_x(o.location.x / R.FT)
    S["service"] = service_pairs(S)
    S["service_markers"] = service_markers(S["service"], c)
    S["bypass"] = stack_bypasses(c)
    S.update(logistics(L, R.coll("Site logistics (assumed)")))


def choreograph_seq(clk, S, W, plan):
    T = TRANS_S

    def ph(u, i, s=0.0):                      # nominal seconds (0-4) of phase i -> frame in u's window
        t0, t1 = W[u][i]
        return clk.f(t0 + (t1 - t0) * s / PHASE_S)

    def span(u, i, s):                        # nominal duration -> frames
        t0, t1 = W[u][i]
        return max(1, int(round(s * (t1 - t0) / PHASE_S * clk.fps)))

    mine = lambda name, u: [o for o in S[name] if o.get("unit") == u]
    ga = bpy.data.materials["Architectural ghost (walls)"].node_tree.nodes["ghost_amount"].outputs[0]
    sx = S["ci_mat"].node_tree.nodes["sweep_x"].outputs[0]
    wp = S["abs_mat"].node_tree.nodes["water_phase"].outputs[0]
    sx.default_value = PARK_X * R.FT; sx.keyframe_insert("default_value", frame=1)
    for o in S["pour"] + S["routes_out"] + S["routes_in"] + S["bypass"] + [o for o in S["nodes"] if "is_cap" in o]:
        key(o, "vanish", 1, 1)
    key(S["stockpile"], "vanish", 1, 1); key_scale(S["stockpile"], 1, 0.02)
    key_scale(S["bin_heap"], 1, 0.02, axes=(2,))
    for o in S["service_markers"]:
        key(o, "vanish", 1, 1); key(o, "glow", 1, 0)
    water = 0.0
    for u in SCHED.ORDER:
        x0, x1 = R.UNITS[u]
        kept = {o.name for o in S["service"][u]}
        movable = [o for o in mine("fixtures", u) if o.name not in kept]

        # 01 investigation: x-ray over this unit's trench, sonar sweep across the unit, marks appear
        for o in mine("slab", u) + mine("finish", u) + mine("soil", u):
            key(o, "vanish", ph(u, 0, 0.5), 0); key(o, "vanish", ph(u, 0, 1.25), 0.82)
            key(o, "vanish", ph(u, 0, 3.1), 0.82); key(o, "vanish", ph(u, 0, 3.85), 0)
        a, b = x0 - 10, x1 + 10
        for f, x in ((ph(u, 0, 0.8) - 1, PARK_X), (ph(u, 0, 0.8), a), (ph(u, 0, 3.4), b), (ph(u, 0, 3.4) + 1, PARK_X)):
            sx.default_value = x * R.FT; sx.keyframe_insert("default_value", frame=f)
        for o in mine("marks", u):
            s0 = 0.8 + (o["x_min"] - a) / (b - a) * 2.6
            key(o, "vanish", 1, 1); key(o, "vanish", ph(u, 0, s0), 1); key(o, "vanish", ph(u, 0, s0 + 0.35), 0)
            key(o, "vanish", ph(u, 2, 0.5), 0); key(o, "vanish", ph(u, 2, 0.8), 1)
        for f, v in ((ph(u, 2, 0.3), 1.0), (ph(u, 2, 1.8), 0.35), (ph(u, 5, 1.0), 0.35), (ph(u, 5, 2.5), 1.0)):
            ga.default_value = v; ga.keyframe_insert("default_value", frame=f)

        # 02 staging: protection, props and work lights in; fixtures out except the service pair
        for o in mine("protection", u):
            key(o, "vanish", ph(u, 1, 0.0), 1); key(o, "vanish", ph(u, 1, 0.2 + T), 0)
        for e in mine("props", u):
            key_scale(e, ph(u, 1, 0.4), 0.0); key_scale(e, ph(u, 1, 0.4 + T), 1.0)
        for lo in mine("work_lights", u):
            lo.data.energy = 0; lo.data.keyframe_insert("energy", frame=ph(u, 1, 0.9))
            lo.data.energy = WORK_LIGHT_W; lo.data.keyframe_insert("energy", frame=ph(u, 1, 0.9 + T))
        for i, o in enumerate(movable):
            s0 = 1.0 + 0.15 * (i % 3)
            key_z(o, ph(u, 1, s0), 0); key(o, "vanish", ph(u, 1, s0), 0)
            key_z(o, ph(u, 1, s0 + T), LIFT_FIXTURE); key(o, "vanish", ph(u, 1, s0 + T), 1)
        for o in mine("service_markers", u):
            key(o, "vanish", ph(u, 1, 0.0), 1); key(o, "vanish", ph(u, 1, 0.6), 0)
            key(o, "vanish", ph(u, 7, 3.0), 0); key(o, "vanish", ph(u, 7, 3.6), 1)
        # 5:00 PM pulse on the service pair at the end of every working day from staging to finishes
        p = next(p for p in plan["units"] if p["unit"] == u)
        d0, d1 = p["phase_start_day"][1], p["phase_start_day"][6] + p["days"][6]
        for day in range(math.floor(d0) + 1, math.floor(d1 + 1e-9) + 1):
            f = clk.f(SCHED.time_at_day(plan, W, u, day))
            for o in mine("service_markers", u):
                key(o, "glow", f - 4, 0); key(o, "glow", f, 1); key(o, "glow", f + 8, 0)

        # 03 demolition + excavation: saw-cut glow, cut-outs lifted away, soil dug down; spoil hauled out
        for o in mine("slab", u):
            key(o, "glow", ph(u, 2, 0.1), 0); key(o, "glow", ph(u, 2, 0.45), 1); key(o, "glow", ph(u, 2, 0.5 + T), 0)
        for o in mine("slab", u) + mine("finish", u):
            key_z(o, ph(u, 2, 0.5), 0); key(o, "vanish", ph(u, 2, 0.5), 0)
            key_z(o, ph(u, 2, 0.5 + T), 3.28); key(o, "vanish", ph(u, 2, 0.5 + T), 1)
        for o in mine("soil", u):
            key_scale(o, ph(u, 2, 1.3), 1.0, axes=(2,)); key_scale(o, ph(u, 2, 2.9), 0.03, axes=(2,))
            key(o, "vanish", ph(u, 2, 2.9), 0); key(o, "vanish", ph(u, 2, 3.2), 1)
        for o in mine("routes_out", u):
            f0, f1 = ph(u, 2, 0.6), ph(u, 3, 0.6)
            key(o, "vanish", f0, 1); key(o, "vanish", f0 + span(u, 2, 0.4), 0)
            key(o, "vanish", f1 - span(u, 3, 0.4), 0); key(o, "vanish", f1, 1)
            key(o, "flow", f0, 0); key(o, "flow", f1, FLOW_FT_S * (f1 - f0) / clk.fps)
        for o in mine("bypass", u):              # upper-floor stacks on bypass while the line is open (03-06)
            f0, f1 = ph(u, 2, 0.3), ph(u, 6, 0.3)
            key(o, "vanish", f0, 1); key(o, "vanish", f0 + span(u, 2, 0.4), 0)
            key(o, "vanish", f1 - span(u, 6, 0.3), 0); key(o, "vanish", f1, 1)
            key(o, "flow", f0, 0); key(o, "flow", f1, 0.5 * FLOW_FT_S * (f1 - f0) / clk.fps)
        heap = S["bin_heap"]
        key_scale(heap, ph(u, 2, 0.6), 0.02, axes=(2,)); key_scale(heap, ph(u, 2, 3.6), 1.0, axes=(2,))
        key_scale(heap, ph(u, 3, 1.0), 1.0, axes=(2,)); key_scale(heap, ph(u, 3, 3.5), 0.02, axes=(2,))   # bin swapped

        # 04 new ABS: cast iron out, bedding in, pipe grows from the tie-in upstream with a cyan front
        for o in mine("ci", u):
            key_z(o, ph(u, 3, 0.0), 0); key(o, "vanish", ph(u, 3, 0.0), 0)
            key_z(o, ph(u, 3, T), 0.8); key(o, "vanish", ph(u, 3, T), 1)
        for o in mine("bedding", u):
            key(o, "vanish", ph(u, 3, 0.0), 1); key(o, "vanish", ph(u, 3, 0.6), 0)
        runs = mine("abs", u)
        fmax = max(o["flow_hi"] for o in runs)
        k = 2.6 / fmax
        t_at = lambda flow: ph(u, 3, 0.95 + k * flow)
        for o in runs:
            fa, fb = t_at(o["flow_lo"]), max(t_at(o["flow_hi"]), t_at(o["flow_lo"]) + 1)
            o.data.bevel_factor_end = 0.0; o.data.keyframe_insert("bevel_factor_end", frame=fa)
            o.data.bevel_factor_end = 1.0; o.data.keyframe_insert("bevel_factor_end", frame=fb)
            key(o, "vanish", 1, 1); key(o, "vanish", fa - 1, 1); key(o, "vanish", fa, 0)
            key(o, "glow", fa - 1, 0); key(o, "glow", fa, 1); key(o, "glow", fb, 1); key(o, "glow", fb + span(u, 3, 0.5), 0)
        for o in mine("nodes", u):
            if "is_cap" in o:
                continue
            f = t_at(o["flow"])
            key(o, "vanish", 1, 1); key(o, "vanish", f - 1, 1); key(o, "vanish", f, 0)
            key(o, "glow", f, 1); key(o, "glow", f + span(u, 3, 0.5), 0)
        pile = S["stockpile"]                     # bedding and backfill delivered while the pipe goes in
        key(pile, "vanish", ph(u, 3, 0.2), 1); key(pile, "vanish", ph(u, 3, 0.6), 0)
        key_scale(pile, ph(u, 3, 0.2), 0.02); key_scale(pile, ph(u, 3, 2.0), 1.0)

        # 05 water test: plugs in, fill from the tie-in up, hold, drain, plugs out
        for o in mine("nodes", u):
            if "is_cap" in o:
                key(o, "vanish", ph(u, 4, 0.0), 1); key(o, "vanish", ph(u, 4, 0.3), 0)
                key(o, "vanish", ph(u, 4, 3.6), 0); key(o, "vanish", ph(u, 4, 3.95), 1)
        kf = 1.7 / fmax
        for o in runs:
            f0 = ph(u, 4, 0.35 + kf * o["flow_lo"])
            key(o, "water", 1, 0); key(o, "water", f0 - 1, 0); key(o, "water", f0 + span(u, 4, 0.25), 1)
            key(o, "water", ph(u, 4, 3.3), 1); key(o, "water", ph(u, 4, 3.8), 0)
        t0, t1 = W[u][4]
        for f, v in ((ph(u, 4, 0.0), water), (ph(u, 4, 4.0), water + 10.0 * (t1 - t0))):
            wp.default_value = v; wp.keyframe_insert("default_value", frame=f)
        water += 10.0 * (t1 - t0)

        # 06 backfill + pour-back: material hauled in, soil rises to the pour-back underside, concrete in
        for o in mine("soil", u):
            z0 = o["zmin_ft"]
            target = (-POURBACK - z0) / (-R.SLAB - z0)
            key(o, "vanish", ph(u, 5, 0.1) - 1, 1); key(o, "vanish", ph(u, 5, 0.1), 0)
            key_scale(o, ph(u, 5, 0.1), 0.03, axes=(2,)); key_scale(o, ph(u, 5, 1.6), target, axes=(2,))
        for o in mine("pour", u):
            x = centre_ft(o)[0]
            s0 = 2.0 + 0.9 * (x - x0) / (x1 - x0)
            key(o, "vanish", ph(u, 5, s0), 1); key_z(o, ph(u, 5, s0), 1.0)
            key(o, "vanish", ph(u, 5, s0 + T), 0); key_z(o, ph(u, 5, s0 + T), 0)
        for o in mine("routes_in", u):
            f0, f1 = ph(u, 5, 0.0), ph(u, 5, 3.7)
            key(o, "vanish", f0, 1); key(o, "vanish", f0 + span(u, 5, 0.4), 0)
            key(o, "vanish", f1 - span(u, 5, 0.4), 0); key(o, "vanish", f1, 1)
            key(o, "flow", f0, 0); key(o, "flow", f1, FLOW_FT_S * (f1 - f0) / clk.fps)
        key_scale(pile, ph(u, 5, 0.2), 1.0); key_scale(pile, ph(u, 5, 3.4), 0.05)
        key(pile, "vanish", ph(u, 5, 3.4), 0); key(pile, "vanish", ph(u, 5, 3.8), 1)

        # 07 finishes, after the cure: the first cure_days of the phase pass with the patches still out,
        # then they come down from +0.5 m with a fade-in, south across the unit, in the time left
        cure = PHASE_S * min(0.8, p["cure_days"] / p["days"][6])
        rest = PHASE_S - cure
        for o in mine("finish", u):
            x = centre_ft(o)[0]
            s0 = cure + rest * (0.075 + 0.55 * max(0.0, x - x0) / (x1 - x0))
            t_in = min(T, 0.3 * rest)
            key_z(o, ph(u, 6, 0.0), LIFT_FINISH); key(o, "vanish", ph(u, 6, s0), 1); key_z(o, ph(u, 6, s0), LIFT_FINISH)
            key_z(o, ph(u, 6, s0 + t_in), 0); key(o, "vanish", ph(u, 6, s0 + t_in), 0)

        # 08 reinstatement: protection out, fixtures back, the unit's lights up (done, occupied)
        for o in mine("protection", u):
            key(o, "vanish", ph(u, 7, 0.0), 0); key(o, "vanish", ph(u, 7, T), 1)
        for e in mine("props", u):
            key_scale(e, ph(u, 7, 0.0), 1.0); key_scale(e, ph(u, 7, T), 0.0)
        for lo in mine("work_lights", u):
            lo.data.energy = WORK_LIGHT_W; lo.data.keyframe_insert("energy", frame=ph(u, 7, 0.0))
            lo.data.energy = 0; lo.data.keyframe_insert("energy", frame=ph(u, 7, T))
        for i, o in enumerate(movable):
            s0 = 0.6 + 0.15 * (i % 3)
            key_z(o, ph(u, 7, s0), LIFT_FIXTURE); key(o, "vanish", ph(u, 7, s0), 1)
            key_z(o, ph(u, 7, s0 + T), 0); key(o, "vanish", ph(u, 7, s0 + T), 0)
        for lo in mine("bath_lights", u):
            lo.data.energy = 0; lo.data.keyframe_insert("energy", frame=ph(u, 7, 1.8))
            lo.data.energy = 90; lo.data.keyframe_insert("energy", frame=ph(u, 7, 2.8))


def seq_points(L, which, unit=None):
    """World points a shot must contain: the whole site, one unit's work, or that unit's haul."""
    env = Polygon(R.SHELL["envelope_ft"])
    g = L["grade_ft"]
    if which == "site":
        xy = list(env.exterior.coords) + [c for m in L["massing"] if m["kind"] != "drive" for c in m["ring_ft"]]
        return [R.P(x, y, z) for x, y in xy for z in (g, R.WALL_TOP)]
    take = next(t for t in R.TAKE["units"] if t["unit"] == unit)
    work = unary_union([Polygon(r) for r in take["footprint_S2"]]).buffer(7.0)       # the trench and its working room
    pts = [R.P(x, y, z) for x, y in box(*work.bounds).exterior.coords for z in (-3.0, 3.0)]
    if which == "haul":
        r = L["routes"][unit]
        stage = next(m for m in L["massing"] if m["kind"] == "staging")
        pts += [R.P(x, y, z) for x, y, z in r["out_ft"]] + [R.P(x, y, g) for x, y in stage["ring_ft"]]
    return pts


def fit_shot(co, pts, safe=SEQ_SAFE, view=SEQ_VIEW, margin=0.92):
    """Camera position and target (metres) that frame pts inside the safe box from direction view."""
    from bpy_extras.object_utils import world_to_camera_view
    sc = bpy.context.scene
    d = R.P(*view).normalized()
    tgt = sum(pts, Vector()) / len(pts)
    w_safe, h_safe = (safe[1] - safe[0]) * margin, (safe[3] - safe[2]) * margin

    def bounds(t, dist):
        co.location = t + d * dist
        co.rotation_mode = "QUATERNION"; co.rotation_quaternion = (t - co.location).to_track_quat("-Z", "Y")
        bpy.context.view_layer.update()
        v = [world_to_camera_view(sc, co, p) for p in pts]
        return min(q.x for q in v), max(q.x for q in v), min(q.y for q in v), max(q.y for q in v), min(q.z for q in v)
    for _ in range(5):
        lo, hi = 1.0, 2000.0
        for _ in range(32):
            mid = (lo + hi) / 2
            x0, x1, y0, y1, z = bounds(tgt, mid)
            if z > 0 and x1 - x0 <= w_safe and y1 - y0 <= h_safe:
                hi = mid
            else:
                lo = mid
        x0, x1, y0, y1, _ = bounds(tgt, hi)
        q = co.rotation_quaternion
        w = hi * co.data.sensor_width / co.data.lens
        h = w * sc.render.resolution_y / sc.render.resolution_x
        tgt = tgt + (q @ Vector((1, 0, 0))) * ((x0 + x1) / 2 - (safe[0] + safe[1]) / 2) * w \
                  + (q @ Vector((0, 1, 0))) * ((y0 + y1) / 2 - (safe[2] + safe[3]) / 2) * h
    bounds(tgt, hi)
    return co.location.copy(), tgt.copy()


def seq_shots(co, W, L, total_s):
    """[(t_in, blend_s, camera, target, points)] in time order: site wide, then per unit a close
    shot, the haul shot in demolition and in backfill, back to close; site wide at the end."""
    fits = {}

    def shot(t_in, blend, which, unit=None):
        k = (which, unit)
        if k not in fits:
            pts = seq_points(L, which, unit)
            fits[k] = (*fit_shot(co, pts, view=SEQ_VIEW_CLOSE if which == "unit" else SEQ_VIEW), pts)
        return [t_in, blend, *fits[k]]
    S_ = [shot(0.0, 0.0, "site")]
    for u in SCHED.ORDER:
        w = W[u]
        S_ += [shot(w[0][0], 1.3, "unit", u), shot(w[2][0] + 0.3 * (w[2][1] - w[2][0]), 1.1, "haul", u),
               shot(w[3][0], 1.1, "unit", u), shot(w[5][0], 1.1, "haul", u), shot(w[6][0], 1.1, "unit", u)]
    S_.append(shot(W[SCHED.ORDER[-1]][7][1], 1.6, "site"))
    for a, b in zip(S_, S_[1:]):
        b[1] = min(b[1], 0.8 * (b[0] - a[0]))
    return [tuple(s_) for s_ in S_]


def camera_rig_seq(clk, shots, co, tgt):
    ends = [s_[0] for s_ in shots[1:]] + [clk.end / clk.fps]

    def hold(j, s):
        t_in, _, c, t, _ = shots[j]
        u = min(1.0, max(0.0, (s - t_in) / (ends[j] - t_in)))
        return c + (t - c) * PUSH * u, t

    def pose(s):
        j = max(i for i, s_ in enumerate(shots) if s_[0] <= s)
        t_in, blend = shots[j][:2]
        if j == 0 or s >= t_in + blend:
            return hold(j, s)
        (ac, at), (bc, bt) = hold(j - 1, t_in), hold(j, s)
        x = (s - t_in) / blend
        w = x * x * x * (x * (6 * x - 15) + 10)            # smootherstep
        return ac.lerp(bc, w), at.lerp(bt, w)
    bake_camera(clk, co, tgt, pose)


# ------------------------------------------------------------------------------------------ build

DATA = None


def build(fps, plan="overview"):
    global DATA
    _augmented.clear()
    seq = plan == "sequence"
    if seq:
        R.DRESSED = set(R.UNITS)                  # every unit gets its props and work lights in turn
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
    sc = bpy.context.scene
    if seq:
        sched = SCHED.build(); W, total_s = SCHED.windows(sched)
        L = json.loads(LOGISTICS.read_text())
        clk = Clock(fps, total_s)
        sequence_scene(S, L, c_seq)
        for lo in bpy.data.collections["Studio light rig"].objects:
            lo.visible_camera = False              # this film looks from the east, toward the key light
        bpy.data.materials["Studio floor"].node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.95
        for u in SCHED.ORDER:
            for i, name in enumerate(PHASES):
                sc.timeline_markers.new(f"{u} {name}", frame=clk.f(W[u][i][0]))
        S.update(sched=sched, W=W, L=L)
    else:
        clk = Clock(fps)
        for i, name in enumerate(PHASES):
            sc.timeline_markers.new(name, frame=clk.phase_frame(i))
    sc.render.fps = fps; sc.frame_start = 1; sc.frame_end = clk.end
    if seq:
        choreograph_seq(clk, S, W, sched)
    else:
        choreograph(clk, S)
    stats.update(hidden_when_faded=hide_vanished(clk))
    if seq:
        co, tgt = camera_objects()
        S["shots"] = seq_shots(co, W, L, total_s)
        camera_rig_seq(clk, S["shots"], co, tgt)
    else:
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


def validate_seq(clk, S, stats):
    """Per-unit sequence checks, cross-unit checks (one unit at a time), and framing per shot."""
    from bpy_extras.object_utils import world_to_camera_view
    sc = bpy.context.scene
    W, plan = S["W"], S["sched"]
    errs = []
    if abs(stats["pipe_lf_anim"] - R.TAKE["totals"]["pipe_lf"]) > 0.05:
        errs.append(f'ABS length {stats["pipe_lf_anim"]:.2f} != takeoff')
    if clk.end != round(SCHED.windows(plan)[1] * clk.fps):
        errs.append("film length does not match schedule.windows()")
    at = lambda u, i, s: clk.f(W[u][i][0] + (W[u][i][1] - W[u][i][0]) * s / PHASE_S)
    of = lambda name, u: [o for o in S[name] if o.get("unit") == u]
    cure_frac = lambda u: next(min(0.8, p["cure_days"] / p["days"][6]) for p in plan["units"] if p["unit"] == u)
    checks = []
    for n, u in enumerate(SCHED.ORDER):
        fx = of("fixtures", u); kept = [o for o in fx if o.get("service")]; moved = [o for o in fx if not o.get("service")]
        before, after = SCHED.ORDER[n + 1:], SCHED.ORDER[:n]
        checks += [
            (at(u, 0, 0.2), lambda u=u, fx=fx: all(o.get("vanish", 0) < 0.01 for o in fx), f"{u}: fixtures in place at start"),
            (at(u, 0, 2.0), lambda u=u: all(o["vanish"] > 0.8 for o in of("soil", u)), f"{u}: x-ray during investigation"),
            (at(u, 1, 0.0), lambda u=u: all(o["vanish"] < 0.01 for o in of("marks", u)), f"{u}: routes marked"),
            (at(u, 2, 0.1), lambda m=moved: all(o["vanish"] > 0.99 for o in m), f"{u}: fixtures out before demolition"),
            (at(u, 2, 0.1), lambda k=kept: k and all(o.get("vanish", 0) < 0.01 for o in k), f"{u}: service pair stays (SOR 21)"),
            (at(u, 2, 3.0), lambda u=u: all(o["vanish"] < 0.01 for o in of("routes_out", u)), f"{u}: haul-out route shown"),
            (at(u, 3, 0.0), lambda u=u: all(o["vanish"] > 0.99 for o in of("marks", u)), f"{u}: marks gone with the slab"),
            (at(u, 3, 0.5), lambda u=u: all(o.scale.z < 0.05 for o in of("soil", u)), f"{u}: trenches excavated"),
            (at(u, 3, 0.9), lambda u=u: all(o.data.bevel_factor_end < 1e-3 for o in of("abs", u)), f"{u}: no ABS before installation"),
            (at(u, 3, 0.9), lambda u=u: all(o["vanish"] > 0.99 for o in of("ci", u)), f"{u}: cast iron gone before ABS"),
            (at(u, 4, 0.0), lambda u=u: all(o.data.bevel_factor_end > 0.999 for o in of("abs", u)), f"{u}: all ABS in by the test"),
            (at(u, 4, 3.0), lambda u=u: all(o["water"] > 0.99 for o in of("abs", u)), f"{u}: system full during hold"),
            (at(u, 5, 0.0), lambda u=u: all(o["water"] < 0.01 for o in of("abs", u)), f"{u}: drained before backfill"),
            (at(u, 5, 2.0), lambda u=u: all(o["vanish"] < 0.01 for o in of("routes_in", u)), f"{u}: haul-in route shown"),
            (at(u, 3, 2.0), lambda u=u: all(o["vanish"] < 0.01 for o in of("bypass", u)), f"{u}: stacks on bypass"),
            (at(u, 7, 2.0), lambda u=u: all(o["vanish"] > 0.99 for o in of("bypass", u)), f"{u}: bypass removed"),
            (at(u, 6, 0.0), lambda u=u: all(o["vanish"] < 0.01 for o in of("pour", u)), f"{u}: pour-back placed"),
            (at(u, 6, PHASE_S * cure_frac(u) - 0.02), lambda u=u: all(o["vanish"] > 0.99 for o in of("finish", u)),
             f"{u}: no finishes before the cure ends"),
            (at(u, 7, 3.99), lambda u=u, fx=fx, m=moved: all(o.get("vanish", 0) < 0.01 for o in fx) and
             all(o["vanish"] < 0.01 and abs(o.location.z) < 1e-4 for o in m + of("finish", u)),
             f"{u}: fixtures and finishes restored"),
            (at(u, 7, 3.99), lambda u=u: all(o["vanish"] > 0.99 for o in of("protection", u)), f"{u}: protection removed"),
            # one unit at a time: the others are untouched (later units) or finished (earlier units)
            (at(u, 3, 2.0), lambda b=before: all(o.scale.z > 0.999 for v in b for o in of("soil", v)) and
             all(o.get("vanish", 0) < 0.01 for v in b for o in of("fixtures", v) + of("slab", v)), f"{u}: later units untouched"),
            (at(u, 3, 2.0), lambda a=after: all(o["vanish"] < 0.01 for v in a for o in of("pour", v) + of("finish", v)) and
             all(o["vanish"] > 0.99 for v in a for o in of("protection", v)), f"{u}: earlier units finished"),
            (at(u, 3, 2.0), lambda a=after, b=before: all(o["vanish"] > 0.99 for v in a + b for o in of("routes_out", v) + of("routes_in", v)),
             f"{u}: only this unit's routes"),
        ]
    for f, test, label_ in checks:
        sc.frame_set(f)
        if not test():
            errs.append(f"frame {f}: {label_}")
    ends = [s_[0] for s_ in S["shots"][1:]] + [clk.end / clk.fps]
    worst = 0.0
    for (t_in, blend, _, _, pts), t_end in zip(S["shots"], ends):
        for s_ in (t_in + blend + 0.05, t_end - 0.05):
            sc.frame_set(min(clk.end, clk.f(s_)))
            v = [world_to_camera_view(sc, sc.camera, p) for p in pts]
            b = (min(q.x for q in v), max(q.x for q in v), min(q.y for q in v), max(q.y for q in v))
            out = max(SEQ_SAFE[0] - b[0], b[1] - SEQ_SAFE[1], SEQ_SAFE[2] - b[2], b[3] - SEQ_SAFE[3])
            worst = max(worst, out)
            if out > 0:
                errs.append(f"t={s_:.2f}s: shot leaves the safe frame {[round(x, 3) for x in b]}")
    res = {"ok": not errs, "errors": errs, "plan": "sequence", "frames": clk.end, "fps": clk.fps,
           "seconds": round(clk.end / clk.fps, 2), "working_days": plan["working_days"], "order": SCHED.ORDER,
           "pipe_lf": round(stats["pipe_lf_anim"], 2), "checks": len(checks), "shots": len(S["shots"]),
           "framing_checks": 2 * len(S["shots"]), "hidden_when_faded": stats.get("hidden_when_faded"),
           "service_pairs": {u: [o.name for o in v] for u, v in S["service"].items()},
           "stack_bypasses": len(S["bypass"])}
    print("CHECKS", json.dumps(res), flush=True)
    if errs:
        sys.exit(1)
    return res


def seq_stills(W):
    """Check frames: intro, and for each unit demolition (haul shot), ABS, water test, backfill; outro."""
    t = [1.0]
    for u in SCHED.ORDER:
        w = W[u]
        t += [w[2][0] + 0.8 * (w[2][1] - w[2][0]), w[3][0] + 0.8 * (w[3][1] - w[3][0]),
              w[4][0] + 0.6 * (w[4][1] - w[4][0]), w[5][0] + 0.7 * (w[5][1] - w[5][0])]
    t.append(W[SCHED.ORDER[-1]][7][1] + 2.0)
    return t


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
    ap.add_argument("--plan", default="overview", choices=["overview", "sequence"],
                    help="overview: all units together, 8 x 4 s; sequence: one unit at a time on the schedule")
    ap.add_argument("--no-render", action="store_true")
    ap.add_argument("--stills", action="store_true", help="one check frame per phase (2 s into each)")
    ap.add_argument("--frames", default="", help="start:end:step")
    ap.add_argument("--res", type=float, default=1.0, help="scale on 1920x1080")
    ap.add_argument("--samples", type=int, default=128)
    ap.add_argument("--device", default="CPU", choices=["CPU", "CUDA", "OPTIX"])
    ap.add_argument("--tag", default="", help="frame folder name (default final, or seq for --plan sequence)")
    ap.add_argument("--worker", default="0/1")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    seq = a.plan == "sequence"
    clk, S, stats = build(a.fps, a.plan)
    (validate_seq if seq else validate)(clk, S, stats)
    if a.no_render:
        blend = OUT / ("Meydenbauer-B-4D-sequence.blend" if seq else "Meydenbauer-B-4D.blend")
        bpy.ops.file.pack_all()
        bpy.ops.wm.save_as_mainfile(filepath=str(blend), compress=True)
        print("SAVED", blend)
        return
    if a.stills:
        frames = [clk.f(t) for t in seq_stills(S["W"])] if seq else [clk.phase_frame(i, 2.0) for i in range(len(PHASES))]
        tag = a.tag or ("seq-stills" if seq else "stills")
    else:
        s0, s1, st = (int(v) for v in (a.frames or f"1:{clk.end}:1").split(":"))
        frames, tag = list(range(s0, s1 + 1, st)), a.tag or ("seq" if seq else "final")
    res = (int(1920 * a.res) // 2 * 2, int(1080 * a.res) // 2 * 2)
    k, n = (int(v) for v in a.worker.split("/"))
    render_frames(frames, res, a.samples, a.device, f"{tag}-{a.fps}", (k, n))


if __name__ == "__main__":
    main()
