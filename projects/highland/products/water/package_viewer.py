from pathlib import Path
import base64,json
HERE=Path(__file__).parent
BUILD=HERE.parents[3]/'build/highland-water'
html=(HERE/'viewer.template.html').read_text()
models={k:base64.b64encode((BUILD/(k+'.glb')).read_bytes()).decode() for k in ['unit','building','plant']}
spec=json.loads((HERE/'highland-water.spec.json').read_text())
html=html.replace('__SPEC__',json.dumps({'limitations':spec['limitations']})).replace('__MODELS__',json.dumps(models)).replace('__BUNDLE__',(HERE/'viewer.bundle.js').read_text().replace('</script',r'<\/script'))
# Bundled GLSL templates contain insignificant end-of-line whitespace.
html='\n'.join(line.rstrip() for line in html.split('\n'))
(BUILD/'Highland-plumbing-3D.html').write_text(html)
print(f'Packaged standalone viewer: {len(html)/1e6:.1f} MB')
