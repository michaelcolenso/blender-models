import * as THREE from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {RectAreaLightUniformsLib} from 'three/addons/lights/RectAreaLightUniformsLib.js';

const S=window.FLIGHT_SPEC, I=.0254, stage=document.getElementById('stage');
const scene=new THREE.Scene();scene.background=new THREE.Color(0x394e69);scene.fog=new THREE.Fog(0x394e69,140,400);
const camera=new THREE.PerspectiveCamera(67,1,.025,400);
const renderer=new THREE.WebGLRenderer({antialias:true,powerPreference:'high-performance',preserveDrawingBuffer:true});
renderer.setPixelRatio(Math.min(devicePixelRatio,1.5));renderer.outputColorSpace=THREE.SRGBColorSpace;
renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1.05;
renderer.localClippingEnabled=true;
stage.prepend(renderer.domElement);
scene.add(new THREE.HemisphereLight(0xa8c4ec,0x574733,1.45));
const sun=new THREE.DirectionalLight(0xffd7a4,1.35);sun.position.set(-40,100,75);scene.add(sun);
RectAreaLightUniformsLib.init();
const city=new THREE.Group();city.name='OpenStreetMap neighborhood massing';scene.add(city);
const cityColors=[0x55515a,0x4d4e58,0x62524d,0x4b5661,0x625d59];
const cityMaterials=cityColors.map(color=>new THREE.MeshStandardMaterial({color,roughness:.84,metalness:.03}));
for(const item of S.osm_context.buildings){
 const shape=new THREE.Shape();item.footprint_m.forEach(([x,y],i)=>i?shape.lineTo(x,y):shape.moveTo(x,y));shape.closePath();
 const geometry=new THREE.ExtrudeGeometry(shape,{depth:item.height_m,steps:1,bevelEnabled:false});
 geometry.rotateX(-Math.PI/2);
 const mass=new THREE.Mesh(geometry,cityMaterials[item.osm_id%cityMaterials.length]);
 mass.name=`OSM building ${item.osm_id}`;city.add(mass);
}
const cityGround=new THREE.Mesh(new THREE.PlaneGeometry(350,350),new THREE.MeshStandardMaterial({color:0x242f39,roughness:.27,metalness:.2}));
cityGround.rotation.x=-Math.PI/2;cityGround.position.set(18,-.18,-22);cityGround.name='evening context ground';city.add(cityGround);

const material=(color,roughness=1,metalness=0)=>new THREE.MeshStandardMaterial({color,roughness,metalness,side:THREE.DoubleSide});
const M={wall:material(0xd1c9ba,.72),floor:material(0x4e5553,.38),ceiling:material(0xe7e1d4),trim:material(0x554c43,.32),door:material(0x74604f,.28),metal:material(0x999c92,.26,.65),dark:material(0x29333b),glass:new THREE.MeshPhysicalMaterial({color:0xb5c7c9,transparent:true,opacity:.18,side:THREE.DoubleSide,roughness:.15,metalness:.1}),lamp:new THREE.MeshStandardMaterial({color:0xffefbf,emissive:0xffc581,emissiveIntensity:2.2,side:THREE.DoubleSide}),line:new THREE.MeshBasicMaterial({color:0x567f89})};
function weaveTexture(){
 const canvas=document.createElement('canvas');canvas.width=256;canvas.height=256;
 const ctx=canvas.getContext('2d'),image=ctx.createImageData(256,256);
 for(let y=0;y<256;y++)for(let x=0;x<256;x++){
  const i=(y*256+x)*4,grain=((x*37+y*67+x*y*13)%19)-9;
  const stripe=(Math.floor(x/32)+Math.floor(y/32))%2?8:-4;
  const thread=(x%4===0||y%4===0)?-8:0;
  const v=THREE.MathUtils.clamp(93+stripe+thread+grain,50,130);
  image.data[i]=v+6;image.data[i+1]=v+5;image.data[i+2]=v+1;image.data[i+3]=255;
 }
 ctx.putImageData(image,0,0);const texture=new THREE.CanvasTexture(canvas);
 texture.colorSpace=THREE.SRGBColorSpace;texture.wrapS=texture.wrapT=THREE.RepeatWrapping;texture.repeat.set(2,18);
 return texture;
}
const carpet=weaveTexture();M.floor.color.setHex(0xffffff);M.floor.map=carpet;M.floor.roughness=.86;
M.lobbyFloor=material(0x777e7c,.28,.08);
M.brass=material(0xbda06a,.27,.78);
M.led=new THREE.MeshBasicMaterial({color:0xffdab0,side:THREE.DoubleSide});
const plasterNormal=new Uint8Array(64*64*4);
for(let y=0;y<64;y++)for(let x=0;x<64;x++){
 const i=(y*64+x)*4,n=((x*17+y*23+x*y*7)%17)-8;
 plasterNormal[i]=128+n;plasterNormal[i+1]=128-n;plasterNormal[i+2]=254;plasterNormal[i+3]=255;
}
const plasterMap=new THREE.DataTexture(plasterNormal,64,64);plasterMap.needsUpdate=true;
plasterMap.wrapS=plasterMap.wrapT=THREE.RepeatWrapping;plasterMap.repeat.set(5,6);
M.wall.normalMap=plasterMap;M.wall.normalScale.set(.13,.13);
const pavementData=new Uint8Array(128*128*4);
for(let y=0;y<128;y++)for(let x=0;x<128;x++){
 const i=(y*128+x)*4,v=(x*29+y*41+x*y*3)%101;
 const rough=v<21?45:155+v%45;
 pavementData[i]=rough;pavementData[i+1]=rough;pavementData[i+2]=rough;pavementData[i+3]=255;
}
const pavementMap=new THREE.DataTexture(pavementData,128,128);pavementMap.needsUpdate=true;
pavementMap.wrapS=pavementMap.wrapT=THREE.RepeatWrapping;pavementMap.repeat.set(18,18);
cityGround.material.roughnessMap=pavementMap;
M.wall.transparent=true;M.wall.depthWrite=false;
M.ceiling.emissive.setHex(0xd4c6ae);M.ceiling.emissiveIntensity=.42;
const interior=new THREE.Group();interior.name='R1 lobby / Corridor 108 / illustrative finishes';scene.add(interior);
let interiorObjects=0;
function box(name,x0,x1,y0,y1,z0,z1,mat,parent=interior){
 const g=new THREE.BoxGeometry((x1-x0)*I,(z1-z0)*I,(y1-y0)*I),m=new THREE.Mesh(g,mat);
 m.name=name;m.position.set((x0+x1)*.5*I,(z0+z1)*.5*I,-(y0+y1)*.5*I);parent.add(m);interiorObjects++;return m;
}
const floor=132,ceiling=234;
for(const [name,r] of Object.entries(S.rooms)){
 if(name==='corridor-208')continue;
 const [x0,x1,y0,y1]=r.bounds_in;
 box(name+' floor',x0,x1,y0,y1,floor-3,floor,name.startsWith('corridor')?M.floor:M.lobbyFloor);
 box(name+' ceiling',x0,x1,y0,y1,ceiling,ceiling+3,M.ceiling);
}
// Room extents and the 6-foot corridor are from A2.03. Wall faces and finishes
// are simplified for this camera flight; they are not a measured interior model.
box('lobby north wall',1120,1475,1405,1410,floor,ceiling,M.wall);
box('lobby south wall',1120,1475,1255,1260,floor,ceiling,M.wall);
box('lobby west wall north return',1115,1120,1368,1410,floor,ceiling,M.wall);
box('lobby west wall south return',1115,1120,1255,1296,floor,ceiling,M.wall);
box('lobby glazing south fixed',1475,1477,1266,1277,floor+2,ceiling-2,M.glass);
box('lobby glazing north fixed',1475,1477,1388,1399,floor+2,ceiling-2,M.glass);
const entrySouth=box('entry glass sliding south',1475,1477,1277,1332.5,floor+2,ceiling-2,M.glass);
const entryNorth=box('entry glass sliding north',1475,1477,1332.5,1388,floor+2,ceiling-2,M.glass);
function hingeDoor(leaf,name,planY){
 const hinge=new THREE.Group();hinge.name=name;
 hinge.position.set(1476*I,(floor+47)*I,-planY*I);
 leaf.position.sub(hinge.position);interior.remove(leaf);hinge.add(leaf);interior.add(hinge);
 return hinge;
}
const entrySouthHinge=hingeDoor(entrySouth,'south inward entry hinge',1277);
const entryNorthHinge=hingeDoor(entryNorth,'north inward entry hinge',1388);
for(const y of [1266,1399])box('lobby glazing jamb',1473,1479,y-2,y+2,floor,ceiling,M.dark);
box('lobby glazing head',1473,1479,1266,1399,ceiling-3,ceiling,M.dark);
box('link north wall',951,1120,1368,1373,floor,ceiling,M.wall);
box('link south wall',951,1120,1291,1296,floor,ceiling,M.wall);
box('corridor west wall south',874,879,670,1430,floor,ceiling,M.wall);
box('corridor west wall north',874,879,1474,1540,floor,ceiling,M.wall);
box('corridor east wall south',951,956,670,1296,floor,ceiling,M.wall);
box('corridor east wall north',951,956,1368,1540,floor,ceiling,M.wall);
box('corridor north end',879,951,1540,1545,floor,ceiling,M.wall);
box('corridor south end',879,951,665,670,floor,ceiling,M.wall);
for(const [name,r] of Object.entries(S.rooms)){
 if(name==='corridor-208')continue;
 const [x0,x1,y0,y1]=r.bounds_in;
 for(const yy of [y0+2,y1-2])box(name+' base trim',x0,x1,yy,yy+2,floor+1,floor+5,M.trim);
}
for(const x of [886,944])box('R1 recessed linear cove '+x,x-1,x+1,695,1510,ceiling-2,ceiling-1,M.led);
for(const x of [1170,1330])box('lobby light '+x,x-27,x+27,1305,1360,ceiling-1,ceiling,M.lamp);
for(const x of [1000,1070])box('link light '+x,x-13,x+13,1318,1346,ceiling-1,ceiling,M.lamp);
function panel(name,x,y,w,mat,base=floor,parent=interior){
 box(name+' leaf',x-1,x+1,y-w/2,y+w/2,base+4,base+88,mat,parent);
 box(name+' jamb left',x-2,x+2,y-w/2-2,y-w/2+1,base+3,base+90,M.trim,parent);
 box(name+' jamb right',x-2,x+2,y+w/2-1,y+w/2+2,base+3,base+90,M.trim,parent);
 box(name+' head',x-2,x+2,y-w/2-2,y+w/2+2,base+89,base+92,M.trim,parent);
 box(name+' handle',x+(x<915?2:-2),x+(x<915?3:-1),y+8,y+11,base+42,base+46,M.brass,parent);
}
for(const y of [750,900,1090,1215])panel('east corridor door '+y,949,y,31,M.door);
for(const y of [765,1020,1170])panel('west corridor door '+y,881,y,31,M.door);
panel('second elevator',881,1390,41,M.metal);
for(const y of [1390,1452])box('elevator indicator '+y,881,884,y-4,y+4,floor+93,floor+96,M.line);
box('lobby feature wall',1132,1134,1262,1290,floor+16,floor+88,M.trim);
box('lobby feature band',1132,1134,1275,1290,floor+80,floor+87,M.metal);

// A2.04 shows Corridor 208 on R2; the public corridor location repeats at
// this core. Door elevations and the elevator cab are presentation assumptions.
const upper=new THREE.Group();upper.name='R2 Corridor 208 / illustrative finishes';scene.add(upper);
const uFloor=255,uCeil=357;
box('Corridor 208 floor',879,951,670,1540,uFloor-3,uFloor,M.floor,upper);
box('Corridor 208 ceiling',879,951,670,1540,uCeil,uCeil+3,M.ceiling,upper);
box('R2 west wall south',874,879,670,1430,uFloor,uCeil,M.wall,upper);
box('R2 west wall north',874,879,1474,1540,uFloor,uCeil,M.wall,upper);
box('R2 east wall',951,956,670,1540,uFloor,uCeil,M.wall,upper);
box('R2 south end',879,951,665,670,uFloor,uCeil,M.wall,upper);
box('R2 north end',879,951,1540,1545,uFloor,uCeil,M.wall,upper);
for(const y of [750,900,1090,1215])panel('R2 east door '+y,949,y,31,M.door,uFloor,upper);
for(const y of [765,1020,1170])panel('R2 west door '+y,881,y,31,M.door,uFloor,upper);
for(const x of [886,944])box('R2 recessed linear cove '+x,x-1,x+1,695,1510,uCeil-2,uCeil-1,M.led,upper);
for(const x of [876,954])box('R2 base trim '+x,x-1,x+1,670,1540,uFloor+1,uFloor+5,M.trim,upper);

const car=new THREE.Group();car.name='Illustrative elevator car';scene.add(car);
box('car floor',816,879,1430,1474,-3,0,M.metal,car);
box('car ceiling',816,879,1430,1474,102,105,M.ceiling,car);
box('car rear wall',813,816,1430,1474,0,102,M.wall,car);
const cabFeature=material(0x71563a,.38,.12);cabFeature.emissive.setHex(0x7a4620);cabFeature.emissiveIntensity=.2;
box('car rear feature panel',816,817,1435,1469,23,86,cabFeature,car);
const cabStripe=new THREE.MeshBasicMaterial({color:0xffd79a});
for(const y of [1438,1466])box('car rear warm vertical sconce',818,818.5,y,y+1,25,84,cabStripe,car);
box('car rear panel top frame',816,818,1434,1470,86,89,M.metal,car);
box('car rear panel bottom frame',816,818,1434,1470,20,23,M.metal,car);
for(const y of [1434,1470])box('car rear panel side frame',816,818,y-1,y+1,20,89,M.metal,car);
box('car south wall',816,879,1427,1430,0,102,M.wall,car);
box('car north wall',816,879,1474,1477,0,102,M.wall,car);
box('car handrail south',829,867,1430,1433,32,35,M.metal,car);
box('car handrail north',829,867,1471,1474,32,35,M.metal,car);
box('car light',835,859,1441,1463,101,102,M.lamp,car);
const leftDoor=box('sliding elevator door left',877,880,1430,1452,1,91,M.metal,car);
const rightDoor=box('sliding elevator door right',877,880,1452,1474,1,91,M.metal,car);
const elevatorDoorMaterial=M.metal.clone();elevatorDoorMaterial.transparent=true;
leftDoor.material=elevatorDoorMaterial;rightDoor.material=elevatorDoorMaterial;
const leftHome=leftDoor.position.z,rightHome=rightDoor.position.z;

// Browser-native architectural lights: emissive panels plus nearby rectangular
// luminaires. Their direct illumination works in the phone viewer and video.
const lightRig=new THREE.Group();scene.add(lightRig);
function areaAt(name,x,y,z,width,depth,intensity=12,parent=lightRig){
 const light=new THREE.RectAreaLight(0xffc994,intensity,width,depth);
 light.name=name;light.position.set(x*I,z*I,-y*I);light.rotation.x=Math.PI/2;parent.add(light);
}
for(const y of [850,1060,1270,1480])areaAt('R1 warm corridor downlight',915,y,ceiling-4,.75,.65);
for(const y of [850,1060,1270,1480])areaAt('R2 warm corridor downlight',915,y,uCeil-4,.75,.65);
for(const x of [1170,1330])areaAt('Lobby 110 downlight',x,1332,ceiling-4,1.1,.9,14);
areaAt('Elevator cab downlight',847,1452,99,.65,.55,10,car);
const carFill=new THREE.PointLight(0xffdfb7,22,5);carFill.position.set(847*I,72*I,-1452*I);car.add(carFill);

// Gold floor guidance is a presentation path, sampled from the same camera
// trajectory. It stops at the elevator and resumes on R2.
const gold=new THREE.MeshBasicMaterial({color:0xffe1a0,transparent:true,opacity:.95,depthWrite:false});
const goldHalo=new THREE.MeshBasicMaterial({color:0xf2af44,transparent:true,opacity:.2,depthWrite:false});
function ribbon(name,start,end,z){
 const points=[];for(let t=start;t<=end+.001;t+=.1){const p=path(t);p.y=z*I+.035;points.push(p)}
 const segments=240,curve=new THREE.CatmullRomCurve3(points);
 const geometry=new THREE.TubeGeometry(curve,segments,.012,5,false);
 const mesh=new THREE.Mesh(geometry,gold);mesh.name=name;scene.add(mesh);
 const halo=new THREE.Mesh(new THREE.TubeGeometry(curve,segments,.055,5,false),goldHalo);
 halo.name=name+' soft glow';scene.add(halo);
 return {mesh,halo,segments,start,end};
}
function floorLabel(textLabel,x,y,z,width=1.8){
 const canvas=document.createElement('canvas');canvas.width=512;canvas.height=128;
 const ctx=canvas.getContext('2d');ctx.clearRect(0,0,512,128);
 ctx.strokeStyle='rgba(248,205,130,.8)';ctx.lineWidth=2;ctx.strokeRect(8,12,496,104);
 ctx.fillStyle='#ffe4b6';ctx.font='600 42px Arial';ctx.textAlign='center';ctx.textBaseline='middle';
 ctx.fillText(textLabel,256,65);
 const tex=new THREE.CanvasTexture(canvas);tex.colorSpace=THREE.SRGBColorSpace;
 const mark=new THREE.Mesh(new THREE.PlaneGeometry(width,width/4),new THREE.MeshBasicMaterial({map:tex,transparent:true,side:THREE.DoubleSide,depthWrite:false}));
 mark.name='in-scene wayfinding '+textLabel;mark.rotation.x=-Math.PI/2;
 mark.position.set(x*I,z*I+.08,-y*I);scene.add(mark);
}
floorLabel('LOBBY 110',1300,1332,floor,2.1);
floorLabel('CORRIDOR 108',915,1375,floor,1.6);
floorLabel('CORRIDOR 208',915,1335,uFloor,1.6);
const brass=new THREE.LineBasicMaterial({color:0xe6bf79,transparent:true,opacity:0,depthWrite:false});
for(const level of [132,163,194,225,255,286,317,357]){
 const geometry=new THREE.EdgesGeometry(new THREE.BoxGeometry(65*I,.006,50*I));
 const ring=new THREE.LineSegments(geometry,brass);ring.name='shaft brass section ring';
 ring.position.set(847*I,level*I,-1452*I);scene.add(ring);
}
const shaftEdges=new THREE.LineSegments(new THREE.EdgesGeometry(new THREE.BoxGeometry(65*I,225*I,50*I)),brass);
shaftEdges.name='shaft structural edges';shaftEdges.position.set(847*I,(132+225/2)*I,-1452*I);scene.add(shaftEdges);
const glassShaftMat=new THREE.MeshPhysicalMaterial({color:0x8cb7bd,transparent:true,opacity:.12,roughness:.16,metalness:.15,side:THREE.DoubleSide,depthWrite:false});
const glassShaft=new THREE.Mesh(new THREE.BoxGeometry(65*I,225*I,50*I),glassShaftMat);
glassShaft.name='frosted elevator shaft cutaway';glassShaft.position.copy(shaftEdges.position);scene.add(glassShaft);
const cutawayLevels=[];
for(const [label,level] of [['R1',132],['R2',255]]){
 const slab=new THREE.Mesh(new THREE.BoxGeometry(290*I,.028,280*I),new THREE.MeshBasicMaterial({color:0x90b5b9,transparent:true,opacity:.2,side:THREE.DoubleSide,depthWrite:false}));
 slab.name=label+' transparent level plane';slab.position.set(847*I,level*I,-1452*I);scene.add(slab);cutawayLevels.push(slab);
 const edge=new THREE.LineSegments(new THREE.EdgesGeometry(slab.geometry),brass);slab.add(edge);
}
const sectionPlane=new THREE.Plane(new THREE.Vector3(-1,0,0),1100*I);
const sectionMats=[M.wall,M.floor,M.lobbyFloor,M.ceiling,M.trim,M.door,M.metal,M.dark,M.glass,M.brass,M.led,...cutawayLevels.map(o=>o.material)];
const sectionEdgeMat=new THREE.LineBasicMaterial({color:0xffcd75,transparent:true,opacity:0,depthWrite:false});
const sectionEdge=new THREE.LineSegments(new THREE.EdgesGeometry(new THREE.BoxGeometry(.01,225*I,280*I)),sectionEdgeMat);
sectionEdge.name='moving glowing section edge';scene.add(sectionEdge);
sectionEdge.position.set(1100*I,244.5*I,-1452*I);
const xrayObjects=[];
for(const group of [interior,upper,car])group.traverse(o=>{
 if(o.isMesh&&(/wall|ceiling/i.test(o.name))){
  const wire=new THREE.LineSegments(new THREE.EdgesGeometry(o.geometry),brass);wire.name='brass x-ray edges';o.add(wire);xrayObjects.push(wire);
 }
});

function xyz(ft){return new THREE.Vector3(ft[0]*12*I,ft[2]*12*I,-ft[1]*12*I)}
const curves=S.camera_bezier_segments.map(s=>({t0:s.t0,t1:s.t1,curve:new THREE.CubicBezierCurve3(xyz(s.p0),xyz(s.p1),xyz(s.p2),xyz(s.p3))}));
function path(t){
 t=THREE.MathUtils.clamp(t,0,26);
 const segment=curves.find(c=>t<=c.t1)||curves.at(-1);
 return segment.curve.getPoint(THREE.MathUtils.clamp((t-segment.t0)/(segment.t1-segment.t0),0,1));
}
const ribbons=[ribbon('R1 animated gold floor route',6.55,13.35,floor),ribbon('R2 animated gold floor route',19.6,25.9,uFloor)];
let exterior,elapsed=0,playing=false,last=0;
const foliage=[];
const player=document.getElementById('play'),scrub=document.getElementById('scrub'),cue=document.getElementById('cue'),time=document.getElementById('time');
const veil=document.getElementById('veil'),liftBadge=document.getElementById('lift-badge'),liftCard=document.getElementById('lift-card');
const mapRooms=document.getElementById('plan-rooms'),mapDot=document.getElementById('map-dot'),radar=document.getElementById('radar-wedge'),mapLevel=document.getElementById('map-level');
const svgNS='http://www.w3.org/2000/svg';let shownLevel='';
function mapX(x,level){return level==='R1'?8+(x-850)*.23:72+(x-879)*.55}
function mapY(y){return 12+(1560-y)*.19}
function drawMiniMap(level){
 if(shownLevel===level)return;shownLevel=level;mapRooms.replaceChildren();mapLevel.textContent=level;
 const names=level==='R1'?['lobby-110','lobby-link','corridor-108']:['corridor-208'];
 for(const name of names){
  const r=S.rooms[name],b=r.bounds_in,rect=document.createElementNS(svgNS,'rect');
  rect.setAttribute('x',mapX(b[0],level));rect.setAttribute('y',mapY(b[3]));
  rect.setAttribute('width',(b[1]-b[0])*(level==='R1'?.23:.55));rect.setAttribute('height',(b[3]-b[2])*.19);
  rect.setAttribute('fill',name.startsWith('corridor')?'#b8bca055':'#86aab244');
  rect.setAttribute('stroke','#d8c098');rect.setAttribute('stroke-width','1.5');mapRooms.append(rect);
  if(!name.includes('link')){const label=document.createElementNS(svgNS,'text');
   label.setAttribute('x',mapX((b[0]+b[1])/2,level));label.setAttribute('y',mapY((b[2]+b[3])/2));
   label.setAttribute('fill','#f5dfb0');label.setAttribute('font-size','10');label.setAttribute('text-anchor','middle');
   label.textContent=name.split('-')[1];mapRooms.append(label)}
 }
}
function updateMiniMap(look,cutaway){
 const level=elapsed>=17.3?'R2':'R1';drawMiniMap(level);
 const here=cutaway?new THREE.Vector3(847*I,car.position.y,-1452*I):camera.position;
 const x=THREE.MathUtils.clamp(mapX(here.x/I,level),6,154),y=THREE.MathUtils.clamp(mapY(-here.z/I),6,204);
 mapDot.setAttribute('cx',x);mapDot.setAttribute('cy',y);
 const direction=cutaway?new THREE.Vector2(0,-1):new THREE.Vector2(look.x-camera.position.x,look.z-camera.position.z).normalize();
 const dx=direction.x,dy=direction.y,length=27,width=11;
 radar.setAttribute('d',`M ${x} ${y} L ${x+dx*length-dy*width} ${y+dy*length+dx*width} L ${x+dx*length+dy*width} ${y+dy*length-dx*width} Z`);
}
const trackTarget=new THREE.Object3D();trackTarget.name='camera look target';scene.add(trackTarget);
function resize(){const w=stage.clientWidth,h=stage.clientHeight;renderer.setSize(w,h);camera.aspect=w/h;camera.updateProjectionMatrix();renderer.render(scene,camera)}
new ResizeObserver(resize).observe(stage);
function title(t){return t<4.7?'Approach the east frontage':t<6.6?'Through the lobby glazing':t<9.2?'Lobby 110':t<13.2?'Corridor 108 · elevator core':t<15.2?'Entering Elevator M1':t<18.6?'Up one floor':t<20?'R2 elevator lobby':'Corridor 208 · toward the stair'}
const smooth=(a,b,t)=>{const v=THREE.MathUtils.clamp((t-a)/(b-a),0,1);return v*v*(3-2*v)};
function frame(t){
 elapsed=THREE.MathUtils.clamp(t,0,26);camera.position.copy(path(elapsed));
 const look=path(Math.min(26,elapsed+1.5));if(look.distanceTo(camera.position)<.02){
  const prior=path(Math.max(0,elapsed-.3));look.copy(camera.position).add(camera.position.clone().sub(prior).normalize());
 }
 if(elapsed<3.5)look.lerp(xyz([122.9,111,16.5]),.35*(1-elapsed/3.5));
 if(elapsed>=14.8&&elapsed<=19.4)look.lerp(camera.position.clone().add(new THREE.Vector3(1,0,0)),Math.min(smooth(14.8,15.2,elapsed),1-smooth(18.8,19.4,elapsed)));
 const pull=smooth(15.1,16.1,elapsed)*(1-smooth(18.1,19.15,elapsed));
 const section=smooth(15,16,elapsed)*(1-smooth(18.2,19.15,elapsed));
 const cutaway=section>.5;
 camera.position.lerp(new THREE.Vector3(1050*I,240*I,-1335*I),pull);
 look.lerp(new THREE.Vector3(847*I,244*I,-1452*I),pull);
 const cutX=1100-200*smooth(15,16,elapsed)+200*smooth(18.2,19.15,elapsed);
 sectionPlane.constant=cutX*I;
 const clipActive=section>.005;
 for(const mat of sectionMats)mat.clippingPlanes=clipActive?[sectionPlane]:null;
 interior.visible=true;upper.visible=true;
 glassShaft.visible=clipActive;shaftEdges.visible=clipActive;
 for(const level of cutawayLevels)level.visible=clipActive;
 sectionEdge.visible=clipActive;sectionEdge.position.x=cutX*I;sectionEdgeMat.opacity=.85*section;
 car.position.y=(floor+123*smooth(16,17.8,elapsed))*I;
 const portal=new THREE.Vector3(1475*I,(floor+65)*I,-1332.5*I);
 const proximity=1-smooth(2,5,camera.position.distanceTo(portal));
 const entryOpen=Math.max(proximity,smooth(4,5.25,elapsed)*(1-smooth(7.1,8.1,elapsed)));
 entrySouthHinge.rotation.y=1.32*entryOpen;
 entryNorthHinge.rotation.y=-1.32*entryOpen;
 const open=elapsed<12.15?0:elapsed<13.2?smooth(12.15,13.2,elapsed):elapsed<15.4?1:elapsed<16?1-smooth(15.4,16,elapsed):elapsed<17.8?0:elapsed<18.45?smooth(17.8,18.45,elapsed):elapsed<19.7?1:elapsed<20.3?1-smooth(19.7,20.3,elapsed):0;
 leftDoor.position.z=leftHome+22*I*open;rightDoor.position.z=rightHome-22*I*open;
 const xray=section;
 M.wall.opacity=1-.78*xray;M.wall.roughness=.72-.52*xray;M.wall.metalness=.18*xray;
 M.ceiling.transparent=true;M.ceiling.depthWrite=false;M.ceiling.opacity=1-.55*xray;
 M.floor.transparent=true;M.floor.depthWrite=xray<.05;M.floor.opacity=1-.75*xray;
 M.door.transparent=true;M.door.depthWrite=xray<.05;M.door.opacity=1-.7*xray;
 M.trim.transparent=true;M.trim.depthWrite=xray<.05;M.trim.opacity=1-.65*xray;
 elevatorDoorMaterial.opacity=1-.94*xray;elevatorDoorMaterial.depthWrite=xray<.05;
 brass.opacity=.82*xray;
 for(const r of ribbons){
  const progress=THREE.MathUtils.clamp((elapsed+1.5-r.start)/(r.end-r.start),0,1);
  r.mesh.geometry.setDrawRange(0,Math.round(progress*r.segments)*5*6);
  r.halo.geometry.setDrawRange(0,Math.round(progress*r.segments)*5*6);
 }
 goldHalo.opacity=.12+.12*(.5+.5*Math.sin(elapsed*5));
 for(let i=0;i<foliage.length;i++)foliage[i].rotation.z=Math.sin(elapsed*.85+i*.41)*.013;
 trackTarget.position.copy(look);camera.lookAt(trackTarget.position);
 if(!cutaway){const before=path(Math.max(0,elapsed-.28)),after=path(Math.min(26,elapsed+.28));
  const prev=path(Math.max(0,elapsed-.65));
  const turn=(camera.position.x-before.x)*(after.z-camera.position.z)-(camera.position.z-before.z)*(after.x-camera.position.x);
  const bank=THREE.MathUtils.clamp(turn*1.2,-.035,.035);
  if(camera.position.distanceTo(prev)>.02)camera.rotateZ(bank);
 }
 if(exterior)exterior.visible=elapsed<6.08;city.visible=elapsed<6.08;
 // The exterior drawing model has no surveyed lobby behind its storefront.
 // A short dark crossing covers the switch to the plan-based interior study.
 veil.style.opacity=elapsed<5.35||elapsed>6.65?'0':elapsed<6.03?String((elapsed-5.35)/.68):String((6.65-elapsed)/.62);
 liftBadge.hidden=elapsed<13.55||elapsed>19.5;
 liftBadge.querySelector('strong').textContent=elapsed<16?'R1':elapsed<17.8?'R1  ↑  R2':'R2';
 liftCard.hidden=elapsed<15.2||elapsed>18.7;
 liftCard.style.opacity=String(Math.min(smooth(15.2,15.6,elapsed),1-smooth(18.3,18.7,elapsed)));
 liftCard.querySelector('#rise').style.height=`${Math.max(4,100*smooth(16,17.8,elapsed))}%`;
 scrub.value=elapsed.toFixed(2);cue.textContent=title(elapsed);time.textContent=`${elapsed.toFixed(1)} / 26 s`;
 updateMiniMap(look,cutaway);
 renderer.render(scene,camera);
 return {t:elapsed,xyz_ft:[camera.position.x/I/12,-camera.position.z/I/12,camera.position.y/I/12].map(x=>+x.toFixed(2)),car_elevation_ft:+(car.position.y/I/12).toFixed(2),cutaway,section_x_ft:+(cutX/12).toFixed(2),cue:cue.textContent,exterior_visible:!!exterior?.visible,entry_open:+entryOpen.toFixed(2),elevator_open:+open.toFixed(2),xray:+xray.toFixed(2)};
}
function animate(now){if(playing){elapsed=Math.min(26,elapsed+(now-last)/1000);frame(elapsed);if(elapsed===26){playing=false;player.textContent='Replay';}}last=now;requestAnimationFrame(animate)}requestAnimationFrame(animate);
player.onclick=()=>{if(elapsed>=26)frame(0);playing=!playing;player.textContent=playing?'Pause':'Play';last=performance.now()};
scrub.oninput=()=>{playing=false;player.textContent='Play';frame(+scrub.value)};
window.drone={frame,stats:()=>({interior_objects:interiorObjects,exterior_meshes:(()=>{let n=0;exterior?.traverse(o=>{if(o.isMesh)n++});return n})(),osm_buildings:S.osm_context.buildings.length,area_lights:lightRig.children.filter(o=>o.isRectAreaLight).length,ribbons:ribbons.length,foliage:foliage.length,entry:S.exterior_entry_id,rooms:Object.keys(S.rooms)})};
const bytes=Uint8Array.from(atob(window.EXTERIOR_BASE64),c=>c.charCodeAt(0));
new GLTFLoader().parse(bytes.buffer,'',g=>{
 exterior=g.scene;exterior.name='200 W. Highland exterior drawing model';scene.add(exterior);
 const crownsByTree=new Map();
 exterior.traverse(o=>{if(o.isMesh&&o.material){
  if(o.name==='east-R1-08-glazing')o.visible=false;
  if(o.name==='east-R1-08-frames')o.visible=false;
  if(/tree-\d+-branch-/.test(o.name))foliage.push(o);
  const crown=/^tree-(\d+)-crown-/.exec(o.name);
  if(crown){const group=crownsByTree.get(crown[1])||[];group.push(o);crownsByTree.set(crown[1],group)}
  if(/east-R[2-5]-(?:01|04|06|09)-glazing/.test(o.name)){
   o.material=o.material.clone();o.material.color.setHex(0xffd7a0);
   o.material.emissive=new THREE.Color(0xffad5b);o.material.emissiveIntensity=.62;
   o.material.transparent=true;o.material.opacity=.6;
  }
  const ms=Array.isArray(o.material)?o.material:[o.material];for(const m of ms){
  if(/^brick-/i.test(m.name)){m.color.setRGB(.25,.075,.038);m.roughness=.84;}
  if(/^road$/i.test(m.name)){m.color.setHex(0x363d45);m.roughness=.36;m.metalness=.12;m.roughnessMap=pavementMap;}
  if(/glass/i.test(m.name)&&!o.material.emissive?.getHex()){m.transparent=true;m.opacity=.27;m.depthWrite=false;m.side=THREE.DoubleSide;}
 }}});
 const leafShape=new THREE.IcosahedronGeometry(1,1),leafMaterial=new THREE.MeshStandardMaterial({color:0xffffff,roughness:.92});
 for(const [treeId,crowns] of crownsByTree){
  const trunk=exterior.getObjectByName(`tree-trunk-${treeId}`),trunkBounds=new THREE.Box3().setFromObject(trunk);
  const pivot=trunkBounds.getCenter(new THREE.Vector3());pivot.y=trunkBounds.min.y;
  const leaves=new THREE.Group();leaves.name=`procedural tree canopy ${treeId}`;leaves.position.copy(pivot);exterior.add(leaves);foliage.push(leaves);
  const count=crowns.length*14,instances=new THREE.InstancedMesh(leafShape,leafMaterial,count);
  const dummy=new THREE.Object3D();let index=0;
  for(const crown of crowns){
   const bounds=new THREE.Box3().setFromObject(crown),mid=bounds.getCenter(new THREE.Vector3()),size=bounds.getSize(new THREE.Vector3());
   crown.visible=false;
   for(let k=0;k<14;k++){
    const seed=Number(treeId)*997+index*31;
    const a=seed*2.39996,r=Math.sqrt((k+.5)/14),spread=.34+.35*r;
    dummy.position.set(mid.x+Math.cos(a)*size.x*spread,mid.y+Math.sin(seed*.7)*size.y*.27,mid.z+Math.sin(a)*size.z*spread);
    dummy.position.sub(pivot);
    const scale=.22+((seed*17)%13)/45;
    dummy.scale.set(scale,scale*.75,scale);dummy.rotation.set(seed*.03,seed*.11,seed*.07);dummy.updateMatrix();
    instances.setMatrixAt(index,dummy.matrix);
    instances.setColorAt(index,new THREE.Color().setHSL(.28+((seed%11)/150),.27,.23+((seed%7)/80)));
    index++;
   }
  }
  instances.instanceMatrix.needsUpdate=true;instances.name=`leaf clusters ${treeId}`;leaves.add(instances);
 }
 const canopy=exterior.getObjectByName('east-entry-canopy');
 if(canopy){const bounds=new THREE.Box3().setFromObject(canopy),mid=bounds.getCenter(new THREE.Vector3());
  for(const offset of [-.65,.65]){const lamp=new THREE.RectAreaLight(0xffc994,24,.65,.45);
   lamp.name='warm canopy downlight';lamp.position.set(mid.x, bounds.min.y-.08, mid.z+offset);lamp.rotation.x=Math.PI/2;lightRig.add(lamp)}
 }
 frame(0);document.getElementById('loading').hidden=true;window.ready=true;
},e=>{document.getElementById('loading').textContent='Model load failed';throw e});
