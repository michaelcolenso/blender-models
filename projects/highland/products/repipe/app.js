import * as THREE from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
const S=window.REPIPE_SPEC,$=id=>document.getElementById(id);
const scene=new THREE.Scene();scene.background=new THREE.Color('#0b1822');
const camera=new THREE.PerspectiveCamera(37,1280/720,.03,200);
const renderer=new THREE.WebGLRenderer({antialias:true,preserveDrawingBuffer:true});renderer.setSize(1280,720);renderer.setPixelRatio(1);renderer.outputColorSpace=THREE.SRGBColorSpace;renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1.1;$('canvas').append(renderer.domElement);
scene.add(new THREE.HemisphereLight(0xcdeeff,0x3d4650,1.5));
for(const [x,y,z,p] of [[10,20,15,2],[-10,8,-8,1.5],[0,2,12,1]]){const light=new THREE.DirectionalLight(0xffffff,p);light.position.set(x,y,z);scene.add(light);}
const colors={CW:0x379eff,HW:0xff694a,HWC:0x41dda2};
const refGroup=new THREE.Group();refGroup.name='Drawing reference — installed conditions unverified';scene.add(refGroup);
const proposed=new THREE.Group();proposed.name='Proposed sequence — routes are schematic';scene.add(proposed);
const oldMaterial=new THREE.MeshStandardMaterial({color:0x80909a,roughness:.6,transparent:true,opacity:.48,depthWrite:false});
const offset=new THREE.Vector3().fromArray(S.display_offset_m);
const cv=p=>new THREE.Vector3(p[0]*.0254,p[2]*.0254,-p[1]*.0254);
const ease=t=>t*t*(3-2*t),clamp=t=>Math.min(1,Math.max(0,t));
const routes=[],ties=[],oldPilot=[];let reference;
function tube(points,r,color,parent){const curve=new THREE.CurvePath();for(let i=1;i<points.length;i++)if(points[i].distanceTo(points[i-1])>1e-7)curve.add(new THREE.LineCurve3(points[i-1],points[i]));const n=Math.max(24,points.length*4),geom=new THREE.TubeGeometry(curve,n,r,8,false);const mat=new THREE.MeshStandardMaterial({color,metalness:.2,roughness:.35,emissive:color,emissiveIntensity:.16});const mesh=new THREE.Mesh(geom,mat);parent.add(mesh);return {mesh,curve,n,full:geom.index.count};}
for(const e of S.elements){const points=e.points.map(p=>cv(p).add(offset));const t=tube(points,Math.max(.010,e.nominal_in*.0254*.75),colors[e.system],proposed);routes.push({...t,e});}
for(const p of S.pilot_ports){const end=cv(p.port),start=end.clone().add(offset);const tie=tube([start,end],.012,colors[p.system],proposed);const marker=new THREE.Mesh(new THREE.SphereGeometry(.055,12,8),new THREE.MeshStandardMaterial({color:0xffcc72,emissive:0xffb441,emissiveIntensity:.45}));marker.position.copy(start);proposed.add(marker);ties.push({...tie,p,marker});}
const feedTies=[];for(const [system,port] of Object.entries(S.unit_roots)){feedTies.push(tube([cv(port),cv(port).add(offset)],.025,colors[system],proposed));}
const zone=new THREE.Mesh(new THREE.BoxGeometry(...S.work_zone.size),new THREE.MeshStandardMaterial({color:0xc4aa58,transparent:true,opacity:.24,depthWrite:false}));zone.position.fromArray(S.work_zone.center);scene.add(zone);
const zoneEdge=new THREE.LineSegments(new THREE.EdgesGeometry(zone.geometry),new THREE.LineBasicMaterial({color:0xdab866,transparent:true,opacity:.85}));zoneEdge.position.copy(zone.position);scene.add(zoneEdge);
const pulses=[];for(const r of routes.filter(r=>r.e.group==='mains')){const dot=new THREE.Mesh(new THREE.SphereGeometry(.038,8,6),new THREE.MeshBasicMaterial({color:colors[r.e.system]}));proposed.add(dot);pulses.push({dot,r});}
const cameras={bath:{target:[-7,1,-5.5],position:[.5,8.5,3.3]},unit:{target:[0,1,2.18],position:[16,21,25]},close:{target:[-7.3,.85,-4.4],position:[-2,3.2,0]}};
const duration=S.phases.reduce((n,p)=>n+p.seconds,0);let playback=false,start=0,currentTime=0;
function setRange(r,p){r.mesh.visible=p>0;r.mesh.geometry.setDrawRange(0,Math.floor(clamp(p)*r.n)*8*6);}
function frame(seconds){
 currentTime=clamp(seconds/duration)*duration;let phaseIndex=0,local=currentTime;
 while(phaseIndex<S.phases.length-1&&local>=S.phases[phaseIndex].seconds){local-=S.phases[phaseIndex].seconds;phaseIndex++;}
 const phase=S.phases[phaseIndex],t=clamp(local/phase.seconds),c=cameras[phase.view];
 const target=new THREE.Vector3().fromArray(c.target),pos=new THREE.Vector3().fromArray(c.position).sub(target).multiplyScalar(Math.max(1,1.15/camera.aspect));pos.applyAxisAngle(new THREE.Vector3(0,1,0),-.12+.24*ease(t));camera.position.copy(target).add(pos);camera.lookAt(target);
 $('title').textContent=phase.title;$('action').textContent=phase.action;$('service').textContent=phase.service;$('gate').textContent=phase.gate;
 $('repeat').style.display=phaseIndex===6?'block':'none';$('unit-now').style.color='#75e6ad';$('unit-next').style.color=phaseIndex===6&&t>.45?'#ffcc72':'#758894';
 $('time').textContent=Math.floor(currentTime)+' / '+duration+' s';$('scrub').value=currentTime;
 $('steps').innerHTML=S.phases.map((p,i)=>`<button class="${i===phaseIndex?'selected':i<phaseIndex?'done':''}" data-phase="${i}">${i+1} ${['Prepare','Distribution','Branches','Test','Cutover','Verify','Restore'][i]}</button>`).join('');
 for(const button of $('steps').children)button.onclick=()=>{pause();frame(S.phases.slice(0,+button.dataset.phase).reduce((n,p)=>n+p.seconds,0)+.01);};
 for(const r of routes){let progress=0;if(phaseIndex===1&&r.e.group==='mains')progress=clamp((t-.05)/.85);else if(phaseIndex>=2&&r.e.group==='mains')progress=1;else if(phaseIndex===2&&r.e.group==='branches')progress=clamp((t-.05)/.85);else if(phaseIndex>2)progress=1;setRange(r,progress);r.mesh.material.emissiveIntensity=phaseIndex===3?.25+.2*Math.sin(t*Math.PI*6):.16;}
 const doneCount=phaseIndex>4?5:phaseIndex===4?Math.min(5,Math.floor(t*6)):0;
 for(const tie of ties){const index=S.fixture_order.indexOf(tie.p.fixture),connected=index<doneCount;setRange(tie,connected?1:0);tie.marker.visible=phaseIndex>=2&&phaseIndex<=5;tie.marker.material.color.setHex(connected?0x75e6ad:0xffcc72);tie.marker.scale.setScalar(phaseIndex===4&&index===doneCount?1.3:1);}
 for(const tie of feedTies)setRange(tie,phaseIndex>=4?1:0);
 // Only the pilot's terminal supply drops/connectors are candidates for retirement.
 // Shared reference mains stay visible because their other users are unverified.
 for(const item of oldPilot){const index=S.fixture_order.indexOf(item.fixture);item.mesh.material.opacity=phaseIndex>=6?.05:phaseIndex>=5?.15:phaseIndex===4&&index<doneCount?.18:.48;}
 zone.visible=zoneEdge.visible=phaseIndex<6;zone.material.opacity=phaseIndex===0?.10+.20*ease(t):.22;
 for(let i=0;i<pulses.length;i++){const {dot,r}=pulses[i];dot.visible=phaseIndex>=5;dot.position.copy(r.curve.getPoint((seconds*.12+i*.13)%1));}
 renderer.render(scene,camera);
 return {phase:phase.id,phaseIndex,connected_pilot_ports:ties.filter(x=>x.mesh.visible).length,visible_routes:routes.filter(x=>x.mesh.visible).length,reference_mains_retained:true};
}
function pause(){playback=false;$('play').textContent='Play sequence';}
function tick(now){if(!playback)return;frame((now-start)/1000);if(currentTime>=duration){pause();return;}requestAnimationFrame(tick);}
$('play').onclick=()=>{if(playback){pause();return;}if(currentTime>=duration)currentTime=0;playback=true;start=performance.now()-currentTime*1000;$('play').textContent='Pause';requestAnimationFrame(tick);};$('scrub').max=duration;$('scrub').oninput=e=>{pause();frame(+e.target.value);};
new ResizeObserver(()=>{const stage=$('stage');renderer.setSize(stage.clientWidth,stage.clientHeight);camera.aspect=stage.clientWidth/stage.clientHeight;camera.updateProjectionMatrix();if(window.ready)frame(currentTime);}).observe($('stage'));
window.repipe={frame,pause,duration,validation:()=>({route_count:routes.length,pilot_port_count:ties.length,phases:S.phases.length,separate_reference_and_proposed:refGroup!==proposed})};
const bytes=Uint8Array.from(atob(window.REFERENCE_GLB),c=>c.charCodeAt(0));
new GLTFLoader().parse(bytes.buffer,'',gltf=>{reference=gltf.scene;refGroup.add(reference);const map=new Map();for(const p of S.pilot_ports){map.set(p.reference_route,p.fixture);const source=window.REFERENCE_SPEC.bathroom_pilot.supply_connections.find(c=>c.fixture===p.fixture&&c.system===p.system);map.set(source.drop,p.fixture);}
 reference.traverse(o=>{if(!o.isMesh)return;let parent=o;while(parent&&!parent.userData.kind)parent=parent.parent;const e=parent?.userData;if(e&&['CW','HW','HWC'].includes(e.system)){o.material=oldMaterial.clone();if(map.has(e.id))oldPilot.push({mesh:o,fixture:map.get(e.id)});}});
 frame(0);window.ready=true;$('loading').hidden=true;
},e=>{console.error(e);$('loading').textContent='Unable to load the reference model.'});
