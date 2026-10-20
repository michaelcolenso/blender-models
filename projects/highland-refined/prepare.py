"""Record a conservative revision of the visible south facade.

The inherited elevation projection clips several south openings onto the wrong
plan returns. Reassign the front bays by plan topology, retaining the dimensioned
grid and floor datums. Exact jamb offsets remain assumed; no fit tolerance is
claimed. Rear/north conflicts that cannot be resolved from the available crops
remain in the rejected-candidate ledger.
"""
import copy
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
s=json.loads((ROOT/'projects/highland-exterior/exterior.spec.json').read_text())
original=copy.deepcopy(s)
changes=[]

def assign(level,col,segment,center=None,width=None):
    ident=f'south-{level}-{col:02}'
    e=next((e for e in s['openings'] if e['id']==ident),None)
    restored=e is None
    old=copy.deepcopy(e)
    if e is None:
        # Restore only candidates explicitly present in the original elevation
        # takeoff. Retain the same source pixels and standardized sill/head basis.
        candidates={5:(1104,1164,'wide'),7:(1250,1286,'window'),11:(1503,1515,'window'),4:(1103,1163,'wide')}
        p0,p1,kind=candidates[col]
        z=next(x['z'] for x in s['levels'] if x['name']==level)
        e={'id':ident,'face':'south','level':level,'polygon':'r1' if level in ('P1','R1') else 'typical','source_pixels':[p0,p1],'kind':kind,'source_width_in':120 if col==5 else 92,'z':z+(20 if level=='P1' else 9),'height':72 if level=='P1' else 90,'source':'A3.01 / 01 south elevation; A2.03/A2.04 registered south plan returns'}
        s['openings'].append(e)
    a,b=(s['polygons'][e['polygon']][segment],s['polygons'][e['polygon']][(segment+1)%len(s['polygons'][e['polygon']])])
    lo,hi=sorted((a[0],b[0]));assert abs(a[1]-b[1])<.01 and b[0]<a[0]
    c=center if center is not None else (lo+hi)/2
    w=width or e.get('source_width_in',92)
    assert lo+5<c-w/2 and c+w/2<hi-5,(ident,lo,hi,c,w)
    e.update(segment=segment,u=round(c,3),width=round(w,3),plan_depth_in=a[1],status='assumed',xy_status='provisional',basis='Visible front bay reassigned by A2.03/A2.04 plan-return topology and A3.01 opening order. Exact jamb offsets and sill/head geometry remain assumed. Local correction does not establish a single dimensional tolerance.')
    changes.append({'id':ident,'action':'restored source candidate' if restored else 'reassigned/widened within plan bay','old':old,'new':copy.deepcopy(e)})
    if restored:
        s['rejected_candidates']=[r for r in s['rejected_candidates'] if not(r['level']==level and r['face']=='south' and r['pixels']==e['source_pixels'])]

for level in ('R1','R2','R3','R4'):
    poly=s['polygons']['r1' if level=='R1' else 'typical']
    assign(level,5,20)
    assign(level,6,18)
    center=(poly[16][0]+poly[17][0])/2
    assign(level,7,16,center-70,88)
    assign(level,8,16,center+70)
    assign(level,9,14)
    assign(level,10,12)
    # The narrow outboard return also appears in the east plan/elevation. Width
    # is constrained by the registered return and remains an assumption.
    assign(level,11,10,width=24)
assign('P1',4,20,width=112)
for col,segment,offset,width in [(5,18,0,60),(6,16,-70,88),(7,16,70,58),(8,14,0,64),(9,12,0,106)]:
    poly=s['polygons']['r1'];c=(poly[segment][0]+poly[(segment+1)%len(poly)][0])/2+offset
    assign('P1',col,segment,c,width)

s['continuous_floor_bands']=False
s['guard_infill_rows']=10
s['wide_window_center_pane']=True
s['project']='200 W. Highland / visible-facade revision'
s['revision_basis']={'source':'Owner photo-02; A2.03/A2.04 registered outlines; A3.01 south/east elevation crops','scope':'Front south bays, continuous floor-edge appearance, wide-window divisions and balcony infill character.','limits':'Exact opening offsets remain assumed. Ten rail rows and section sizes interpret the drawing character; they are not a verified guard schedule. Building grid, story heights, roof/parapet datums and footprint are unchanged.'}
s['limitations'].append('Visible front bays have been reassigned within the registered plan topology; their exact opening offsets remain assumed. Rear/north omitted candidates remain unresolved.')
(HERE/'exterior-revised.spec.json').write_text(json.dumps(s,indent=2)+'\n')
report={'base_openings':len(original['openings']),'revised_openings':len(s['openings']),'restored_candidates':sum(x['action'].startswith('restored') for x in changes),'remaining_unresolved':len(s['rejected_candidates']),'geometry_changes':changes,'appearance_changes':['Remove continuous pale floor bands through brick fields, per photo-02. Window sills and main roof cornices remain.','Interpret denser horizontal balcony infill from A3.01; sections/spacing assumed.','Wide windows use a broad central pane with narrow side lights, per A3.01.'],'protected_controls':['Registered plan polygons','Dimensioned grid spans','Floor elevations','Roof/parapet top datums']}
for key in ('polygons','levels','grid_dimensions_in','roof_features','roof_plate_z','north_roof_plate_z'):
    assert s[key]==original[key],key
(HERE/'revision-ledger.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ('geometry_changes',)},indent=2))
