from pathlib import Path
import base64
h=Path(__file__).parent;b=h.parent.parent/'build/highland-repipe'
s=(h/'template.html').read_text().replace('__STRATEGY__',(h/'repipe-strategy.json').read_text()).replace('__REFERENCE_SPEC__',(h.parent/'highland-water/highland-water.spec.json').read_text()).replace('__GLB__',base64.b64encode((b.parent/'highland-water/unit.glb').read_bytes()).decode()).replace('__APP__',(h/'app.bundle.js').read_text().replace('</script',r'<\/script'))
(b/'Highland-repipe-sequence.html').write_text('\n'.join(l.rstrip() for l in s.splitlines()))
print('Packaged separate repipe sequence:',len(s),'bytes')
