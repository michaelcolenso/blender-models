"""Photographic presentation pass, preserving the drawing-study architecture.

Run with the repository's bpy 5.0.1 Python. No network, add-ons or external assets
are needed. Presentation geometry and lighting are explicitly assumed.
"""
import argparse
import hashlib
import json
import math
import random
import time
from pathlib import Path

import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
import sys
CONFIG_PATH=Path(sys.argv[sys.argv.index('--config')+1]) if '--config' in sys.argv else HERE/'scene.json'
OUT = Path(sys.argv[sys.argv.index('--output-dir')+1]) if '--output-dir' in sys.argv else ROOT / 'deliverables/highland-cinematic'
OUT.mkdir(parents=True, exist_ok=True)
CFG = json.loads(CONFIG_PATH.read_text())
S = json.loads((ROOT / CFG['base_spec']).read_text())
I = .0254
RNG = random.Random(CFG['seed'])
P = argparse.ArgumentParser()
P.add_argument('--preview', action='store_true')
P.add_argument('--build-only', action='store_true')
P.add_argument('--width', type=int)
P.add_argument('--samples', type=int)
P.add_argument('--config')
P.add_argument('--output-dir')
ARGS = P.parse_args()
START = time.monotonic()
bpy.context.preferences.filepaths.use_scripts_auto_execute = False
bpy.ops.wm.open_mainfile(filepath=str(ROOT / CFG['base_scene']), load_ui=False, use_scripts=False)
SCENE = bpy.context.scene


def architecture_hash():
    """Protect the source-derived building from a presentation-only mutation."""
    digest = hashlib.sha256()
    inventory = {}
    for cname in ('Envelope', 'Glazing', 'Balconies', 'Roof'):
        for o in sorted(bpy.data.collections[cname].objects, key=lambda o: o.name):
            if o.type != 'MESH':
                continue
            assert o.get('source') and o.get('basis') and o.get('status')
            record = [o.name, list(o.matrix_world), [list(v.co) for v in o.data.vertices], [list(p.vertices) for p in o.data.polygons]]
            # Matrix rows need ordinary lists before JSON serialization.
            record[1] = [list(row) for row in o.matrix_world]
            digest.update(json.dumps(record, separators=(',', ':')).encode())
            inventory[o.name] = len(o.data.vertices)
    return digest.hexdigest(), inventory


BASE_HASH, BASE_INVENTORY = architecture_hash()
for o in list(SCENE.objects):
    if o.name.startswith('caption') or o.type == 'LIGHT':
        bpy.data.objects.remove(o, do_unlink=True)
    elif o.name.startswith(('tree-', 'tree-trunk-', 'south-hedge-')):
        bpy.data.objects.remove(o, do_unlink=True)

COLS = {}
for name in ('Presentation / room dressing', 'Presentation / botanical', 'Presentation / street details', 'Presentation / lighting', 'Presentation / typography'):
    c = bpy.data.collections.new(name)
    SCENE.collection.children.link(c)
    COLS[name.split(' / ')[1]] = c


def tag(o, group):
    o['status'] = 'assumed'
    o['source'] = 'Owner photographs / presentation specification scene.json'
    o['basis'] = CFG['presentation_basis']
    o['presentation_group'] = group
    return o


def mesh(name, vs, fs, material, group='street details'):
    data = bpy.data.meshes.new(name)
    data.from_pydata(vs, [], fs)
    data.update()
    ob = bpy.data.objects.new(name, data)
    COLS[group].objects.link(ob)
    if material:
        data.materials.append(material)
    return tag(ob, group)


FACES = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]


def box(name, center, size, material, group='street details', bevel=0):
    c = Vector(center)
    x, y, z = [v / 2 for v in size]
    vs = [c + Vector(p) for p in [(-x,-y,-z),(x,-y,-z),(x,y,-z),(-x,y,-z),(-x,-y,z),(x,-y,z),(x,y,z),(-x,y,z)]]
    ob = mesh(name, vs, FACES, material, group)
    if bevel:
        mod = ob.modifiers.new('Small presentation edge radius', 'BEVEL')
        mod.width = bevel
        mod.segments = 2
    return ob


def material(name, color, rough=.5, metal=0, emission=0):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    nodes = m.node_tree.nodes
    nodes.clear()
    out = nodes.new('ShaderNodeOutputMaterial')
    bs = nodes.new('ShaderNodeBsdfPrincipled')
    bs.inputs['Base Color'].default_value = (*color, 1)
    bs.inputs['Roughness'].default_value = rough
    bs.inputs['Metallic'].default_value = metal
    if emission:
        bs.inputs['Emission Color'].default_value = (*color, 1)
        bs.inputs['Emission Strength'].default_value = emission
    m.node_tree.links.new(bs.outputs[0], out.inputs['Surface'])
    m.diffuse_color = (*color, 1)
    return m, bs


def texture_noise(m, scale):
    n, l = m.node_tree.nodes, m.node_tree.links
    coords = n.new('ShaderNodeTexCoord')
    noise = n.new('ShaderNodeTexNoise')
    noise.inputs['Scale'].default_value = scale
    noise.inputs['Detail'].default_value = 3
    l.new(coords.outputs['Object'], noise.inputs['Vector'])
    return noise


def detail_bump(m, bs, scale=150, strength=.15, distance=.001):
    noise = texture_noise(m, scale)
    bump = m.node_tree.nodes.new('ShaderNodeBump')
    bump.inputs['Strength'].default_value = strength
    bump.inputs['Distance'].default_value = distance
    m.node_tree.links.new(noise.outputs['Fac'], bump.inputs['Height'])
    m.node_tree.links.new(bump.outputs[0], bs.inputs['Normal'])


# Brick uses world position, so courses are continuous across separate wall pieces.
for axis in ('x', 'y'):
    m, bs = material('brick-' + axis, (.20,.064,.034), .78)
    n, l = m.node_tree.nodes, m.node_tree.links
    geom = n.new('ShaderNodeNewGeometry')
    sep = n.new('ShaderNodeSeparateXYZ')
    comb = n.new('ShaderNodeCombineXYZ')
    l.new(geom.outputs['Position'], sep.inputs[0])
    l.new(sep.outputs[axis.upper()], comb.inputs['X'])
    l.new(sep.outputs['Z'], comb.inputs['Y'])
    brick = n.new('ShaderNodeTexBrick')
    brick.offset = .5
    brick.inputs['Scale'].default_value = 1
    brick.inputs['Brick Width'].default_value = .203
    brick.inputs['Row Height'].default_value = .067
    brick.inputs['Mortar Size'].default_value = .0028
    brick.inputs['Mortar Smooth'].default_value = .0015
    brick.inputs['Color1'].default_value = (.245,.078,.042,1)
    brick.inputs['Color2'].default_value = (.105,.034,.023,1)
    brick.inputs['Mortar'].default_value = (.09,.082,.067,1)
    l.new(comb.outputs[0], brick.inputs['Vector'])
    noise = texture_noise(m, 75)
    mix = n.new('ShaderNodeMixRGB')
    mix.blend_type = 'MULTIPLY'
    mix.inputs[0].default_value = .22
    l.new(brick.outputs['Color'], mix.inputs[1])
    l.new(noise.outputs['Fac'], mix.inputs[2])
    l.new(mix.outputs[0], bs.inputs['Base Color'])
    mortar = n.new('ShaderNodeBump')
    mortar.invert = True
    mortar.inputs['Distance'].default_value = .003
    mortar.inputs['Strength'].default_value = .45
    l.new(brick.outputs['Fac'], mortar.inputs['Height'])
    grain = n.new('ShaderNodeBump')
    grain.inputs['Distance'].default_value = .0007
    grain.inputs['Strength'].default_value = .22
    l.new(noise.outputs['Fac'], grain.inputs['Height'])
    l.new(mortar.outputs[0], grain.inputs['Normal'])
    l.new(grain.outputs[0], bs.inputs['Normal'])

for name, color, rough, metal in [('concrete',(.52,.49,.40),.66,0),('frame',(.012,.018,.022),.28,.55),('metal',(.09,.105,.11),.46,.28),('rail',(.055,.07,.072),.3,.65),('roof',(.11,.13,.14),.83,.05),('bark',(.095,.063,.038),.92,0)]:
    m, bs = material(name, color, rough, metal)
    detail_bump(m, bs, 110 if name == 'concrete' else 60, .12, .00065)
glass, bs = material('glass', (.90,.96,.98), .075)
bs.inputs['Transmission Weight'].default_value = 1
bs.inputs['IOR'].default_value = 1.46
bs.inputs['Coat Weight'].default_value = .15
bs.inputs['Coat Roughness'].default_value = .055

# Damped pavement reflects the environment in irregular, broad wet patches.
road, bs = material('road', (.045,.053,.058), .32)
n, l = road.node_tree.nodes, road.node_tree.links
noise = texture_noise(road, .42)
ramp = n.new('ShaderNodeMapRange')
ramp.inputs['From Min'].default_value = .25
ramp.inputs['From Max'].default_value = .72
ramp.inputs['To Min'].default_value = .11
ramp.inputs['To Max'].default_value = .58
l.new(noise.outputs['Fac'], ramp.inputs[0])
l.new(ramp.outputs[0], bs.inputs['Roughness'])
bs.inputs['Coat Weight'].default_value = .55
bs.inputs['Coat Roughness'].default_value = .10
detail_bump(road, bs, 160, .19, .00065)
paving, bs = material('paving', (.24,.26,.25), .49)
n, l = paving.node_tree.nodes, paving.node_tree.links
coord = n.new('ShaderNodeTexCoord')
tile = n.new('ShaderNodeTexBrick')
tile.offset = 0
for key, value in [('Scale',1),('Brick Width',1.2),('Row Height',1.2),('Mortar Size',.006),('Mortar Smooth',.002)]:
    tile.inputs[key].default_value = value
tile.inputs['Color1'].default_value = (.28,.30,.28,1)
tile.inputs['Color2'].default_value = (.22,.24,.22,1)
tile.inputs['Mortar'].default_value = (.10,.12,.11,1)
l.new(coord.outputs['Object'],tile.inputs['Vector'])
l.new(tile.outputs['Color'],bs.inputs['Base Color'])
bump = n.new('ShaderNodeBump')
bump.invert = True
bump.inputs['Distance'].default_value = .003
bump.inputs['Strength'].default_value = .35
l.new(tile.outputs['Fac'], bump.inputs['Height'])
l.new(bump.outputs[0], bs.inputs['Normal'])
bs.inputs['Coat Weight'].default_value = .14
ground, bs = material('ground', (.065,.093,.034), .95)
noise = texture_noise(ground, 9)
ramp = ground.node_tree.nodes.new('ShaderNodeValToRGB')
ramp.color_ramp.elements[0].color = (.018,.032,.009,1)
ramp.color_ramp.elements[1].color = (.11,.155,.045,1)
ground.node_tree.links.new(noise.outputs['Fac'],ramp.inputs[0])
ground.node_tree.links.new(ramp.outputs[0],bs.inputs['Base Color'])
detail_bump(ground,bs,180,.4,.025)

# The old study's provenance-material swap reset every site face to slot zero.
# Restore its published presentation surface map without moving any vertex.
site=bpy.data.objects['continuous-site-context']
for face in site.data.polygons:
    x=sum(site.data.vertices[v].co.x for v in face.vertices)/len(face.vertices)/I
    y=sum(site.data.vertices[v].co.y for v in face.vertices)/len(face.vertices)/I
    index=0
    if (1670<x<2250 and -550<y<2400) or (-1600<x<3600 and -550<y<-180):index=2
    if (1510<x<1670 and -180<y<2050) or (-1600<x<1670 and -180<y<0):index=1
    if 1590<x<1670 and -150<y<2050:index=0
    face.material_index=index


def light(name, center, target, power, color, size, group='lighting'):
    data = bpy.data.lights.new(name, 'AREA')
    data.energy = power
    data.color = color
    data.shape = 'DISK'
    data.size = size
    o = bpy.data.objects.new(name, data)
    COLS[group].objects.link(o)
    o.location = center
    o.rotation_euler = (Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()
    return tag(o, group)


white, _ = material('Room / ivory plaster',(.56,.51,.40),.86)
dark, _ = material('Room / unlit plaster',(.18,.20,.18),.9)
wood, wb = material('Room / smoked oak',(.085,.052,.026),.49)
detail_bump(wood,wb,45,.16,.0007)
curtain, cb = material('Room / linen',(.48,.40,.29),.95)
cb.inputs['Sheen Weight'].default_value = .6
detail_bump(curtain,cb,250,.16,.0008)
lamp, _ = material('Room / warm lampshade',(1,.62,.27),.75,emission=1.8)
floor, _ = material('Room / oak floor',(.14,.086,.038),.64)
room_lights = 0


def room_box(name, center, u, n, du, dn, dz, mat, bevel=0):
    sz = (du,dn,dz) if abs(u.x) > .5 else (dn,du,dz)
    return box(name,center,sz,mat,'room dressing',bevel)


for opening in S['openings']:
    o = bpy.data.objects.get(opening['id']+'-glazing')
    if o is None or opening['kind'] == 'garage':
        continue
    corners = [o.matrix_world @ Vector(v) for v in o.bound_box]
    low = Vector([min(p[i] for p in corners) for i in range(3)])
    high = Vector([max(p[i] for p in corners) for i in range(3)])
    c = (low+high)/2
    face = opening['face']
    normal = Vector({'east':(1,0,0),'west':(-1,0,0),'south':(0,-1,0),'north':(0,1,0)}[face])
    tangent = Vector((0,1,0)) if face in ('east','west') else Vector((1,0,0))
    w = max(high.x-low.x, high.y-low.y)
    h = high.z-low.z
    depth = RNG.uniform(*CFG['room_depth_m'])
    lit = RNG.random() < CFG['lit_window_probability']
    back = c-normal*(depth+.05)
    room_box('Room back / '+o.name,back,tangent,normal,w+.13,.06,h+.1,white if lit else dark)
    for side in (-1,1):
        room_box('Room return / '+o.name,c-normal*(depth/2)+tangent*(side*(w/2+.025)),tangent,normal,.06,depth,h+.1,white if lit else dark)
        room_box('Room slab / '+o.name,c-normal*(depth/2)+Vector((0,0,side*(h/2+.025))),tangent,normal,w,depth,.06,white if side>0 else floor)
    # Folded curtains, with varied opening widths rather than uniform luminous cards.
    cover = RNG.uniform(.13,.30) if RNG.random() < .74 else .46
    for side in (-1,1):
        vs, fs = [], []
        for j in range(23):
            across = side*(w/2-cover*w*j/22)
            for zz in (-h/2+.03,h/2-.03):
                p = c+tangent*across-normal*(.14+.035*math.sin(j*math.pi*.65))+Vector((0,0,zz))
                vs.append(p)
        for j in range(22):
            fs.append((j*2,j*2+2,j*2+3,j*2+1))
        ob = mesh('Linen folds / '+o.name,vs,fs,curtain,'room dressing')
        for f in ob.data.polygons:f.use_smooth = True
    if lit:
        room_lights += 1
        warm = RNG.choice([(1,.67,.37),(1,.78,.54),(1,.86,.69)])
        pos = c-normal*(depth*.45)+Vector((0,0,h/2-.20))
        light('Apartment warm light / '+o.name,pos,c-normal*(depth*.8)+Vector((0,0,-h*.3)),RNG.uniform(28,65),warm,1.15)
        if w>.9 and h>1.5:
            # A few low furniture silhouettes and lamps give the glass actual depth.
            cc = back+normal*.3+tangent*(w*.18)
            room_box('Console / '+o.name,cc+Vector((0,0,-h/2+.65)),tangent,normal,w*.48,.35,.06,wood)
            room_box('Lamp stem / '+o.name,cc+Vector((0,0,-h/2+.87)),tangent,normal,.025,.025,.4,wood)
            room_box('Lamp shade / '+o.name,cc+Vector((0,0,-h/2+1.10)),tangent,normal,.24,.22,.25,lamp,.035)
            room_box('Interior art / '+o.name,back+normal*.06-tangent*w*.20,tangent,normal,w*.29,.02,h*.29,wood)


def grade(x,y):
    yf = min(1,max(0,y/(1800*I)))
    xf = min(1,max(0,x/(1420*I)))
    return yf*(228*(1-xf)+144*xf)*I


# Curb and a shallow gutter follow the same assumed grade as the base study.
curb, _ = material('Street / pale curb',(.32,.33,.29),.55)
water, _ = material('Street / gutter water',(.025,.035,.042),.10)
path = [(-40,-4.5),(39.5,-4.5)]
for j in range(1,16):
    a=-math.pi/2+j*(math.pi/2)/15
    path.append((39.5+2.9*math.cos(a),-1.6+2.9*math.sin(a)))
path.append((42.4,85))


def ribbon(name,path,width,height,mat,zoffset=0):
    vs=[]
    for j,p in enumerate(path):
        tangent=Vector(path[min(j+1,len(path)-1)])-Vector(path[max(j-1,0)])
        tangent.normalize()
        n=Vector((-tangent.y,tangent.x))
        for off,z in [(-width/2,0),(width/2,0),(width/2,height),(-width/2,height)]:
            q=Vector(p)+n*off
            vs.append((q.x,q.y,grade(q.x,q.y)+z+zoffset))
    fs=[]
    for j in range(len(path)-1):
        for k in range(4):fs.append((j*4+k,j*4+(k+1)%4,(j+1)*4+(k+1)%4,(j+1)*4+k))
    return mesh(name,vs,fs,mat)


ribbon('Continuous street curb',path,.19,.13,curb)
ribbon('Rain-darkened gutter',[(x+.14,y-.14) for x,y in path],.24,.004,water,.006)
soil, _ = material('Planting / moist mulch',(.045,.031,.016),.98)
for x,y,_ in CFG['street_trees_m']:
    box('Tree planting well',(x,y,grade(x,y)+.012),(1.0,1.55,.035),soil)

# Original, deterministic botanical meshes. Branches are tapered tubes; leaves
# have a folded midrib and translucent back-light response.
leaf_mats=[]
for j,col in enumerate([(.026,.065,.012),(.044,.105,.018),(.068,.135,.025),(.10,.15,.026),(.15,.13,.028)]):
    m,bs=material('Botanical / leaf '+str(j),col,.65)
    bs.inputs['Subsurface Weight'].default_value=.05
    n,l=m.node_tree.nodes,m.node_tree.links
    out=n.get('Material Output')
    trans=n.new('ShaderNodeBsdfTranslucent')
    trans.inputs['Color'].default_value=(*col,1)
    mix=n.new('ShaderNodeMixShader')
    mix.inputs[0].default_value=.23
    l.new(bs.outputs[0],mix.inputs[1]);l.new(trans.outputs[0],mix.inputs[2]);l.new(mix.outputs[0],out.inputs[0])
    leaf_mats.append(m)


def leaf_mesh(name,points,length=.095):
    vs,fs,mi=[],[],[]
    for c in points:
        c=Vector(c)
        a=RNG.uniform(0,math.tau)
        u=Vector((math.cos(a),math.sin(a),RNG.uniform(-.75,.85))).normalized()
        v=u.cross(Vector((.15,.25,1))).normalized()
        sz=length*RNG.uniform(.65,1.3)
        k=len(vs)
        vs.extend([c-u*sz*.5,c-u*sz*.22+v*sz*.26,c+u*sz*.30+v*sz*.22,c+u*sz*.55,c+u*sz*.3-v*sz*.22,c-u*sz*.22-v*sz*.26,c+Vector((0,0,sz*.065))])
        fs.extend([(k+6,k+j,k+(j+1)%6) for j in range(6)])
        color=RNG.choices(range(5),[2,4,5,3,1])[0]
        mi.extend([color]*6)
    ob=mesh(name,vs,fs,leaf_mats[0],'botanical')
    for mat in leaf_mats[1:]:ob.data.materials.append(mat)
    for p,i in zip(ob.data.polygons,mi):p.material_index=i;p.use_smooth=True
    return ob


def branch_mesh(name,segments):
    vs,fs=[],[]
    for a,b,r1,r2 in segments:
        a,b=Vector(a),Vector(b);axis=(b-a).normalized()
        u=axis.cross(Vector((.01,1,.05))).normalized();v=axis.cross(u)
        k=len(vs)
        for p,r in [(a,r1),(b,r2)]:
            for j in range(7):vs.append(p+r*(u*math.cos(j*math.tau/7)+v*math.sin(j*math.tau/7)))
        for j in range(7):fs.append((k+j,k+(j+1)%7,k+7+(j+1)%7,k+7+j))
    ob=mesh(name,vs,fs,bpy.data.materials['bark'],'botanical')
    for p in ob.data.polygons:p.use_smooth=True
    return ob


segments=[];tips=[]
trunk=Vector((0,0,2.0))
segments.append(((0,0,0),trunk,.12,.075))
for j in range(11):
    a=j*math.tau/11+RNG.uniform(-.2,.2)
    mid=Vector((math.cos(a)*RNG.uniform(.7,1.3),math.sin(a)*RNG.uniform(.7,1.3),RNG.uniform(2.6,3.6)))
    segments.append((trunk+Vector((0,0,RNG.uniform(-.3,.2))),mid,.048,.023))
    for k in range(5):
        aa=a+(k-2)*.42
        end=mid+Vector((math.cos(aa)*RNG.uniform(.5,1.0),math.sin(aa)*RNG.uniform(.5,1.0),RNG.uniform(.25,.95)))
        segments.append((mid,end,.019,.005))
        tips.append(end)
points=[]
for tip in tips:
    for j in range(230):
        while True:
            p=Vector((RNG.uniform(-1,1),RNG.uniform(-1,1),RNG.uniform(-1,1)))
            if p.length_squared<1:break
        points.append(tip+Vector((p.x*.95,p.y*.95,p.z*.95)))
tree_b=branch_mesh('Street tree branches / prototype',segments)
tree_l=leaf_mesh('Street tree leaves / prototype',points,.12)
trees=CFG['street_trees_m']+CFG['background_trees_m']
for j,(x,y,height) in enumerate(trees):
    angle=RNG.uniform(0,math.tau);scale=height/4.7
    for base in (tree_b,tree_l):
        ob=base if j==0 else base.copy()
        if j:COLS['botanical'].objects.link(ob)
        ob.name=('Tree %02d / '%j)+('leaves' if base==tree_l else 'branches')
        ob.location=(x,y,grade(x,y))
        ob.rotation_euler.z=angle
        ob.scale=(scale,scale,scale)

# A clipped hedge is built from fine leaf clusters, without smooth green blobs.
pts=[]
for j in range(2500):
    x=RNG.uniform(-.5,.5);y=RNG.uniform(-.31,.31);z=RNG.uniform(.12,.84)
    if abs(x)>.37 or abs(y)>.21 or z>.64:pts.append((x,y,z))
hedge=leaf_mesh('Garden hedge / prototype',pts,.075)
for j in range(43):
    x=1.5+j*.83;y=.35
    ob=hedge if j==0 else hedge.copy()
    if j:COLS['botanical'].objects.link(ob)
    ob.name='South garden hedge / %02d'%j
    ob.location=(x,y,grade(x,y))
for j in range(38):
    x=37.55;y=1+j*1.1
    ob=hedge.copy();COLS['botanical'].objects.link(ob)
    ob.name='East garden hedge / %02d'%j
    ob.location=(x,y,grade(x,y));ob.rotation_euler.z=math.pi/2

# Sparse individual plants and ornamental grasses give the planted edge depth.
for j in range(26):
    x=RNG.uniform(3,36);y=RNG.uniform(.85,2.8)
    pts=[]
    for k in range(160):
        a=RNG.uniform(0,math.tau);r=RNG.uniform(.08,.45)
        pts.append((x+math.cos(a)*r,y+math.sin(a)*r,grade(x,y)+RNG.uniform(.18,.75)))
    leaf_mesh('Garden shrubs / %02d'%j,pts,.12)


def cylinder(name,a,b,r,mat,group='street details',sides=12):
    a,b=Vector(a),Vector(b);axis=(b-a).normalized()
    u=axis.cross(Vector((.01,1,.03))).normalized();v=axis.cross(u)
    vs=[]
    for p in (a,b):
        for j in range(sides):vs.append(p+r*(u*math.cos(j*math.tau/sides)+v*math.sin(j*math.tau/sides)))
    fs=[tuple(reversed(range(sides))),tuple(range(sides,2*sides))]
    fs.extend([(j,(j+1)%sides,(j+1)%sides+sides,j+sides) for j in range(sides)])
    ob=mesh(name,vs,fs,mat,group)
    for p in ob.data.polygons:p.use_smooth=True
    return ob


steel,_=material('Street / dark bronze',(.035,.041,.039),.3,.7)
glow,_=material('Street / warm opal',(1,.62,.24),.2,emission=4)
for j,(x,y) in enumerate([(40.8,-2.5),(41.5,29.5),(-1,-2.7)]):
    z=grade(x,y)
    cylinder('Street lamp / fluted base',(x,y,z),(x,y,z+.4),.12,steel)
    cylinder('Street lamp / post',(x,y,z+.4),(x,y,z+4.25),.055,steel)
    cylinder('Street lamp / collar',(x,y,z+4.20),(x,y,z+4.27),.19,steel)
    box('Street lamp / lantern',(x,y,z+4.47),(.23,.23,.39),glow,bevel=.04)
    cylinder('Street lamp / cap',(x,y,z+4.66),(x,y,z+4.72),.19,steel)
    light('Street pool / %d'%j,(x,y,z+4.2),(x,y,z),150,(1,.69,.38),.65)

# Low garden fencing and terrace chairs remain separate presentation objects.
for x in range(2,37):
    z=grade(x,.75)
    cylinder('Garden fence post',(x,.75,z+.05),(x,.75,z+1.12),.012,steel,sides=6)
for zz in (.15,1.1):
    cylinder('Garden fence rail',(1.5,.75,zz),(36.5,.75,zz),.014,steel,sides=8)

# Nearby OSM footprints provide quiet background context. Heights, facade
# details and registration remain assumed, as in the existing drone project.
context=json.loads((ROOT/'projects/highland-drone/flight.spec.json').read_text())['osm_context']
neighbor,_=material('Context / muted masonry',(.13,.11,.095),.82)
neighbor_glass,_=material('Context / dark windows',(.033,.048,.064),.25,.48)
from mathutils.geometry import tessellate_polygon
context_count=0
for item in context['buildings']:
    poly=item['footprint_m'];cx=sum(p[0] for p in poly)/len(poly);cy=sum(p[1] for p in poly)/len(poly)
    if (cx-19)**2+(cy-23)**2>CFG['context_max_distance_m']**2 or cy<0:continue
    z=grade(cx,cy);h=item['height_m'];npoly=len(poly)
    vs=[(x,y,z) for x,y in poly]+[(x,y,z+h) for x,y in poly]
    fs=[(j,(j+1)%npoly,(j+1)%npoly+npoly,j+npoly) for j in range(npoly)]
    vectors=[Vector((x,y,0)) for x,y in poly]
    for tri in tessellate_polygon([vectors]):
        ids=[p if isinstance(p,int) else min(range(npoly),key=lambda i:(vectors[i]-p).length_squared) for p in tri]
        fs.append(tuple(i+npoly for i in ids))
    ob=mesh('OSM context / '+str(item['osm_id']),vs,fs,neighbor)
    ob['source']='OpenStreetMap contributors (ODbL); existing flight.spec.json osm_context'
    ob['basis']='Approximate footprint registration; height and facade treatment assumed. No surveyed neighboring facades.'
    context_count+=1
    # Recess-like dark window panels at a quiet, representative rhythm.
    signed_area=sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(poly,poly[1:]+poly[:1]))
    for a,b in zip(poly,poly[1:]+poly[:1]):
        a,b=Vector(a),Vector(b);d=b-a;length=d.length
        if length<3:continue
        u=Vector((d.x/length,d.y/length,0));normal=Vector((u.y,-u.x,0))*(1 if signed_area>0 else -1)
        for k in range(max(1,int(length/3.3))):
            q=a+d*((k+.5)/max(1,int(length/3.3)))
            for floor_i in range(max(1,int(h/3.05))):
                c=Vector((q.x,q.y,z+1.6+floor_i*3.05))+normal*.025
                v=[c-u*.55-Vector((0,0,.7)),c+u*.55-Vector((0,0,.7)),c+u*.55+Vector((0,0,.7)),c-u*.55+Vector((0,0,.7))]
                mesh('Context window',v,[(0,1,2,3)],neighbor_glass)

# Generic parked vehicles provide street scale. These are original meshes,
# unrelated to the actual vehicles or parking occupancy in the source photos.
rubber,_=material('Vehicle / tire',(.012,.015,.018),.7)
chrome,_=material('Vehicle / brushed alloy',(.23,.27,.29),.24,.85)
auto_glass,_=material('Vehicle / dark glazing',(.025,.044,.064),.14,.68)
headlamp,_=material('Vehicle / headlamp lens',(.34,.43,.51),.18,.3)
rear_lamp,_=material('Vehicle / tail lens',(.27,.012,.008),.21,.25)
for car_i,config in enumerate(CFG['parked_cars']):
    x,y=config['center_m'];angle=config['angle_rad'];z=grade(x,y)+.025
    paint,pb=material('Vehicle / paint '+str(car_i),[(.035,.044,.05),(.12,.13,.12),(.14,.16,.18)][car_i],.24,.65)
    pb.inputs['Coat Weight'].default_value=.65;pb.inputs['Coat Roughness'].default_value=.13
    def world(p):
        return (x+p[0]*math.cos(angle)-p[1]*math.sin(angle),y+p[0]*math.sin(angle)+p[1]*math.cos(angle),z+p[2])
    # Broad body cross-sections with chamfered shoulders, rather than cube bodies.
    sections=[(-2.26,.73,.48),(-2.12,.88,.72),(-1.55,.91,.85),(-.85,.92,.87),(.75,.91,.84),(1.65,.87,.73),(2.22,.74,.62)]
    vs=[]
    for yy,w,top in sections:
        for xx,zz in [(-w*.87,.32),(-w,.48),(-w*.96,top-.09),(-w*.76,top),(w*.76,top),(w*.96,top-.09),(w,.48),(w*.87,.32)]:vs.append(world((xx,yy,zz)))
    fs=[tuple(reversed(range(8))),tuple(range((len(sections)-1)*8,len(sections)*8))]
    for j in range(len(sections)-1):
        for k in range(8):fs.append((j*8+k,j*8+(k+1)%8,(j+1)*8+(k+1)%8,(j+1)*8+k))
    ob=mesh('Vehicle %d / coachwork'%car_i,vs,fs,paint)
    for f in ob.data.polygons:f.use_smooth=True
    cabin=[(-1.40,.77,.86),(-.70,.69,1.37),(.45,.67,1.39),(1.20,.77,.84)]
    vs=[]
    for yy,w,zz in cabin:vs.extend([world((-w,yy,zz)),world((w,yy,zz))])
    ob=mesh('Vehicle %d / cabin'%car_i,vs,[(0,1,3,2),(2,3,5,4),(4,5,7,6),(0,2,4,6),(1,7,5,3)],auto_glass)
    for xx in (-.85,.85):
        for yy in (-1.35,1.35):
            cylinder('Vehicle tire',world((xx-.10,yy,.34)),world((xx+.10,yy,.34)),.33,rubber,sides=24)
            side=-.116 if xx<0 else .116
            cylinder('Vehicle wheel',world((xx+side,yy,.34)),world((xx+side*1.08,yy,.34)),.21,chrome,sides=24)
    for yy,mat in [(-2.20,rear_lamp),(2.17,headlamp)]:
        for xx in (-.57,.57):
            ob=box('Vehicle lens',world((xx,yy,.64)),(.27,.055,.11),mat,bevel=.025)
            ob.rotation_euler.z=angle

# World illumination uses the existing, locally supplied CC0 sky asset.
world=bpy.data.worlds.new('Seattle / dusk atmosphere')
SCENE.world=world;world.use_nodes=True
n,l=world.node_tree.nodes,world.node_tree.links;n.clear()
out=n.new('ShaderNodeOutputWorld')
bg=n.new('ShaderNodeBackground');bg.inputs['Strength'].default_value=.20
env=n.new('ShaderNodeTexEnvironment')
env.image=bpy.data.images.load(str(HERE/'assets/kloofendal_48d_partly_cloudy_puresky_4k.hdr'),check_existing=True)
tex=n.new('ShaderNodeTexCoord');mapping=n.new('ShaderNodeMapping')
mapping.inputs['Rotation'].default_value[2]=math.radians(125)
l.new(tex.outputs['Generated'],mapping.inputs['Vector']);l.new(mapping.outputs[0],env.inputs['Vector'])
tint=n.new('ShaderNodeMixRGB');tint.blend_type='MULTIPLY';tint.inputs[0].default_value=.68;tint.inputs[2].default_value=(.40,.56,1,1)
l.new(env.outputs[0],tint.inputs[1]);l.new(tint.outputs[0],bg.inputs['Color']);l.new(bg.outputs[0],out.inputs[0])
# Broad, soft sky sources retain legibility in the brick and recessed balconies.
light('Soft southwest sky',(-30,-45,45),(17,18,10),26000,(.72,.80,1),42)
light('Warm last light',(-25,8,32),(17,18,11),16000,(1,.74,.55),30)
light('East sky fill',(65,25,35),(20,20,10),19000,(.58,.72,1),40)

cam=SCENE.camera
cam.name='200 West Highland / hero camera'
cam.location=CFG['camera']['location_m']
cam.rotation_euler=(Vector(CFG['camera']['target_m'])-cam.location).to_track_quat('-Z','Y').to_euler()
cam.data.type='PERSP';cam.data.lens=CFG['camera']['lens_mm'];cam.data.shift_y=CFG['camera']['shift_y'];cam.data.clip_end=1000
cam.data.dof.use_dof=False
SCENE.render.engine='CYCLES'
SCENE.cycles.device='CPU'
SCENE.cycles.samples=ARGS.samples or (24 if ARGS.preview else CFG['output']['samples'])
SCENE.cycles.use_denoising=True
SCENE.cycles.use_adaptive_sampling=True
SCENE.cycles.adaptive_threshold=CFG['output']['adaptive_threshold']
SCENE.cycles.adaptive_min_samples=12
SCENE.cycles.max_bounces=8
SCENE.cycles.transmission_bounces=6
SCENE.cycles.transparent_max_bounces=8
SCENE.cycles.diffuse_bounces=3
SCENE.cycles.glossy_bounces=4
SCENE.cycles.sample_clamp_indirect=4
SCENE.cycles.seed=CFG['seed']
SCENE.render.threads_mode='FIXED';SCENE.render.threads=3
width=ARGS.width or (1440 if ARGS.preview else CFG['output']['width'])
SCENE.render.resolution_x=width
SCENE.render.resolution_y=round(width*CFG['output']['height']/CFG['output']['width'])
SCENE.render.resolution_percentage=100
SCENE.render.image_settings.file_format='PNG'
SCENE.render.image_settings.color_mode='RGB'
SCENE.render.image_settings.color_depth='8'
SCENE.view_settings.view_transform='AgX'
SCENE.view_settings.look='AgX - Medium High Contrast'
SCENE.view_settings.exposure=.65
SCENE.render.film_transparent=False

# Very restrained bloom, applied by Blender's compositor to the rendered scene.
compositor=bpy.data.node_groups.new('Highland / photographic finish','CompositorNodeTree')
compositor.interface.new_socket(name='Image',in_out='OUTPUT',socket_type='NodeSocketColor')
SCENE.compositing_node_group=compositor
n,l=compositor.nodes,compositor.links
rl=n.new('CompositorNodeRLayers')
glare=n.new('CompositorNodeGlare')
glare.inputs['Type'].default_value='Fog Glow'
glare.inputs['Quality'].default_value='High'
glare.inputs['Threshold'].default_value=2
glare.inputs['Strength'].default_value=.06
comp=n.new('NodeGroupOutput');l.new(rl.outputs['Image'],glare.inputs['Image']);l.new(glare.outputs['Image'],comp.inputs['Image'])

# A discreet native-camera caption retains the study notice on exported images.
text_mat,_=material('Typography / ivory',(.72,.77,.80),.5,emission=1)
horizontal=cam.data.sensor_width/cam.data.lens
vertical=horizontal*SCENE.render.resolution_y/SCENE.render.resolution_x
center_y=cam.data.shift_y*horizontal
for name,body,size,y in [('Property','200 WEST HIGHLAND',.0145,-.444),('Notice',CFG['notice'],.0083,-.472)]:
    data=bpy.data.curves.new('Caption / '+name,'FONT');data.body=body;data.size=vertical*size
    ob=bpy.data.objects.new('Caption / '+name,data);COLS['typography'].objects.link(ob)
    ob.parent=cam;ob.location=(-horizontal*.465,center_y+vertical*y,-1)
    ob.data.materials.append(text_mat);ob.visible_shadow=False
    tag(ob,'typography')

assert architecture_hash()[0]==BASE_HASH, 'Presentation pass changed architectural geometry'
assert len(S['openings'])==CFG.get('expected_openings',165)
for c in COLS.values():
    for o in c.objects:
        assert o.get('source') and o.get('basis') and o.get('status')=='assumed'
SCENE['source_architecture_sha256']=BASE_HASH
SCENE['base_scene']=CFG['base_scene']
SCENE['notice']=CFG['notice']
SCENE['presentation_spec']='projects/highland-cinematic/scene.json'
bpy.ops.file.pack_all()
filename='Highland-dusk-preview.png' if ARGS.preview else 'Highland-dusk-4K.png'
SCENE.render.filepath=str(OUT/filename)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Highland-dusk.blend'))
report={'blender':bpy.app.version_string,'base_architecture_sha256':BASE_HASH,'architecture_unchanged':True,'protected_mesh_objects':len(BASE_INVENTORY),'source_openings':len(S['openings']),'unresolved_source_candidates':len(S['rejected_candidates']),'lit_windows':room_lights,'presentation_objects':sum(len(c.objects) for c in COLS.values()),'dimensions':[SCENE.render.resolution_x,SCENE.render.resolution_y],'samples':SCENE.cycles.samples,'notice':CFG['notice'],'base_limitations':S['limitations'],'built_seconds':round(time.monotonic()-START,2)}
(OUT/'scene-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print('SCENE READY',json.dumps(report),flush=True)
if not ARGS.build_only:
    bpy.ops.render.render(write_still=True)
    report['total_seconds']=round(time.monotonic()-START,2)
    (OUT/('preview-render.json' if ARGS.preview else 'final-render.json')).write_text(json.dumps(report,indent=2)+'\n')
    print('RENDER COMPLETE',SCENE.render.filepath,flush=True)
