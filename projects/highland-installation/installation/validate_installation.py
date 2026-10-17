"""Validate source identity, proposed network integrity and delivered artifacts."""
import json,math,hashlib,struct
from pathlib import Path
from PIL import Image,ImageStat,ImageChops
import yaml
ROOT=Path(__file__).resolve().parent
S=yaml.safe_load((ROOT/'highland-installation-proposed.yaml').read_text())
checks=[]
def check(name,condition,detail=''):
 checks.append({'check':name,'passed':bool(condition),'detail':detail})
 if not condition:raise AssertionError(name+': '+detail)
manifest=json.loads((ROOT.parent/'source-manifest.json').read_text())
check('Original source checksum',hashlib.sha256((ROOT.parent/'Highland-original.pdf').read_bytes()).hexdigest()==manifest['sha256']==S['source_sha256'])
ids=[e['id'] for e in S['elements']]
check('Stable IDs unique',len(ids)==len(set(ids)))
check('Every physical element explicitly assumed',all(e['status']=='assumed' and e.get('basis') and e.get('source') for e in S['elements']))
check('All six process phases have release gates',len(S['phases'])==6 and all(p['gate'] for p in S['phases']))
check('Source-backed systems represented',set(e['system'] for e in S['elements'] if e['type']=='pipe')=={'CW','HW','HWC'})
# Split segments wherever another same-system endpoint lands on them.
def on_segment(p,a,b):
 ab=[b[k]-a[k] for k in range(3)];ap=[p[k]-a[k] for k in range(3)]
 dd=sum(v*v for v in ab)
 if dd==0:return sum(v*v for v in ap)<1e-12
 t=sum(ap[k]*ab[k] for k in range(3))/dd
 return -.000001<=t<=1.000001 and sum((ap[k]-t*ab[k])**2 for k in range(3))<1e-10
for system in ['CW','HW','HWC']:
 routes=[e for e in S['elements'] if e['type']=='pipe' and e['system']==system]
 pts=set(tuple(p) for e in routes for p in e['points']);adj={p:set() for p in pts}
 for e in routes:
  for a,b in zip(e['points'],e['points'][1:]):
   members=[p for p in pts if on_segment(p,a,b)]
   for p in members:adj[p].update(members)
 reached=set();todo=[tuple(routes[0]['points'][0])]
 while todo:
  p=todo.pop()
  if p in reached:continue
  reached.add(p);todo.extend(adj[p]-reached)
 check(system+' proposed network connected',reached==pts,f'{len(routes)} routes; topology check only, no hydraulic sizing validation')
hw=next(e for e in S['elements'] if e['id']=='HW-02')
hwc=next(e for e in S['elements'] if e['id']=='HWC-01')
check('Proposed return reaches hot-water far end',hw['points'][-1]==hwc['points'][0],'Return termination remains a field/design hold point')
for eid in ['F05','F08','F10']:
 e=next(e for e in S['elements'] if e['id']==eid)
 check(eid+' cold-only supply',e['systems']==['CW'])
check('No field quantities asserted','not a physical building dimension' in S['display']['basis'])
for image_path in sorted((ROOT/'renders').glob('*.png')):
 if 'contact' in image_path.stem:continue
 im=Image.open(image_path).convert('RGB');std=ImageStat.Stat(im.resize((100,100))).stddev
 check('Nonblank '+image_path.name,min(im.size)>=1000 and max(std)>8,f'{im.width} x {im.height}')
check('All expected review views present',all((ROOT/'renders'/('review-'+v+'.png')).exists() for v in ['plan','front','side','iso']))
check('All six stage renders present',all((ROOT/'renders'/f'phase-{p:02}.png').exists() for p in range(1,7)))
for phase in range(1,6):
 a=Image.open(ROOT/'renders'/f'phase-{phase:02}.png').convert('RGB').resize((200,175))
 b=Image.open(ROOT/'renders'/f'phase-{phase+1:02}.png').convert('RGB').resize((200,175))
 check(f'Stage {phase} to {phase+1} changes visibly',sum(ImageStat.Stat(ImageChops.difference(a,b)).mean)>.01)
for stem in ['Highland-installation-unit-B','Highland-installation-shared']:
 check(stem+' Blender file', (ROOT/(stem+'.blend')).stat().st_size>10000)
 data=(ROOT/(stem+'.glb')).read_bytes();magic,version,size=struct.unpack('<4sII',data[:12]);n,typ=struct.unpack('<II',data[12:20]);g=json.loads(data[20:20+n])
 check(stem+' portable model',magic==b'glTF' and version==2 and size==len(data) and len(g.get('nodes',[]))>10)
 check(stem+' provenance metadata',any(n.get('extras',{}).get('status')=='assumed' for n in g['nodes']))
 if 'unit-B' in stem:
  systems=set(n.get('extras',{}).get('system') for n in g['nodes'])
  check('Portable unit model contains all three systems',{'CW','HW','HWC'}<=systems)
result={'passed':True,'checks':checks,'limits':'Checks establish file integrity and proposed graph continuity only; no hydraulic, structural, code or field verification.'}
(ROOT/'validation.json').write_text(json.dumps(result,indent=2))
print('PASS:',len(checks),'checks. Graph continuity is not field or hydraulic validation.')
