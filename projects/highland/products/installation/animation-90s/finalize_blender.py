"""Read back geometry and timed states; finish the editable VSE master."""
import bpy,json,hashlib,sys
from pathlib import Path
from mathutils import Vector
import compose_film as film
ROOT=Path(__file__).resolve().parent;SRC=ROOT.parent/'installation';S=json.loads((ROOT/'animation-spec.json').read_text())
def geometry(o):
 if o.type=='CURVE':
  content={'splines':[[list(p.co) for p in sp.points] for sp in o.data.splines],'radius':o.data.bevel_depth}
 elif o.type=='MESH':content={'vertices':[list(v.co) for v in o.data.vertices]}
 else:return None
 content['transform']=[list(o.location),list(o.rotation_euler),list(o.scale)]
 return hashlib.sha256(json.dumps(content,sort_keys=True).encode()).hexdigest()
source_shapes={}
for kind,filename in [('shared','Highland-installation-shared.blend'),('unit','Highland-installation-unit-B.blend')]:
 bpy.ops.wm.open_mainfile(filepath=str(SRC/filename));sc=bpy.context.scene
 if kind=='unit':sc.frame_set(121)
 source_shapes[kind]={o.name:geometry(o) for o in sc.objects if o.get('element_id') and o.type in {'CURVE','MESH'}}
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Highland-repipe-90s.blend'))
results={'source_geometry':{},'staging':{},'movie_timeline':[]}
for kind,name in [('unit','3D - Unit B installation'),('shared','3D - Shared distribution')]:
 sc=bpy.data.scenes[name];bpy.context.window.scene=sc;sc.frame_set(1070);bpy.context.view_layer.update()
 actual={o.name:geometry(o) for o in sc.objects if o.name in source_shapes[kind]}
 missing=set(source_shapes[kind])-set(actual)
 assert not missing,(kind,missing)
 mismatches=[n for n in actual if actual[n]!=source_shapes[kind][n]]
 assert not mismatches,(kind,mismatches)
 results['source_geometry'][kind]={'compared':len(actual),'unchanged':True}
unit=bpy.data.scenes['3D - Unit B installation'];bpy.context.window.scene=unit
def state(t):unit.frame_set(round(t*24)+1);bpy.context.view_layer.update()
def obj(n):return unit.objects[n]
state(28);assert obj('CW-01').hide_render
state(30);assert not obj('CW-01').hide_render and 0<obj('CW-01').data.bevel_factor_end<1
state(44);assert all(not obj(n).hide_render and obj(n).data.bevel_factor_end>.999 for n in S['reveal'])
state(55);assert not obj('TEST-GAUGE').hide_render
state(61);assert not obj('TEST-GAUGE').hide_render
state(63);assert obj('TEST-GAUGE').hide_render and not obj('SVC-CW').hide_render
state(66);assert all(o.hide_render for o in unit.objects if o.name.startswith('Flow '))
state(68);assert all(not o.hide_render for o in unit.objects if o.name.startswith('Flow '))
positions=[tuple(o.location) for o in unit.objects if o.name.startswith('Flow ')]
state(69);assert positions!=[tuple(o.location) for o in unit.objects if o.name.startswith('Flow ')]
state(80);assert obj('A01').hide_render and not obj('A01-RESTORE').hide_render
results['staging']={'roots_grow_after_29s':True,'mains_complete_before_branches':True,'test_boundary_visible_before_transfer':True,'flow_starts_after_depicted_transfer':True,'return_markers_move':True,'restoration_follows_cutover':True}
m=bpy.data.scenes['MASTER - 90 seconds'];bpy.context.window.scene=m
for strip in m.sequence_editor.strips:
 if strip.type=='SCENE':
  sh=next(sh for sh in S['shots'] if strip.name.startswith(f"{sh['id']:02}"))
  assert strip.frame_final_start==round(sh['start']*24)+1,(strip.name,strip.frame_final_start)
  assert strip.frame_final_end==round(sh['end']*24)+1,(strip.name,strip.frame_final_end)
  strip.transform.scale_x=2816/1600;strip.transform.scale_y=2816/1600;strip.transform.offset_x=-480;strip.transform.offset_y=16
  results['movie_timeline'].append({'shot':sh['id'],'start':strip.frame_final_start,'end_exclusive':strip.frame_final_end})
# Rebuild native editable graphics from the same event list used for the movie.
for strip in list(m.sequence_editor.strips):
 if strip.type=='TEXT' or strip.name.startswith('Editorial ') or strip.name=='Source drawing opening':m.sequence_editor.strips.remove(strip)
roles={};rect_roles={}
for i,e in enumerate(film.E):
 a=round(e['start']*24)+1;length=round((e['end']-e['start'])*24)
 if e['type']=='text':
  role=(e['x'],e['y']);channel=32+roles.setdefault(role,len(roles))
  strip=m.sequence_editor.strips.new_effect(name='Editorial '+str(i),type='TEXT',channel=channel,frame_start=a,length=length)
  strip.text=e['text'];strip.font_size=e['size']
  rgb=[int(e['color'][k:k+2],16)/255 for k in (1,3,5)];strip.color=tuple(rgb)+(1,)
  strip.location=(e['x']/3840,1-e['y']/2160);strip.anchor_x='LEFT';strip.anchor_y='TOP';strip.alignment_x='LEFT';strip.use_shadow=False
  strip.font=bpy.data.fonts.load(film.BOLD if e['bold'] else film.FONT,check_existing=True)
 else:
  role=(e['x'],e['y']);channel=4+rect_roles.setdefault(role,len(rect_roles))
  strip=m.sequence_editor.strips.new_effect(name='Editorial '+str(i),type='COLOR',channel=channel,frame_start=a,length=length)
  rgb=[int(e['color'][k:k+2],16)/255 for k in (1,3,5)];strip.color=tuple(rgb)
  strip.transform.scale_x=e['w']/3840;strip.transform.scale_y=e['h']/2160;strip.transform.offset_x=e['x']+e['w']/2-1920;strip.transform.offset_y=1080-e['y']-e['h']/2
assert max(s.channel for s in m.sequence_editor.strips)<128
opening=m.sequence_editor.strips.new_image(name='Source drawing opening',filepath=str(ROOT/'opening-source.png'),channel=3,frame_start=1)
opening.frame_final_duration=60;opening.transform.scale_x=2816/1600;opening.transform.scale_y=2816/1600;opening.transform.offset_x=-480;opening.transform.offset_y=16
for f,v in [(1,1),(39,1),(61,0)]:opening.blend_alpha=v;opening.keyframe_insert(data_path='blend_alpha',frame=f)
for strip in m.sequence_editor.strips:
 if strip.type=='SOUND':strip.sound.filepath=str(ROOT/'audio/mix.wav')
 if strip.name=='Warm paper background':strip.color=tuple(int(S['palette']['paper'][k:k+2],16)/255 for k in (1,3,5))
m.frame_set(1);bpy.ops.file.pack_all();bpy.ops.file.make_paths_relative();bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Highland-repipe-90s.blend'))
(ROOT/'blender-validation.json').write_text(json.dumps(results,indent=2))
print('EDITABLE_MODEL_PASS',results,flush=True)
if '--render-check' in sys.argv:
 m.frame_set(round(55.5*24)+1);m.render.resolution_percentage=25;m.render.image_settings.file_format='PNG';m.render.filepath=str(ROOT/'editable-master-check.png');bpy.ops.render.render(write_still=True)
