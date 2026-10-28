"""Package native Cycles review frames for a phone and record provenance."""
import argparse
import hashlib
import json
import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[4]
VIEWS={1:'Exterior',160:'Lobby',319:'Elevator',529:'Corridor'}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--scene',type=Path,default=ROOT/'build/highland-archviz/Highland-archviz.blend')
    parser.add_argument('--before',type=Path,default=ROOT/'build/highland-archviz-before/frames')
    parser.add_argument('--output',type=Path,default=ROOT/'projects/highland/deliverables/archviz')
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    validation=json.loads(args.scene.with_suffix('.validation.json').read_text())
    assert validation['look']=='archviz' and validation['frames']==624
    assert not validation['wall_collisions'] and not validation['door_collisions']
    assert validation['r1_to_r2_rise_in']==123
    font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',22)
    records=[]
    for frame,label in VIEWS.items():
        source=args.scene.parent/'frames'/f'frame_{frame:04d}.png'
        before=args.before/f'frame_{frame:04d}.png'
        with Image.open(source) as image:
            assert image.size==(540,960),f'Unexpected review size: {source}'
            image.load();after=image.convert('RGB')
        with Image.open(before) as image:
            assert image.size==after.size,f'Comparison dimensions differ: {before}'
            image.load();prior=image.convert('RGB')
        name=f'Highland-archviz-{label.lower()}.png'
        shutil.copyfile(source,args.output/name)
        canvas=Image.new('RGB',(1080,1010),(15,23,27));canvas.paste(prior,(0,50));canvas.paste(after,(540,50))
        draw=ImageDraw.Draw(canvas);draw.text((24,13),'PREVIOUS STUDY',font=font,fill=(180,195,198))
        draw.text((564,13),'ARCHVIZ / '+label.upper(),font=font,fill=(231,202,146))
        canvas.save(args.output/f'Compare-{label.lower()}.jpg',quality=91)
        records.append({'frame':frame,'time_s':round((frame-1)/24,3),'view':label,'image':name,
                        'sha256':hashlib.sha256(source.read_bytes()).hexdigest()})
    shutil.copyfile(args.scene,args.output/args.scene.name)
    shutil.copyfile(args.scene.with_suffix('.validation.json'),args.output/args.scene.with_suffix('.validation.json').name)
    manifest={'renderer':'Blender 5.0.1 / Cycles CPU / denoised','dimensions':[540,960],
              'samples':24,'scene_sha256':hashlib.sha256(args.scene.read_bytes()).hexdigest(),
              'baseline_scene_sha256':hashlib.sha256((args.before.parent/'Highland-study.blend').read_bytes()).hexdigest(),
              'views':records,'status':'Four native stills; upgraded full animation not rendered',
              'comparison':'Prior published .blend, matching frame numbers, dimensions and sample count'}
    (args.output/'review-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print('Packaged four Blender stills, comparisons and editable scene:',args.output)


if __name__=='__main__':main()
