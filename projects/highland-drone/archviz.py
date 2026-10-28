"""Illustrative archviz finishes and planting; all geometry is native Blender.

The HDRI is CC0 from Poly Haven. Botanical geometry and art are deterministic
procedural assets, not a surveyed planting scheme or licensed asset library.
"""
import math
import random
from pathlib import Path

import bpy
from mathutils import Vector

I = .0254


def surface(mat, kind):
    """Meter-scale texture detail, independent of each object's dimensions."""
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bsdf = nodes.get('Principled BSDF')
    for node in list(nodes):
        if node not in (bsdf, nodes.get('Material Output')):
            nodes.remove(node)
    links.new(bsdf.outputs[0], nodes.get('Material Output').inputs['Surface'])
    coord = nodes.new('ShaderNodeTexCoord')
    noise = nodes.new('ShaderNodeTexNoise')
    noise.inputs['Detail'].default_value = 3
    links.new(coord.outputs['Object'], noise.inputs['Vector'])
    bump = nodes.new('ShaderNodeBump')
    bump.inputs['Strength'].default_value = .075
    bump.inputs['Distance'].default_value = .0006
    links.new(noise.outputs['Fac'], bump.inputs['Height'])
    links.new(bump.outputs['Normal'], bsdf.inputs['Normal'])
    rough = nodes.new('ShaderNodeMapRange')
    rough.inputs['To Min'].default_value = .57 if kind == 'plaster' else .25
    rough.inputs['To Max'].default_value = .72 if kind == 'plaster' else .38
    links.new(noise.outputs['Fac'], rough.inputs['Value'])
    links.new(rough.outputs['Result'], bsdf.inputs['Roughness'])
    noise.inputs['Scale'].default_value = 180 if kind == 'plaster' else 35
    if kind == 'wood':
        stretch = nodes.new('ShaderNodeVectorMath'); stretch.operation = 'MULTIPLY'
        stretch.inputs[1].default_value = (55, 55, 1.2)
        links.new(coord.outputs['Object'], stretch.inputs[0])
        links.new(stretch.outputs[0], noise.inputs['Vector'])
        noise.inputs['Scale'].default_value = 1
        ramp = nodes.new('ShaderNodeValToRGB')
        ramp.color_ramp.elements[0].color = (.045, .023, .012, 1)
        ramp.color_ramp.elements[1].color = (.115, .061, .029, 1)
        links.new(noise.outputs['Fac'], ramp.inputs[0])
        links.new(ramp.outputs[0], bsdf.inputs['Base Color'])
        bsdf.inputs['Coat Weight'].default_value = .18
    elif kind == 'carpet':
        waves = []
        for direction in ('X', 'Y'):
            w = nodes.new('ShaderNodeTexWave'); w.wave_type = 'BANDS'; w.bands_direction = direction
            w.inputs['Scale'].default_value = 340; w.inputs['Distortion'].default_value = .15
            links.new(coord.outputs['Object'], w.inputs['Vector']); waves.append(w)
        weave = nodes.new('ShaderNodeMath'); weave.operation = 'MULTIPLY'
        for j, w in enumerate(waves): links.new(w.outputs['Fac'], weave.inputs[j])
        links.new(weave.outputs[0], bump.inputs['Height'])
        bump.inputs['Distance'].default_value = .001; bump.inputs['Strength'].default_value = .16
        rough.inputs['To Min'].default_value = .82; rough.inputs['To Max'].default_value = .96
        tiles = nodes.new('ShaderNodeTexBrick'); tiles.offset = .5
        tiles.inputs['Scale'].default_value = 1; tiles.inputs['Brick Width'].default_value = .5
        tiles.inputs['Row Height'].default_value = .5; tiles.inputs['Mortar Size'].default_value = .0008
        tiles.inputs['Color1'].default_value = (.055, .068, .068, 1)
        tiles.inputs['Color2'].default_value = (.085, .096, .091, 1)
        tiles.inputs['Mortar'].default_value = (.04, .05, .05, 1)
        links.new(coord.outputs['Object'], tiles.inputs['Vector'])
        links.new(tiles.outputs['Color'], bsdf.inputs['Base Color'])
        bsdf.inputs['Sheen Weight'].default_value = .25
    elif kind == 'stone':
        tile = nodes.new('ShaderNodeTexBrick'); tile.offset = 0
        tile.inputs['Scale'].default_value = 1; tile.inputs['Brick Width'].default_value = .9
        tile.inputs['Row Height'].default_value = .6; tile.inputs['Mortar Size'].default_value = .0015
        tile.inputs['Mortar Smooth'].default_value = .001
        tile.inputs['Color1'].default_value = (.22, .245, .235, 1)
        tile.inputs['Color2'].default_value = (.30, .315, .29, 1)
        tile.inputs['Mortar'].default_value = (.10, .12, .11, 1)
        links.new(coord.outputs['Object'], tile.inputs['Vector'])
        links.new(tile.outputs['Color'], bsdf.inputs['Base Color'])
        grout = nodes.new('ShaderNodeBump'); grout.inputs['Distance'].default_value = .0012
        grout.inputs['Strength'].default_value = .3; grout.invert = True
        links.new(tile.outputs['Fac'], grout.inputs['Height'])
        links.new(bump.outputs[0], grout.inputs['Normal']); links.new(grout.outputs[0], bsdf.inputs['Normal'])
    elif kind == 'metal':
        stretch = nodes.new('ShaderNodeVectorMath'); stretch.operation = 'MULTIPLY'
        stretch.inputs[1].default_value = (500, 500, 1)
        links.new(coord.outputs['Object'], stretch.inputs[0]); links.new(stretch.outputs[0], noise.inputs['Vector'])
        noise.inputs['Scale'].default_value = 1
        rough.inputs['To Min'].default_value = .25; rough.inputs['To Max'].default_value = .3
        bsdf.inputs['Anisotropic'].default_value = .65
        bump.inputs['Distance'].default_value = .00008


def upgrade(scene, M, col, lighting, box, area, material):
    rng = random.Random(200)
    for key, kind in [('wall','plaster'),('ceiling','plaster'),('wood','wood'),
                      ('carpet','carpet'),('stone','stone'),('cabStone','stone'),
                      ('metal','metal'),('cabDoor','metal'),('brass','metal')]:
        surface(M[key], kind)
    # The floor trail is intentionally thin and gently breathing, not a stripe.
    glow = M['gold'].node_tree.nodes.get('Principled BSDF').inputs['Emission Strength']
    for frame in range(1, 625, 6):
        glow.default_value = 1.5 + .3*math.sin(frame/24*math.tau*.4)
        glow.keyframe_insert('default_value', frame=frame)
    for obj in scene.objects:
        if 'floor guidance' in obj.name: obj.data.bevel_depth = .007
        if obj.name.startswith('Lobby diffuser '):
            # Narrow linear architectural lenses replace broad glowing panels.
            for vertex in obj.data.vertices: vertex.co.y *= .22
        if obj.type=='LIGHT' and obj.name.startswith('Lobby soft downlight '):
            obj.data.energy=50

    dress = bpy.data.collections.new('Archviz / illustrative furniture and planting')
    scene.collection.children.link(dress)
    steel = material('Entrance stainless steel', (.55,.58,.59), .23, .9)
    ceramic = material('Charcoal ceramic planters', (.045,.055,.052), .38)
    soil = material('Planter soil', (.018,.012,.008), .98)
    bark = material('Fine branch bark', (.085,.046,.021), .9)
    leaves = [material('Leaf variation '+str(j), c, .46) for j,c in enumerate(
        [(.045,.10,.018),(.085,.17,.03),(.13,.22,.045),(.06,.135,.028)])]
    for mat in leaves:
        n,l=mat.node_tree.nodes,mat.node_tree.links;b=n.get('Principled BSDF')
        translucent=n.new('ShaderNodeBsdfTranslucent');translucent.inputs[0].default_value=b.inputs['Base Color'].default_value
        mix=n.new('ShaderNodeMixShader');mix.inputs[0].default_value=.22
        l.new(b.outputs[0],mix.inputs[1]);l.new(translucent.outputs[0],mix.inputs[2]);l.new(mix.outputs[0],n.get('Material Output').inputs[0])

    def exterior_time(obj):
        for frame,value in [(1,False),(146,False),(147,True)]:
            obj.hide_render=value;obj.hide_viewport=value
            obj.keyframe_insert('hide_render',frame=frame);obj.keyframe_insert('hide_viewport',frame=frame)
        return obj

    def tube(name, points, radius, mat):
        cu=bpy.data.curves.new(name,'CURVE');cu.dimensions='3D';cu.bevel_depth=radius;cu.bevel_resolution=2
        sp=cu.splines.new('POLY');sp.points.add(len(points)-1)
        for p,co in zip(sp.points,points):p.co=(*co,1)
        obj=bpy.data.objects.new(name,cu);dress.objects.link(obj);cu.materials.append(mat);return obj

    def leaf_cloud(name, center, dims, count, exterior=False, elongated=False):
        vertices=[];faces=[];colors=[];center=Vector(center)
        for k in range(count):
            v=Vector((rng.gauss(0,1),rng.gauss(0,1),rng.gauss(0,1))).normalized()*rng.random()**(1/3)
            p=center+Vector(tuple(v[j]*dims[j]*.5 for j in range(3)))
            direction=Vector((rng.uniform(-1,1),rng.uniform(-1,1),rng.uniform(-.5,.8))).normalized()
            side=direction.cross(Vector((0,0,1))).normalized()
            length=rng.uniform(.10,.21)*(1.8 if elongated else 1)
            width=length*(.18 if elongated else .40);base=len(vertices)
            vertices.extend([p-direction*length/2,p-side*width,p+Vector((0,0,.018)),p+side*width,p+direction*length/2])
            faces.extend([(base,base+1,base+2),(base+1,base+4,base+2),(base+4,base+3,base+2),(base+3,base,base+2)])
            colors.extend([rng.randrange(len(leaves))]*4)
        mesh=bpy.data.meshes.new(name);mesh.from_pydata(vertices,[],faces);mesh.update()
        obj=bpy.data.objects.new(name,mesh);dress.objects.link(obj)
        for m in leaves:mesh.materials.append(m)
        for polygon,color in zip(mesh.polygons,colors):polygon.material_index=color;polygon.use_smooth=True
        obj['basis']='Procedural illustrative planting; not a botanical or site survey'
        if exterior:exterior_time(obj)
        return obj

    # Keep the photo-informed tree placement and branching, replace opaque blobs
    # with individually shaped, curved leaves and small branch tips.
    crowns=[o for o in list(scene.objects) if '-crown-' in o.name or o.name.startswith('south-hedge-')]
    leaf_count=0
    for old in crowns:
        bb=[old.matrix_world@Vector(v) for v in old.bound_box]
        lo=Vector(tuple(min(v[j] for v in bb) for j in range(3)))
        hi=Vector(tuple(max(v[j] for v in bb) for j in range(3)))
        center=(lo+hi)/2;dims=hi-lo;count=700 if '-crown-' in old.name else 230
        leaf_cloud(old.name+' / individual leaves',center,dims,count,True);leaf_count+=count
        if '-crown-' in old.name:
            for j in range(5):
                end=center+Vector((rng.uniform(-1,1)*dims.x*.35,rng.uniform(-1,1)*dims.y*.35,rng.uniform(-.5,.5)*dims.z*.5))
                exterior_time(tube('Fine canopy twig',[center-Vector((0,0,.55)),end],.009,bark))
        bpy.data.objects.remove(old,do_unlink=True)

    # Window recesses: actual back panels, softly folded curtains and warm glow.
    curtain=material('Apartment linen',(.52,.43,.30),.9,emission=.12)
    warm=material('Apartment warm interior',(.65,.36,.13),.8,emission=.55)
    windows=[o for o in scene.objects if o.type=='MESH' and '-glazing' in o.name and any(f'-R{j}-' in o.name for j in (2,3,4,5))]
    lit_windows=0
    for window in windows:
        if rng.random()>.52:continue
        bb=[window.matrix_world@Vector(v) for v in window.bound_box]
        lo=Vector(tuple(min(v[j] for v in bb) for j in range(3)));hi=Vector(tuple(max(v[j] for v in bb) for j in range(3)))
        axis=0 if hi.x-lo.x < hi.y-lo.y else 1;along=1-axis
        face=window.name.split('-')[0];outward=1 if face in ('east','north') else -1
        # A window-specific low-opacity reflective pane reveals the recess.
        glass=M['glass'].copy();glass.name=window.name+' / reflective glass'
        b=glass.node_tree.nodes.get('Principled BSDF');b.inputs['Base Color'].default_value=(.93,.96,.98,1)
        window.data.materials.clear();window.data.materials.append(glass)
        bounds=[]
        for j in range(3):
            if j==axis:
                c=(lo[j]+hi[j])/2-outward*.38;bounds.extend((c/I-.5,c/I+.5))
            else:bounds.extend((lo[j]/I,hi[j]/I))
        back=box('Warm apartment recess '+window.name,tuple(bounds),warm,dress);exterior_time(back)
        for edge in (-1,1):
            for fold in range(6):
                bounds=[]
                for j in range(3):
                    if j==axis:
                        c=(lo[j]+hi[j])/2-outward*(.16+.025*math.sin(fold*1.7));bounds.extend((c/I-.25,c/I+.25))
                    elif j==along:
                        width=(hi[j]-lo[j])*.17/6;c=(lo[j] if edge<0 else hi[j])+(-edge)*(fold+.5)*width
                        bounds.extend(((c-width*.55)/I,(c+width*.55)/I))
                    else:bounds.extend((lo[j]/I,hi[j]/I))
                exterior_time(box('Apartment curtain fold',tuple(bounds),curtain,dress))
        lit_windows+=1

    # Entry handrails follow the existing assumed five-step run, with returns.
    for y in (1263,1401):
        points=[(1544*I,y*I,168*I),(1550*I,y*I,168*I),(1616*I,y*I,133*I),(1622*I,y*I,133*I)]
        exterior_time(tube('Entry stainless handrail',points,.019,steel))
        for x,z in [(1552,167),(1608,137)]:
            exterior_time(tube('Entry handrail post',[(x*I,y*I,(z-36)*I),(x*I,y*I,z*I)],.016,steel))
    mat=material('Recessed entry mat',(.035,.043,.038),.95);surface(mat,'carpet')
    box('Textured entry welcome mat',(1430,1470,1294,1370,132.02,132.25),mat,col)
    for x,y in [(1524,1267),(1524,1400)]:
        exterior_time(box('Entrance planter',(x-10,x+10,y-10,y+10,132,150),ceramic,dress))
        exterior_time(box('Entrance planter soil',(x-9,x+9,y-9,y+9,149,150),soil,dress))
        leaf_cloud('Entrance evergreen planting',(x*I,y*I,167*I),(.7,.7,1),350,True,True)
    for y in (1287,1375):
        exterior_time(box('Canopy recessed downlight',(1512,1518,y-3,y+3,238.6,239),M['led'],dress))
        exterior_time(area('Canopy accent downlight',(1515,y,237),25,.18,lighting))

    # Lobby furniture hugs the north wall, well outside the walking centerline.
    box('Lobby floating console top',(1230,1310,1389,1403,163,165),M['wood'],col,wall=True)
    for x in (1235,1305):box('Console brass leg',(x,x+1,1393,1401,132,163),M['brass'],col,wall=True)
    art=material('Art / warm ivory',(.68,.59,.45),.85)
    box('Lobby artwork walnut frame',(1220,1320,1401,1404,176,218),M['trim'],col)
    box('Lobby artwork canvas',(1222,1318,1400.5,1401,178,216),art,col)
    for j in range(11):
        color=material('Abstract art pigment '+str(j),(.07+.012*j,.12+.009*j,.12+.004*j),.9)
        box('Abstract landscape band',(1223+j*8,1230+j*8,1400.1,1400.5,180+j%3*5,201+j%4*3),color,col)
    for x,y in [(1360,1389),(1140,1388)]:
        box('Lobby stone planter',(x-7,x+7,y-7,y+7,132,154),ceramic,col,wall=True)
        tube('Indoor plant stem',[(x*I,y*I,153*I),(x*I,y*I,200*I)],.012,bark)
        leaf_cloud('Indoor plant foliage',(x*I,y*I,186*I),(.65,.6,1.1),100,False,True)
    # Wall-wash beams give door recesses rhythm without flattening the corridor.
    # These are illustrative spot optics, not manufacturer IES photometry.
    for z,label in [(132,'R1'),(255,'R2')]:
        for x,y in [(937,750),(937,1090),(893,1020),(893,1170)]:
            data=bpy.data.lights.new(label+' recessed wall wash','SPOT');data.energy=16
            data.color=(1,.79,.55);data.spot_size=math.radians(72);data.spot_blend=.65;data.shadow_soft_size=.045
            obj=bpy.data.objects.new(data.name,data);lighting.objects.link(obj);obj.location=Vector((x,y,z+98))*I
            aim=Vector((950 if x>915 else 880,y,z+64))*I
            obj.rotation_euler=(aim-obj.location).to_track_quat('-Z','Y').to_euler()
            box(label+' recessed wash trim',(x-2,x+2,y-2,y+2,z+100,z+100.5),M['brass'],col)
    area('Lobby art wash',(1270,1380,225),25,.8,lighting,target=(1270,1400,194))

    # A genuine high-dynamic-range sky is packed into the editable scene.
    hdr=Path(__file__).resolve().parents[2]/'assets/hdri/kloofendal_48d_partly_cloudy_puresky_1k.hdr'
    world=scene.world;world.use_nodes=True;n,l=world.node_tree.nodes,world.node_tree.links;n.clear()
    env=n.new('ShaderNodeTexEnvironment');env.image=bpy.data.images.load(str(hdr),check_existing=True)
    tex=n.new('ShaderNodeTexCoord');mapping=n.new('ShaderNodeMapping');mapping.inputs['Rotation'].default_value[2]=math.radians(110)
    l.new(tex.outputs['Normal'],mapping.inputs['Vector']);l.new(mapping.outputs[0],env.inputs[0])
    bg=n.new('ShaderNodeBackground');bg.inputs['Strength'].default_value=.7
    out=n.new('ShaderNodeOutputWorld');l.new(env.outputs[0],bg.inputs[0]);l.new(bg.outputs[0],out.inputs['Surface'])
    for obj in scene.objects:
        if obj.type=='LIGHT' and obj.data.type=='SUN':
            obj.data.energy=1.6;obj.data.angle=math.radians(12);obj.data.color=(1,.86,.68)
    for name in ('road','paving'):
        mat=bpy.data.materials.get(name)
        if mat:
            b=mat.node_tree.nodes.get('Principled BSDF');b.inputs['Roughness'].default_value=.25 if name=='road' else .48
            n,l=mat.node_tree.nodes,mat.node_tree.links;noise=n.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=35
            bump=n.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.16;bump.inputs['Distance'].default_value=.002
            l.new(noise.outputs['Fac'],bump.inputs['Height']);l.new(bump.outputs[0],b.inputs['Normal'])
    scene['presentation_look']='Archviz materials, individual procedural leaves, CC0 Poly Haven HDRI, illustrative furniture and warm window recesses'
    scene['hdri_attribution']='Kloofendal 48d Partly Cloudy (Pure Sky) / Poly Haven / CC0'
    scene['archviz_plant_leaves']=leaf_count
    scene['archviz_warm_windows']=lit_windows
    scene['fixture_photometry']='Illustrative spot and area optics; no manufacturer IES profiles used'
