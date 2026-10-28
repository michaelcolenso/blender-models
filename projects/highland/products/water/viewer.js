import * as THREE from 'three';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';

const $=id=>document.getElementById(id);
const scene=new THREE.Scene();scene.background=new THREE.Color('#0b1822');
const camera=new THREE.PerspectiveCamera(37,1,.03,300);
const renderer=new THREE.WebGLRenderer({antialias:true,preserveDrawingBuffer:true});
renderer.setPixelRatio(Math.min(devicePixelRatio,2));renderer.outputColorSpace=THREE.SRGBColorSpace;
renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1.1;
$('canvas').append(renderer.domElement);
const controls=new OrbitControls(camera,renderer.domElement);controls.enableDamping=true;controls.dampingFactor=.09;
controls.minDistance=1;controls.maxDistance=110;controls.maxPolarAngle=Math.PI*.91;
scene.add(new THREE.HemisphereLight(0xcdeeff,0x3d4650,1.5));
for(const [x,y,z,p] of [[10,20,15,2],[-10,8,-8,1.5],[0,2,12,1]]){
 const light=new THREE.DirectionalLight(0xffffff,p);light.position.set(x,y,z);scene.add(light);
}
const loader=new GLTFLoader(),models={};let current='unit',selected=null,auto=false,bathroomFocus=false;
const shown={CW:true,HW:true,HWC:true,MW:true,hardware:true,context:true,fixtures:true,equipment:true};
const selectionDialog=document.createElement('dialog');selectionDialog.innerHTML='<button id="close-selection">Close</button><div id="selection-content"></div>';document.body.append(selectionDialog);$('close-selection').onclick=()=>selectionDialog.close();
const info={
 unit:{title:'Inside Unit 107',subtitle:'Fixture connections • P4.01',body:'Follow the overhead supplies into the bathrooms, washer and kitchen. The kitchen sink drops below the floor; the green line returns circulating hot water.',stats:'14 fixtures · one detailed dwelling',target:[0,1,2.18],position:[19.3,23.1,29.6],top:[0,40,2.19],scale:'Pipes shown at 1.5× nominal diameter. Unit XY calibrated through A2.03 / P2.02; allowance ±1% scale, ±6 in local trace. Pipe heights and fixture envelopes remain assumed.'},
 building:{title:'The shared water network',subtitle:'Five stack groups • P3.02',body:'Blue supplies cold water. Orange delivers hot water. Green returns water for circulation. Each short branch marks a continuation to a dwelling plan.',stats:'5 stack groups · 23 visible branch groups',target:[0,11,0],position:[29,23,36],top:[0,52,.01],scale:'Pipes shown at 2.5× nominal diameter. Floor datums follow A3.11. Stack positions remain illustrative; the ’04 stack’s R1 dwelling connection remains unresolved.'},
 plant:{title:'Where the hot water starts',subtitle:'Boilers & storage • P3.02 / detail 1',body:'Two boilers connect with two storage tanks. The return line brings circulating water back to the plant. Pump WAC2 is a loose spare, so only one circulation pump is installed in this view.',stats:'2 boilers · 2 storage tanks · 3 installed pumps',target:[0,1.4,0],position:[9,9,12],top:[0,17,.01],scale:'Nominal pipe diameters shown at 1×. Equipment envelopes and arrangement are illustrative; relief piping, flues, controls and balancing bypasses are not fully modeled.'}
};
function showModel(name){
 bathroomFocus=false;current=name;for(const [id,m] of Object.entries(models))m.visible=id===name;
 const i=info[name];$('model-title').textContent=i.title;$('model-subtitle').textContent=i.subtitle;
 $('story').textContent=i.body;$('stats').textContent=i.stats;$('scale').textContent=i.scale;
 document.querySelectorAll('[data-model]').forEach(b=>{b.classList.toggle('active',b.dataset.model===name);b.setAttribute('aria-pressed',String(b.dataset.model===name));});
 controls.target.fromArray(i.target);camera.position.fromArray(i.position).sub(controls.target).multiplyScalar(Math.max(1,1.15/camera.aspect)).add(controls.target);controls.update();resetSelection();
 $('detail').innerHTML='<span class="eyebrow">Inspect the model</span><p>Select a pipe or fixture to see its drawing reference and size.</p>';
}
function resetSelection(){if(selected){selected.traverse(o=>{if(o.isMesh&&o.userData.oldMaterial){o.material=o.userData.oldMaterial;delete o.userData.oldMaterial;}});selected=null;}}
function escape(s){return String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
function pick(event){
 if(down&&Math.hypot(event.clientX-down[0],event.clientY-down[1])>5)return;
 const rect=renderer.domElement.getBoundingClientRect();const pointer=new THREE.Vector2((event.clientX-rect.left)/rect.width*2-1,-(event.clientY-rect.top)/rect.height*2+1);
 const ray=new THREE.Raycaster();ray.setFromCamera(pointer,camera);
 const hits=ray.intersectObject(models[current],true).filter(h=>{let o=h.object;while(o){if(!o.visible)return false;o=o.parent;}return true;});
 if(!hits.length)return;
 let obj=hits[0].object;while(obj.parent&&!obj.userData.kind)obj=obj.parent;
 const d=obj.userData;if(!d.kind||d.kind==='label')return;resetSelection();selected=obj;
 obj.traverse(o=>{if(o.isMesh){o.userData.oldMaterial=o.material;const material=o.material.clone();material.emissive=new THREE.Color('#f4dd76');material.emissiveIntensity=.65;o.material=material;}});
 $('detail').innerHTML=`<span class="eyebrow">${escape(d.system)} / ${escape(d.kind)}</span><h3>${escape(d.tag||d.id||obj.name)}</h3>${d.nominal_in?`<p><strong>${d.nominal_in}″ nominal</strong> · ${escape(d.size_status||d.hardware_status||"assumed")} size</p>`:''}<p>${escape(d.source||'Presentation context')}</p>${d.role?`<p>${escape(d.role)}</p>`:''}${d.hardware_status?'<small>Representative hardware; exact product and arrangement unverified.</small>':''}<small>${d.xy_status==='provisional'?'Plan XY: provisional (A2.03 / P2.02); height & envelope: assumed.':d.xy_status==='assumed'?'Local position and hardware: assumed; fixture anchors derive from the calibrated plan.':d.datum_status?'Floor datum: confirmed (A3.11); XY: assumed.':'Position & envelope: assumed.'} ${escape(d.size_status==='assumed'?d.size_basis||'':'')}</small>`;
 if(innerWidth<=800){$('selection-content').innerHTML=$('detail').innerHTML;selectionDialog.showModal();}
}
let down=null;renderer.domElement.addEventListener('pointerdown',e=>down=[e.clientX,e.clientY]);renderer.domElement.addEventListener('pointerup',pick);
document.querySelectorAll('[data-model]').forEach(b=>b.onclick=()=>showModel(b.dataset.model));
document.querySelectorAll('[data-system]').forEach(b=>b.onclick=()=>{
 const s=b.dataset.system;shown[s]=!shown[s];b.classList.toggle('off',!shown[s]);b.setAttribute('aria-pressed',String(shown[s]));
 for(const m of Object.values(models))m.traverse(o=>{if(s==='hardware'&&['elbow','tee','stop','mixer'].includes(o.userData.kind)){o.visible=shown[s]&&(shown[o.userData.system]!==false);}else if(o.userData.system===s){o.visible=shown[s]&&(!['elbow','tee','stop','mixer'].includes(o.userData.kind)||shown.hardware);}});
});
$('bath').onclick=()=>{showModel('unit');controls.target.set(-7,1,-5.5);camera.position.set(2,10,5).sub(controls.target).multiplyScalar(.78*Math.max(1,1.15/camera.aspect)).add(controls.target);controls.update();$('model-title').textContent='Primary bathroom';$('story').textContent='Nine supply ports connect the five fixtures. Inspect the rounded elbows, branch tees, shutoffs and mixing bodies. Purple shows mixed water to the shower and tub; hardware and heights are representative.';$('stats').textContent='5 fixtures · 9 supply connections';bathroomFocus=true;};
$('connections').onclick=()=>{$('bath').click();controls.target.set(-7.3,.85,-4.4);camera.position.set(-2,3.2,0).sub(controls.target).multiplyScalar(Math.max(1,1.15/camera.aspect)).add(controls.target);controls.update();$('model-title').textContent='Fixture connections';};
$('reset').onclick=()=>showModel(current);
$('top').onclick=()=>{controls.target.fromArray(info[current].target);camera.position.fromArray(info[current].top).sub(controls.target).multiplyScalar(Math.max(1,1.15/camera.aspect)).add(controls.target);controls.update();};
$('rotate').onclick=()=>{auto=!auto;controls.autoRotate=auto;$('rotate').setAttribute('aria-pressed',String(auto));$('rotate').textContent=auto?'Pause orbit':'Orbit model';};
$('notes').onclick=()=>$('notes-dialog').showModal();$('close-notes').onclick=()=>$('notes-dialog').close();
$('limitations').innerHTML=window.MODEL_SPEC.limitations.map(s=>`<li>${escape(s)}</li>`).join('');
const observer=new ResizeObserver(()=>{const w=$('canvas').clientWidth,h=$('canvas').clientHeight;renderer.setSize(w,h);camera.aspect=w/h;camera.updateProjectionMatrix();if(window.ready){if(bathroomFocus)$('bath').click();else showModel(current);}});observer.observe($('canvas'));
async function load(){
 for(const name of ['unit','building','plant']){
  const bytes=Uint8Array.from(atob(window.MODELS[name]),c=>c.charCodeAt(0));
  const gltf=await loader.parseAsync(bytes.buffer,'');models[name]=gltf.scene;scene.add(gltf.scene);gltf.scene.visible=false;
 }
 showModel('unit');$('bath').click();$('loading').hidden=true;window.ready=true;
}
load().catch(error=>{$('loading').textContent='The 3D viewer could not start: '+error.message;console.error(error);});
renderer.setAnimationLoop(()=>{controls.update();renderer.render(scene,camera);});
// Fixed-time camera control for reproducible video capture, independent of frame rate.
window.videoFrame=({target,position,angle=0})=>{
 controls.autoRotate=false;controls.enableDamping=false;
 const t=new THREE.Vector3().fromArray(target);
 const offset=new THREE.Vector3().fromArray(position).sub(t);
 offset.applyAxisAngle(new THREE.Vector3(0,1,0),angle);
 controls.target.copy(t);camera.position.copy(t).add(offset);
 controls.update();renderer.render(scene,camera);
};
// Deterministic camera positions for review frames and the owner video.
window.presentation={show:showModel,frame(name,angle){if(current!==name)showModel(name);const i=info[name],t=new THREE.Vector3().fromArray(i.target);let v=new THREE.Vector3().fromArray(i.position).sub(t);v.applyAxisAngle(new THREE.Vector3(0,1,0),angle);camera.position.copy(t).add(v);controls.target.copy(t);controls.update();renderer.render(scene,camera);},stats(){return Object.fromEntries(Object.entries(models).map(([k,m])=>[k,{objects:m.children.length,meshes:(()=>{let n=0;m.traverse(o=>{if(o.isMesh)n++;});return n;})()}]));}};
