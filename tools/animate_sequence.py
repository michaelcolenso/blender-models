"""Construction-sequence animation for an existing/proposed detail pair.

  python tools/animate_sequence.py specs/<x>-existing.yaml specs/<x>-proposed.yaml --out build/<x>-sequence
      [--fps 12] [--res 960x540] [--samples 12] [--no-video]

Reads `sequence:` from the proposed spec. Each step: {caption, remove: [ids], install: [ids], seconds}
Special step `weave: {shingles: <id>, flashing: [<id>, ...]}` splits the shingle band into courses at the
flashing repeat spacing and installs shingle course k then flashing piece k, course by course.
Components are built full-length (no cutaway peel). Outputs:
  <out>.mp4   captioned video (Cycles CPU frames + ffmpeg), plays on any phone
  <out>.usdz  same timeline as transform animation (install = drop in + scale up; remove = lift out + scale down)
"""
import argparse, math, subprocess, sys, json
from pathlib import Path

import bpy
import yaml
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).parent))
import detail  # noqa: E402
import build as B  # noqa: E402  (material palette + material())

IN = 0.0254


def mk(c, name=None, y0=0.0, y1=None, L=0, slope=0, coll=None, mat_override=None):
    prof = detail._profile(c)
    o = detail.sweep(name or c["id"], prof, y0, L if y1 is None else y1, slope, coll)
    detail._set_mat(o, B.material(mat_override or c.get("material", "default")))
    # origin to geometry centre so scale animations collapse in place
    pts = [v.co.copy() for v in o.data.vertices]
    ctr = sum(pts, Vector()) / len(pts)
    for v in o.data.vertices:
        v.co -= ctr
    o.location = ctr
    return o


def key(o, f, loc=None, scale=None):
    if loc is not None:
        o.location = loc
    if scale is not None:
        o.scale = (scale, scale, scale)
    o.keyframe_insert("location", frame=f); o.keyframe_insert("scale", frame=f)


def scope_mat(label):
    return ("scope_new" if label.startswith("NEW") else "scope_req" if label.startswith("REQ'D") else
            "scope_rec" if label.startswith("REC") else None)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("existing"); ap.add_argument("proposed"); ap.add_argument("--out", required=True)
    ap.add_argument("--fps", type=int, default=12); ap.add_argument("--res", default="960x540")
    ap.add_argument("--samples", type=int, default=12); ap.add_argument("--no-video", action="store_true")
    ap.add_argument("--test-frames", help="comma list: render only these frames, no mp4")
    a = ap.parse_args()
    E = yaml.safe_load(open(a.existing)); P = yaml.safe_load(open(a.proposed))
    ee, pe = E["elements"][0], P["elements"][0]
    L = ee["path"]["length_in"]; slope = ee["path"].get("pitch", 0) / 12.0
    seq = P["sequence"]
    out = Path(a.out); out.parent.mkdir(parents=True, exist_ok=True)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    coll = bpy.data.collections.new("sequence"); sc.collection.children.link(coll)
    comps = {}
    for c in ee["components"]:
        comps[("E", c["id"])] = c
    for c in pe["components"]:
        comps[("P", c["id"])] = c

    objs = {}          # key -> list of objects
    # existing assembly (everything in the existing spec)
    for c in ee["components"]:
        objs[("E", c["id"])] = [mk(c, "E_" + c["id"], L=L, slope=slope, coll=coll)]
    # proposed-only components (hidden until installed); repeats built per piece
    ekeys = {(c["id"], tuple(c["rect"])) for c in ee["components"]}
    for c in pe["components"]:
        if (c["id"], tuple(c["rect"])) in ekeys:
            continue
        m = scope_mat(c.get("label", ""))
        if m == "scope_new" and c.get("material") in ("wrb", "membrane"):
            m = "scope_new_light"
        if c.get("repeat"):
            w, sp = c["repeat"]["width_in"], c["repeat"]["spacing_in"]; t = c["repeat"].get("start_in", 0); lst = []
            while t + w <= L + 1e-6:
                lst.append(mk(c, f"P_{c['id']}.{len(lst) + 1:02d}", t, t + w, L, slope, coll, m)); t += sp
            objs[("P", c["id"])] = lst
        else:
            objs[("P", c["id"])] = [mk(c, "P_" + c["id"], L=L, slope=slope, coll=coll, mat_override=m)]

    for c in (seq.get("extras", []) if isinstance(seq, dict) else []):  # e.g. an existing band that comes off
        comps[("E", c["id"])] = c
        objs[("E", c["id"])] = [mk(c, "E_" + c["id"], L=L, slope=slope, coll=coll)]
    fps = a.fps; sc.render.fps = fps
    finals = {o.name: (o.location.copy(), 1.0) for lst in objs.values() for o in lst}
    hidden = set()
    show0 = set(seq.get("initial_show", [])) if isinstance(seq, dict) else set()
    hide0 = set(seq.get("initial_hide", [])) if isinstance(seq, dict) else set()
    for (side, cid), lst in objs.items():
        if (side == "P" and cid in show0) or (side == "E" and cid not in hide0 and side != "P"):
            for o in lst:
                key(o, 1, finals[o.name][0], 1.0)
            continue
        if side == "E" and cid in hide0:
            for o in lst:
                key(o, 1, finals[o.name][0], 0.0001)
            continue
        if side == "P":
            for o in lst:
                key(o, 1, o.location + Vector((0, 0, 12 * IN)), 0.0001); hidden.add(o.name)
        else:
            for o in lst:
                key(o, 1, finals[o.name][0], 1.0)

    def resolve(cid):
        k = ("P", cid) if ("P", cid) in objs else ("E", cid)
        return objs[k], k

    f = 1 + int(fps * 1.5)  # opening hold
    timeline = [(1, f, seq.get("title", "Existing condition") if isinstance(seq, dict) else "Existing condition")]
    steps = seq["steps"] if isinstance(seq, dict) else seq
    for st in steps:
        dur = max(1, int(round(st.get("seconds", 1.5) * fps)))
        f0, f1 = f, f + dur
        for cid in st.get("remove", []):
            lst, _ = resolve(cid)
            for o in lst:
                key(o, f0, finals[o.name][0], 1.0)
                key(o, f1, finals[o.name][0] + Vector((10 * IN, 0, 14 * IN)), 0.0001)
        for cid in st.get("install", []):
            lst, _ = resolve(cid)
            n = len(lst)
            for i, o in enumerate(lst):  # stagger repeated pieces across the step
                s0 = f0 + int(i * dur * 0.6 / max(n, 1)); s1 = min(f1, s0 + max(3, int(dur * 0.5)))
                key(o, s0, finals[o.name][0] + Vector((0, 0, 12 * IN)), 0.0001)
                key(o, s1, finals[o.name][0], 1.0)
        if "weave" in st:
            wv = st["weave"]
            band = comps[("P", wv["shingles"])]
            fl_lists = [objs[("P", fid)] for fid in wv["flashing"]]
            rep = comps[("P", wv["flashing"][0])]["repeat"]
            sp = rep["spacing_in"]; ncourses = len(fl_lists[0])
            m = scope_mat(band.get("label", ""))
            band_objs = objs[("P", wv["shingles"])]
            for o in band_objs:  # replace the single band with per-course strips
                key(o, 1, o.location, 0.0001); key(o, f1 + 1, o.location, 0.0001)
            per = dur / max(ncourses, 1)
            for k in range(ncourses):
                y0 = k * sp; y1 = min(L, (k + 1) * sp)
                strip = mk(band, f"P_{wv['shingles']}_course{k + 1:02d}", y0, y1, L, slope, coll, m)
                finals[strip.name] = (strip.location.copy(), 1.0)
                c0 = f0 + int(k * per)
                key(strip, 1, strip.location + Vector((0, 0, 12 * IN)), 0.0001)
                key(strip, c0, strip.location + Vector((0, 0, 12 * IN)), 0.0001)
                key(strip, c0 + max(2, int(per * 0.45)), finals[strip.name][0], 1.0)
                for lst in fl_lists:
                    o = lst[k]
                    fa = c0 + max(2, int(per * 0.45)); fb = fa + max(2, int(per * 0.45))
                    key(o, fa, finals[o.name][0] + Vector((0, 0, 12 * IN)), 0.0001)
                    key(o, fb, finals[o.name][0], 1.0)
        timeline.append((f0, f1, st["caption"]))
        f = f1 + int(fps * st.get("hold", 0.4))
    end = f + int(fps * 2.0)
    timeline.append((f, end, seq.get("closing", "Complete") if isinstance(seq, dict) else "Complete"))
    sc.frame_start, sc.frame_end = 1, end

    # hold every object's last key to the end (so nothing drifts)
    for lst in objs.values():
        for o in lst:
            pass

    # --- re-seat for AR: lowest point at Z=0, centred in X/Y (parent everything to one offset empty) ---
    bpy.context.view_layer.update()
    pts0 = [o.matrix_world @ v.co for o in coll.objects for v in o.data.vertices]
    lo0 = Vector([min(p[i] for p in pts0) for i in range(3)]); hi0 = Vector([max(p[i] for p in pts0) for i in range(3)])
    root = bpy.data.objects.new("seat", None); coll.objects.link(root)
    root.location = (-(lo0.x + hi0.x) / 2, -(lo0.y + hi0.y) / 2, -lo0.z)
    for o in list(coll.objects):
        if o is not root and o.parent is None:
            o.parent = root
    bpy.context.view_layer.update()

    # --- camera: from the roof side toward the far end, slow orbit ---
    pts = [o.matrix_world @ v.co for o in coll.objects if o.type == "MESH" for v in o.data.vertices]
    lo = Vector([min(p[i] for p in pts) for i in range(3)]); hi = Vector([max(p[i] for p in pts) for i in range(3)])
    ctr = (lo + hi) / 2; span = (hi - lo).length
    cd = bpy.data.cameras.new("cam"); cd.lens = 32
    cam = bpy.data.objects.new("cam", cd); sc.collection.objects.link(cam); sc.camera = cam
    base = Vector(pe.get("cutaway_dir", (1.0, 0.7, 0.9))).normalized()
    target = Vector((ctr.x, ctr.y, ctr.z + span * 0.02))
    for fk in range(1, end + 1, max(1, fps // 2)):
        ang = math.radians(-8 + 16 * (fk - 1) / max(end - 1, 1))
        d = Vector((base.x * math.cos(ang) - base.y * math.sin(ang), base.x * math.sin(ang) + base.y * math.cos(ang), base.z))
        cam.location = target + d * span * 1.2
        cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
        cam.keyframe_insert("location", frame=fk); cam.keyframe_insert("rotation_euler", frame=fk)

    # --- light / world ---
    w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True
    bg = w.node_tree.nodes["Background"]; bg.inputs[0].default_value = (0.93, 0.93, 0.92, 1); bg.inputs[1].default_value = 0.8
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN")); sun.data.energy = 3.0
    sun.rotation_euler = (math.radians(45), 0, math.radians(-35)); sc.collection.objects.link(sun)
    sc.render.engine = "CYCLES"; sc.cycles.device = "CPU"; sc.cycles.samples = a.samples; sc.cycles.use_denoising = True
    sc.view_settings.view_transform = "Standard"
    rx, ry = [int(v) for v in a.res.split("x")]; sc.render.resolution_x, sc.render.resolution_y = rx, ry

    # --- USDZ (transform animation) ---
    bpy.ops.wm.usd_export(filepath=str(out.with_suffix(".usdz").resolve()), export_animation=True,
                          export_materials=True, generate_preview_surface=True, export_cameras=False,
                          export_lights=False, convert_orientation=True, export_global_forward_selection="NEGATIVE_Z",
                          export_global_up_selection="Y", meters_per_unit=1.0, selected_objects_only=False)
    json.dump({"fps": fps, "frames": end, "timeline": timeline}, open(out.with_suffix(".timeline.json"), "w"), indent=1)
    print(f"USDZ {out.with_suffix('.usdz')} frames={end} fps={fps} seconds={end / fps:.1f}")
    if a.no_video:
        return

    # --- frames + captions + mp4 ---
    from PIL import Image, ImageDraw, ImageFont
    fdir = out.parent / (out.name + "_frames"); fdir.mkdir(exist_ok=True)
    try:
        fb = ImageFont.truetype("DejaVuSans-Bold.ttf", max(18, ry // 22)); fs = ImageFont.truetype("DejaVuSans.ttf", max(14, ry // 34))
    except OSError:
        fb = fs = ImageFont.load_default()
    title = P.get("project", "")
    frames = range(1, end + 1) if not a.test_frames else [int(x) for x in a.test_frames.split(",")]
    for fr in frames:
        sc.frame_set(fr)
        p = fdir / f"f{fr:05d}.png"; sc.render.filepath = str(p)
        bpy.ops.render.render(write_still=True)
        cap = next((t for (a0, a1, t) in reversed(timeline) if fr >= a0), timeline[0][2])
        idx = next((i for i, (a0, a1, t) in enumerate(timeline) if a0 <= fr <= a1 + fps), 0)
        im = Image.open(p).convert("RGB"); d = ImageDraw.Draw(im)
        d.rectangle([0, ry - ry // 6, rx, ry], fill=(255, 255, 255))
        d.text((16, ry - ry // 6 + 8), cap, fill=(20, 20, 20), font=fb)
        d.text((16, ry - ry // 14), f"{title}   ·   step {idx}/{len(timeline) - 1}   ·   model — not to scale where marked [A]",
               fill=(110, 110, 110), font=fs)
        im.save(p)
    if a.test_frames:
        return
    mp4 = out.with_suffix(".mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(fps), "-i", str(fdir / "f%05d.png"),
                    "-vf", "fps=24,format=yuv420p", "-c:v", "libx264", "-crf", "22", "-movflags", "+faststart", str(mp4)], check=True)
    print(f"MP4 {mp4} frames={end} seconds={end / fps:.1f}")


if __name__ == "__main__":
    main()
