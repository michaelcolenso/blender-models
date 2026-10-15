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
                    if -1e-7<=t<=1+1e-7 and (Vector(p)-(a+t*ab)).length<1e-5: on.append((t,p))
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
    report={'counts':actual,'connectivity':connected,'limitations':SPEC['limitations'],'result':'PASS: modeled counts, provenance and per-system distribution reachability; plant internals and cross-system flow not validated'}
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
colors={'CW':(.025,.40,.95,1),'HW':(.98,.18,.045,1),'HWC':(.03,.72,.42,1),
 'equipment':(.45,.56,.64,1),'fixtures':(.80,.85,.88,1),'context':(.14,.22,.29,1),
 'metal':(.48,.38,.15,1),'dark':(.025,.045,.065,1),'text':(.78,.89,.94,1),'assumed':(1,.32,.035,1)}
mats={}
for name,c in colors.items():
    mat=bpy.data.materials.new(name);mat.diffuse_color=c;mat.use_nodes=True
    bsdf=mat.node_tree.nodes.get('Principled BSDF');bsdf.inputs['Base Color'].default_value=c
    bsdf.inputs['Metallic'].default_value=.45 if name in ['equipment','metal'] else .12
    bsdf.inputs['Roughness'].default_value=.32
    if name in ['CW','HW','HWC','text']:
        bsdf.inputs['Emission Color'].default_value=c;bsdf.inputs['Emission Strength'].default_value=.15
    mats[name]=mat
collections={}
for model in ['building','plant','unit']:
    parent=bpy.data.collections.new(model);scene.collection.children.link(parent)
    collections[model]=parent
    for trade in ['CW','HW','HWC','equipment','fixtures','context']:
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
def fixture(e):
    x,y,z=[v*IN for v in e['at']];kind=e['fixture'];W=mats['fixtures']
    if kind in ['lav','sink']:
        width=.60 if kind=='lav' else .85
        cube((x,y,z+.76),(width,.48,.12),'fixtures',.045)
        cube((x,y,z+.825),(width*.73,.32,.012),'dark',.035)
        cylinder((x,y+.16,z+.82),(x,y+.16,z+1.02),.012,'metal')
        cylinder((x,y+.16,z+1.02),(x,y,z+1.02),.012,'metal')
        cylinder((x,y,z+.23),(x,y,z+.70),.025,'fixtures')
    elif kind=='wc':
        sphere((x,y,z+.34),1,'fixtures',(.19,.28,.18))
        sphere((x,y-.04,z+.45),1,'dark',(.12,.17,.012))
        cube((x,y+.24,z+.60),(.40,.18,.42),'fixtures',.04)
        cylinder((x,y,z+.02),(x,y,z+.23),.12,'fixtures')
    elif kind=='bath':
        cube((x,y,z+.24),(1.65,.80,.48),'fixtures',.13)
        cube((x,y,z+.485),(1.35,.57,.02),'dark',.10)
        cylinder((x+.6,y+.28,z+.48),(x+.6,y+.28,z+.7),.016,'metal')
    elif kind=='shower':
        cube((x,y,z+.035),(.95,.95,.07),'fixtures',.045)
        cylinder((x,y+.42,z+1.12),(x,y+.42,z+2.03),.014,'metal')
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
        tube([[v*IN for v in p] for p in e['points']],e['nominal_in']*IN*.5*mult,sysname)
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
 ('unit','unit-iso',(16,-23,21),(0,-1.7,1.0),20),
 ('unit','review-plan',(0,-1.8,30),(0,-1.8,0),20),
 ('unit','review-front',(0,-35,4),(0,-1.8,1.3),20),
 ('unit','review-side',(35,-1.8,4),(0,-1.8,1.3),20),
 ('building','review-building',(31,-40,28),(0,0,11),39),
 ('unit','review-iso',(16,-23,21),(0,-1.7,1.0),20)]
for model,name,pos,target,scale in views:
    for m in ['building','plant','unit']:collections[m].hide_render=m!=model
    camera.location=pos;camera.rotation_euler=(Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.ortho_scale=scale
    scene.view_layers[0].material_override=mats['assumed'] if name.startswith('review') else None
    scene.render.filepath=str(OUT/(name+'.png'))
    bpy.ops.render.render(write_still=True)
scene.view_layers[0].material_override=None
for m in ['building','plant','unit']:
    collections[m].hide_render=m!='building'
    for obj in collections[m].all_objects:obj.hide_set(m!='building')
camera.location=(31,-40,28);camera.rotation_euler=(Vector((0,0,11))-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.ortho_scale=39
scene['readme']='Highland domestic water. Unhide plant or unit collections individually. Geometry coordinates assumed; source nominal sizes retained in object metadata. See specification and report.'
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Highland-domestic-water.blend'))
print('BUILD COMPLETE',flush=True)
