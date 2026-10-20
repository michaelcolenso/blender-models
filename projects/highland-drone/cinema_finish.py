"""Grade, title, score and encode the Highland cinematic film.

Reads the per-shot Cycles frames written by cinema.py, finishes each frame in
a scope picture inside a 1920 x 1080 master, and encodes H.264 with the
mastered score. Python 3.11 with NumPy, Pillow and opencv-python-headless.
"""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SPEC = json.loads((HERE/'cinema.shots.json').read_text())
FPS = SPEC['fps']
W, H, PW, PH = 1920, 1080, 1920, 804
TOP = (H-PH)//2
FONTS = ROOT/'projects/highland-installation/immersive-film/assets/fonts'
GOLD = (222, 190, 136)
NOTE = 'Illustrative study · finishes, furnishings and lighting not surveyed'


def font(name, size):
    return ImageFont.truetype(str(FONTS/name), size)


def tracked(draw, xy, text, fnt, fill, spacing=0., anchor='l'):
    """Letter-spaced text; returns the drawn width."""
    widths = [draw.textlength(c, font=fnt) for c in text]
    total = sum(widths)+spacing*(len(text)-1)
    x, y = xy
    if anchor == 'r':
        x -= total
    elif anchor == 'c':
        x -= total/2
    for c, w in zip(text, widths):
        draw.text((x, y), c, font=fnt, fill=fill)
        x += w+spacing
    return total


def layer():
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    return im, ImageDraw.Draw(im)


def shadowed(im, radius=14, strength=150):
    """Soft dark halo behind light type over picture."""
    alpha = im.getchannel('A').filter(ImageFilter.GaussianBlur(radius))
    shade = Image.new('RGBA', im.size, (0, 0, 0, 0)); shade.putalpha(alpha.point(lambda v: min(255, v*strength//255)))
    return Image.alpha_composite(shade, im)


def build_titles():
    t = {}
    im, d = layer()
    x, y = 1262, TOP+96
    tracked(d, (x, y), 'OWNER PRESENTATION', font('NotoSans-Regular.ttf', 17), GOLD+(255,), 5.5)
    d.text((x-3, y+26), '200 W. Highland', font=font('NotoSerifDisplay-Regular.ttf', 76), fill=(246, 242, 234, 255))
    d.text((x, y+122), 'From the street to Corridor 208', font=font('NotoSerifDisplay-Italic.ttf', 28), fill=(232, 226, 214, 235))
    t['title'] = shadowed(im)
    for shot in SPEC['shots']:
        if not shot.get('label'):
            continue
        im, d = layer()
        n = [s for s in SPEC['shots'] if s.get('label')].index(shot)+1
        base = TOP+PH+46
        tracked(d, (96, base), f'{n:02d}', font('NotoSans-Regular.ttf', 17), GOLD+(255,), 3)
        d.line((140, base+12, 176, base+12), fill=GOLD+(200,), width=1)
        tracked(d, (192, base), shot['label'].upper(), font('NotoSans-Regular.ttf', 17), (226, 224, 218, 255), 4.2)
        t[shot['id']] = im
    im, d = layer()
    tracked(d, (W-96, TOP+PH+48), NOTE.upper(), font('NotoSans-Regular.ttf', 14), (168, 168, 162, 255), 2.4, 'r')
    t['note'] = im
    im, d = layer()
    tracked(d, (W/2, 392), 'OWNER PRESENTATION', font('NotoSans-Regular.ttf', 17), GOLD+(255,), 5.5, 'c')
    f = font('NotoSerifDisplay-Regular.ttf', 92); w = d.textlength('200 W. Highland', font=f)
    d.text(((W-w)/2, 420), '200 W. Highland', font=f, fill=(246, 242, 234, 255))
    f = font('NotoSerifDisplay-Italic.ttf', 30); line = 'Lobby 110  ·  Corridors 108 & 208  ·  Elevator M1'; w = d.textlength(line, font=f)
    d.text(((W-w)/2, 548), line, font=f, fill=(220, 214, 202, 255))
    t['end'] = im
    im, d = layer()
    small = font('NotoSans-Regular.ttf', 17)
    for j, line in enumerate((
            'Presentation study. Floor datums and circulation follow sheets A2.03, A2.04 and A3.11.',
            'Finishes, furnishings, lighting, planting, the slat wall and neighboring massing are illustrative; field verification required.',
            'Neighborhood footprints © OpenStreetMap contributors, ODbL 1.0  ·  Sky: Poly Haven, CC0  ·  Rendered natively in Blender Cycles')):
        w = d.textlength(line, font=small)
        d.text(((W-w)/2, 672+j*30), line, font=small, fill=(165, 165, 160, 255))
    t['credits'] = im
    return {k: np.asarray(v, dtype=np.float32)/255 for k, v in t.items()}


def ramp(t, a, b):
    return float(np.clip((t-a)/(b-a), 0, 1)) if b > a else float(t >= a)


def window(t, start, end, fade_in=.45, fade_out=.45):
    return min(ramp(t, start, start+fade_in), 1-ramp(t, end-fade_out, end))


def smooth(a, b, t):
    v = min(1., max(0., (t-a)/(b-a)))
    return v*v*(3-2*v)


def grade(img, exposure, rng, upscaled):
    """Display-referred finishing: halation, gentle S-curve, split tone, lens and grain."""
    img = img*(2**exposure)
    lum = img@np.array([.2126, .7152, .0722], np.float32)
    hi = np.clip((img-.74)/.26, 0, 1)
    small = cv2.resize(hi, (PW//4, PH//4), interpolation=cv2.INTER_AREA)
    glow = cv2.resize(cv2.GaussianBlur(small, (0, 0), 7), (PW, PH), interpolation=cv2.INTER_LINEAR)
    img = img+glow*np.array([1., .58, .36], np.float32)*.12
    if upscaled:
        img = img+.35*(img-cv2.GaussianBlur(img, (0, 0), 1.1))
    img = np.clip(img, 0, 1)
    img = img+(img*img*(3-2*img)-img)*.16
    w_shadow = ((1-lum)**2)[..., None]; w_light = (lum**2)[..., None]
    img = img+w_shadow*np.array([-.010, .002, .014], np.float32)+w_light*np.array([.012, .004, -.010], np.float32)
    img = .010+img*(1-.010)
    # Very slight lateral chromatic aberration, strongest at the frame edge.
    for ch, s in ((0, 1.0007), (2, .9993)):
        m = np.float32([[s, 0, (1-s)*PW/2], [0, s, (1-s)*PH/2]])
        img[..., ch] = cv2.warpAffine(img[..., ch], m, (PW, PH), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    yy, xx = np.mgrid[0:PH, 0:PW].astype(np.float32)
    r = np.sqrt(((xx-PW/2)/(PW/2))**2+((yy-PH/2)/(PW/2))**2)/np.sqrt(1+(PH/PW)**2)
    img = img*(1-.24*r**2.4)[..., None]
    grain = cv2.GaussianBlur(rng.standard_normal((PH, PW)).astype(np.float32), (0, 0), .65)*.022
    img = img+(grain*(.55+.45*(1-np.clip(lum, 0, 1))))[..., None]
    return np.clip(img, 0, 1)


def over(base, ov, alpha=1.):
    a = ov[..., 3:4]*alpha
    return base*(1-a)+ov[..., :3]*a


def section_gauge(frame, t_local, shot):
    """Live R1-to-R2 datum readout driven by the native car keyframes."""
    src = shot['src_start']+t_local*FPS
    t = (src-1)/FPS
    u = smooth(16, 17.8, t)  # build_blender.py keys the car with smooth(16,17.8,t)
    im = Image.fromarray((frame*255).astype(np.uint8))
    d = ImageDraw.Draw(im, 'RGBA')
    alpha = int(255*window(t_local, .5, shot['frames']/FPS, .5, .35))
    x, y0, y1 = 1724, TOP+250, TOP+560
    d.line((x, y0, x, y1), fill=GOLD+(alpha*120//255,), width=1)
    for yy, name in ((y1, 'R1  353.00'), (y0, 'R2  363.25')):
        d.line((x-6, yy, x+6, yy), fill=GOLD+(alpha,), width=1)
        tracked(d, (x+18, yy-9), name, font('NotoSans-Regular.ttf', 15), (226, 224, 218, alpha), 1.5)
    ym = y1+(y0-y1)*u
    d.ellipse((x-4, ym-4, x+4, ym+4), fill=(255, 226, 170, alpha))
    tracked(d, (x-18, ym-10), f'EL. {353+10.25*u:6.2f} FT', font('NotoSans-Regular.ttf', 15), (255, 236, 200, alpha), 1.5, 'r')
    return np.asarray(im, dtype=np.float32)/255


def frames(profile):
    for shot in SPEC['shots']:
        for j in range(1, shot['frames']+1):
            yield shot, j, ROOT/'build/highland-cinema/frames'/profile/shot['id']/f'{j:04d}.png'


def loudnorm(src, dst):
    probe = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-i', str(src), '-af', 'loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json', '-f', 'null', '-'],
                           capture_output=True, text=True).stderr
    m = json.loads(probe[probe.rindex('{'):probe.rindex('}')+1])
    flt = (f"loudnorm=I=-16:TP=-1.5:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
           f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', str(src), '-af', flt, '-ar', '48000', str(dst)], check=True)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--profile', default='local')
    p.add_argument('--output', type=Path, default=ROOT/'deliverables/highland-cinema')
    p.add_argument('--stills', default='', help='Only write graded stills for these film seconds, comma-separated')
    a = p.parse_args()
    import sys
    sys.path.insert(0, str(HERE))
    import cinema_score
    build = ROOT/'build/highland-cinema'; a.output.mkdir(parents=True, exist_ok=True)
    titles = build_titles()
    picture = sum(s['frames'] for s in SPEC['shots'])/FPS
    total = picture+cinema_score.END_CARD+cinema_score.TAIL
    count = round(total*FPS)
    listing = list(frames(a.profile))
    missing = [str(f) for _, _, f in listing if not f.exists()]
    stills = [float(s) for s in a.stills.split(',') if s]
    if missing and not stills:
        raise SystemExit(f'{len(missing)} frames missing, first {missing[0]}')
    if not stills:
        score = build/'Highland-cinema-score.wav'; info = cinema_score.synthesize(score)
        mastered = build/'Highland-cinema-score-mastered.wav'; loudnorm(score, mastered)
        movie = a.output/'Highland-cinema-1080p.mp4'
        lossless = build/'Highland-cinema-master-rgb.mkv'
        enc = subprocess.Popen(['ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                                '-c:v', 'libx264rgb', '-qp', '0', '-preset', 'ultrafast', str(lossless)], stdin=subprocess.PIPE)
    rng = np.random.default_rng(208)
    starts, t0 = {}, 0.
    for s in SPEC['shots']:
        starts[s['id']] = t0; t0 += s['frames']/FPS
    native = None
    stats = []
    for n in range(count):
        t = n/FPS
        if stills and not any(abs(t-s) < .5/FPS for s in stills):
            rng.standard_normal(1); continue
        canvas = np.zeros((H, W, 3), np.float32)
        if n < len(listing):
            shot, j, path = listing[n]
            raw = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
            native = raw.shape[1::-1]
            img = cv2.cvtColor(raw, cv2.COLOR_BGR2RGB).astype(np.float32)/(65535 if raw.dtype == np.uint16 else 255)
            upscaled = img.shape[1] != PW
            if upscaled:
                img = cv2.resize(img, (PW, PH), interpolation=cv2.INTER_LANCZOS4)
            img = grade(np.clip(img, 0, 1), shot.get('exposure', 0), rng, upscaled)
            if shot['id'] == '07-section':
                img = section_gauge(img, t-starts[shot['id']], shot)
            # Fade in from black on the arrival, out at the end of the corridor.
            fade = min(ramp(t, 0, 1.5), 1-ramp(t, picture-1.0, picture))
            canvas[TOP:TOP+PH] = img*fade
            stats.append(float(img.std()))
            if shot['id'] == '01-arrival':
                canvas = over(canvas, titles['title'], window(t, 1.1, 4.25, .8, .6))
            if shot.get('label'):
                local = t-starts[shot['id']]
                canvas = over(canvas, titles[shot['id']], window(local, .3, shot['frames']/FPS-.1, .45, .35))
            canvas = over(canvas, titles['note'], window(t, 1.5, picture, .8, .8)*.9)
        else:
            canvas = over(canvas, titles['end'], window(t, picture+.25, total-.55, .7, .6))
            canvas = over(canvas, titles['credits'], window(t, picture+.75, total-.55, .7, .6))
        out = (np.clip(canvas, 0, 1)*255+rng.uniform(-.5, .5, canvas.shape)).clip(0, 255).astype(np.uint8)
        if stills:
            Image.fromarray(out).save(build/f'still-{t:05.2f}s.png'); continue
        enc.stdin.write(out.tobytes())
    if stills:
        return
    enc.stdin.close()
    if enc.wait():
        raise SystemExit('ffmpeg failed')
    # Two-pass 10 Mbit/s H.264 High: phone-safe 8-bit 4:2:0, BT.709, about 38 MB.
    video = ['-c:v', 'libx264', '-preset', 'slow', '-profile:v', 'high', '-b:v', '10M', '-maxrate', '16M', '-bufsize', '20M',
             '-pix_fmt', 'yuv420p', '-vf', 'scale=out_color_matrix=bt709:out_range=tv', '-color_primaries', 'bt709', '-color_trc', 'bt709',
             '-colorspace', 'bt709', '-x264-params', 'keyint=48:min-keyint=24', '-passlogfile', str(build/'x264-2pass')]
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', str(lossless), *video, '-pass', '1', '-an', '-f', 'null', '-'], check=True)
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', str(lossless), '-i', str(mastered), '-map', '0:v', '-map', '1:a', *video, '-pass', '2',
                    '-c:a', 'aac', '-b:a', '256k', '-ar', '48000', '-movflags', '+faststart', '-t', f'{count/FPS:.4f}', str(movie)], check=True)
    # Stills, a timed shot sheet and a silent phone-gallery preview of the section.
    stills_dir = a.output/'stills'; stills_dir.mkdir(exist_ok=True)
    for name, at in (('01-title', 3.0), ('02-entry', 6.4), ('03-lobby', 9.0), ('04-slats', 11.6), ('06-elevator', 17.6), ('07-section', 20.3), ('08-corridor-208', 23.6)):
        subprocess.run(['ffmpeg', '-y', '-v', 'error', '-ss', str(at), '-i', str(lossless), '-frames:v', '1', '-q:v', '2', str(stills_dir/f'{name}.jpg')], check=True)
    tiles = []
    for s in SPEC['shots']:
        at = starts[s['id']]+s['frames']/FPS*.6
        tile = build/f'tile-{s["id"]}.png'
        subprocess.run(['ffmpeg', '-y', '-v', 'error', '-ss', f'{at:.3f}', '-i', str(lossless), '-frames:v', '1', '-vf', f'crop={PW}:{PH}:0:{TOP},scale=640:-2', str(tile)], check=True)
        tiles.append((s, at, Image.open(tile).convert('RGB')))
    sheet = Image.new('RGB', (1280, 4*(268+34)), (8, 8, 8)); d = ImageDraw.Draw(sheet)
    for k, (s, at, im) in enumerate(tiles):
        x, y = (k % 2)*640, (k//2)*(268+34)
        sheet.paste(im, (x, y+34)); tracked(d, (x+10, y+9), f'{s["id"].upper()}   {at:05.2f} S', font('NotoSans-Regular.ttf', 15), GOLD, 2)
    sheet.save(a.output/'Highland-cinema-shots.jpg', quality=90)
    sec = starts['07-section']
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-ss', f'{sec:.3f}', '-t', '3', '-i', str(lossless), '-vf',
                    f'crop={PW}:{PH}:0:{TOP},fps=12,scale=640:-2:flags=lanczos,split[a][b];[a]palettegen=stats_mode=diff[p];[b][p]paletteuse=dither=sierra2_4a',
                    '-loop', '0', str(a.output/'Highland-cinema-section.gif')], check=True)
    probe = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-count_frames', '-of', 'json', str(movie)]))
    video = next(s for s in probe['streams'] if s['codec_type'] == 'video'); audio = next(s for s in probe['streams'] if s['codec_type'] == 'audio')
    meter = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-i', str(movie), '-af', 'ebur128=peak=true', '-f', 'null', '-'], capture_output=True, text=True).stderr
    summary = meter[meter.rindex('Summary:'):]
    lufs = float(summary.split('I:')[1].split('LUFS')[0]); peak = float(summary.split('Peak:')[1].split('dBFS')[0])
    checks = {
        'frames': int(video['nb_read_frames']) == count, 'size': (video['width'], video['height']) == (W, H),
        'codec': video['codec_name'] == 'h264' and video['pix_fmt'] == 'yuv420p', 'fps': video['r_frame_rate'] == f'{FPS}/1',
        'audio': audio['codec_name'] == 'aac' and audio['channels'] == 2 and audio['sample_rate'] == '48000',
        'duration': abs(float(probe['format']['duration'])-count/FPS) < .05,
        'loudness': abs(lufs+16) < 1.0, 'true_peak': peak <= -1.0,
        'no_blank_shots': min(stats) > .02,
    }
    report = {
        'film': SPEC['film'], 'video': movie.name, 'sha256': hashlib.sha256(movie.read_bytes()).hexdigest(),
        'frames': count, 'fps': FPS, 'duration_s': round(count/FPS, 3), 'master': f'{W}x{H}', 'picture': f'{PW}x{PH} (2.39:1)',
        'render_profile': a.profile, 'native_render_size': native, 'upscaled_to_picture': native != (PW, PH),
        'rendered_frames': len(listing), 'shots': [{'id': s['id'], 'film_start_s': round(starts[s['id']], 3), 'frames': s['frames'],
                                                     'native_scene_frames': [s['src_start'], s['src_start']+s['frames']-1]} for s in SPEC['shots']],
        'loudness_lufs': lufs, 'true_peak_dbfs': peak, 'score': info, 'checks': checks,
        'shots_spec_sha256': hashlib.sha256((HERE/'cinema.shots.json').read_bytes()).hexdigest(),
        'finish_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }
    (a.output/'validation.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(checks, indent=2))
    if not all(checks.values()):
        raise SystemExit('Film validation failed')


if __name__ == '__main__':
    main()
