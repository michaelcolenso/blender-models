from pathlib import Path
import hashlib,json
import numpy as np
from PIL import Image
root=Path(__file__).resolve().parents[2];out=root/'deliverables/highland-drawings'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
native=sha(out/'Highland-drawing-reconciled.blend')
geometry=json.loads((out/'geometry-validation.json').read_text());digest=hashlib.sha256(json.dumps(geometry['after'],sort_keys=True,separators=(',',':')).encode()).hexdigest()
rows={}
for report in ['review-render','native-render','dusk-render','dusk-review-render']:
 d=json.loads((out/f'{report}.json').read_text());assert d['native_sha256']==native and d['architecture_inventory_sha256']==digest
 for name,h in d['images'].items():
  p=out/name;assert sha(p)==h
  with Image.open(p) as im:
   rgb=np.asarray(im.convert('RGB'));std=float(rgb.std());assert std>8,(name,'blank image')
   if name=='Highland-daylight-drawing-reconciled.png':assert im.size==(1995,1323)
   elif name=='Highland-dusk-drawing-reconciled.png':assert im.size==(1920,1080)
   elif name.startswith('dusk-review/'):assert im.size==(960,540)
   else:assert im.size==(1200,944)
   rows[name]={'sha256':h,'size':list(im.size),'rgb_standard_deviation':round(std,3)}
assert len(rows)==14
result={'status':'PASS','native_sha256':native,'architecture_inventory_sha256':digest,'images':rows,'note':'Nonblank/dimension/hash checks supplement the separately recorded visual inspection.'}
(out/'render-validation.json').write_text(json.dumps(result,indent=2)+'\n')
print('PASS',len(rows),'final native renders')
