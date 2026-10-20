"""Add source-tagged detail, make daylight/film scenes and export the film asset."""
import argparse
import json
import math
import random
from pathlib import Path

import bpy
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
OUT=ROOT/'deliverables/highland-refined';OUT.mkdir(parents=True,exist_ok=True)
S=json.loads((HERE/'exterior-revised.spec.json').read_text())
D=json.loads((HERE/'detail-spec.json').read_text());I=.0254
p=argparse.ArgumentParser();p.add_argument('--preview',action='store_true');p.add_argument('--build-only',action='store_true');A=p.parse_args()
bpy.context.preferences.filepaths.use_scripts_auto_execute=False
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'build/highland-refined/presentation/Highland-dusk.blend'),load_ui=False,use_scripts=False)
night=bpy.context.scene;night.name='Dusk exterior film'
col=bpy.data.collections.new('Reference-led exterior detail');night.collection.children.link(col)

def tag(o,source=None):
    o['status']='assumed';o['source']=source or D['source'];o['basis']=D['basis'];return o

def material(name,color,rough=.6,metal=0):
    m=bpy.data.materials.new(name);m.use_nodes=True;b=m.node_tree.nodes.get('Principled BSDF')
    b.inputs['Base Color'].default_value=(*color,1);b.inputs['Roughness'].default_value=rough;b.inputs['Metallic'].default_value=metal
    m.diffuse_color=(*color,1);return m

def mesh(name,vs,fs,mat):
    data=bpy.data.meshes.new(name);data.from_pydata(vs,[],fs);data.update();o=bpy.data.objects.new(name,data);col.objects.link(o);data.materials.append(mat);return tag(o)

def box(name,c,size,mat,bevel=0):
    x,y,z=c;dx,dy,dz=[v/2 for v in size]
    vs=[(x-dx,y-dy,z-dz),(x+dx,y-dy,z-dz),(x+dx,y+dy,z-dz),(x-dx,y+dy,z-dz),(x-dx,y-dy,z+dz),(x+dx,y-dy,z+dz),(x+dx,y+dy,z+dz),(x-dx,y+dy,z+dz)]
    o=mesh(name,vs,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],mat)
    if bevel:
        mod=o.modifiers.new('Small edge radius','BEVEL');mod.width=bevel;mod.segments=2
    return o

def tube(name,points,r,mat):
    data=bpy.data.curves.new(name,'CURVE');data.dimensions='3D';data.bevel_depth=r;data.bevel_resolution=2
    sp=data.splines.new('POLY');sp.points.add(len(points)-1)
    for p,v in zip(sp.points,points):p.co=(*v,1)
    o=bpy.data.objects.new(name,data);col.objects.link(o);data.materials.append(mat);return tag(o)

def disc(name,c,r,h,mat):
    vs=[]
    for z in (-h/2,h/2):
        for j in range(24):vs.append((c[0]+r*math.cos(j*math.tau/24),c[1]+r*math.sin(j*math.tau/24),c[2]+z))
    fs=[tuple(reversed(range(24))),tuple(range(24,48))]+[(j,(j+1)%24,(j+1)%24+24,j+24) for j in range(24)]
    return mesh(name,vs,fs,mat)

steel=material('Detail / dark coated metal',(.025,.033,.032),.4,.5)
wood=material('Detail / teak',(.23,.13,.058),.63)
stone=bpy.data.materials['concrete'];brick=bpy.data.materials['brick-x']
def grade(x,y):
    xf=min(1,max(0,x/(1420*I)));yf=min(1,max(0,y/(1800*I)))
    return yf*(228*(1-xf)+144*xf)*I
ground=D['assumed_context_ground_m'];xs=[ground['x_bounds'][0],0,1420*I,ground['x_bounds'][1]];ys=[ground['y_bounds'][0],0,1800*I,ground['y_bounds'][1]]
vs=[(x,y,grade(x,y)-.025) for y in ys for x in xs];fs=[]
for j in range(len(ys)-1):
    for k in range(len(xs)-1):
        a=j*len(xs)+k;fs.append((a,a+1,a+len(xs)+1,a+len(xs)))
mesh('Context ground / extended assumed grade',vs,fs,bpy.data.materials['ground'])
for o in night.objects:
    if 'garden hedge' in o.name.lower():o.scale.z*=D['hedge_height_scale']

# The photograph shows a planted terrace edge rather than an exposed slab lawn.
# Sections and levels below are explicitly assumed, separate from the footprint.
g=D['south_garden'];lo,hi=g['x_range_m'];front,back=g['front_y_m'],g['back_y_m'];h=g['wall_height_m'];t=g['wall_thickness_m']
for a,b in [(lo,21.5),(23.2,hi)]:
    box('South garden / brick retaining edge',((a+b)/2,front,h/2),(b-a,t,h),brick)
    box('South garden / pale coping',((a+b)/2,front,h+.035),(b-a+.10,t+.09,.07),stone)
    box('South garden / terrace surface',((a+b)/2,(front+back)/2,g['patio_height_m']),(b-a,back-front,.08),stone)
for k in range(4):
    z=(k+1)*.15;box('Private garden / illustrative step',(22.35,front-.8+k*.24,z/2),(1.7,.24,z),stone)
for x in (21.5,23.2):
    tube('Garden entry / handrail',[(x,front-.85,.90),(x,front+.12,1.50),(x,front+.55,1.50)],.018,steel)

# Furnish only selected wide balcony recesses. Keep pieces inside each bay.
furnished=[]
for e in S['openings']:
    if e['kind']!='balcony' or e['level'] not in ('R2','R3','R4') or e['width']<65:continue
    if (sum(map(ord,e['id']))%3)==0:continue
    poly=S['polygons'][e['polygon']];a,b=poly[e['segment']],poly[(e['segment']+1)%len(poly)]
    u=Vector((b[0]-a[0],b[1]-a[1],0)).normalized();n=Vector((-u.y,u.x,0))
    along=(e['u']-a[0])/u.x if abs(u.x)>.5 else (e['u']-a[1])/u.y
    c=(Vector((a[0],a[1],0))+u*along)*I-n*.65
    floor=next(v['z'] for v in S['levels'] if v['name']==e['level'])*I
    def at(x,y,z):return c+u*x+n*y+Vector((0,0,floor+z))
    disc('Balcony / teak table top',at(0,0,.70),.27,.045,wood)
    tube('Balcony / pedestal',[at(0,0,.03),at(0,0,.68)],.025,steel)
    for side in (-1,1):
        cc=at(side*.54,-.04,.43)
        for j in range(5):
            q=box('Balcony / chair seat slat',cc+n*((j-2)*.065),(.38,.052,.025) if abs(u.x)>.5 else (.052,.38,.025),wood,.006)
        for sign in (-1,1):
            tube('Balcony / chair leg',[at(side*.54+sign*.16,-.20,.02),at(side*.54+sign*.16,-.20,.45),at(side*.54+sign*.16,.14,.82)],.011,steel)
        for zz in (.56,.66,.76):tube('Balcony / chair back',[at(side*.54-.17,.14,zz),at(side*.54+.17,.14,zz)],.018,wood)
    furnished.append(e['id'])

# Add small parked-car detail and soften the earlier low-polygon body shell.
for o in list(night.objects):
    if '/ coachwork' in o.name:
        mod=o.modifiers.new('Rounded vehicle shell','SUBSURF');mod.levels=1;mod.render_levels=2
    if '/ cabin' in o.name:
        edges=set()
        for poly in o.data.polygons:
            for a,b in zip(poly.vertices,list(poly.vertices[1:])+[poly.vertices[0]]):edges.add(tuple(sorted((a,b))))
        for a,b in edges:tube('Vehicle / glazing trim',[o.data.vertices[a].co,o.data.vertices[b].co],.012,steel)

# Quiet facade frames/cornices make the OSM context read as buildings. These are
# assumed details; the original mapped footprint and inherited height are kept.
context_trim=material('Context / stone trim',(.27,.26,.23),.83)
for o in list(night.objects):
    if o.type=='MESH' and o.name.startswith('OSM context /'):
        n=len(o.data.vertices)//2
        for j in range(n):
            a=o.data.vertices[j+n].co;b=o.data.vertices[(j+1)%n+n].co
            tube('Context / roof cornice',[a,b],.10,context_trim)
    elif o.type=='MESH' and o.name.startswith('Context window'):
        pts=[v.co.copy() for v in o.data.vertices]
        tube('Context / window surround',pts+[pts[0]],.035,context_trim)

lit_ids=[o.name.split(' / ',1)[-1] for o in night.objects if o.type=='LIGHT' and o.name.startswith('Apartment warm light / ')]
day=night.copy();day.name='Daylight reference comparison'
# Copies share geometry, with different world, camera and light visibility.
day.compositing_node_group=night.compositing_node_group.copy()
for node in day.compositing_node_group.nodes:
    if node.bl_idname=='CompositorNodeRLayers':node.scene=day
day.world=night.world.copy();day.world.name='Daylight / source photo comparison'
for node in day.world.node_tree.nodes:
    if node.bl_idname=='ShaderNodeBackground':node.inputs['Strength'].default_value=.8
    if node.bl_idname=='ShaderNodeMixRGB':node.inputs[0].default_value=0
day.view_layers[0].layer_collection.children['Presentation / lighting'].exclude=True
def find_layer(layer,name):
    if layer.name==name:return layer
    for c in layer.children:
        found=find_layer(c,name)
        if found:return found
find_layer(day.view_layers[0].layer_collection,'Site').exclude=True
dry_site=bpy.data.collections.new('Daylight / dry site surfaces');day.collection.children.link(dry_site)
dry_materials={}
for mat_name in ('road','paving'):
    m=bpy.data.materials[mat_name].copy();m.name='Daylight / dry '+mat_name
    b=m.node_tree.nodes.get('Principled BSDF')
    for link in list(m.node_tree.links):
        if link.to_socket==b.inputs['Roughness']:m.node_tree.links.remove(link)
    b.inputs['Roughness'].default_value=.86;b.inputs['Coat Weight'].default_value=0
    if mat_name=='road':b.inputs['Base Color'].default_value=(.12,.13,.14,1)
    dry_materials[mat_name]=m
for o in bpy.data.collections['Site'].objects:
    copy=o.copy();copy.data=o.data.copy();dry_site.objects.link(copy)
    for j,m in enumerate(copy.data.materials):
        if m.name in dry_materials:copy.data.materials[j]=dry_materials[m.name]
sun_col=bpy.data.collections.new('Daylight / sun');day.collection.children.link(sun_col)
light_data=bpy.data.lights.new('Daylight key','SUN');light_data.energy=2.1;light_data.angle=math.radians(3)
sun=bpy.data.objects.new('Daylight key',light_data);sun_col.objects.link(sun);sun.rotation_euler=Vector((.4,.55,-1)).to_track_quat('-Z','Y').to_euler();tag(sun)
cam=night.camera.copy();cam.data=night.camera.data.copy();cam.name='Daylight comparison camera';cam.animation_data_clear();day.collection.objects.link(cam);day.camera=cam
cam.location=D['daylight_camera']['position_m'];cam.rotation_euler=(Vector(D['daylight_camera']['target_m'])-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.lens=D['daylight_camera']['lens_mm'];cam.data.shift_y=0
day.render.resolution_x=1440 if A.preview else 1920;day.render.resolution_y=960 if A.preview else 1280;day.cycles.samples=24 if A.preview else 48;day.cycles.adaptive_threshold=.05
day.view_settings.exposure=.5;day.view_settings.look='AgX - Medium High Contrast'
day.render.filepath=str(OUT/('Highland-daylight-preview.png' if A.preview else 'Highland-daylight-revised.png'))

# A continuous, source-coordinate camera path, also saved in the native scene.
cam=night.camera;cam.name='Dusk approach and rise';cam.animation_data_clear();cam.data.animation_data_clear()
for k in D['film']['keys']:
    cam.location=k['position_m'];cam.rotation_euler=(Vector(k['target_m'])-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.lens=k['lens_mm']
    cam.keyframe_insert(data_path='location',frame=k['frame']);cam.keyframe_insert(data_path='rotation_euler',frame=k['frame']);cam.data.keyframe_insert(data_path='lens',frame=k['frame'])
for owner in (cam,cam.data):
    if owner.animation_data and owner.animation_data.action:
        for layer in owner.animation_data.action.layers:
            for strip in layer.strips:
                for bag in strip.channelbags:
                    for curve in bag.fcurves:
                        for point in curve.keyframe_points:point.interpolation='BEZIER';point.handle_left_type='AUTO_CLAMPED';point.handle_right_type='AUTO_CLAMPED'
night.frame_start=1;night.frame_end=432;night.render.fps=24;night.render.resolution_x=1920;night.render.resolution_y=1080;night.camera.data.shift_y=0
night.render.filepath='//native-film/frame-'
controls=[]
architecture=[o for c in ('Envelope','Glazing','Balconies','Roof') for o in bpy.data.collections[c].objects if o.type=='MESH']
coords=[o.matrix_world@Vector(v) for o in architecture for v in o.bound_box]
lo=Vector([min(v[j] for v in coords) for j in range(3)]);hi=Vector([max(v[j] for v in coords) for j in range(3)])
corners=[Vector((x,y,z)) for x in (lo.x,hi.x) for y in (lo.y,hi.y) for z in (lo.z,hi.z)]
clipped=[];minimum_margin=1
for f in range(1,433):
    night.frame_set(f)
    # The full registered architectural envelope must remain inside every frame.
    projected=[world_to_camera_view(night,cam,v) for v in corners]
    margin=min(min(p.x,p.y,1-p.x,1-p.y) for p in projected)
    minimum_margin=min(minimum_margin,margin)
    if margin<.015:clipped.append({'frame':f,'margin':margin})
    q=cam.rotation_euler.to_quaternion();direction=q@Vector((0,0,-1));target=cam.location+direction*100
    fov_y=2*math.atan((cam.data.sensor_width/cam.data.lens/2)*1080/1920)
    controls.append({'frame':f,'time':(f-1)/24,'position_m':list(cam.location),'target_m':list(target),'vertical_fov_degrees':math.degrees(fov_y)})
assert not clipped,clipped[:5]
night.frame_set(145)
# Captions are native camera overlays in both scenes; the GLB export excludes
# FONT objects and the film capture supplies its own fixed overlay.
day_text=bpy.data.collections.new('Daylight / study notice');day.collection.children.link(day_text)
for o in bpy.data.collections['Presentation / typography'].objects:
    copy=o.copy();copy.data=o.data.copy();day_text.objects.link(copy);copy.parent=day.camera;copy.name='Daylight / '+o.name
    hw=day.camera.data.sensor_width/day.camera.data.lens;vh=hw*1280/1920
    is_note='Notice' in o.name
    copy.location=(-hw*.465,-vh*(.472 if is_note else .444),-1);copy.data.size=vh*(.0083 if is_note else .0145);copy.hide_render=False
    hw=cam.data.sensor_width/cam.data.lens;vh=hw*1080/1920
    o.location=(-hw*.465,-vh*(.472 if is_note else .444),-1);o.data.size=vh*(.0083 if is_note else .0145)
bpy.context.window.scene=night
bpy.ops.file.pack_all()
# Store portable render destinations; use an absolute path only for this run.
day.render.filepath='//Highland-daylight-revised.png'
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Highland-revised-daylight-and-film.blend'))
(OUT/'camera-path.json').write_text(json.dumps(controls,indent=2)+'\n')
report={'opening_count':len(S['openings']),'remaining_unresolved_candidates':len(S['rejected_candidates']),'restored_source_candidates':10,'camera_frames_checked':432,'minimum_frame_margin':minimum_margin,'camera_clips':clipped,'furnished_balconies':furnished,'film_dimensions':[1920,1080],'duration_seconds':18,'fps':24,'lit_window_ids':lit_ids}
(OUT/'revision-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print('SCENE READY',json.dumps({k:v for k,v in report.items() if k!='lit_window_ids'}),flush=True)
# The portable asset uses an explicit animation LOD for foliage. The full native
# scene keeps every leaf; source architecture is not decimated.
bpy.ops.object.select_all(action='DESELECT')
for o in night.objects:
    if o.type in ('MESH','CURVE') and o.visible_get():o.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(OUT/'Highland-revised-exterior.glb'),export_format='GLB',use_selection=True,export_extras=True,export_animations=False,export_cameras=False,export_lights=False)
print('GLB EXPORTED',flush=True)
if not A.build_only:
    day.render.filepath=str(OUT/('Highland-daylight-preview.png' if A.preview else 'Highland-daylight-revised.png'))
    bpy.context.window.scene=day;bpy.ops.render.render(write_still=True,scene=day.name)
    print('DAYLIGHT RENDER COMPLETE',day.render.filepath,flush=True)
