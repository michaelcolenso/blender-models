"""Export a built model to USDZ for iPhone/iPad Quick Look + AR (no app needed).

  python tools/export_usdz.py build/<name>/<name>.blend [--out build/<name>/<name>.usdz]

- Meshes only (no cameras/lights/ground); real-world scale (1 unit = 1 m, meters_per_unit = 1).
- Model re-seated so its lowest point is at Z = 0 and it is centred in X/Y — AR places it on the floor.
- Y-up conversion (Quick Look expects Y-up).
- Materials exported as UsdPreviewSurface base colors; procedural bump patterns do not carry over.
"""
import argparse, sys
from pathlib import Path
import bpy
from mathutils import Vector


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    ap = argparse.ArgumentParser(); ap.add_argument("blend"); ap.add_argument("--out")
    a = ap.parse_args(argv)
    out = Path(a.out or Path(a.blend).with_suffix(".usdz"))
    bpy.ops.wm.open_mainfile(filepath=str(Path(a.blend).resolve()))
    for o in list(bpy.data.objects):
        if o.type != "MESH" or o.name == "ground":
            bpy.data.objects.remove(o)
    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    bpy.context.view_layer.update()
    pts = [o.matrix_world @ v.co for o in meshes for v in o.data.vertices]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    shift = Vector((-(lo.x + hi.x) / 2, -(lo.y + hi.y) / 2, -lo.z))
    for o in meshes:
        if o.parent is None:
            o.location += shift
    bpy.context.view_layer.update()
    bpy.ops.wm.usd_export(filepath=str(out.resolve()), export_materials=True, generate_preview_surface=True,
                          export_cameras=False, export_lights=False, convert_orientation=True,
                          export_global_forward_selection="NEGATIVE_Z", export_global_up_selection="Y",
                          meters_per_unit=1.0, triangulate_meshes=True, export_custom_properties=True)
    size = hi - lo
    print(f"USDZ {out} size_m=({size.x:.2f}, {size.y:.2f}, {size.z:.2f}) objects={len(meshes)} bytes={out.stat().st_size}")


if __name__ == "__main__":
    main()
