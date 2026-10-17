"""Production timeline. Model geometry remains governed by the existing installation spec."""
import json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parent
SOURCE=ROOT.parent/'installation'
C=json.loads((ROOT.parent/'studio-upgrade/studio-config.json').read_text())
G=json.loads((SOURCE/'installation-data.json').read_text())
def pose(az,el,target,scale):return {'azimuth':az,'elevation':el,'target':target,'ortho_scale':scale}
def coord(p):return [(p[0]-.5)*G['display']['width_in']*.0254,(.5-p[1])*G['display']['height_in']*.0254,p[2]*.0254]
def blend(a,b,u):return [x*(1-u)+y*u for x,y in zip(a,b)]
wide=[-.8,.2,1.0]
service=coord([.129,.102,66])
kitchen=coord(next(e for e in G['elements'] if e['id']=='CW-04')['points'][-1])
# One continuous rig spans chapter boundaries. Each path key is a presentation
# choice; source routes and field dimensions remain governed by the source spec.
unit_path=[(8,wide,21,59),(18,wide,20.5,55),(22,blend(kitchen,wide,.4),13.5,52),
           (26,blend(kitchen,wide,.4),13.5,51),(30,wide,20.5,50),(47,wide,20.5,49),
           (54,blend(service,wide,.18),9.5,49),(61,blend(service,wide,.18),9.5,48),
           (68,wide,20.5,50),(85,wide,21,53)]
def unit_pose(t):
 if t<=unit_path[0][0]:a=b=unit_path[0];u=0
 elif t>=unit_path[-1][0]:a=b=unit_path[-1];u=0
 else:
  a,b=next((a,b) for a,b in zip(unit_path,unit_path[1:]) if a[0]<=t<b[0])
  u=(t-a[0])/(b[0]-a[0]);u=u*u*(3-2*u)
 return pose(-65+(max(8,min(85,t))-8)*.38,a[3]*(1-u)+b[3]*u,blend(a[1],b[1],u),a[2]*(1-u)+b[2]*u)
shots=[
 dict(id=1,start=0,end=8,scene='shared',title='Follow the water',caption='One shared system. A coordinated replacement.',
      voice='A successful repipe starts with understanding how the building’s water system connects.',
      points=['Three connected services','Source-labeled riser groups','A distinct Unit B / 106 pilot'],source='P3.02 · PDF 13',
      camera=[(0,pose(-59,40,[0,0,2],25)),(8,pose(-53,41,[0,0,2],24))]),
 dict(id=2,start=8,end=18,scene='unit',title='Verify and protect',caption='Confirm routes, access, and affected services.',
      voice='Confirm the actual routes, access, and affected services before committing to a shutdown.',
      points=['Trace supply and return','Prove the isolation boundary','Agree access and protection'],source='P4.01 · PDF 15',
      camera=[(8,pose(-90,89.9,[0,0,.1],24)),(18,pose(-65,74,[-.7,.8,.3],22.5))]),
 dict(id=3,start=18,end=29,scene='unit',title='Open and prepare',caption='Protect finishes. Open access. Prepare the route.',
      voice='Protect the home, open the necessary areas, and prepare the new route.',
      points=['Service assembly access','Support and penetration review','Kitchen low-wall connection'],source='P4.01 · PDF 15',
      camera=[(18,pose(-65,74,[-.7,.8,.3],22.5)),(24,pose(-58,60,[-1,1.4,.6],19)),(29,pose(-55,54,[-1,2.2,1],18))]),
 dict(id=4,start=29,end=45,scene='unit',title='Install distribution',caption='Install the replacement distribution.',
      voice='Build the replacement distribution as an isolated system, coordinating cold water, hot water, and circulation return.',
      points=['Cold-water distribution','Hot-water distribution','Circulation-return continuity'],source='P4.01 · PDF 15',
      camera=[(29,pose(-55,54,[-1,2.2,1],18)),(45,pose(-48,55,[-1,2.2,1],18.5))]),
 dict(id=5,start=45,end=58,scene='unit',title='Branch, test, inspect',caption='Complete branches. Test. Inspect.',
      voice='Complete the fixture branches, then test and inspect the new piping before service transfer.',
      points=['Complete fixture-group branches','Keep the new network isolated','Required test and inspection'],source='P4.01 · PDF 15',
      camera=[(45,pose(-48,55,[-1,2.2,1],18.5)),(52,pose(-51,57,[-.7,.5,.8],19.5)),(58,pose(-55,58,[-.4,.3,.8],21))]),
 dict(id=6,start=58,end=73,scene='unit',title='Transfer and commission',caption='Transfer service. Check connections. Balance circulation.',
      voice='Within a verified isolation boundary, transfer service, check the final connections, flush, and balance circulation.',
      points=['Isolate and drain','Connect and check final tie-ins','Flush and balance the return'],source='P4.01 / P3.02',
      camera=[(58,pose(-55,52,[-4.05,3.8,1.45],5.7)),(63,pose(-53,53,[-4.05,3.8,1.45],6.2)),(67,pose(-53,55,[-2,2,1],13)),(73,pose(-55,58,[-.4,.3,.8],21))]),
 dict(id=7,start=73,end=85,scene='unit',title='Restore and document',caption='Restore finishes. Preserve access. Record the installation.',
      voice='After acceptance, restore penetrations and finishes, preserve service access, and document what is behind the walls.',
      points=['Restore required assemblies','Retain service access','Photograph, label, and record'],source='P4.01 · Proposed method',
      camera=[(73,pose(-55,58,[-.4,.3,.8],21)),(85,pose(-52,58,[0,0,.6],23))]),
 dict(id=8,start=85,end=90,scene='shared',title='A maintainable system',caption='A planned sequence. Restored service. A maintainable system.',
      voice='A planned sequence. Restored service. A maintainable system.',
      points=['Coordinated access','Verified service transfer','Documented installation'],source='Shared-system concept',
      camera=[(85,pose(-53,41,[0,0,2],24)),(90,pose(-51,41,[0,0,2],25))]),
]
spec={
 'presentation_version':2,
 'project':'200 W Highland — proposed repipe installation','duration':90,'fps':24,
 'master_size':[3840,2160], 'render_size':[1600,900], 'render_fps':6,
 'render_method':'Cycles CPU, coated Principled materials, studio HDRI/area lights, AgX and a separate exact-color plate. Six native scene frames/second interpolated to 24 fps before 4K graphics; this is not native 4K/24 fps model imagery.',
 'geometry_authority':'../installation/highland-installation-proposed.yaml',
 'footer':'Proposed installation sequence · Field verification required.',
 'shots':shots,
 'sources':{name:hashlib.sha256((SOURCE/name).read_bytes()).hexdigest() for name in ['Highland-installation-shared.blend','Highland-installation-unit-B.blend','highland-installation-proposed.yaml']},
 'assumptions':['Camera placement, timing, lighting and flow-marker positions are presentation choices.','All physical geometry retains the source model provenance; no verified shutdown boundary, pipe sizing or test result is added.','Flow markers illustrate proposed direction after the depicted service transfer; no hydraulic simulation is claimed.'],
 'reveal':{'CW-01':[29,31],'CW-02':[31,34],'CW-03':[34,37],
           'HW-01':[30,32],'HW-02':[32,35],'HW-03':[35,38], 'HWC-01':[38,42]},
 'cutover':{'isolate':[58,61],'connect':[61,64],'check_and_flush':[64,67],'flow_start':67},
 'palette':{'paper':C['background_srgb'],'ink':C['palette']['ink'],'muted':'#5b6c70',**{k:C['palette'][k] for k in ['CW','HW','HWC','access']}},
 'render_samples':16,
 'camera_rigs':{'unit':{'path':unit_path,'azimuth_start':-65,'azimuth_drift_degrees_per_second':.38}},
 'opening':{'exterior_start':0,'exterior_end':4.5,'shared_start':3.5,'shared_end':8,'transition':'one-second dissolve; no unit location asserted'},
}
for shot in shots:
 if shot['scene']=='unit':
  times=sorted({shot['start'],shot['end'],*[k[0] for k in unit_path if shot['start']<k[0]<shot['end']]})
  shot['camera']=[(t,unit_pose(t)) for t in times]
shots[0].update(title='Exterior to system',caption='Begin at the building. Follow the water.',
                points=['Exterior overview','Three connected services','A distinct Unit B / 106 pilot'],source='Exterior study / P3.02')
(ROOT/'animation-spec.json').write_text(json.dumps(spec,indent=2,ensure_ascii=False))
print('Production specification: 8 shots, 90 seconds, 2160 output frames.')
