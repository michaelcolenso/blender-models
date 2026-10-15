"""Explicit drawing takeoff + assumed presentation coordinates. All dimensions in inches.

This is a separate manual takeoff workflow: the house extractor does not support
this scanned, multistory source. No raster coordinates are claimed as measurements.
"""
from pathlib import Path
import json, hashlib

HERE = Path(__file__).parent
CAL=json.loads((HERE/'calibration.json').read_text())
elements = []
def element(id, scene, kind, **kw):
    obj = dict(id=id, scene=scene, kind=kind, status='assumed',
        basis='Presentation geometry: routing coordinates, elevations, external envelopes and fitting shapes are not field measured.', **kw)
    elements.append(obj)
    return obj
def pipe(id, scene, system, points, size, source, size_status='confirmed', terminal=False, **kw):
    return element(id,scene,'pipe',system=system,points=points,nominal_in=size,
        size_status=size_status,source=source,terminal=terminal,
        size_basis=('Explicit nominal size callout' if size_status=='confirmed' else 'Representative continuation; drawing refers to unit plans for sizing'), **kw)
def label(id, scene, at, text, size=12):
    element(id,scene,'label',at=at,text=text,size=size,system='context')
def box(id,scene,at,dims,system='context',**kw):
    element(id,scene,'box',at=at,dims=dims,system=system,**kw)
def tank(id,scene,at,radius,height,source,role):
    element(id,scene,'tank',at=at,radius=radius,height=height,system='equipment',source=source,role=role,count_status='confirmed')
S='P3.02 / domestic water riser diagram (PDF page 13)'
B='P3.02 / detail 1, low temp boiler piping diagram, SCALE NONE (PDF page 13)'
U='P4.01 / Unit A 107 domestic water plan (PDF page 15)'
floor_z={k:round((v-332)*12,3) for k,v in CAL['floor_elevations_ft'].items()}
levels=list(floor_z.items())+[('PLATE',round((CAL['plate_reference_ft']-332)*12,3))]
systems=['CW','HW','HWC']
offsets={'CW':-10,'HW':0,'HWC':10}
roots={}
for name,z in levels:
    # Floor edges only: no drawing sheets and no pretend architectural model.
    for k,(a,b) in enumerate([((-235,-310),(235,-310)),((235,-310),(235,310)),((235,310),(-235,310)),((-235,310),(-235,-310))]):
        element(f'floor-{name}-{k}','building','pipe',system='context',points=[[a[0],a[1],z],[b[0],b[1],z]],nominal_in=0.5,size_status='assumed',size_basis='Level datum line',source=S)
    label('level-'+name,'building',[250,-310,z+4],name,16)
    for e in elements[-5:]:
        e['datum_status']='confirmed';e['datum_elevation_ft']=CAL['plate_reference_ft'] if name=='PLATE' else CAL['floor_elevations_ft'][name]
        e['datum_source']=CAL['elevation_source']
stacks=[('01',130,-240,[0,1,2,3,4]),('02',-130,-240,[0,1,2,3,4]),('03',-130,0,[0,1,2,3]),('04',-130,240,[1,2,3,4]),('05',130,240,[0,1,2,3,4])]
hz=floor_z['R1']+104
for sys in systems:
    dx=offsets[sys]
    root=[-340,340+dx,floor_z['P1']+94]
    roots['building:'+sys]=root
    pipe('plant-to-building-'+sys,'building',sys,[root,[-270,340+dx,root[2]],[-270,340+dx,hz],[dx,340+dx,hz],[dx,300,hz]],{'CW':4,'HW':3,'HWC':1.5}[sys],S)
    # Continuous header; graph validator recognizes tees on straight segments.
    pipe('distribution-main-'+sys,'building',sys,[[dx,300,hz],[dx,-270,hz]],{'CW':3,'HW':3,'HWC':1.25}[sys],S)
    for tag,x,y,branches in stacks:
        sx=x+dx
        pipe(f'{tag}-base-{sys}','building',sys,[[dx,y,hz],[sx,y,hz]],{'CW':2,'HW':2,'HWC':.75}[sys],S)
        last=hz
        branch_heights=[floor_z['R'+str(i+1)]+104 for i in branches]
        for i,z in enumerate(sorted(set([hz]+branch_heights))):
            if z>last:
                top=z==branch_heights[-1]
                d=({'CW':1,'HW':1,'HWC':.5} if top else {'CW':2,'HW':1.5 if z>floor_z['R3'] else 2,'HWC':.75})[sys]
                pipe(f'{tag}-riser-{sys}-{i}','building',sys,[[sx,y,last],[sx,y,z]],d,S)
            last=z
        for level,z in zip(branches,branch_heights):
            end=[sx+(65 if x>0 else -65),y,z]
            pipe(f'{tag}-R{level+1}-branch-{sys}','building',sys,[[sx,y,z],end],.5 if sys=='HWC' else 1,S,'assumed',True,role='unit branch continuation')
        if sys=='HW':
            label('stack-'+tag,'building',[x-15,y,branch_heights[-1]+32],"STACK "+tag,14)
    # Separate paired service to Units 106 / 107, not a copied typical riser.
    pipe('106-107-drop-'+sys,'building',sys,[[dx,-100,hz],[80+dx,-100,hz],[80+dx,-100,floor_z['P1']+104],[80+dx,-155,floor_z['P1']+104]],{'CW':1.5,'HW':1.25,'HWC':.75}[sys],S,terminal=True,role='106 / 107 continuation')
label('106-107','building',[80,-170,floor_z['P1']+74],'106 / 107',12)
label('scope','building',[-230,-360,20],'DOMESTIC WATER  /  FIVE STACK GROUPS',14)

# Mechanical plant is shown separately at a readable scale. Deliberately no
# invisible joins between cold, heated water and return in the graph validator.
# The schematic has internal mixing and recirculation; device internals are omitted.
for i,x in enumerate([-70,70],1):
    tank('B'+str(i),'plant',[x,90,8],24,76,B,'boiler')
    tank('ST'+str(i),'plant',[x,-80,8],29,88,B,'storage tank')
    box('boiler-pad-'+str(i),'plant',[x,90,4],[65,65,8],source=B)
    box('tank-pad-'+str(i),'plant',[x,-80,4],[70,70,8],source=B)
    label('boiler-label-'+str(i),'plant',[x-14,60,55],'B'+str(i),10)
    label('tank-label-'+str(i),'plant',[x-18,-112,55],'ST'+str(i),10)
    # Charging outlet (hot) and pump inlet (recirculated water) ports.
    pipe('boiler-out-'+str(i),'plant','HW',[[x,64,65],[x,20,65],[x,20,105]],2,B)
    pipe('boiler-in-'+str(i),'plant','HWC',[[x,64,25],[x,48,25],[x,48,16],[x,-20,16]],2,B)
    element('CP'+str(i),'plant','pump',at=[x,48,25],system='HWC',source=B,role='factory boiler pump',count_status='confirmed')
    pipe('storage-charge-'+str(i),'plant','HW',[[x,20,105],[x,-35,105],[x,-35,35],[x,-50,35]],2.5,B,terminal=True)
    pipe('storage-return-'+str(i),'plant','HWC',[[x,-50,20],[x,-20,20],[x,-20,16]],2.5,B,terminal=True)
    pipe('storage-hot-'+str(i),'plant','HW',[[x,-80,96],[x,-80,124],[x,-130,124]],2.5,B,terminal=True)
    # Expansion vessels: external envelopes are explicitly assumed.
    tank('ET'+str(i),'plant',[x+40,90,45],9,25,B,'expansion vessel')
    pipe('ET-boiler-'+str(i),'plant','HW',[[x,64,65],[x+40,64,65],[x+40,90,65]],.75,B,'assumed')
    tank('ET'+str(i+2),'plant',[x+40,-80,8],11,34,B,'expansion vessel')
    pipe('ET-storage-'+str(i),'plant','HWC',[[x,-20,16],[x+40,-20,16],[x+40,-80,16]],.75,B,'assumed')
pipe('charge-header','plant','HW',[[-140,20,105],[110,20,105]],3,B)
pipe('cold-injection','plant','CW',[[-180,20,105],[-140,20,105]],3,B,terminal=True)
pipe('hot-header','plant','HW',[[-180,-130,124],[110,-130,124]],3,B)
pipe('return-header','plant','HWC',[[-180,-20,16],[110,-20,16]],1.5,B)
element('WAC1','plant','pump',at=[-140,-20,16],system='HWC',source=B,role='circulation pump; WAC2 is the loose spare',count_status='confirmed')
label('cold-label','plant',[-200,20,126],'COLD IN',10)
label('hot-label','plant',[-200,-130,143],'HOT OUT',10)
label('return-label','plant',[-200,-20,36],'RETURN',10)
label('plant-heading','plant',[-170,-180,3],'BOILERS + STORAGE',12)

# Unit A plan trace. XY coordinates reference the displayed P4.01 crop;
# conversion is PROVISIONAL, calibrated through the shared structural grid.
# Pipe heights are assigned 102 in overhead; island route -6 in underfloor.
def p(x,y,z=102): return [round((x-900)*CAL['unit_xy_in_per_normalized_pixel'],5),round((700-y)*CAL['unit_xy_in_per_normalized_pixel'],5),z]
def route(id,sys,coords,size=.5,terminal=False,assumed=False):
    return pipe(id,'unit',sys,[p(*c) for c in coords],size,U,'assumed' if assumed else 'confirmed',terminal)
roots['unit:CW']=p(1450,180)
roots['unit:HW']=p(1450,200)
roots['unit:HWC']=p(1430,245)
route('A-cold-master','CW',[(1450,180),(110,180)],1)
route('A-hot-master','HW',[(1450,200),(110,200)],1)
route('A-cold-lavs','CW',[(165,180),(165,335),(400,335)],.5)
route('A-hot-bath-loop','HW',[(110,200),(165,200),(165,350),(820,350),(820,245),(1390,245)],.75)
route('A-bath-return-link','HWC',[(1390,245),(1430,245)],.5)
route('A-cold-spine','CW',[(1395,180),(1395,645),(1590,645),(1590,875)],.75)
route('A-hot-spine','HW',[(1410,200),(1410,665),(1570,665),(1570,875)],.75)
route('A-return-spine','HWC',[(1430,245),(1430,685),(1550,685),(1550,875),(1570,875)],.5)
route('A-lower-lav-cold','CW',[(1590,875),(1510,875)],.5)
route('A-lower-lav-hot','HW',[(1570,875),(1525,875)],.5)
route('A-hosebib-trunk','CW',[(1395,645),(1395,770),(1055,770),(1055,1270),(1055,1270,26)],.75,True)
# Fixture envelopes: equipment symbols determine type and rough relation only.
fixtures=[
 ('master-shower','shower',165,165,'SH2'),('master-bath','bath',335,170,'BT1'),
 ('master-wc','wc',485,170,'WC1'),('master-lav-1','lav',300,365,'L1'),('master-lav-2','lav',375,365,'L1'),
 ('powder-lav','lav',1180,265,'L1'),('powder-wc','wc',1125,320,'WC1'),
 ('washer','washer',1490,240,'WB1'),('lower-shower','shower',1590,735,'SH1'),
 ('lower-lav','lav',1530,900,'L1'),('lower-wc','wc',1600,890,'WC1'),
 ('kitchen-sink','sink',1125,690,'SK1'),('dishwasher','dishwasher',1060,690,'DW1'),
 ('terrace-hosebib','hosebib',1055,1270,'HB1')]
for id,kind,x,y,tag in fixtures:
    element(id,'unit','fixture',fixture=kind,at=p(x,y,0),system='fixtures',source=U,tag=tag,count_status='confirmed')
    label('label-'+id,'unit',p(x-35,y+45,2),tag,5)
# Explicit branch endpoints. All device drops connect to a source main.
def drop(id,sys,a,b,size=.5):
    route(id,sys,[a,(b[0],a[1]),(b[0],b[1]),(b[0],b[1],b[2])],size,True)
drop('shower-master-cw','CW',(165,180),(155,165,48))
drop('shower-master-hw','HW',(165,200),(175,165,48))
drop('bath-cw','CW',(335,180),(325,150,24),.75)
drop('bath-hw','HW',(335,200),(345,150,24),1)
drop('wc-master-cw','CW',(485,180),(485,150,12))
for x in [300,375]:
    drop('lav-'+str(x)+'-cw','CW',(x,335),(x-5,365,24))
    drop('lav-'+str(x)+'-hw','HW',(x,350),(x+5,365,24))
drop('powder-cw','CW',(1180,180),(1175,265,24))
drop('powder-hw','HW',(1180,200),(1185,265,24))
drop('powder-wc-cw','CW',(1125,180),(1125,320,12))
drop('washer-cw','CW',(1395,240),(1485,240,42))
drop('washer-hw','HW',(1410,240),(1495,240,42))
drop('shower-lower-cw','CW',(1590,735),(1600,735,48))
drop('shower-lower-hw','HW',(1570,735),(1580,735,48))
drop('lav-lower-cw','CW',(1510,875),(1525,900,24))
drop('lav-lower-hw','HW',(1525,875),(1535,900,24))
drop('wc-lower-cw','CW',(1590,875),(1600,890,12))
for sys,x in [('CW',1395),('HW',1410)]:
    shift=0 if sys=='CW' else 15
    route('island-underfloor-'+sys,sys,[(x,645),(x,645,-6),(1120+shift,645,-6),(1120+shift,690,-6),(1120+shift,690,24)],.5,True)
# Separate dishwasher connection not unambiguously resolved in scan; omit pipe
# rather than invent a confirmed hot/cold connection. Fixture remains visible.
for sys,x,y in [('CW',1450,180),('HW',1450,200),('HWC',1430,245)]:
    element('unit-isolation-'+sys,'unit','valve',at=p(x-40,y),system=sys,source=U)
element('unit-meter','unit','meter',at=p(1450,180),system='CW',source=U)
label('unit-name','unit',p(750,1180,3),'UNIT A / 107',14)
label('master-name','unit',p(120,420,3),'PRIMARY BATH',7)
label('kitchen-name','unit',p(980,780,3),'KITCHEN',7)
outline=[(100,120),(1450,120),(1450,600),(1660,600),(1660,1260),(750,1260),(750,850),(100,850),(100,120)]
for i,(a,b) in enumerate(zip(outline,outline[1:])):
    element('unit-outline-'+str(i),'unit','wall',points=[p(*a,0),p(*b,0)],height=18,thickness=4,system='context',source=U)
for i,(a,b) in enumerate([((100,420),(650,420)),((650,120),(650,420)),((1080,120),(1080,380)),((1080,380),(1300,380)),((1450,600),(1450,950)),((1450,950),(1660,950))]):
    element('partition-'+str(i),'unit','wall',points=[p(*a,0),p(*b,0)],height=18,thickness=3,system='context',source=U)

for e in elements:
    if e['scene']=='unit':
        e['xy_status']='provisional';e['xy_source']=CAL['dimension_source']+' → P2.02 common grid → P4.01 registered crop'
        e['xy_tolerance']='Scale allowance ±1%; local simplified trace allowance ±6 in; not field accuracy.'
        e['z_status']='assumed';e['envelope_status']='assumed'
        e['basis']='XY derived from calibrated raster trace. Pipe elevations, fixture envelopes and simplified fittings remain assumed.'

spec={
 'project':'Highland | domestic water in 3D','units':'inches','workflow':'manual scanned drawing takeoff; separate from house extractor',
 'sources':[{'file':'RL- REVISED Highland Condos Plumbing 10-29-07.pdf','sheet':'P3.02','page':13,'issue':'2007-10-29','scale':'NONE for boiler diagram'}, {'sheet':'P4.01','page':15,'issue':'2007-10-29','scale':'provisional cross-sheet calibration; see calibration.json'}, {'sheet':'P2.02','page':5,'issue':'2007-10-29','scale':'common structural grid calibrated to A2.03 dimensions'}, {'file':CAL['architectural_file'],'sheet':'A2.03','page':1,'issue':'2007-04-02'}, {'file':CAL['architectural_file'],'sheet':'A3.11','page':9,'issue':'2007-04-02'}],
 'calibration':CAL,
 'limitations':[
 'Domestic water only. Sanitary, vent, gas, fire protection and architectural building geometry are not modeled.',
 'Unit 107 XY is provisionally calibrated through the shared structural grid; building floor datums are documented. Pipe heights, building stack XY, fittings and equipment envelopes remain assumed. This is not an as-built or fully coordinated model.',
 'A3.11 establishes 11 ft floor-to-floor at Unit 107, not clear ceiling height. Its (+1/4 in) interval notes conflict slightly with labeled elevation differences; model uses the labeled elevations.',
 'Nominal bore is used as outside visual diameter; pipe material, wall thickness, insulation and actual OD are not established. No pipe lengths or quantities should be taken from this model.',
 'Building stack positions are arranged for presentation. Typical unit branches terminate at continuations; their diameters are assumed pending unit-specific takeoff.',
 '04 stack has four explicit upper branch groups on P3.02; its R1 dwelling branch is unresolved and is not invented.',
 'Common-area and garage/irrigation services are omitted from this first model. Unit 106 is a continuation only; Unit 107 is the detailed dwelling.',
 'Plant arrangement and reduced device detail are illustrative. Safety relief/drain piping, flues, detailed controls and balancing bypasses are not fully modeled. WAC2 is a loose spare, not a second installed pump.',
 'Unit A island underfloor path is assumed between annotated drops. Dishwasher connection is unresolved and omitted. Hot/return joins are depicted at representative loop endpoints.',
 'Annotations in the supplied PDF are treated as review information, not proof of installed conditions.'
 ],
 'display':{'building_pipe_multiplier':2.5,'plant_pipe_multiplier':1.0,'unit_pipe_multiplier':1.5},
 'checks':{'stack_groups':5,'typical_branch_trios':23,'unit_fixtures':14,'boilers':2,'storage_tanks':2,'expansion_vessels':4,'installed_pumps':3,'source':S+'; '+B+'; '+U},
 'roots':roots,'elements':elements}
out=HERE/'highland-water.spec.json'
out.write_text(json.dumps(spec,indent=2)+'\n')
print(f'{len(elements)} source-tagged elements → {out}')
