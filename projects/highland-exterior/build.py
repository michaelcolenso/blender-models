"""Build an editable, source-tagged exterior study from the separate exterior spec."""
from pathlib import Path
import json,math,sys
import bpy
from mathutils import Vector
from mathutils.geometry import tessellate_polygon
H=Path(__file__).parent;OUT=H.parent.parent/'build/highland-exterior';OUT.mkdir(parents=True,exist_ok=True)
S=json.loads((H/'exterior.spec.json').read_text());I=.0254
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene;scene.unit_settings.system='IMPERIAL';scene.unit_settings.length_unit='INCHES'
scene.render.engine='CYCLES';scene.cycles.samples=24;scene.cycles.use_denoising=True;scene.render.threads_mode='FIXED';scene.render.threads=4
scene.render.resolution_x=1600;scene.render.resolution_y=1100;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='AgX'
world=bpy.data.worlds.new('Daylight');scene.world=world;world.use_nodes=True;bg=world.node_tree.nodes.get('Background');bg.inputs['Color'].default_value=(.30,.45,.65,1);bg.inputs['Strength'].default_value=.5
bpy.ops.object.light_add(type='SUN',location=(30,-35,40));sun=bpy.context.object;sun.rotation_euler=Vector((-100,130,-160)).to_track_quat('-Z','Y').to_euler();sun.data.energy=3.0;sun.data.angle=math.radians(5)
root=bpy.data.collections.new('Highland / exterior study');scene.collection.children.link(root)
collections={}
for name in ['Envelope','Glazing','Balconies','Roof','Site']:
 c=bpy.data.collections.new(name);root.children.link(c);collections[name]=c
mats={}
def mat(name,color,metal=0,rough=.5,emission=False):
 m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);m.use_nodes=True;b=m.node_tree.nodes.get('Principled BSDF');b.inputs['Base Color'].default_value=(*color,1);b.inputs['Metallic'].default_value=metal;b.inputs['Roughness'].default_value=rough
 if emission:
  nodes=m.node_tree.nodes;nodes.remove(b);em=nodes.new('ShaderNodeEmission');em.inputs['Color'].default_value=(*color,1);m.node_tree.links.new(em.outputs[0],nodes.get('Material Output').inputs['Surface'])
 mats[name]=m;return m
for name,c,metal,rough in [('concrete',(.65,.61,.52),0,.78),('metal',(.08,.10,.11),.45,.32),('frame',(.008,.012,.015),.65,.25),('glass',(.025,.065,.11),.6,.18),('rail',(.16,.18,.17),.7,.3),('roof',(.30,.33,.32),.1,.85),('ground',(.28,.30,.245),0,.95),('paving',(.48,.49,.46),0,.85),('road',(.095,.11,.12),0,.95),('plant',(.12,.20,.075),0,.9),('confirmed',(.12,.72,.28),0,.65),('provisional',(.95,.64,.05),0,.65),('assumed',(1,.24,.035),0,.65)]:mat(name,c,metal,rough)
for axis in ['x','y']:
 m=mat('brick-'+axis,(.28,.10,.05),0,.7);nodes=m.node_tree.nodes;links=m.node_tree.links;b=nodes.get('Principled BSDF');geo=nodes.new('ShaderNodeNewGeometry');sep=nodes.new('ShaderNodeSeparateXYZ');links.new(geo.outputs['Position'],sep.inputs[0]);co=nodes.new('ShaderNodeCombineXYZ');links.new(sep.outputs[axis.upper()],co.inputs['X']);links.new(sep.outputs['Z'],co.inputs['Y']);brick=nodes.new('ShaderNodeTexBrick');links.new(co.outputs[0],brick.inputs['Vector']);brick.inputs['Color1'].default_value=(.32,.12,.055,1);brick.inputs['Color2'].default_value=(.24,.075,.028,1);brick.inputs['Mortar'].default_value=(.15,.13,.11,1);brick.inputs['Scale'].default_value=1;brick.inputs['Mortar Size'].default_value=.003;brick.inputs['Brick Width'].default_value=.205;brick.inputs['Row Height'].default_value=.073;links.new(brick.outputs['Color'],b.inputs['Base Color']);bump=nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.25;bump.inputs['Distance'].default_value=.004;links.new(brick.outputs['Fac'],bump.inputs['Height']);links.new(bump.outputs[0],b.inputs['Normal'])
objects=[]
def obj(name,verts,faces,material,collection,source,status='assumed',basis='Simplified exterior geometry; dimensions or details are assumed unless a separate confirmed datum is recorded.'):
 mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],faces);mesh.update();o=bpy.data.objects.new(name,mesh);collections[collection].objects.link(o);o.data.materials.append(mats[material]);o['id']=name;o['status']=status;o['source']=source;o['basis']=basis;o['finish_status']='assumed';objects.append(o);return o
FACES=[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]
def boxes(name,parts,material,collection,source,status='assumed',basis=None):
 vs=[];fs=[]
 for center,dims in parts:
  x,y,z=[a*I for a in center];dx,dy,dz=[a*I*.5 for a in dims];k=len(vs);vs.extend([(x-dx,y-dy,z-dz),(x+dx,y-dy,z-dz),(x+dx,y+dy,z-dz),(x-dx,y+dy,z-dz),(x-dx,y-dy,z+dz),(x+dx,y-dy,z+dz),(x+dx,y+dy,z+dz),(x-dx,y+dy,z+dz)]);fs.extend([tuple(k+i for i in f) for f in FACES])
 if not vs:return
 return obj(name,vs,fs,material,collection,source,status,basis or 'Representative sections and thicknesses; source controls arrangement, not every component dimension.')
def slab(name,poly,z,thick,material='concrete',collection='Envelope',source='A2.03/A2.04/A2.07 plan outline',status='assumed'):
 ps=[Vector((x*I,y*I,0)) for x,y in poly];vs=[(p.x,p.y,z*I) for p in ps]+[(p.x,p.y,(z+thick)*I) for p in ps];n=len(ps);fs=[]
 for tri in tessellate_polygon([ps]):
  ids=[p if isinstance(p,int) else min(range(n),key=lambda i:(ps[i]-p).length) for p in tri];fs.append(tuple(reversed(ids)));fs.append(tuple(i+n for i in ids))
 fs.extend([(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]);return obj(name,vs,fs,material,collection,source,status)
def segment_data(a,b):
 v=Vector((b[0]-a[0],b[1]-a[1],0));L=v.length;v.normalize();return v,Vector((-v.y,v.x,0)),L

def facade_part(a,tangent,normal,u,z,width,height,depth,offset=0):
 c=Vector((a[0],a[1],z))+tangent*u+normal*offset
 return (list(c),[width if abs(tangent.x)>.5 else depth,depth if abs(tangent.x)>.5 else width,height])

def rail(name,a,b,z,source,collection='Balconies'):
 v,n,L=segment_data(a,b);parts=[]
 for zz,d in [(z+S['guard_height'],1.7),(z+4,1.2),(z+S['guard_height']*.5,1.0)]:parts.append(facade_part(a,v,n,L/2,zz,L,d,1.5))
 count=max(1,math.ceil(L/36))
 for k in range(count+1):parts.append(facade_part(a,v,n,L*k/count,z+S['guard_height']/2,.8,S['guard_height'],.8))
 boxes(name,parts,'rail',collection,source)

# Boolean-free facade walls, with actual openings in the envelope.
opening_count=0;clipped=[]
for li,level in enumerate(S['levels']):
 name,z,pk=level['name'],level['z'],level['polygon'];poly=S['polygons'][pk];top=S['levels'][li+1]['z'] if li<5 else S['roof_plate_z']
 slab('slab-'+name,poly,z-7,7,'concrete')
 for j,(a,b) in enumerate(zip(poly,poly[1:]+poly[:1])):
  v,n,L=segment_data(a,b);axis='x' if abs(v.x)>.5 else 'y';walltop=top
  if name=='R5' and (a[1]+b[1])/2>S['north_roof_split_y']:walltop=S['north_roof_plate_z']
  ops=[e for e in S['openings'] if e['level']==name and e['segment']==j]
  holes=[]
  for e in ops:
   center=(e['u']-a[0])/v.x if axis=='x' else (e['u']-a[1])/v.y
   recess=e['kind']=='balcony' and name not in ['P1','R1'];pad=14 if recess else 0
   lo=max(0,center-e['width']/2-pad);hi=min(L,center+e['width']/2+pad);zb=z+4 if recess else max(z,e['z']);zt=walltop-7 if recess else min(walltop,e['z']+e['height']);holes.append((lo,hi,zb,zt,e,center));opening_count+=1
   if abs(lo-(center-e['width']/2-pad))>.01 or abs(hi-(center+e['width']/2+pad))>.01:clipped.append(e['id'])
  xs=sorted(set([0,L]+[x for h in holes for x in h[:2]]));zs=sorted(set([z,walltop]+[x for h in holes for x in h[2:4]]));parts={}
  for x0,x1 in zip(xs,xs[1:]):
   for z0,z1 in zip(zs,zs[1:]):
    u=(x0+x1)/2;zz=(z0+z1)/2
    if any(h[0]<u<h[1] and h[2]<zz<h[3] for h in holes):continue
    material='metal' if name=='R5' and (a[1]+b[1])/2<1110 else 'brick-'+axis
    if name=='P1' and n.y>0.5:material='concrete'
    for lo,hi,zb,zt,e,center in holes:
     if e['kind'] in ['balcony','entry'] and abs(u-center)<e['width']/2+15:material='metal'
     if e['kind']=='wide' and e['face'] in ['east','west'] and e['width']>110 and abs(u-center)<e['width']/2+12:material='concrete'
    parts.setdefault(material,[]).append(facade_part(a,v,n,u,zz,x1-x0,z1-z0,S['wall_thickness']))
  for material,boxes_ in parts.items():boxes(f'wall-{name}-{j}-{material}',boxes_,material,'Envelope','A2.03/.04/.07 outline and A3.01/.02 facade pattern')
  # Floor edge/cap dimensions remain representative.
  boxes(f'edge-{name}-{j}',[facade_part(a,v,n,L/2,z+1,L,3.5,10,.5)],'concrete','Envelope','A3.01/A3.02 floor and facade bands')
  for lo,hi,zb,zt,e,center in holes:
   recess=e['kind']=='balcony' and name not in ['P1','R1'];baywidth=hi-lo
   if recess:center=(lo+hi)/2
   w=min(e['width'],baywidth-4) if recess else hi-lo;zb=e['z'] if recess else zb;zt=e['z']+e['height'] if recess else zt;h=zt-zb;cz=(zb+zt)/2;off=S['wall_thickness']/2+.5-(S['balcony_depth']-4 if recess else 0)
   if recess:
    dep=S['balcony_depth'];parts=[facade_part(a,v,n,center,(z+walltop)/2,baywidth,walltop-z-6,6,-dep),facade_part(a,v,n,center-baywidth/2,(z+walltop)/2,6,walltop-z,dep,-dep/2),facade_part(a,v,n,center+baywidth/2,(z+walltop)/2,6,walltop-z,dep,-dep/2)]
    boxes(e['id']+'-recess',parts,'metal','Balconies','A3.01/A3.02 and user photo-02; recess depth assumed 60 inches')
   glass=boxes(e['id']+'-glazing',[facade_part(a,v,n,center,cz,w-3,h-3,1,off-.6)],'glass','Glazing',e['source']);glass['reference_opening']=e['id'];glass['xy_status']='provisional'
   frame=[facade_part(a,v,n,center-w/2+1,cz,2,h,3,off),facade_part(a,v,n,center+w/2-1,cz,2,h,3,off),facade_part(a,v,n,center,zb+1,w,2,3,off),facade_part(a,v,n,center,zt-1,w,2,3,off)]
   if e['kind']=='garage':
    for zz in range(int(zb+12),int(zt),12):frame.append(facade_part(a,v,n,center,zz,w,1.3,3,off))
    for uu in [center-w/4,center,center+w/4]:frame.append(facade_part(a,v,n,uu,cz,1.5,h,3,off))
   else:
    divisions=3 if w>100 else 2 if w>38 else 1
    for q in range(1,divisions):frame.append(facade_part(a,v,n,center-w/2+w*q/divisions,cz,1.6,h,3,off))
    if h>70:frame.append(facade_part(a,v,n,center,zb+20,w,1.5,3,off))
   boxes(e['id']+'-frames',frame,'frame','Glazing',e['source'])
   boxes(e['id']+'-sill',[facade_part(a,v,n,center,zb-2,w+5,3,12,off-2)],'concrete','Glazing',e['source'])
   if recess:
    dep=S['balcony_depth'];start=Vector((a[0],a[1],0))+v*(center-baywidth/2)+n*5;end=start+v*baywidth
    boxes(e['id']+'-deck',[facade_part(a,v,n,center,z-2,baywidth,4,dep,-dep/2)],'concrete','Balconies',e['source'])
    rail(e['id']+'-guard',start[:2],end[:2],z,e['source'])
   if e['kind']=='entry':
    # Canopy and entry landing are illustrative sections based on the drawn form.
    boxes('east-entry-canopy',[facade_part(a,v,n,center,z+109,w+30,5,84,42)],'metal','Envelope','A3.01 east entry canopy; section and projection assumed')
    boxes('east-entry-landing',[facade_part(a,v,n,center,z-4,w+30,8,72,36)],'concrete','Site','A3.01 east entry; landing/grade dimensions assumed')
    for k in range(5):boxes('east-entry-step-'+str(k),[facade_part(a,v,n,center,z-7*(k+1),w+30,7,12,78+12*k)],'concrete','Site','A3.01 east stair form; risers/treads assumed')
# Roof plates, setbacks, parapets and terrace rails.
def clip(poly,threshold,above):
 result=[]
 for a,b in zip(poly,poly[1:]+poly[:1]):
  ai=(a[1]>=threshold) if above else (a[1]<=threshold);bi=(b[1]>=threshold) if above else (b[1]<=threshold)
  if ai:result.append(a)
  if ai!=bi:
   t=(threshold-a[1])/(b[1]-a[1]);result.append([a[0]+t*(b[0]-a[0]),threshold])
 return result
for label,poly,z in [('south',clip(S['polygons']['r5'],1110,False),S['roof_plate_z']),('north',clip(S['polygons']['r5'],1110,True),S['north_roof_plate_z'])]:slab('roof-'+label,poly,z-5,5,'roof','Roof','A2.08 roof outline; drainage falls omitted')
for j,(a,b) in enumerate(zip(S['polygons']['r5'],S['polygons']['r5'][1:]+S['polygons']['r5'][:1])):
 v,n,L=segment_data(a,b);z=S['north_roof_plate_z'] if (a[1]+b[1])/2>1110 else S['roof_plate_z'];h=16 if z==S['north_roof_plate_z'] else 22
 boxes('roof-parapet-'+str(j),[facade_part(a,v,n,L/2,z+h/2,L,h,8),facade_part(a,v,n,L/2,z+h+j*.02,L+30,7,44)],'concrete','Roof','A2.08 parapet elevations; local sections simplified')
split_x=[p[0] for p in clip(S['polygons']['r5'],1110,False) if abs(p[1]-1110)<.001]
lo,hi=min(split_x),max(split_x)
boxes('roof-step-closure',[([(lo+hi)/2,1110,(S['roof_plate_z']+S['north_roof_plate_z'])/2],[hi-lo,8,S['north_roof_plate_z']-S['roof_plate_z']])],'metal','Roof','A2.08 roof level change; band follows provisional footprint')
# Exposed R5 terrace surface uses the lower story outline. No landscaped roof is invented.
slab('R5-terrace-surface',S['polygons']['typical'],625,2,'concrete','Roof','A2.07 terrace extents, simplified')
def inside(p,poly):
 x,y=p;c=False
 for a,b in zip(poly,poly[1:]+poly[:1]):
  if (a[1]>y)!=(b[1]>y) and x<(b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0]:c=not c
 return c
for j,(a,b) in enumerate(zip(S['polygons']['typical'],S['polygons']['typical'][1:]+S['polygons']['typical'][:1])):
 v,n,L=segment_data(a,b);mid=(Vector(a)+Vector(b))*.5
 if not inside(mid,S['polygons']['r5']):rail('R5-terrace-guard-'+str(j),a,b,627,'A3.01/A3.02 upper terrace guards; sections assumed')
for e in S['roof_features']:
 p=e['polygon'];z=e['z'];top=e['top'];slab(e['id'],p,z,top-z,'metal','Roof',e['source']);objects[-1]['datum_status']='confirmed';objects[-1]['top_elevation_ft']=342+top/12
 for j,(a,b) in enumerate(zip(p,p[1:]+p[:1])):
  v,n,L=segment_data(a,b);boxes(e['id']+'-cap-'+str(j),[facade_part(a,v,n,L/2,top+j*.02,L+18,6,30)],'concrete','Roof',e['source'])
  if e['id']=='south-clerestory' and n.y<-.5:
   for k in range(4):
    u=(k+.5)*L/4;w=L/4-22;zz=(z+top)/2
    boxes(f'clerestory-glass-{k}',[facade_part(a,v,n,u,zz,w,23,1,5)],'glass','Glazing','A3.01 south clerestory glazing; dimensions representative')
    parts=[facade_part(a,v,n,u-w/2,zz,2,25,2,6),facade_part(a,v,n,u+w/2,zz,2,25,2,6),facade_part(a,v,n,u,zz-12,w,2,2,6),facade_part(a,v,n,u,zz+12,w,2,2,6)]
    boxes(f'clerestory-frame-{k}',parts,'frame','Glazing','A3.01 south clerestory glazing')
# Roof louver screen between the two tower volumes, diagrammatic.
boxes('roof-mechanical-screen',[([804,845,794],[116,240,64])],'metal','Roof','A2.08 roof mechanical zone; equipment envelope assumed')
for k in range(9):boxes('screen-louver-'+str(k),[([804,722,770+k*6],[120,3,2])],'frame','Roof','A2.08 mechanical screen, assumed louver sections')
# Site: a neutral grade study, separate and entirely assumed.
def grade(x,y):
 yf=min(1,max(0,y/1800));xf=min(1,max(0,x/1420));return yf*(228*(1-xf)+144*xf)
# One continuous mesh avoids intersections between independently tessellated slopes.
xs=sorted(set(list(range(-1600,3601,60))+[-1600,-600,-180,0,1420,1510,1590,1670,2250,3600]))
ys=sorted(set(list(range(-1800,3601,60))+[-1800,-550,-180,-150,0,1800,2050,2400,3600]))
vs=[(x*I,y*I,grade(x,y)*I) for y in ys for x in xs];fs=[];indices=[]
for j in range(len(ys)-1):
 for k in range(len(xs)-1):
  a=j*len(xs)+k;fs.append((a,a+1,a+len(xs)+1,a+len(xs)));x=(xs[k]+xs[k+1])/2;y=(ys[j]+ys[j+1])/2
  material=0
  if (1670<x<2250 and -550<y<2400) or (-600<x<2250 and -550<y<-180):material=2
  if (1510<x<1670 and -180<y<2050) or (-180<x<1670 and -180<y<0):material=1
  if 1590<x<1670 and -150<y<2050:material=0
  indices.append(material)
site=obj('continuous-site-context',vs,fs,'ground','Site','A3.01/A3.02 approximate grade and user photos; street widths, planting, grading and surface boundaries assumed')
site.data.materials.append(mats['paving']);site.data.materials.append(mats['road'])
for face,index in zip(site.data.polygons,indices):face.material_index=index
# Photo-informed planting character; positions and envelopes remain assumed.
import random
random.seed(200)
mat('bark',(.12,.075,.035),0,.95)
for k,c in enumerate([(.10,.19,.045),(.16,.26,.07),(.08,.14,.03)]):mat('leaf-'+str(k),c,0,.9)
def branch(name,a,b,r):
 av,bv=Vector(a),Vector(b);axis=(bv-av).normalized();u=axis.cross(Vector((0,1,0))).normalized();v=axis.cross(u);verts=[]
 for pt in [av,bv]:
  for k in range(8):verts.append(tuple((pt+r*(u*math.cos(k*math.tau/8)+v*math.sin(k*math.tau/8)))*I))
 faces=[tuple(range(7,-1,-1)),tuple(range(8,16))]+[(k,(k+1)%8,(k+1)%8+8,k+8) for k in range(8)]
 return obj(name,verts,faces,'bark','Site','User photo-02 / generic street-tree character; placement and dimensions assumed')
def foliage(name,center,dims,color):
 verts=[];faces=[];N=12;M=8
 for j in range(M+1):
  t=math.pi*j/M
  for k in range(N):
   p=math.tau*k/N;r=1+random.uniform(-.12,.12);verts.append(((center[0]+dims[0]*.5*r*math.sin(t)*math.cos(p))*I,(center[1]+dims[1]*.5*r*math.sin(t)*math.sin(p))*I,(center[2]+dims[2]*.5*r*math.cos(t))*I))
 for j in range(M):
  for k in range(N):a=j*N+k;b=j*N+(k+1)%N;faces.append((a,b,b+N,a+N))
 o=obj(name,verts,faces,'leaf-'+str(color),'Site','User photo-02 / planted edges; representative vegetation, not a planting survey')
 for face in o.data.polygons:face.use_smooth=True
for i,(x,y) in enumerate([(1630,330),(1630,920),(1630,1510),(300,-95),(1080,-95)]):
 z=grade(x,y);branch('tree-trunk-'+str(i),[x,y,z],[x,y,z+170],3.5)
 for k in range(9):
  angle=k*math.tau/9;cx=x+55*math.cos(angle);cy=y+55*math.sin(angle);cz=z+180+random.uniform(-25,28)
  branch(f'tree-{i}-branch-{k}',[x,y,z+110],[cx,cy,cz],1.3);foliage(f'tree-{i}-crown-{k}',[cx,cy,cz],[115,115,100],k%3)
for k in range(20):foliage('south-hedge-'+str(k),[80+k*68,20,24],[88,44,48],k%3)
# Source-derived validation, distinct from illustrative detail checks.
assert S['grid_dimensions_in']['x_6_to_10'][-1]==1236
assert S['grid_dimensions_in']['y_H_to_A'][-1]==1800
assert [342+x['z']/12 for x in S['levels']]==S['checks']['floor_elevations_ft']
assert abs(342+S['roof_features'][0]['top']/12-415)<1e-6
assert len({o.name for o in objects})==len(objects)
assert opening_count==len(S['openings'])
for o in objects:assert o.get('source') and o.get('basis') and o.get('status') in ['assumed','provisional','confirmed']
report=dict(source_grid_span_in=[1236,1800],checked_floor_datums=6,openings_built=opening_count,source_candidates_omitted=len(S['rejected_candidates']),opening_build_clips=clipped,objects=len(objects),result='PASS: grid dimensions, floor/tower datums, opening inventory and object provenance. Exterior placement/finishes remain provisional or assumed.',limitations=S['limitations'])
(OUT/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
# Export editable geometry with provenance; no camera labels are baked into GLB.
bpy.ops.object.select_all(action='DESELECT')
for o in objects:o.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(OUT/'Highland-exterior.glb'),export_format='GLB',use_selection=True,export_extras=True)
# Camera and camera-parented annotation, present on every rendered deliverable.
bpy.ops.object.camera_add();cam=bpy.context.object;cam.name='Exterior review camera';scene.camera=cam;cam.data.clip_end=1500;cam.data.lens=48
hud=[]
for name,body,size,y in [('title','200 W. HIGHLAND / EXTERIOR STUDY',.018,-.430),('note','DRAWING-BASED STUDY  |  Facade details, finish colors and site context are provisional / assumed.',.010,-.464)]:
 cu=bpy.data.curves.new(name,'FONT');cu.body=body;ob=bpy.data.objects.new('caption-'+name,cu);scene.collection.objects.link(ob);ob.parent=cam;ob.data.materials.append(mat('caption-'+name,(.92,.95,.97),emission=True));hud.append((ob,size,y))
# Flat caption backing is parented to the camera; export above excludes it.
bpy.ops.mesh.primitive_plane_add(size=1);back=bpy.context.object;back.name='caption backing';back.parent=cam;back.data.materials.append(mat('caption-back',(.012,.023,.032),emission=True))
def setcam(pos,target,ortho=None):
 cam.location=Vector(pos)*12*I;cam.rotation_euler=(Vector(target)*12*I-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO' if ortho else 'PERSP'
 if ortho:cam.data.ortho_scale=ortho*12*I;w=cam.data.ortho_scale
 else:w=cam.data.sensor_width/cam.data.lens
 h=w*scene.render.resolution_y/scene.render.resolution_x
 for ob,size,y in hud:ob.location=(-w*.475,h*y,-1);ob.data.size=h*size
 back.location=(0,-h*.445,-1.01);back.scale=(w,h*.11,1)
 for ob,_,_ in hud:ob.visible_shadow=False
 back.visible_shadow=False
views=[('southeast',(195,-130,12),(58,70,34),None),('east-entry',(245,55,27),(75,92,32),None),('south-review',(58,-250,34),(58,75,34),148),('east-review',(360,75,34),(58,75,34),185),('west-review',(-220,75,34),(58,75,34),185),('north-review',(58,350,34),(58,75,34),148),('plan-review',(58,75,300),(58,75,0),275)]
if '--quick' in sys.argv:views=views[:1];scene.cycles.samples=12;scene.render.resolution_x=1280;scene.render.resolution_y=880
if '--beauty-only' in sys.argv:views=views[:2]
for name,pos,target,scale in views:
 if '--quick' not in sys.argv:scene.cycles.samples=32 if scale is None else 16
 setcam(pos,target,scale);scene.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True)
# Provenance review uses the same geometry and four orthographic/iso directions.
if '--quick' not in sys.argv and '--beauty-only' not in sys.argv:
 original={o.name:list(o.data.materials) for o in objects}
 for o in objects:o.data.materials.clear();o.data.materials.append(mats[o['status']])
 scene.cycles.samples=12;scene.render.resolution_x=1000;scene.render.resolution_y=740
 for name,pos,target,scale in [views[2],views[3],views[-1],views[0]]:
  setcam(pos,target,scale);scene.render.filepath=str(OUT/('provenance-'+name+'.png'));bpy.ops.render.render(write_still=True)
 for o in objects:
  o.data.materials.clear()
  for m in original[o.name]:o.data.materials.append(m)
scene.render.resolution_x=1600;scene.render.resolution_y=1100;scene.cycles.samples=32;setcam(views[0][1],views[0][2]);bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Highland-exterior.blend'));print('EXTERIOR BUILD COMPLETE')
