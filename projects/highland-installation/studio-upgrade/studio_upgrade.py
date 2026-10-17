"""Apply a source-preserving studio treatment to the Highland animation (Blender 5.0).

Run with Blender's --python or a Python 3.11 environment containing bpy 5.0.1.
The original files are read only. Configuration and all added geometry are illustrative.
"""
import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent
C = json.loads((ROOT / 'studio-config.json').read_text())
G = json.loads((PROJECT / 'installation/installation-data.json').read_text())
FPS = C['render']['fps']
OUT = ROOT / 'output'
OUT.mkdir(exist_ok=True)


def rgba(value):
    rgb = [int(value[k:k+2], 16) / 255 for k in (1, 3, 5)]
    return tuple(v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in rgb) + (1,)


def frame(seconds):
    return round(seconds * FPS) + 1


def node(tree, kind, name, x=0, y=0):
    result = tree.nodes.new(kind)
    result.name = result.label = name
    result.location = (x, y)
    return result


def material(name):
    result = bpy.data.materials.new('Studio | ' + name)
    result.use_nodes = True
    result.node_tree.nodes.clear()
    return result, result.node_tree


def drive(owner, path, expression, variables=()):
    driver = owner.driver_add(path).driver
    driver.expression = expression
    for name, target, data_path in variables:
        variable = driver.variables.new()
        variable.name = name
        variable.type = 'SINGLE_PROP'
        variable.targets[0].id_type = 'CURVE' if isinstance(target, bpy.types.Curve) else 'OBJECT'
        variable.targets[0].id = target
        variable.targets[0].data_path = data_path
    return driver


def tag(obj, role, basis):
    obj['status'] = 'assumed'
    obj['presentation_role'] = role
    obj['basis'] = basis
    obj['not_for_takeoff'] = True


def visibility(obj, start, end):
    for t, hidden in [(0, True), (max(0, start-1/FPS), True), (start, False), (end, True)]:
        obj.hide_render = obj.hide_viewport = hidden
        obj.keyframe_insert('hide_render', frame=frame(t))
        obj.keyframe_insert('hide_viewport', frame=frame(t))
    if obj.animation_data:
        for layer in obj.animation_data.action.layers:
            for strip in layer.strips:
                bag = strip.channelbag(obj.animation_data.action_slot)
                if bag:
                    for curve in bag.fcurves:
                        for key in curve.keyframe_points:
                            key.interpolation = 'CONSTANT'


def new_mesh(scene, name, vertices, faces, mat):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    scene.collection.objects.link(obj)
    obj.data.materials.append(mat)
    return obj


def new_curve(scene, name, paths, radius, mat):
    data = bpy.data.curves.new(name, 'CURVE')
    data.dimensions = '3D'
    data.bevel_depth = radius
    data.bevel_resolution = 3
    data.use_fill_caps = True
    for points in paths:
        spline = data.splines.new('POLY')
        spline.points.add(len(points)-1)
        for p, xyz in zip(spline.points, points):
            p.co = (*xyz, 1)
    obj = bpy.data.objects.new(name, data)
    scene.collection.objects.link(obj)
    obj.data.materials.append(mat)
    return obj


def plain_principled(name, color, roughness=.4, emission=0):
    mat, tree = material(name)
    bs = node(tree, 'ShaderNodeBsdfPrincipled', 'Surface')
    bs.inputs['Base Color'].default_value = rgba(color)
    bs.inputs['Roughness'].default_value = roughness
    bs.inputs['Emission Color'].default_value = rgba(color)
    bs.inputs['Emission Strength'].default_value = emission
    out = node(tree, 'ShaderNodeOutputMaterial', 'Output', 300)
    tree.links.new(bs.outputs['BSDF'], out.inputs['Surface'])
    return mat


def pipe_material(system):
    mat, tree = material('Coated pipe ' + system)
    bs = node(tree, 'ShaderNodeBsdfPrincipled', 'Coated polymer presentation finish', 350)
    bs.inputs['Base Color'].default_value = rgba(C['palette'][system])
    for key, value in [('Roughness', .25), ('Coat Weight', .5), ('Coat Roughness', .18), ('Metallic', 0), ('IOR', 1.46)]:
        bs.inputs[key].default_value = value
    p = C['pipe']
    bs.inputs['Roughness'].default_value = p['roughness']
    bs.inputs['Coat Weight'].default_value = p['coat_weight']
    bs.inputs['Coat Roughness'].default_value = p['coat_roughness']
    bs.inputs['Metallic'].default_value = p['metallic']
    bs.inputs['Specular IOR Level'].default_value = .35
    bs.inputs['Coat IOR'].default_value = 1.35
    tex = node(tree, 'ShaderNodeTexNoise', 'Fine roughness only', -650, -100)
    tex.inputs['Scale'].default_value = 180
    tex.inputs['Detail'].default_value = 2
    rough = node(tree, 'ShaderNodeMapRange', '0.25 ± 0.025', -200, -50)
    rough.inputs['To Min'].default_value = p['roughness']-p['roughness_variation']
    rough.inputs['To Max'].default_value = p['roughness']+p['roughness_variation']
    tree.links.new(tex.outputs['Fac'], rough.inputs['Value'])
    tree.links.new(rough.outputs['Result'], bs.inputs['Roughness'])
    geom = node(tree, 'ShaderNodeNewGeometry', 'World coordinates', -900, -100)
    tree.links.new(geom.outputs['Position'], tex.inputs['Vector'])
    bump = node(tree, 'ShaderNodeBump', 'Subtle microtexture', 80, -210)
    bump.inputs['Strength'].default_value = .06
    bump.inputs['Distance'].default_value = p['micro_bump_m']
    tree.links.new(tex.outputs['Fac'], bump.inputs['Height'])
    tree.links.new(bump.outputs['Normal'], bs.inputs['Normal'])
    fresnel = node(tree, 'ShaderNodeFresnel', 'Subtle colored edge tint', -600, 240)
    fresnel.inputs['IOR'].default_value = 1.46
    gain = node(tree, 'ShaderNodeMath', 'Keep the rim restrained', -390, 240)
    gain.operation = 'MULTIPLY'
    gain.inputs[1].default_value = .10
    mix = node(tree, 'ShaderNodeMixRGB', 'System-colored rim', -120, 240)
    base = rgba(C['palette'][system])
    mix.inputs[1].default_value = base
    mix.inputs[2].default_value = tuple(min(1, v*1.35+.025) for v in base[:3])+(1,)
    tree.links.new(fresnel.outputs['Fac'], gain.inputs[0])
    tree.links.new(gain.outputs[0], mix.inputs[0])
    tree.links.new(mix.outputs[0], bs.inputs['Base Color'])
    out = node(tree, 'ShaderNodeOutputMaterial', 'Output', 650)
    tree.links.new(bs.outputs[0], out.inputs['Surface'])
    return mat


def blueprint_material():
    mat, tree = material('Cubic blueprint, transparent paper')
    tex = node(tree, 'ShaderNodeTexImage', 'P4.01 / original PDF at 400 dpi', -800)
    tex.image = bpy.data.images.load(str(ROOT / 'assets/unit-b-plan-400dpi.png'), check_existing=True)
    tex.image.colorspace_settings.name = 'sRGB'
    tex.interpolation = 'Cubic'
    tex.extension = 'CLIP'
    bw = node(tree, 'ShaderNodeRGBToBW', 'Drawing luminance', -550)
    ramp = node(tree, 'ShaderNodeValToRGB', 'Ink / paper separation', -330)
    ramp.color_ramp.elements[0].position = C['blueprint']['ink_black_point']
    ramp.color_ramp.elements[0].color = (1, 1, 1, 1)
    ramp.color_ramp.elements[1].position = C['blueprint']['paper_white_point']
    ramp.color_ramp.elements[1].color = (0, 0, 0, 0)
    tree.links.new(tex.outputs['Color'], bw.inputs[0])
    tree.links.new(bw.outputs[0], ramp.inputs['Fac'])
    # Hue/saturation keeps the owner's colored source annotations intact.
    hsv = node(tree, 'ShaderNodeSeparateColor', 'Source markup saturation', -550, -230)
    hsv.mode = 'HSV'
    tree.links.new(tex.outputs['Color'], hsv.inputs['Color'])
    colored = node(tree, 'ShaderNodeMath', 'Preserve colored markup', -300, -230)
    colored.operation = 'GREATER_THAN'
    colored.inputs[1].default_value = .12
    tree.links.new(hsv.outputs[1], colored.inputs[0])
    ink = node(tree, 'ShaderNodeMixRGB', 'Charcoal lines / source markup', -50, -80)
    ink.inputs[1].default_value = rgba(C['blueprint']['ink_srgb'])
    tree.links.new(tex.outputs['Color'], ink.inputs[2])
    tree.links.new(colored.outputs[0], ink.inputs[0])
    emission = node(tree, 'ShaderNodeEmission', 'Unlit readable ink', 180, -70)
    emission.inputs['Strength'].default_value = .6
    tree.links.new(ink.outputs[0], emission.inputs[0])
    transparent = node(tree, 'ShaderNodeBsdfTransparent', 'Paper is transparent', 180, 140)
    mix = node(tree, 'ShaderNodeMixShader', 'Ink over receiver', 430)
    opacity = node(tree, 'ShaderNodeMath', '25 percent warm gray reference', 180, 320)
    opacity.operation = 'MULTIPLY'
    opacity.inputs[1].default_value = C['blueprint']['opacity']
    tree.links.new(ramp.outputs['Alpha'], opacity.inputs[0])
    tree.links.new(opacity.outputs[0], mix.inputs[0])
    tree.links.new(transparent.outputs[0], mix.inputs[1])
    tree.links.new(emission.outputs[0], mix.inputs[2])
    out = node(tree, 'ShaderNodeOutputMaterial', 'Output', 650)
    tree.links.new(mix.outputs[0], out.inputs['Surface'])
    return mat


def receiver_material():
    mat, tree = material('Shadow receiver with local contact AO')
    ao = node(tree, 'ShaderNodeAmbientOcclusion', 'Short-range contact only', -500)
    ao.inputs['Distance'].default_value = C['contact']['ao_distance_m']
    ao.samples = C['contact']['ao_samples']
    strength = node(tree, 'ShaderNodeMixRGB', 'AO strength 16 percent', -200)
    strength.blend_type = 'MULTIPLY'
    strength.inputs[0].default_value = C['contact']['ao_strength']
    strength.inputs[1].default_value = (1, 1, 1, 1)
    tree.links.new(ao.outputs['AO'], strength.inputs[2])
    bs = node(tree, 'ShaderNodeBsdfPrincipled', 'Matte receiver', 70)
    bs.inputs['Roughness'].default_value = 1
    tree.links.new(strength.outputs[0], bs.inputs['Base Color'])
    out = node(tree, 'ShaderNodeOutputMaterial', 'Output', 360)
    tree.links.new(bs.outputs[0], out.inputs[0])
    return mat


def ghost_material():
    mat, tree = material('90 percent transparent frosted context')
    transparent = node(tree, 'ShaderNodeBsdfTransparent', '90 percent clear')
    bs = node(tree, 'ShaderNodeBsdfPrincipled', '10 percent frosted surface', 0, -180)
    bs.inputs['Base Color'].default_value = rgba('#DCE3E4')
    bs.inputs['Roughness'].default_value = .42
    bs.inputs['Coat Weight'].default_value = .15
    bs.inputs['Transmission Weight'].default_value = .15
    mix = node(tree, 'ShaderNodeMixShader', 'Single-surface coverage', 300)
    mix.inputs[0].default_value = C['ghost_walls']['surface_opacity']
    tree.links.new(transparent.outputs[0], mix.inputs[1])
    tree.links.new(bs.outputs[0], mix.inputs[2])
    out = node(tree, 'ShaderNodeOutputMaterial', 'Output', 550)
    tree.links.new(mix.outputs[0], out.inputs[0])
    if hasattr(mat, 'surface_render_method'):
        mat.surface_render_method = 'DITHERED'
    return mat


def studio_hdri():
    """A real float EXR environment, procedurally generated rather than a photo."""
    import numpy as np
    path = ROOT / 'assets/neutral-studio.exr'
    if path.exists():
        image=bpy.data.images.load(str(path), check_existing=True)
        image.colorspace_settings.name=C['lighting']['authored_hdri_color_space']
        return image
    w, h = 1024, 512
    y, x = np.mgrid[0:h, 0:w]
    data = np.zeros((h, w, 4), dtype=np.float32)
    sky = np.full((h, w), .09, dtype=np.float32)
    for u, v, sx, sy, gain in [(.20, .72, .08, .09, 6), (.66, .68, .13, .06, 3), (.88, .82, .04, .10, 4)]:
        dx = np.minimum(np.abs(x/w-u), 1-np.abs(x/w-u))
        sky += gain*np.exp(-((dx/sx)**8+((y/h-v)/sy)**8))
    data[:, :, :3] = sky[:, :, None]
    data[:, :, 3] = 1
    image = bpy.data.images.new('Procedural neutral studio HDRI', width=w, height=h, float_buffer=True)
    image.colorspace_settings.name=C['lighting']['authored_hdri_color_space']
    image.pixels.foreach_set(data.ravel())
    image.filepath_raw = str(path)
    image.file_format = 'OPEN_EXR'
    image.save()
    image.pack()
    return image


def configure(scene, hdri):
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = C['render']['samples']
    scene.cycles.use_denoising = False  # preserve blueprint lettering
    scene.cycles.use_adaptive_sampling = True
    scene.cycles.adaptive_threshold = .04
    scene.cycles.max_bounces = 6
    scene.cycles.diffuse_bounces = 2
    scene.cycles.glossy_bounces = 3
    scene.cycles.transmission_bounces = 4
    scene.cycles.transparent_max_bounces = 12
    scene.render.threads_mode = 'FIXED'
    scene.render.threads = 2
    scene.render.use_persistent_data = True
    scene.render.film_transparent = True
    scene.render.use_sequencer = False
    scene.render.resolution_x = C['render']['width']
    scene.render.resolution_y = C['render']['height']
    scene.render.resolution_percentage = 100
    scene.render.fps = FPS
    scene.frame_start, scene.frame_end = 1, FPS*90
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'
    scene.render.image_settings.color_depth = '8'
    scene.view_settings.view_transform = C['color']['view_transform']
    scene.view_settings.look = C['color']['look']
    scene.view_settings.exposure = C['color']['exposure']
    scene.view_settings.gamma = 1
    scene.display_settings.display_device = 'sRGB'
    scene.render.dither_intensity = 0
    for layer in scene.view_layers:
        layer.use_pass_ambient_occlusion = True
        layer.use_pass_shadow = True
        layer.cycles.use_pass_shadow_catcher = True
    world = bpy.data.worlds.new('Studio world | ' + scene.name)
    world.use_nodes = True
    tree = world.node_tree
    tree.nodes.clear()
    tex = node(tree, 'ShaderNodeTexEnvironment', 'Neutral studio EXR')
    tex.image = hdri
    bg = node(tree, 'ShaderNodeBackground', 'Low-energy reflection environment', 250)
    bg.inputs[1].default_value = C['lighting']['hdri_strength']
    out = node(tree, 'ShaderNodeOutputWorld', 'Output', 480)
    tree.links.new(tex.outputs[0], bg.inputs[0])
    tree.links.new(bg.outputs[0], out.inputs[0])
    scene.world = world


def lighting(scene, scale=1):
    for obj in scene.objects:
        if obj.type == 'LIGHT':
            obj.hide_render = True
    for entry in C['lighting']['lights']:
        data = bpy.data.lights.new(entry['name'], 'AREA')
        data.energy = entry['power_w']*scale**2
        data.shape = 'RECTANGLE' if 'size_y_m' in entry else 'DISK'
        data.size = entry['size_m']*scale
        if 'size_y_m' in entry:
            data.size_y = entry['size_y_m']*scale
        obj = bpy.data.objects.new('Studio | ' + entry['name'], data)
        scene.collection.objects.link(obj)
        obj.location = Vector(entry['position'])*scale
        obj.rotation_euler = (Vector(entry['target'])*scale-obj.location).to_track_quat('-Z', 'Y').to_euler()


def coord(point):
    return Vector(((point[0]-.5)*G['display']['width_in']*.0254, (.5-point[1])*G['display']['height_in']*.0254, point[2]*.0254))


def ghost_walls(scene):
    cfg = C['ghost_walls']
    mat = ghost_material()
    edge = plain_principled('Ghost wall top edge', '#AABBC0', .55, .08)
    height = cfg['display_height_in']*.0254
    for i, segment in enumerate(cfg['segments']):
        a, b = (coord([*p, 0]) for p in segment)
        top_a, top_b = a+Vector((0, 0, height)), b+Vector((0, 0, height))
        wall = new_mesh(scene, f'Studio ghost wall {i+1:02}', [a, b, top_b, top_a], [(0, 1, 2, 3)], mat)
        wall.visible_shadow = False
        tag(wall, 'ghost_wall', cfg['basis'])
        wall['source'] = cfg['source']
        visibility(wall, cfg['start_s'], cfg['end_s'])
        top = new_curve(scene, f'Studio ghost edge {i+1:02}', [[top_a, top_b]], .009, edge)
        top.visible_shadow = False
        tag(top, 'ghost_wall_edge', cfg['basis'])
        visibility(top, cfg['start_s'], cfg['end_s'])


def access_boxes(scene):
    mat = plain_principled('Amber access wire', C['palette']['access'], .35, C['access']['emission_strength'])
    fill, tree = material('Barely visible access volume')
    trans = node(tree, 'ShaderNodeBsdfTransparent', 'Clear')
    em = node(tree, 'ShaderNodeEmission', 'Amber envelope', 0, -180)
    em.inputs[0].default_value = rgba(C['palette']['access'])
    mix = node(tree, 'ShaderNodeMixShader', '2.5 percent envelope', 260)
    mix.inputs[0].default_value = C['access']['fill_opacity']
    tree.links.new(trans.outputs[0], mix.inputs[1])
    tree.links.new(em.outputs[0], mix.inputs[2])
    out = node(tree, 'ShaderNodeOutputMaterial', 'Output', 500)
    tree.links.new(mix.outputs[0], out.inputs[0])
    for i, item in enumerate(e for e in G['elements'] if e['type'] == 'access'):
        x0, y0, x1, y1 = item['rect']
        bottom = [coord([x0, y0, 3]), coord([x1, y0, 3]), coord([x1, y1, 3]), coord([x0, y1, 3])]
        top = [p+Vector((0, 0, C['access']['display_height_m'])) for p in bottom]
        paths = [[bottom[k], bottom[(k+1)%4]] for k in range(4)]
        paths += [[top[k], top[(k+1)%4]] for k in range(4)]
        paths += [[bottom[k], top[k]] for k in range(4)]
        dashed = []
        for a,b in paths:
            length = (b-a).length
            count = max(1, math.ceil(length/C['access']['dash_length_m']))
            for n in range(count):
                dashed.append([a.lerp(b,n/count),a.lerp(b,min(1,(n+.58)/count))])
        box = new_curve(scene, 'Studio access '+item['id'], dashed, C['access']['wire_radius_m'], mat)
        box.visible_shadow = False
        tag(box, 'access_envelope', 'Wire bounding box for proposed access; display height is not an opening dimension or wall depth.')
        visibility(box, 18.5+i*.9, 74+i*.65)
        volume = new_mesh(scene,'Studio access volume '+item['id'],bottom+top,[(0,1,2,3),(4,7,6,5),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)],fill)
        volume.visible_shadow = False
        tag(volume,'access_envelope',box['basis'])
        visibility(volume,18.5+i*.9,74+i*.65)
        source = scene.objects.get(item['id'])
        if source:
            drive(box.data, 'bevel_factor_end', 'reveal', [('reveal', source.data, 'bevel_factor_end')])
            drive(source, 'hide_render', 'True')


def joints(scene, pipe, mat):
    for spline in pipe.data.splines:
        if spline.type != 'POLY':
            continue
        pts = [Vector(p.co[:3]) for p in spline.points]
        lengths = [(b-a).length for a, b in zip(pts, pts[1:])]
        total = sum(lengths)
        distance = 0
        for index in range(1, len(pts)-1):
            distance += lengths[index-1]
            a, b = pts[index]-pts[index-1], pts[index+1]-pts[index]
            if min(a.length, b.length) < 1e-8 or abs(a.normalized().dot(b.normalized())) > .98:
                continue
            bpy.context.window.scene = scene
            bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=8, radius=pipe.data.bevel_depth*C['pipe']['joint_radius_factor'])
            obj = bpy.context.object
            obj.name = f'Studio corner | {pipe.name} | {index}'
            obj.parent = pipe
            obj.location = pts[index]
            obj.data.materials.clear()
            obj.data.materials.append(mat)
            for poly in obj.data.polygons:
                poly.use_smooth = True
            drive(obj, 'hide_render', f'hidden or reveal < {distance/total:.9f}', [('hidden', pipe, 'hide_render'), ('reveal', pipe.data, 'bevel_factor_end')])
            tag(obj, 'corner_fillet', 'Smooth presentation cover at a route corner; not a specified elbow or joint product.')


def pulse_overlay(scene, pipe, shared=False):
    """Per-vertex arc length gives directional travel around bends, never global X."""
    if len(pipe.data.splines) != 1 or pipe.data.splines[0].type != 'POLY':
        return
    pts = [Vector(p.co[:3]) for p in pipe.data.splines[0].points]
    vertices, faces, distances = [], [], []
    radius, distance, sides = pipe.data.bevel_depth*1.025, 0.0, 16
    for a, b in zip(pts, pts[1:]):
        tangent = b-a
        length = tangent.length
        if length < 1e-7:
            continue
        direction = tangent.normalized()
        axis = direction.cross(Vector((0, 0, 1)))
        if axis.length < .01:
            axis = direction.cross(Vector((0, 1, 0)))
        axis.normalize()
        other = direction.cross(axis).normalized()
        start = len(vertices)
        for endpoint, s in [(a, distance), (b, distance+length)]:
            for k in range(sides):
                angle = k*math.tau/sides
                vertices.append(endpoint+radius*(axis*math.cos(angle)+other*math.sin(angle)))
                distances.append(s)
        for k in range(sides):
            faces.append((start+k, start+(k+1)%sides, start+sides+(k+1)%sides, start+sides+k))
        distance += length
    mat, tree = material('Pulse '+pipe.name)
    attr = node(tree, 'ShaderNodeAttribute', 'Arc length in meters', -900)
    attr.attribute_name = 'studio_s'
    reveal = node(tree, 'ShaderNodeValue', 'Installed extent', -900, -200)
    drive(reveal.outputs[0], 'default_value', f'reveal*{distance}', [('reveal', pipe.data, 'bevel_factor_end')])
    delta = node(tree, 'ShaderNodeMath', 'Assembly leading edge', -650, -180)
    delta.operation = 'SUBTRACT'
    tree.links.new(reveal.outputs[0], delta.inputs[0])
    tree.links.new(attr.outputs['Fac'], delta.inputs[1])
    assembly = node(tree, 'ShaderNodeMapRange', 'Assembly highlight, not water flow', -430, -200)
    assembly.clamp = True
    assembly.inputs['From Max'].default_value = .18
    assembly.inputs['To Min'].default_value = .16
    assembly.inputs['To Max'].default_value = 0
    tree.links.new(delta.outputs[0], assembly.inputs['Value'])
    frequency = node(tree, 'ShaderNodeMath', 'Pulse spacing', -670, 100)
    frequency.operation = 'MULTIPLY'
    sign = -1 if shared and pipe.get('system')=='HWC' and not pipe.name.startswith('RETURN-') else 1
    frequency.inputs[1].default_value = sign/C['pulse']['spacing_m']
    tree.links.new(attr.outputs['Fac'], frequency.inputs[0])
    phase = node(tree, 'ShaderNodeMath', 'Travel after service restoration', -450, 100)
    phase.operation = 'SUBTRACT'
    tree.links.new(frequency.outputs[0], phase.inputs[0])
    drive(phase.inputs[1], 'default_value', f'(frame-1)/{FPS}*{C["pulse"]["speed_m_s"]}/{C["pulse"]["spacing_m"]}')
    fraction = node(tree, 'ShaderNodeMath', 'Repeat', -240, 100)
    fraction.operation = 'FRACT'
    tree.links.new(phase.outputs[0], fraction.inputs[0])
    band = node(tree, 'ShaderNodeValToRGB', 'Soft narrow highlight', -40, 100)
    band.color_ramp.elements[0].position = .0
    band.color_ramp.elements[0].color = (0, 0, 0, 1)
    band.color_ramp.elements[1].position = C['pulse']['width_fraction']
    band.color_ramp.elements[1].color = (0, 0, 0, 1)
    middle = band.color_ramp.elements.new(C['pulse']['width_fraction']/2)
    middle.color = (.24, .24, .24, 1)
    tree.links.new(fraction.outputs[0], band.inputs[0])
    gain = node(tree, 'ShaderNodeValue', 'Flow release gate', -40, 320)
    start, end = (85, 90) if shared else (67, 85)
    drive(gain.outputs[0], 'default_value', f'1 if {start} <= (frame-1)/{FPS} < {end} else 0')
    flowing = node(tree, 'ShaderNodeMath', 'Flow only after transfer', 230, 150)
    flowing.operation = 'MULTIPLY'
    tree.links.new(band.outputs[0], flowing.inputs[0])
    tree.links.new(gain.outputs[0], flowing.inputs[1])
    assembly_gate = node(tree, 'ShaderNodeValue', 'Installation gate', -40, -240)
    drive(assembly_gate.outputs[0], 'default_value', '0' if shared else f'1 if 29 <= (frame-1)/{FPS} < 45 else 0')
    assembling = node(tree, 'ShaderNodeMath', 'Visible assembly tip', 230, -200)
    assembling.operation = 'MULTIPLY'
    tree.links.new(assembly.outputs[0], assembling.inputs[0])
    tree.links.new(assembly_gate.outputs[0], assembling.inputs[1])
    combine = node(tree, 'ShaderNodeMath', 'Assembly or commissioned flow', 460)
    combine.operation = 'MAXIMUM'
    tree.links.new(flowing.outputs[0], combine.inputs[0])
    tree.links.new(assembling.outputs[0], combine.inputs[1])
    inside = node(tree, 'ShaderNodeMath', 'Respect the growing pipe end', 450, -220)
    inside.operation = 'LESS_THAN'
    tree.links.new(attr.outputs['Fac'], inside.inputs[0])
    tree.links.new(reveal.outputs[0], inside.inputs[1])
    mask = node(tree, 'ShaderNodeMath', 'No light beyond installed extent', 650)
    mask.operation = 'MULTIPLY'
    tree.links.new(combine.outputs[0], mask.inputs[0])
    tree.links.new(inside.outputs[0], mask.inputs[1])
    em = node(tree, 'ShaderNodeEmission', 'Subtle system-colored pulse', 650, 180)
    base = rgba(C['palette'][pipe['system']])
    em.inputs[0].default_value = tuple(min(1, x+.12) for x in base[:3])+(1,)
    em.inputs[1].default_value = .8
    trans = node(tree, 'ShaderNodeBsdfTransparent', 'Invisible between pulses', 650, -100)
    mix = node(tree, 'ShaderNodeMixShader', 'Pulse overlay', 900)
    tree.links.new(mask.outputs[0], mix.inputs[0])
    tree.links.new(trans.outputs[0], mix.inputs[1])
    tree.links.new(em.outputs[0], mix.inputs[2])
    out = node(tree, 'ShaderNodeOutputMaterial', 'Output', 1120)
    tree.links.new(mix.outputs[0], out.inputs[0])
    obj = new_mesh(scene, 'Studio pulse | '+pipe.name, vertices, faces, mat)
    obj.parent = pipe
    obj.visible_shadow = False
    for poly in obj.data.polygons:
        poly.use_smooth = True
    attribute = obj.data.attributes.new('studio_s', 'FLOAT', 'POINT')
    for entry, s in zip(attribute.data, distances):
        entry.value = s
    active = f'(29 <= (frame-1)/{FPS} < 45 or 67 <= (frame-1)/{FPS} < 85)' if not shared else f'(85 <= (frame-1)/{FPS} < 90)'
    drive(obj, 'hide_render', 'hidden or not '+active, [('hidden', pipe, 'hide_render')])
    tag(obj, 'directional_pulse', 'Arc-length presentation overlay; installation tip is not water flow. Commissioned motion starts only after depicted transfer.')


def geometry_digest(obj):
    if obj.type == 'CURVE':
        data = {'points': [[list(p.co) for p in spline.points] for spline in obj.data.splines], 'radius': obj.data.bevel_depth}
    elif obj.type == 'MESH':
        data = {'vertices': [list(v.co) for v in obj.data.vertices]}
    else:
        return None
    data['transform'] = [list(obj.location), list(obj.rotation_euler), list(obj.scale)]
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()


def camera_story(scene):
    """Continuous azimuth drift; smooth focus changes rather than abrupt cuts."""
    camera = scene.camera
    camera.animation_data_clear()
    camera.data.animation_data_clear()
    service = scene.objects['SVC-CW'].location.copy()
    kitchen = coord(next(e for e in G['elements'] if e['id']=='CW-04')['points'][-1])
    wide = Vector((-.8,.2,1.0))
    keys = [(8,wide,21,59),(18,wide,20.5,55),(22,kitchen.lerp(wide,.4),13.5,52),
            (26,kitchen.lerp(wide,.4),13.5,51),(30,wide,20.5,50),
            (47,wide,20.5,49),(54,service.lerp(wide,.18),9.5,49),
            (61,service.lerp(wide,.18),9.5,48),(68,wide,20.5,50),(85,wide,21,53)]
    for f in range(1,2161):
        t=(f-1)/24
        if t<=keys[0][0]:a=b=keys[0];u=0
        elif t>=keys[-1][0]:a=b=keys[-1];u=0
        else:
            a,b=next((a,b) for a,b in zip(keys,keys[1:]) if a[0]<=t<b[0])
            u=(t-a[0])/(b[0]-a[0]);u=u*u*(3-2*u)
        target=a[1].lerp(b[1],u)
        scale=a[2]*(1-u)+b[2]*u
        elevation=math.radians(a[3]*(1-u)+b[3]*u)
        azimuth=math.radians(-65+(max(8,min(85,t))-8)*.38)
        camera.location=target+30*Vector((math.cos(azimuth)*math.cos(elevation),math.sin(azimuth)*math.cos(elevation),math.sin(elevation)))
        camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler()
        camera.data.ortho_scale=scale
        camera.keyframe_insert('location',frame=f)
        camera.keyframe_insert('rotation_euler',frame=f)
        camera.data.keyframe_insert('ortho_scale',frame=f)
    scene['camera_story']='Continuous 0.38 degree/second azimuth drift. Smooth kitchen and service/test framing; no sudden cutover zoom.'


def isolation_icons(scene):
    mat=plain_principled('Proposed valve indicator',C['palette']['access'],.3,.6)
    for system in ['CW','HW','HWC']:
        point=scene.objects['SVC-'+system].location.copy()
        circle=[point+Vector((.10*math.cos(a*math.tau/24),.10*math.sin(a*math.tau/24),.12)) for a in range(25)]
        ring=new_curve(scene,'Studio proposed valve ring '+system,[circle],.009,mat)
        visibility(ring,58,64)
        tag(ring,'proposed_valve_icon','Illustrative isolation icon at an assumed service symbol. Actual valve locations and isolation capability require field verification.')
        handle=new_curve(scene,'Studio proposed valve handle '+system,[[(-.14,0,0),(.14,0,0)]],.014,mat)
        handle.location=point+Vector((0,0,.13))
        visibility(handle,58,64)
        for t,angle in [(58,0),(60.5,math.pi/2),(64,math.pi/2)]:
            handle.rotation_euler.z=angle
            handle.keyframe_insert('rotation_euler',frame=frame(t))
        tag(handle,'proposed_valve_icon',ring['basis'])


def upgrade_scene(scene, shared, hdri):
    bpy.context.window.scene = scene
    scene.frame_set(frame(88 if shared else 69))
    original = {o.name: geometry_digest(o) for o in scene.objects if o.get('element_id') and o.type in {'CURVE', 'MESH'}}
    configure(scene, hdri)
    lighting(scene, 1.32 if shared else G['display']['width_in']*.0254/12)
    mats = {system: pipe_material(system) for system in ['CW', 'HW', 'HWC']}
    neutral = plain_principled('Service symbols', '#607178', .32)
    original_objects = list(scene.objects)
    for obj in original_objects:
        if obj.type == 'FONT':
            drive(obj, 'hide_render', 'True')
            continue
        if obj.name.startswith(('Studio ground', 'Source drawing backing', 'Flow ', 'Shared flow ')):
            drive(obj, 'hide_render', 'True')
            continue
        if obj.name.startswith('P4.01 Unit B'):
            obj.data.materials.clear()
            obj.data.materials.append(blueprint_material())
            obj.visible_shadow = obj.visible_diffuse = obj.visible_glossy = False
            continue
        system = obj.get('system')
        if system in mats and obj.type in {'CURVE', 'MESH'}:
            obj.data.materials.clear()
            obj.data.materials.append(mats[system])
            if obj.type == 'CURVE':
                obj.data.bevel_resolution = 5
                joints(scene, obj, mats[system])
                pulse_overlay(scene, obj, shared)
        elif obj.type == 'MESH' and obj.get('element_id'):
            obj.data.materials.clear()
            obj.data.materials.append(neutral)
            bevel = obj.modifiers.new('Small presentation edge highlight', 'BEVEL')
            bevel.width, bevel.segments = .004, 3
    size = 24 if shared else 8
    z = -2.3 if shared else 0
    receiver = new_mesh(scene, 'Studio shadow receiver', [(-size, -size, z), (size, -size, z), (size, size, z), (-size, size, z)], [(0, 1, 2, 3)], receiver_material())
    receiver.is_shadow_catcher = True
    tag(receiver, 'shadow_catcher', 'Presentation receiver only; not an actual slab elevation.')
    if not shared:
        ghost_walls(scene)
        access_boxes(scene)
        camera_story(scene)
        isolation_icons(scene)
    for name, expected in original.items():
        assert geometry_digest(scene.objects[name]) == expected, name
    scene['studio_geometry_check'] = f'{len(original)} original objects retain centerlines/vertices, radius and local transforms.'
    return {'original_objects_unchanged': len(original), 'presentation_objects_added': len(scene.objects)-len(original_objects)}


def exterior(hdri):
    path = PROJECT.parents[1] / 'deliverables/highland-exterior/Highland-exterior.blend'
    with bpy.data.libraries.load(str(path), link=False) as (source, target):
        target.scenes = [source.scenes[0]]
    scene = target.scenes[0]
    scene.name = 'STUDIO - Exterior opening'
    configure(scene, hdri)
    scene.cycles.use_denoising = True
    scene.world.node_tree.nodes['Low-energy reflection environment'].inputs[1].default_value = .5
    for obj in scene.objects:
        if obj.name.startswith('caption') or obj.type == 'FONT':
            obj.hide_render = True
    camera = scene.camera
    camera.animation_data_clear()
    target = Vector((58, 70, 34))*.3048
    for t, pos in [(0, (220, -155, 32)), (4, (195, -130, 26))]:
        camera.location = Vector(pos)*.3048
        camera.rotation_euler = (target-camera.location).to_track_quat('-Z', 'Y').to_euler()
        camera.keyframe_insert('location', frame=frame(t))
        camera.keyframe_insert('rotation_euler', frame=frame(t))
    scene['opening_basis'] = C['opening']['note']
    return scene


def main():
    argv = sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else sys.argv[1:]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--hdri', type=Path, help='Optional licensed latitude-longitude HDR/EXR')
    args = parser.parse_args(argv)
    source = PROJECT / 'animation-90s/Highland-repipe-90s.blend'
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    bpy.ops.wm.open_mainfile(filepath=str(source))
    bpy.ops.file.make_paths_absolute()
    hdri = bpy.data.images.load(str(args.hdri.resolve())) if args.hdri else studio_hdri()
    results = {}
    for name, shared in [('3D - Shared distribution', True), ('3D - Unit B installation', False)]:
        scene = bpy.data.scenes[name]
        results[name] = upgrade_scene(scene, shared, hdri)
    ext = exterior(hdri)
    # Keep only the three source-derived 3D scenes. The exact-color editorial
    # composite is intentionally downstream of AgX, outside the old VSE master.
    keep = {'3D - Shared distribution', '3D - Unit B installation', ext.name}
    for scene in list(bpy.data.scenes):
        if scene.name not in keep:
            bpy.data.scenes.remove(scene)
    bpy.context.window.scene = ext
    ext.frame_set(1)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'Highland-studio-upgrade.blend'))
    assert hashlib.sha256(source.read_bytes()).hexdigest() == source_hash
    results['source_animation_sha256'] = source_hash
    results['source_animation_unchanged'] = True
    results['background_method'] = 'Exact sRGB #F7F6F2 composited after AgX; PNG regions outside geometry/shadows are exact.'
    (OUT / 'build-validation.json').write_text(json.dumps(results, indent=2)+'\n')
    print('STUDIO_BUILD_PASS', results, flush=True)


if __name__ == '__main__':
    main()
