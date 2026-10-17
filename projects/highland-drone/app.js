import * as THREE from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';

const S=window.FLIGHT_SPEC, I=.0254, stage=document.getElementById('stage');
const scene=new THREE.Scene();scene.background=new THREE.Color(0x8398a6);scene.fog=new THREE.Fog(0x8398a6,140,400);
const camera=new THREE.PerspectiveCamera(67,1,.025,400);
const renderer=new THREE.WebGLRenderer({antialias:true,powerPreference:'high-performance',preserveDrawingBuffer:true});
renderer.setPixelRatio(Math.min(devicePixelRatio,1.5));renderer.outputColorSpace=THREE.SRGBColorSpace;
renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1.05;
stage.prepend(renderer.domElement);
scene.add(new THREE.HemisphereLight(0xffffff,0x75654f,1.8));
const sun=new THREE.DirectionalLight(0xffe6c8,1.2);sun.position.set(-40,100,75);scene.add(sun);

const material=(color,roughness=1,metalness=0)=>new THREE.MeshStandardMaterial({color,roughness,metalness,side:THREE.DoubleSide});
const M={wall:material(0xc8c1af),floor:material(0x4e5553),ceiling:material(0xe3ddcd),trim:material(0x554c43),door:material(0x74604f),metal:material(0x999c92,.34,.55),dark:material(0x29333b),glass:new THREE.MeshPhysicalMaterial({color:0xb5c7c9,transparent:true,opacity:.18,side:THREE.DoubleSide,roughness:.2,metalness:.1}),lamp:new THREE.MeshBasicMaterial({color:0xffefbf}),line:new THREE.MeshBasicMaterial({color:0x567f89})};
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
 box(name+' floor',x0,x1,y0,y1,floor-3,floor,M.floor);
 box(name+' ceiling',x0,x1,y0,y1,ceiling,ceiling+3,M.ceiling);
}
// Room extents and the 6-foot corridor are from A2.03. Wall faces and finishes
// are simplified for this camera flight; they are not a measured interior model.
box('lobby north wall',1120,1475,1405,1410,floor,ceiling,M.wall);
box('lobby south wall',1120,1475,1255,1260,floor,ceiling,M.wall);
box('lobby west wall north return',1115,1120,1368,1410,floor,ceiling,M.wall);
box('lobby west wall south return',1115,1120,1255,1296,floor,ceiling,M.wall);
box('lobby glazed east frontage',1475,1477,1266,1399,floor+2,ceiling-2,M.glass);
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
for(let y=730;y<=1490;y+=105){
 box('corridor light '+y,899,931,y-19,y+19,ceiling-2,ceiling-1,M.lamp);
}
for(const x of [1170,1330])box('lobby light '+x,x-27,x+27,1305,1360,ceiling-1,ceiling,M.lamp);
for(const x of [1000,1070])box('link light '+x,x-13,x+13,1318,1346,ceiling-1,ceiling,M.lamp);
function panel(name,x,y,w,mat,base=floor,parent=interior){
 box(name+' leaf',x-1,x+1,y-w/2,y+w/2,base+4,base+88,mat,parent);
 box(name+' jamb left',x-2,x+2,y-w/2-2,y-w/2+1,base+3,base+90,M.trim,parent);
 box(name+' jamb right',x-2,x+2,y+w/2-1,y+w/2+2,base+3,base+90,M.trim,parent);
 box(name+' head',x-2,x+2,y-w/2-2,y+w/2+2,base+89,base+92,M.trim,parent);
 box(name+' handle',x+(x<915?2:-2),x+(x<915?3:-1),y+8,y+11,base+42,base+46,M.metal,parent);
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
for(let y=730;y<=1490;y+=105)box('R2 corridor light '+y,899,931,y-19,y+19,uCeil-2,uCeil-1,M.lamp,upper);
for(const x of [876,954])box('R2 base trim '+x,x-1,x+1,670,1540,uFloor+1,uFloor+5,M.trim,upper);

const car=new THREE.Group();car.name='Illustrative elevator car';scene.add(car);
box('car floor',816,879,1430,1474,-3,0,M.metal,car);
box('car ceiling',816,879,1430,1474,102,105,M.ceiling,car);
box('car rear wall',813,816,1430,1474,0,102,M.wall,car);
box('car rear feature panel',816,817,1435,1469,23,86,M.dark,car);
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
const leftHome=leftDoor.position.z,rightHome=rightDoor.position.z;

function xyz(ft){return new THREE.Vector3(ft[0]*12*I,ft[2]*12*I,-ft[1]*12*I)}
const keys=S.waypoints;
function path(t){
 t=THREE.MathUtils.clamp(t,0,26);
 let j=keys.findIndex((k,i)=>i<keys.length-1&&t<=keys[i+1].t);if(j<0)j=keys.length-2;
 const a=keys[j],b=keys[j+1],u=(t-a.t)/(b.t-a.t),p0=xyz(keys[Math.max(0,j-1)].xyz_ft),p1=xyz(a.xyz_ft),p2=xyz(b.xyz_ft),p3=xyz(keys[Math.min(keys.length-1,j+2)].xyz_ft);
 // Centripetal-style easing keeps the drone from overshooting narrow hall walls.
 const q=u*u*(3-2*u);return p1.lerp(p2,q).add(p0.sub(p1.clone()).multiplyScalar((q-q*q)*.02)).add(p3.sub(p2.clone()).multiplyScalar((q-q*q)*.02));
}
let exterior,elapsed=0,playing=false,last=0;
const player=document.getElementById('play'),scrub=document.getElementById('scrub'),cue=document.getElementById('cue'),time=document.getElementById('time');
const veil=document.getElementById('veil'),liftBadge=document.getElementById('lift-badge'),liftCard=document.getElementById('lift-card');
function resize(){const w=stage.clientWidth,h=stage.clientHeight;renderer.setSize(w,h);camera.aspect=w/h;camera.updateProjectionMatrix();renderer.render(scene,camera)}
new ResizeObserver(resize).observe(stage);
function title(t){return t<4.7?'Approach the east frontage':t<6.6?'Through the lobby glazing':t<9.2?'Lobby 110':t<13.2?'Corridor 108 · elevator core':t<15.2?'Entering Elevator M1':t<18.6?'Up one floor':t<20?'R2 elevator lobby':'Corridor 208 · toward the stair'}
const smooth=(a,b,t)=>{const v=THREE.MathUtils.clamp((t-a)/(b-a),0,1);return v*v*(3-2*v)};
function frame(t){
 elapsed=THREE.MathUtils.clamp(t,0,26);camera.position.copy(path(elapsed));
 const look=path(Math.min(26,elapsed+.56));if(look.distanceTo(camera.position)<.02){
  const prior=path(Math.max(0,elapsed-.3));look.copy(camera.position).add(camera.position.clone().sub(prior).normalize());
 }
 if(elapsed<3.5)look.lerp(xyz([122.9,111,16.5]),.35*(1-elapsed/3.5));
 if(elapsed>=15.2&&elapsed<=19.4)look.lerp(camera.position.clone().add(new THREE.Vector3(1,0,0)),Math.min(smooth(15.2,16,elapsed),1-smooth(18.8,19.4,elapsed)));
 car.position.y=(floor+123*smooth(16,17.8,elapsed))*I;
 const open=elapsed<13.6?0:elapsed<14.3?smooth(13.6,14.3,elapsed):elapsed<15.3?1:elapsed<16?1-smooth(15.3,16,elapsed):elapsed<17.8?0:elapsed<18.5?smooth(17.8,18.5,elapsed):elapsed<19.7?1:elapsed<20.3?1-smooth(19.7,20.3,elapsed):0;
 leftDoor.position.z=leftHome+22*I*open;rightDoor.position.z=rightHome-22*I*open;
 camera.lookAt(look);if(exterior)exterior.visible=elapsed<6.08;
 // The exterior drawing model has no surveyed lobby behind its storefront.
 // A short dark crossing covers the switch to the plan-based interior study.
 veil.style.opacity=elapsed<5.35||elapsed>6.65?'0':elapsed<6.03?String((elapsed-5.35)/.68):String((6.65-elapsed)/.62);
 liftBadge.hidden=elapsed<13.55||elapsed>19.5;
 liftBadge.querySelector('strong').textContent=elapsed<16?'R1':elapsed<17.8?'R1  ↑  R2':'R2';
 liftCard.hidden=elapsed<15.2||elapsed>18.7;
 liftCard.style.opacity=String(Math.min(smooth(15.2,15.6,elapsed),1-smooth(18.3,18.7,elapsed)));
 liftCard.querySelector('#rise').style.height=`${Math.max(4,100*smooth(16,17.8,elapsed))}%`;
 scrub.value=elapsed.toFixed(2);cue.textContent=title(elapsed);time.textContent=`${elapsed.toFixed(1)} / 26 s`;
 renderer.render(scene,camera);
 return {t:elapsed,xyz_ft:[camera.position.x/I/12,-camera.position.z/I/12,camera.position.y/I/12].map(x=>+x.toFixed(2)),cue:cue.textContent,exterior_visible:!!exterior?.visible};
}
function animate(now){if(playing){elapsed=Math.min(26,elapsed+(now-last)/1000);frame(elapsed);if(elapsed===26){playing=false;player.textContent='Replay';}}last=now;requestAnimationFrame(animate)}requestAnimationFrame(animate);
player.onclick=()=>{if(elapsed>=26)frame(0);playing=!playing;player.textContent=playing?'Pause':'Play';last=performance.now()};
scrub.oninput=()=>{playing=false;player.textContent='Play';frame(+scrub.value)};
window.drone={frame,stats:()=>({interior_objects:interiorObjects,exterior_meshes:(()=>{let n=0;exterior?.traverse(o=>{if(o.isMesh)n++});return n})(),entry:S.exterior_entry_id,rooms:Object.keys(S.rooms)})};
const bytes=Uint8Array.from(atob(window.EXTERIOR_BASE64),c=>c.charCodeAt(0));
new GLTFLoader().parse(bytes.buffer,'',g=>{
 exterior=g.scene;exterior.name='200 W. Highland exterior drawing model';scene.add(exterior);
 exterior.traverse(o=>{if(o.isMesh&&o.material){const ms=Array.isArray(o.material)?o.material:[o.material];for(const m of ms){
  if(/^brick-/i.test(m.name)){m.color.setRGB(.25,.075,.038);m.roughness=.84;}
  if(/glass/i.test(m.name)){m.transparent=true;m.opacity=.27;m.depthWrite=false;m.side=THREE.DoubleSide;}
 }}});
 frame(0);document.getElementById('loading').hidden=true;window.ready=true;
},e=>{document.getElementById('loading').textContent='Model load failed';throw e});
