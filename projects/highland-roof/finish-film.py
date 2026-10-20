"""Normalize H.264/MP4 color tags without changing the compressed image content."""
import hashlib
import json
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'deliverables/highland-roof'


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def probe(p):
    return json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-of','json',str(p)]))['streams'][0]


def main():
    movie=OUT/'Highland-dusk-geometry-revised-18s.mp4'
    info=probe(movie)
    expected={'color_space':'bt709','color_primaries':'bt709','color_transfer':'bt709','color_range':'tv'}
    assert info.get('color_space')=='bt709' and info.get('color_range')=='tv', 'This helper only normalizes primaries/transfer tags on the known limited-range BT.709 encode.'
    before=sha(movie)
    changed=not all(info.get(k)==v for k,v in expected.items())
    if changed:
        folder=ROOT/'build/highland-geometry/color-normalization';folder.mkdir(parents=True,exist_ok=True)
        temporary=folder/'normalized.mp4'
        subprocess.run(['ffmpeg','-y','-v','error','-i',str(movie),'-map','0:v:0','-c:v','copy',
                        '-bsf:v','h264_metadata=colour_primaries=1:transfer_characteristics=1:matrix_coefficients=1:video_full_range_flag=0',
                        '-color_range','tv','-colorspace','bt709','-color_primaries','bt709','-color_trc','bt709',
                        '-movflags','+faststart',str(temporary)],check=True)
        normalized=probe(temporary)
        assert all(normalized.get(k)==v for k,v in expected.items())
        assert normalized['nb_frames']==info['nb_frames'] and normalized['duration']==info['duration']
        original=folder/f'original-{before[:12]}.mp4'
        movie.replace(original);temporary.replace(movie)
    encoding=json.loads((OUT/'film-encoding.json').read_text())
    encoding['bytes']=movie.stat().st_size
    encoding['color_normalization']='color-normalization.json'
    (OUT/'film-encoding.json').write_text(json.dumps(encoding,indent=2)+'\n')
    result={'normalization_applied':changed,'original_sha256':before,'movie_sha256':sha(movie),
            'method':'Lossless stream copy with H.264 SPS and MP4 primaries/transfer/matrix/range tags normalized to BT.709 limited range. No video re-encoding.',
            'verified_tags':expected,'reason':'The PNG-to-libx264 encode can inherit unspecified per-frame primaries/transfer tags despite the output flags.'}
    (OUT/'color-normalization.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))


if __name__=='__main__':
    main()
