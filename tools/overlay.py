"""Overlay an orthographic model render on a drawing elevation at the same scale.

Usage:
  python tools/overlay.py build/<name>/<name>.blend --pdf sources/X.pdf --page 6 \
      --clip x0,y0,x1,y1 --pt-per-ft 9 --view front --out build/<name>/overlay_front.png

Rasterizes the elevation at 1 px/in, renders the model's silhouette edges from the same
side at 1 px/in, aligns by (a) the floor line (longest dash-dot row = FF 100'-0") given
via --floor-row or auto, and (b) horizontal centre found by mirror-symmetry search, then
reports edge agreement (share of model edge pixels within 2 in of drawing ink).
Drawing = grey, model edges = red. Output PNG is for human review; the number is evidence,
not proof.
"""
import argparse, math, sys
import numpy as np, cv2, pymupdf as fitz
import bpy
from mathutils import Vector

IN = 0.0254


def elevation(pdf, page, clip, pt_per_ft):
    dpi = int(round(72 / (pt_per_ft / 12)))  # 1 px per inch
    pix = fitz.open(pdf)[page - 1].get_pixmap(clip=fitz.Rect(*clip), dpi=dpi, colorspace=fitz.csGRAY)
    return np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.width) < 128


def render_view(blend, view, width_in, height_in, z_floor_px):
    bpy.ops.wm.open_mainfile(filepath=blend)
    sc = bpy.context.scene
    for o in list(sc.objects):
        if o.type in ("CAMERA", "LIGHT"):
            bpy.data.objects.remove(o)
    sc.render.engine = "CYCLES"; sc.cycles.samples = 4; sc.cycles.device = "CPU"
    sc.view_settings.view_transform = "Standard"
    sc.render.resolution_x, sc.render.resolution_y = int(width_in), int(height_in)
    sc.render.film_transparent = True
    cd = bpy.data.cameras.new("ov"); cd.type = "ORTHO"; cd.ortho_scale = width_in * IN
    cam = bpy.data.objects.new("ov", cd); sc.collection.objects.link(cam); sc.camera = cam
    # image row z_floor_px corresponds to z=0 ; camera centred vertically on image
    zc = (z_floor_px - height_in / 2) * IN  # z at image centre
    if view == "front":
        cam.location = (0, -60, zc); cam.rotation_euler = (math.radians(90), 0, 0)
    elif view == "rear":
        cam.location = (0, 60, zc); cam.rotation_euler = (math.radians(90), 0, math.radians(180))
    elif view == "right":
        cam.location = (60, 0, zc); cam.rotation_euler = (math.radians(90), 0, math.radians(90))
    sc.render.filepath = "/tmp/_ov.png"
    bpy.ops.render.render(write_still=True)
    img = cv2.imread("/tmp/_ov.png", cv2.IMREAD_UNCHANGED)
    rgb = cv2.cvtColor(img[:, :, :3], cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(rgb, 20, 60) > 0
    sil = img[:, :, 3] > 0
    edges |= (cv2.morphologyEx(sil.astype(np.uint8), cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8)) > 0)
    return edges


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("blend"); ap.add_argument("--pdf", required=True); ap.add_argument("--page", type=int, required=True)
    ap.add_argument("--clip", required=True); ap.add_argument("--pt-per-ft", type=float, required=True)
    ap.add_argument("--view", default="front"); ap.add_argument("--floor-row", type=int)
    ap.add_argument("--center-col", type=int); ap.add_argument("--out", required=True)
    a = ap.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else None)
    ink = elevation(a.pdf, a.page, [float(v) for v in a.clip.split(",")], a.pt_per_ft)
    H, W = ink.shape
    fr = a.floor_row if a.floor_row is not None else int(np.argmax(ink.sum(1)))
    cc = a.center_col if a.center_col is not None else W // 2
    # render with building centre at image centre column, then shift
    edges = render_view(a.blend, a.view, W, H, fr)
    edges = np.roll(edges, cc - W // 2, axis=1)
    near = cv2.dilate(ink.astype(np.uint8), np.ones((5, 5), np.uint8)) > 0  # within 2 in
    agree = (edges & near).sum() / max(edges.sum(), 1)
    out = np.full((H, W, 3), 255, np.uint8)
    out[ink] = (170, 170, 170); out[edges] = (0, 0, 255)
    cv2.putText(out, f"model edges within 2in of drawing: {agree:.1%}", (10, 30), 0, 0.8, (0, 0, 200), 2)
    cv2.imwrite(a.out, out)
    print(f"OVERLAY {a.view}: floor_row={fr} center_col={cc} agreement={agree:.3f} -> {a.out}")


if __name__ == "__main__":
    main()
