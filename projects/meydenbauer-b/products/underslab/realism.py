"""Construction-phase realism model of Building B's ground floor: what the crew will face.

Everything is built from the project's JSON (no PDF parsing):
  meydenbauer-b.spec.json       new under-slab waste network (P1.02)
  meydenbauer-b.shell.json      walls, openings, rooms, ceiling heights, tubs/showers (P2.1)
  meydenbauer-b.structure.json  record footings (Exhibit B, registered)
  build/meydenbauer-b/takeoff.json  S2 trench footprints
The scene shows the work in progress: the slab saw-cut and the trench open to its
modelled depth in soil, the bedding and the new ABS, record footings where the trench
meets them, and finishes, floor protection, dust walls and work lights in the units.

Each view is built in its own pass. A section view clips the plan at a vertical plane, so
the cut through soil, footing, slab and pipe is exact geometry rather than a render trick.

Usage:
  python projects/meydenbauer-b/products/underslab/realism.py                       # all views, local CPU preview
  python projects/meydenbauer-b/products/underslab/realism.py --only section_b103_east --samples 32 --res 0.5
  python projects/meydenbauer-b/products/underslab/realism.py --device OPTIX --profile final   # RunPod GPU
  python projects/meydenbauer-b/products/underslab/realism.py --no-render           # model + checks + .blend only
"""
import argparse, json, math, sys, time
from pathlib import Path

import bpy, bmesh
import numpy as np
import shapely
from mathutils import Vector
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union

HERE = Path(__file__).resolve().parent
from bmodels.paths import ROOT  # noqa: E402  (repo root)
sys.path.insert(0, str(HERE))
import assets  # noqa: E402

OUT = ROOT / "build" / "meydenbauer-b" / "realism"
SPEC = json.loads((HERE / "meydenbauer-b.spec.json").read_text())
SHELL = json.loads((HERE / "meydenbauer-b.shell.json").read_text())
STRUCT = json.loads((HERE / "meydenbauer-b.structure.json").read_text())
TAKE = json.loads((ROOT / "build/meydenbauer-b/takeoff.json").read_text())
HDRI = ROOT / "assets/hdri/kloofendal_48d_partly_cloudy_puresky_1k.hdr"

FT = 0.3048
TIE_DEPTH = 3.5                                  # POC invert, ft below FF (assumed; SOR 2.5-4.5)
SLOPE = TAKE["inputs"]["slope_ft_per_ft"]
BEDDING = TAKE["inputs"]["bedding_ft"]
SLAB = TAKE["inputs"]["slab_ft"]
OD_IN = {2: 2.375, 3: 3.5, 4: 4.5}
WALL_TOP = 9.0
DOOR_HEAD = 6.667
FINISH = 0.05                                    # 9/16" hardwood / porcelain on thinset, top of finish
GROUND = 12.0                                    # depth of the soil block shown
UNITS = {"B-101": (-4.0, 45.9), "B-102": (45.9, 80.0), "B-103": (80.0, 113.6), "B-104": (113.6, 166.0)}
DRESSED = {"B-104", "B-103"}                     # units with props (others: finishes and protection only)

VIEWS = {
    # name: camera position, target (plan ft, height ft), lens mm, clip half-plane, ceilings shown
    "b104_plan": dict(cam=(138, 28, 60), look=(138, 28, 0), lens=None, ortho=80, clip=None, ceilings=False,
                      hide=("Dust walls (6-mil poly)", "Spring poles")),
    "b104_overview": dict(cam=(168, 60, 78), look=(138, 24, -1), lens=24, clip=None, ceilings=False,
                          hide=("Dust walls (6-mil poly)", "Spring poles")),
    "b104_master_bath": dict(cam=(146.6, 10.4, 5.3), look=(142.5, 1.5, -0.5), lens=16, clip=None, ceilings=True),
    "b104_kitchen_run": dict(cam=(141.2, 42.8, 5.4), look=(127.0, 40.3, -2.0), lens=20, clip=None, ceilings=True,
                             hide=()),
    "section_b103_east": dict(cam=(85.5, 9.0, 0.6), look=(95.1, 4.8, -1.6), lens=26, clip=("x>", 95.1), ceilings=True),
}
def _z_pipe(x, y, nom=2):
    return trench_bottom(x, y) + BEDDING + OD_IN[nom] / 24


ANNOTATIONS = {   # view: [(label, plan x, y, z or callable)]; drawn with leaders after render
    "section_b103_east": [
        ("Record footing (1974, Exhibit B): 2'-6\" wide, bottom 3'-4\" below floor", 95.1, 4.4, -1.6),
        ("Trench bottom at the lav pit, about 2.9 ft below floor (depth assumed)", 95.1, 6.3, lambda x, y: trench_bottom(x, y)),
        ("New 2\" ABS on 4\" bedding (2/P5.0)", 95.1, 7.6, lambda x, y: _z_pipe(x, y)),
        ("Slab 4\" (assumed), saw-cut; vapor barrier unknown", 95.1, 10.5, -0.17),
    ],
    "b104_kitchen_run": [
        ("4\" ABS to the KS stack: P1.02 new, P3.2 \"previous replaced\" (RFI 4)", 133.0, 40.4, lambda x, y: _z_pipe(x, y, 4)),
        ("Saw-cut slab edge; finish removed 6\" back", 137.0, 41.5, 0.0),
        ("Ram Board, taped seams", 136.0, 44.0, 0.07),
        ("6-mil poly dust wall on spring poles", 131.0, 36.2, 4.5),
    ],
    "b104_master_bath": [
        ("Lav pits at the east wall: the record footing projects about 10\" inside it", 146.4, 0.7, -0.45),
        ("Slab and soil left between the two lav trenches (S2 as drawn)", 144.2, 3.2, 0.1),
    ],
}
PROFILES = {"preview": (1280, 800), "final": (2560, 1600), "uhd": (3840, 2400)}


# ------------------------------------------------------------------------------------------ geometry

def P(x, y, z=0.0):
    """Plan feet (x south along the building, y west) and height feet -> Blender metres; +Y east."""
    return Vector((x * FT, -y * FT, z * FT))


def polys(g):
    if g is None or g.is_empty:
        return []
    if g.geom_type == "Polygon":
        return [g]
    return [p for q in getattr(g, "geoms", []) for p in polys(q)]


def clean(g, tol=0.01):
    g = g.buffer(0)
    return unary_union([p.simplify(tol) for p in polys(g) if p.area > 0.02])


def prism(bm, poly, ztop, zbot, densify=None):
    """Closed solid over a polygon (with holes). ztop/zbot: number or f(x, y) in feet."""
    zt = ztop if callable(ztop) else (lambda x, y: ztop)
    zb = zbot if callable(zbot) else (lambda x, y: zbot)
    for p in polys(poly):
        p = shapely.set_precision(p, 1e-4)
        if densify:
            p = p.segmentize(densify)
        if p.is_empty or p.area < 1e-3:
            continue
        p = shapely.geometry.polygon.orient(p)
        top, bot = {}, {}

        def v(cache, x, y, f):
            k = (round(x, 4), round(y, 4))
            if k not in cache:
                cache[k] = bm.verts.new(P(x, y, f(x, y)))
            return cache[k]
        for tri in shapely.constrained_delaunay_triangles(p).geoms:
            c = list(tri.exterior.coords)[:3]
            try:
                bm.faces.new([v(top, x, y, zt) for x, y in c])
                bm.faces.new([v(bot, x, y, zb) for x, y in c[::-1]])
            except ValueError:
                pass
        for ring in [p.exterior, *p.interiors]:
            cs = list(ring.coords)[:-1]
            for (x1, y1), (x2, y2) in zip(cs, cs[1:] + cs[:1]):
                try:
                    bm.faces.new([v(bot, x1, y1, zb), v(bot, x2, y2, zb), v(top, x2, y2, zt), v(top, x1, y1, zt)])
                except ValueError:
                    pass
    return bm


def obj(name, bm, mats, coll, **props):
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); coll.objects.link(o)
    for m in (mats if isinstance(mats, (list, tuple)) else [mats]):
        o.data.materials.append(m)
    for k, v in props.items():
        o[k] = v if isinstance(v, (int, float, str)) else json.dumps(v)
    return o


def solid(name, poly, ztop, zbot, mats, coll, densify=None, **props):
    return obj(name, prism(bmesh.new(), poly, ztop, zbot, densify), mats, coll, **props)


def oriented_box(bm, p0, p1, t, z0, z1):
    """Box along the plan segment p0-p1, t ft thick, from z0 to z1."""
    ls = LineString([p0, p1])
    if ls.length < 1e-3:
        return bm
    return prism(bm, ls.buffer(t / 2, cap_style="flat"), z1, z0)


def centreline(poly):
    """Long axis of a thin strip polygon: (p0, p1, thickness)."""
    r = list(poly.minimum_rotated_rectangle.exterior.coords)[:4]
    e = [(r[i], r[(i + 1) % 4]) for i in range(4)]
    L = [math.dist(a, b) for a, b in e]
    i = int(np.argmin(L))
    mid = lambda a, b: ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
    return mid(*e[i]), mid(*e[(i + 2) % 4]), L[i]


def coll(name, parent=None):
    c = bpy.data.collections.new(name)
    (parent or bpy.context.scene.collection).children.link(c)
    return c


# ------------------------------------------------------------------------------------------ materials

def principled(name, rgb, rough=0.5, metal=0.0, coat=0.0, spec=0.5):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    b.inputs["Coat Weight"].default_value = coat
    b.inputs["Specular IOR Level"].default_value = spec
    return m


def materials(data):
    M = {}
    M["soil"] = assets.pbr(principled("Excavated soil (CC0 scan)", (1, 1, 1), 0.9), data, "excavated_soil_wall",
                           tint=(0.80, 0.76, 0.72), rough=(0.75, 1.0), bump=0.6, scale=0.55, variation=0.85)
    M["landscape"] = assets.pbr(principled("Landscape bed (CC0 scan)", (1, 1, 1), 0.95), data, "excavated_soil_wall",
                                tint=(0.42, 0.36, 0.30), rough=(0.8, 1.0), bump=0.5, scale=0.4)
    M["gravel"] = assets.pbr(principled("Pipe bedding gravel (CC0 scan)", (1, 1, 1), 0.85), data, "gravel",
                             tint=(0.95, 0.93, 0.9), rough=(0.6, 0.95), bump=0.8, scale=0.25)
    M["slab"] = assets.pbr(principled("Slab concrete (CC0 scan)", (1, 1, 1), 0.8), data, "brushed_concrete",
                           tint=(0.92, 0.92, 0.9), rough=(0.6, 0.95), bump=0.2, scale=0.6)
    M["sawcut"] = assets.pbr(principled("Saw-cut slab edge (CC0 scan)", (1, 1, 1), 0.7), data, "brushed_concrete",
                             tint=(1.15, 1.13, 1.1), rough=(0.5, 0.8), bump=0.1, scale=0.25)
    M["footing"] = assets.pbr(principled("Record footing concrete (CC0 scan)", (1, 1, 1), 0.8), data, "concrete",
                              tint=(0.85, 0.85, 0.83), rough=(0.6, 0.95), bump=0.35, scale=0.8)
    M["wall"] = assets.pbr(principled("Painted gypsum (CC0 scan)", (1, 1, 1), 0.6), data, "white_plaster_02",
                           tint=(0.95, 0.93, 0.89), rough=(0.45, 0.65), bump=0.05, scale=1.0, variation=0.12)
    M["ceiling"] = assets.pbr(principled("Ceiling gypsum (CC0 scan)", (1, 1, 1), 0.7), data, "white_plaster_02",
                              tint=(0.97, 0.96, 0.94), rough=(0.6, 0.8), bump=0.08, scale=0.6, variation=0.1)
    M["wood"] = assets.pbr(principled("EHF engineered oak (CC0 scan)", (1, 1, 1), 0.4), data, "wood_floor",
                           tint=(1.08, 1.0, 0.9), rough=(0.25, 0.55), bump=0.15, scale=1.0)
    M["quartz"] = assets.pbr(principled("Quartz counter (CC0 scan)", (1, 1, 1), 0.15), data, "marble_01",
                             tint=(1.05, 1.05, 1.05), rough=(0.05, 0.2), bump=0.02, scale=0.8)
    M["tile"] = tile_material("NS-2 porcelain 12x24 (procedural)", (0.80, 0.78, 0.74), (0.56, 0.54, 0.50), 24, 12, 0.33)
    M["mosaic"] = tile_material("NS-1 limestone mosaic (procedural)", (0.82, 0.79, 0.72), (0.55, 0.53, 0.49), 3, 1, 0.5)
    M["base"] = principled("Painted base trim", (0.93, 0.92, 0.89), 0.3)
    M["abs"] = principled("ABS DWV (black)", (0.018, 0.018, 0.02), 0.42, spec=0.6)
    M["cap"] = principled("Test cap", (0.75, 0.12, 0.06), 0.5)
    M["vapor"] = principled("Vapor barrier (assumed)", (0.05, 0.05, 0.055), 0.35, spec=0.7)
    M["frame"] = principled("Window frame dark bronze", (0.07, 0.06, 0.05), 0.35, metal=0.6)
    M["enamel"] = principled("Tub enamel", (0.93, 0.93, 0.91), 0.08, coat=0.6)
    M["cabinet"] = principled("CAB-1 painted shaker", (0.92, 0.91, 0.88), 0.35)
    M["porcelain"] = principled("Vitreous china", (0.95, 0.95, 0.94), 0.1, coat=0.8)
    M["bucket"] = principled("5-gal bucket", (0.95, 0.36, 0.04), 0.45)
    M["pole"] = principled("Spring pole aluminium", (0.8, 0.8, 0.82), 0.3, metal=1.0)
    M["housing"] = principled("Work light housing", (0.92, 0.62, 0.04), 0.4)
    M["black"] = principled("Black plastic", (0.02, 0.02, 0.02), 0.5)
    M["glass"] = glass_material()
    M["poly"] = poly_material()
    M["ramboard"] = ramboard_material()
    M["led"] = emitter("Work light LED", (1.0, 0.96, 0.9), 40.0)
    M["lawn"] = lawn_material()
    return M


def tile_material(name, field, grout, w_in, h_in, offset):
    m = bpy.data.materials.new(name); m.use_nodes = True
    n, l = m.node_tree.nodes, m.node_tree.links
    b = n["Principled BSDF"]; b.inputs["Roughness"].default_value = 0.35
    tc = n.new("ShaderNodeTexCoord"); mp = n.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (1 / FT * 12 / w_in, 1 / FT * 12 / w_in, 1)
    l.new(tc.outputs["Object"], mp.inputs["Vector"])
    br = n.new("ShaderNodeTexBrick")
    br.offset = offset; br.inputs["Scale"].default_value = 1.0
    br.inputs["Mortar Size"].default_value = 0.012 * 24 / w_in
    br.inputs["Brick Width"].default_value = 1.0; br.inputs["Row Height"].default_value = h_in / w_in
    br.inputs["Color1"].default_value = (*field, 1)
    br.inputs["Color2"].default_value = (*[c * 0.97 for c in field], 1)
    br.inputs["Mortar"].default_value = (*grout, 1)
    l.new(mp.outputs[0], br.inputs["Vector"])
    nz = n.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 18; nz.inputs["Detail"].default_value = 8
    l.new(mp.outputs[0], nz.inputs["Vector"])
    mix = n.new("ShaderNodeMix"); mix.data_type = "RGBA"; mix.blend_type = "OVERLAY"
    mix.inputs["Factor"].default_value = 0.12
    l.new(br.outputs["Color"], mix.inputs["A"]); l.new(nz.outputs["Color"], mix.inputs["B"])
    l.new(mix.outputs["Result"], b.inputs["Base Color"])
    bp = n.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = 0.35; bp.invert = True
    l.new(br.outputs["Fac"], bp.inputs["Height"]); l.new(bp.outputs["Normal"], b.inputs["Normal"])
    return m


def lawn_material():
    m = bpy.data.materials.new("Lawn (procedural)"); m.use_nodes = True
    n, l = m.node_tree.nodes, m.node_tree.links
    b = n["Principled BSDF"]; b.inputs["Roughness"].default_value = 0.9
    tc = n.new("ShaderNodeTexCoord")
    nz = n.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 60; nz.inputs["Detail"].default_value = 12
    l.new(tc.outputs["Object"], nz.inputs["Vector"])
    ramp = n.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (0.035, 0.07, 0.02, 1); ramp.color_ramp.elements[1].color = (0.11, 0.2, 0.05, 1)
    l.new(nz.outputs["Fac"], ramp.inputs["Fac"]); l.new(ramp.outputs["Color"], b.inputs["Base Color"])
    bp = n.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = 0.6
    l.new(nz.outputs["Fac"], bp.inputs["Height"]); l.new(bp.outputs["Normal"], b.inputs["Normal"])
    return m


def glass_material():
    """Clear glazing that does not block sunlight (shadow rays pass), as window glass does."""
    m = bpy.data.materials.new("Glazing"); m.use_nodes = True
    n, l = m.node_tree.nodes, m.node_tree.links
    out = n["Material Output"]; n.remove(n["Principled BSDF"])
    g = n.new("ShaderNodeBsdfGlass"); g.inputs["Roughness"].default_value = 0.0; g.inputs["IOR"].default_value = 1.5
    g.inputs["Color"].default_value = (0.92, 0.96, 0.95, 1)
    t = n.new("ShaderNodeBsdfTransparent")
    lp = n.new("ShaderNodeLightPath"); mix = n.new("ShaderNodeMixShader")
    l.new(lp.outputs["Is Shadow Ray"], mix.inputs["Fac"])
    l.new(g.outputs[0], mix.inputs[1]); l.new(t.outputs[0], mix.inputs[2]); l.new(mix.outputs[0], out.inputs["Surface"])
    return m


def poly_material():
    """6-mil poly sheeting: mostly see-through, milky and glossy, slightly wrinkled."""
    m = bpy.data.materials.new("Dust wall 6-mil poly"); m.use_nodes = True
    n, l = m.node_tree.nodes, m.node_tree.links
    out = n["Material Output"]; b = n["Principled BSDF"]
    b.inputs["Base Color"].default_value = (0.9, 0.92, 0.93, 1); b.inputs["Roughness"].default_value = 0.25
    t = n.new("ShaderNodeBsdfTransparent"); mix = n.new("ShaderNodeMixShader")
    mix.inputs["Fac"].default_value = 0.86
    l.new(b.outputs[0], mix.inputs[1]); l.new(t.outputs[0], mix.inputs[2]); l.new(mix.outputs[0], out.inputs["Surface"])
    nz = n.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 2.5; nz.inputs["Detail"].default_value = 6
    nz.inputs["Distortion"].default_value = 1.5
    bp = n.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = 0.5
    l.new(nz.outputs["Fac"], bp.inputs["Height"]); l.new(bp.outputs["Normal"], b.inputs["Normal"])
    return m


def ramboard_material():
    """Ram Board floor protection: kraft-brown board, 38 in rolls, taped seams."""
    m = bpy.data.materials.new("Ram Board floor protection"); m.use_nodes = True
    n, l = m.node_tree.nodes, m.node_tree.links
    b = n["Principled BSDF"]; b.inputs["Roughness"].default_value = 0.85
    tc = n.new("ShaderNodeTexCoord")
    nz = n.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 40; nz.inputs["Detail"].default_value = 10
    l.new(tc.outputs["Object"], nz.inputs["Vector"])
    kraft = n.new("ShaderNodeMix"); kraft.data_type = "RGBA"
    kraft.inputs["A"].default_value = (0.29, 0.18, 0.09, 1); kraft.inputs["B"].default_value = (0.36, 0.24, 0.13, 1)
    l.new(nz.outputs["Fac"], kraft.inputs["Factor"])
    sep = n.new("ShaderNodeSeparateXYZ"); l.new(tc.outputs["Object"], sep.inputs["Vector"])
    wrap = n.new("ShaderNodeMath"); wrap.operation = "PINGPONG"; wrap.inputs[1].default_value = 38 * 0.0254 / 2
    l.new(sep.outputs["Y"], wrap.inputs[0])
    tape = n.new("ShaderNodeMath"); tape.operation = "LESS_THAN"; tape.inputs[1].default_value = 0.024
    l.new(wrap.outputs[0], tape.inputs[0])
    col = n.new("ShaderNodeMix"); col.data_type = "RGBA"; col.inputs["B"].default_value = (0.08, 0.28, 0.75, 1)
    l.new(tape.outputs[0], col.inputs["Factor"]); l.new(kraft.outputs["Result"], col.inputs["A"])
    l.new(col.outputs["Result"], b.inputs["Base Color"])
    bp = n.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = 0.15
    l.new(nz.outputs["Fac"], bp.inputs["Height"]); l.new(bp.outputs["Normal"], b.inputs["Normal"])
    return m


def emitter(name, rgb, strength):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb, 1)
    b.inputs["Emission Color"].default_value = (*rgb, 1); b.inputs["Emission Strength"].default_value = strength
    return m


def set_face_materials(o, rule):
    """rule(face_centre_ft, normal) -> material slot index."""
    for f in o.data.polygons:
        c = f.center; n = f.normal
        f.material_index = rule((c.x / FT, -c.y / FT, c.z / FT), (n.x, -n.y, n.z))


# ------------------------------------------------------------------------------------------ inputs

def depth_samples():
    pts = []
    for u in SPEC["units"]:
        N = u["nodes"]
        for e in u["edges"]:
            a, b = N[e["a"]], N[e["b"]]
            n = max(2, int(e["length_ft"] / 0.25) + 1)
            for t in np.linspace(0, 1, n):
                pts.append((a["xy_ft"][0] + (b["xy_ft"][0] - a["xy_ft"][0]) * t,
                            a["xy_ft"][1] + (b["xy_ft"][1] - a["xy_ft"][1]) * t,
                            TIE_DEPTH - SLOPE * (a["flow_ft"] + (b["flow_ft"] - a["flow_ft"]) * t)))
    return np.array(pts)


SAMPLES = depth_samples()


def trench_bottom(x, y):
    i = int(((SAMPLES[:, 0] - x) ** 2 + (SAMPLES[:, 1] - y) ** 2).argmin())
    return -(SAMPLES[i, 2] + BEDDING)


def plan_inputs(clip):
    env = Polygon(SHELL["envelope_ft"]).buffer(0)
    walls = unary_union([Polygon(w["ring_ft"], w["holes_ft"]).buffer(0) for w in SHELL["walls"]])
    trench = unary_union([Polygon(r).buffer(0) for u in TAKE["units"] for r in u["footprint_S2"]])
    outside = unary_union([Polygon(r).buffer(0) for u in TAKE["units"] for r in u.get("outside_S2", [])])
    trench = unary_union([trench, outside])
    footing = unary_union([Polygon(f["ring_ft"]).buffer(0) for f in STRUCT["footings"]])
    world = box(-30, -30, 200, 100)
    keep = world
    if clip:
        axis, v = clip[0], clip[1]
        keep = {"x>": box(v, -30, 200, 100), "x<": box(-30, -30, v, 100),
                "y>": box(-30, v, 200, 100), "y<": box(-30, -30, 200, v)}[axis]
    return dict(env=env, walls=walls, trench=trench, footing=footing, keep=keep)


# ------------------------------------------------------------------------------------------ build

def build(view):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = "IMPERIAL"; sc.unit_settings.length_unit = "FEET"
    data = assets.fetch()
    M = materials(data)
    V = VIEWS[view] if view else dict(clip=None, ceilings=True)
    I = plan_inputs(V["clip"])
    K = I["keep"]
    c_ground = coll("Ground and structure (below slab)")
    c_work = coll("New waste piping and bedding")
    c_build = coll("Building ground floor (P2.1)")
    c_ceil = coll("Ceilings")
    c_temp = coll("Temporary protection and dust control")
    c_props = coll("Props and fixtures (illustrative)")

    # --- ground: soil block minus the trench voids and the footings (Manifold boolean)
    site = I["env"].buffer(8, join_style="mitre")
    soil = solid("Soil (unclipped extent)", site.intersection(K), -SLAB, -GROUND, M["soil"], c_ground,
                 status="assumed", basis="native soil, uniform; grade outside the footprint at slab underside (assumed)")
    voids = coll("_cutters", c_ground)
    vt = I["trench"].buffer(0.0005)
    solid("Trench void", vt, 0.6, trench_bottom, M["soil"], voids, densify=0.75)
    solid("Footing cutter", I["footing"], -SLAB + 0.03, -STRUCT["footings"][0]["bottom_ft"], M["footing"], voids)
    md = soil.modifiers.new("trench and footings", "BOOLEAN"); md.operation = "DIFFERENCE"
    md.operand_type = "COLLECTION"; md.collection = voids; md.solver = "MANIFOLD"
    bpy.context.view_layer.objects.active = soil
    bpy.ops.object.modifier_apply(modifier=md.name)
    bpy.data.collections.remove(voids)
    soil.name = "Soil (excavated to modelled trench depth)"
    env = I["env"]
    solid("Lawn at the building", site.difference(env).difference(I["trench"]).intersection(K), -SLAB + 0.004, -SLAB,
          M["lawn"], c_ground, status="assumed", basis="grade assumed at slab underside")

    lawn = solid("Lawn beyond the dig", box(-900, -900, 1100, 1000).difference(site).intersection(K), -SLAB, -GROUND,
                 [M["soil"], M["lawn"]], c_ground, status="assumed", basis="context only")
    set_face_materials(lawn, lambda c, n: 1 if n[2] > 0.9 else 0)

    # --- record footings (Exhibit B), shown intact: where a trench meets one, it is in the way
    solid("Record footings (Exhibit B)", I["footing"].intersection(K), -SLAB, -STRUCT["footings"][0]["bottom_ft"],
          M["footing"], c_ground, status="provisional",
          source="Exhibit B FPB1/FPB2 registered to grid; 2'-6\" x 3'-0\", bottom 3'-4\" below FF (D2 sections 10, 11)")

    # --- slab (saw-cut at the trench), vapour barrier lip
    slab_poly = env.difference(I["trench"]).intersection(K)
    so = solid("Slab on grade (4\" assumed)", slab_poly, 0.0, -SLAB, [M["slab"], M["sawcut"]], c_ground,
               status="assumed", basis="slab thickness not documented; 10/P5.1 pour-back is the thicker of existing or 5\"")
    tb = I["trench"].boundary
    set_face_materials(so, lambda c, n: 1 if abs(n[2]) < 0.1 and tb.distance(Point(c[0], c[1])) < 0.05 else 0)
    solid("Vapor barrier (assumed)", env.difference(I["trench"].buffer(-0.04)).intersection(K), -SLAB, -SLAB - 0.015,
          M["vapor"], c_ground, status="assumed", basis="SOR Note 4: existing barrier to be identified at demolition")

    # --- bedding and pipe
    bed = I["trench"].buffer(-0.03).intersection(K).difference(I["footing"].buffer(0.02))
    solid("Pipe bedding (2/P5.0)", bed, lambda x, y: trench_bottom(x, y) + 0.45, lambda x, y: trench_bottom(x, y) - 0.02,
          M["gravel"], c_work, densify=0.75, status="provisional", source="2/P5.0 4\" bedding; depth assumed")
    lf = pipes(M, c_work, K)

    # --- building ground floor
    walls_k = I["walls"].intersection(K)
    solid("Walls (P2.1)", walls_k, WALL_TOP, 0.0, M["wall"], c_build, status="provisional",
          source="P2.1 wall double lines; height assumed to 9'-0\" above slab")
    base = I["walls"].buffer(0.045, join_style="mitre").difference(I["walls"]).difference(I["trench"].buffer(0.5))
    solid("Base trim", base.intersection(K).intersection(env), 0.4, FINISH, M["base"], c_build)
    openings(M, c_build, K)
    floors(M, I, c_build, K)
    ceilings(M, I, c_ceil, K)
    c_ceil.hide_render = not V["ceilings"]
    fixtures(M, I, c_props, K)
    protection(M, I, c_temp, K)
    props(M, I, c_props, K, data)
    lights(M, I, c_temp, K)
    room_lights(I, c_ceil, K)
    world_and_sun()
    return dict(pipe_lf=lf)


def pipes(M, c, K):
    lf = 0.0
    deg = {}
    for u in SPEC["units"]:
        N = u["nodes"]
        zc = lambda k, nom: -(TIE_DEPTH - SLOPE * N[k]["flow_ft"]) + OD_IN[nom] / 24
        for i, e in enumerate(u["edges"]):
            nom = e["nominal_in"]
            a, b = N[e["a"]]["xy_ft"], N[e["b"]]["xy_ft"]
            seg = LineString([a, b]).intersection(K)
            if seg.is_empty or seg.length < 1e-3:
                continue
            (x0, y0), (x1, y1) = list(seg.coords)[0], list(seg.coords)[-1]
            L = math.dist(a, b)
            za, zb = zc(e["a"], nom), zc(e["b"], nom)
            f = lambda x, y: za + (zb - za) * (math.dist(a, (x, y)) / L if L else 0)
            cu = bpy.data.curves.new(f'{u["unit"]}-R{i:03d}', "CURVE"); cu.dimensions = "3D"
            cu.bevel_depth = OD_IN[nom] / 24 * FT; cu.bevel_resolution = 6; cu.use_fill_caps = True
            sp = cu.splines.new("POLY"); sp.points.add(1)
            sp.points[0].co = (*P(x0, y0, f(x0, y0)), 1); sp.points[1].co = (*P(x1, y1, f(x1, y1)), 1)
            o = bpy.data.objects.new(cu.name, cu); c.objects.link(o); o.data.materials.append(M["abs"])
            o["nominal_in"] = nom; o["length_ft"] = round(e["length_ft"], 3); o["status"] = "provisional"
            lf += e["length_ft"] if seg.length > L - 1e-3 else 0.0
            for k in (e["a"], e["b"]):
                deg.setdefault((u["unit"], k), []).append(nom)
        # fittings at tees and bends, risers with test caps at every end
        for (unit, k), noms in deg.items():
            if unit != u["unit"]:
                continue
            x, y = N[k]["xy_ft"]
            if not K.contains(Point(x, y)):
                continue
            nom = max(noms)
            r = OD_IN[nom] / 24 * 1.18
            if len(noms) >= 2:
                bpy.ops.mesh.primitive_uv_sphere_add(radius=r * FT, location=P(x, y, zc(k, nom)), segments=20, ring_count=12)
                s = bpy.context.object; s.name = f"{unit}-fitting"; move(s, c); s.data.materials.append(M["abs"])
        for e in u["ends"]:
            k = e["node"]; x, y = N[k]["xy_ft"]
            if e["kind"] == "TEE" or not K.contains(Point(x, y)):
                continue
            nom = 4 if e["kind"] == "STACK-4" else 3 if e["kind"] in ("STACK-3", "WC", "WB") else 2
            z0 = zc(k, nom); top = 3.0 if e["kind"].startswith("STACK") else 0.35
            bpy.ops.mesh.primitive_cylinder_add(radius=OD_IN[nom] / 24 * FT, depth=(top - z0) * FT,
                                                location=P(x, y, (top + z0) / 2), vertices=24)
            s = bpy.context.object; s.name = f'{u["unit"]}-{e["kind"]}-riser'; move(s, c); s.data.materials.append(M["abs"])
            bpy.ops.mesh.primitive_cylinder_add(radius=OD_IN[nom] / 24 * FT * 1.12, depth=0.12 * FT,
                                                location=P(x, y, top + 0.06), vertices=24)
            s = bpy.context.object; s.name = f'{u["unit"]}-test-cap'; move(s, c); s.data.materials.append(M["cap"])
        deg = {}
    return lf


def move(o, c):
    for cc in o.users_collection:
        cc.objects.unlink(o)
    c.objects.link(o)


def openings(M, c, K):
    bm_hdr, bm_glass, bm_frame = bmesh.new(), bmesh.new(), bmesh.new()
    for o in SHELL["openings"]:
        poly = Polygon(o["ring_ft"]).buffer(0)
        if not K.contains(poly.centroid):
            continue
        if o["kind"] == "door":
            prism(bm_hdr, poly.intersection(K), WALL_TOP, DOOR_HEAD)
            continue
        p0, p1, t = centreline(poly)
        west = poly.centroid.y > 28
        sill, head = (0.35, 7.6) if west else (3.0, 7.0)
        t = max(t, 0.5)
        prism(bm_hdr, poly.intersection(K), WALL_TOP, head)
        prism(bm_hdr, poly.intersection(K), sill, 0.0)
        oriented_box(bm_glass, p0, p1, 0.03, sill + 0.12, head - 0.12)
        oriented_box(bm_frame, p0, p1, 0.18, sill, sill + 0.12)
        oriented_box(bm_frame, p0, p1, 0.18, head - 0.12, head)
        d = (p1[0] - p0[0], p1[1] - p0[1]); L = math.hypot(*d); u = (d[0] / L, d[1] / L)
        for s in [0.0] + [k * L / math.ceil(L / 5.0) for k in range(1, math.ceil(L / 5.0))] + [L]:
            q = (p0[0] + u[0] * s, p0[1] + u[1] * s)
            a = (q[0] - u[0] * 0.07, q[1] - u[1] * 0.07); b = (q[0] + u[0] * 0.07, q[1] + u[1] * 0.07)
            oriented_box(bm_frame, a, b, 0.18, sill, head)
    obj("Door and window headers / sills", bm_hdr, M["wall"], c)
    obj("Glazing", bm_glass, M["glass"], c, status="assumed", basis="sill/head heights from photos, not documented")
    obj("Window frames", bm_frame, M["frame"], c)


def unit_floor(I, unit):
    x0, x1 = UNITS[unit]
    return I["env"].intersection(box(x0, -30, x1, 100)).difference(I["walls"])


def floors(M, I, c, K):
    removed = I["trench"].buffer(0.5, join_style="mitre")
    tile = unary_union([Polygon(r["ring_ft"]).buffer(0) for r in SHELL["rooms"]
                        if r["name"] in ("BATH", "LAUNDRY")] +
                       [box(*f["box_ft"][0], *f["box_ft"][1]) for f in SHELL["fixtures"] if f["kind"] == "SHR"])
    for unit in UNITS:
        fl = unit_floor(I, unit).difference(removed).intersection(K)
        solid(f"{unit} hardwood EHF", fl.difference(tile), FINISH, 0.0, M["wood"], c, status="assumed",
              basis="finish by room type; B-104 per Addendum 1 custom finish schedule (EHF-2, NS-2)")
        solid(f"{unit} tile NS", fl.intersection(tile), FINISH, 0.0, M["tile"], c, status="assumed")


def ceilings(M, I, c, K):
    rooms = [(Polygon(r["ring_ft"]).buffer(0), r["ch_ft"]) for r in SHELL["rooms"] if r["ch_ft"]]
    done = unary_union([p for p, _ in rooms])
    bm = bmesh.new()
    for unit in UNITS:
        rest = unit_floor(I, unit).difference(done).intersection(K)
        prism(bm, rest, 8.05, 8.0)
    for p, h in rooms:
        prism(bm, p.intersection(K), h + 0.05, h)
    obj("Ceilings (room CH per P2.1)", bm, M["ceiling"], c, status="confirmed", source="P2.1 room tags CH")


def fixtures(M, I, c, K):
    bm_tub, bm_glass, bm_curb = bmesh.new(), bmesh.new(), bmesh.new()
    for f in SHELL["fixtures"]:
        bb = box(*f["box_ft"][0], *f["box_ft"][1])
        if not K.contains(bb.centroid):
            continue
        if f["kind"] == "TUB":
            outer = bb.buffer(0.15, join_style="mitre").difference(I["walls"]) if bb.area < 11 else bb
            inner = outer.buffer(-0.28, join_style="mitre")
            prism(bm_tub, outer.difference(inner), 1.25, 0.0)
            prism(bm_tub, inner, 0.28, 0.0)
        else:
            free = bb.exterior.difference(I["walls"].buffer(0.4))
            for seg in getattr(free, "geoms", [free]):
                if seg.length < 1.0:
                    continue
                cs = list(seg.coords)
                for a, b in zip(cs, cs[1:]):
                    oriented_box(bm_curb, a, b, 0.3, 0.33, 0.0)
                    oriented_box(bm_glass, a, b, 0.03, 6.6, 0.33)
    obj("Tubs (P2.1 symbols)", bm_tub, M["enamel"], c, status="provisional", basis="P2.1 tub symbol extent; 15\" rim assumed")
    obj("Shower glass", bm_glass, M["glass"], c, status="assumed")
    obj("Shower curbs", bm_curb, M["tile"], c, status="assumed")


def nearest_wall(walls, pt):
    q = Point(pt)
    best = min(polys(walls), key=lambda p: p.exterior.distance(q))
    on = best.exterior.interpolate(best.exterior.project(q))
    v = (pt[0] - on.x, pt[1] - on.y); L = math.hypot(*v) or 1
    return (on.x, on.y), (v[0] / L, v[1] / L)


def protection(M, I, c, K):
    removed = I["trench"].buffer(0.5, join_style="mitre")
    bm_rb, bm_poly, bm_pole = bmesh.new(), bmesh.new(), bmesh.new()
    for unit in UNITS:
        fl = unit_floor(I, unit)
        zone = I["trench"].buffer(5.0).intersection(fl)
        prism(bm_rb, zone.difference(removed.buffer(0.08)).intersection(K), FINISH + 0.02, FINISH)
        wall = I["trench"].buffer(3.5).intersection(fl).buffer(-0.05)
        edge = wall.boundary.difference(I["walls"].buffer(0.55)).intersection(I["env"].buffer(-0.5))
        for seg in getattr(edge, "geoms", [edge]):
            if seg.geom_type != "LineString" or seg.length < 1.5:
                continue
            seg = seg.intersection(K)
            for piece in getattr(seg, "geoms", [seg]):
                if piece.geom_type != "LineString" or piece.length < 1.0:
                    continue
                cs = list(piece.simplify(0.05).coords)
                for a, b in zip(cs, cs[1:]):
                    oriented_box(bm_poly, a, b, 0.004, 7.95, FINISH)
                n = max(1, math.ceil(piece.length / 5.0))
                for k in range(n + 1):
                    q = piece.interpolate(k / n, normalized=True)
                    prism(bm_pole, Point(q.x, q.y).buffer(0.05, quad_segs=4), 7.95, FINISH)
    obj("Ram Board floor protection", bm_rb, M["ramboard"], c, status="assumed",
        basis="protection within 5 ft of the work (SOR protection requirements; extent assumed)")
    obj("Dust walls (6-mil poly)", bm_poly, M["poly"], c, status="assumed", basis="containment 3.5 ft beyond trench (assumed)")
    obj("Spring poles", bm_pole, M["pole"], c, status="assumed")


def place_points(I, unit, n, seed, ring=1.8):
    fl = unit_floor(I, unit)
    band = I["trench"].buffer(ring).boundary.intersection(fl.buffer(-0.9)).difference(I["trench"].buffer(1.2))
    lines = [g for g in getattr(band, "geoms", [band]) if g.geom_type == "LineString" and g.length > 1.0]
    if not lines:
        return []
    rng = np.random.default_rng(seed)
    total = sum(g.length for g in lines); out = []
    for t in sorted(rng.uniform(0, total, n * 3)):
        acc = 0.0
        for g in lines:
            if t <= acc + g.length:
                p = g.interpolate(t - acc)
                if all(p.distance(Point(q)) > 2.2 for q, _ in out):
                    out.append(((p.x, p.y), float(rng.uniform(0, 2 * math.pi))))
                break
            acc += g.length
        if len(out) >= n:
            break
    return out


def props(M, I, c, K, data):
    lib = assets.library(bpy.context.scene, data)
    kit = ["cement_bag", "cement_bag", "cement_bag", "plastic_crate_01", "metal_toolbox", "rusted_spade_01",
           "sledgehammer_01", "plastic_broom", "dustpan", "trashbag", "cardboard_box_01"]
    bucket = make_bucket(M)
    toilet = make_toilet(M)
    for unit in sorted(DRESSED):
        pts = place_points(I, unit, len(kit) + 6, seed=hash(unit) % 1000)
        for (xy, yaw), mid in zip(pts, kit):
            if K.contains(Point(xy)):
                assets.instance(lib, mid, c, P(*xy, FINISH + 0.02), yaw=yaw)
        for (xy, yaw) in pts[len(kit):]:
            if K.contains(Point(xy)):
                e = bucket.copy(); e.location = P(*xy, FINISH + 0.02); e.rotation_euler[2] = yaw; c.objects.link(e)
        # pulled toilets stand on the protection, 3 ft from their flange
        for u in SPEC["units"]:
            if u["unit"] != unit:
                continue
            for e in u["ends"]:
                if e["kind"] != "WC":
                    continue
                x, y = u["nodes"][e["node"]]["xy_ft"]
                _, n_in = nearest_wall(I["walls"], (x, y))
                q = (x + n_in[0] * 3.2 + n_in[1] * 1.5, y + n_in[1] * 3.2 - n_in[0] * 1.5)
                if unit_floor(I, unit).buffer(-0.8).contains(Point(q)) and K.contains(Point(q)):
                    t = toilet.copy(); t.location = P(*q, FINISH + 0.02)
                    t.rotation_euler[2] = math.atan2(-n_in[1], n_in[0]) + 0.4; c.objects.link(t)
    for o in (bucket, toilet):
        bpy.data.objects.remove(o)


def make_bucket(M):
    """5-gallon pail with spoil: 12 in dia, 14.5 in tall."""
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=32, radius1=0.47 * FT, radius2=0.52 * FT, depth=1.2 * FT)
    bmesh.ops.translate(bm, verts=bm.verts, vec=(0, 0, 0.6 * FT))
    bmesh.ops.delete(bm, geom=[max(bm.faces, key=lambda f: f.calc_center_median().z)], context="FACES_ONLY")
    bmesh.ops.solidify(bm, geom=list(bm.faces), thickness=0.012 * FT)
    o = obj("5-gal bucket", bm, [M["bucket"], M["soil"]], bpy.context.scene.collection)
    bm2 = bmesh.new()
    bmesh.ops.create_cone(bm2, cap_ends=True, segments=32, radius1=0.49 * FT, radius2=0.49 * FT, depth=0.05 * FT)
    bmesh.ops.translate(bm2, verts=bm2.verts, vec=(0, 0, 1.1 * FT))
    s = obj("spoil", bm2, M["soil"], bpy.context.scene.collection)
    s.parent = o
    return o


def make_toilet(M):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=28, radius1=0.38 * FT, radius2=0.3 * FT, depth=0.9 * FT)
    bmesh.ops.translate(bm, verts=bm.verts, vec=(0.15 * FT, 0, 0.45 * FT))
    bowl = bmesh.ops.create_uvsphere(bm, u_segments=28, v_segments=14, radius=0.5 * FT)
    bmesh.ops.scale(bm, vec=(1.25, 0.85, 0.42), verts=bowl["verts"])
    bmesh.ops.translate(bm, verts=bowl["verts"], vec=(0.25 * FT, 0, 1.05 * FT))
    tank = bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=(0.6 * FT, 1.6 * FT, 1.25 * FT), verts=tank["verts"])
    bmesh.ops.translate(bm, verts=tank["verts"], vec=(-0.45 * FT, 0, 1.75 * FT))
    return obj("Pulled toilet (stored on protection)", bm, M["porcelain"], bpy.context.scene.collection)


def lights(M, I, c, K):
    """LED tripod work lights, two per dressed unit, aimed at the trench."""
    for unit in sorted(DRESSED):
        pts = place_points(I, unit, 2, seed=7 + len(unit), ring=2.6)
        for (x, y), _ in pts:
            if not K.contains(Point(x, y)):
                continue
            aim = I["trench"].boundary.interpolate(I["trench"].boundary.project(Point(x, y)))
            cu = bpy.data.curves.new(f"{unit} work light stand", "CURVE"); cu.dimensions = "3D"
            cu.bevel_depth = 0.035 * FT; cu.bevel_resolution = 3; cu.use_fill_caps = True
            for k in range(3):
                a = 2 * math.pi * k / 3 + 0.4
                sp = cu.splines.new("POLY"); sp.points.add(1)
                sp.points[0].co = (*P(x + 1.1 * math.cos(a), y + 1.1 * math.sin(a), FINISH + 0.02), 1)
                sp.points[1].co = (*P(x, y, 2.6), 1)
            sp = cu.splines.new("POLY"); sp.points.add(1)
            sp.points[0].co = (*P(x, y, 2.4), 1); sp.points[1].co = (*P(x, y, 5.7), 1)
            st = bpy.data.objects.new(cu.name, cu); c.objects.link(st); st.data.materials.append(M["black"])
            head = P(x, y, 5.9)
            target = P(aim.x, aim.y, -1.0)
            bpy.ops.mesh.primitive_cube_add(size=1, location=head)
            h = bpy.context.object; h.name = f"{unit} work light head"; move(h, c)
            h.scale = (0.75 * FT, 0.18 * FT, 0.55 * FT); h.data.materials.append(M["housing"])
            h.rotation_euler = (target - head).to_track_quat("Y", "Z").to_euler()
            ld = bpy.data.lights.new(f"{unit} LED", "AREA"); ld.energy = 220; ld.shape = "RECTANGLE"
            ld.size, ld.size_y = 0.6 * FT, 0.4 * FT; ld.color = (1.0, 0.95, 0.88)
            lo = bpy.data.objects.new(f"{unit} LED", ld); c.objects.link(lo)
            lo.location = head + (target - head).normalized() * 0.1
            lo.rotation_euler = (target - head).to_track_quat("-Z", "Y").to_euler()


def room_lights(I, c, K):
    """Existing ceiling lights left on in the dressed units: one warm panel per tagged room."""
    for r in SHELL["rooms"]:
        p = Polygon(r["ring_ft"]).buffer(0)
        q = p.representative_point()
        unit = next((u for u, (x0, x1) in UNITS.items() if x0 <= q.x < x1), None)
        if unit not in DRESSED or not r["ch_ft"] or not K.contains(q):
            continue
        ld = bpy.data.lights.new(f'{unit} {r["name"]} ceiling light', "AREA"); ld.shape = "DISK"
        ld.size = 1.0 * FT; ld.energy = 12 + 0.25 * p.area / 1.0; ld.color = (1.0, 0.86, 0.68)
        lo = bpy.data.objects.new(ld.name, ld); c.objects.link(lo)
        lo.location = P(q.x, q.y, r["ch_ft"] - 0.05)
        lo["status"] = "assumed"; lo["basis"] = "existing room lighting assumed on"


def world_and_sun():
    sc = bpy.context.scene
    w = bpy.data.worlds.new("Sky"); sc.world = w; w.use_nodes = True
    n, l = w.node_tree.nodes, w.node_tree.links
    env = n.new("ShaderNodeTexEnvironment"); env.image = bpy.data.images.load(str(HDRI))
    l.new(env.outputs["Color"], n["Background"].inputs["Color"])
    n["Background"].inputs["Strength"].default_value = 0.8
    sun = bpy.data.lights.new("Sun (late afternoon, from the lake side)", "SUN"); sun.energy = 3.2; sun.angle = math.radians(1.5)
    sun.color = (1.0, 0.93, 0.84)
    so = bpy.data.objects.new(sun.name, sun); sc.collection.objects.link(so)
    so.rotation_euler = (math.radians(58), 0, math.radians(-75))


# ------------------------------------------------------------------------------------------ render

def camera(view):
    V = VIEWS[view]
    cam = bpy.data.cameras.new(view); cam.clip_start = 0.05; cam.clip_end = 300
    if V.get("ortho"):
        cam.type = "ORTHO"; cam.ortho_scale = V["ortho"] * FT
    else:
        cam.lens = V["lens"]
    cam.sensor_width = 36
    o = bpy.data.objects.new(view, cam); bpy.context.scene.collection.objects.link(o)
    o.location = P(*V["cam"]); look = P(*V["look"])
    o.rotation_euler = (look - o.location).to_track_quat("-Z", "Y").to_euler()
    if V.get("ortho"):
        o.rotation_euler = (0.0, 0.0, math.pi / 2)        # straight down; north up, east right
    bpy.context.scene.camera = o
    for name in V.get("hide", ()):
        if name in bpy.data.objects:
            bpy.data.objects[name].hide_render = True
    return o


def render(view, res, samples, device, path):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    prefs = bpy.context.preferences.addons["cycles"].preferences
    if device != "CPU":
        prefs.compute_device_type = device; prefs.get_devices()
        for d in prefs.devices:
            d.use = d.type == device
        sc.cycles.device = "GPU"
    else:
        sc.cycles.device = "CPU"
    sc.cycles.samples = samples; sc.cycles.use_denoising = True; sc.cycles.denoiser = "OPENIMAGEDENOISE"
    sc.cycles.max_bounces = 8; sc.cycles.transparent_max_bounces = 16; sc.cycles.sample_clamp_indirect = 8
    sc.cycles.use_light_tree = True
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.view_settings.view_transform = "AgX"; sc.view_settings.look = "AgX - Medium High Contrast"
    sc.view_settings.exposure = 0.0
    sc.render.filepath = str(path)
    t = time.time(); bpy.ops.render.render(write_still=True)
    print(f"RENDER {view} {res[0]}x{res[1]} {samples} spp {time.time() - t:.0f}s", flush=True)


def annotate(path, view):
    """Leader-line callouts at projected 3D points (run inside Blender after the render)."""
    from bpy_extras.object_utils import world_to_camera_view
    from PIL import Image, ImageDraw, ImageFont
    items = ANNOTATIONS.get(view)
    if not items:
        return
    sc = bpy.context.scene; cam = sc.camera
    im = Image.open(path).convert("RGB"); w, h = im.size; k = w / 1280
    f = ImageFont.truetype("DejaVuSans-Bold.ttf", int(15 * k))
    d = ImageDraw.Draw(im, "RGBA")
    pts = []
    for label, x, y, z in items:
        zz = z(x, y) if callable(z) else z
        v = world_to_camera_view(sc, cam, P(x, y, zz))
        if not (0 <= v.x <= 1 and 0 <= v.y <= 1 and v.z > 0):
            print("ANNOTATION off-frame:", label); continue
        pts.append((label, v.x * w, (1 - v.y) * h))
    boxes = []
    for label, px, py in sorted(pts, key=lambda t: -t[2]):       # lowest dot first, labels stack upward
        tw = d.textlength(label, font=f); bh = 34 * k
        tx = min(max(px - tw / 2, 10 * k), w - tw - 10 * k)
        ty = py - 60 * k
        while any(not (tx + tw + 8 * k < bx0 or tx - 8 * k > bx1 or ty + bh < by0 or ty - 8 * k > by1) for bx0, by0, bx1, by1 in boxes):
            ty -= 8 * k
        ty = max(ty, 8 * k)
        boxes.append((tx - 6 * k, ty - 4 * k, tx + tw + 6 * k, ty + 22 * k))
        d.line([(px, py), (min(max(px, tx), tx + tw), ty + 22 * k)], fill=(255, 255, 255, 230), width=max(2, int(2 * k)))
        d.ellipse([px - 4 * k, py - 4 * k, px + 4 * k, py + 4 * k], fill=(255, 210, 0, 255))
        d.rounded_rectangle(boxes[-1], radius=5 * k, fill=(20, 20, 20, 205))
        d.text((tx, ty), label, font=f, fill=(255, 255, 255))
    im.save(path)


def caption(path, view):
    from PIL import Image, ImageDraw, ImageFont
    im = Image.open(path).convert("RGB"); w, h = im.size
    k = w / 1280
    try:
        f = ImageFont.truetype("DejaVuSans.ttf", int(17 * k)); fb = ImageFont.truetype("DejaVuSans-Bold.ttf", int(19 * k))
    except OSError:
        f = fb = ImageFont.load_default()
    titles = {
        "b104_plan": "B-104 plan cutaway, ceilings and dust walls off (north up, east right)",
        "b104_overview": "B-104 during the work: trench open, finishes protected (dust walls hidden)",
        "b104_master_bath": "B-104 master bath: lav branches dug at the east wall",
        "b104_kitchen_run": "B-104 living/kitchen: 4\" run to the KS stack (P1.02 vs P3.2 conflict)",
        "section_b103_east": "Section at B-103 east lav branch: trench against the record footing",
    }
    note = ("Illustrative model for internal planning, not a contract document. Plan from bid set P1.02/P2.1 (scale verified); "
            "footings from 1974 record set (reference only). Assumed: pipe depths (tie-in invert 3.5 ft), slab 4\", soil, "
            "protection/containment layout, props.")
    d0 = ImageDraw.Draw(im)
    lines, cur = [], ""
    for word in note.split(" "):
        if d0.textlength((cur + " " + word).strip(), font=f) > w - 40 * k:
            lines.append(cur); cur = word
        else:
            cur = (cur + " " + word).strip()
    lines.append(cur)
    band = int(44 * k + 24 * k * len(lines))
    out = Image.new("RGB", (w, h + band), (255, 255, 255)); out.paste(im, (0, 0))
    d = ImageDraw.Draw(out)
    d.text((int(18 * k), h + int(10 * k)), "101 Meydenbauer Bldg B — " + titles.get(view, view), font=fb, fill=(20, 20, 20))
    for i, line in enumerate(lines):
        d.text((int(18 * k), h + int(40 * k + 24 * k * i)), line, font=f, fill=(150, 40, 20))
    out.save(path)


def validate(stats):
    errs = []
    if abs(stats["pipe_lf"] - TAKE["totals"]["pipe_lf"]) > 0.05:
        errs.append(f'pipe LF {stats["pipe_lf"]:.2f} != takeoff {TAKE["totals"]["pipe_lf"]:.2f}')
    soil = next(o for o in bpy.data.objects if o.name.startswith("Soil"))
    if len(soil.data.polygons) < 1000:
        errs.append("soil boolean produced too few faces")
    walls = unary_union([Polygon(w["ring_ft"], w["holes_ft"]).buffer(0) for w in SHELL["walls"]])
    for v, V in VIEWS.items():
        x, y, z = V["cam"]
        if walls.contains(Point(x, y)) and z < WALL_TOP:
            errs.append(f"camera {v} is inside a wall")
    print("CHECKS", json.dumps({"ok": not errs, "errors": errs, **stats}), flush=True)
    if errs:
        sys.exit(1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="")
    ap.add_argument("--samples", type=int, default=64)
    ap.add_argument("--profile", default="preview", choices=PROFILES)
    ap.add_argument("--res", type=float, default=1.0, help="scale on the profile resolution")
    ap.add_argument("--device", default="CPU", choices=["CPU", "CUDA", "OPTIX"])
    ap.add_argument("--no-render", action="store_true")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    views = [v for v in VIEWS if not a.only or v in a.only.split(",")]
    if a.no_render or not a.only:
        stats = build(None)
        validate(stats)
        bpy.ops.file.pack_all()
        bpy.ops.wm.save_as_mainfile(filepath=str(OUT / "Meydenbauer-B-construction.blend"), compress=True)
        print("SAVED", OUT / "Meydenbauer-B-construction.blend")
        if a.no_render:
            return
    res = tuple(int(v * a.res) for v in PROFILES[a.profile])
    for v in views:
        stats = build(v)
        camera(v)
        path = OUT / f"{v}-{a.profile}.png"
        render(v, res, a.samples, a.device, path)
        annotate(path, v)
        caption(path, v)


if __name__ == "__main__":
    main()
