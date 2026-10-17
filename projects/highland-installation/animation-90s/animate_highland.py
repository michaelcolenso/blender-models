"""Source-preserving Blender rig and deterministic frame renderer for the 90s film."""
import bpy,json,math,sys,hashlib,time
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parent;SRC=ROOT.parent/'installation'
S=json.loads((ROOT/'animation-spec.json').read_text());G=json.loads((SRC/'installation-data.json').read_text())
FPS=S['fps'];DURATION=S['duration'];IN=.0254;FRAMES=ROOT/'frames';FRAMES.mkdir(exist_ok=True)
def frame(t):return round(t*FPS)+1
def ease(x):x=max(0,min(1,x));return x*x*(3-2*x)
def linear_rgba(hexcode):
 rgb=[int(hexcode[i:i+2],16)/255 for i in (1,3,5)]
 return tuple(x/12.92 if x<=.04045 else ((x+.055)/1.055)**2.4 for x in rgb)+(1,)
def coord(p):return Vector(((p[0]-.5)*G['display']['width_in']*IN,(.5-p[1])*G['display']['height_in']*IN,p[2]*IN))
def key(o,prop,t,value):
 setattr(o,prop,value);o.keyframe_insert(data_path=prop,frame=frame(t))
def show_between(o,start,end=90):
 for t,hidden in [(0,True),(max(0,start-1/FPS),True),(start,False),(end,True)]:
  key(o,'hide_render',t,hidden);key(o,'hide_viewport',t,hidden)
def growth(o,start,end,hide_at=90):
 show_between(o,start,hide_at)
 if o.type=='CURVE':
  o.data.use_fill_caps=True;o.data.bevel_factor_mapping_end='SPLINE'
  for t,v in [(0,0),(start,0),(end,1),(90,1)]:key(o.data,'bevel_factor_end',t,v)
def smooth_actions():
 for a in bpy.data.actions:
  for layer in a.layers:
   for strip in layer.strips:
    for slot in a.slots:
     bag=strip.channelbag(slot)
     if bag:
      for fc in bag.fcurves:
       for p in fc.keyframe_points:p.interpolation='CONSTANT' if fc.data_path.startswith('hide_') else 'LINEAR'
def presentation_materials():
 for m in bpy.data.materials:
  if not m.use_nodes:continue
  n=m.node_tree.nodes;bs=n.get('Principled BSDF')
  if not bs:continue
  color=tuple(bs.inputs['Base Color'].default_value);n.clear()
  normal=n.new('ShaderNodeNewGeometry');dot=n.new('ShaderNodeVectorMath');dot.operation='DOT_PRODUCT';dot.inputs[1].default_value=(-.35,-.5,.8)
  shade=n.new('ShaderNodeMath');shade.operation='MULTIPLY_ADD';shade.inputs[1].default_value=.45;shade.inputs[2].default_value=.65
  em=n.new('ShaderNodeEmission');em.inputs[0].default_value=color;out=n.new('ShaderNodeOutputMaterial')
  m.node_tree.links.new(normal.outputs['Normal'],dot.inputs[0]);m.node_tree.links.new(dot.outputs['Value'],shade.inputs[0]);m.node_tree.links.new(shade.outputs[0],em.inputs['Strength']);m.node_tree.links.new(em.outputs[0],out.inputs[0])
def configure(sc):
 sc.render.engine='CYCLES';sc.cycles.device='CPU';sc.cycles.samples=4;sc.cycles.use_denoising=False;sc.cycles.max_bounces=0;sc.cycles.use_light_tree=False
 sc.render.threads_mode='FIXED';sc.render.threads=3;sc.render.resolution_x=S['render_size'][0];sc.render.resolution_y=S['render_size'][1];sc.render.resolution_percentage=100
 sc.render.image_settings.file_format='PNG';sc.render.image_settings.color_mode='RGB';sc.render.image_settings.compression=15
 sc.render.fps=FPS;sc.frame_start=1;sc.frame_end=FPS*DURATION;sc.timeline_markers.clear()
 sc.view_settings.view_transform='Standard';sc.view_settings.exposure=0;sc.view_settings.gamma=1
 sc.world.use_nodes=True;sc.world.node_tree.nodes['Background'].inputs[0].default_value=linear_rgba(S['palette']['paper']);sc.world.node_tree.nodes['Background'].inputs[1].default_value=1
 for o in sc.objects:
  o.animation_data_clear()
  if o.data and hasattr(o.data,'animation_data_clear'):o.data.animation_data_clear()
  o.hide_render=False;o.hide_viewport=False
  if o.name.startswith('Studio ground') or o.type=='LIGHT':o.hide_render=True
 sc['purpose']='90-second proposed installation animation; source geometry and provenance preserved.'
 sc['footer']=S['footer'];sc['render_note']=S['render_method']
def camera_pose(sh,t):
 values=sh['camera']
 if t<=values[0][0]:return values[0][1]
 if t>=values[-1][0]:return values[-1][1]
 for (ta,a),(tb,b) in zip(values,values[1:]):
  if ta<=t<=tb:
   u=ease((t-ta)/(tb-ta));return {k:[(1-u)*x+u*y for x,y in zip(a[k],b[k])] if isinstance(a[k],list) else (1-u)*a[k]+u*b[k] for k in a}
def animate_camera(sc,kind):
 shots=[sh for sh in S['shots'] if sh['scene']==kind];cam=sc.camera;cam.animation_data_clear();cam.data.animation_data_clear();cam.data.type='ORTHO';cam.data.clip_end=500
 for f in range(1,2161):
  t=(f-1)/FPS;sh=next((s for s in shots if s['start']<=t<s['end']),shots[0] if t<shots[0]['start'] else shots[-1]);p=camera_pose(sh,t)
  az=math.radians(p['azimuth']);el=math.radians(p['elevation']);target=Vector(p['target'])
  cam.location=target+Vector((math.cos(az)*math.cos(el),math.sin(az)*math.cos(el),math.sin(el)))*30
  cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=p['ortho_scale']
  cam.keyframe_insert(data_path='location',frame=f);cam.keyframe_insert(data_path='rotation_euler',frame=f);cam.data.keyframe_insert(data_path='ortho_scale',frame=f)
 for sh in shots:sc.timeline_markers.new(f"{sh['id']:02} {sh['title']}",frame=frame(sh['start']))
def path_at(pts,u):
 lengths=[(b-a).length for a,b in zip(pts,pts[1:])];d=u*sum(lengths)
 for a,b,l in zip(pts,pts[1:],lengths):
  if d<=l:return a.lerp(b,0 if l==0 else d/l)
  d-=l
 return pts[-1]
def flow_marker(sc,name,pts,system,start,end,offset):
 bpy.context.window.scene=sc
 bpy.ops.mesh.primitive_uv_sphere_add(segments=12,ring_count=6,radius=.065)
 o=bpy.context.object;o.name=name;o['status']='assumed';o['basis']='Presentation flow marker; no hydraulic simulation or actual flow measurement.';o['source']='Proposed installation model';o['system']=system;o['not_for_takeoff']=True
 m=bpy.data.materials.get('Flow '+system)
 if not m:
  m=bpy.data.materials.new('Flow '+system);m.use_nodes=True;n=m.node_tree.nodes;n.clear();em=n.new('ShaderNodeEmission');em.inputs[0].default_value=linear_rgba(S['palette'][system]);em.inputs[1].default_value=1.7;out=n.new('ShaderNodeOutputMaterial');m.node_tree.links.new(em.outputs[0],out.inputs[0])
 o.data.materials.append(m);show_between(o,start,end)
 for f in range(frame(start),frame(end)+1,4):
  t=(f-1)/FPS;o.location=path_at(pts,((t-start)/5+offset)%1);o.keyframe_insert(data_path='location',frame=f)
 return o
def rig_unit(sc):
 configure(sc);obs=list(sc.objects)
 for o in obs:
  n=o.name;phase=o.get('phase',0)
  if n.startswith('Studio ground') or o.type in {'LIGHT','CAMERA'}:continue
  if o.type=='FONT':show_between(o,95,96);continue
  if n.startswith('P4.01 Unit B') or n=='Source drawing backing':continue
  if n=='P01':growth(o,9,11);continue
  if n.startswith('A') and n[:3] in {'A01','A02','A03','A04','A05'}:
   idx=int(n[1:3])-1
   if 'RESTORE' in n:growth(o,74+idx*.65,75+idx*.65)
   else:growth(o,18.5+idx*.9,20+idx*.9,74+idx*.65)
   continue
  if n.startswith('SUP-'):
   idx=int(n[-2:])-1;show_between(o,22+idx*.35);continue
  if n in S['reveal']:
   growth(o,*S['reveal'][n]);continue
  if o.type=='CURVE' and (n.startswith('F') or n in {'CW-04','HW-04'}):
   idx=int(n[1:3]) if n.startswith('F') else 8
   growth(o,45+idx*.52,47+idx*.52);continue
  if o.get('phase_only')==3:show_between(o,54,62);continue
  if phase==4:
   show_between(o,62 if n.startswith('SVC-') else 63.5);continue
  if phase==3:
   idx=int(n[1:3]) if n.startswith('F') else 0;show_between(o,47+idx*.52);continue
  if phase>0:show_between(o,18)
 # A source-plan trace is a coordination graphic; it does not assert an existing CPVC path.
 src=next(o for o in sc.objects if o.name=='A01');trace=src.copy();trace.data=src.data.copy();sc.collection.objects.link(trace);trace.name='Verify service location - presentation trace';trace.animation_data_clear();trace.data.animation_data_clear();trace['basis']='Source-plan highlight for field tracing; not an isolation confirmation.';growth(trace,11,13,18.5)
 pipes={e['id']:e for e in G['elements'] if e['type']=='pipe'}
 for system in ['CW','HW']:
  pts=[coord(p) for p in pipes[system+'-01']['points']+pipes[system+'-02']['points'][1:]]
  for j in range(2):flow_marker(sc,'Flow '+system+str(j),pts,system,67,85,j*.5)
 pts=[coord(p) for p in pipes['HWC-01']['points']]
 for j in range(2):flow_marker(sc,'Flow HWC'+str(j),pts,'HWC',67,85,j*.5)
 animate_camera(sc,'unit')
def rig_shared(sc):
 configure(sc)
 for i,o in enumerate(list(sc.objects)):
  if o.type=='CURVE':
   growth(o,.4+(i%5)*.18,3.1+(i%5)*.18)
  elif o.type=='MESH' and not o.name.startswith('Studio ground'):show_between(o,1)
 s=G['shared_distribution']
 for system,y in s['system_offsets_in'].items():
  pts=[Vector((s['header_extent_in'][0],y,s['header_z_in']))*IN,Vector((s['header_extent_in'][1],y,s['header_z_in']))*IN]
  if system=='HWC':pts.reverse()
  for j in range(2):flow_marker(sc,'Shared flow '+system+str(j),pts,system,85,90,j*.5)
 animate_camera(sc,'shared')
def add_text(master,name,text,start,end,loc,size,color,channel=12):
 e=master.sequence_editor.strips.new_effect(name=name,type='TEXT',channel=channel,frame_start=frame(start),length=round((end-start)*FPS))
 e.text=text;e.font_size=size;e.location=loc;e.anchor_x='LEFT';e.anchor_y='CENTER';e.alignment_x='LEFT';e.color=linear_rgba(color);e.use_shadow=False
 return e
def master_scene(scenes):
 import textwrap
 m=bpy.data.scenes.new('MASTER - 90 seconds');m.render.resolution_x=3840;m.render.resolution_y=2160;m.render.resolution_percentage=100;m.render.fps=24;m.frame_start=1;m.frame_end=2160;m.render.use_sequencer=True;m.sequence_editor_create()
 m.view_settings.view_transform='Standard'
 bg=m.sequence_editor.strips.new_effect(name='Warm paper background',type='COLOR',channel=1,frame_start=1,length=2160);bg.color=linear_rgba(S['palette']['paper'])[:3]
 for sh in S['shots']:
  strip=m.sequence_editor.strips.new_scene(name=f"{sh['id']:02} {sh['title']}",scene=scenes[sh['scene']],channel=2,frame_start=1)
  strip.frame_offset_start=round(sh['start']*24);strip.frame_final_duration=round((sh['end']-sh['start'])*24)
  strip.transform.scale_x=2800/3840;strip.transform.scale_y=2800/3840;strip.transform.offset_x=-480;strip.transform.offset_y=17.5
  add_text(m,f"Title {sh['id']}",'\n'.join(textwrap.wrap(sh['title'],18)),sh['start'],sh['end'],(.765,.73),72,S['palette']['ink'],12)
  add_text(m,f"Caption {sh['id']}",'\n'.join(textwrap.wrap(sh['caption'],57)),sh['start'],sh['end'],(.025,.115),64,S['palette']['ink'],13)
  body='\n\n'.join('\n'.join(textwrap.wrap(t,25)) for t in sh['points'])
  add_text(m,f"Notes {sh['id']}",body,sh['start'],sh['end'],(.765,.49),43,S['palette']['muted'],14)
  add_text(m,f"Source {sh['id']}",sh['source'],sh['start'],sh['end'],(.765,.30),32,S['palette']['muted'],15)
  m.timeline_markers.new(sh['title'],frame=frame(sh['start']))
 add_text(m,'Brand','200 W HIGHLAND',0,90,(.025,.95),53,S['palette']['ink'],16)
 add_text(m,'Concept footer',S['footer'],0,90,(.025,.028),32,S['palette']['muted'],17)
 for j,system in enumerate(['CW','HW','HWC']):add_text(m,'Legend '+system,{'CW':'Cold water','HW':'Hot water','HWC':'Circulation return'}[system],0,90,(.765,.20-j*.028),34,S['palette'][system],18+j)
 audio=ROOT/'audio/mix.wav'
 if audio.exists():m.sequence_editor.strips.new_sound('Narration + original score',str(audio),channel=7,frame_start=1)
 m['purpose']='Editable source-camera assembly. Delivered MP4 uses the same model rig with a separate high-resolution typography composite.'
 m['source_notes']='All physical geometry remains assumed as recorded in the original installation spec.'
 m.frame_set(1);return m
def build():
 bpy.ops.wm.read_factory_settings(use_empty=True);scenes={}
 for kind,name in [('shared','Highland-installation-shared.blend'),('unit','Highland-installation-unit-B.blend')]:
  with bpy.data.libraries.load(str(SRC/name),link=False) as (source,target):target.scenes=[source.scenes[0]]
  sc=target.scenes[0];sc.name='3D - '+('Shared distribution' if kind=='shared' else 'Unit B installation');scenes[kind]=sc
 rig_unit(scenes['unit']);rig_shared(scenes['shared']);presentation_materials();smooth_actions()
 m=master_scene(scenes);bpy.context.window.scene=m;bpy.context.preferences.filepaths.save_version=0
 for sc in bpy.data.scenes:
  sc['geometry_provenance']='Preserved from supplied Highland installation models; assumed geometry remains assumed.'
 bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Highland-repipe-90s.blend'))
 return scenes
def scenes_from_file():
 bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Highland-repipe-90s.blend'))
 return {'shared':bpy.data.scenes['3D - Shared distribution'],'unit':bpy.data.scenes['3D - Unit B installation']}
def render(scenes,preview=False):
 results=[]
 for sh in S['shots']:
  sc=scenes[sh['scene']];bpy.context.window.scene=sc
  times=[(sh['start']+sh['end'])/2] if preview else [sh['start']+i/S['render_fps'] for i in range(round((sh['end']-sh['start'])*S['render_fps']))]
  folder=ROOT/'preview' if preview else FRAMES/f"shot-{sh['id']:02}";folder.mkdir(exist_ok=True,parents=True)
  t0=time.time()
  for i,t in enumerate(times):
   path=folder/(f"shot-{sh['id']:02}.png" if preview else f'{i:04}.png')
   if not preview and path.exists() and path.stat().st_size>10000:continue
   sc.frame_set(frame(t));bpy.context.view_layer.update();sc.render.filepath=str(path);bpy.ops.render.render(write_still=True)
   if i%18==0:print('PROGRESS',sh['id'],i+1,'/',len(times),'elapsed',round(time.time()-t0,1),flush=True)
  results.append({'shot':sh['id'],'frames':len(times),'seconds':round(time.time()-t0,2)});print('SHOT_COMPLETE',results[-1],flush=True)
 if not preview:(ROOT/'render-result.json').write_text(json.dumps(results,indent=2))
if __name__=='__main__':
 scenes=scenes_from_file() if '--resume' in sys.argv else build()
 render(scenes,'--preview' in sys.argv)
