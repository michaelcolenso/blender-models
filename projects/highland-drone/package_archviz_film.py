"""Publish a checked native film with its Actions frame provenance."""
import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]


def main():
    parser=argparse.ArgumentParser();parser.add_argument('artifact',type=Path)
    parser.add_argument('--base-run',required=True);parser.add_argument('--final-run',required=True)
    parser.add_argument('--render-commit',required=True)
    parser.add_argument('--replacement-frames',type=int,nargs=2);args=parser.parse_args()
    if args.base_run!=args.final_run:
        assert args.replacement_frames and 1<=args.replacement_frames[0]<=args.replacement_frames[1]<=624
    else:assert args.replacement_frames is None
    source=args.artifact;target=ROOT/'deliverables/highland-blender';gallery=ROOT/'deliverables/highland-archviz'
    movie=source/'Highland-Blender-walkthrough.mp4'
    media=json.loads((source/'media-validation.json').read_text())
    native=json.loads((source/'Highland-walkthrough.validation.json').read_text())
    playback=json.loads((source/'playback-validation.json').read_text())
    assert hashlib.sha256(movie.read_bytes()).hexdigest()==media['video_sha256']
    assert media['resolution']==[540,960] and media['frames']==624
    assert native['look']=='archviz' and native['r1_to_r2_rise_in']==123
    assert not native['wall_collisions'] and not native['door_collisions']
    assert playback['decoded_frames']==624 and playback['progressive_playback_faststart']
    assert not playback['black_camera_frames'] and not playback['frozen_ranges_over_half_second']
    target.mkdir(parents=True,exist_ok=True);gallery.mkdir(parents=True,exist_ok=True)
    # Keep the exact prior study used in the before/after stills. The canonical
    # scene is about to become the upgraded film and must not become a baseline.
    baseline=gallery/'Highland-study-baseline.blend'
    expected=json.loads((gallery/'review-manifest.json').read_text())['baseline_scene_sha256']
    original=baseline if baseline.exists() else target/'Highland-walkthrough.blend'
    assert hashlib.sha256(original.read_bytes()).hexdigest()==expected,'Previous-study baseline does not match the still provenance'
    if not baseline.exists():shutil.copyfile(original,baseline)
    for name in ['Highland-Blender-walkthrough.mp4','Highland-walkthrough.blend',
                 'Highland-walkthrough.validation.json','Highland-Blender-poster.png',
                 'Highland-Blender-section.png','playback-validation.json','Highland-Blender-full-review.jpg']:
        shutil.copyfile(source/name,target/name)
    if (source/'native-frame-provenance.json').exists():
        shutil.copyfile(source/'native-frame-provenance.json',target/'native-frame-provenance.json')
    # A complete low-bandwidth GIF plays in the GitHub gallery on a phone.
    preview=target/'Highland-Blender-preview.gif'
    subprocess.run(['ffmpeg','-y','-v','error','-i',str(target/movie.name),'-vf',
        'fps=6,scale=234:416:flags=lanczos,split[a][b];[a]palettegen=max_colors=128:stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=3',
        '-loop','0',str(preview)],check=True)
    media.update({'look':'archviz','samples':16,'quality':'phone',
                  'render_commit':args.render_commit,'base_frame_run':args.base_run,
                  'final_run':args.final_run,'replacement_frames':args.replacement_frames or [],
                  'workflow_url':f'https://github.com/michaelcolenso/blender-models/actions/runs/{args.final_run}',
                  'preview':'Entire 26-second film at 6 fps, silent GIF; MP4 is 24 fps with stereo audio'})
    (target/'media-validation.json').write_text(json.dumps(media,indent=2)+'\n')
    shutil.copyfile(target/movie.name,gallery/'Highland-archviz-walkthrough.mp4')
    shutil.copyfile(preview,gallery/'Highland-archviz-preview.gif')
    shutil.copyfile(target/'Highland-Blender-poster.png',gallery/'Highland-archviz-film-poster.png')
    (target/'README.md').write_text('''# Highland / upgraded Blender walkthrough

![Full upgraded walkthrough preview](Highland-Blender-preview.gif)

[Watch the full MP4](Highland-Blender-walkthrough.mp4?raw=true) · [Download the matching Blender scene](Highland-walkthrough.blend?raw=true) · [Phone gallery and comparisons](../highland-archviz/README.md)

The complete 26-second walkthrough is rendered in native Blender Cycles at **540 × 960, 24 fps**, with denoising, AgX, subtle bloom, captions, location map and stereo AAC sound. The GIF above previews the entire tour at 6 fps without audio; use the MP4 for full motion and sound.

The film includes HDRI lighting, individual leaf canopies, warm curtained windows, entrance handrails and planting, lobby furniture and art, tile grout, fine wood grain, woven carpet and wall accent lighting. Opening doors, the moving elevator and the glass-and-brass architectural section remain native animation. The camera keeps the cab feature in view until the section pullback, then returns to Corridor 208.

Open the scene in **Blender 5.0.1 or newer** and play frames 1–624. HDRI and sound are packed. The floor datums and circulation follow the drawings; finishes, furniture, planting, facade details and nearby massing remain illustrative.

Sky: [Poly Haven / CC0](../../projects/highland-drone/assets/README.md). Surrounding massing: [© OpenStreetMap contributors](https://www.openstreetmap.org/copyright), ODbL 1.0, with approximate registration and assumed heights.

- [Poster](Highland-Blender-poster.png)
- [Elevator section](Highland-Blender-section.png)
- [Timed full-film review sheet](Highland-Blender-full-review.jpg)
- [Native camera and door checks](Highland-walkthrough.validation.json)
- [Decoded video, audio and playback checks](playback-validation.json)
- [Render provenance](media-validation.json)
- [Rebuild and Actions instructions](../../projects/highland-drone/BLENDER.md)
''')
    # Retain the four 24-sample still comparisons and their own provenance.
    readme=gallery/'README.md';content=readme.read_text()
    end=content.find('## Editable scene and render status')
    if end<0:end=content.index('## Scene, sources and verification')
    content=content[content.index('## Lobby'):end]
    intro='''# Highland / upgraded full walkthrough

![Full animated tour preview](Highland-archviz-preview.gif)

[Watch the upgraded MP4](Highland-archviz-walkthrough.mp4?raw=true) · [Matching animated Blender scene](../highland-blender/Highland-walkthrough.blend?raw=true)

The entire **26-second** tour now uses the upgraded Cycles lighting, materials and planting. The MP4 is **540 × 960 / 24 fps with stereo audio**; the GIF previews all 26 seconds at 6 fps without sound. Doors open on approach, the elevator rises from R1 to R2, and the glass-and-brass section leads back to Corridor 208. Finishes and unverified details remain illustrative.

The stills below compare this visual treatment with the previous study at matching frame numbers. They use 24 samples; the full animation uses 16 samples with denoising.

'''
    outro='''## Scene, sources and verification

Use the [matching film scene](../highland-blender/Highland-walkthrough.blend?raw=true) in Blender 5.0.1 or newer. It includes the revised cutaway transition, packed CC0 Poly Haven HDRI and packed soundtrack. The earlier [still-review scene](Highland-archviz.blend?raw=true) remains available for the four preview images.

[Full-film review sheet](../highland-blender/Highland-Blender-full-review.jpg) · [Playback checks](../highland-blender/playback-validation.json) · [Native camera checks](../highland-blender/Highland-walkthrough.validation.json) · [Film provenance](../highland-blender/media-validation.json)

The model retains drawing-based circulation and the 123-inch R1-to-R2 rise. Planting, warm window back panels, furniture, finishes, facade details and fixture optics are illustrative. No manufacturer IES profiles or paid botanical libraries are included. Nearby massing uses [© OpenStreetMap contributors](https://www.openstreetmap.org/copyright) / ODbL 1.0, with approximate placement and heights. [HDRI source and license](../../projects/highland-drone/assets/README.md) · [Still-image provenance](review-manifest.json) · [Build and render instructions](../../projects/highland-drone/BLENDER.md)
'''
    readme.write_text(intro+content+outro)
    print('Published checked archviz film and matching scene:',target)


if __name__=='__main__':main()
