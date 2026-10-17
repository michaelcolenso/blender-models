"""Record the R1 lobby / corridor flight against the exterior study."""
from pathlib import Path
import json,hashlib

H=Path(__file__).parent
ext=json.loads((H.parent/'highland-exterior/exterior.spec.json').read_text())
entry=next(o for o in ext['openings'] if o['id']=='east-R1-08')
assert entry['kind']=='entry' and entry['level']=='R1' and entry['face']=='east'
assert entry['width']>120 and abs(entry['u']-1332.612)<.01
assert entry['z']==132 and ext['levels'][1]['z']==132
# Inches in the exterior coordinate system: x east, y north, z above P1.
# The lobby and corridor rectangles are manually digitized, then rounded to
# the plan's explicit 6'-0" corridor callout. They are not surveyed walls.
rooms={
 'lobby-110':{'bounds_in':[1120,1475,1260,1405],'source':'A2.03 R1 plan: Lobby 110 and east glazed entry','status':'provisional'},
 'lobby-link':{'bounds_in':[951,1120,1296,1368],'source':'A2.03 R1 plan: connector east of elevator core','status':'provisional'},
 'corridor-108':{'bounds_in':[879,951,670,1540],'source':'A2.03 R1 plan: Corridor 108, 6-foot callout','status':'provisional'},
 'corridor-208':{'bounds_in':[879,951,670,1540],'source':'A2.04 R2 plan: Corridor 208; registered to the same dimensioned grids','status':'provisional'},
}
flight=[
 {'t':0,'xyz_ft':[190,20,48],'cue':'Approach / southeast corner'},
 {'t':3.2,'xyz_ft':[165,92,25],'cue':'Align with east lobby glazing'},
 {'t':5.7,'xyz_ft':[125,111,17],'cue':'Dive toward glazing'},
 {'t':6.5,'xyz_ft':[119,111,16.3],'cue':'Inside Lobby 110'},
 {'t':8.8,'xyz_ft':[92,111,16.3],'cue':'Lobby connector'},
 {'t':10.5,'xyz_ft':[76.5,112,16.3],'cue':'Corridor 108 / elevator core'},
 {'t':12,'xyz_ft':[76.5,126,16.3],'cue':'Elevator bank'},
 {'t':13.2,'xyz_ft':[76.5,121,16.3],'cue':'Turn toward Elevator M1'},
 {'t':14.3,'xyz_ft':[73.5,121,16.3],'cue':'Elevator doorway'},
 {'t':15.3,'xyz_ft':[70.8,121,16.3],'cue':'Inside elevator'},
 {'t':16,'xyz_ft':[70.8,121,16.3],'cue':'Elevator doors close'},
 {'t':17.8,'xyz_ft':[70.8,121,26.55],'cue':'Rise to R2'},
 {'t':18.5,'xyz_ft':[70.8,121,26.55],'cue':'Elevator doors open'},
 {'t':19.7,'xyz_ft':[76.5,121,26.55],'cue':'Corridor 208'},
 {'t':22,'xyz_ft':[76.5,100,26.55],'cue':'Corridor 208 south'},
 {'t':26,'xyz_ft':[76.5,61,26.55],'cue':'Stair M1 vicinity on R2'},
]
spec={
 'project':'200 W. Highland / lobby and main corridors drone shot',
 'source_pdf_sha256':ext['source_pdf_sha256'],
 'source_sheets':['A2.03 R1 floor plan','A2.04 R2 floor plan','A3.01 east elevation'],
 'exterior_entry_id':entry['id'],
 'entry_opening_in':{'x':entry['plan_depth_in'],'y':entry['u'],'width':entry['width'],'bottom':entry['z'],'height':entry['height']},
 'r1_floor_z_in':132,
 'r2_floor_z_in':255,
 'corridor_width_in':72,
 'corridor_width_status':'confirmed on A2.03 6-foot callout; local modeled wall faces remain provisional',
 'rooms':rooms,'waypoints':flight,
 'assumptions':[
  'The flight crosses the exterior model\'s broad east R1 glazed entry opening. The drawing calls this the lobby entrance; window/door subdivision is not resolved.',
  'Room and wall boxes are a rounded manual interpretation of A2.03; no dimensional tolerance established.',
  'Corridor floor, ceiling, doors, elevator fronts and lighting are illustrative. Ceiling clear height is assumed 8.5 feet.',
  'The flight path is a presentation camera path, not a route or accessibility survey.',
  'The elevator car and its door timing are illustrative; no manufacturer or control sequence is documented here.',
  'No tenant interiors or concealed building systems are depicted.'
 ]
}
assert all(flight[i]['t']<flight[i+1]['t'] for i in range(len(flight)-1))
assert all(rooms[n]['bounds_in'][1]-rooms[n]['bounds_in'][0]==72 for n in ['corridor-108','corridor-208'])
assert abs(flight[3]['xyz_ft'][1]*12-entry['u'])<2
(H/'flight.spec.json').write_text(json.dumps(spec,indent=2)+'\n')
print('R1 lobby entrance and Corridors 108/208 flight prepared.')
