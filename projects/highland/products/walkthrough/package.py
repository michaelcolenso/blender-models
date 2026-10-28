"""Bundle a standalone phone viewer with the exterior GLB embedded."""
from pathlib import Path
import json,base64

H=Path(__file__).parent;ROOT=H.parents[3];B=ROOT/'build/highland-drone';B.mkdir(parents=True,exist_ok=True)
spec=json.loads((H/'flight.spec.json').read_text());src=(H/'template.html').read_text()
bundle=(B/'app.bundle.js').read_text();glb=(ROOT/'projects/highland/deliverables/exterior/Highland-exterior.glb').read_bytes()
assert len(glb)>1_000_000 and len(bundle)>20_000
html=src.replace('__SPEC__',json.dumps(spec,separators=(',',':'))).replace('__EXTERIOR__',base64.b64encode(glb).decode()).replace('__BUNDLE__',bundle)
assert '__BUNDLE__' not in html and '__EXTERIOR__' not in html
html='\n'.join(line.rstrip(' \t') for line in html.split('\n'))
(B/'Highland-drone-tour.html').write_text(html)
print(f'Standalone phone viewer: {len(html)/1e6:.1f} MB')
