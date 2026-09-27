"""Overlay a detail model's section cut on the source detail drawing.

Renders a thin slab (first 0.3 in of the sweep) orthographically, looking along the sweep,
at exactly the drawing raster's px/in, aligned on the section origin, and overlays drawing ink.
Reports: share of model edge pixels within 1/8 in of drawing ink.

  python tools/detail_overlay.py build/<name>/<name>.blend --pdf sources/X.pdf --page 8 \
     --clip 1640,360,2030,630 --pt-per-ft 106.5 --origin-pt 1772.5,<z0 y pt> --px-per-in 16 \
     --out build/<name>/overlay_section.png
"""
import argparse, sys
import numpy as np, cv2, pymupdf as fitz
import bpy

IN = 0.0254


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("blend"); ap.add_argument("--pdf", required=True); ap.add_argument("--page", type=int, required=True)
    ap.add_argument("--clip", required=True); ap.add_argument("--pt-per-ft", type=float, required=True)
    ap.add_argument("--origin-pt", required=True, help="x,y page points of section origin (X=0, Z=0)")
    ap.add_argument("--px-per-in", type=float, default=16); ap.add_argument("--out", required=True)
    a = ap.parse_args()
    x0, y0, x1, y1 = [float(v) for v in a.clip.split(",")]
    ox_pt, oz_pt = [float(v) for v in a.origin_pt.split(",")]
    pt_in = a.pt_per_ft / 12
    dpi = a.px_per_in * 72 / pt_in
    pix = fitz.open(a.pdf)[a.page - 1].get_pixmap(clip=fitz.Rect(x0, y0, x1, y1), dpi=int(round(dpi)), colorspace=fitz.csGRAY)
    ppi = int(round(dpi)) * pt_in / 72  # actual px per inch after dpi rounding
    ink = np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.width) < 140
    H, W = ink.shape
    ocol = (ox_pt - x0) * int(round(dpi)) / 72; orow = (oz_pt - y0) * int(round(dpi)) / 72

    bpy.ops.wm.open_mainfile(filepath=a.blend)
    sc = bpy.context.scene
    for o in list(sc.objects):
        if o.type in ("CAMERA", "LIGHT"):
            bpy.data.objects.remove(o)
    sc.render.engine = "CYCLES"; sc.cycles.samples = 8; sc.cycles.device = "CPU"
    sc.view_settings.view_transform = "Standard"; sc.render.film_transparent = True
    sc.render.resolution_x, sc.render.resolution_y = W, H
    w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[1].default_value = 1.5
    cd = bpy.data.cameras.new("sec"); cd.type = "ORTHO"; cd.ortho_scale = (W / ppi) * IN
    d = 1.0
    cd.clip_start = d - 0.0005; cd.clip_end = d + 0.3 * IN
    cam = bpy.data.objects.new("sec", cd); sc.collection.objects.link(cam); sc.camera = cam
    cx_in = (W / 2 - ocol) / ppi; cz_in = (orow - H / 2) / ppi
    import math
    cam.location = (cx_in * IN, -d, cz_in * IN); cam.rotation_euler = (math.radians(90), 0, 0)
    sc.render.filepath = "/tmp/_sec.png"; bpy.ops.render.render(write_still=True)
    img = cv2.imread("/tmp/_sec.png", cv2.IMREAD_UNCHANGED)
    alpha = img[:, :, 3] > 0
    gray = cv2.cvtColor(img[:, :, :3], cv2.COLOR_BGR2GRAY)
    edges = (cv2.Canny(gray, 15, 45) > 0) | (cv2.morphologyEx(alpha.astype(np.uint8), cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8)) > 0)
    tol = max(1, int(round(ppi / 8)))  # 1/8 in
    near = cv2.dilate(ink.astype(np.uint8), np.ones((2 * tol + 1, 2 * tol + 1), np.uint8)) > 0
    agree = (edges & near).sum() / max(edges.sum(), 1)
    out = np.full((H, W, 3), 255, np.uint8)
    out[alpha] = (0.35 * img[:, :, :3][alpha] + 0.65 * 255).astype(np.uint8)
    out[ink] = (60, 60, 60); out[edges] = (0, 0, 255)
    big = cv2.resize(out, None, fx=2, fy=2, interpolation=cv2.INTER_NEAREST)
    cv2.putText(big, f"model section edges within 1/8 in of drawing: {agree:.1%}", (12, 30), 0, 0.8, (0, 0, 200), 2)
    cv2.imwrite(a.out, big)
    print(f"SECTION OVERLAY agreement={agree:.3f} px_per_in={ppi:.2f} -> {a.out}")


if __name__ == "__main__":
    main()
