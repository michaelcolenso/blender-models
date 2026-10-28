"""Separate proposed sequencing spec. No changes to the drawing-reference model."""
from pathlib import Path
import hashlib,json
here=Path(__file__).parent
base=here.parent/'water/highland-water.spec.json'
s=json.loads(base.read_text()); elements=[]
for e in s['elements']:
 if e['scene']=='unit' and e['kind']=='pipe' and e['system'] in ['CW','HW','HWC']:
  elements.append(dict(id='proposed-'+e['id'],reference_id=e['id'],system=e['system'],points=e.get('render_points',e['points']),nominal_in=e['nominal_in'],group='branches' if e.get('terminal') or 'connector' in e['id'] else 'mains',status='assumed',basis='Concept sequence reuses the drawing-study topology. New-route separation is graphical; final route, size, material and isolation limits are unselected.'))
phases=[
 dict(id='prepare',seconds=4,title='01 / Prepare the pilot work area',action='Survey access, locate services, protect the work area and coordinate resident access.',service='Existing supply intended to remain in service',gate='Confirm route, access and isolation boundaries before work.',view='bath'),
 dict(id='mains',seconds=5,title='02 / Install parallel distribution',action='New supply and circulation paths appear alongside the reference network.',service='Existing supply retained • new piping not in service',gate='Spacing is graphic only; final routing and materials remain open.',view='unit'),
 dict(id='branches',seconds=5,title='03 / Run branches to the fixtures',action='Prepare new branches; leave final fixture connections isolated for cutover.',service='Existing supply retained • new fixture ties held',gate='The nine colored tie points identify the bathroom pilot.',view='bath'),
 dict(id='test',seconds=4,title='04 / Test the isolated new section',action='Complete the specified inspections, testing and water-quality preparation.',service='New section held out of service pending acceptance',gate='Acceptance gate shown as a proposal—not a recorded test result.',view='bath'),
 dict(id='cutover',seconds=6,title='05 / Cut over one unit at a time',action='Isolate the verified unit boundary and tie in the new supplies. The bathroom shows the switch.',service='Planned service interruption • affected scope to be verified',gate='No outage duration or independent unit isolation is assumed.',view='close'),
 dict(id='commission',seconds=4,title='06 / Verify service at the pilot',action='Check leaks, fixture operation, hot-water delivery and circulation before release.',service='Restore pilot service only after acceptance',gate='Colored pulses indicate the sequence, not simulated water flow.',view='bath'),
 dict(id='restore',seconds=4,title='07 / Restore this unit, then repeat',action='Verify all remaining users, retire redundant piping and restore finishes. Then move to the next unit.',service='Pilot handover • remaining building work still to be planned',gate='Verify all remaining users before removing or abandoning old piping.',view='unit')]
ports=[]
for c in s['bathroom_pilot']['supply_connections']:
 ports.append(dict(id=c['fixture']+'-'+c['system'],fixture=c['fixture'],system=c['system'],port=c['port'],reference_route=c.get('connector') or c['drop'],status='assumed',basis='Concept tie point uses the bathroom study port, not a surveyed connection.'))
obj=dict(title='Highland / Proposed repipe sequence',status='assumed',strategy='Parallel installation followed by one-unit-at-a-time cutover',strategy_basis='User selected parallel new supply routes and one-unit-at-a-time cutover. Detailed staging, isolation feasibility and connection geometry remain assumed.',scope='Unit 107 domestic-water illustration with a five-fixture bathroom pilot. Building riser replacement, other units, material selection and final routing are not designed here.',source=dict(spec=str(base.relative_to(here.parents[3])),sha256=hashlib.sha256(base.read_bytes()).hexdigest(),drawings=['P4.01 Unit A / 107','A2.03 and A3.11 calibration references'],existing_status='Drawing-based reference; not verified installed conditions'),display_offset_m=[0,0,-.25],display_offset_basis='Graphic separation only, not a proposed 250 mm construction offset.',phases=phases,elements=elements,pilot_ports=ports,fixture_order=s['bathroom_pilot']['fixtures'],unit_roots={k.split(':')[1]:v for k,v in s['roots'].items() if k.startswith('unit:')},work_zone=dict(center=[-7.5,.035,-5.5],size=[5.4,.025,4.3],status='assumed',basis='Representative floor-protection graphic at the pilot. Actual access, staging, egress and protection limits require a site plan.'),limitations=['Proposed sequence only; no contractor-approved repipe plan supplied.','Reference pipes are not a verified existing-conditions survey.','The new routes reuse reference topology for explanation; they do not establish new routing or sizes.','Only nine pilot fixture tie points are explicit; other dwelling connections and building tie-ins are outside the demonstrated cutover.','Graphic pipe separation does not establish available clearance.','No material, test pressure, outage duration, valve location or shutdown boundary is specified.','New network acceptance is a required future step, not a test result.','Sanitary, vent, gas and fire protection are outside this illustration.'])
byid={e['reference_id']:e for e in elements}
assert len(byid)==len(elements)
assert len(ports)==9 and sum(p['system']=='CW' for p in ports)==5
for p in ports:
 e=byid[p['reference_route']]
 assert all(abs(a-b)<1e-4 for a,b in zip(e['points'][-1],p['port'])),p
assert [p['id'] for p in phases].index('test')<[p['id'] for p in phases].index('cutover')
(here/'repipe-strategy.json').write_text(json.dumps(obj,indent=2)+'\n')
print(f'{len(elements)} concept routes; nine matching pilot ports; separate proposed spec.')
