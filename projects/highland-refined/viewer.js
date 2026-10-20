import * as THREE from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {RGBELoader} from 'three/addons/loaders/RGBELoader.js';
import {mergeGeometries} from 'three/addons/utils/BufferGeometryUtils.js';
import {EffectComposer} from 'three/addons/postprocessing/EffectComposer.js';
import {RenderPass} from 'three/addons/postprocessing/RenderPass.js';
import {ShaderPass} from 'three/addons/postprocessing/ShaderPass.js';
import {OutputPass} from 'three/addons/postprocessing/OutputPass.js';
import {FXAAShader} from 'three/addons/shaders/FXAAShader.js';

const [path,review]=await Promise.all([fetch('/output/camera-path.json').then(r=>r.json()),fetch('/output/revision-validation.json').then(r=>r.json())]);
const renderer=new THREE.WebGLRenderer({antialias:false,preserveDrawingBuffer:true,powerPreference:'high-performance'});
renderer.setPixelRatio(1);renderer.setSize(innerWidth,innerHeight);renderer.outputColorSpace=THREE.SRGBColorSpace;
renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1.05;
renderer.shadowMap.enabled=true;renderer.shadowMap.type=THREE.PCFSoftShadowMap;renderer.shadowMap.autoUpdate=false;
document.body.prepend(renderer.domElement);
const scene=new THREE.Scene(),camera=new THREE.PerspectiveCamera(28,innerWidth/innerHeight,.1,900);
const composer=new EffectComposer(renderer);composer.addPass(new RenderPass(scene,camera));composer.addPass(new OutputPass());
const fxaa=new ShaderPass(FXAAShader);fxaa.material.uniforms.resolution.value.set(1/innerWidth,1/innerHeight);composer.addPass(fxaa);renderer.info.autoReset=false;
const map=new THREE.PMREMGenerator(renderer);map.compileEquirectangularShader();
const sky=await new RGBELoader().loadAsync('/sky.hdr');sky.mapping=THREE.EquirectangularReflectionMapping;
scene.environment=map.fromEquirectangular(sky).texture;scene.background=new THREE.Color('#17273d');scene.environmentIntensity=.22;
const skyDome=new THREE.Mesh(new THREE.SphereGeometry(400,40,24),new THREE.MeshBasicMaterial({map:sky,color:new THREE.Color(.20,.32,.60),side:THREE.BackSide,depthWrite:false}));scene.add(skyDome);
scene.add(new THREE.HemisphereLight(0x9bb8e9,0x292320,.9));
const sun=new THREE.DirectionalLight(0xf5ddbe,1.5);sun.position.set(-35,55,45);sun.target.position.set(19,8,-23);scene.add(sun,sun.target);
sun.castShadow=true;sun.shadow.mapSize.set(2048,2048);Object.assign(sun.shadow.camera,{left:-85,right:85,top:85,bottom:-85,near:1,far:220});sun.shadow.bias=-.00045;sun.shadow.normalBias=.04;
const model=(await new GLTFLoader().loadAsync('/output/Highland-revised-exterior.glb')).scene;model.updateMatrixWorld(true);
const normalize=s=>s.replace(/[^a-z0-9]/gi,'').toLowerCase();const lit=review.lit_window_ids.map(normalize);
const groups=new Map();let sourceMeshes=0,leafTriangles=0;

function brickShader(mat,axis){
 mat.color.setRGB(.50,.23,.13);mat.roughness=.85;mat.metalness=0;
 mat.onBeforeCompile=shader=>{
  shader.vertexShader='varying vec3 vBrickWorld;\n'+shader.vertexShader;
  shader.vertexShader=shader.vertexShader.replace('#include <worldpos_vertex>','#include <worldpos_vertex>\nvBrickWorld=(modelMatrix*vec4(transformed,1.0)).xyz;');
  shader.fragmentShader='varying vec3 vBrickWorld;\n'+shader.fragmentShader;
  shader.fragmentShader=shader.fragmentShader.replace('#include <map_fragment>',`#include <map_fragment>
   vec2 p=vec2(vBrickWorld.${axis},vBrickWorld.y);
   float row=floor(p.y/.067);vec2 cell=vec2(p.x/.203+mod(row,2.)*.5,p.y/.067);
   vec2 edge=min(fract(cell),1.-fract(cell));vec2 aa=max(fwidth(cell),vec2(.001));
   float face=smoothstep(.013-aa.x,.013+aa.x,edge.x)*smoothstep(.038-aa.y,.038+aa.y,edge.y);
   float r=fract(sin(dot(floor(cell),vec2(12.9898,78.233)))*43758.5453);
   diffuseColor.rgb*=mix(vec3(.39,.41,.39),vec3(.68+.39*r),face);`);
 };
 mat.customProgramCacheKey=()=>`highlandBrick-${axis}`;
}

function simplifyLeaves(geo,stride){
 const pos=geo.attributes.position,normal=geo.attributes.normal,ps=[],ns=[];
 for(let start=0;start<pos.count;start+=18*stride){
  const end=Math.min(start+18,pos.count),c=new THREE.Vector3();
  for(let i=start;i<end;i++)c.add(new THREE.Vector3().fromBufferAttribute(pos,i));c.multiplyScalar(1/(end-start));
  for(let i=start;i<end;i++){const v=new THREE.Vector3().fromBufferAttribute(pos,i).sub(c).multiplyScalar(Math.sqrt(stride)*.77).add(c);ps.push(v.x,v.y,v.z);ns.push(normal.getX(i),normal.getY(i),normal.getZ(i));}
 }
 const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.Float32BufferAttribute(ps,3));g.setAttribute('normal',new THREE.Float32BufferAttribute(ns,3));leafTriangles+=ps.length/9;return g;
}

model.traverse(o=>{
 if(!o.isMesh)return;sourceMeshes++;
 let geo=o.geometry.index?o.geometry.toNonIndexed():o.geometry.clone();
 for(const key of Object.keys(geo.attributes))if(!['position','normal'].includes(key))geo.deleteAttribute(key);
 if(!geo.attributes.normal)geo.computeVertexNormals();geo.applyMatrix4(o.matrixWorld);
 const source=o.material;let key=source.name;
 const luminous=lit.some(id=>normalize(o.name).includes(id));
 if(luminous&&/Room back|Room slab|Linen folds|Room_back|Room_slab|Linen_folds/i.test(o.name))key+=' / illuminated';
 if(!groups.has(key)){
  const diffuse=/^(Botanical|Context |ground$|paving$|bark$)/.test(source.name);
  const m=diffuse?new THREE.MeshLambertMaterial({color:source.color?.clone()||new THREE.Color(.3,.3,.3),side:THREE.DoubleSide}):new THREE.MeshStandardMaterial({color:source.color?.clone()||new THREE.Color(.3,.3,.3),roughness:source.roughness??.7,metalness:source.metalness??0,side:THREE.DoubleSide});
  m.name=key;
  if(source.emissive){m.emissive.copy(source.emissive);m.emissiveIntensity=source.emissiveIntensity||1;}
  if(source.name==='brick-x')brickShader(m,'x');
  if(source.name==='brick-y')brickShader(m,'z');
  if(source.name==='glass'){m.color.setRGB(.43,.51,.57);m.metalness=.08;m.roughness=.16;m.transparent=true;m.opacity=.27;m.depthWrite=false;}
  if(source.name.startsWith('Botanical')){m.roughness=.87;m.metalness=0;}
  if(source.name==='road'){m.color.setRGB(.10,.115,.13);m.roughness=.25;m.metalness=.35;}
  if(source.name==='ground'){m.color.setRGB(.045,.085,.025);m.roughness=.95;}
  if(source.name==='paving'){m.roughness=.73;m.color.setRGB(.36,.37,.35);}
  if(luminous){m.color.multiplyScalar(1.2);m.emissive.setRGB(.90,.43,.12);m.emissiveIntensity=.75;}
  groups.set(key,{material:m,geometries:[]});
 }
 if(source.name.startsWith('Botanical'))geo=simplifyLeaves(geo,/Tree.*leaves/i.test(o.name)?8:4);
 groups.get(key).geometries.push(geo);
});
for(const {material,geometries} of groups.values()){
 const geometry=mergeGeometries(geometries,false);if(!geometry)throw Error('Failed to batch '+material.name);
 const mesh=new THREE.Mesh(geometry,material);const fineMetal=['rail','frame'].includes(material.name);mesh.castShadow=material.name!=='glass'&&!fineMetal;mesh.receiveShadow=!fineMetal;scene.add(mesh);
}
const poolCanvas=document.createElement('canvas');poolCanvas.width=poolCanvas.height=128;const pc=poolCanvas.getContext('2d'),gradient=pc.createRadialGradient(64,64,0,64,64,64);gradient.addColorStop(0,'rgba(255,185,95,.38)');gradient.addColorStop(.32,'rgba(255,168,70,.17)');gradient.addColorStop(1,'rgba(255,160,60,0)');pc.fillStyle=gradient;pc.fillRect(0,0,128,128);const poolTexture=new THREE.CanvasTexture(poolCanvas);poolTexture.colorSpace=THREE.SRGBColorSpace;
const grade=(x,y)=>Math.max(0,Math.min(1,y/45.72))*(5.7912*(1-Math.max(0,Math.min(1,x/36.068)))+3.6576*Math.max(0,Math.min(1,x/36.068)));
for(const [x,y] of [[40.8,-2.5],[41.5,29.5],[-1,-2.7]]){
 const radius=2.3,vertices=[];for(const [dx,dy] of [[-1,-1],[1,-1],[1,1],[-1,1]])vertices.push(x+dx*radius,grade(x+dx*radius,y+dy*radius)+.025,-y-dy*radius);
 const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.Float32BufferAttribute(vertices,3));g.setAttribute('uv',new THREE.Float32BufferAttribute([0,0,1,0,1,1,0,1],2));g.setIndex([0,1,2,0,2,3]);g.computeVertexNormals();
 scene.add(new THREE.Mesh(g,new THREE.MeshBasicMaterial({map:poolTexture,transparent:true,depthWrite:false,side:THREE.DoubleSide,blending:THREE.AdditiveBlending})));
}
function convert(a){return new THREE.Vector3(a[0],a[2],-a[1]);}
function frame(index){
 const p=path[Math.max(0,Math.min(path.length-1,index))];camera.position.copy(convert(p.position_m));camera.lookAt(convert(p.target_m));camera.fov=p.vertical_fov_degrees;camera.aspect=innerWidth/innerHeight;camera.updateProjectionMatrix();
 renderer.info.reset();composer.render();return {frame:p.frame,time:p.time,position:p.position_m,fov:camera.fov};
}
renderer.shadowMap.needsUpdate=true;frame(0);renderer.shadowMap.needsUpdate=false;
const captureCanvas=document.createElement('canvas');captureCanvas.width=innerWidth;captureCanvas.height=innerHeight;const ctx=captureCanvas.getContext('2d');
function capture(index,format='image/jpeg'){
 frame(index);ctx.drawImage(renderer.domElement,0,0);ctx.save();ctx.shadowColor='rgba(0,0,0,.7)';ctx.shadowBlur=8;ctx.fillStyle='#f5f2e9';ctx.font='25px Arial';ctx.letterSpacing='4px';ctx.fillText('200 WEST HIGHLAND',innerWidth*.04,innerHeight*.95-29);ctx.shadowBlur=4;ctx.font='12px Arial';ctx.letterSpacing='.3px';ctx.fillStyle='#e4e8e7';ctx.fillText('Drawing-based visualization · Façade details and site context are approximate.',innerWidth*.04,innerHeight*.95);ctx.restore();
 return captureCanvas.toDataURL(format,.95).split(',')[1];
}
window.highland={frame,capture,stats:()=>({sourceMeshes,drawCalls:renderer.info.render.calls,triangles:renderer.info.render.triangles,leafTriangles,frames:path.length,dimensions:[innerWidth,innerHeight],renderer:renderer.getContext().getParameter(renderer.getContext().RENDERER)})};
document.querySelector('#loading').remove();window.ready=true;
