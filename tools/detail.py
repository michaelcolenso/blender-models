"""Detail (assembly) builder: a construction section drawn as component profiles, extruded
along the element it cuts through.

Section frame (inches): X horizontal in the section plane, Z vertical (plumb). Each
component is a rect [x0, z0, x1, z1] or a polygon [[x, z], ...] with a material, status and
source. The profile is swept along a path of `length_in`, rising `pitch` (rise per 12 run) —
a sheared sweep, so plumb faces stay plumb and the roof deck climbs, as at a rake.
Components that occur at spacing (lookouts, furring) use `repeat: {width_in, spacing_in}`.

Blender: x = X, y = distance along the path, z = Z (+ rise). 1 unit = 1 m.
"""
import math
import bpy, bmesh
from mathutils import Vector

IN = 0.0254


def _set_mat(o, m):
    o.data.materials.clear(); o.data.materials.append(m)
    for p in o.data.polygons:
        p.material_index = 0


def _profile(c):
    if "rect" in c:
        x0, z0, x1, z1 = c["rect"]
        return [(x0, z0), (x1, z0), (x1, z1), (x0, z1)]
    return [tuple(p) for p in c["polygon"]]


def sweep(name, prof, y0, y1, slope, coll):
    """Prism of polygon `prof` (X,Z inches) from path distance y0..y1 (inches), rising slope*y."""
    bm = bmesh.new()
    def ring(y):
        return [bm.verts.new(Vector((x * IN, y * IN, (z + slope * y) * IN))) for x, z in prof]
    a, b = ring(y0), ring(y1)
    n = len(prof)
    bm.faces.new(a[::-1]); bm.faces.new(b)
    for i in range(n):
        bm.faces.new((a[i], a[(i + 1) % n], b[(i + 1) % n], b[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); coll.objects.link(o)
    return o


def build(el, material, coll_for):
    L = el["path"]["length_in"]; slope = el["path"].get("pitch", 0) / 12.0
    step = el.get("cutaway_step_in", 0)  # presentation: outer layers stop short of the FAR end
    built = []
    for c in el["components"]:
        coll = coll_for(c.get("trade", "assembly"))
        prof = _profile(c)
        rep = c.get("repeat")
        Lc = L - step * c.get("peel", 0)  # near end (y=0) stays a full, true section
        spans = [(0, Lc)]
        if rep:
            w, s = rep["width_in"], rep["spacing_in"]; start = rep.get("start_in", 0)
            spans = []
            t = start
            while t + w <= Lc + 1e-6:
                spans.append((t, t + w)); t += s
        for k, (y0, y1) in enumerate(spans):
            nm = c["id"] if len(spans) == 1 else f"{c['id']}.{k + 1:02d}"
            o = sweep(nm, prof, y0, y1, slope, coll)
            _set_mat(o, material(c.get("material", "default")))
            meta = {k2: c.get(k2) for k2 in ("status", "source", "basis", "trade", "callout")}
            meta.update(id=nm, spec_id=el["id"], component=c["id"])
            for k2 in ("status", "source", "basis", "callout"):
                if c.get(k2):
                    o[k2] = str(c[k2])
            built.append((meta, o))
    bpy.context.view_layer.update()
    return built


def component_size(c):
    """(width X, height Z) in inches of a rect component."""
    x0, z0, x1, z1 = c["rect"]
    return round(x1 - x0, 4), round(z1 - z0, 4)


def annotate(png_path, spec, built, cam):
    """Label each component on a cutaway render with its callout (leaders to the far-end face)."""
    from bpy_extras.object_utils import world_to_camera_view
    from PIL import Image, ImageDraw, ImageFont
    sc = bpy.context.scene
    el = next(e for e in spec["elements"] if e.get("type") == "detail")
    L = el["path"]["length_in"]; slope = el["path"].get("pitch", 0) / 12.0; step = el.get("cutaway_step_in", 0)
    img = Image.open(png_path).convert("RGB"); W, H = img.size
    pts = []
    for c in el["components"]:
        prof = _profile(c)
        xs = [p[0] for p in prof]; zs = [p[1] for p in prof]
        xc, zc = (min(xs) + max(xs)) / 2, (min(zs) + max(zs)) / 2
        y = L - step * c.get("peel", 0) - 1.0
        if c.get("repeat"):
            y = c["repeat"].get("start_in", 0) + c["repeat"]["width_in"] / 2
        co = Vector((xc * IN, y * IN, (zc + slope * y) * IN))
        u, v, depth = world_to_camera_view(sc, cam, co)
        if 0 <= u <= 1 and 0 <= v <= 1 and depth > 0:
            txt = c.get("label") or c.get("callout") or c["id"].replace("_", " ")
            txt = txt.split(" (")[0].split(" — ")[0].split(";")[0].split(", extended")[0]
            tag = {"confirmed": "", "provisional": " [P]", "assumed": " [A]"}.get(c.get("status"), "")
            pts.append((u * W, (1 - v) * H, (txt[:46] + tag)))
    M = 560
    canvas = Image.new("RGB", (W + 2 * M, H), "white"); canvas.paste(img, (M, 0))
    d = ImageDraw.Draw(canvas)
    try:
        f = ImageFont.truetype("DejaVuSans.ttf", 22); fb = ImageFont.truetype("DejaVuSans-Bold.ttf", 26)
    except OSError:
        f = fb = ImageFont.load_default()
    for side in ("L", "R"):
        grp = sorted([p for p in pts if (p[0] < W / 2) == (side == "L")], key=lambda p: p[1])
        y_last = -99
        for x, y, t in grp:
            ly = max(y, y_last + 34); y_last = ly
            lx = 16 if side == "L" else W + M + 16
            ex = M - 12 if side == "L" else W + M + 8
            d.line([(x + M, y), (ex, ly)], fill=(200, 40, 40), width=2)
            d.ellipse([x + M - 5, y - 5, x + M + 5, y + 5], fill=(200, 40, 40))
            d.text((lx, ly - 13), t, fill=(20, 20, 20), font=f)
    d.text((16, H - 70), f"{spec.get('project', '')}", fill=(20, 20, 20), font=fb)
    d.text((16, H - 36), "[P] provisional (measured/not called out)  [A] assumed  — cutaway: layers stepped back at the far end only",
           fill=(90, 90, 90), font=f)
    canvas.save(png_path)
