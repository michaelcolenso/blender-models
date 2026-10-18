"""Record the R1 lobby / corridor flight against the exterior study."""
from pathlib import Path
import json,hashlib

H=Path(__file__).parent
ext=json.loads((H.parent/'highland-exterior/exterior.spec.json').read_text())
osm=json.loads((H/'osm-buildings-source.json').read_text())
subject=next(e for e in osm['elements'] if e['id']==231753705)
lat0,lon0=47.629745,-122.3594891
def local_point(v):
 return [(v['lon']-lon0)*75100,(v['lat']-lat0)*111195]
subject_points=[local_point(v) for v in subject['geometry']]
shift_x=1.3-min(p[0] for p in subject_points)
shift_y=.15-min(p[1] for p in subject_points)
context=[]
for element in osm['elements']:
 if element['id']==subject['id'] or 'geometry' not in element:continue
 points=[[round(p[0]+shift_x,2),round(p[1]+shift_y,2)] for p in map(local_point,element['geometry'])]
 if len(points)>1 and points[0]==points[-1]:points.pop()
 if len(points)<3:continue
 cx=sum(p[0] for p in points)/len(points);cy=sum(p[1] for p in points)/len(points)
 if (cx-19)**2+(cy-23)**2>145**2:continue
 tags=element.get('tags',{})
 try:levels=max(1,min(12,float(tags.get('building:levels','3'))))
 except ValueError:levels=3
 context.append({'osm_id':element['id'],'footprint_m':points,'height_m':round(levels*3.05,2)})
assert len(context)>=40
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
 {'t':12.5,'xyz_ft':[76.5,120.4,16.3],'cue':'Centered at Elevator M1 opening'},
 {'t':14.3,'xyz_ft':[73.5,121,16.3],'cue':'Elevator doorway'},
 {'t':15.3,'xyz_ft':[70.8,121,16.3],'cue':'Inside elevator'},
 {'t':16,'xyz_ft':[70.8,121,16.3],'cue':'Elevator doors close'},
 {'t':17.8,'xyz_ft':[70.8,121,26.55],'cue':'Rise to R2'},
 {'t':18.5,'xyz_ft':[70.8,121,26.55],'cue':'Elevator doors open'},
 {'t':19.7,'xyz_ft':[76.5,119.5,26.55],'cue':'Corridor 208'},
 {'t':22,'xyz_ft':[76.5,100,26.55],'cue':'Corridor 208 south'},
 {'t':26,'xyz_ft':[76.5,61,26.55],'cue':'Stair M1 vicinity on R2'},
]
# Cubic Bezier controls keep the camera inside public circulation. The turn
# from Lobby 110 into Corridor 108 occurs after x enters the 6-foot hallway;
# the elevator approach turns west only at its modeled doorway opening.
controls=[
 ([190,49,45],[177,82,29]),
 ([156,101,23],[134,111,18]),
 ([123,111,16.5],[121,111,16.3]),
 ([110,111,16.3],[100,111,16.3]),
 ([87,111,16.3],[76.5,111,16.3]),
 ([76.5,115,16.3],[76.5,118.5,16.3]),
 ([76.5,121,16.3],[74.6,121,16.3]),
 ([72.6,121,16.3],[71.6,121,16.3]),
 ([70.8,121,16.3],[70.8,121,16.3]),
 ([70.8,121,18.5],[70.8,121,24.35]),
 ([70.8,121,26.55],[70.8,121,26.55]),
 ([73,121,26.55],[76.5,121,26.55]),
 ([76.5,113,26.55],[76.5,106,26.55]),
 ([76.5,91,26.55],[76.5,70,26.55]),
]
assert len(controls)==len(flight)-1
curves=[{'t0':a['t'],'t1':b['t'],'p0':a['xyz_ft'],'p1':c1,'p2':c2,'p3':b['xyz_ft']}
        for (a,b),(c1,c2) in zip(zip(flight,flight[1:]),controls)]
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
 'rooms':rooms,'waypoints':flight,'camera_bezier_segments':curves,
 'osm_context':{'attribution':'© OpenStreetMap contributors (ODbL 1.0)','subject_way_id':subject['id'],
                'source':'Overpass building footprints within 170 m of 200 W. Highland',
                'source_sha256':hashlib.sha256((H/'osm-buildings-source.json').read_bytes()).hexdigest(),
                'position_status':'registered approximately to the architectural exterior footprint',
                'height_status':'building:levels × 3.05 m where mapped; 3 levels assumed otherwise',
                'buildings':context},
 'assumptions':[
  'The flight crosses the exterior model\'s broad east R1 glazed entry opening. The drawing calls this the lobby entrance; window/door subdivision is not resolved.',
  'Room and wall boxes are a rounded manual interpretation of A2.03; no dimensional tolerance established.',
  'Corridor floor, ceiling, doors, elevator fronts and lighting are illustrative. Ceiling clear height is assumed 8.5 feet.',
  'The flight path is a presentation camera path, not a route or accessibility survey.',
  'Bezier camera controls are constrained to the modeled public corridors and elevator opening, not a measured clearance survey.',
  'The elevator car and its door timing are illustrative; no manufacturer or control sequence is documented here.',
  'No tenant interiors or concealed building systems are depicted.',
  'OSM neighborhood footprints are approximate context; their heights and registration are not surveyed.'
 ]
}
assert all(flight[i]['t']<flight[i+1]['t'] for i in range(len(flight)-1))
assert all(rooms[n]['bounds_in'][1]-rooms[n]['bounds_in'][0]==72 for n in ['corridor-108','corridor-208'])
assert abs(flight[3]['xyz_ft'][1]*12-entry['u'])<2
(H/'flight.spec.json').write_text(json.dumps(spec,indent=2)+'\n')
print('R1 lobby entrance and Corridors 108/208 flight prepared.')
