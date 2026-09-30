"""Build-up animation for a house model (type: house) from the spec's `sequence:` block.

  python tools/animate_house.py specs/<name>.yaml [--blend build/<name>/<name>.blend] --out build/<name>-sequence/<name>-sequence
      [--fps 12] [--res 960x540] [--samples 8] [--no-video] [--test-frames 1,60,200]

Needs the built .blend (run tools/build.py first). Steps: {caption, objects: [glob..], motion, seconds, stagger}
  motion drop  = lowered in from 3 m above (roof, slab)
  motion rise  = grows up from its own base (walls, gable ends)
  motion grow  = scales up in place; stagger: opening -> one opening (all parts) after another
Camera orbits the building once, elevated 3/4 view starting front-left. Outputs <out>.mp4, <out>.usdz
(transform animation, re-seated so grade = Z 0, centred), <out>.timeline.json.
"""
import argparse, fnmatch, json, math, re, sys
from pathlib import Path

import bpy
import yaml
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).parent))
import anim_common as AC  # noqa: E402


def bake_pivot(o, pivot):
    """Apply the object's transform to its mesh, then put the origin at world point `pivot`."""
    mw = o.matrix_world.copy()
    o.data.transform(mw)
    o.matrix_world = Matrix.Identity(4)
    o.data.transform(Matrix.Translation(-pivot))
    o.location = pivot


def key(o, f, loc, scale):
    o.location = loc; o.scale = scale
    o.keyframe_insert("location", frame=f); o.keyframe_insert("scale", frame=f)


def opening_id(name):
    return re.sub(r"_(glass|panel|fh|fs|ct|cl|cr|cs|m\d+|seam\d+)$", "", name)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spec"); ap.add_argument("--blend"); ap.add_argument("--out", required=True)
    ap.add_argument("--fps", type=int, default=12); ap.add_argument("--res", default="960x540")
    ap.add_argument("--samples", type=int, default=8); ap.add_argument("--no-video", action="store_true")
    ap.add_argument("--test-frames")
    a = ap.parse_args()
    spec = yaml.safe_load(open(a.spec)); seq = spec["sequence"]
    name = Path(a.spec).stem
    blend = Path(a.blend or f"build/{name}/{name}.blend")
    out = Path(a.out); out.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(blend.resolve()))
    sc = bpy.context.scene
    for o in list(bpy.data.objects):
        if o.type != "MESH" or o.name == "ground":
            bpy.data.objects.remove(o)
    meshes = {o.name: o for o in bpy.data.objects}
    bpy.context.view_layer.update()

    fps = a.fps; sc.render.fps = fps
    finals, assigned = {}, set()
    f = 1 + int(fps * 1.5)
    timeline = [(1, f, seq.get("title", spec.get("project", name)))]
    plans = []
    for st in seq["steps"]:
        objs = [n for n in meshes if n not in assigned and any(fnmatch.fnmatch(n, p) for p in st["objects"])]
        if not objs:
            sys.exit(f"sequence step matched no objects: {st['caption']}")
        assigned.update(objs); plans.append((st, objs))
    left = sorted(set(meshes) - assigned)
    if left:
        print(f"WARNING: not in any step (shown from start): {left}")

    for st, objs in plans:
        for n in objs:
            o = meshes[n]
            ws = [o.matrix_world @ v.co for v in o.data.vertices]
            lo = Vector([min(p[i] for p in ws) for i in range(3)]); hi = Vector([max(p[i] for p in ws) for i in range(3)])
            piv = Vector(((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, lo.z if st["motion"] == "rise" else (lo.z + hi.z) / 2))
            bake_pivot(o, piv); finals[n] = piv.copy()
        dur = max(1, int(round(st.get("seconds", 1.5) * fps)))
        f0, f1 = f, f + dur
        groups = {}
        for n in objs:
            groups.setdefault(opening_id(n) if st.get("stagger") == "opening" else "_all", []).append(n)
        gl = sorted(groups)
        for gi, g in enumerate(gl):
            s0 = f0 + int(gi * dur * 0.7 / max(len(gl), 1)); s1 = min(f1, s0 + max(4, int(dur * (0.3 if len(gl) > 1 else 1.0))))
            for n in groups[g]:
                o = meshes[n]; p = finals[n]
                m = st["motion"]
                if m == "drop":  # hidden (tiny) until its step, appears 3 m up, lowers into place
                    up = p + Vector((0, 0, 3.0))
                    key(o, 1, up, (0.0001,) * 3); key(o, s0 - 1, up, (0.0001,) * 3); key(o, s0, up, (1, 1, 1))
                elif m == "rise":
                    key(o, 1, p, (0.0001,) * 3); key(o, s0 - 1, p, (0.0001,) * 3); key(o, s0, p, (1, 1, 0.0001))  # hidden, then flat at base
                else:
                    key(o, 1, p, (0.0001,) * 3); key(o, s0, p, (0.0001,) * 3)
                key(o, s1, p, (1, 1, 1))
        timeline.append((f0, f1, st["caption"]))
        f = f1 + int(fps * st.get("hold", 0.4))
    end = f + int(fps * 5.0)
    timeline.append((f, end, seq.get("closing", "Complete")))
    sc.frame_start, sc.frame_end = 1, end

    # re-seat: grade (lowest point) at Z=0, centred — for AR placement
    bpy.context.view_layer.update()
    sc.frame_set(end); bpy.context.view_layer.update()
    pts = [o.matrix_world @ v.co for o in meshes.values() for v in o.data.vertices]
    lo = Vector([min(p[i] for p in pts) for i in range(3)]); hi = Vector([max(p[i] for p in pts) for i in range(3)])
    root = bpy.data.objects.new("seat", None); sc.collection.objects.link(root)
    root.location = (-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2, -lo.z)
    for o in meshes.values():
        o.parent = root
    size = hi - lo

    # USDZ first (meshes only; ground/camera/light added after)
    usdz = out.with_suffix(".usdz")
    bpy.ops.wm.usd_export(filepath=str(usdz.resolve()), export_animation=True, export_materials=True,
                          generate_preview_surface=True, export_cameras=False, export_lights=False,
                          convert_orientation=True, export_global_forward_selection="NEGATIVE_Z",
                          export_global_up_selection="Y", meters_per_unit=1.0, selected_objects_only=False)
    json.dump({"fps": fps, "frames": end, "size_m": [round(v, 2) for v in size], "timeline": timeline},
              open(out.with_suffix(".timeline.json"), "w"), indent=1)
    print(f"USDZ {usdz} frames={end} fps={fps} seconds={end / fps:.1f} size_m={tuple(round(v, 2) for v in size)}")
    if a.no_video:
        return

    # ground, sky, sun, orbiting camera
    g = bpy.data.meshes.new("ground"); gv = 80.0
    g.from_pydata([(-gv, -gv, -0.005), (gv, -gv, -0.005), (gv, gv, -0.005), (-gv, gv, -0.005)], [], [(0, 1, 2, 3)])
    go = bpy.data.objects.new("ground", g); sc.collection.objects.link(go)
    grass = bpy.data.materials.get("mat_grass")
    if grass is None:
        grass = bpy.data.materials.new("mat_grass"); grass.use_nodes = True
        grass.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.25, 0.36, 0.18, 1)
    g.materials.append(grass)
    w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True
    bg = w.node_tree.nodes["Background"]; bg.inputs[0].default_value = (0.62, 0.74, 0.90, 1); bg.inputs[1].default_value = 0.6
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN")); sun.data.energy = 3.0
    sun.rotation_euler = (math.radians(50), 0, math.radians(-35)); sc.collection.objects.link(sun)
    sc.render.engine = "CYCLES"; sc.cycles.device = "CPU"; sc.cycles.samples = a.samples; sc.cycles.use_denoising = True
    sc.view_settings.view_transform = "AgX"; sc.view_settings.look = "AgX - Base Contrast"
    rx, ry = [int(v) for v in a.res.split("x")]; sc.render.resolution_x, sc.render.resolution_y = rx, ry
    cd = bpy.data.cameras.new("cam"); cd.lens = 28; cd.shift_y = -0.08  # lift the building clear of the caption band
    cam = bpy.data.objects.new("cam", cd); sc.collection.objects.link(cam); sc.camera = cam
    span = size.length
    target = Vector((0, 0, size.z * 0.30))
    a0 = math.atan2(-0.75, -0.55)            # start front-left (front faces -Y)
    for fk in list(range(1, end + 1, max(1, fps // 2))) + [end]:
        ang = a0 + 2 * math.pi * (fk - 1) / max(end - 1, 1)
        cam.location = target + Vector((math.cos(ang) * span * 1.05, math.sin(ang) * span * 1.05, span * 0.45))
        cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
        cam.keyframe_insert("location", frame=fk); cam.keyframe_insert("rotation_euler", frame=fk)

    fdir = out.parent / (out.name + "_frames"); fdir.mkdir(exist_ok=True)
    frames = range(1, end + 1) if not a.test_frames else [int(x) for x in a.test_frames.split(",")]
    for fr in frames:
        sc.frame_set(fr)
        p = fdir / f"f{fr:05d}.png"; sc.render.filepath = str(p)
        bpy.ops.render.render(write_still=True)
        AC.caption(p, fr, timeline, spec.get("project", name), "presentation sequence — see report.md for provenance")
        print(f"frame {fr}/{end}", flush=True)
    if a.test_frames:
        return
    AC.encode(fdir, fps, out.with_suffix(".mp4"))
    print(f"MP4 {out.with_suffix('.mp4')} frames={end} seconds={end / fps:.1f}")


if __name__ == "__main__":
    main()
