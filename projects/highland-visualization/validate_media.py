"""Validate the complete encoded movie and bind it to its capture evidence."""
import hashlib
import json
import struct
import subprocess
from pathlib import Path
from PIL import Image, ImageChops, ImageStat

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'deliverables/highland-visualization'
CACHE=ROOT/'build/highland-visualization/film-frames'


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    movie=OUT/'Highland-dusk-drawing-reconciled-18s.mp4'
    probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-count_frames','-show_streams','-show_format','-of','json',str(movie)]))
    streams=probe['streams'];assert len(streams)==1
    v=streams[0]
    assert (v['width'],v['height'],v['codec_name'],v['pix_fmt'])==(1280,720,'h264','yuv420p')
    assert v['r_frame_rate']==v['avg_frame_rate']=='24/1'
    assert int(v['nb_read_frames'])==int(v['nb_frames'])==432
    assert abs(float(v['duration'])-18)<.001
    assert all(v[k]=='bt709' for k in ('color_space','color_transfer','color_primaries'))
    assert v['color_range']=='tv'
    decoded=subprocess.check_output(['ffmpeg','-v','error','-i',str(movie),'-map','0:v:0','-f','framemd5','-']).decode()
    lines=[line for line in decoded.splitlines() if line and not line.startswith('#')]
    hashes=[line.rsplit(',',1)[-1].strip() for line in lines]
    assert len(hashes)==len(set(hashes))==432
    (OUT/'decoded-frame-checksums.txt').write_text(decoded)
    capture=json.loads((OUT/'film-capture.json').read_text())
    encoding=json.loads((OUT/'film-encoding.json').read_text())
    cache=json.loads((CACHE/'manifest.json').read_text())
    assert capture['signature']==encoding['signature']==cache['signature']
    assert capture['stats']['msaaSamples']==4 and capture['stats']['fxaa']
    assert capture['stats']['aaScope']=='rails and window frames'
    assert capture['stats']['glError']==capture['finalStats']['glError']==0 and not capture['errors']
    assert len(list(CACHE.glob('frame-*.png')))==432
    frame_hashes={}
    all_variations=[]
    for f in range(432):
        with Image.open(CACHE/f'frame-{f:03}.png') as im:
            assert im.size==(1280,720)
            all_variations.append(max(ImageStat.Stat(im.convert('RGB').resize((128,72))).stddev)/255)
        frame_hashes[f'frame-{f:03}']=sha(CACHE/f'frame-{f:03}.png')
    assert min(all_variations)>.03
    (OUT/'capture-frame-hashes.json').write_text(json.dumps(frame_hashes,indent=2)+'\n')
    variations=[]
    for f in [0,72,144,216,288,360,431]:
        with Image.open(OUT/f'film-review/frame-{f:03}.png') as im:
            variations.append(max(ImageStat.Stat(im.convert('RGB').resize((128,72))).stddev)/255)
    assert min(variations)>.03
    aa=json.loads((OUT/'aa-comparison.json').read_text())
    assert aa['baseline']['msaaSamples']==0 and aa['revised']['msaaSamples']==4
    a=Image.open(OUT/'film-review/frame-216.png').convert('RGB')
    b=Image.open(OUT/'film-review/frame-216-fxaa-only.png').convert('RGB')
    diff=ImageChops.difference(a,b)
    assert diff.getbbox()
    # Verify the container places its metadata before video data for streaming.
    atoms=[];data=movie.read_bytes();offset=0
    while offset+8<=len(data):
        size,kind=struct.unpack_from('>I4s',data,offset)
        if size==1:size=struct.unpack_from('>Q',data,offset+8)[0]
        assert size>=8
        atoms.append(kind.decode('ascii'));offset+=size
    assert atoms.index('moov')<atoms.index('mdat')
    source=json.loads((OUT/'source-validation.json').read_text())
    assert sha(ROOT/source['source_native'])==source['source_native_sha256']
    assert sha(ROOT/source['source_glb'])==source['source_glb_sha256']
    result={'status':'PASS','source_native_sha256':source['source_native_sha256'],'source_glb_sha256':source['source_glb_sha256'],'movie_sha256':sha(movie),'decoded_frames':len(hashes),'distinct_decoded_frames':len(set(hashes)),
            'resolution':[1280,720],'duration_seconds':float(v['duration']),'fps':24,'codec':v['codec_name'],
            'pixel_format':v['pix_fmt'],'color_space':'BT.709 limited range','faststart':True,
            'lossless_capture_frames':432,'signature':capture['signature'],'aa_samples':4,'fxaa':True,
            'all_frame_minimum_pixel_stddev':min(all_variations),'review_frame_minimum_pixel_stddev':min(variations),'browser_errors':capture['errors'],
            'aa_baseline_and_revised_images_differ':True,'scope':'Full decode, distinct frames, capture completeness and encoding checks. See visual-review.json for visual judgement.'}
    (OUT/'media-validation.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    main()
