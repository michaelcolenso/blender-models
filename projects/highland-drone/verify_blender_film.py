"""Check the finished native Blender movie and make a timed visual review sheet."""
import argparse
import json
import struct
import subprocess
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


def verify(movie, output):
    probe=json.loads(subprocess.check_output([
        'ffprobe','-v','error','-show_streams','-show_format','-of','json',str(movie)]))
    video=next(s for s in probe['streams'] if s['codec_type']=='video')
    audio=next(s for s in probe['streams'] if s['codec_type']=='audio')
    assert (video['codec_name'],video['pix_fmt'],video['r_frame_rate'],int(video['nb_frames']))==('h264','yuv420p','24/1',624)
    assert (video['width'],video['height'])==(540,960)
    assert audio['codec_name']=='aac' and audio['channels']==2
    assert abs(float(probe['format']['duration'])-26)<.06
    atoms=[]
    with movie.open('rb') as stream:
        while header:=stream.read(8):
            assert len(header)==8
            length,kind=struct.unpack('>I4s',header);header_length=8
            if length==1:length=struct.unpack('>Q',stream.read(8))[0];header_length=16
            atoms.append(kind.decode('ascii'))
            if length==0:break
            assert length>=header_length
            stream.seek(length-header_length,1)
    assert atoms.index('moov')<atoms.index('mdat'),'MP4 is not optimized for progressive phone playback'
    raw=subprocess.check_output([
        'ffmpeg','-v','error','-i',str(movie),'-an','-vf','scale=54:96',
        '-pix_fmt','rgb24','-f','rawvideo','pipe:1'])
    frames=np.frombuffer(raw,dtype=np.uint8).reshape(-1,96,54,3)
    assert len(frames)==624
    # Exclude the captions and map when looking for a black camera view.
    center=frames[:,24:72,13:40,:].astype(float)
    black_fraction=(center.max(axis=3)<8).mean(axis=(1,2))
    black_frames=(np.flatnonzero(black_fraction>.98)+1).tolist()
    assert not black_frames,f'Black camera views in frames {black_frames}'
    deltas=np.abs(frames[1:].astype(float)-frames[:-1].astype(float)).mean(axis=(1,2,3))
    identical=[];start=None
    for i,delta in enumerate(deltas):
        if delta==0 and start is None:start=i+1
        if delta!=0 and start is not None:
            if i+1-start>=12:identical.append([start,i+1])
            start=None
    if start is not None and 624-start>=12:identical.append([start,624])
    assert not identical,f'Unexpected frozen video ranges: {identical}'
    # Inspect the largest changes and chunk joins visually rather than treating
    # deliberate camera turns and the architectural section as encoding errors.
    jumps=[{'frame':int(j+2),'mean_rgb_change':round(float(deltas[j]),3)}
           for j in np.argsort(deltas)[-10:][::-1]]
    joins=[{'frame':f,'mean_rgb_change':round(float(deltas[f-2]),3)}
           for f in range(40,625,39)]
    pcm=subprocess.check_output([
        'ffmpeg','-v','error','-i',str(movie),'-vn','-ac','2','-ar','44100',
        '-f','f32le','pipe:1'])
    samples=np.frombuffer(pcm,dtype='<f4').reshape(-1,2)
    peak=float(np.max(np.abs(samples)));rms=float(np.sqrt(np.mean(samples**2)))
    assert .005<peak<1 and rms>.0005,'Silent or clipped soundtrack'
    output.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='highland-film-review-') as temp:
        subprocess.run(['ffmpeg','-v','error','-i',str(movie),'-vf',
                        'fps=1,scale=162:288:flags=lanczos',str(Path(temp)/'%02d.png')],check=True)
        thumbs=sorted(Path(temp).glob('*.png'));assert len(thumbs)==26
        sheet=Image.new('RGB',(810,1836),(12,21,28));draw=ImageDraw.Draw(sheet)
        font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',12)
        for i,path in enumerate(thumbs):
            x,y=(i%5)*162,(i//5)*306
            draw.text((x+8,y+2),f'{i:02d} seconds',font=font,fill=(232,203,150))
            with Image.open(path) as thumb:sheet.paste(thumb,(x,y+18))
        sheet.save(output/'Highland-Blender-full-review.jpg',quality=92)
    report={'decoded_frames':len(frames),'duration_seconds':float(probe['format']['duration']),
            'resolution':[video['width'],video['height']],'video_codec':video['codec_name'],
            'pixel_format':video['pix_fmt'],'fps':video['r_frame_rate'],
            'progressive_playback_faststart':True,
            'audio_codec':audio['codec_name'],'audio_channels':audio['channels'],
            'audio_peak':round(peak,5),'audio_rms':round(rms,5),
            'black_camera_frames':black_frames,'frozen_ranges_over_half_second':identical,
            'largest_frame_changes':jumps,'render_chunk_joins':joins}
    (output/'playback-validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('movie',type=Path)
    parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    verify(args.movie,args.output)
