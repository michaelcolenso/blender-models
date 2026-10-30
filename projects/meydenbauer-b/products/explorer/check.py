from __future__ import annotations
import json
from pathlib import Path
HERE=Path(__file__).parent; ROOT=HERE.parents[3]
state=json.loads((ROOT/'projects/meydenbauer-b/state/project-state.json').read_text()); schedule=json.loads((ROOT/'projects/meydenbauer-b/products/underslab/meydenbauer-b.schedule.json').read_text()); projection=json.loads((HERE/'time-state.json').read_text()); app=(HERE/'app.js').read_text(); html=(HERE/'index.html').read_text(); errors=[]
def need(ok,msg):
    if not ok: errors.append(msg)
need(state.get('schema_version')=='0.1.0','unexpected CIE schema')
need(len(state.get('scenarios',[]))>=3,'S1/S2/S3 scenarios missing')
qs={(q.get('scenario_id'),q.get('measure')):q.get('value') for q in state.get('quantities',[])}
s2=qs.get(('meydenbauer-b:scenario:s2','slab_cut')); s3=qs.get(('meydenbauer-b:scenario:s3','slab_cut'))
allowance=next((c.get('value') for c in state.get('claims',[]) if c.get('predicate')=='slab_allowance'),None)
need(s2==686.0,'S2 slab decision regression'); need(s3==991.0,'S3 slab decision regression'); need(allowance==700,'700 SF allowance claim missing')
need(schedule.get('working_days')==81.5,'working-day baseline regression'); need(schedule.get('order')==['B-103','B-102','B-101','B-104'],'unit sequence regression'); need(len(schedule.get('phases',[]))==8,'eight construction phases required')
need(projection.get('working_days')==schedule.get('working_days'),'projection baseline must match schedule')
need(projection.get('order')==schedule.get('order'),'projection order must match schedule')
for sid in ['meydenbauer-b:scenario:s1','meydenbauer-b:scenario:s2','meydenbauer-b:scenario:s3']:
    p=projection['scenarios'][sid]; need(p['slab_cut_sf']==qs[(sid,'slab_cut')],f'{sid} slab projection drift'); need(p['excavation_bank_cy']==qs[(sid,'excavation_bank')],f'{sid} excavation projection drift'); need(p['allowance_sf']==allowance,f'{sid} allowance projection drift')
need(projection['scenarios']['meydenbauer-b:scenario:s2']['projected_working_days']==81.5,'S2 duration must equal schedule baseline')
need(projection['scenarios']['meydenbauer-b:scenario:s3']['projected_working_days']>81.5,'S3 depth risk must propagate to duration')
for token in ['cie_id','GLTFLoader','Raycaster','related(el)','scenario_id','slab_allowance','data-mode="evidence"','data-mode="risk"','data-mode="time"','time-slider','activeAt(day)','scenarioQuantity','propagation-line','schedule.working_days','time-state.json','projected_working_days']: need(token in app or token in html,f'Explorer wiring missing: {token}')
for forbidden in ['686.0','991.0','700 SF','90.96']: need(forbidden not in app,f'duplicated canonical value in app.js: {forbidden}')
if errors: raise SystemExit('EXPLORER CHECK FAILED\n- '+'\n- '.join(errors))
print(f'EXPLORER CHECK PASS — S2 {s2} SF / {projection["scenarios"]["meydenbauer-b:scenario:s2"]["projected_working_days"]} d; S3 {s3} SF / {projection["scenarios"]["meydenbauer-b:scenario:s3"]["projected_working_days"]} d')
