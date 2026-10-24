"""Package final outputs only after required build, reopen and render checks succeed."""
from pathlib import Path
import hashlib,json,zipfile
from PIL import Image,ImageStat
root=Path(__file__).resolve().parents[1]
for name in ['build_validation_report.json','saved_blend_verification.json']:
    r=json.loads((root/'output'/name).read_text());assert r['validation_passed'],(name,r)
r=json.loads((root/'output/extended_runtime_qa.json').read_text())
assert not r['invalid_drivers'] and not r['flagged_driver_errors'] and not r['nonfinite_objects']
assert all(c['passed'] for c in r['saved_route_checks'])
assert r['boolean_grid']['mismatch_count']==0
frames=[1,38,50,61,68,76,83,89]
for f in frames:assert len(list((root/'renders').glob(f'B101_demo_{f:03d}_*.png')))==1
inventory=[]
for p in sorted((root/'renders').rglob('*.png')):
    with Image.open(p) as im:
        im.load();rgb=im.convert('RGB');stat=ImageStat.Stat(rgb)
        assert max(stat.extrema[0])>0
        inventory.append({'file':str(p.relative_to(root)),'width':im.width,'height':im.height,'bytes':p.stat().st_size,'channel_mean':stat.mean,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'decode_passed':True})
(root/'output/render_inventory.json').write_text(json.dumps(inventory,indent=2))
blend=root/'output/Meydenbauer_B101_Demolition_v4.blend'
summary={'blender_version':'4.3.2','platform':'Linux x86_64','command':'bash run_blender.sh --render-keyframes','launcher_exit_code':0,'requested_passes':[1,2,3],'requested_render_frames':frames,'requested_render_count':8,'additional_diagnostic_render_count':len(inventory)-8,'strict_build_validation_passed':True,'fresh_process_reopen_validation_passed':True,'original_python_sources_modified':False,'runtime_model_fixes':[],'coordination_acceptance':'REVISION REQUIRED','acceptance_blockers':['Authored trench cutters overlap the marked prior-ABS no-demolition envelope.','Authored default camera is obstructed by upper-floor context and poorly frames B-101.'],'blend_sha256':hashlib.sha256(blend.read_bytes()).hexdigest()}
(root/'output/execution_summary.json').write_text(json.dumps(summary,indent=2))
files=[p for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.blend1' and p.name!='DELIVERY_MANIFEST.sha256']
(root/'DELIVERY_MANIFEST.sha256').write_text('\n'.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+str(p.relative_to(root)) for p in sorted(files))+'\n')
files.append(root/'DELIVERY_MANIFEST.sha256')
zip_path=root.parent/'Meydenbauer_B101_v4_Executed_Delivery.zip'
with zipfile.ZipFile(zip_path,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for p in sorted(files):z.write(p,root.name+'/'+str(p.relative_to(root)))
with zipfile.ZipFile(zip_path) as z:assert z.testzip() is None
print(json.dumps({'zip':str(zip_path),'bytes':zip_path.stat().st_size,'files':len(files),'renders':len(inventory)},indent=2))
