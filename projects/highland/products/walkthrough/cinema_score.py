"""Original score and sound design for the Highland cinematic film.

Everything is synthesized here with NumPy, so no licensed music or sample
library is involved. Felt-piano chords and a pad change on the picture cuts (film v2
dropped the arpeggio). Ambience follows the story: street air and wind outside, a warm
room tone inside, faint footsteps on stone then carpet, and effects land on the native
door, chime and elevator events, all derived from cinema.shots.json.
"""
import json
import wave
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
SPEC = json.loads((HERE/'cinema.shots.json').read_text())
FPS = SPEC['fps']
SR = 48_000
END_CARD = 3.0
TAIL = .75
RNG = np.random.default_rng(200)


def timeline():
    """Output cut times (s) and a map from native scene frames to film time."""
    cuts, t = [], 0.
    for shot in SPEC['shots']:
        cuts.append((shot['id'], t, shot))
        t += shot['frames']/FPS
    return cuts, t


def film_time(src_frame, shot_id):
    for sid, start, shot in timeline()[0]:
        if sid == shot_id and shot['src_start'] <= src_frame < shot['src_start']+shot['frames']:
            return start+(src_frame-shot['src_start'])/FPS
    raise ValueError(f'Frame {src_frame} is not in shot {shot_id}')


def midi(n):
    return 440*2**((n-69)/12)


def shape(x, lo=None, hi=None, order=2):
    """Zero-phase Butterworth-shaped filter applied in the frequency domain."""
    spec = np.fft.rfft(x, axis=0)
    f = np.fft.rfftfreq(len(x), 1/SR)[:, None] if x.ndim == 2 else np.fft.rfftfreq(len(x), 1/SR)
    gain = np.ones_like(f)
    if hi:
        gain = gain/np.sqrt(1+(f/hi)**(2*order))
    if lo:
        gain = gain/np.sqrt(1+(lo/np.maximum(f, 1e-3))**(2*order))
    return np.fft.irfft(spec*gain, len(x), axis=0)


def place(buf, start, sig, pan=.5, gain=1.):
    i = int(round(start*SR))
    if i >= len(buf):
        return
    sig = sig[:len(buf)-i]
    buf[i:i+len(sig), 0] += sig*gain*np.sqrt(1-pan)
    buf[i:i+len(sig), 1] += sig*gain*np.sqrt(pan)


def felt_piano(freq, dur=4.5, vel=.6):
    t = np.arange(int(dur*SR))/SR
    out = np.zeros_like(t)
    for k in range(1, 11):
        fk = k*freq*np.sqrt(1+.00035*k*k)
        if fk > 14000:
            break
        amp = vel**(.6+.15*k)/k**1.15*np.exp(-.12*k)
        out += amp*np.sin(2*np.pi*fk*t+RNG.uniform(0, 6.28))*np.exp(-t*(.7+.38*k))
    attack = np.minimum(t/.006, 1)
    thump = RNG.standard_normal(len(t))*np.exp(-t/.012)*.04*vel
    return (out*attack+shape(thump, 80, 900))*.75


def bell(freq, dur=3.5, vel=.5):
    t = np.arange(int(dur*SR))/SR
    out = np.zeros_like(t)
    for ratio, amp, decay in ((1, 1, 1.1), (2.0, .45, 1.6), (2.76, .3, 2.4), (5.4, .12, 4.), (8.9, .05, 6.)):
        out += amp*np.sin(2*np.pi*freq*ratio*t)*np.exp(-t*decay)
    return out*np.minimum(t/.002, 1)*vel*.3


def pad(notes, dur, level=.06):
    t = np.arange(int(dur*SR))/SR
    left = np.zeros_like(t); right = np.zeros_like(t)
    for j, n in enumerate(notes):
        for detune, pan in ((-.07, .2), (0, .5), (.07, .8)):
            f = midi(n+detune)
            voice = np.zeros_like(t)
            for k in range(1, 12):
                if k*f > 9000:
                    break
                voice += np.sin(2*np.pi*k*f*t+RNG.uniform(0, 6.28))/k*np.exp(-k/3.2)
            voice *= 1+.12*np.sin(2*np.pi*(.13+.03*j)*t)
            left += voice*np.sqrt(1-pan); right += voice*np.sqrt(pan)
    env = np.minimum(np.minimum(t/1.4, 1), np.clip((dur-t)/1.2, 0, 1))
    return np.stack((left, right), 1)*env[:, None]*level/len(notes)


def noise(dur):
    return RNG.standard_normal(int(dur*SR))


def reverb(x, seconds=2.8, wet=.32):
    n = int(seconds*SR); t = np.arange(n)/SR
    ir = np.stack([shape(noise(seconds), 120, 7000)*np.exp(-t*6.9/seconds) for _ in range(2)], 1)
    ir[:int(.012*SR)] = 0
    ir /= np.sqrt(np.sum(ir**2, 0))
    size = 1 << int(np.ceil(np.log2(len(x)+n)))
    out = np.fft.irfft(np.fft.rfft(x, size, axis=0)*np.fft.rfft(ir, size, axis=0), size, axis=0)[:len(x)]
    return x*(1-wet)+out*wet*2.2


# Chord voicings in MIDI: bass, pad, top voice (melody note).
CHORDS = {
    'Dmaj9': (38, (50, 57, 61, 64, 66), (62, 66, 69, 73, 76)),
    'Bm9': (35, (47, 54, 57, 62, 64), (59, 62, 66, 69, 73)),
    'Gmaj7#11': (31, (43, 50, 54, 59, 61), (55, 59, 62, 66, 73)),
    'Asus': (33, (45, 52, 55, 59, 62), (57, 62, 64, 69, 71)),
    'D/F#': (30, (42, 50, 54, 57, 64), (66, 69, 74, 78, 81)),
    'Gmaj9': (31, (43, 50, 54, 57, 59), (62, 66, 69, 71, 74)),
    'A': (33, (45, 52, 57, 61, 64), (61, 64, 69, 73, 76)),
}
# Shot ID -> chord; the end card resolves home.
HARMONY = {'01-arrival': 'Dmaj9', '02-entry': 'Bm9', '03-lobby': 'Bm9', '04-slats': 'Gmaj7#11',
           '05-corridor-108': 'Gmaj7#11', '06-elevator': 'Asus', '07-section': 'D/F#', '08-corridor-208': 'Gmaj9',
           '09-release': 'Dmaj9'}  # back outside: home chord, then A and the end-card resolution
def gusts(dur, rate=.35, depth=.6):
    """Slow random amplitude envelope (wind gusts), 0..1."""
    n = int(dur*SR); k = max(4, int(dur*rate)+3)
    pts = RNG.uniform(1-depth, 1, k)
    return np.interp(np.linspace(0, k-1, n), np.arange(k), pts)


def step(tile=True, vel=1.):
    """One soft footstep: heel thump plus, on tile, a short bright scuff."""
    d = .16; t = np.arange(int(d*SR))/SR
    body = shape(noise(d), 60, 260)*np.exp(-t/.025)*.5
    if tile:
        body += shape(noise(d), 1500, 5000)*np.exp(-t/.008)*.25
    else:  # carpet: duller and quieter
        body = shape(body, None, 500)*.6
    return body*vel


def synthesize(path):
    cuts, picture = timeline()
    total = picture+END_CARD+TAIL
    start_of = {sid: start for sid, start, _ in cuts}
    music = np.zeros((int(total*SR), 2)); fx = np.zeros_like(music); bed = np.zeros_like(music)
    sections = [(start, HARMONY[sid]) for sid, start, _ in cuts]
    # Last bars of the release turn to A, resolving to D on the end card.
    sections.append((picture-1.5, 'A')); sections.append((picture, 'Dmaj9'))
    # Music: felt-piano chords rolled once per cut over a soft pad. No arpeggio.
    for j, (start, name) in enumerate(sections):
        end = sections[j+1][0] if j+1 < len(sections) else total-TAIL
        bass, voicing, top = CHORDS[name]
        hero = name == 'D/F#'
        bed_pad = pad(voicing, end-start+1.8, .036 if hero else .026)
        air = pad([n+24 for n in voicing[2:]], end-start+1.8, .009 if hero else .005)
        for ch, side in ((0, 0), (1, 1)):
            place(music, max(0, start-.6), bed_pad[:, ch]+air[:, ch], side)
        t = np.arange(int((end-start+2.5)*SR))/SR
        sub = np.sin(2*np.pi*midi(bass+12)*t)*.045
        sub *= np.minimum(np.minimum(t/.8, 1), np.clip((end-start+1.2-t)/1.2, 0, 1))
        place(music, start, sub, .5)
        if start < picture-1.6:  # the turn to A and the end card get their own resolution below
            for k, note in enumerate((bass+12,)+voicing[1:4]):
                place(music, start+.05+k*.045+RNG.normal(0, .004), felt_piano(midi(note), 5.5, .34), .35+.1*k)
            # One melody note per cut, an octave up for the section reveal.
            place(music, start+.6, felt_piano(midi(top[-1]+(12 if hero else 0)), 5., .4), .62)
    # Final resolution on the end card: low D, the chord and a high shimmer, fading out cleanly.
    res = picture
    for k, note in enumerate((38, 50, 57, 62, 66, 69)):
        place(music, res+k*.06, felt_piano(midi(note), 7., .55 if k < 2 else .4), .4+.05*k)
    place(music, res+.9, felt_piano(midi(81), 6., .3), .7)
    music = reverb(music, 3.2, .38)
    # Decorrelated reverb tails differ slightly in level; recentre the music bus.
    music *= np.sqrt(np.mean(music**2))/np.sqrt(np.mean(music**2, 0))

    # Ambience beds, cross-faded on the story beats (times come from the cut list).
    lobby = start_of['03-lobby']; corridor = start_of['05-corridor-108']
    elevator = start_of['06-elevator']; section = start_of['07-section']; upper = start_of['08-corridor-208']
    release = start_of['09-release']
    door = film_time(97, '02-entry')

    def env(t, pts):
        return np.interp(t, [p[0] for p in pts], [p[1] for p in pts])
    t = np.arange(len(bed))/SR
    # Exterior: urban room tone, distant traffic hum and wind in the trees (wide, decorrelated).
    street = np.stack([shape(noise(total), 70, 900)*.020+shape(noise(total), 35, 160)*.030 for _ in range(2)], 1)
    wind = np.stack([shape(noise(total), 900, 5200)*gusts(total)*.012 for _ in range(2)], 1)
    outside = street+wind
    # As the door opens the outside air dulls (low-passed copy) before the cut to the lobby.
    muffled = shape(outside, None, 450)
    out_gain = env(t, [(0, 0), (1.5, 1), (door, 1), (lobby, .25), (lobby+1, 0), (release-1, 0), (release+1.2, 1),
                       (picture+1, 1), (total, 0)])
    dull = env(t, [(0, 0), (door, 0), (lobby, 1), (release, 0)])[:, None]
    bed += (outside*(1-dull)+muffled*dull)*out_gain[:, None]
    for when, pan in ((1.2, .2), (3.4, .85), (release+1.5, .7)):
        tt = np.arange(int(2.6*SR))/SR
        place(bed, when, shape(noise(2.6), 300, 2500)*np.sin(np.pi*tt/2.6)**3*.03, pan)
    # Interior: warm, low air-handling tone; corridor 208 is quieter and slightly darker.
    room = np.stack([shape(noise(total), 45, 420)*.016 for _ in range(2)], 1)
    room += (np.sin(2*np.pi*118*t)*.0025)[:, None]
    in_gain = env(t, [(0, 0), (door, 0), (lobby, 1), (section-.4, 1), (section, .35), (upper, .35), (upper+.4, .75),
                      (release-.6, .75), (release+.8, 0)])
    bed += room*in_gain[:, None]

    # Entry: latch release, then the glass door's pivot swing.
    place(fx, door-.18, shape(noise(.05), 1800, 7000)*np.exp(-np.arange(int(.05*SR))/SR/.006)*.10, .5)
    tt = np.arange(int(1.4*SR))/SR
    place(fx, door, shape(noise(1.4), 200, 1800)*np.sin(np.pi*np.minimum(tt/1.4, 1))**2*.045, .5)
    place(fx, door+1.25, shape(noise(.08), 1500, 6000)*np.exp(-np.arange(int(.08*SR))/SR/.01)*.10, .5)
    # Very faint footsteps: stone in the lobby, carpet from Corridor 108 to the elevator landing.
    when, k = lobby+.4, 0
    while when < elevator-.3:
        place(fx, when+RNG.normal(0, .015), step(when < corridor, .5 if when < corridor else .4), .44 if k % 2 else .56)
        when += .62; k += 1
    # Elevator M1: arrival chime, then the brushed-metal door slide.
    chime = film_time(289, '06-elevator')
    place(fx, chime-.25, bell(midi(88), vel=.5), .45); place(fx, chime+.12, bell(midi(84), vel=.45), .55)
    tt = np.arange(int(1.2*SR))/SR
    slide = shape(noise(1.2), 80, 700)*.05+shape(noise(1.2), 2500, 7000)*.008
    place(fx, chime+.05, slide*np.sin(np.pi*tt/1.2), .5)
    # Section rise: a clean low traction hum whose pitch climbs with the cab, R1 to R2.
    rise = film_time(385, '07-section'); stop = film_time(428, '07-section')
    d = stop-rise+.6; tt = np.arange(int(d*SR))/SR
    f = 46+20*np.clip(tt/(stop-rise), 0, 1)**1.3
    phase = 2*np.pi*np.cumsum(f)/SR
    hum = np.sin(phase)*.028+np.sin(2*phase)*.008+shape(noise(d), 40, 260)*.012
    hum *= np.minimum(tt/.4, 1)*np.clip((d-tt)/.5, 0, 1)
    place(fx, rise, hum, .5)
    place(fx, film_time(426, '07-section'), bell(midi(88), vel=.38), .55)
    # A soft swell into the section cut; no impact hit.
    rlen = 1.6; tt = np.arange(int(rlen*SR))/SR
    place(fx, section-rlen, shape(noise(rlen), 300, 3000)*(tt/rlen)**2.5*np.clip((rlen-tt)/.15, 0, 1)*.05, .5)
    fx = reverb(fx, 2.2, .25)

    mix = music+fx+bed
    t = np.arange(len(mix))/SR
    mix *= np.clip((total-t)/TAIL, 0, 1)[:, None]
    # Leave headroom; the finish step masters loudness with ffmpeg loudnorm.
    mix *= .7/np.max(np.abs(mix))
    mix = np.tanh(mix/.8)*.8
    pcm = (mix*32767).astype('<i2')
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), 'wb') as out:
        out.setnchannels(2); out.setsampwidth(2); out.setframerate(SR); out.writeframes(pcm.tobytes())
    return {'duration_s': round(len(mix)/SR, 3), 'sample_rate': SR, 'cuts_s': [(sid, round(s, 3)) for sid, s, _ in cuts],
            'events_s': {'entry_door': round(door, 3), 'landing_chime': round(chime, 3), 'cab_rise': [round(rise, 3), round(stop, 3)], 'section': round(section, 3),
                          'footsteps_carpet_from': round(corridor, 3), 'release': round(release, 3)}}


if __name__ == '__main__':
    root = HERE.parents[3]
    print(json.dumps(synthesize(root/'build/highland-cinema/Highland-cinema-score.wav'), indent=2))
