import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {activeAt, unitAt, lineage, related, decisionAt, semanticForObject} from './view-state.mjs';
const state = JSON.parse(readFileSync(new URL('../../state/project-state.json', import.meta.url)));
const timeline = state.metadata.timeline;
const s2 = timeline.baseline_scenario_id;

test('every phase boundary is half-open, with exact terminal completion', () => {
  let previous = null;
  for (const unit of timeline.units) {
    for (const phase of unit.phases) {
      const at = activeAt(timeline, phase.start_day);
      assert.equal(at.unit.element_id, unit.element_id);
      assert.equal(at.phase.activity_id, phase.activity_id);
      assert.equal(activeAt(timeline, phase.end_day - 1e-8).phase.activity_id, phase.activity_id);
      if (previous) assert.equal(activeAt(timeline, phase.start_day - 1e-8).phase.activity_id, previous.activity_id);
      previous = phase;
    }
  }
  assert.deepEqual(activeAt(timeline, 81.5), {unit: null, phase: null});
  for (const day of [-1, 81.5001, NaN, Infinity]) assert.throws(() => activeAt(timeline, day));
});

test('all eight phases drive different canonical model presentations for every unit', () => {
  for (const unit of timeline.units) {
    const states = unit.phases.map(p => unitAt(timeline, unit.element_id, p.start_day));
    assert.equal(new Set(states.map(s => s.state)).size, 8);
    assert.equal(new Set(states.map(s => JSON.stringify(s.styles))).size, 8);
    assert.equal(unitAt(timeline, unit.element_id, unit.end_day).state, 'complete');
    if (unit.start_day) assert.equal(unitAt(timeline, unit.element_id, unit.start_day - 0.1).state, 'future');
  }
  assert.equal(unitAt(timeline, 'unknown', 0).state, 'context');
});

test('selection follows actual GLB names and inherited extras into semantic evidence and activities', () => {
  const binding = state.metadata.geometry_bindings['B-104-R000'];
  const selected = semanticForObject({name: 'mesh', parent: {name: 'B-104-R000'}}, state);
  assert.deepEqual(selected, binding);
  assert.equal(semanticForObject({userData:{cie_id:binding.element_id, cie_kind:'pipe'}},state).element_id, binding.element_id);
  assert.equal(semanticForObject({name:'Unmapped mesh'},state), null);
  assert.equal(lineage(state,binding.element_id)[1].kind, 'unit');
  const r = related(state, binding.element_id, s2);
  assert.ok(r.evidence.length);
  assert.ok(r.claims.some(c => c.predicate === 'poc_invert_depth_ft'));
  assert.ok(r.quantities.some(q => q.element_id === binding.element_id));
  assert.equal(r.activities.length, 8);
  assert.ok(r.issues.some(i => i.severity === 'critical'));
});

test('scenario propagation filters canonical quantities, preserves baseline and refuses invented durations', () => {
  for (const scenario of state.scenarios) {
    const decision = decisionAt(state, scenario.id);
    const q = state.quantities.find(q => q.scenario_id === scenario.id && q.measure === 'slab_cut' && q.element_id.includes(':system:'));
    assert.equal(decision.value, q.value);
    const pipe = state.elements.find(e => e.kind === 'pipe');
    const r = related(state, pipe.id, scenario.id);
    assert.ok(r.quantities.length);
    assert.ok(r.quantities.every(q => !q.scenario_id || q.scenario_id === scenario.id));
    if (scenario.id === s2) assert.equal(decision.working_days, 81.5);
    else {assert.equal(decision.working_days, null); assert.equal(decision.schedule_status, 'not_calculated');}
  }
  const changed = structuredClone(state);
  changed.metadata.decisions[s2].value = 123;
  assert.equal(decisionAt(changed,s2).value,123); // read canonical presentation, never recompute in the browser
  assert.equal(timeline.working_days,81.5);
  assert.throws(() => decisionAt(state,'missing'));
});
