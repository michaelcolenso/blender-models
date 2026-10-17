"""Headless, spec-driven pipe coordination model; Cycles CPU, no inferred takeoff."""
import bpy, json, math, sys
from pathlib import Path
import yaml
from mathutils import Vector

ROOT=Path(__file__).resolve().parent
SPEC=yaml.safe_load((ROOT/'highland-installation-proposed.yaml').read_text())
OUT=ROOT/'renders';OUT.mkdir(exist_ok=True)
IN=.0254
W=SPEC['display']['width_in'];H=SPEC['display']['height_in']
PALETTE={'CW':(.025,.31,.76),'HW':(.85,.10,.055),'HWC':(.47,.13,.72),
 'access':(.93,.43,.04),'support':(.26,.30,.33),'protection':(.91,.68,.16),
 'terminal':(.13,.22,.25),'assembly':(.62,.45,.17),'restore':(.26,.42,.43),
 'assumed':(.97,.34,.045),'confirmed':(.25,.65,.33),'provisional':(.94,.73,.08)}
OBJECTS=[];MATS={}
def material(name,color):
 m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);m.use_nodes=True
 bs=m.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(*color,1);bs.inputs['Roughness'].default_value=.5
 MATS[name]=m;return m
def coll(name):
 c=bpy.data.collections.get(name)
 if c is None:c=bpy.data.collections.new(name);bpy.context.scene.collection.children.link(c)
 return c
def move(o,c):
 for cc in list(o.users_collection):cc.objects.unlink(o)
 coll(c).objects.link(o)
def tag(o,e,collection=None):
 o['element_id']=e['id'];o['status']=e.get('status','assumed');o['basis']=e.get('basis','Presentation symbol; not measured geometry.')
 o['source']=e.get('source','P4.01');o['phase']=e.get('phase',0)
 if e.get('system'):o['system']=e['system']
 o['not_for_takeoff']=True;o['description']=e.get('description',e.get('label',''))
 move(o,collection or e.get('collection','Presentation'));OBJECTS.append(o)
 return o
def coord(p):return Vector(((p[0]-.5)*W*IN,(.5-p[1])*H*IN,p[2]*IN))
def curve(name,points,radius,mat,e,normalized=True):
 pts=[coord(p) if normalized else Vector(p)*IN for p in points]
 cu=bpy.data.curves.new(name,'CURVE');cu.dimensions='3D';cu.resolution_u=1;cu.bevel_depth=radius*IN;cu.bevel_resolution=2
 sp=cu.splines.new('POLY');sp.points.add(len(pts)-1)
 for v,p in zip(sp.points,pts):v.co=(*p,1)
 o=bpy.data.objects.new(name,cu);bpy.context.scene.collection.objects.link(o);o.data.materials.append(MATS[mat]);tag(o,e)
 return o
def box(name,at,size,mat,e,normalized=True):
 bpy.ops.mesh.primitive_cube_add(size=1,location=coord(at) if normalized else Vector(at)*IN)
 o=bpy.context.object;o.name=name;o.dimensions=Vector(size)*IN;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
 o.data.materials.append(MATS[mat]);tag(o,e);return o
def sphere(name,at,r,mat,e):
 bpy.ops.mesh.primitive_uv_sphere_add(segments=12,ring_count=6,radius=r*IN,location=coord(at));o=bpy.context.object;o.name=name;o.data.materials.append(MATS[mat]);tag(o,e);return o
def text(name,body,at,size,e,normalized=True):
 bpy.ops.object.text_add(location=coord(at) if normalized else Vector(at)*IN)
 o=bpy.context.object;o.name=name;o.data.body=body;o.data.size=size*IN;o.data.extrude=.05*IN;o.data.materials.append(MATS['terminal']);tag(o,e,'Labels');return o
def boundary(e,z,mat,suffix=''):
 x0,y0,x1,y1=e['rect'];pts=[[x0,y0,z],[x1,y0,z],[x1,y1,z],[x0,y1,z],[x0,y0,z]]
 return curve(e['id']+suffix,pts,1.1,mat,e)
def setup(name):
 global OBJECTS
 OBJECTS=[]
 for obj in list(bpy.data.objects):bpy.data.objects.remove(obj,do_unlink=True)
 sc=bpy.context.scene;sc.name=name;sc.render.engine='CYCLES';sc.cycles.device='CPU';sc.cycles.samples=6;sc.cycles.use_denoising=True
 sc.timeline_markers.clear();sc.frame_start=1;sc.frame_end=1;sc.frame_set(1)
 sc.render.threads_mode='FIXED';sc.render.threads=4;sc.render.resolution_x=1280;sc.render.resolution_y=1120;sc.render.resolution_percentage=100
 sc.render.image_settings.file_format='PNG';sc.view_settings.view_transform='Standard'
 sc.world.use_nodes=True;sc.world.node_tree.nodes['Background'].inputs[0].default_value=(.8,.84,.88,1);sc.world.node_tree.nodes['Background'].inputs[1].default_value=.65
 sc.unit_settings.system='IMPERIAL';sc.unit_settings.length_unit='INCHES';sc['purpose']='Installation method coordination; all physical geometry assumed'
 sc['source_issue']='2007-10-29';sc['limitations']='Do not measure, order materials, operate valves or infer affected units from this schematic.'
 for key,value in PALETTE.items():material(key,value)
 material('ground',(.86,.88,.88));material('backing',(.72,.76,.77))
 bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.08));o=bpy.context.object;o.name='Studio ground';o.data.materials.append(MATS['ground'])
 bpy.ops.object.light_add(type='AREA',location=(3,-5,16));bpy.context.object.data.energy=1600;bpy.context.object.data.size=9
 bpy.ops.object.camera_add();sc.camera=bpy.context.object;sc.camera.name='Review camera';sc.camera.data.type='ORTHO'
 return sc
def camera(sc,view):
 target=Vector((0,0,.5));positions={'iso':(14,-19,21),'plan':(0,0,25),'front':(0,-24,7),'side':(24,0,7)}
 cam=sc.camera;cam.location=positions[view];cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=19.2 if view=='iso' else 15.6
def render(sc,name):
 if '--reuse-early-stages' in sys.argv and name in {'phase-01.png','phase-02.png','phase-03.png'} and (OUT/name).exists():
  print('Reuse unchanged early stage:',name);return
 sc.render.filepath=str(OUT/name);bpy.context.view_layer.update();bpy.ops.render.render(write_still=True)
def export(sc,path):
 # Snapshot evaluated geometry into unanimated meshes. Exporters can otherwise
 # sample frame zero and omit staged objects even for a nominally static export.
 graph=bpy.context.evaluated_depsgraph_get()
 visible=[o for o in sc.objects if o.type in {'MESH','CURVE','FONT'} and o.name!='Studio ground' and not o.hide_render]
 bpy.ops.object.select_all(action='DESELECT')
 copies=[]
 for o in visible:
  mesh=bpy.data.meshes.new_from_object(o.evaluated_get(graph),depsgraph=graph)
  cp=bpy.data.objects.new(o.name+' [static]',mesh);sc.collection.objects.link(cp);cp.matrix_world=o.matrix_world.copy()
  for key in o.keys():cp[key]=o[key]
  cp.select_set(True);copies.append(cp)
 bpy.ops.export_scene.gltf(filepath=str(path),use_selection=True,export_extras=True,export_animations=False,export_current_frame=True)
 for cp in copies:
  mesh=cp.data;bpy.data.objects.remove(cp,do_unlink=True);bpy.data.meshes.remove(mesh)
def plane(sc):
 e={'id':'SOURCE-P4.01','status':'assumed','source':'P4.01 / PDF 15','basis':SPEC['display']['basis'],'phase':0,'collection':'Source_reference'}
 box('Source drawing backing',[.5,.5,-1.5],[W,H,2],'backing',e)
 bpy.ops.mesh.primitive_plane_add(size=2,location=(0,0,.002));o=bpy.context.object;o.name='P4.01 Unit B source drawing';o.scale=(W*IN/2,H*IN/2,1);tag(o,e)
 o['content_status']='confirmed';o['content_source']='Unchanged source drawing crop; physical placement and scale assumed.'
 m=bpy.data.materials.new('Source image');m.use_nodes=True;n=m.node_tree.nodes;n.clear();im=n.new('ShaderNodeTexImage');im.image=bpy.data.images.load(str(ROOT/'unit-b-plan.png'));em=n.new('ShaderNodeEmission');em.inputs['Strength'].default_value=.85;out=n.new('ShaderNodeOutputMaterial');m.node_tree.links.new(im.outputs['Color'],em.inputs['Color']);m.node_tree.links.new(em.outputs[0],out.inputs[0]);o.data.materials.append(m)
def visible(o,p):
 phase=o.get('phase',0)
 if o.get('phase_only') is not None:return p==o['phase_only']
 if o.get('hide_after') is not None and p>o['hide_after']:return False
 return p>=phase
def set_phase(sc,p):
 for o in OBJECTS:o.hide_render=not visible(o,p);o.hide_viewport=not visible(o,p)
 sc['installation_phase']=p;sc['phase_title']=SPEC['phases'][p]['title'];sc.frame_set(p*24+1)

def build_unit():
 sc=setup('Unit B - proposed installation');plane(sc)
 for e in SPEC['elements']:
  typ=e['type']
  if typ=='pipe':curve(e['id'],e['points'],e['radius_in'],e['system'],e)
  elif typ=='access':
   o=boundary(e,3,'access');o['hide_after']=4
   text(e['id']+' label',e['id'],[e['rect'][0],e['rect'][1]-.012,4],6,e)
   patch={**e,'id':e['id']+'-RESTORE','phase':5,'collection':'07_Restoration','basis':'Restoration boundary symbol only; actual rated assembly and access-panel design pending.'}
   boundary(patch,3,'restore')
  elif typ=='protection':boundary(e,2,'protection')
  elif typ=='terminal':
   box(e['id']+' fixture-group symbol',e['at'],[8,6,5],'terminal',e)
   for k,system in enumerate(e['systems']):
    at=[e['at'][0]+(k-.5)*.01,e['at'][1],e['at'][2]+4]
    cap={**e,'id':e['id']+'-CAP-'+system,'collection':'06_Test_boundary'}
    o=sphere(cap['id'],at,2.1,'access',cap);o['phase_only']=3
    stop={**e,'id':e['id']+'-STOP-'+system,'phase':4,'collection':'05_Service_assembly'}
    box(stop['id'],at,[5,3,2],system,stop)
   text(e['id']+' label',e['id'],[e['at'][0]+.012,e['at'][1]+.02,4],5,e)
  elif typ=='assembly':
   # Three service symbols; meter/control device details intentionally unresolved.
   for port in e['ports']:
    system=port['system'];at=port['at']
    box('SVC-'+system,at,[4,10,4],'assembly',{**e,'id':'SVC-'+system,'system':system})
   box('Meter coordination envelope',[.129,.148,66],[9,9,7],'terminal',{**e,'id':'METER-ENVELOPE'})
  elif typ=='test':
   for port in e['ports']:
    system=port['system'];cap={**e,'id':'SERVICE-CAP-'+system};o=sphere(cap['id'],port['at'],2.7,'access',cap);o['phase_only']=3
   o=sphere('TEST-GAUGE',e['at'],5,'terminal',e);o['phase_only']=3
  elif typ=='support':
   at=e['at'];box(e['id'],[at[0],at[1],at[2]+4],e['size_in'],'support',e)
 # Mark method-stage keyframes, plus actual scene visibility for manual review.
 sc.frame_start=1;sc.frame_end=144;sc.render.fps=12
 for phase in SPEC['phases']:
  f=phase['id']*24+1;sc.timeline_markers.new(phase['title'],frame=f)
  for o in OBJECTS:
   o.hide_render=not visible(o,phase['id']);o.hide_viewport=o.hide_render
   o.keyframe_insert(data_path='hide_render',frame=f);o.keyframe_insert(data_path='hide_viewport',frame=f)
 for o in OBJECTS:
  if o.animation_data and o.animation_data.action:
   for layer in o.animation_data.action.layers:
    for strip in layer.strips:
     for slot in o.animation_data.action.slots:
      bag=strip.channelbag(slot)
      if bag:
       for fc in bag.fcurves:
        for key in fc.keyframe_points:key.interpolation='CONSTANT'
 camera(sc,'iso')
 for p in range(6):set_phase(sc,p);render(sc,f'phase-{p+1:02}.png')
 set_phase(sc,5);camera(sc,'iso')
 bpy.ops.file.pack_all();bpy.context.preferences.filepaths.save_version=0
 bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Highland-installation-unit-B.blend'))
 export(sc,ROOT/'Highland-installation-unit-B.glb')
 # Provenance review: all proposed geometry is orange. Source pixels remain unchanged.
 originals={}
 for o in OBJECTS:
  if o.type in {'MESH','CURVE','FONT'} and o.name!='P4.01 Unit B source drawing':
   originals[o.name]=list(o.data.materials);o.data.materials.clear();o.data.materials.append(MATS['assumed'])
 for view in ['plan','front','side','iso']:camera(sc,view);render(sc,'review-'+view+'.png')
 return {'objects':len(OBJECTS),'phase_frames':[1,25,49,73,97,121]}

def build_shared():
 sc=setup('Shared distribution - proposed schematic');s=SPEC['shared_distribution']
 # Remove source-plane expectation: this scene is an explicitly unregistered schematic.
 e={'id':'SHARED','phase':2,'source':'P3.02 / PDF 13','collection':'Shared_distribution','basis':s['basis']}
 x0,x1=s['header_extent_in'];z=s['header_z_in'];zt=s['riser_height_in']
 for system,y in s['system_offsets_in'].items():
  curve('HEADER-'+system,[[x0,y,z],[x1,y,z]],3,system,{**e,'id':'HEADER-'+system,'system':system},False)
 for idx,stack in enumerate(s['stacks']):
  x=stack['x_in'];label=stack['label']
  for system,y in s['system_offsets_in'].items():
   curve('STACK-'+label+'-'+system,[[x,y,z],[x,y,zt]],2,system,{**e,'id':'STACK-'+label+'-'+system,'system':system},False)
   box('VALVE-'+label+'-'+system,[x,y,z+22],[9,9,9],'assembly',{**e,'id':'VALVE-'+label+'-'+system},False)
  curve('RETURN-'+label,[[x,12,zt],[x,24,zt]],2,'HWC',{**e,'id':'RETURN-'+label,'system':'HWC'},False)
  text('LABEL-'+label,label,[x-10,-12,zt+15],15,{**e,'id':'LABEL-'+label},False)
 # Distinct source-note service stubs: schematic, not field isolation boundaries.
 for stub in s['auxiliary_stubs']:
  eid,label,x,systems=stub['id'],stub['label'],stub['x_in'],stub['systems']
  for k,system in enumerate(systems):
   y=s['system_offsets_in'][system]
   curve(eid+'-'+system,[[x,y,z],[x,y,-55]],2,system,{**e,'id':eid+'-'+system,'system':system},False)
  text(eid+' label',label,[x-20,-5,-76],9,{**e,'id':eid+'-LABEL'},False)
 bpy.data.objects['Studio ground'].location.z=-3
 sc.camera.location=(13,-20,17);target=Vector((0,0,2));sc.camera.rotation_euler=(target-sc.camera.location).to_track_quat('-Z','Y').to_euler();sc.camera.data.ortho_scale=22
 sc.render.resolution_x=1600;sc.render.resolution_y=1100
 render(sc,'shared-distribution.png')
 for o in OBJECTS:o.hide_viewport=False;o.hide_render=False
 sc['limitations']='Schematic positions, pipe sizes, connections and valves assumed. No isolation boundary or served-unit mapping confirmed.'
 bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Highland-installation-shared.blend'))
 export(sc,ROOT/'Highland-installation-shared.glb')
 return {'objects':len(OBJECTS),'review_labels':[v['label'] for v in s['stacks']]}

if __name__=='__main__':
 result={'unit':build_unit(),'shared':build_shared()}
 (ROOT/'build-result.json').write_text(json.dumps(result,indent=2));print('INSTALLATION_BUILD_COMPLETE',result)
