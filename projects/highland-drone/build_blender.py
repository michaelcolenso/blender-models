"""Native Blender reconstruction of the Highland lobby/corridor presentation.

Run with Python 3.11 and bpy==5.0.1. Geometry uses plan inches, converted to
meters. Interior wall faces, finishes and elevator details are illustrative.
"""
import argparse
import hashlib
import json
import math
import time
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'deliverables/highland-exterior/Highland-exterior.blend'
SPEC_FILE = Path(__file__).with_name('flight.spec.json')
S = json.loads(SPEC_FILE.read_text())
I, FT, FPS, LAST = .0254, .3048, 24, 624
WALLS, SECTION, RIG = [], [], {}


def smooth(a, b, t):
    v = max(0., min(1., (t-a)/(b-a)))
    return v*v*(3-2*v)


def point(t):
    seg = next((s for s in S['camera_bezier_segments'] if t <= s['t1']), S['camera_bezier_segments'][-1])
    u = max(0., min(1., (t-seg['t0'])/(seg['t1']-seg['t0'])))
    return sum((Vector(seg[f'p{j}']) * math.comb(3,j) * (1-u)**(3-j) * u**j for j in range(4)), Vector()) * FT


def trajectory(t):
    pos = point(t)
    look = point(min(26, t+1.0))
    if t<3.8:
        look=(Vector((80,90,33))*FT).lerp(look,smooth(1.7,3.8,t))
    if (look-pos).length < .02:
        look = pos + (pos-point(max(0,t-.4))).normalized()
    if 10.3 <= t <= 13.4:
        look = Vector((915*I,1535*I,pos.z)).lerp(Vector((847*I,1452*I,pos.z)),smooth(12.15,13.4,t))
    if 14.8 <= t <= 19.4:
        p = min(smooth(14.8,15.2,t),1-smooth(18.8,19.4,t))
        look = look.lerp(pos+Vector((1,0,0)),p)
    pull = smooth(15.1,16.1,t)*(1-smooth(18.1,19.15,t))
    pos = pos.lerp(Vector((1090*I,1310*I,260*I)),pull)
    lift = 132+123*smooth(16,17.8,t)
    look = look.lerp(Vector((847*I,1452*I,(lift+48)*I)),pull)
    return pos, look


def collection(name):
    c = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(c)
    return c


def material(name, color, rough=.6, metal=0., emission=0.):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes.get('Principled BSDF')
    b.inputs['Base Color'].default_value = (*color,1)
    b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal
    b.inputs['Emission Color'].default_value = (*color,1)
    b.inputs['Emission Strength'].default_value = emission
    return m


def texture(m, kind):
    n, l = m.node_tree.nodes, m.node_tree.links
    b = n.get('Principled BSDF'); coord = n.new('ShaderNodeTexCoord')
    noise = n.new('ShaderNodeTexNoise'); noise.inputs['Scale'].default_value = 65 if kind=='plaster' else 25
    noise.inputs['Detail'].default_value = 3
    l.new(coord.outputs['Object'],noise.inputs['Vector'])
    bump = n.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = .12
    bump.inputs['Distance'].default_value = .001 if kind=='plaster' else .002
    l.new(noise.outputs['Fac'],bump.inputs['Height']); l.new(bump.outputs['Normal'],b.inputs['Normal'])
    if kind in ('wood','carpet'):
        wave = n.new('ShaderNodeTexWave'); wave.wave_type='BANDS'; wave.bands_direction='X'
        wave.inputs['Scale'].default_value = 38 if kind=='carpet' else 6
        wave.inputs['Distortion'].default_value = 2 if kind=='wood' else .4
        l.new(coord.outputs['Object'],wave.inputs['Vector'])
        ramp = n.new('ShaderNodeValToRGB')
        colors = ((.035,.045,.055,1),(.11,.13,.14,1)) if kind=='carpet' else ((.028,.014,.009,1),(.13,.068,.033,1))
        for el,color in zip(ramp.color_ramp.elements,colors): el.color=color
        l.new(wave.outputs['Color'],ramp.inputs[0]); l.new(ramp.outputs[0],b.inputs['Base Color'])
    return m


def box(name, bounds, mat, col, parent=None, wall=False, section=False):
    x0,x1,y0,y1,z0,z1 = bounds
    bpy.ops.mesh.primitive_cube_add(size=1, location=((x0+x1)*I/2,(y0+y1)*I/2,(z0+z1)*I/2))
    o=bpy.context.object; o.name=name; o.dimensions=((x1-x0)*I,(y1-y0)*I,(z1-z0)*I)
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    for c in list(o.users_collection): c.objects.unlink(o)
    col.objects.link(o); o.data.materials.append(mat)
    if parent: o.parent=parent
    o['basis']='A2.03/A2.04 fitted public circulation; finishes and details illustrative'
    if wall: WALLS.append((o,tuple(v*I for v in bounds)))
    if section: SECTION.append(o)
    if min(o.dimensions)>.012:
        bev=o.modifiers.new('Soft architectural edges','BEVEL'); bev.width=.002; bev.segments=2
    return o


def empty(name,col,loc=(0,0,0)):
    o=bpy.data.objects.new(name,None);col.objects.link(o);o.location=loc;return o


def area(name, pos, power, size, col, parent=None, target=None):
    d=bpy.data.lights.new(name,'AREA');d.energy=power;d.color=(1,.76,.49);d.shape='DISK';d.size=size
    o=bpy.data.objects.new(name,d);col.objects.link(o);o.location=Vector(pos)*I
    if parent:o.parent=parent
    if target:o.rotation_euler=(Vector(target)*I-o.location).to_track_quat('-Z','Y').to_euler()
    return o


def text(name, body, pos, size, mat, col, rotation=(math.pi/2,0,0)):
    d=bpy.data.curves.new(name,'FONT');d.body=body;d.size=size;d.align_x='CENTER';d.align_y='CENTER';d.extrude=.001
    o=bpy.data.objects.new(name,d);col.objects.link(o);o.location=Vector(pos)*I;o.rotation_euler=rotation;d.materials.append(mat)
    return o


def panel(name,x,y,w,z,col,M):
    for label,b,mat in [
        ('leaf',(x-1,x+1,y-w/2,y+w/2,z+4,z+88),M['wood']),
        ('south jamb',(x-2,x+2,y-w/2-2,y-w/2+1,z+3,z+90),M['trim']),
        ('north jamb',(x-2,x+2,y+w/2-1,y+w/2+2,z+3,z+90),M['trim']),
        ('head',(x-2,x+2,y-w/2-2,y+w/2+2,z+89,z+92),M['trim']),
        ('pull',(x+(2 if x<915 else -3),x+(3 if x<915 else -2),y+8,y+11,z+40,z+48),M['brass'])]:
        box(name+' '+label,b,mat,col)


def ghost_material(m):
    n,l=m.node_tree.nodes,m.node_tree.links;b=n.get('Principled BSDF');out=n.get('Material Output')
    glass=n.new('ShaderNodeBsdfGlass');glass.inputs['Color'].default_value=(.68,.83,.94,1);glass.inputs['Roughness'].default_value=.08;glass.inputs['IOR'].default_value=1.05
    transparent=n.new('ShaderNodeBsdfTransparent');glassmix=n.new('ShaderNodeMixShader');glassmix.inputs[0].default_value=.78
    l.new(glass.outputs[0],glassmix.inputs[1]);l.new(transparent.outputs[0],glassmix.inputs[2])
    mix=n.new('ShaderNodeMixShader');mix.name='Elevator architectural section'
    l.new(b.outputs[0],mix.inputs[1]);l.new(glassmix.outputs[0],mix.inputs[2]);l.new(mix.outputs[0],out.inputs['Surface'])
    for f in range(1,LAST+1):
        t=(f-1)/FPS;mix.inputs[0].default_value=.95*smooth(15,16,t)*(1-smooth(18.2,19.15,t));mix.inputs[0].keyframe_insert('default_value',frame=f)


def build(output):
    WALLS.clear(); SECTION.clear(); RIG.clear()
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE));scene=bpy.context.scene
    exterior=[o for o in scene.objects if o.type=='MESH' and not o.name.startswith('caption')]
    for o in list(bpy.data.objects):
        if o.name.startswith('caption') or o.type=='CAMERA':bpy.data.objects.remove(o,do_unlink=True)
    for o in exterior:
        if 'east-R1-08-glazing' in o.name or 'east-R1-08-frames' in o.name or o.name=='slab-R1':o.hide_render=True;o.hide_viewport=True;continue
        for f,value in [(1,False),(146,False),(147,True)]:
            o.hide_render=value;o.hide_viewport=value;o.keyframe_insert('hide_render',frame=f);o.keyframe_insert('hide_viewport',frame=f)
    for o in scene.objects:
        if o.type=='LIGHT':
            o.data.energy=1.2 if o.data.type=='SUN' else o.data.energy
    col=collection('Native interior / Lobby 110 and Corridors 108–208')
    rig=collection('Native animation / camera doors elevator and section')
    lighting=collection('Warm architectural lighting')
    context=collection('OSM neighborhood / approximate registration and heights')
    M={
        'wall':texture(material('Gallery plaster',(.67,.64,.58),.75),'plaster'),
        'ceiling':texture(material('Warm plaster ceiling',(.73,.71,.66),.85),'plaster'),
        'carpet':texture(material('Woven corridor carpet',(.08,.1,.11),.9),'carpet'),
        'stone':texture(material('Honed lobby stone',(.24,.27,.28),.3),'stone'),
        'wood':texture(material('Satin walnut doors',(.08,.04,.02),.3),'wood'),
        'trim':material('Dark walnut frames',(.028,.021,.016),.38),
        'brass':material('Brushed champagne brass',(.62,.42,.18),.26,.8),
        'metal':material('Satin elevator bronze',(.26,.23,.18),.3,.65),
        'led':material('Warm LED diffuser',(1,.72,.39),.3,emission=5),
        'ink':material('Wayfinding midnight enamel',(.009,.025,.034),.42),
        'letter':material('Wayfinding lettering',(.85,.68,.39),.3,emission=.25),
        'glass':material('Entry glass',(.86,.93,.97),.06),
        'gold':material('Guidance light trail',(1,.55,.16),.3,emission=2.5),
    }
    g=M['glass'].node_tree.nodes.get('Principled BSDF');g.inputs['Transmission Weight'].default_value=1;g.inputs['IOR'].default_value=1.45
    M['cabStone']=M['stone'].copy();M['cabStone'].name='Elevator solid stone floor'
    M['cabDoor']=M['metal'].copy();M['cabDoor'].name='Elevator door / glass during section'
    for name,r in S['rooms'].items():
        z=255 if name=='corridor-208' else 132;x0,x1,y0,y1=r['bounds_in']
        box(name+' floor',(x0,x1,y0,y1,z-3,z),M['carpet'] if 'corridor' in name else M['stone'],col,section=True)
        box(name+' ceiling',(x0,x1,y0,y1,z+102,z+105),M['ceiling'],col,section=True)
    for z,label in [(132,'R1'),(255,'R2')]:
        bounds=[('west south',(874,879,670,1430)),('west north',(874,879,1474,1540)),('east north',(951,956,1368 if z==132 else 670,1540)),('south',(879,951,665,670)),('north',(879,951,1540,1545))]
        if z==132:bounds.append(('east south',(951,956,670,1296)))
        for name,b in bounds:box(label+' corridor wall '+name,(*b,z,z+102),M['wall'],col,wall=True,section=True)
        for y in [750,900,1090,1215]:panel(label+' east residence door '+str(y),949,y,31,z,col,M)
        for y in [765,1020,1170]:panel(label+' west residence door '+str(y),881,y,31,z,col,M)
        for x in [881,949]:box(label+' skirting '+str(x),(x-1,x+1,680,1525,z+1,z+5),M['trim'],col)
        for x in [887,943]:box(label+' recessed linear LED '+str(x),(x-1,x+1,695,1510,z+99,z+100),M['led'],col,section=True)
        for y in [790,990,1190,1400,1500]:
            box(label+' ceiling luminaire '+str(y),(897,933,y-5,y+5,z+100,z+101),M['led'],col,section=True)
            area(label+' ceiling wash '+str(y),(915,y,z+97),55,.7,lighting)
        box(label+' stair door',(894,936,670,672,z+4,z+87),M['wood'],col)
        box(label+' stair header',(891,939,669,674,z+87,z+91),M['trim'],col)
        box(label+' stair plaque',(891,939,672,674,z+92,z+100),M['ink'],col)
        text(label+' stair wayfinding','STAIR M1',(915,675,z+96),.095,M['letter'],col,rotation=(math.pi/2,0,math.pi))
        # Signs are actual editable Blender text, with floor labels on geometry.
        text(label+' floor wayfinding','CORRIDOR '+('108' if z==132 else '208'),(915,1300,z+.4),.13,M['letter'],col,rotation=(0,0,math.pi))
    for name,b in [
        ('north',(1120,1475,1405,1410)),('south',(1120,1475,1255,1260)),
        ('west north return',(1115,1120,1368,1410)),('west south return',(1115,1120,1255,1296)),
        ('link north',(951,1120,1368,1373)),('link south',(951,1120,1291,1296))]:
        box('Lobby wall '+name,(*b,132,234),M['wall'],col,wall=True,section=True)
    for x in [1000,1070,1170,1320,1410]:
        box('Lobby diffuser '+str(x),(x-14,x+14,1322,1342,232,233),M['led'],col,section=True)
        area('Lobby soft downlight '+str(x),(x,1332,229),65,.75,lighting)
    text('Lobby floor wayfinding','LOBBY 110',(1280,1332,132.5),.20,M['letter'],col,rotation=(0,0,math.pi/2))
    box('Elevator direction plaque',(890,940,1537,1539,198,214),M['ink'],col)
    text('Elevator wayfinding','ELEVATOR M1  <',(915,1536,206),.11,M['letter'],col)
    # Operable entry leaves: pivots sit on the jambs, not at mesh centers.
    hinges=[];door_leaves=[]
    for name,y0,y1,angle in [('south',1277,1332.5,1.32),('north',1332.5,1388,-1.32)]:
        pivot=empty('Entry '+name+' hinge',rig,(1476*I,(y0 if name=='south' else y1)*I,179*I))
        leaf=box('Entry '+name+' glass',(1475,1477,y0,y1,134,232),M['glass'],col)
        leaf.parent=pivot;leaf.matrix_parent_inverse=pivot.matrix_world.inverted()
        door_leaves.append(leaf)
        for yy in [y0,y1]:
            frame=box('Entry '+name+' stile',(1473,1479,yy-1,yy+1,134,232),M['metal'],col)
            frame.parent=pivot;frame.matrix_parent_inverse=pivot.matrix_world.inverted()
        hinges.append((pivot,angle))
    for y0,y1 in [(1266,1277),(1388,1399)]:box('Fixed lobby sidelight',(1475,1477,y0,y1,134,232),M['glass'],col)
    for y in [1266,1399]:box('Lobby jamb',(1473,1479,y-2,y+2,132,234),M['trim'],col)
    area('Entry canopy warm downlight',(1520,1332,239),100,1.2,lighting)
    # A complete lit moving elevator cab, with separate landing and car leaves.
    car=empty('Elevator M1 / animated R1 to R2 cab',rig)
    for name,b,mat in [
        ('floor',(816,879,1430,1474,-3,0),'cabStone'),('ceiling',(816,879,1430,1474,102,105),'ceiling'),
        ('rear wall',(813,816,1430,1474,0,102),'wood'),('south wall',(816,879,1427,1430,0,102),'wall'),
        ('north wall',(816,879,1474,1477,0,102),'wall'),('rear feature',(816,818,1435,1469,18,88),'wood')]:
        box('Cab '+name,b,M[mat],col,parent=car,section=True)
    for y in [1434,1470]:box('Cab brass feature edge',(818,819,y,y+1,18,88),M['brass'],col,parent=car)
    for y in [1438,1466]:box('Cab vertical light',(819,820,y,y+1,24,84),M['led'],col,parent=car)
    for y in [1431,1472]:box('Cab handrail',(827,868,y,y+1,34,36),M['brass'],col,parent=car)
    area('Cab ceiling softbox',(847,1452,98),45,.6,lighting,parent=car)
    area('Cab rear feature wash',(862,1452,72),12,.4,lighting,parent=car,target=(816,1452,54))
    doors=[]
    for side,y0,y1,travel in [('south',1430,1452,-24),('north',1452,1474,24)]:
        leaf=box('Cab sliding door '+side,(877,880,y0,y1,1,91),M['cabDoor'],col,parent=car,section=True)
        door_leaves.append(leaf)
        doors.append((leaf,leaf.location.copy(),travel,None))
        for z in [132,255]:
            landing=box('Landing '+str(z)+' door '+side,(880,882,y0,y1,z+1,z+91),M['metal'],col,section=True)
            door_leaves.append(landing)
            for f,v in [(1,False),(364,False),(365,True),(453,True),(454,False)]:
                landing.hide_render=v;landing.hide_viewport=v;landing.keyframe_insert('hide_render',frame=f);landing.keyframe_insert('hide_viewport',frame=f)
            doors.append((landing,landing.location.copy(),travel,z))
    # Context is Blender mesh geometry with source IDs, not a backdrop image.
    contextmat=material('Neighborhood massing',(.13,.15,.18),.85)
    for item in S['osm_context']['buildings']:
        pts=item['footprint_m']; n=len(pts); h=item['height_m']
        verts=[(x,y,z) for z in [0,h] for x,y in pts]
        faces=[tuple(reversed(range(n))),tuple(range(n,2*n))]+[(j,(j+1)%n,(j+1)%n+n,j+n) for j in range(n)]
        mesh=bpy.data.meshes.new('OSM footprint');mesh.from_pydata(verts,[],faces);mesh.update()
        o=bpy.data.objects.new('OSM building '+str(item['osm_id']),mesh);context.objects.link(o);mesh.materials.append(contextmat)
        o['source']='© OpenStreetMap contributors / ODbL 1.0; heights and registration approximate'
    ground=box('Context pavement',(-6000,8000,-6000,8000,-10,-8),texture(material('Damp pavement',(.027,.037,.045),.3),'stone'),context)
    # Draw the guidance on floors only; it never travels vertically up the shaft.
    for name,start,end,z in [('R1',6.5,14.4,132.5),('R2',19.3,26,255.5)]:
        cu=bpy.data.curves.new(name+' guidance ribbon','CURVE');cu.dimensions='3D';cu.bevel_depth=.012;cu.bevel_resolution=2
        sp=cu.splines.new('POLY');pts=[point(start+(end-start)*j/160) for j in range(161)];sp.points.add(len(pts)-1)
        for p,v in zip(sp.points,pts):p.co=(v.x,v.y,z*I,1)
        o=bpy.data.objects.new(name+' floor guidance',cu);col.objects.link(o);cu.materials.append(M['gold'])
        for f in range(1,LAST+1):
            cu.bevel_factor_end=max(0.,min(1.,(((f-1)/FPS)+1.5-start)/(end-start)));cu.keyframe_insert('bevel_factor_end',frame=f)
    # One native Follow Path camera and one Track To target, with time-mapped
    # controls sampled from the source cubic Bezier segments at film frames.
    poses=[trajectory((f-1)/FPS) for f in range(1,LAST+1)]
    cu=bpy.data.curves.new('Cubic Bezier flight / time-sampled controls','CURVE');cu.dimensions='3D';cu.resolution_u=1
    sp=cu.splines.new('BEZIER');sp.bezier_points.add(LAST-1)
    distances=[0.]
    for j,(pos,_) in enumerate(poses):
        p=sp.bezier_points[j];p.co=pos;p.handle_left_type=p.handle_right_type='VECTOR'
        if j:distances.append(distances[-1]+(pos-poses[j-1][0]).length)
    path=bpy.data.objects.new('Flight route / editable Bezier curve',cu);rig.objects.link(path);path.hide_render=True
    path.hide_set(True)
    cam=bpy.data.objects.new('Owner drone camera',bpy.data.cameras.new('Portrait 22 mm architectural lens'));rig.objects.link(cam);scene.camera=cam
    cam.data.lens=22;cam.data.sensor_fit='VERTICAL';cam.data.sensor_height=32;cam.data.clip_start=.025;cam.data.clip_end=500
    follow=cam.constraints.new('FOLLOW_PATH');follow.target=path;follow.use_fixed_location=True
    target=empty('Camera look target / animated',rig)
    track=cam.constraints.new('TRACK_TO');track.target=target;track.track_axis='TRACK_NEGATIVE_Z';track.up_axis='UP_Y'
    for f,((pos,look),dist) in enumerate(zip(poses,distances),1):
        follow.offset_factor=dist/distances[-1];follow.keyframe_insert('offset_factor',frame=f)
        target.location=look;target.keyframe_insert('location',frame=f)
        t=(f-1)/FPS;car.location.z=(132+123*smooth(16,17.8,t))*I;car.keyframe_insert('location',frame=f)
        for hinge,angle in hinges:
            hinge.rotation_euler.z=angle*smooth(4,5.25,t)*(1-smooth(7.1,8.1,t));hinge.keyframe_insert('rotation_euler',frame=f)
        op=smooth(12.0,13.15,t)*(1-smooth(15.3,15.9,t))+smooth(17.7,18.4,t)*(1-smooth(19.7,20.3,t))
        for leaf,home,travel,level in doors:
            value=op if level is None else (smooth(12,13.15,t)*(1-smooth(15.3,15.9,t)) if level==132 else smooth(17.7,18.4,t)*(1-smooth(19.7,20.3,t)))
            leaf.location=home+Vector((0,travel*I*value,0));leaf.keyframe_insert('location',frame=f)
    # A moving Boolean volume removes the east side continuously as the camera
    # pulls back. The remaining walls shift into frosted glass and brass edges.
    cutter=box('Animated architectural section volume',(1100,4000,500,1800,100,410),M['ink'],rig)
    cutter.hide_render=True;cutter.display_type='WIRE';cutter.hide_set(True)
    for o in SECTION:
        mod=o.modifiers.new('Animated east-side section','BOOLEAN');mod.object=cutter;mod.operation='DIFFERENCE';mod.solver='EXACT'
        for f,v in [(1,False),(360,False),(361,True),(460,True),(461,False)]:mod.show_render=v;mod.show_viewport=v;mod.keyframe_insert('show_render',frame=f);mod.keyframe_insert('show_viewport',frame=f)
    for f in range(1,LAST+1):
        t=(f-1)/FPS;cutx=1100-205*smooth(15,16,t)+205*smooth(18.2,19.15,t)
        cutter.location.x=(cutx+(4000-1100)/2)*I;cutter.keyframe_insert('location',frame=f)
    # Keep the cab's walnut rear panel and bronze doors solid so the rising car
    # remains the visual anchor while architectural surfaces become glass.
    for key in ['wall','ceiling','carpet','stone','cabDoor']:ghost_material(M[key])
    edgeMat=material('Section brass edges',(.7,.44,.15),.4,emission=.6)
    shaft=box('Elevator shaft / section reference',(810,885,1424,1480,132,360),edgeMat,rig)
    wire=shaft.modifiers.new('Gold vertical shaft outline','WIREFRAME');wire.thickness=.006
    for f,v in [(1,True),(371,True),(372,False),(440,False),(441,True)]:shaft.hide_render=v;shaft.hide_viewport=v;shaft.keyframe_insert('hide_render',frame=f);shaft.keyframe_insert('hide_viewport',frame=f)
    for o in SECTION:
        if o.name.startswith('Cab ') or 'diffuser' in o.name or 'luminaire' in o.name or 'LED' in o.name:continue
        edge=bpy.data.objects.new(o.name+' / section edges',o.data.copy());col.objects.link(edge);edge.matrix_world=o.matrix_world.copy()
        if o.parent:edge.parent=o.parent;edge.matrix_local=o.matrix_local.copy()
        edge.data.materials.clear();edge.data.materials.append(edgeMat)
        wire=edge.modifiers.new('Brass structural edge outline','WIREFRAME');wire.thickness=.002;wire.use_replace=True
        for f,v in [(1,True),(371,True),(372,False),(440,False),(441,True)]:edge.hide_render=v;edge.hide_viewport=v;edge.keyframe_insert('hide_render',frame=f);edge.keyframe_insert('hide_viewport',frame=f)
    # Exterior illumination and context use blue-hour colors; the corridor
    # receives actual area-light bounce from its own native luminaires.
    scene.world.use_nodes=True;bg=scene.world.node_tree.nodes.get('Background');bg.inputs['Color'].default_value=(.18,.29,.48,1);bg.inputs['Strength'].default_value=.32
    scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=16;scene.cycles.use_denoising=True
    scene.cycles.max_bounces=6;scene.cycles.transmission_bounces=4;scene.cycles.transparent_max_bounces=8
    scene.render.resolution_x=540;scene.render.resolution_y=960;scene.render.resolution_percentage=100
    scene.render.fps=FPS;scene.frame_start=1;scene.frame_end=LAST;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGB'
    scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast'
    tree=bpy.data.node_groups.new('Highland subtle architectural bloom','CompositorNodeTree')
    tree.interface.new_socket(name='Image',in_out='OUTPUT',socket_type='NodeSocketColor')
    scene.compositing_node_group=tree;nodes=tree.nodes;links=tree.links
    layers=nodes.new('CompositorNodeRLayers');glow=nodes.new('CompositorNodeGlare')
    glow.inputs['Type'].default_value='Fog Glow';glow.inputs['Quality'].default_value='Medium'
    glow.inputs['Threshold'].default_value=2;glow.inputs['Strength'].default_value=.18;glow.inputs['Size'].default_value=.2
    composite=nodes.new('NodeGroupOutput');links.new(layers.outputs['Image'],glow.inputs['Image']);links.new(glow.outputs['Image'],composite.inputs['Image'])
    scene.render.use_persistent_data=True
    scene['source_spec_sha256']=hashlib.sha256(SPEC_FILE.read_bytes()).hexdigest()
    scene['scope']='Native editable exterior, lobby, corridors, doors, elevator and camera animation. Interior faces and finishes illustrative.'
    scene['source_sheets']='A2.03/A2.04 circulation; A3.11 R1/R2 datums; exterior source model retains its own provenance.'
    scene['osm_attribution']='© OpenStreetMap contributors / ODbL 1.0'
    import audio
    audio.BUILD=output.parent;audio.BUILD.mkdir(parents=True,exist_ok=True)
    soundtrack=audio.synthesize();editor=scene.sequence_editor_create()
    editor.strips.new_sound('Architectural ambience and elevator chimes',str(soundtrack),channel=1,frame_start=1)
    scene.render.use_sequencer=False
    bpy.ops.file.pack_all()
    scene.frame_set(1);bpy.context.view_layer.update()
    output.parent.mkdir(parents=True,exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(output),compress=True)
    # Validate the evaluated constrained camera, not just the source waypoints.
    failures=[];max_error=0.
    for f in range(1,LAST+1):
        scene.frame_set(f);bpy.context.view_layer.update();pos=cam.matrix_world.translation;t=(f-1)/FPS
        max_error=max(max_error,(pos-poses[f-1][0]).length)
        if 6.3<t<15.1 or 19.2<t<=26:
            for wall,b in WALLS:
                x0,x1,y0,y1,z0,z1=b
                if x0-.035<pos.x<x1+.035 and y0-.035<pos.y<y1+.035 and z0<pos.z<z1:
                    failures.append({'frame':f,'wall':wall.name})
        if 5.7<t<15.1 or 19.2<t<=26:
            for leaf in door_leaves:
                local=leaf.matrix_world.inverted()@pos
                lo=[min(v[j] for v in leaf.bound_box)-.025 for j in range(3)]
                hi=[max(v[j] for v in leaf.bound_box)+.025 for j in range(3)]
                if all(lo[j]<local[j]<hi[j] for j in range(3)):failures.append({'frame':f,'door':leaf.name})
    scene.frame_set(1)
    report={'blender':bpy.app.version_string,'frames':LAST,'fps':FPS,'objects':len(scene.objects),'native_meshes':sum(o.type=='MESH' for o in col.objects),'native_lights':len(lighting.objects),'camera_constraints':[c.type for c in cam.constraints],'max_camera_path_error_m':round(max_error,5),'wall_collisions':failures,'r1_to_r2_rise_in':123,'source_spec_sha256':scene['source_spec_sha256']}
    output.with_suffix('.validation.json').write_text(json.dumps(report,indent=2)+'\n')
    if failures or max_error>.08:raise RuntimeError('Native camera clearance/path validation failed: '+json.dumps(report))
    print('Native Blender scene validated:',json.dumps(report))
    return scene


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,default=ROOT/'build/highland-blender/Highland-walkthrough.blend');p.add_argument('--reuse',action='store_true');p.add_argument('--frames',default='');p.add_argument('--start',type=int);p.add_argument('--end',type=int);p.add_argument('--width',type=int,default=540);p.add_argument('--height',type=int,default=960);p.add_argument('--samples',type=int,default=16);p.add_argument('--threads',type=int,default=0);a=p.parse_args()
    scene=None
    if a.reuse:bpy.ops.wm.open_mainfile(filepath=str(a.output));scene=bpy.context.scene
    else:scene=build(a.output)
    scene.render.resolution_x=a.width;scene.render.resolution_y=a.height;scene.cycles.samples=a.samples
    if a.threads:scene.render.threads_mode='FIXED';scene.render.threads=a.threads
    frames=[int(f) for f in a.frames.split(',') if f] if a.frames else list(range(a.start,a.end+1)) if a.start is not None else []
    renderdir=a.output.parent/'frames';renderdir.mkdir(exist_ok=True)
    for f in frames:
        scene.frame_set(f);scene.render.filepath=str(renderdir/f'frame_{f:04d}.png');start=time.monotonic();bpy.ops.render.render(write_still=True);print(f'FRAME {f} {time.monotonic()-start:.2f}s',flush=True)


if __name__=='__main__':main()
