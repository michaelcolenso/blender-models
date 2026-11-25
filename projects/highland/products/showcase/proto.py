"""Proof renders for the two riskiest showcase movements, headless, Blender 5.3 (env/).

  uv run --project projects/highland/products/showcase/env --frozen python projects/highland/products/showcase/proto.py [out_dir]

1 Ink:   Grease Pencil v3 strokes trace the plan outlines and draw on (Build modifier).
6 Truth: one camera, four looks: shaded, Freestyle line drawing, clay, provenance colours.
The building is generalized: captions (address, sheet names) are removed.
"""
import math
import sys
import time
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[4]
SOURCE = ROOT/'projects/highland/deliverables/exterior/Highland-exterior.blend'
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT/'build/highland/showcase/proof'
OUT.mkdir(parents=True, exist_ok=True)
STATUS = {'confirmed': (.12, .72, .28), 'provisional': (.95, .64, .05), 'assumed': (1, .24, .035)}


def generalize(scene):
    """No address, sheet names or captions on screen."""
    for o in list(scene.objects):
        if o.type == 'FONT' or o.name.startswith('caption'):
            bpy.data.objects.remove(o, do_unlink=True)


def bounds(scene):
    pts = [o.matrix_world@Vector(c) for o in scene.objects if o.type == 'MESH' for c in o.bound_box]
    lo = Vector(tuple(min(p[i] for p in pts) for i in range(3))); hi = Vector(tuple(max(p[i] for p in pts) for i in range(3)))
    return lo, hi


def building_bounds(scene):
    keep = [o for o in scene.objects if o.type == 'MESH' and o.users_collection[0].name in ('Envelope', 'Roof', 'Glazing', 'Balconies')]
    pts = [o.matrix_world@Vector(c) for o in keep for c in o.bound_box]
    lo = Vector(tuple(min(p[i] for p in pts) for i in range(3))); hi = Vector(tuple(max(p[i] for p in pts) for i in range(3)))
    return lo, hi


def camera(scene, pos, look, lens=28, shift_y=.1):
    cam = bpy.data.objects.new('Proof camera', bpy.data.cameras.new('Proof lens'))
    scene.collection.objects.link(cam)
    cam.data.lens = lens; cam.data.shift_y = shift_y; cam.data.clip_end = 2000
    d = look-pos
    cam.location = pos; cam.rotation_euler = (math.pi/2, 0, math.atan2(d.y, d.x)-math.pi/2)
    scene.camera = cam
    for other in [o for o in scene.objects if o.type == 'CAMERA' and o != cam]:
        bpy.data.objects.remove(other, do_unlink=True)
    bpy.context.view_layer.update()
    return cam


def render(scene, name, w=960, h=540, samples=16):
    scene.render.engine = 'CYCLES'; scene.cycles.device = 'CPU'; scene.cycles.samples = samples
    scene.cycles.use_denoising = True
    scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage = w, h, 100
    scene.render.filepath = str(OUT/f'{name}.png')
    t = time.time(); bpy.ops.render.render(write_still=True)
    print(f'PROOF {name} {time.time()-t:.1f}s', flush=True)


def flat(name, color, emit=0.):
    m = bpy.data.materials.new(name)
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*color, 1); b.inputs['Roughness'].default_value = .8
    if emit:
        b.inputs['Emission Color'].default_value = (*color, 1); b.inputs['Emission Strength'].default_value = emit
    return m


def ink(scene):
    """Plan outlines as Grease Pencil v3 strokes, drawn on by the Build modifier."""
    lo, hi = building_bounds(scene)
    gp = bpy.data.grease_pencils.new('Ink')
    obj = bpy.data.objects.new('Ink', gp); scene.collection.objects.link(obj)
    mat = bpy.data.materials.new('Ink line'); bpy.data.materials.create_gpencil_data(mat)
    mat.grease_pencil.color = (1, 1, 1, 1); gp.materials.append(mat)
    layer = gp.layers.new('Plan'); frame = layer.frames.new(1); drawing = frame.drawing
    # Every slab outline on every level, from the model itself.
    loops = []
    for o in scene.objects:
        if o.type == 'MESH' and o.name.startswith('slab-'):
            me = o.data; top = max(v.co.z for v in me.vertices)
            ring = [o.matrix_world@v.co for v in me.vertices if abs(v.co.z-top) < 1e-4]
            if len(ring) >= 3:
                loops.append(ring+[ring[0]])
    drawing.add_strokes([len(r) for r in loops])
    for stroke, ring in zip(drawing.strokes, loops):
        for p, co in zip(stroke.points, ring):
            p.position = co; p.radius = .05
        stroke.material_index = 0
    build = obj.modifiers.new('Draw on', 'GREASE_PENCIL_BUILD')
    build.mode = 'SEQUENTIAL'; build.frame_start = 1; build.length = 48
    print('INK strokes', len(loops), 'bounds', tuple(round(x, 1) for x in lo), tuple(round(x, 1) for x in hi), flush=True)
    return obj, lo, hi


def main():
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
    scene = bpy.context.scene
    generalize(scene)
    lo, hi = building_bounds(scene); c = (lo+hi)/2; size = (hi-lo).length
    print('BUILDING', tuple(round(x, 1) for x in lo), tuple(round(x, 1) for x in hi), flush=True)

    # --- 6 Truth: four looks through one camera --------------------------------------------
    camera(scene, Vector((hi.x+size*.55, lo.y-size*.45, lo.z+size*.18)), Vector((c.x, c.y, lo.z+size*.18)), lens=28, shift_y=.12)
    render(scene, '6a-shaded')
    originals = {o: [s.material for s in o.material_slots] for o in scene.objects if o.type == 'MESH'}
    clay = flat('Clay', (.62, .6, .57))
    for o in originals:
        for s in o.material_slots:
            s.material = clay
    render(scene, '6c-clay')
    scene.render.use_freestyle = True
    ls = scene.view_layers[0].freestyle_settings.linesets[0]
    ls.linestyle.color = (.05, .05, .06); ls.linestyle.thickness = 1.4
    paper = flat('Paper', (.92, .9, .86))
    for o in originals:
        for s in o.material_slots:
            s.material = paper
    render(scene, '6b-line')
    scene.render.use_freestyle = False
    mats = {k: flat('Status '+k, v) for k, v in STATUS.items()}
    for o in originals:
        st = 'provisional' if o.get('xy_status') == 'provisional' else 'confirmed' if o.get('datum_status') == 'confirmed' else o.get('status', 'assumed')
        for s in o.material_slots:
            s.material = mats.get(st, mats['assumed'])
    render(scene, '6d-provenance')

    # --- 1 Ink: Grease Pencil draw-on, rendered through Cycles ---------------------------------
    for o in originals:
        o.hide_render = True
    scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0
    ink(scene)
    cam2 = camera(scene, Vector((c.x+size*.35, lo.y-size*.55, lo.z+size*.75)), c, lens=35, shift_y=0)
    d = c-cam2.location; cam2.rotation_euler = (math.pi/2+math.atan2(d.z, math.hypot(d.x, d.y)), 0, math.atan2(d.y, d.x)-math.pi/2)
    for f in (20, 60):
        scene.frame_set(f); render(scene, f'1-ink-f{f:03d}')


main()
