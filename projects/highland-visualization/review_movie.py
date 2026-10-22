"""Extract the actual encoded opening, middle and closing frames plus poster."""
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageChops, ImageStat

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'deliverables/highland-visualization'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    movie=OUT/'Highland-dusk-drawing-reconciled-18s.mp4'
    folder=OUT/'decoded-review';folder.mkdir(exist_ok=True)
    selected=[0,216,431]
    expression='select='+'+'.join(f'eq(n\\,{n})' for n in selected)
    subprocess.run(['ffmpeg','-y','-v','error','-i',str(movie),'-vf',expression,
        '-fps_mode','vfr',str(folder/'decoded-%02d.png')],check=True)
    records={};errors={}
    for i,frame in enumerate(selected,1):
        destination=folder/f'frame-{frame:03}.png'
        (folder/f'decoded-{i:02}.png').replace(destination)
        records[str(destination.relative_to(OUT))]=sha(destination)
        with Image.open(destination) as decoded, Image.open(OUT/f'film-review/frame-{frame:03}.png') as source:
            difference=ImageStat.Stat(ImageChops.difference(decoded.convert('RGB'),source.convert('RGB')))
            errors[f'frame-{frame:03}']=sum(difference.mean)/3
            assert errors[f'frame-{frame:03}']<8,'Unexpected encode/decode color or image change'
    poster=OUT/'Highland-dusk-poster.png'
    shutil.copyfile(folder/'frame-216.png',poster)
    result={'movie_sha256':sha(movie),'decoded_frame_files':records,
        'decoded_vs_capture_mean_abs_rgb_error':errors,'poster_frame':217,'poster_file':poster.name,'poster_sha256':sha(poster)}
    (OUT/'poster.json').write_text(json.dumps(result,indent=2)+'\n')
    print('Extracted three decoded review frames and the frame-217 poster',flush=True)


if __name__=='__main__':main()
