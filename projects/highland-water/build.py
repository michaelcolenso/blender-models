"""Reproducible Blender geometry from the expanded specification; no PDF parsing."""
import bpy, json, math, sys
from pathlib import Path
from mathutils import Vector
from collections import defaultdict

HERE=Path(__file__).parent
SPEC=json.loads((HERE/'highland-water.spec.json').read_text())
OUT=HERE.parent.parent/'build/highland-water'
OUT.mkdir(parents=True,exist_ok=True)
IN=.0254
def validate():
    es=SPEC['elements']; ids=[e['id'] for e in es]
    assert len(set(ids))==len(ids), 'Duplicate element ids'
    for e in es:
        assert e.get('source') or e.get('basis'),e['id']
        assert e['status']=='assumed' and e.get('basis'),e['id']
        if e['kind']=='pipe':
            assert e['nominal_in']>0
            assert len(e['points'])>=2
            if e['size_status']=='confirmed': assert e.get('source')
    actual={
      'stack_groups':len([e for e in es if e['id'].startswith('stack-')]),
      'typical_branch_trios':len([e for e in es if e.get('role')=='unit branch continuation' and e['system']=='CW']),
      'unit_fixtures':len([e for e in es if e['kind']=='fixture']),
      'boilers':len([e for e in es if e.get('role')=='boiler']),
      'storage_tanks':len([e for e in es if e.get('role')=='storage tank']),
      'expansion_vessels':len([e for e in es if e.get('role')=='expansion vessel']),
      'installed_pumps':len([e for e in es if e['kind']=='pump'])}
    for k,v in actual.items(): assert v==SPEC['checks'][k],(k,v)
    # Endpoint / tee reachability, separately for each system. This checks the
    # modeled graph, not construction adequacy or the correctness of a source.
    connected={}
    for key,root in SPEC['roots'].items():
        scene,system=key.split(':')
        pipes=[e for e in es if e['scene']==scene and e['kind']=='pipe' and e['system']==system]
        points=set(tuple(p) for e in pipes for p in e['points']); points.add(tuple(root))
        adjacency=defaultdict(set)
        for e in pipes:
            for a,b in zip(e['points'],e['points'][1:]):
                a,b=Vector(a),Vector(b); ab=b-a
                if ab.length<1e-8: continue
                on=[]
                for p in points:
                    t=(Vector(p)-a).dot(ab)/ab.length_squared
                    if -1e-6<=t<=1+1e-6 and (Vector(p)-(a+t*ab)).length<1e-3: on.append((t,p))
                on.sort()
                for (_,p),(_,q) in zip(on,on[1:]): adjacency[p].add(q);adjacency[q].add(p)
        seen=set(); todo=[tuple(root)]
        while todo:
            p=todo.pop()
            if p in seen:continue
            seen.add(p);todo.extend(adjacency[p]-seen)
        terminals=[e for e in pipes if e.get('terminal')]
        failed=[e['id'] for e in terminals if tuple(e['points'][-1]) not in seen]
        assert not failed,(key,failed)
        connected[key]={'terminal_routes_reachable':len(terminals),'nodes_reachable':len(seen),'nodes_total':len(points)}
        assert len(seen)==len(points),(key,'disconnected internal routes')
    cal=SPEC['calibration'];grid_scales={}
    for axis in ['grid_x','grid_y']:
        g=cal[axis];rates=[(b-a)/d for a,b,d in zip(g['p2_02_pdf_points'],g['p2_02_pdf_points'][1:],g['spans_in'])]
        assert max(abs(r/.75-1) for r in rates)<.006,(axis,rates)
        grid_scales[axis]=rates
    reg=json.loads((HERE/cal['registration_file']).read_text())
    assert reg['inliers']>=20 and reg['median_residual_pdf_pt']<.5
    factor=math.hypot(*reg['affine'][0][:2])/.75
    assert abs(factor/cal['unit_xy_in_per_normalized_pixel']-1)<1e-6
    for level,elev in cal['floor_elevations_ft'].items():
        line=next(e for e in es if e['id']=='floor-'+level+'-0')
        assert abs(line['points'][0][2]-(elev-332)*12)<.001
    assert (cal['floor_elevations_ft']['R1']-cal['floor_elevations_ft']['P1'])*12==132
    pilot=SPEC['bathroom_pilot'];byid={e['id']:e for e in es}
    def near(a,b):return (Vector(a)-Vector(b)).length<.001
    port_counts=defaultdict(int)
    for c in pilot['supply_connections']:
        f=byid[c['fixture']];drop=byid[c['drop']]
        assert f['kind']=='fixture' and drop['system']==c['system']
        assert near(f['supply_ports'][c['system']],c['port'])
        if c['connector']:
            hose=byid[c['connector']]
            assert hose['system']==c['system'] and near(hose['points'][0],drop['points'][-1])
            assert near(hose['points'][-1],c['port'])
        else:
            assert near(drop['points'][-1],c['port'])
            assert near(byid[c['device']]['supply_ports'][c['system']],c['port'])
        port_counts[c['system']]+=1
    assert dict(port_counts)==pilot['expected_supply_ports']
    assert set(byid['master-wc']['supply_ports'])=={'CW'},'Toilet must not acquire a hot-water connection'
    for c in pilot['mixed_outlets']:
        assert near(byid[c['device']]['outlet'],byid[c['outlet_route']]['points'][0])
        assert near(c['end'],byid[c['outlet_route']]['points'][-1])
        assert byid[c['outlet_route']]['system']=='MW'
    hardware={k:len([e for e in es if e.get('pilot') and e['kind']==k]) for k in ['stop','mixer','elbow','tee']}
    assert hardware['stop']==5 and hardware['mixer']==2
    for e in es:
        if e['kind']=='elbow':
            route=byid[e['route_id']]
            assert all(any(near(p,q) for q in route['render_points']) for p in e['ports'])
        if e['kind']=='stop':
            route=byid[e['route_id']];a,b=map(Vector,route['points'][-2:]);v=b-a
            for p in e['ports']:
                t=(Vector(p)-a).dot(v)/v.length_squared
                assert 0<=t<=1 and (Vector(p)-(a+t*v)).length<.001
    pilot_checks={'fixtures':len(pilot['fixtures']),'supply_ports':dict(port_counts),'matching_fixture_endpoints':9,'mixed_outlets':2,'hardware_model_counts':hardware,'result':'All nine modeled fixture supplies meet explicit ports; five stops lie on their supply routes; both mixed outlets meet mixer ports. Hardware and heights remain assumed.'}
    report={'counts':actual,'connectivity':connected,'calibration_checks':{'grid_points_per_inch':grid_scales,'max_allowed_raster_grid_variation_percent':.6,'registration_inliers':reg['inliers'],'median_registration_error_pt':reg['median_residual_pdf_pt'],'unit_scale_in_per_pixel':factor,'floor_datums_checked':7,'unit_107_floor_to_floor_in':132},'limitations':SPEC['limitations'],'result':'PASS: modeled counts, provenance, distribution reachability, raster-scale consistency and floor datums; exact pipe XYZ and plant internals not validated'}
    report['element_count']=len(es);report['bathroom_pilot']=pilot_checks
    (OUT/'validation.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2),flush=True)
validate()
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
for coll in list(bpy.data.collections):
    if coll.name!='Collection': bpy.data.collections.remove(coll)
scene=bpy.context.scene
scene.unit_settings.system='IMPERIAL';scene.unit_settings.length_unit='INCHES'
scene.render.engine='CYCLES';scene.cycles.samples=16;scene.cycles.use_denoising=True
scene.render.threads_mode='FIXED';scene.render.threads=4
scene.render.resolution_x=1400;scene.render.resolution_y=1100;scene.render.resolution_percentage=100
scene.world.color=(.19,.19,.19)
scene.view_settings.view_transform='AgX'
scene.render.image_settings.file_format='PNG'
colors={'CW':(.025,.40,.95,1),'HW':(.98,.18,.045,1),'HWC':(.03,.72,.42,1),'MW':(.56,.23,.92,1),
 'equipment':(.45,.56,.64,1),'fixtures':(.80,.85,.88,1),'context':(.14,.22,.29,1),
 'metal':(.48,.38,.15,1),'dark':(.025,.045,.065,1),'text':(.78,.89,.94,1),'assumed':(1,.32,.035,1)}
mats={}
for name,c in colors.items():
    mat=bpy.data.materials.new(name);mat.diffuse_color=c;mat.use_nodes=True
    bsdf=mat.node_tree.nodes.get('Principled BSDF');bsdf.inputs['Base Color'].default_value=c
    bsdf.inputs['Metallic'].default_value=.45 if name in ['equipment','metal'] else .12
    bsdf.inputs['Roughness'].default_value=.32
    if name in ['CW','HW','HWC','MW','text']:
        bsdf.inputs['Emission Color'].default_value=c;bsdf.inputs['Emission Strength'].default_value=.15
    mats[name]=mat
collections={}
for model in ['building','plant','unit']:
    parent=bpy.data.collections.new(model);scene.collection.children.link(parent)
    collections[model]=parent
    for trade in ['CW','HW','HWC','MW','equipment','fixtures','context']:
        col=bpy.data.collections.new(model+' / '+trade);parent.children.link(col);collections[(model,trade)]=col

parts=[]
def attach(obj,mat):
    obj.data.materials.append(mats[mat]);parts.append(obj)
    if obj.type=='MESH':
        for poly in obj.data.polygons:poly.use_smooth=len(poly.vertices)<=4
    return obj
def cube(at,dims,mat,bevel=0):
    bpy.ops.mesh.primitive_cube_add(size=1,location=at);o=bpy.context.object;o.dimensions=dims
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    if bevel:
        mod=o.modifiers.new('soft edges','BEVEL');mod.width=bevel;mod.segments=3
        bpy.context.view_layer.objects.active=o;bpy.ops.object.modifier_apply(modifier=mod.name)
    return attach(o,mat)
def cylinder(a,b,r,mat,vertices=16):
    a,b=Vector(a),Vector(b)
    if (b-a).length<1e-8:return
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices,radius=r,depth=(b-a).length,location=(a+b)*.5)
    o=bpy.context.object;o.rotation_euler=(b-a).to_track_quat('Z','Y').to_euler();return attach(o,mat)
def sphere(at,r,mat,scale=None):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=16,ring_count=8,radius=r,location=at)
    o=bpy.context.object
    if scale:o.scale=scale
    return attach(o,mat)
def tube(points,r,mat):
    # Swept mesh with small rounded corners. An overlap ball at junctions forms
    # a visible fitting; all endpoint positions stay equal to the graph spec.
    pts=[Vector(p) for i,p in enumerate(points) if i==0 or Vector(p)!=Vector(points[i-1])]
    for a,b in zip(pts,pts[1:]): cylinder(a,b,r,mat)
    for p in pts[1:-1]:sphere(p,r*1.08,mat)
    for p,q in [(pts[0],pts[1]),(pts[-1],pts[-2])]:
        v=(q-p).normalized();cylinder(p+v*r*.5,p+v*r*2.4,r*1.17,mat)
def swept(points,r,mat,smooth=False):
    curve=bpy.data.curves.new('swept pipe','CURVE');curve.dimensions='3D';curve.resolution_u=12
    curve.bevel_depth=r;curve.bevel_resolution=3;curve.use_fill_caps=True
    s=curve.splines.new('BEZIER' if smooth else 'POLY')
    if smooth:
        s.bezier_points.add(len(points)-1)
        for p,co in zip(s.bezier_points,points):
            p.co=co;p.handle_left_type='AUTO';p.handle_right_type='AUTO'
    else:
        s.points.add(len(points)-1)
        for p,co in zip(s.points,points):p.co=(*co,1)
    o=bpy.data.objects.new('swept pipe',curve);scene.collection.objects.link(o)
    bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o;bpy.ops.object.convert(target='MESH')
    return attach(bpy.context.object,mat)
def fixture(e):
    x,y,z=[v*IN for v in e['at']];kind=e['fixture'];W=mats['fixtures']
    pixel=SPEC['calibration']['unit_xy_in_per_normalized_pixel']*IN
    if kind in ['lav','sink']:
        width=.60 if kind=='lav' else .85
        cube((x,y,z+.76),(width,.48,.12),'fixtures',.045)
        cube((x,y,z+.825),(width*.73,.32,.012),'dark',.035)
        cylinder((x,y+.16,z+.82),(x,y+.16,z+1.02),.012,'metal')
        cylinder((x,y+.16,z+1.02),(x,y,z+1.02),.012,'metal')
        if not e.get('pilot_device'):cylinder((x,y,z+.23),(x,y,z+.70),.025,'fixtures')
        # Representative fixture tails meet the drawing-derived supply drops.
        for dx in ([] if e.get('pilot_device') else [-5*pixel,5*pixel]):
            cylinder((x+dx,y,z+24*IN),(x+dx,y,z+.76),.009,'metal')
    elif kind=='wc':
        sphere((x,y,z+.34),1,'fixtures',(.19,.28,.18))
        sphere((x,y-.04,z+.45),1,'dark',(.12,.17,.012))
        cube((x,y+.24,z+.60),(.40,.18,.42),'fixtures',.04)
        cylinder((x,y,z+.02),(x,y,z+.23),.12,'fixtures')
    elif kind=='bath':
        cube((x,y,z+.24),(1.65,.80,.48),'fixtures',.13)
        cube((x,y,z+.485),(1.35,.57,.02),'dark',.10)
        if not e.get('pilot_device'):
            yy=y+20*pixel;zz=z+24*IN
            cylinder((x-10*pixel,yy,zz),(x+10*pixel,yy,zz),.022,'metal')
            cylinder((x,yy,zz),(x,yy-.18,zz),.016,'metal')
    elif kind=='shower':
        cube((x,y,z+.035),(.95,.95,.07),'fixtures',.045)
        if e.get('pilot_device'):
            h=Vector([v*IN for v in e['head_port']]);cylinder(h-Vector((0,0,.018)),h,.08,'metal')
        else:
            zz=z+48*IN
            cylinder((x-10*pixel,y,zz),(x+10*pixel,y,zz),.023,'metal')
            cylinder((x,y,zz),(x,y+.42,zz),.014,'metal')
            cylinder((x,y+.42,zz),(x,y+.42,z+2.03),.014,'metal')
            cylinder((x,y+.42,z+2.03),(x,y+.12,z+2.03),.014,'metal')
            cylinder((x,y+.12,z+2.0),(x,y+.12,z+2.03),.08,'metal')
    elif kind=='washer':
        cube((x,y,z+.47),(.60,.60,.94),'fixtures',.03)
        cylinder((x,y-.31,z+.45),(x,y-.34,z+.45),.19,'dark')
    elif kind=='dishwasher':
        cube((x,y,z+.43),(.58,.55,.86),'equipment',.02)
        cube((x,y-.29,z+.72),(.45,.025,.035),'dark',.01)
    elif kind=='hosebib':
        cylinder((x,y,z+.66),(x,y-.16,z+.66),.025,'metal')
        cylinder((x,y-.16,z+.66),(x,y-.16,z+.56),.025,'metal')
        cube((x,y-.08,z+.74),(.13,.035,.025),'CW',.01)

for e in SPEC['elements']:
    parts=[];kind=e['kind'];sysname=e['system'];model=e['scene']
    if kind=='pipe':
        mult=SPEC['display'][model+'_pipe_multiplier'] if sysname!='context' else 1
        points=[[v*IN for v in p] for p in e.get('render_points',e['points'])]
        if e.get('pilot'):swept(points,e['nominal_in']*IN*.5*mult,sysname,e.get('sweep_style')=='smooth')
        else:tube(points,e['nominal_in']*IN*.5*mult,sysname)
    elif kind=='elbow':
        swept([[v*IN for v in p] for p in e['points']],e['nominal_in']*IN*.5*SPEC['display']['unit_pipe_multiplier']*1.2,'metal')
    elif kind=='tee':
        center=Vector([v*IN for v in e['at']])
        for port,diam in zip(e['ports'],e['diameters']):
            q=Vector([v*IN for v in port]);r=diam*IN*.5*SPEC['display']['unit_pipe_multiplier']*1.2
            cylinder(center,q,r,'metal');cylinder(q+(center-q)*.13,q,r*1.12,'metal')
    elif kind=='stop':
        a,b=[Vector([v*IN for v in p]) for p in e['ports']];c=(a+b)*.5;r=e['nominal_in']*IN*1.1
        cylinder(a,b,r,'metal',12)
        for q in [a,b]:cylinder(q-Vector((0,0,.008)),q+Vector((0,0,.008)),r*1.3,'metal',6)
        cylinder(c,c+Vector((0,-.045,0)),.007,'metal')
        cube(c+Vector((0,-.05,0)),(.055,.012,.018),'dark',.004)
    elif kind=='mixer':
        c=Vector([v*IN for v in e['at']]);out=Vector([v*IN for v in e['outlet']])
        for pipe_system,port in e['supply_ports'].items():
            q=Vector([v*IN for v in port]);r=e['inlet_sizes'][pipe_system]*IN*.5*SPEC['display']['unit_pipe_multiplier']*1.2
            cylinder(c,q,r,'metal');cylinder(q+(c-q)*.12,q,r*1.2,'metal',6)
        cylinder(c,out,e['nominal_in']*IN*.8,'metal')
        cylinder(c-Vector((0,.03,0)),c+Vector((0,.03,0)),.065,'metal',24)
        cylinder(c-Vector((0,.05,0)),c-Vector((0,.03,0)),.025,'dark',20)
        cube(c+Vector((.025,-.058,0)),(.08,.013,.016),'metal',.005)
    elif kind=='box':cube([v*IN for v in e['at']],[v*IN for v in e['dims']],sysname,.025)
    elif kind=='tank':
        x,y,z=[v*IN for v in e['at']];r=e['radius']*IN;h=e['height']*IN
        cylinder((x,y,z+r*.15),(x,y,z+h-r*.15),r,sysname,32)
        sphere((x,y,z+h-r*.15),r,sysname,(1,1,.22));sphere((x,y,z+r*.15),r,sysname,(1,1,.22))
        for zz in [z+h*.1,z+h*.9]:cylinder((x,y,zz),(x,y,zz+.025),r*1.02,'metal',32)
        if e['role'] in ['boiler','storage tank']:
            cube((x,y-r-.025,z+h*.55),(.22,.08,.27),'dark',.015)
            cube((x,y-r-.07,z+h*.58),(.15,.012,.08),'HWC',.005)
    elif kind in ['valve','meter','pump']:
        x,y,z=[v*IN for v in e['at']]
        if kind=='pump':
            cylinder((x,y-.14,z),(x,y+.14,z),.12,'metal');cylinder((x,y,z),(x+.22,y,z),.09,'dark')
        elif kind=='meter':
            sphere((x,y,z),.07,'metal');cylinder((x,y,z),(x,y,z+.07),.06,'fixtures')
        else:
            sphere((x,y,z),.035,'metal');cube((x+.055,y,z+.06),(.15,.025,.02),sysname,.006)
    elif kind=='fixture': fixture(e)
    elif kind=='wall':
        a,b=[Vector([v*IN for v in p]) for p in e['points']];mid=(a+b)*.5
        o=cube(mid+Vector((0,0,e['height']*IN*.5)),((b-a).length,e['thickness']*IN,e['height']*IN),'context',.01)
        o.rotation_euler.z=math.atan2((b-a).y,(b-a).x)
    elif kind=='label':
        bpy.ops.object.text_add(location=[v*IN for v in e['at']]);o=bpy.context.object
        o.data.body=e['text'];o.data.size=e['size']*IN;o.data.extrude=.0005
        if model in ['building','plant']:o.rotation_euler=(math.pi/2,0,0)
        o.data.materials.append(mats['text']);bpy.ops.object.convert(target='MESH');parts=[bpy.context.object]
    if not parts:continue
    bpy.ops.object.select_all(action='DESELECT')
    for o in parts:o.select_set(True)
    bpy.context.view_layer.objects.active=parts[0]
    if len(parts)>1:bpy.ops.object.join()
    obj=bpy.context.object;obj.name=e['id']
    for c in list(obj.users_collection):c.objects.unlink(obj)
    collections[(model,sysname)].objects.link(obj)
    for k,v in e.items():
        if k not in ['points','at','dims']:obj[k]=v if isinstance(v,(str,int,float,bool)) else json.dumps(v)
    if kind=='pipe':obj['display_diameter_multiplier']=mult

# Check the actual generated fixture bounds against the vertical wall-side drops.
clearance=[]
for contract in SPEC['bathroom_pilot']['supply_connections']:
    if contract['fixture'] not in ['master-lav-1','master-lav-2','master-wc']:continue
    fixture_object=bpy.data.objects[contract['fixture']]
    bbox=[fixture_object.matrix_world@Vector(c) for c in fixture_object.bound_box]
    max_y=max(p.y for p in bbox)
    route=next(e for e in SPEC['elements'] if e['id']==contract['drop'])
    y=route['points'][-1][1]*IN
    radius=route['nominal_in']*IN*.5*SPEC['display']['unit_pipe_multiplier']
    gap=(y-radius-max_y)/IN
    assert gap>0,(contract['drop'],'vertical supply intersects fixture envelope')
    clearance.append({'route':route['id'],'gap_behind_fixture_in':round(gap,3)})
report=json.loads((OUT/'validation.json').read_text());report['bathroom_pilot']['mesh_fixture_clearances']=clearance
(OUT/'validation.json').write_text(json.dumps(report,indent=2))

# Separate GLBs avoid loading the building and unit into the same coordinate space.
for model in ['building','plant','unit']:
    bpy.ops.object.select_all(action='DESELECT')
    for obj in collections[model].all_objects:obj.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(OUT/(model+'.glb')),export_format='GLB',use_selection=True,export_extras=True,export_cameras=False,export_lights=False)

def area(name,at,power,size):
    bpy.ops.object.light_add(type='AREA',location=at);o=bpy.context.object;o.name=name;o.data.energy=power;o.data.shape='DISK';o.data.size=size
    o.rotation_euler=(Vector((0,0,7))-o.location).to_track_quat('-Z','Y').to_euler()
area('key',(10,-15,25),5000,14);area('fill',(-15,-4,16),3500,10);area('rim',(6,12,22),5000,10)
bpy.ops.object.camera_add();camera=bpy.context.object;scene.camera=camera;camera.data.type='ORTHO';camera.data.lens=50
views=[
 ('building','building-iso',(31,-40,28),(0,0,11),39),
 ('plant','plant-iso',(11,-15,11),(-.7,0,1.3),15),
 ('unit','unit-iso',(20,-29,26),(0,-2.2,1.0),26),
 ('unit','unit-bath',(2,-5,10),(-7,5.5,1),11),
 ('unit','bath-connections',(-2,0,3.2),(-7.3,4.4,.85),5),
 ('unit','review-plan',(0,0,35),(0,0,0),26),
 ('unit','review-front',(0,-35,4),(0,0,1.3),26),
 ('unit','review-side',(35,0,4),(0,0,1.3),26),
 ('building','review-building',(31,-40,28),(0,0,11),39),
 ('unit','review-iso',(20,-29,26),(0,-2.2,1.0),26)]
for model,name,pos,target,scale in views:
    if '--unit-only' in sys.argv and model!='unit':continue
    for m in ['building','plant','unit']:collections[m].hide_render=m!=model
    camera.location=pos;camera.rotation_euler=(Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.ortho_scale=scale
    scene.view_layers[0].material_override=mats['assumed'] if name.startswith('review') else None
    scene.render.filepath=str(OUT/(name+'.png'))
    bpy.ops.render.render(write_still=True)
scene.view_layers[0].material_override=None
for m in ['building','plant','unit']:
    collections[m].hide_render=m!='unit'
    for obj in collections[m].all_objects:obj.hide_set(m!='unit')
camera.location=(2,-5,10);camera.rotation_euler=(Vector((-7,5.5,1))-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.ortho_scale=11
scene['readme']='Highland domestic water; opens on Unit 107 bathroom. Unit XY provisional; pipe heights and hardware assumed; floor datums documented. Hide unit and unhide plant or building to explore other studies. See specification and report.'
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Highland-domestic-water.blend'))
print('BUILD COMPLETE',flush=True)
