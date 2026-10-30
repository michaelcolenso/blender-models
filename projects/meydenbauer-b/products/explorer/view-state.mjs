// Presentation only: interval lookup, hierarchy traversal and canonical style selection.
// No construction rates, takeoff formulas or scenario-duration calculations here.
export function activeAt(timeline, day) {
  if (!Number.isFinite(day) || day < 0 || day > timeline.working_days) throw Error('Day outside baseline');
  for (const unit of timeline.units) {
    for (const phase of unit.phases) {
      if (day >= phase.start_day && day < phase.end_day) return {unit, phase};
    }
  }
  if (day === timeline.working_days) return {unit: null, phase: null};
  throw Error('Gap in canonical timeline');
}

export function unitAt(timeline, unitId, day) {
  const unit = timeline.units.find(u => u.element_id === unitId);
  if (!unit) return {state: 'context', styles: null};
  if (day < unit.start_day) return {state: 'future', styles: {pipe: timeline.future_style, trench: timeline.future_style}};
  if (day >= unit.end_day) return {state: 'complete', styles: timeline.complete_styles};
  const phase = unit.phases.find(p => day >= p.start_day && day < p.end_day);
  return {state: phase.construction_state, styles: phase.styles};
}

export function lineage(state, id) {
  const elements = new Map(state.elements.map(e => [e.id, e]));
  const result = [], seen = new Set();
  while (elements.has(id) && !seen.has(id)) {
    seen.add(id);
    const element = elements.get(id);
    result.push(element);
    id = element.parent_id;
  }
  return result;
}

export function related(state, id, scenario) {
  const parents = lineage(state, id), ids = new Set(parents.map(e => e.id));
  const quantities = state.quantities.filter(q => ids.has(q.element_id) && (!q.scenario_id || q.scenario_id === scenario));
  const claimIds = new Set(quantities.flatMap(q => q.source_claim_ids || []));
  const claims = state.claims.filter(c => ids.has(c.subject_id) || claimIds.has(c.id));
  claims.forEach(c => claimIds.add(c.id));
  const evidenceIds = new Set([...claims.flatMap(c => c.evidence_ids), ...parents.flatMap(e => e.source_ids)]);
  return {
    claims, quantities,
    evidence: state.evidence.filter(e => evidenceIds.has(e.id)),
    activities: state.activities.filter(a => a.element_ids.some(e => ids.has(e))),
    issues: state.issues.filter(i => i.element_ids.some(e => ids.has(e)) || i.claim_ids.some(c => claimIds.has(c))),
  };
}

export function decisionAt(state, scenario) {
  const decision = state.metadata.decisions[scenario];
  if (!decision) throw Error(`Missing canonical decision: ${scenario}`);
  return decision;
}

export function semanticForObject(object, state) {
  for (let node = object; node; node = node.parent) {
    const id = node.userData?.cie_id;
    if (id && state.elements.some(e => e.id === id)) {
      return {element_id: id, role: node.userData.cie_kind || 'pipe'};
    }
    const binding = state.metadata.geometry_bindings[node.name];
    if (binding) return binding;
  }
  return null;
}
