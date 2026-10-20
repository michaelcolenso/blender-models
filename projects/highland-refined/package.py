"""Validate actual media and package the editable native scene and sources."""
import hashlib
import json
import shutil
import struct
import subprocess
import zipfile
from pathlib import Path

from PIL import Image,ImageStat

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
OUT=ROOT/'deliverables/highland-refined'
def read(path):return json.loads(path.read_text())
def info(path):return {'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
def command(args):return subprocess.run(args,check=True,capture_output=True,text=True).stdout

review=read(OUT/'visual-review.json')
assert review['daylight_and_source_views'] and review['all_pdf_pages'] and review['film_review_frames'] and review['encoded_movie_frames']
scene=read(OUT/'scene-readback.json');assert scene['scene_readback'] and scene['revised_architecture_preserved']
assert not scene['external_images_required'] and not scene['untagged_geometry']
revision=read(OUT/'revision-validation.json')
assert revision['opening_count']==175 and revision['remaining_unresolved_candidates']==16
assert revision['camera_frames_checked']==432 and not revision['camera_clips']
assert revision['minimum_frame_margin']>.015
base=read(ROOT/'projects/highland-exterior/exterior.spec.json');revised=read(HERE/'exterior-revised.spec.json')
controls=['polygons','levels','grid_dimensions_in','roof_features']
for key in controls:assert base[key]==revised[key],key
assert len(revised['openings'])==175 and len({e['id'] for e in revised['openings']})==175

images={}
for name,size in [('Highland-daylight-revised.png',(1920,1280))]+[(f'film-review/frame-{i:03}.png',(1920,1080)) for i in (0,72,144,216,288,360,431)]:
    with Image.open(OUT/name) as im:
        im.load();assert im.size==size,(name,im.size)
        stats=ImageStat.Stat(im.convert('RGB'));assert max(stats.stddev)>12 and max(stats.mean)>15,name
        images[name]={'dimensions':list(im.size),'mean_rgb':stats.mean,'stddev_rgb':stats.stddev}

movie=OUT/'Highland-dusk-approach-and-rise-18s.mp4'
film=read(OUT/'film-validation.json');assert film['frames']==432 and not film['errors']
probe=json.loads(command(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(movie)]))
streams=probe['streams'];assert len(streams)==1
stream=streams[0]
assert stream['codec_name']=='h264' and stream['pix_fmt']=='yuv420p'
assert (stream['width'],stream['height'])==(1920,1080)
assert stream['avg_frame_rate']=='24/1' and int(stream['nb_frames'])==432
assert abs(float(probe['format']['duration'])-18)<.001
decoded=command(['ffmpeg','-v','error','-i',str(movie),'-map','0:v:0','-f','framemd5','-'])
frames=[line for line in decoded.splitlines() if line and not line.startswith('#')]
assert len(frames)==432,len(frames)
distinct=len({line.rsplit(',',1)[-1].strip() for line in frames});assert distinct>400,distinct

data=(OUT/'Highland-revised-exterior.glb').read_bytes()
magic,version,length=struct.unpack('<4sII',data[:12]);assert (magic,version,length)==(b'glTF',2,len(data))
length,kind=struct.unpack('<II',data[12:20]);assert kind==0x4e4f534a
glb=json.loads(data[20:20+length]);assert len(glb['meshes'])>3000
mesh_nodes=[n for n in glb['nodes'] if 'mesh' in n]
assert all(all(n.get('extras',{}).get(k) for k in ('status','source','basis')) for n in mesh_nodes)
assert len(read(OUT/'camera-path.json'))==432
pdf=OUT/'Highland-photo-and-drawing-comparison.pdf'
assert pdf.read_bytes().startswith(b'%PDF-') and pdf.stat().st_size>100000

for src,name in [(HERE/'README.md','README.md'),(HERE/'revision-ledger.json','revision-ledger.json'),(HERE/'exterior-revised.spec.json','exterior-revised.spec.json'),(ROOT/'build/highland-refined/presentation/scene-validation.json','presentation-validation.json')]:
    shutil.copyfile(src,OUT/name)
files=['Highland-daylight-revised.png','Highland-photo-and-drawing-comparison.pdf','Highland-dusk-approach-and-rise-18s.mp4','Highland-revised-daylight-and-film.blend','Highland-revised-exterior.glb','README.md','element-provenance.csv','revision-ledger.json','exterior-revised.spec.json','revision-validation.json','builder-regression.json','scene-readback.json','presentation-validation.json','camera-path.json','film-validation.json','visual-review.json']
files.extend(str(p.relative_to(OUT)) for folder in ('source-review','film-review','encoded-review') for p in sorted((OUT/folder).glob('*.png')))
manifest={'source_controls_unchanged':controls,'revised_openings':175,'unresolved_candidates':16,'native_readback':scene,
    'image_validation':images,'film':{'dimensions':[1920,1080],'fps':24,'duration_seconds':18,'decoded_frames':len(frames),'distinct_decoded_frames':distinct,'codec':'H.264 / yuv420p','render_method':film['method']},
    'glb':{'mesh_nodes':len(mesh_nodes),'meshes':len(glb['meshes']),'source_metadata_on_all_mesh_nodes':True},
    'visual_review_completed':True,'source_accuracy_scope':'Qualitative source comparison; geometry and appearance assumptions remain. Not verified as-built.',
    'files':{name:info(OUT/name) for name in files}}
(OUT/'delivery-validation.json').write_text(json.dumps(manifest,indent=2)+'\n');files.append('delivery-validation.json')

sources=[]
for folder in (HERE,ROOT/'projects/highland-cinematic/assets',ROOT/'projects/highland-exterior/source-review'):
    sources.extend(p for p in folder.iterdir() if p.is_file() and p.suffix not in ('.blend1','.pyc'))
sources.extend(ROOT/name for name in ['projects/highland-exterior/build.py','projects/highland-exterior/exterior.spec.json','projects/highland-exterior/README.md','projects/highland-exterior/report.md','projects/highland-cinematic/build.py','projects/highland-cinematic/scene.json','projects/highland-drone/flight.spec.json','projects/highland-drone/osm-buildings-source.json'])
source_manifest={'architectural_pdf_sha256_recorded_by_original_study':base['source_pdf_sha256'],'original_pdf_present':False,'sources':{str(p.relative_to(ROOT)):info(p) for p in sorted(set(sources))}}
(OUT/'source-records.json').write_text(json.dumps(source_manifest,indent=2)+'\n');files.append('source-records.json')
archive=OUT/'Highland-revised-editable-package.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for name in files:z.write(OUT/name,name)
    for p in sorted(set(sources)):z.write(p,'reproduction/'+str(p.relative_to(ROOT)))
    z.write(OUT/'builder-regression.json','reproduction/deliverables/highland-refined/builder-regression.json')
    z.writestr('REPRODUCE.md','# Open or rebuild\n\nOpen Highland-revised-daylight-and-film.blend in Blender 5.0.1 or newer. Both scenes have portable render destinations and the sky is packed. Select the Daylight reference comparison scene for the still, or Dusk exterior film for native animation. The MP4 uses the separately documented real-time renderer.\n\nFor a scripted rebuild, change into reproduction/ and follow projects/highland-refined/README.md. Use Python with bpy 5.0.1 for Blender scripts and Python with Pillow/ReportLab for report.py/package.py. Node, local Chromium and FFmpeg are needed for movie capture. Run report.py after capture and validate-scene.py before package.py. Visual review is required; visual-review.json records the reviews for this delivered revision. The original architectural PDF is absent; all available drawing crops, photographs and registered source specifications used here are included.\n')
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    archive_report={'archive':archive.name,'files':len(z.infolist()),'crc_verified':True,**info(archive)}
(OUT/'archive-validation.json').write_text(json.dumps(archive_report,indent=2)+'\n')
print(json.dumps({'delivery':str(OUT),'decoded_frames':len(frames),'archive':archive_report},indent=2))
