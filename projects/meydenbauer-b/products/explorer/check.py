from __future__ import annotations
import json
from pathlib import Path
HERE=Path(__file__).parent; ROOT=HERE.parents[3]
state=json.loads((ROOT/'projects/meydenbauer-b/state/project-state.json').read_text()); app=(HERE/'app.js').read_text(); html=(HERE/'index.html').read_text(); errors=[]
def need(ok,msg):
    if not ok: errors.append(msg)
need(state.get('schema_version')=='0.1.0','unexpected CIE schema')
need(len(state.get('scenarios',[]))>=3,'S1/S2/S3 scenarios missing')
qs={(q.get('scenario_id'),q.get('measure')):q.get('value') for q in state.get('quantities',[])}
s2=qs.get(('meydenbauer-b:scenario:s2','slab_cut')); s3=qs.get(('meydenbauer-b:scenario:s3','slab_cut'))
allowance=next((c.get('value') for c in state.get('claims',[]) if c.get('predicate')=='slab_allowance'),None)
need(s2==686.0,'S2 slab decision regression'); need(s3==991.0,'S3 slab decision regression'); need(allowance==700,'700 SF allowance claim missing')
need(s2 is not None and allowance is not None and s2<=allowance,'S2 should remain inside allowance'); need(s3 is not None and allowance is not None and s3>allowance,'S3 should exceed allowance')
for token in ['cie_id','GLTFLoader','Raycaster','related(el)','scenario_id','slab_allowance','data-mode="evidence"','data-mode="risk"']: need(token in app or token in html,f'Explorer wiring missing: {token}')
for forbidden in ['686.0','991.0','700 SF']: need(forbidden not in app,f'duplicated decision value in app.js: {forbidden}')
if errors: raise SystemExit('EXPLORER CHECK FAILED\n- '+'\n- '.join(errors))
print(f'EXPLORER CHECK PASS — {len(state.get("scenarios",[]))} scenarios; allowance {allowance} SF; S2 {s2} SF; S3 {s3} SF')
