import * as THREE from 'three';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {activeAt, unitAt, lineage, related, decisionAt, semanticForObject} from './view-state.mjs';

const STATE = '../../state/project-state.json';
const GLB = '../../deliverables/underslab/Meydenbauer-B-underslab.glb';
const $ = s => document.querySelector(s), $$ = s => [...document.querySelectorAll(s)];
const esc = v => String(v ?? '—').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const number = (v, digits=1) => v == null ? '—' : Number(v).toLocaleString(undefined, {maximumFractionDigits: digits});
let state, timeline, scenario, selectedId, mode = 'time', model, currentDay = 0, playing = false, lastFrame = 0;
const index = new Map(), meshes = [];

function inspect(id) {
  const el = index.get(id);
  if (!el) return;
  selectedId = id;
  const r = related(state, id, scenario);
  $('#inspector').innerHTML = `
    <div class="card"><span class="eyebrow">${esc(el.kind)}</span><h2>${esc(el.name)}</h2>
    <div class="id">${esc(el.id)}</div><span class="status">${esc(el.status)}</span></div>
    <div class="card"><span class="label">QUANTITIES · ${esc(index.get(scenario).name)}</span>
    ${r.quantities.map(q => `<div class="source"><div class="id">${esc(q.element_id)}</div><b>${esc(q.measure)} · ${number(q.value, 2)} ${esc(q.unit)}</b><div class="id">${esc(q.id)}</div></div>`).join('')}</div>
    <div class="card"><span class="label">CLAIMS → EVIDENCE</span>
    ${r.claims.map(c => `<div class="source"><b>${esc(c.predicate)} · ${esc(c.status)}</b><div class="id">${esc(c.id)}</div>${esc(c.value)}
    <div>${esc(c.rationale)}</div>${c.evidence_ids.map(e => `<div class="id">↳ ${esc(index.get(e)?.source)} · ${esc(index.get(e)?.locator)}</div>`).join('')}</div>`).join('')}
    ${r.evidence.map(e => `<div class="source"><b>${esc(e.source)} · ${esc(e.locator)}</b>${esc(e.description)}</div>`).join('')}</div>
    <div class="card"><span class="label">ACTIVITIES · S2 BASELINE</span>
    ${r.activities.map(a => `<div class="source"><b>${esc(a.name)}</b>${number(a.duration_working_days)} working days<div class="id">${esc(a.id)}</div></div>`).join('')}</div>
    <div class="card"><span class="label">OPEN ISSUES</span>
    ${r.issues.map(i => `<div class="source"><b>${esc(i.severity)} · ${esc(i.title)}</b>${esc(i.description)}<div class="id">${esc(i.id)}</div></div>`).join('') || 'None directly linked.'}</div>`;
}

function decisionUI() {
  const d = decisionAt(state, scenario), s = index.get(scenario);
  $('#decision').className = `decision ${d.within_allowance ? '' : 'over'}`;
  $('#decision').innerHTML = `<span class="label">${esc(s.name)} · SLAB ALLOWANCE</span><strong>${number(d.value)} SF</strong>
    <span>${number(Math.abs(d.delta))} SF ${d.within_allowance ? 'REMAINING' : 'OVER'} / ${number(d.allowance)} SF</span>`;
  $('#decision-line').textContent = `${s.name}: ${number(Math.abs(d.delta))} SF ${d.within_allowance ? 'remaining' : 'over allowance'}`;
  $('#propagation-line').textContent = `${d.takeoff_case}: ${number(s.inputs.poc_invert_ft)} ft assumed invert → ${number(d.value)} SF → ${number(d.excavation_bank_cy)} CY`;
  $('#schedule-basis').textContent = d.schedule_status === 'baseline_strawman'
    ? `S2 baseline · ${number(d.working_days)} working days · rates and order assumed`
    : `${s.name} duration: NOT CALCULATED · timeline and model remain S2 baseline`;
  $('#scenario-description').textContent = s.description;
  if (selectedId) inspect(selectedId);
  timelineUI();
}

function scenarioUI() {
  $('#scenarios').innerHTML = state.scenarios.map(s => `<button class="scenario ${s.id === scenario ? 'active' : ''}" data-scenario="${esc(s.id)}" aria-pressed="${s.id === scenario}">${esc(s.name)}<span>${number(s.inputs.poc_invert_ft)}′</span></button>`).join('');
  $$('.scenario').forEach(b => b.onclick = () => {scenario = b.dataset.scenario; scenarioUI(); decisionUI();});
}

function timelineUI() {
  const a = activeAt(timeline, currentDay), total = timeline.working_days;
  $('#time-slider').max = total;
  $('#time-slider').value = currentDay;
  $('#time-readout').textContent = `DAY ${currentDay.toFixed(1)} / ${total}`;
  $('#active-phase').textContent = a.phase ? `${a.unit.unit} · ${a.phase.name}` : 'Baseline sequence complete';
  $('#elapsed').textContent = `${number(currentDay)} d elapsed · ${number(total - currentDay)} d remaining` + (a.unit ? ` · ${a.unit.unit}: ${number(currentDay-a.unit.start_day)} d elapsed / ${number(a.unit.end_day-currentDay)} d remaining` : '');
  $('#phase-duration').textContent = a.phase
    ? `${number(currentDay - a.phase.start_day)} / ${number(a.phase.duration_days)} d in phase · ${number(a.phase.end_day - currentDay)} d remaining · ${a.phase.construction_state}`
    : 'All baseline activities complete · acceptance not recorded';
  const qs = a.unit ? state.quantities.filter(q => q.element_id === a.unit.element_id && (!q.scenario_id || q.scenario_id === scenario)) : [];
  $('#active-quantities').textContent = a.unit ? `${index.get(scenario).name} quantities · ` + qs.map(q => `${q.measure}: ${number(q.value)} ${q.unit}`).join(' · ') : 'No active unit';
  $('#unit-track').innerHTML = timeline.units.map(u => `<button class="unit-segment ${currentDay >= u.end_day ? 'done' : ''} ${a.unit === u ? 'active' : ''}" data-unit="${u.element_id}">${u.unit} · ${number(u.end_day-u.start_day)} d</button>`).join('');
  $$('.unit-segment').forEach(b => b.onclick = () => {const u = timeline.units.find(u => u.element_id === b.dataset.unit); setDay(u.start_day); inspect(u.element_id);});
  $('#phase-track').innerHTML = (a.unit?.phases || []).map(p => `<button class="phase-step ${p === a.phase ? 'active' : ''}" data-day="${p.start_day}">${esc(p.name)}</button>`).join('');
  $$('.phase-step').forEach(b => b.onclick = () => setDay(Number(b.dataset.day)));
  applyMode();
}

function setMode(value) {
  mode = value;
  $$('.mode').forEach(b => b.classList.toggle('active', b.dataset.mode === mode));
  applyMode();
}
function setDay(value) {
  currentDay = Math.max(0, Math.min(timeline.working_days, value));
  setMode('time');
  timelineUI();
}

function applyMode() {
  $('#mode-label').textContent = mode.toUpperCase();
  for (const item of meshes) {
    const {mesh, binding, unitId, base} = item, el = binding && index.get(binding.element_id);
    mesh.visible = mode !== 'risk' || !!el && ['unknown','assumed','provisional'].includes(el.status);
    const presentation = mode === 'time' && unitId ? unitAt(timeline, unitId, currentDay) : null;
    const style = presentation?.styles?.[binding.role];
    mesh.userData.construction_state = presentation?.state || 'context';
    const materials = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
    materials.forEach((mat, i) => {
      mat.color.copy(base[i].color);
      mat.opacity = base[i].opacity;
      mat.transparent = base[i].transparent;
      mat.depthWrite = base[i].depthWrite;
      if (mode === 'evidence' && el) mat.opacity = el.status === 'confirmed' ? 1 : el.status === 'provisional' ? 0.72 : 0.38;
      if (style) {mat.color.set(style.color); mat.opacity = style.opacity;}
      mat.transparent = mat.transparent || mat.opacity < 1;
      mat.depthWrite = mat.opacity >= 0.5 && base[i].depthWrite;
      mat.needsUpdate = true;
    });
  }
}

async function boot() {
  const response = await fetch(STATE);
  if (!response.ok) throw Error(`state ${response.status}`);
  state = await response.json();
  timeline = state.metadata.timeline;
  scenario = timeline.baseline_scenario_id;
  for (const group of ['evidence','claims','elements','quantities','activities','issues','scenarios']) for (const x of state[group]) index.set(x.id, x);
  scenarioUI(); decisionUI();
  $('#visual-basis').textContent = timeline.visual_basis;
  $('#constraints').textContent = timeline.constraints.join(' · ');
  $('#health').textContent = `state ${state.schema_version} · ${state.elements.length} elements · S2 baseline`;
  const host = $('#canvas'), scene = new THREE.Scene(), camera = new THREE.PerspectiveCamera(38, 1, 0.01, 1000);
  const renderer = new THREE.WebGLRenderer({antialias:true, alpha:true});
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2)); host.append(renderer.domElement);
  const controls = new OrbitControls(camera, renderer.domElement); controls.enableDamping = true;
  scene.add(new THREE.HemisphereLight(0xf4f1e7, 0x31342c, 2.3));
  const sun = new THREE.DirectionalLight(0xffffff, 2); sun.position.set(8,-10,15); scene.add(sun);
  const resize = () => {const r=host.getBoundingClientRect(); renderer.setSize(r.width,r.height); camera.aspect=r.width/r.height; camera.updateProjectionMatrix();};
  addEventListener('resize', resize); resize();
  model = (await new GLTFLoader().loadAsync(GLB)).scene;
  model.traverse(mesh => {
    if (!mesh.isMesh) return;
    const binding = semanticForObject(mesh, state);
    const unitId = binding && lineage(state, binding.element_id).find(e => e.kind === 'unit')?.id;
    // GLTF materials are shared across units: isolate before any presentation changes.
    mesh.material = Array.isArray(mesh.material) ? mesh.material.map(m => m.clone()) : mesh.material.clone();
    const materials = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
    meshes.push({mesh, binding, unitId, base: materials.map(m => ({color:m.color.clone(), opacity:m.opacity, transparent:m.transparent, depthWrite:m.depthWrite}))});
  });
  scene.add(model);
  const box = new THREE.Box3().setFromObject(model), center = box.getCenter(new THREE.Vector3()), size = box.getSize(new THREE.Vector3()).length();
  controls.target.copy(center); camera.position.copy(center).add(new THREE.Vector3(size*0.55, size*0.65, size*0.55));
  camera.near=size/1000; camera.far=size*10; camera.updateProjectionMatrix(); controls.update(); applyMode();
  const ray = new THREE.Raycaster(), mouse = new THREE.Vector2();
  renderer.domElement.onclick = e => {
    const r=renderer.domElement.getBoundingClientRect(); mouse.set((e.clientX-r.left)/r.width*2-1, -((e.clientY-r.top)/r.height)*2+1); ray.setFromCamera(mouse,camera);
    for (const hit of ray.intersectObject(model, true)) {
      if (!hit.object.visible) continue;
      const binding = semanticForObject(hit.object, state);
      if (binding) {inspect(binding.element_id); break;}
    }
  };
  function frame(t) {
    requestAnimationFrame(frame);
    if (playing && lastFrame) {
      setDay(currentDay + Math.min((t-lastFrame)/1000, 0.1)*2);
      if (currentDay === timeline.working_days) {playing=false; $('#play').textContent='PLAY';}
    }
    lastFrame=t; controls.update(); renderer.render(scene,camera);
  }
  requestAnimationFrame(frame);
  $('#play').disabled = false; $('#time-slider').disabled = false;
}
$$('.mode').forEach(b => b.onclick = () => setMode(b.dataset.mode));
$('#time-slider').oninput = e => setDay(Number(e.target.value));
$('#play').onclick = () => {if (currentDay >= timeline.working_days) setDay(0); setMode('time'); playing=!playing; $('#play').textContent=playing?'PAUSE':'PLAY';};
boot().catch(e => {$('#health').textContent=`blocked · ${e.message}`; $('#health').classList.add('bad'); $('#decision-line').textContent='Explorer input unavailable'; console.error(e);});
