"""Create source-linked installation coordination specs; no field dimensions implied."""
import json, hashlib
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent
SOURCES = [
    {'id':'P4.01','page':15,'title':'Unit A / B domestic water plans','issue':'2007-10-29'},
    {'id':'P3.02','page':13,'title':'Domestic water risers and boiler piping','issue':'2007-10-29'},
    {'id':'P2.03','page':6,'title':'Level R1 plumbing plan','issue':'2007-10-29'},
    {'id':'P4.02','page':16,'title':'Unit S / R domestic water plans; Unit 302 annotation','issue':'2007-10-29'},
]
phases = [
 {'id':0,'title':'Verify and protect','caption':'Trace all three services and prove isolation before scheduling the outage.',
  'work':['Confirm current revision and field-route every service.','Record pressures, temperatures and circulation performance.','Agree affected residents, unit access and contingency service.','Protect finishes; keep the actual egress route clear.'],
  'gate':'No demolition release until current routes, service boundaries and access are documented.'},
 {'id':1,'title':'Open and prepare','caption':'Open only the verified service zones; prepare supports and penetrations.',
  'work':['Inspect suspect finishes before disturbance.','Make controlled openings after concealed-service checks.','Document rated assemblies and select compatible listed penetration details.','Confirm sufficient space for new piping alongside live CPVC; otherwise revise the outage plan.'],
  'gate':'Access locations, support strategy and penetration details accepted before rough-in.'},
 {'id':2,'title':'Install distribution','caption':'Build new cold, hot and circulation-return paths as an isolated network.',
  'work':['Install replacement distribution without connecting to the live system.','Follow the selected system instructions for joints, supports, movement and insulation.','Maintain hot-water return continuity; retain access to balancing components.','Verify each proposed route against the opened conditions.'],
  'gate':'Material, hydraulic sizes, support spacing and return routing approved before installation.'},
 {'id':3,'title':'Branch, cap and test','caption':'Complete new branches; cap test boundaries and inspect before concealment.',
  'work':['Route hot/cold branches to the source-plan fixture groups.','Keep the kitchen low-wall route visible for coordination.','Isolate meters, controls and equipment that cannot withstand the test.','Test using the adopted code and manufacturer procedure; document inspection results.'],
  'gate':'New isolated piping passes the specified test and required rough inspection; final tie-ins remain to be checked.'},
 {'id':4,'title':'Cut over and commission','caption':'Transfer service only within a field-proven isolation boundary.',
  'work':['Notify affected occupants and establish the approved outage.','Isolate supply and return paths; drain before cutting brittle CPVC.','Transfer service, preserve/reconnect metering and alarm-linked shutoffs as applicable.','Flush and disinfect where required; check final tie-ins and simultaneous demand.','Verify hot-water temperature, return balance and alarm/shutoff operation.'],
  'gate':'Safe service and circulation restored; final connections inspected; abandoned CPVC disconnected without live dead legs.'},
 {'id':5,'title':'Restore and hand over','caption':'Close walls after acceptance; retain access to service components.',
  'work':['Complete documented firestop and assembly restoration; inspect before covering.','Restore finishes and maintain required access panels.','Label isolation valves and document routes with preclosure photographs.','Deliver as-builts, test records, balancing results and warranties.'],
  'gate':'Final acceptance and owner handover complete; no untested joints concealed.'},
]
spec = {
 'project':'200 W Highland — repipe installation', 'model_type':'installation_coordination',
 'source_pdf':'../Highland-original.pdf',
 'source_sha256':hashlib.sha256((ROOT.parent/'Highland-original.pdf').read_bytes()).hexdigest(),
 'sources':SOURCES, 'units':'inches; converted to meters in Blender',
 'geometry_status':'assumed',
 'limitations':[
  'All new pipe positions, elevations, diameters, supports, openings and working areas are assumed coordination geometry, not a measured design.',
  'Plan trace follows the P4.01 Unit B / 106 drawing relationships. No dimension-string calibration is available; presentation scale must not be used for takeoff.',
  'The circulation-return termination and balancing connection are proposed and must be traced in the field.',
  'Fixture-group endpoints are diagram symbols, not individual fixture rough-ins or verified fixture counts.',
  'Replacement material, hydraulic sizing, isolation boundaries and outage durations remain undecided.',
  'The shared distribution scene is a schematic; stack positions do not locate actual chases or establish affected units.',
  'The project title is 200 West Highland Drive; the drawing location block reads 202 W Highland Drive, Seattle. Confirm address and governing revision.',
 ],
 'display':{'width_in':480,'height_in':442.1,'basis':'Arbitrary display mapping of source crop; not a physical building dimension.',
            'source_crop_normalized':[.51,.21,.89,.70],'image':'unit-b-plan.png'},
 'phases':phases,'elements':[]
}
E=spec['elements']
def add(e):
 e.setdefault('status','assumed')
 e.setdefault('basis','Proposed installation-method geometry; location, size and elevation require field verification.')
 e.setdefault('source','P4.01')
 E.append(e)
def line(eid,system,pts,phase,group,**kw):
 add(dict(id=eid,type='pipe',system=system,points=pts,phase=phase,collection=group,radius_in=1.4,**kw))
# X/Y follow normalized drawing coordinates; Z is a proposed elevation in inches.
# Routes are method diagrams, with visible pipe separation rather than sized offsets.
for system,dy in [('CW',-.008),('HW',.008)]:
 def p(x,y,z):return [x,y+dy,z]
 line(f'{system}-01',system,[p(.129,.11,66),p(.129,.11,84),p(.129,.322,84)],2,'02_Distribution',description='Unit service to high distribution junction')
 line(f'{system}-02',system,[p(.129,.322,84),p(.56,.322,84)],2,'02_Distribution',description='High route to far bathroom group')
 line(f'{system}-03',system,[p(.129,.322,84),p(.129,.54,84),p(.38,.54,84)],2,'02_Distribution',description='High route across west bathroom toward kitchen')
 line(f'{system}-04',system,[p(.38,.54,84),p(.38,.54,24),p(.38,.585,24),p(.5,.585,24)],3,'03_Branches',description='Kitchen low-wall supply; elevation assumed; source low-wall note retained')
line('HWC-01','HWC',[[.56,.330,84],[.56,.342,84],[.147,.342,84],[.147,.11,84],[.147,.11,66]],2,'02_Distribution',description='Proposed far-end circulation return to service assembly; termination/balance unverified')
fixtures=[
 ('F01','Laundry tray',[.18,.13,26],[.129,.18,84],['CW','HW']),
 ('F02','Washer box',[.11,.22,42],[.129,.22,84],['CW','HW']),
 ('F03','West bath / lavatory group',[.21,.35,26],[.21,.322,84],['CW','HW']),
 ('F04','West bath / tub',[.11,.49,26],[.129,.49,84],['CW','HW']),
 ('F05','West bath / WC',[.33,.55,12],[.33,.54,84],['CW']),
 ('F06','Far bath / lavatory group',[.49,.27,26],[.49,.322,84],['CW','HW']),
 ('F07','Far bath / shower',[.55,.40,48],[.55,.322,84],['CW','HW']),
 ('F08','Far bath / WC group',[.62,.40,12],[.55,.322,84],['CW']),
 ('F09','Kitchen sink + dishwasher',[.5,.585,24],[.5,.585,24],['CW','HW']),
 ('F10','Exterior hose bibb',[.644,.94,24],[.38,.54,84],['CW']),
]
for eid,label,end,start,systems in fixtures:
 add(dict(id=eid,type='terminal',label=label,at=end,phase=3,collection='04_Fixture_groups',systems=systems))
 if eid=='F09':continue
 for system in systems:
  dy=-.008 if system=='CW' else .008
  s=[start[0],start[1]+dy,start[2]];e=[end[0],end[1]+dy,end[2]]
  if eid=='F10':pts=[s,[.38,.625+dy,84],[.644,.625+dy,84],[.644,.94+dy,84],e]
  elif eid=='F08':pts=[s,[.62,.322+dy,84],[.62,.40+dy,84],e]
  else:pts=[s,[end[0],start[1]+dy,start[2]],[end[0],end[1]+dy,start[2]],e]
  pts=[pt for n,pt in enumerate(pts) if n==0 or pt!=pts[n-1]]
  line(f'{eid}-{system}',system,pts,3,'03_Branches',description=label+' supply; final individual fixture rough-ins not modeled')
for eid,label,rect in [
 ('A01','Service / meter access',[.095,.08,.19,.26]),
 ('A02','High distribution access',[.115,.295,.59,.347]),
 ('A03','West wet-wall access',[.105,.345,.16,.56]),
 ('A04','Kitchen low-wall access',[.36,.53,.53,.61]),
 ('A05','Exterior branch access',[.62,.61,.67,.95]),
]:add(dict(id=eid,type='access',label=label,rect=rect,phase=1,collection='01_Access'))
add(dict(id='P01',type='protection',label='Proposed protected work approach',rect=[.32,.64,.55,.81],phase=0,collection='00_Protection',basis='Illustrative work protection footprint only; actual entry and egress not established.'))
add(dict(id='SVC01',type='assembly',at=[.13,.105,66],label='CW / HW / HWC service assembly',phase=4,collection='05_Service_assembly',basis='P4.01 identifies unit shutoffs, water meter, circulation return and alarm-linked solenoid. Proposed assembly spacing/order are schematic; verify actual devices.'))
add(dict(id='TEST01',type='test',at=[.13,.08,66],phase=3,collection='06_Test_boundary',label='Isolated new network test point',basis='Illustrative gauge and capped test boundary; pressure, duration and medium must be specified by code/manufacturer.'))
for i,at in enumerate([[.129,.27,84],[.3,.322,84],[.5,.322,84],[.129,.46,84],[.3,.54,84]]):
 add(dict(id=f'SUP-{i+1:02}',type='support',at=at,size_in=[5,18,2],phase=1,collection='08_Support_symbols',basis='Support coordination symbol only; count, anchorage and spacing not designed.'))
ports=[{'system':'CW','at':next(e for e in E if e['id']=='CW-01')['points'][0]},
       {'system':'HW','at':next(e for e in E if e['id']=='HW-01')['points'][0]},
       {'system':'HWC','at':next(e for e in E if e['id']=='HWC-01')['points'][-1]}]
for e in E:
 if e['type'] in ['assembly','test']:e['ports']=ports
spec['checks']=[
 {'id':'source_checksum','description':'Original supplied PDF checksum matches the owner-atlas manifest.','source':'Original file and source-manifest.json'},
 {'id':'systems','expected':['CW','HW','HWC'],'source':'P4.01 service callout and P3.02 water riser diagram'},
 {'id':'unique_ids','description':'Each modeled coordination element has one stable ID.','basis':'Model integrity'},
 {'id':'connectivity','description':'Every supply branch reaches its same-system distribution network; HWC links proposed HW far end to return service.','basis':'Model integrity; proposed topology only'},
]
spec['shared_distribution']={
 'source':'P3.02','status':'assumed',
 'basis':'Schematic display coordinates only. Header topology and review labels follow the source; physical sizes, levels served and isolation are unverified.',
 'header_extent_in':[-310,310], 'header_z_in':24, 'riser_height_in':270,
 'system_offsets_in':{'CW':0,'HW':12,'HWC':24},
 'stacks':[{'label':"'01",'x_in':-240},{'label':"'03",'x_in':-120},{'label':"'02",'x_in':0},{'label':"'04",'x_in':120},{'label':"'05",'x_in':240}],
 'auxiliary_stubs':[
  {'id':'SH-106','label':'106 / 107','x_in':-290,'systems':['CW','HW','HWC']},
  {'id':'SH-IRR','label':'Irrigation / 101','x_in':-70,'systems':['CW']},
  {'id':'SH-AUX','label':'Garage / trash','x_in':70,'systems':['CW']},
  {'id':'SH-COMMON','label':'Fitness / janitor','x_in':280,'systems':['CW','HW']},
 ],
 'source_notes':[
  {'id':'EX01','text':'Units 106 / 107: separate source-diagram tie-in; do not assign to a numbered stack without tracing.','source':'P3.02 review annotation'},
  {'id':'EX02','text':'Irrigation room drop through Unit 101: trace cold-water continuity and access.','source':'P3.02 review annotation'},
  {'id':'EX03','text':"Fitness room / janitor: review annotation associates these with '05 stack; verify service boundary.",'source':'P3.02 review annotation'},
  {'id':'EX04','text':'Garage hose bibbs and trash room: account for auxiliary services during cutover.','source':'P3.02 review annotation'},
  {'id':'EX05','text':'Unit 302: source note places the connection on the other wall; exclude automatic typical-route replication.','source':'P4.02 review annotation'},
 ]}
(ROOT/'highland-installation-proposed.yaml').write_text(yaml.safe_dump(spec,sort_keys=False,allow_unicode=True))
(ROOT/'installation-data.json').write_text(json.dumps(spec,indent=2))
existing={'project':spec['project'],'model_type':'existing_source_reference','source_sha256':spec['source_sha256'],
 'sources':SOURCES,'status':'confirmed','scope':'Unchanged drawing pixels and source annotations only; no existing CPVC route, dimension, valve condition or isolation boundary asserted.',
 'reference_images':['unit-b-plan.png','risers-200dpi.png','unit-b-service.png'],
 'field_report':{'material':'CPVC','condition':'failing','source':'User report in this conversation; not independently inspected.'}}
(ROOT/'highland-installation-existing-reference.yaml').write_text(yaml.safe_dump(existing,sort_keys=False,allow_unicode=True))
print('Wrote proposed spec:',len(E),'elements;',len(phases),'phases. Existing reference kept separate.')
