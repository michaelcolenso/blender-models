"""Cinematic edit of the native Highland walkthrough.

Builds on the validated scene from build_blender.py: the doors, elevator, rise
and section stay native keyframes. This module adds a dusk exterior, refined
interior exposure, a clean x-ray treatment for the section, and one level,
lens-shifted camera per shot from cinema.shots.json. Frames render per shot
and can be resumed. Run with Python 3.11 and bpy==5.0.1.
"""
import argparse
import hashlib
import json
import math
import sys
import time
from pathlib import Path

import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import build_blender as B  # noqa: E402

SPEC_FILE = HERE / 'cinema.shots.json'
SPEC = json.loads(SPEC_FILE.read_text())
I = .0254
BUILD = ROOT / 'build/highland-cinema'
PROFILES = {
    # Scope 2.39:1: width, height, max samples, adaptive noise threshold.
    # cinema_finish.py scales proof/local frames to the master picture size.
    'proof': (640, 268, 8, .02),
    'local': (1280, 536, 20, .02),
    'final': (1920, 804, 128, .01),
    'uhd': (3840, 1608, 96, .01),
}


CAMERA_FIELDS = ('id', 'src_start', 'frames', 'lens', 'shift_y', 'fstop', 'pitch', 'ease', 'keys', 'focus')


def camera_hash():
    """Hash of the shot fields baked into the saved cameras; labels and exposure are finish-only."""
    shots = [{k: s.get(k) for k in CAMERA_FIELDS} for s in SPEC['shots']]
    return hashlib.sha256(json.dumps(shots, sort_keys=True).encode()).hexdigest()


def smooth(a, b, t):
    v = max(0., min(1., (t-a)/(b-a)))
    return v*v*(3-2*v)


def profile(u, a, b):
    """Trapezoidal velocity: accelerate over a, cruise, decelerate over b."""
    u = max(0., min(1., u))
    vmax = 1/(1-(a+b)/2)
    if a and u < a:
        return vmax*u*u/(2*a)
    if b and u > 1-b:
        r = 1-u
        return 1-vmax*r*r/(2*b)
    return vmax*(u-a/2)


def sample(keys, u, field):
    """Catmull-Rom through the shot keys, parameterized by key u values."""
    pts = [(k['u'], Vector(k[field])) for k in keys]
    if u <= pts[0][0]:
        return pts[0][1].copy()
    for j in range(len(pts)-1):
        u0, p1 = pts[j]
        u1, p2 = pts[j+1]
        if u <= u1:
            p0 = pts[j-1][1] if j else p1+(p1-p2)
            p3 = pts[j+2][1] if j+2 < len(pts) else p2+(p2-p1)
            s = (u-u0)/(u1-u0)
            return .5*((2*p1)+(-p0+p2)*s+(2*p0-5*p1+4*p2-p3)*s*s+(-p0+3*p1-3*p2+p3)*s**3)
    return pts[-1][1].copy()


def fcurves(idblock):
    """F-curves of a Blender 5 layered action."""
    ad = idblock.animation_data
    if not ad or not ad.action:
        return []
    return [fc for layer in ad.action.layers for strip in layer.strips
            for fc in (strip.channelbag(ad.action_slot).fcurves if strip.channelbag(ad.action_slot) else [])]


def emission(mat, strength, color=None):
    b = mat.node_tree.nodes.get('Principled BSDF')
    b.inputs['Emission Strength'].default_value = strength
    if color:
        b.inputs['Emission Color'].default_value = (*color, 1)


def dusk(scene):
    """Blue-hour exterior: deep sky, lit apartments, wet street reflections."""
    world = scene.world.node_tree
    n, l = world.nodes, world.links
    env = next(x for x in n if x.type == 'TEX_ENVIRONMENT')
    bg = next(x for x in n if x.type == 'BACKGROUND')
    tint = n.new('ShaderNodeMix'); tint.data_type = 'RGBA'; tint.blend_type = 'MULTIPLY'
    tint.inputs['Factor'].default_value = 1
    tint.inputs['B'].default_value = (.28, .42, .95, 1)
    l.new(env.outputs['Color'], tint.inputs['A']); l.new(tint.outputs['Result'], bg.inputs['Color'])
    bg.inputs['Strength'].default_value = .55
    for o in scene.objects:
        if o.type == 'LIGHT' and o.data.type == 'SUN':
            o.data.energy = .06; o.data.color = (.55, .65, 1)
    emission(bpy.data.materials['Apartment warm interior'], 1.5, (1, .5, .2))
    emission(bpy.data.materials['Apartment linen'], .4, (1, .7, .45))
    # Neighborhood massing gets a sparse grid of warm and cool windows so the
    # street reads as inhabited. Massing heights and windows remain illustrative.
    mat = bpy.data.materials['Neighborhood massing']
    n, l = mat.node_tree.nodes, mat.node_tree.links
    b = n.get('Principled BSDF')
    coord = n.new('ShaderNodeTexCoord')
    sep = n.new('ShaderNodeSeparateXYZ'); l.new(coord.outputs['Object'], sep.inputs[0])
    along = n.new('ShaderNodeMath'); along.operation = 'ADD'
    l.new(sep.outputs['X'], along.inputs[0]); l.new(sep.outputs['Y'], along.inputs[1])
    grid = n.new('ShaderNodeCombineXYZ')
    for axis, src, pitch in (('X', along.outputs[0], 3.1), ('Y', sep.outputs['Z'], 3.3)):
        m = n.new('ShaderNodeMath'); m.operation = 'DIVIDE'; m.inputs[1].default_value = pitch
        l.new(src, m.inputs[0]); l.new(m.outputs[0], grid.inputs[axis])
    cells = n.new('ShaderNodeVectorMath'); cells.operation = 'FLOOR'; l.new(grid.outputs[0], cells.inputs[0])
    frac = n.new('ShaderNodeVectorMath'); frac.operation = 'FRACTION'; l.new(grid.outputs[0], frac.inputs[0])
    fs = n.new('ShaderNodeSeparateXYZ'); l.new(frac.outputs[0], fs.inputs[0])
    mask = None
    for axis, lo, hi in (('X', .25, .75), ('Y', .3, .78)):
        a = n.new('ShaderNodeMath'); a.operation = 'GREATER_THAN'; a.inputs[1].default_value = lo; l.new(fs.outputs[axis], a.inputs[0])
        c = n.new('ShaderNodeMath'); c.operation = 'LESS_THAN'; c.inputs[1].default_value = hi; l.new(fs.outputs[axis], c.inputs[0])
        both = n.new('ShaderNodeMath'); both.operation = 'MULTIPLY'; l.new(a.outputs[0], both.inputs[0]); l.new(c.outputs[0], both.inputs[1])
        if mask:
            m = n.new('ShaderNodeMath'); m.operation = 'MULTIPLY'; l.new(mask, m.inputs[0]); l.new(both.outputs[0], m.inputs[1]); mask = m.outputs[0]
        else:
            mask = both.outputs[0]
    rnd = n.new('ShaderNodeTexWhiteNoise'); rnd.noise_dimensions = '3D'; l.new(cells.outputs[0], rnd.inputs['Vector'])
    lit = n.new('ShaderNodeMath'); lit.operation = 'GREATER_THAN'; lit.inputs[1].default_value = .72; l.new(rnd.outputs['Value'], lit.inputs[0])
    on = n.new('ShaderNodeMath'); on.operation = 'MULTIPLY'; l.new(lit.outputs[0], on.inputs[0]); l.new(mask, on.inputs[1])
    gain = n.new('ShaderNodeMath'); gain.operation = 'MULTIPLY'; gain.inputs[1].default_value = .55; l.new(on.outputs[0], gain.inputs[0])
    hue = n.new('ShaderNodeMix'); hue.data_type = 'RGBA'; hue.inputs['A'].default_value = (1, .55, .24, 1); hue.inputs['B'].default_value = (.75, .85, 1, 1)
    l.new(rnd.outputs['Color'], hue.inputs['Factor'])
    l.new(hue.outputs['Result'], b.inputs['Emission Color']); l.new(gain.outputs[0], b.inputs['Emission Strength'])
    # Wet pavement: low roughness broken up by puddle noise.
    for name in ('road', 'paving', 'Damp pavement', 'ground', 'concrete'):
        mat = bpy.data.materials.get(name)
        if not mat:
            continue
        n, l = mat.node_tree.nodes, mat.node_tree.links
        b = n.get('Principled BSDF')
        coord = n.new('ShaderNodeTexCoord')
        noise = n.new('ShaderNodeTexNoise'); noise.inputs['Scale'].default_value = .35
        noise.inputs['Detail'].default_value = 4
        l.new(coord.outputs['Object'], noise.inputs['Vector'])
        ramp = n.new('ShaderNodeMapRange')
        ramp.inputs['From Min'].default_value = .46; ramp.inputs['From Max'].default_value = .56
        ramp.inputs['To Min'].default_value = .5 if name != 'road' else .32
        ramp.inputs['To Max'].default_value = .06
        l.new(noise.outputs['Fac'], ramp.inputs['Value']); l.new(ramp.outputs['Result'], b.inputs['Roughness'])
        dark = n.new('ShaderNodeMix'); dark.data_type = 'RGBA'; dark.blend_type = 'MULTIPLY'
        dark.inputs['Factor'].default_value = 1; dark.inputs['B'].default_value = (.55, .58, .62, 1)
        src = b.inputs['Base Color'].links[0].from_socket if b.inputs['Base Color'].is_linked else None
        if src:
            l.new(src, dark.inputs['A'])
        else:
            dark.inputs['A'].default_value = b.inputs['Base Color'].default_value[:]
        l.new(dark.outputs['Result'], b.inputs['Base Color'])


def street_lights(scene, col, steel):
    """Illustrative pole lights along the east sidewalk; not a site survey."""
    head = bpy.data.materials.new('Street lantern'); head.use_nodes = True
    emission(head, 12, (1, .72, .42))
    head.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value = (1, .8, .55, 1)
    lights = []
    for y in (380, 980, 1720):
        x = 1790
        for name, b, mat in [('pole', (x-2, x+2, y-2, y+2, 97, 250), steel), ('lantern', (x-5, x+5, y-5, y+5, 250, 262), head)]:
            o = B.box('Street light '+name, b, mat, col)
            o['basis'] = 'Illustrative presentation lighting; not surveyed site furniture'
            lights.append(o)
        d = bpy.data.lights.new('Street light pool', 'POINT'); d.energy = 900; d.color = (1, .7, .4); d.shadow_soft_size = .12
        o = bpy.data.objects.new(d.name, d); col.objects.link(o); o.location = Vector((x, y, 244))*I
        lights.append(o)
    for o in lights:
        for f, v in [(1, False), (146, False), (147, True)]:
            o.hide_render = v; o.keyframe_insert('hide_render', frame=f)


def interior(scene):
    """Calmer luminaires so ceilings read as fixtures, not blown-out holes."""
    emission(bpy.data.materials['Warm LED diffuser'], 3.2)
    for o in scene.objects:
        if 'floor guidance' in o.name:
            o.hide_render = True; o.hide_viewport = True
        if o.type == 'LIGHT' and 'recessed wall wash' in o.name:
            o.data.energy = 26
        if o.type == 'LIGHT' and 'ceiling wash' in o.name:
            o.data.energy = 34
    bronze = bpy.data.materials['Satin elevator bronze'].node_tree.nodes.get('Principled BSDF')
    bronze.inputs['Base Color'].default_value = (.15, .11, .075, 1); bronze.inputs['Metallic'].default_value = .9
    wash = bpy.data.objects['Cab rear feature wash'].data
    wash.energy = 5; wash.size = .9


def slat_wall(scene, col, M):
    """Illustrative walnut slat feature wall on the Lobby 110 south wall, grazed from a cove."""
    verts, faces = [], []
    def add(x0, x1, y0, y1, z0, z1):
        b = len(verts)
        verts.extend([(x*I, y*I, z*I) for z in (z0, z1) for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1))])
        faces.extend([(b, b+3, b+2, b+1), (b+4, b+5, b+6, b+7), (b, b+1, b+5, b+4), (b+1, b+2, b+6, b+5), (b+2, b+3, b+7, b+6), (b+3, b, b+4, b+7)])
    x = 1136.
    while x < 1452:
        add(x, x+1.25, 1261.2, 1263, 136, 226); x += 3
    mesh = bpy.data.meshes.new('Lobby walnut slats'); mesh.from_pydata(verts, [], faces); mesh.update()
    slats = bpy.data.objects.new('Lobby walnut slat feature wall', mesh); col.objects.link(slats)
    mesh.materials.append(M['wood']); slats['basis'] = 'Illustrative finish; not shown on A2.03/A2.04'
    B.box('Lobby slat wall backer', (1132, 1456, 1260, 1261.2, 134, 228), M['trim'], col)
    B.box('Lobby slat wall cove lens', (1132, 1456, 1260, 1265, 228, 229), M['led'], col)
    for x in (1175, 1255, 1335, 1415):
        d = bpy.data.lights.new('Lobby slat grazing light', 'AREA'); d.shape = 'RECTANGLE'
        d.size = 78*I; d.size_y = 2*I; d.energy = 34; d.color = (1, .76, .5)
        o = bpy.data.objects.new(d.name, d); col.objects.link(o)
        o.location = Vector((x, 1266, 227.5))*I; o.rotation_euler = (math.radians(-18), 0, 0)


def xray(scene):
    """Replace the frosted section shader with clean edge-lit glass and a dark void."""
    for key in ('Gallery plaster', 'Warm plaster ceiling', 'Woven corridor carpet', 'Honed lobby stone', 'Elevator door / glass during section'):
        mat = bpy.data.materials[key]
        n, l = mat.node_tree.nodes, mat.node_tree.links
        mix = n.get('Elevator architectural section')
        old = mix.inputs[2].links[0].from_node
        transparent = n.new('ShaderNodeBsdfTransparent')
        glow = n.new('ShaderNodeEmission'); glow.inputs['Color'].default_value = (.62, .78, 1, 1); glow.inputs['Strength'].default_value = .35
        facing = n.new('ShaderNodeLayerWeight'); facing.inputs['Blend'].default_value = .08
        edge = n.new('ShaderNodeMixShader')
        l.new(facing.outputs['Facing'], edge.inputs[0]); l.new(transparent.outputs[0], edge.inputs[1]); l.new(glow.outputs[0], edge.inputs[2])
        l.new(edge.outputs[0], mix.inputs[2])
        n.remove(old)
        # The study ghosted surfaces at 95%; the x-ray reads cleaner fully ghosted.
        for fc in fcurves(mat.node_tree):
            if 'Elevator architectural section' in fc.data_path:
                for k in fc.keyframe_points:
                    for co in (k.co, k.handle_left, k.handle_right):
                        co[1] = min(1., co[1]/.95)
    for o in scene.objects:
        for m in o.modifiers:
            if m.type == 'WIREFRAME':
                m.thickness = .0035 if 'section edges' in o.name else m.thickness
    edge = bpy.data.materials['Section brass edges']
    emission(edge, 2.2, (1, .62, .25))
    # Neighborhood, pavement and the open-air world are hidden only while the
    # section is on screen, so the cut building floats in a dark studio void.
    hide = [o for o in scene.objects if o.name.startswith('OSM building') or o.name == 'Context pavement']
    for o in hide:
        for f, v in [(1, False), (366, False), (367, True), (458, True), (459, False)]:
            o.hide_render = v; o.keyframe_insert('hide_render', frame=f)
    # A dark backdrop sphere, rather than an animated world, keeps Cycles from
    # rebuilding the sky importance map on every frame of the film.
    mesh = bpy.data.meshes.new('Section void backdrop')
    import bmesh
    bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=32, v_segments=16, radius=300); bm.to_mesh(mesh); bm.free()
    void = bpy.data.materials.new('Section void'); void.use_nodes = True
    emission(void, 1., (.0045, .006, .011)); void.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value = (0, 0, 0, 1)
    void.cycles.emission_sampling = 'NONE'
    mesh.materials.append(void)
    backdrop = bpy.data.objects.new('Section void backdrop', mesh)
    bpy.data.collections['Native animation / camera doors elevator and section'].objects.link(backdrop)
    backdrop.location = Vector((848, 1452, 250))*I; backdrop.visible_shadow = False
    for f, v in [(1, True), (366, True), (367, False), (458, False), (459, True)]:
        backdrop.hide_render = v; backdrop.keyframe_insert('hide_render', frame=f)
    # Furnishings east of the cut would float in the void; brass edges and
    # the cut surfaces themselves stay. Objects already hidden or animated
    # (the exterior study, glazing, doors) keep their own visibility keys.
    bpy.context.view_layer.update()
    for o in scene.objects:
        if o.hide_render or o.animation_data:
            continue
        if o.type in ('MESH', 'FONT', 'CURVE') and o not in B.SECTION and 'section edges' not in o.name:
            x = min((o.matrix_world@Vector(v)).x for v in o.bound_box)/I
            if 895 < x < 1700:
                for f, v in [(1, False), (366, False), (367, True), (458, True), (459, False)]:
                    o.hide_render = v; o.keyframe_insert('hide_render', frame=f)


def camera(scene, rig, shot):
    cam = bpy.data.objects.new('Cinema / '+shot['id'], bpy.data.cameras.new('Cinema lens / '+shot['id']))
    rig.objects.link(cam)
    d = cam.data
    d.lens = shot['lens']; d.sensor_fit = 'HORIZONTAL'; d.sensor_width = 36
    d.shift_y = shot.get('shift_y', 0); d.clip_start = .03; d.clip_end = 600
    if shot.get('fstop'):
        d.dof.use_dof = True; d.dof.aperture_fstop = shot['fstop']; d.dof.aperture_blades = 7; d.dof.aperture_ratio = 1
    a, b = shot.get('ease', [0, 0])
    n = shot['frames']
    focus = Vector(shot['focus'])*I
    for j in range(n):
        f = shot['src_start']+j
        u = profile(j/(n-1), a, b)
        pos = sample(shot['keys'], u, 'pos')*I
        look = sample(shot['keys'], u, 'look')*I
        # A barely perceptible stabilized-head drift, a few millimetres.
        t = f/24
        pos += Vector((math.sin(t*1.3+n)*.002, math.sin(t*.9+2*n)*.002, math.sin(t*1.7)*.0015))
        direction = look-pos
        yaw = math.atan2(direction.y, direction.x)
        pitch = math.atan2(direction.z, math.hypot(direction.x, direction.y)) if shot.get('pitch') else 0
        cam.location = pos
        cam.rotation_euler = (math.pi/2+pitch, 0, yaw-math.pi/2)
        cam.keyframe_insert('location', frame=f); cam.keyframe_insert('rotation_euler', frame=f)
        if d.dof.use_dof:
            d.dof.focus_distance = (focus-pos).length; d.dof.keyframe_insert('focus_distance', frame=f)
    return cam


def prepare(base, output):
    if not base.exists():
        B.build(base)
    else:
        B.WALLS.clear(); B.SECTION.clear()
    bpy.ops.wm.open_mainfile(filepath=str(base))
    scene = bpy.context.scene
    # Recover the section list from the saved scene: objects carrying the boolean.
    B.SECTION[:] = [o for o in scene.objects if any(m.name == 'Animated east-side section' for m in o.modifiers)]
    rig = bpy.data.collections['Native animation / camera doors elevator and section']
    dress = bpy.data.collections.new('Cinema / dusk street lighting'); scene.collection.children.link(dress)
    M = {'wood': bpy.data.materials['Satin walnut doors'], 'trim': bpy.data.materials['Dark walnut frames'], 'led': bpy.data.materials['Warm LED diffuser']}
    slat_wall(scene, bpy.data.collections['Native interior / Lobby 110 and Corridors 108–208'], M)
    dusk(scene); interior(scene); xray(scene)
    street_lights(scene, dress, bpy.data.materials['Entrance stainless steel'])
    cams = {s['id']: camera(scene, rig, s) for s in SPEC['shots']}
    c = scene.cycles
    c.use_adaptive_sampling = True; c.adaptive_threshold = .02; c.use_denoising = True
    c.denoiser = 'OPENIMAGEDENOISE'; c.denoising_prefilter = 'ACCURATE'
    c.sample_clamp_indirect = 8; c.blur_glossy = .5; c.caustics_reflective = False; c.caustics_refractive = False
    c.film_exposure = 1.0
    scene.render.use_motion_blur = True; scene.render.motion_blur_shutter = .5
    scene.render.image_settings.color_depth = '16'
    scene.view_settings.look = 'AgX - Base Contrast'
    scene['cinema_spec_sha256'] = hashlib.sha256(SPEC_FILE.read_bytes()).hexdigest()
    scene['cinema_camera_sha256'] = camera_hash()
    scene['cinema_scope'] = 'Edit, cameras, dusk exterior, street lights and x-ray section are presentation treatments.'
    scene.camera = cams[SPEC['shots'][0]['id']]
    output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(output), compress=True)
    return scene


def validate(scene, path):
    """Every shot camera stays clear of interior geometry and OSM massing, and
    turns smoothly within a shot. Uses evaluated cameras at every film frame."""
    interior = [o for o in bpy.data.collections['Native interior / Lobby 110 and Corridors 108–208'].all_objects if o.type == 'MESH']
    osm = json.loads((HERE/'flight.spec.json').read_text())['osm_context']['buildings']

    def inside(x, y, poly):
        c = False
        for i in range(len(poly)):
            (x1, y1), (x2, y2) = poly[i], poly[(i+1) % len(poly)]
            if (y1 > y) != (y2 > y) and x < (x2-x1)*(y-y1)/(y2-y1)+x1:
                c = not c
        return c
    report = {'shots': [], 'failures': []}
    for shot in SPEC['shots']:
        cam = bpy.data.objects['Cinema / '+shot['id']]
        prev, step, clearance = None, 0., 1e9
        for j in range(shot['frames']):
            f = shot['src_start']+j
            scene.frame_set(f)
            pos = cam.matrix_world.translation.copy(); rot = cam.matrix_world.to_quaternion()
            if prev is not None:
                angle = math.degrees(prev.rotation_difference(rot).angle); step = max(step, min(angle, 360-angle))
            prev = rot
            for o in interior:
                if o.hide_render:
                    continue
                local = o.matrix_world.inverted()@pos
                lo = [min(v[k] for v in o.bound_box) for k in range(3)]
                hi = [max(v[k] for v in o.bound_box) for k in range(3)]
                gap = max(max(lo[k]-local[k], local[k]-hi[k]) for k in range(3))
                clearance = min(clearance, gap)
                if gap < .025:
                    report['failures'].append({'shot': shot['id'], 'frame': f, 'object': o.name})
            for b in osm:
                if pos.z < b['height_m'] and inside(pos.x, pos.y, b['footprint_m']):
                    report['failures'].append({'shot': shot['id'], 'frame': f, 'object': 'OSM building '+str(b['osm_id'])})
        report['shots'].append({'id': shot['id'], 'native_frames': [shot['src_start'], shot['src_start']+shot['frames']-1],
                                'min_clearance_m': round(clearance, 4), 'max_rotation_step_deg': round(step, 4)})
        if step > 1.5:
            report['failures'].append({'shot': shot['id'], 'rotation_step_deg': step})
    report['blender'] = bpy.app.version_string
    report['cinema_spec_sha256'] = hashlib.sha256(SPEC_FILE.read_bytes()).hexdigest()
    path.write_text(json.dumps(report, indent=2)+'\n')
    if report['failures']:
        raise RuntimeError('Cinema camera validation failed: '+json.dumps(report['failures'][:5]))
    print('Cinema cameras validated:', json.dumps(report['shots']))


def configure_device(scene, backend):
    """Select CPU, CUDA or OptiX; never fall back silently."""
    scene.cycles.device = 'CPU'
    if backend == 'CPU':
        return []
    prefs = bpy.context.preferences.addons['cycles'].preferences
    prefs.compute_device_type = backend
    prefs.get_devices()
    used = []
    for d in prefs.devices:
        d.use = d.type == backend
        if d.use:
            used.append(d.name)
    if not used:
        raise SystemExit(f'No {backend} device found; refusing to fall back to CPU')
    scene.cycles.device = 'GPU'
    scene.cycles.denoising_use_gpu = True
    print('Cycles devices:', used, flush=True)
    return used


def settings(scene, profile_name, samples=None):
    w, h, max_samples, threshold = PROFILES[profile_name]
    scene.render.resolution_x = w; scene.render.resolution_y = h; scene.render.resolution_percentage = 100
    scene.cycles.samples = samples or max_samples; scene.cycles.adaptive_threshold = threshold
    scene.cycles.adaptive_min_samples = min(32, scene.cycles.samples)


def render(scene, shots, profile_name, step=1, only=None, worker=(0, 1), folder=None):
    log = []
    index = -1
    for shot in SPEC['shots']:
        if shots and shot['id'] not in shots:
            continue
        cam = bpy.data.objects['Cinema / '+shot['id']]; scene.camera = cam
        out = BUILD/'frames'/(folder or profile_name)/shot['id']; out.mkdir(parents=True, exist_ok=True)
        local = only if only else range(1, shot['frames']+1, step)
        for j in local:
            if not 1 <= j <= shot['frames']:
                continue
            # Workers interleave frames so each sees every shot's cost.
            index += 1
            if index % worker[1] != worker[0]:
                continue
            path = out/f'{j:04d}.png'
            if path.exists():
                continue
            scene.frame_set(shot['src_start']+j-1)
            scene.render.filepath = str(path.with_suffix('.tmp.png'))
            start = time.monotonic(); bpy.ops.render.render(write_still=True)
            path.with_suffix('.tmp.png').rename(path)
            log.append((shot['id'], j, round(time.monotonic()-start, 1)))
            print(f'SHOT {shot["id"]} {j}/{shot["frames"]} {log[-1][2]}s', flush=True)
    return log


def bench(scene, profile_name):
    """Render one mid-shot frame per shot and project the full film."""
    folder = 'bench-'+profile_name
    (BUILD/'frames'/folder/SPEC['shots'][0]['id']/'0001.png').unlink(missing_ok=True)
    for shot in SPEC['shots']:
        f = BUILD/'frames'/folder/shot['id']/f'{shot["frames"]//2:04d}.png'
        f.unlink(missing_ok=True)
    # The first frame also pays kernel loading; render a warm-up first.
    render(scene, [SPEC['shots'][0]['id']], profile_name, only=[1], folder=folder)
    log = []
    for shot in SPEC['shots']:
        log += render(scene, [shot['id']], profile_name, only=[shot['frames']//2], folder=folder)
    per = {sid: t for sid, _, t in log}
    total = sum(per[s['id']]*s['frames'] for s in SPEC['shots'])
    report = {'profile': profile_name, 'resolution': PROFILES[profile_name][:2], 'samples': scene.cycles.samples,
              'device': scene.cycles.device, 'seconds_per_frame': per,
              'projected_hours_one_worker': round(total/3600, 2), 'frames': sum(s['frames'] for s in SPEC['shots'])}
    (BUILD/f'bench-{profile_name}.json').write_text(json.dumps(report, indent=2)+'\n')
    print('BENCH', json.dumps(report), flush=True)


def main():
    if '--' in sys.argv:  # blender -b -P cinema.py -- args
        sys.argv = [sys.argv[0]]+sys.argv[sys.argv.index('--')+1:]
    p = argparse.ArgumentParser()
    p.add_argument('--base', type=Path, default=ROOT/'build/highland-blender/Highland-walkthrough.blend')
    p.add_argument('--output', type=Path, default=BUILD/'Highland-cinema.blend')
    p.add_argument('--reuse', action='store_true', help='Open --output instead of preparing it again')
    p.add_argument('--profile', choices=PROFILES, default='proof')
    p.add_argument('--shots', default='', help='Comma-separated shot IDs; default all')
    p.add_argument('--step', type=int, default=1, help='Render every Nth frame (previews)')
    p.add_argument('--only', default='', help='Comma-separated shot-local frame numbers')
    p.add_argument('--threads', type=int, default=0)
    p.add_argument('--validate', action='store_true', help='Check camera clearance and smoothness at every film frame')
    p.add_argument('--device', choices=['CPU', 'CUDA', 'OPTIX'], default='CPU')
    p.add_argument('--samples', type=int, help='Override the profile maximum samples')
    p.add_argument('--worker', default='0/1', help='k/n: render every nth frame starting at k, for parallel processes')
    p.add_argument('--bench', action='store_true', help='Time one frame per shot and project the film')
    a = p.parse_args()
    if a.reuse:
        bpy.ops.wm.open_mainfile(filepath=str(a.output)); scene = bpy.context.scene
        if scene.get('cinema_camera_sha256') != camera_hash():
            raise SystemExit(f'{a.output.name} was prepared from a different cinema.shots.json; '
                             'run cinema.py without --reuse to rebuild the cameras, and delete frames of changed shots')
    else:
        scene = prepare(a.base, a.output)
    if a.threads:
        scene.render.threads_mode = 'FIXED'; scene.render.threads = a.threads
    if a.validate:
        validate(scene, a.output.with_name('cinema-validation.json'))
    configure_device(scene, a.device)
    settings(scene, a.profile, a.samples)
    if a.bench:
        bench(scene, a.profile); return
    only = [int(x) for x in a.only.split(',') if x] or None
    k, n = (int(x) for x in a.worker.split('/'))
    render(scene, [s for s in a.shots.split(',') if s], a.profile, a.step, only, (k, n))


if __name__ == '__main__':
    main()
