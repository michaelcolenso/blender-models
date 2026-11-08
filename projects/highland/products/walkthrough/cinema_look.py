"""Film v2 look upgrades for the Highland cinematic film (bpy 5.0.1).

cinema.prepare() calls these after its own dusk/interior/x-ray passes, on the scene it has just built
from code. The saved Highland-cinema.blend is regenerated on every prepare, so nothing here edits a
hand-tuned file. Before a material is changed, its node tree is copied to a fake-user material named
'<name> / v1 backup' (see backup()), so the previous shader can be compared in the .blend.

Each upgrade has a CONFIG dict at the top of its section. Everything here is a presentation
treatment: lamp colours, window occupancy, blinds, bevels and section graphics are illustrative,
not documented conditions.

Brief-to-code notes (Blender 5.0.1, checked against this build):
- `scene.use_nodes`/`scene.node_tree`, `glare.glare_type` and `lens.use_projector` are 4.x APIs.
  The compositor here is `scene.compositing_node_group`; glare and lens settings are input sockets.
- Musgrave was merged into Noise in Blender 4.1; the micro-roughness uses Noise plus Voronoi.
- Fog glow, lens dispersion and film grain already run once, in cinema_finish.grade(), on the
  rendered frames. Running them again in the compositor would double them, so color() leaves them alone.
"""
import math

import bpy
from mathutils import Vector

I = .0254
EXTERIOR_LAST = 146  # native frames 1-146 are the only ones that show the exterior (see cinema.exterior_only)


def srgb(hex_code):
    """'#E6B87A' -> linear RGB."""
    c = [int(hex_code.lstrip('#')[k:k+2], 16)/255 for k in (0, 2, 4)]
    return tuple(v/12.92 if v <= .04045 else ((v+.055)/1.055)**2.4 for v in c)


def backup(mat):
    """Copy the material once, before its first v2 change, as a fake-user '<name> / v1 backup'."""
    name = mat.name+' / v1 backup'
    if name not in bpy.data.materials:
        copy = mat.copy(); copy.name = name; copy.use_fake_user = True
    return mat


def bsdf(mat):
    return next((n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)


def source(sock):
    """Linked output feeding a socket, or None."""
    return sock.links[0].from_socket if sock.is_linked else None


def exterior_keys(obj):
    for f, v in [(1, False), (EXTERIOR_LAST, False), (EXTERIOR_LAST+1, True)]:
        obj.hide_render = v; obj.keyframe_insert('hide_render', frame=f)
    return obj


# ---------------------------------------------------------------------------------------------
# Task 1: color management
# ---------------------------------------------------------------------------------------------
COLOR = {
    'view_transform': 'AgX',
    # Medium High Contrast was tried against the finish's own S-curve and crushed the corridor
    # shadows; Base Contrast plus the finish curve gives the same contrast with shadow detail.
    'look': 'AgX - Base Contrast',
    'exposure': 0.0,
    'gamma': 1.0,
}


def color(scene, cfg=COLOR):
    vs = scene.view_settings
    vs.view_transform = cfg['view_transform'] if cfg['view_transform'] in [
        i.identifier for i in vs.bl_rna.properties['view_transform'].enum_items] else 'Filmic'
    vs.look = cfg['look'] if vs.view_transform == 'AgX' else 'None'
    vs.exposure = cfg['exposure']; vs.gamma = cfg['gamma']


# ---------------------------------------------------------------------------------------------
# Task 2: blue-hour world, street lamps and atmosphere
# ---------------------------------------------------------------------------------------------
BLUE_HOUR = {
    'hdri': None,                # optional path to a blue-hour HDRI; None keeps the scene's tinted sky HDRI
    'hdri_rotation_deg': 0.0,
    'sky_zenith': (.018, .040, .150),    # camera-visible sky, linear
    'sky_horizon': (.085, .105, .230),   # blue-hour horizon, a touch lighter than the zenith
    'sky_cloud_mix': .55,                # how much the HDRI's clouds modulate the visible gradient
    'sky_camera_strength': 1.0,
    'lamp_kelvin': 2900,
    'lamp_point_w': 220,                 # small omni share for the lamp head and nearby facade
    'lamp_spot_w': 1100,                 # downward pool on the pavement
    'lamp_spot_deg': 118, 'lamp_spot_blend': .6, 'lamp_radius_m': .22,
    'volume_density': .0015, 'volume_anisotropy': .6,
    # Streetscape box in plan inches (exterior study coordinates): sidewalk, street and entry.
    'volume_box_in': (1480, 2440, -300, 2500, 60, 1500),  # top above shot 09's roof-descent start
}


def blue_hour(scene, cfg=BLUE_HOUR):
    world = scene.world; n, l = world.node_tree.nodes, world.node_tree.links
    env = next(x for x in n if x.type == 'TEX_ENVIRONMENT')
    bg = next(x for x in n if x.type == 'BACKGROUND')
    out = next(x for x in n if x.type == 'OUTPUT_WORLD')
    if cfg['hdri']:
        env.image = bpy.data.images.load(str(cfg['hdri']), check_existing=True)
    mapping = next((x for x in n if x.type == 'MAPPING'), None)
    if mapping:
        mapping.inputs['Rotation'].default_value[2] = math.radians(cfg['hdri_rotation_deg'])
    # Camera rays see a blue-hour gradient carrying the HDRI's clouds; every other ray keeps the
    # existing tinted HDRI as the light. The two are graded independently.
    coord = n.new('ShaderNodeTexCoord'); sep = n.new('ShaderNodeSeparateXYZ')
    l.new(coord.outputs['Generated'], sep.inputs[0])
    ramp = n.new('ShaderNodeValToRGB'); l.new(sep.outputs['Z'], ramp.inputs['Fac'])
    ramp.color_ramp.interpolation = 'EASE'
    ramp.color_ramp.elements[0].position = 0.; ramp.color_ramp.elements[0].color = (*cfg['sky_horizon'], 1)
    ramp.color_ramp.elements[1].position = .55; ramp.color_ramp.elements[1].color = (*cfg['sky_zenith'], 1)
    lum = n.new('ShaderNodeRGBToBW'); l.new(env.outputs['Color'], lum.inputs['Color'])
    cloud = n.new('ShaderNodeMapRange'); l.new(lum.outputs['Val'], cloud.inputs['Value'])
    cloud.inputs['To Min'].default_value = 1-cfg['sky_cloud_mix']; cloud.inputs['To Max'].default_value = 1+cfg['sky_cloud_mix']
    sky = n.new('ShaderNodeMix'); sky.data_type = 'RGBA'; sky.blend_type = 'MULTIPLY'; sky.inputs['Factor'].default_value = 1
    l.new(ramp.outputs['Color'], sky.inputs['A']); l.new(cloud.outputs['Result'], sky.inputs['B'])
    cam_bg = n.new('ShaderNodeBackground'); cam_bg.name = 'Blue hour / camera sky'
    l.new(sky.outputs['Result'], cam_bg.inputs['Color']); cam_bg.inputs['Strength'].default_value = cfg['sky_camera_strength']
    bg.name = 'Blue hour / environment light'
    path = n.new('ShaderNodeLightPath'); mix = n.new('ShaderNodeMixShader')
    l.new(path.outputs['Is Camera Ray'], mix.inputs['Fac'])
    l.new(bg.outputs['Background'], mix.inputs[1]); l.new(cam_bg.outputs['Background'], mix.inputs[2])
    l.new(mix.outputs['Shader'], out.inputs['Surface'])

    # Street lamps: 2900 K blackbody bulbs, a soft omni share and a downward pool.
    for name in ('street_lamp_01_bulb', 'street_lamp_01_glass'):
        mat = bpy.data.materials.get(name)
        if not mat:
            continue
        backup(mat); b = bsdf(mat)
        bb = mat.node_tree.nodes.new('ShaderNodeBlackbody'); bb.inputs['Temperature'].default_value = cfg['lamp_kelvin']
        mat.node_tree.links.new(bb.outputs['Color'], b.inputs['Emission Color'])
    lamps = [o for o in scene.objects if o.type == 'LIGHT' and o.name.startswith('Street light pool')]
    col = lamps[0].users_collection[0] if lamps else scene.collection
    for o in lamps:
        d = o.data; d.energy = cfg['lamp_point_w']; d.shadow_soft_size = cfg['lamp_radius_m']
        d.use_temperature = True; d.temperature = cfg['lamp_kelvin']; d.color = (1, 1, 1)
        s = bpy.data.lights.new('Street lamp downward pool', 'SPOT')
        s.energy = cfg['lamp_spot_w']; s.spot_size = math.radians(cfg['lamp_spot_deg']); s.spot_blend = cfg['lamp_spot_blend']
        s.shadow_soft_size = cfg['lamp_radius_m']; s.use_temperature = True; s.temperature = cfg['lamp_kelvin']
        so = bpy.data.objects.new(s.name, s); col.objects.link(so)
        so.location = o.location+Vector((0, 0, -.05)); so.rotation_euler = (0, 0, 0)  # spot points down -Z
        so.visible_camera = False; so.visible_glossy = False
        exterior_keys(so)

    # Thin homogeneous atmosphere over the streetscape, exterior frames only.
    x0, x1, y0, y1, z0, z1 = cfg['volume_box_in']
    mesh = bpy.data.meshes.new('Streetscape atmosphere')
    vs = [(x*I, y*I, z*I) for z in (z0, z1) for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1))]
    mesh.from_pydata(vs, [], [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)])
    mat = bpy.data.materials.new('Streetscape atmosphere'); nt = mat.node_tree
    nt.nodes.remove(bsdf(mat))
    vol = nt.nodes.new('ShaderNodeVolumePrincipled')
    vol.inputs['Density'].default_value = cfg['volume_density']; vol.inputs['Anisotropy'].default_value = cfg['volume_anisotropy']
    vol.inputs['Color'].default_value = (.85, .88, 1, 1)
    nt.links.new(vol.outputs['Volume'], next(x for x in nt.nodes if x.type == 'OUTPUT_MATERIAL').inputs['Volume'])
    mesh.materials.append(mat)
    box = bpy.data.objects.new('Streetscape atmosphere (illustrative)', mesh); col.objects.link(box)
    box.visible_shadow = False
    exterior_keys(box)
    return box


# ---------------------------------------------------------------------------------------------
# Task 3: lit apartment windows
# ---------------------------------------------------------------------------------------------
WINDOWS = {
    'recess_prefix': 'Warm apartment recess ',
    'curtain_name': 'Apartment curtain fold',
    'kelvin': (2500, 3800),
    # Occupancy tiers on the per-window seed: below 'off' dark, below 'bright' medium, else bright.
    'off': .28, 'bright': .80,
    'strength_off': .03, 'strength_medium': 1.3, 'strength_bright': 2.6,
    'blinds_share': .55,         # share of lit windows with blinds lowered
    'blinds_pitch_m': .035, 'blinds_transmission': .35,
    'glass_ior': 1.52, 'glass_roughness': .04,
    'curtain_glow': .35,         # linen glow relative to the window behind it
}


def windows(scene, cfg=WINDOWS):
    """Per-window seeds as an object attribute shared by a recess, its curtains and its glass, so
    one window reads as one room: same colour temperature, same occupancy, blinds at one height."""
    recesses = [o for o in scene.objects if o.name.startswith(cfg['recess_prefix'])]
    if not recesses:
        return 0
    for j, o in enumerate(sorted(recesses, key=lambda o: o.name)):
        # Deterministic, well spread seeds (golden-ratio sequence) instead of Object Info > Random,
        # because the curtains are separate objects that must share their window's seed.
        o['window_seed'] = (j*.6180339887+.31) % 1
    centers = [(o, o.matrix_world@(sum((Vector(c) for c in o.bound_box), Vector())/8)) for o in recesses]
    for c in (o for o in scene.objects if o.name.startswith(cfg['curtain_name'])):
        p = c.matrix_world@(sum((Vector(v) for v in c.bound_box), Vector())/8)
        c['window_seed'] = min(centers, key=lambda oc: (oc[1]-p).length)[0]['window_seed']
    for o in recesses:
        glass = bpy.data.objects.get(o.name[len(cfg['recess_prefix']):])
        if glass:
            glass['window_seed'] = o['window_seed']
            for m in glass.data.materials:
                b = bsdf(m)
                b.inputs['IOR'].default_value = cfg['glass_ior']; b.inputs['Roughness'].default_value = cfg['glass_roughness']

    def seed_nodes(nt):
        attr = nt.nodes.new('ShaderNodeAttribute'); attr.attribute_type = 'OBJECT'; attr.attribute_name = 'window_seed'
        return attr.outputs['Fac']

    def op(nt, kind, a, b=None, clamp=False):
        m = nt.nodes.new('ShaderNodeMath'); m.operation = kind; m.use_clamp = clamp
        for k, v in enumerate((a, b)):
            if v is None:
                continue
            if isinstance(v, (int, float)):
                m.inputs[k].default_value = v
            else:
                nt.links.new(v, m.inputs[k])
        return m.outputs[0]

    def strength(nt, seed):
        """Stepped occupancy: off / medium / bright."""
        lo = op(nt, 'GREATER_THAN', seed, cfg['off'])
        hi = op(nt, 'GREATER_THAN', seed, cfg['bright'])
        s = op(nt, 'ADD', op(nt, 'MULTIPLY', lo, cfg['strength_medium']-cfg['strength_off']),
                 op(nt, 'MULTIPLY', hi, cfg['strength_bright']-cfg['strength_medium']))
        return op(nt, 'ADD', s, cfg['strength_off'])

    def kelvin(nt, seed):
        # Decorrelate colour from occupancy with a second hash of the seed.
        h = op(nt, 'FRACT', op(nt, 'MULTIPLY', seed, 7.31))
        k = nt.nodes.new('ShaderNodeMapRange'); nt.links.new(h, k.inputs['Value'])
        k.inputs['To Min'].default_value, k.inputs['To Max'].default_value = cfg['kelvin']
        bb = nt.nodes.new('ShaderNodeBlackbody'); nt.links.new(k.outputs['Result'], bb.inputs['Temperature'])
        return bb.outputs['Color']

    # Recess back panel: colour, occupancy and lowered blinds.
    mat = backup(bpy.data.materials['Apartment warm interior']); nt = mat.node_tree; b = bsdf(mat)
    seed = seed_nodes(nt)
    s = strength(nt, seed)
    coord = nt.nodes.new('ShaderNodeTexCoord'); sep = nt.nodes.new('ShaderNodeSeparateXYZ')
    nt.links.new(coord.outputs['Object'], sep.inputs[0])
    wave = nt.nodes.new('ShaderNodeTexWave'); wave.wave_type = 'BANDS'; wave.bands_direction = 'Z'
    # Wave bands run sin(20*scale*z): one slat per blinds_pitch_m.
    wave.inputs['Scale'].default_value = 2*math.pi/(20*cfg['blinds_pitch_m'])
    nt.links.new(coord.outputs['Object'], wave.inputs['Vector'])
    slats = nt.nodes.new('ShaderNodeMapRange'); nt.links.new(wave.outputs['Fac'], slats.inputs['Value'])
    slats.inputs['To Min'].default_value = cfg['blinds_transmission']; slats.inputs['To Max'].default_value = 1
    # Blinds hang from the head of the window down to a per-window height, measured in the same
    # object space as the Object texture coordinate (local bounds).
    for o in recesses:
        zs = [v[2] for v in o.bound_box]
        o['window_z'] = (min(zs), max(zs), 0.)
    zattr = nt.nodes.new('ShaderNodeAttribute'); zattr.attribute_type = 'OBJECT'; zattr.attribute_name = 'window_z'
    zv = nt.nodes.new('ShaderNodeSeparateXYZ'); nt.links.new(zattr.outputs['Vector'], zv.inputs[0])
    h2 = op(nt, 'FRACT', op(nt, 'MULTIPLY', seed, 3.97))
    drop = op(nt, 'MULTIPLY', h2, .85)                              # 0-85% of the window height
    height = op(nt, 'SUBTRACT', zv.outputs['Y'], zv.outputs['X'])
    stop = op(nt, 'SUBTRACT', zv.outputs['Y'], op(nt, 'MULTIPLY', height, drop))
    covered = op(nt, 'GREATER_THAN', sep.outputs['Z'], stop)
    has = op(nt, 'LESS_THAN', op(nt, 'FRACT', op(nt, 'MULTIPLY', seed, 5.23)), cfg['blinds_share'])
    blind = op(nt, 'MULTIPLY', covered, has)
    # emission factor = 1 where open, slat pattern where covered
    open_part = op(nt, 'SUBTRACT', 1., blind)
    shade = nt.nodes.new('ShaderNodeMath'); shade.operation = 'MULTIPLY_ADD'
    nt.links.new(blind, shade.inputs[0]); nt.links.new(slats.outputs['Result'], shade.inputs[1]); nt.links.new(open_part, shade.inputs[2])
    # Brighter toward the ceiling, as from a ceiling lamp (kept from the 2026-11-08 review pass).
    gen = nt.nodes.new('ShaderNodeTexCoord'); gz = nt.nodes.new('ShaderNodeSeparateXYZ'); nt.links.new(gen.outputs['Generated'], gz.inputs[0])
    fall = nt.nodes.new('ShaderNodeMapRange'); fall.inputs['To Min'].default_value, fall.inputs['To Max'].default_value = .6, 1.15
    nt.links.new(gz.outputs['Z'], fall.inputs['Value'])
    nt.links.new(op(nt, 'MULTIPLY', op(nt, 'MULTIPLY', s, shade.outputs[0]), fall.outputs['Result']), b.inputs['Emission Strength'])
    nt.links.new(kelvin(nt, seed), b.inputs['Emission Color'])

    # Curtains glow with their own window: same colour, scaled occupancy.
    mat = backup(bpy.data.materials['Apartment linen']); nt = mat.node_tree; b = bsdf(mat)
    seed = seed_nodes(nt)
    nt.links.new(op(nt, 'MULTIPLY', strength(nt, seed), cfg['curtain_glow']), b.inputs['Emission Strength'])
    tint = nt.nodes.new('ShaderNodeMix'); tint.data_type = 'RGBA'; tint.blend_type = 'MULTIPLY'; tint.inputs['Factor'].default_value = 1
    tint.inputs['B'].default_value = (1, .85, .7, 1)
    nt.links.new(kelvin(nt, seed), tint.inputs['A']); nt.links.new(tint.outputs['Result'], b.inputs['Emission Color'])
    return len(recesses)


# ---------------------------------------------------------------------------------------------
# Task 4: interior micro-bevels, micro-roughness and entry glazing
# ---------------------------------------------------------------------------------------------
SURFACES = {
    # material: (bevel radius m or None, roughness variation +-)
    'Satin walnut doors': (.003, .03),          # residence doors, cab panels and the lobby slats
    'Dark walnut frames': (.003, .03),
    'Brushed champagne brass': (.0015, None),   # metals: roughness noise smears their reflections
    'Satin elevator bronze': (.002, None),
    'Gallery plaster': (.004, .06),             # wall corners and returns
    'Warm plaster ceiling': (None, .04),
    'Honed lobby stone': (None, .04),
    'Elevator solid stone floor': (None, .05),
    'Woven corridor carpet': (None, .04),
    'Charcoal ceramic planters': (.008, .05),
    'concrete': (.008, .06),                    # entry steps, edges and site concrete
    'mid_century_lounge_chair': (None, .05),    # leather chairs: scanned geometry, roughness only
    'Recessed entry mat': (None, .03),
}
BEVEL_SAMPLES = 4
ENTRY_GLASS = {'material': 'Entry glass', 'ior': 1.52, 'roughness': 0., 'tint': (.93, .97, .955),
               'edge_tint': (.55, .74, .70), 'edge_blend': .35}


def surfaces(scene, cfg=SURFACES):
    for name, (radius, amp) in cfg.items():
        mat = bpy.data.materials.get(name)
        if not mat or not mat.node_tree:
            continue
        backup(mat); nt = mat.node_tree; n, l = nt.nodes, nt.links
        for b in [x for x in n if x.type == 'BSDF_PRINCIPLED']:
            x, y = b.location
            if radius and not any(x.type == 'BEVEL' for x in n):
                bev = n.new('ShaderNodeBevel'); bev.samples = BEVEL_SAMPLES; bev.location = (x-260, y-420)
                bev.inputs['Radius'].default_value = radius
                # The bevel goes underneath any bump: Cycles' Bevel output ignores detail fed into its
                # Normal input, so bevel -> Principled would wipe out the wood grain. Bevel -> Bump keeps both.
                old = source(b.inputs['Normal'])
                if old and old.node.type == 'BUMP' and not old.node.inputs['Normal'].is_linked:
                    l.new(bev.outputs['Normal'], old.node.inputs['Normal'])
                elif old:  # normal map or other: keep it, skip the bevel rather than lose the detail
                    n.remove(bev)
                else:
                    l.new(bev.outputs['Normal'], b.inputs['Normal'])
            if amp:
                coord = n.new('ShaderNodeTexCoord')
                noise = n.new('ShaderNodeTexNoise'); noise.inputs['Scale'].default_value = 7
                noise.inputs['Detail'].default_value = 6; noise.inputs['Roughness'].default_value = .55
                vor = n.new('ShaderNodeTexVoronoi'); vor.feature = 'SMOOTH_F1'; vor.inputs['Scale'].default_value = 40
                for t in (noise, vor):
                    l.new(coord.outputs['Object'], t.inputs['Vector'])
                blend = n.new('ShaderNodeMix'); blend.data_type = 'FLOAT'; blend.inputs['Factor'].default_value = .35
                l.new(noise.outputs['Fac'], blend.inputs['A']); l.new(vor.outputs['Distance'], blend.inputs['B'])
                # Narrow band around the mean -> +-amp, so the scanned roughness map stays in charge. Glossy
                # walnut and metals take half the amplitude: at +-.06 they read as large smudges.
                band = n.new('ShaderNodeMapRange'); l.new(blend.outputs['Result'], band.inputs['Value'])
                band.inputs['From Min'].default_value = .3; band.inputs['From Max'].default_value = .7
                band.inputs['To Min'].default_value = -amp; band.inputs['To Max'].default_value = amp
                add = n.new('ShaderNodeMath'); add.operation = 'ADD'; add.use_clamp = True
                old = source(b.inputs['Roughness'])
                if old:
                    l.new(old, add.inputs[0])
                else:
                    add.inputs[0].default_value = b.inputs['Roughness'].default_value
                l.new(band.outputs['Result'], add.inputs[1]); l.new(add.outputs[0], b.inputs['Roughness'])
    # Entry glazing: clear low-iron-ish glass, green-blue at grazing angles where the path through
    # the edge is longest. Reflections come from the Principled Fresnel at IOR 1.52.
    g = ENTRY_GLASS; mat = bpy.data.materials.get(g['material'])
    if mat:
        backup(mat); nt = mat.node_tree; b = bsdf(mat)
        b.inputs['IOR'].default_value = g['ior']; b.inputs['Roughness'].default_value = g['roughness']
        lw = nt.nodes.new('ShaderNodeLayerWeight'); lw.inputs['Blend'].default_value = g['edge_blend']
        mix = nt.nodes.new('ShaderNodeMix'); mix.data_type = 'RGBA'
        mix.inputs['A'].default_value = (*g['tint'], 1); mix.inputs['B'].default_value = (*g['edge_tint'], 1)
        nt.links.new(lw.outputs['Facing'], mix.inputs['Factor']); nt.links.new(mix.outputs['Result'], b.inputs['Base Color'])


# ---------------------------------------------------------------------------------------------
# Task 5: two-tier x-ray section graphics
# ---------------------------------------------------------------------------------------------
SECTION = {
    'primary_keywords': ('floor', 'ceiling', 'slab', 'shaft', 'roof'),
    'primary_color': '#E6B87A', 'primary_strength': 2.5, 'primary_wire_m': .0045, 'shaft_wire_m': .007,
    'secondary_color': '#A67C52', 'secondary_strength': 1.6, 'secondary_opacity': .35, 'secondary_wire_m': .0018,
    # Translucent fill on horizontal faces of the ghosted floors/ceilings so R1 and R2 read as volumes.
    'fill_materials': {'Woven corridor carpet': .13, 'Honed lobby stone': .13, 'Warm plaster ceiling': .08},
    'fill_color': '#E6B87A', 'fill_strength': .35,
}


def section(scene, cfg=SECTION):
    primary = backup(bpy.data.materials['Section brass edges'])
    b = bsdf(primary)
    b.inputs['Emission Color'].default_value = (*srgb(cfg['primary_color']), 1)
    b.inputs['Emission Strength'].default_value = cfg['primary_strength']
    b.inputs['Base Color'].default_value = (*srgb(cfg['primary_color']), 1)
    secondary = bpy.data.materials.new('Section bronze partition lines'); nt = secondary.node_tree
    nt.nodes.remove(bsdf(secondary))
    em = nt.nodes.new('ShaderNodeEmission')
    em.inputs['Color'].default_value = (*srgb(cfg['secondary_color']), 1); em.inputs['Strength'].default_value = cfg['secondary_strength']
    tr = nt.nodes.new('ShaderNodeBsdfTransparent'); mix = nt.nodes.new('ShaderNodeMixShader')
    mix.inputs['Fac'].default_value = cfg['secondary_opacity']
    nt.links.new(tr.outputs[0], mix.inputs[1]); nt.links.new(em.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], next(x for x in nt.nodes if x.type == 'OUTPUT_MATERIAL').inputs['Surface'])
    counts = {'primary': 0, 'secondary': 0}
    for o in scene.objects:
        is_shaft = o.name == 'Elevator shaft / section reference'
        if not (o.name.endswith(' / section edges') or is_shaft):
            continue
        tier = 'primary' if is_shaft or any(k in o.name.lower() for k in cfg['primary_keywords']) else 'secondary'
        counts[tier] += 1
        if tier == 'secondary':
            o.data.materials.clear(); o.data.materials.append(secondary)
        for m in o.modifiers:
            if m.type == 'WIREFRAME':
                m.thickness = cfg['shaft_wire_m'] if is_shaft else cfg[tier+'_wire_m']
    for name, alpha in cfg['fill_materials'].items():
        mat = bpy.data.materials.get(name)
        if not mat:
            continue
        nt = mat.node_tree; n, l = nt.nodes, nt.links
        wrap = n.get('Elevator architectural section')
        xray = source(wrap.inputs[2])
        geo = n.new('ShaderNodeNewGeometry'); sep = n.new('ShaderNodeSeparateXYZ'); l.new(geo.outputs['Normal'], sep.inputs[0])
        up = n.new('ShaderNodeMath'); up.operation = 'ABSOLUTE'; l.new(sep.outputs['Z'], up.inputs[0])
        flat = n.new('ShaderNodeMath'); flat.operation = 'GREATER_THAN'; flat.inputs[1].default_value = .7; l.new(up.outputs[0], flat.inputs[0])
        fac = n.new('ShaderNodeMath'); fac.operation = 'MULTIPLY'; fac.inputs[1].default_value = alpha; l.new(flat.outputs[0], fac.inputs[0])
        em = n.new('ShaderNodeEmission'); em.inputs['Color'].default_value = (*srgb(cfg['fill_color']), 1)
        em.inputs['Strength'].default_value = cfg['fill_strength']
        fill = n.new('ShaderNodeMixShader'); l.new(fac.outputs[0], fill.inputs['Fac'])
        l.new(xray, fill.inputs[1]); l.new(em.outputs[0], fill.inputs[2]); l.new(fill.outputs[0], wrap.inputs[2])
    return counts


def apply(scene):
    color(scene)
    blue_hour(scene)
    lit = windows(scene)
    surfaces(scene)
    tiers = section(scene)
    scene['cinema_v2'] = f'look v2: blue-hour world split, 2900 K lamps + atmosphere, {lit} varied windows, bevels, ' \
                         f'micro-roughness, entry glass, section tiers {tiers}'
    print('LOOK v2', scene['cinema_v2'], flush=True)
