"""Original score and sound design for the Highland cinematic film.

Everything is synthesized here with NumPy, so no licensed music or sample
library is involved. Chords change on the picture cuts and effects land on the
native door, chime and elevator events, all derived from cinema.shots.json.
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


# Chord voicings in MIDI: bass, pad, arpeggio.
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
           '05-corridor-108': 'Gmaj7#11', '06-elevator': 'Asus', '07-section': 'D/F#', '08-corridor-208': 'Gmaj9'}
# Eighth-note arpeggio pattern (index into the chord, or None) and velocity.
PATTERN = [(0, .55), (None, 0), (2, .38), (1, .32), (None, 0), (3, .36), (2, .3), (None, 0)]


def synthesize(path):
    cuts, picture = timeline()
    total = picture+END_CARD+TAIL
    music = np.zeros((int(total*SR), 2)); fx = np.zeros_like(music); bed = np.zeros_like(music)
    beat = 60/SPEC['tempo_bpm']
    sections = [(start, HARMONY[sid]) for sid, start, _ in cuts]
    # Last bars of the corridor turn to A, resolving to D on the end card.
    sections.append((picture-1.5, 'A')); sections.append((picture, 'Dmaj9'))
    for j, (start, name) in enumerate(sections):
        end = sections[j+1][0] if j+1 < len(sections) else total-TAIL
        bass, voicing, arp = CHORDS[name]
        hero = name == 'D/F#'
        bed_pad = pad(voicing, end-start+1.8, .045 if hero else .032)
        air = pad([n+24 for n in voicing[2:]], end-start+1.8, .012 if hero else .007)
        for ch, side in ((0, 0), (1, 1)):
            place(music, max(0, start-.6), bed_pad[:, ch]+air[:, ch], side)
        t = np.arange(int((end-start+2.5)*SR))/SR
        sub = np.sin(2*np.pi*midi(bass+12)*t)*.055+np.sin(2*np.pi*midi(bass+24)*t)*.015
        sub *= np.minimum(np.minimum(t/.5, 1), np.clip((end-start+1.2-t)/1.2, 0, 1))
        place(music, start, sub*(1.4 if hero else 1), .5)
        # Felt-piano arpeggio; the opening and end card stay sparse.
        step, k = beat/2, 0
        while start+k*step < end-.1:
            idx, vel = PATTERN[k % len(PATTERN)]
            when = start+k*step
            if idx is not None and not (start == 0 and when < 1.5) and when < picture+1.5:
                note = arp[idx]+(12 if hero and idx > 2 else 0)
                place(music, when+RNG.normal(0, .006), felt_piano(midi(note), vel=vel*(1.15 if hero else 1)), .3+.1*idx, 1)
            k += 1
        # A melody note marks each chord change.
        place(music, start+.02, felt_piano(midi(arp[-1]), 6., .62), .62)
    # Final resolution: low D and a high shimmer on the end card.
    place(music, picture, felt_piano(midi(50), 7., .7), .45); place(music, picture+.37, felt_piano(midi(74), 7., .45), .6)
    place(music, picture+.75, felt_piano(midi(81), 7., .35), .7)
    music = reverb(music, 3.2, .38)
    # Decorrelated reverb tails differ slightly in level; recentre the music bus.
    music *= np.sqrt(np.mean(music**2))/np.sqrt(np.mean(music**2, 0))

    exterior_end = next(start for sid, start, _ in cuts if sid == '03-lobby')
    # Dusk street air: distant traffic rumble and two passing cars.
    t = np.arange(int((exterior_end+1)*SR))/SR
    rumble = shape(noise(exterior_end+1), 40, 400)*np.minimum(t/1.5, 1)*np.clip((exterior_end+.6-t)/.6, 0, 1)*.05
    place(bed, 0, rumble, .45)
    for when, pan in ((1.2, .2), (3.4, .85)):
        tt = np.arange(int(2.6*SR))/SR
        place(bed, when, shape(noise(2.6), 300, 2500)*np.sin(np.pi*tt/2.6)**3*.035, pan)
    # Interior air handling: a quiet room tone with a faint 120 Hz component.
    t = np.arange(int((picture-exterior_end+1)*SR))/SR
    room = (shape(noise(len(t)/SR), 60, 800)*.014+np.sin(2*np.pi*120*t)*.0035)*np.minimum(t/.4, 1)
    place(bed, exterior_end, room, .5)

    # Entry door swing, landing chime, door slide, elevator run and arrival ding.
    door = film_time(97, '02-entry')
    tt = np.arange(int(1.4*SR))/SR
    place(fx, door, shape(noise(1.4), 200, 1800)*np.sin(np.pi*np.minimum(tt/1.4, 1))**2*.05, .5)
    place(fx, door+1.25, shape(noise(.08), 1500, 6000)*np.exp(-np.arange(int(.08*SR))/SR/.01)*.12, .5)
    chime = film_time(289, '06-elevator')
    place(fx, chime-.25, bell(midi(88), vel=.55), .45); place(fx, chime+.12, bell(midi(84), vel=.5), .55)
    tt = np.arange(int(1.2*SR))/SR
    place(fx, chime+.05, shape(noise(1.2), 80, 700)*np.sin(np.pi*tt/1.2)*.06, .5)
    section = next(start for sid, start, _ in cuts if sid == '07-section')
    rise = film_time(385, '07-section'); stop = film_time(428, '07-section')
    tt = np.arange(int((stop-rise+.6)*SR))/SR
    hum = (np.sin(2*np.pi*55*tt)*.03+shape(noise(len(tt)/SR), 40, 300)*.03)*np.minimum(tt/.4, 1)*np.clip((stop-rise+.6-tt)/.5, 0, 1)
    place(fx, rise, hum, .5)
    place(fx, film_time(426, '07-section'), bell(midi(88), vel=.42), .55)
    # Riser into the section cut and a soft low impact on it.
    rlen = 2.2; tt = np.arange(int(rlen*SR))/SR
    swell = np.zeros_like(tt)
    for j in range(8):
        a, b = j/8*rlen, (j+1)/8*rlen
        seg = (tt >= a) & (tt < b)
        swell[seg] = shape(noise(rlen), 300+j*500, 900+j*1100)[seg]
    swell *= (tt/rlen)**2.5*.11
    place(fx, section-rlen, swell, .5)
    tt = np.arange(int(3.5*SR))/SR
    boom = np.sin(2*np.pi*(42+18*np.exp(-tt*8))*tt)*np.exp(-tt*1.4)*.22+shape(noise(3.5), 30, 220)*np.exp(-tt*3)*.08
    place(fx, section, boom, .5)
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
            'events_s': {'entry_door': round(door, 3), 'landing_chime': round(chime, 3), 'cab_rise': [round(rise, 3), round(stop, 3)], 'section_impact': round(section, 3)}}


if __name__ == '__main__':
    root = HERE.parents[3]
    print(json.dumps(synthesize(root/'build/highland-cinema/Highland-cinema-score.wav'), indent=2))
