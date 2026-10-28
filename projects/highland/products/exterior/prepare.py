"""Manual exterior takeoff from A2.03/.04/.07/.08 and A3.01/.02.
Coordinates in the expanded model spec are inches. Source raster picks use the
1815 x 1296 review images of the original 3024 x 2160 point scanned sheets.
"""
from pathlib import Path
import json,hashlib,sys
from bmodels.paths import ROOT
H=Path(__file__).parent
# Source drawings live in the site's git-ignored sources/ folder; pass another path to override.
PDF=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/'projects/highland/sources/Pages from 200 W. Highland Construction Plans - Complete.pdf'
X=[0,195,528,861,1236];Y=[1800,1434,1110,900,690,474,180,0]
def interp(v,ps,vs):
 pairs=sorted(zip(ps,vs));i=next((i for i in range(len(pairs)-1) if v<=pairs[i+1][0]),len(pairs)-2);a,b=pairs[i:i+2];return a[1]+(v-a[0])/(b[0]-a[0])*(b[1]-a[1])
grids={'r1':([864,951,1103,1253,1421],[223,386,532,626,725,820,951,1034]),'typical':([866,954,1106,1257,1425],[224,390,534,629,726,823,955,1034]),'r5':([875,963,1113,1265,1432],[223,386,531,626,726,822,951,1034]),'roof':([874,962,1113,1264,1430],[225,386,531,629,726,822,951,1034])}
# Orthogonal facade centerlines, manually simplified from the plan wall faces.
typical=[(936,229),(1064,229),(1064,242),(1499,242),(1499,336),(1516,336),(1516,466),(1499,466),(1499,814),(1516,814),(1516,897),(1499,897),(1499,968),(1433,968),(1433,949),(1368,949),(1368,1002),(1234,1002),(1234,949),(1177,949),(1177,968),(1090,968),(1090,949),(1069,949),(1069,868),(1090,868),(1090,841),(1028,841),(1028,636),(984,636),(984,344),(936,344)]
r1=[(866,230),(1063,230),(1063,241),(1499,241),(1499,398),(1528,398),(1528,532),(1499,532),(1499,814),(1516,814),(1516,897),(1499,897),(1499,968),(1433,968),(1433,949),(1368,949),(1368,1002),(1234,1002),(1234,949),(1177,949),(1177,968),(1090,968),(1090,949),(1069,949),(1069,868),(1090,868),(1090,841),(1028,841),(1028,636),(977,636),(977,347),(866,347)]
r5=[(993,239),(1510,239),(1510,478),(1477,478),(1477,821),(1443,821),(1443,921),(1090,921),(1090,841),(1036,841),(1036,727),(993,727),(993,540),(1036,540),(1036,483),(993,483)]
def convert(poly,g):return [[round(interp(x,grids[g][0],X),3),round(interp(y,grids[g][1],Y),3)] for x,y in poly]
polys={k:convert(p,k) for k,p in [('r1',r1),('typical',typical),('r5',r5)]}
levels=[('P1',0,'r1'),('R1',132,'r1'),('R2',255,'typical'),('R3',378,'typical'),('R4',501,'typical'),('R5',627,'r5')]
# Elevation grid registration: local spans differ from the dimensioned plan.
# These piecewise mappings are explicit, rather than treating scan pixels as exact.
facades={'south':{'pixels':[868,975,1144,1293,1443],'inches':X,'source':'A3.01 / 01 south elevation'},'east':{'pixels':[646,728,861,962,1052,1149,1296,1460],'inches':list(reversed(Y)),'source':'A3.01 / 02 east elevation'},'west':{'pixels':[646,810,958,1048,1148,1246,1374,1457],'inches':Y,'source':'A3.02 / 02 west elevation'},'north':{'pixels':[920,1071,1222,1390],'inches':[1236,861,528,195],'source':'A3.02 / 01 north elevation'}}
south=[(947,984,'window'),(996,1026,'window'),(1038,1060,'balcony'),(1075,1087,'window'),(1104,1164,'wide'),(1188,1224,'balcony'),(1250,1286,'window'),(1319,1357,'window'),(1385,1421,'balcony'),(1444,1487,'wide'),(1503,1515,'window')]
east=[(679,711,'balcony'),(730,766,'window'),(792,844,'wide'),(885,918,'window'),(1008,1041,'balcony'),(1079,1135,'wide'),(1164,1196,'balcony'),(1220,1280,'wide'),(1311,1344,'balcony'),(1372,1425,'wide')]
west=[(694,757,'wide'),(787,818,'window'),(857,888,'window'),(922,953,'balcony'),(988,1050,'wide'),(1095,1124,'balcony'),(1209,1238,'balcony'),(1301,1364,'wide'),(1398,1420,'balcony')]
north=[(848,865,'window'),(952,978,'small'),(1165,1199,'window'),(1306,1321,'window'),(1354,1369,'window'),(1406,1423,'window')]
cols={'south':south,'east':east,'west':west,'north':north}
roofcols={'south':[(996,1015,'window'),(1042,1073,'window'),(1106,1167,'wide'),(1191,1222,'window'),(1250,1285,'window'),(1319,1354,'window'),(1385,1415,'window'),(1427,1448,'window'),(1473,1491,'window')], 'east':[(759,811,'wide'),(826,842,'window'),(889,918,'window'),(951,972,'window'),(1009,1040,'window'),(1088,1117,'window'),(1167,1198,'window'),(1220,1280,'wide'),(1311,1344,'balcony'),(1372,1425,'wide')], 'west':[(694,757,'wide'),(787,818,'window'),(857,888,'window'),(922,953,'window'),(988,1050,'wide'),(1095,1124,'window'),(1193,1253,'wide'),(1280,1314,'window'),(1320,1337,'window')], 'north':north}
basecols={'south':[(884,934,'wide'),(990,1018,'door'),(1040,1065,'door'),(1103,1163,'wide'),(1188,1218,'door'),(1249,1286,'wide'),(1320,1350,'door'),(1385,1420,'door'),(1444,1486,'wide')], 'east':[(664,707,'wide'),(730,766,'window'),(791,825,'door')], 'west':[], 'north':[]}
def boundary(poly,face,u):
 candidates=[]
 for j,(a,b) in enumerate(zip(poly,poly[1:]+poly[:1])):
  if face in ['south','north'] and abs(a[1]-b[1])<.01 and min(a[0],b[0])+.1<u<max(a[0],b[0])-.1:candidates.append((a[1],j,min(a[0],b[0]),max(a[0],b[0])))
  if face in ['east','west'] and abs(a[0]-b[0])<.01 and min(a[1],b[1])+.1<u<max(a[1],b[1])-.1:candidates.append((a[0],j,min(a[1],b[1]),max(a[1],b[1])))
 if not candidates:return None
 return (min if face in ['south','west'] else max)(candidates,key=lambda x:x[0])
openings=[];rejected=[]
for level,z,pk in levels:
 for face in facades:
  f=facades[face]
  for n,(p0,p1,kind) in enumerate((basecols if level=='P1' else roofcols if level=='R5' else cols)[face]):
   lo,hi=sorted([interp(p,f['pixels'],f['inches']) for p in [p0,p1]]);u=(lo+hi)/2;hit=boundary(polys[pk],face,u)
   if not hit:rejected.append({'level':level,'face':face,'pixels':[p0,p1],'reason':'Projected center outside the corresponding plan outline; not invented.'});continue
   coord,seg,mn,mx=hit;width=min(hi-lo,2*(u-mn-6),2*(mx-u-6))
   if width<16:rejected.append({'level':level,'face':face,'pixels':[p0,p1],'reason':'Opening would overrun the plan facade return; omitted pending reconciliation.'});continue
   sill=9;h=90
   if kind in ['balcony','door']:sill=2;h=96
   if kind=='small':sill=78;h=22
   if level=='P1' and kind!='door':sill=20;h=72
   if level=='R5' and kind!='small':sill=18;h=84
   if face=='east' and level=='R1' and n==7:kind='entry';sill=0;h=102
   openings.append(dict(id=f'{face}-{level}-{n+1:02}',face=face,level=level,polygon=pk,segment=seg,u=round(u,3),width=round(width,3),z=z+sill,height=h,kind=kind,status='assumed',xy_status='provisional',source=f['source'],source_pixels=[p0,p1],source_width_in=round(hi-lo,3),plan_depth_in=coord,basis='Facade pattern picked from elevation and projected onto the simplified plan boundary. Standardized sill/head heights, depth and frame sections are assumed; width may be clipped to fit a plan return.'))
# Garage gate on east P1, as shown on A3.01. Its exact grade interface is assumed.
u=interp(936,facades['east']['pixels'],facades['east']['inches']);coord,seg,_,_=boundary(polys['r1'],'east',u)
openings.append(dict(id='east-P1-garage',face='east',level='P1',polygon='r1',segment=seg,u=u,width=240,z=28,height=94,kind='garage',status='assumed',xy_status='provisional',source='A3.01 east elevation / sectional overhead aluminum gate',basis='Gate position scaled from the elevation; dimensions and grade clearance simplified.',plan_depth_in=coord))
# Roof tower plan extents and documented parapet elevations.
def roofrect(px):
 a,b,c,d=px;p=convert([(a,b),(c,b),(c,d),(a,d)],'roof');return p
roof_features=[dict(id='elevator-overrun',polygon=roofrect((1216,354,1270,499)),z=749.04,top=876,source='A2.08 elevator roof / TO PARAPET 415.00',datum_status='confirmed'),dict(id='stair-overrun',polygon=roofrect((1216,615,1270,728)),z=749.04,top=(414.41-342)*12,source='A2.08 stair roof / TO PARAPET 414.41',datum_status='confirmed'),dict(id='south-clerestory',polygon=roofrect((1184,835,1435,921)),z=749.04,top=(407.75-342)*12,source='A2.08 clerestory roof / TO PARAPET 407.75',datum_status='confirmed')]
for e in roof_features:e.update(status='assumed',xy_status='provisional',basis='Roof footprint manually simplified from A2.08; top datum documented, roof/wall thickness and equipment envelopes assumed.')
spec=dict(photo_references=[{'id':'photo-01','description':'User street-view screenshot labeled September 2025 / 1213 2nd Ave W. Used for brick, panel and roof-cap appearance; not a dimensional reference.'},{'id':'photo-02','description':'User southeast corner photograph. Used for material families, recessed balcony appearance, cornices and planted edges. No scale or capture date established.'}],project='200 W. Highland Drive — exterior drawing study',units='inches',source_pdf_sha256=hashlib.sha256(PDF.read_bytes()).hexdigest(),source_date='2007-04-02',sources=['A2.03 R1 plan','A2.04 R2 plan','A2.07 R5 plan','A2.08 roof plan','A3.01 south/east elevations','A3.02 north/west elevations','A3.11 floor datums'],grid_dimensions_in={'x_6_to_10':X,'y_H_to_A':list(reversed(Y))},grid_pixel_picks=grids,facade_registration=facades,polygons=polys,polygon_status='provisional',polygon_basis='Manual orthogonal simplification registered to the dimensioned grids. Local wall steps and setbacks are provisional; not a surveyed footprint.',levels=[dict(name=n,z=z,polygon=p) for n,z,p in levels],roof_plate_z=749.04,north_roof_plate_z=773.04,north_roof_split_y=1110,roof_parapet_height=22,roof_features=roof_features,openings=openings,rejected_candidates=rejected,wall_thickness=8,frame_width=2,balcony_depth=60,guard_height=42,facade_dimensions_status='assumed',palette_status='provisional',palette_basis='User-supplied street photos show red-brown brick, pale projecting cornices, dark frames, recessed balconies and planted edges. Color matching is approximate because of daylight, perspective and image processing; exact products and recess depths remain assumed.',site=dict(status='assumed',grade_corners_ft={'SE':0,'SW':0,'NE':12,'NW':19},basis='Bilinear grade approximation from the sloping elevation lines; sidewalks, street strips and landscape props are presentation context, not a site survey.'),checks={'grid_x_span_in':1236,'grid_y_span_in':1800,'floor_elevations_ft':[342,353,363.25,373.5,383.75,394.25],'elevator_top_ft':415,'stair_top_ft':414.41},limitations=['Exterior drawing study, not verified installed conditions.','The dimensioned plan grids control footprint scale. Elevation grid spans do not agree uniformly with the plan; facade widths use explicit piecewise registration.','No single dimensional accuracy tolerance is established for this exterior model. Source picks, simplified wall returns and standardized window heights remain provisional/assumed.','Facade openings are surface-envelope studies; jamb details, exact opening schedule and recessed balconies are simplified.','R1/P1 lower enclosure is simplified because the architectural P1 plan was not supplied.','Roof slopes, drains, equipment, landscaping, sidewalk and street geometry are simplified; surrounding buildings are omitted.','Finish families follow the user photos; exact colors, reflectance, recess depth and landscape positions remain interpreted.','Not suitable for quantities, facade access design or construction dimensions.'])
(H/'exterior.spec.json').write_text(json.dumps(spec,indent=2)+'\n');print(f'{len(openings)} facade openings; {len(rejected)} candidates omitted with reasons.')
