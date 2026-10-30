"""Compose the Meydenbauer B presentation film from film.json.

    uv run python projects/meydenbauer-b/products/agency-film/film.py --check    # CI: EDL, claims, captions, plan length
    uv run python projects/meydenbauer-b/products/agency-film/film.py --audio    # scratch VO (Piper) + original score
    uv run python projects/meydenbauer-b/products/agency-film/film.py --video    # picture + mux -> build/.../agency-film/

Inputs: the 2026-10-25 RunPod film (Git LFS), the hero stills from hero_stills.py, and the plan
geometry already in the underslab product (spec + shell JSON). Nothing is re-measured here.
"""
import argparse
import json
import subprocess
import sys
import textwrap
import wave
from pathlib import Path

import numpy as np

from bmodels.paths import ROOT

HERE = Path(__file__).resolve().parent
FILM = json.loads((HERE / "film.json").read_text())
OUT = ROOT / "build" / "meydenbauer-b" / "agency-film"
SRT = HERE / "Meydenbauer-B-film.srt"
F = FILM["format"]
W, H, PH, FPS = F["width"], F["height"], F["picture_height"], F["fps"]
BAR = (H - PH) // 2
SR = 48000
VO_LEAD, VO_GAP = 0.35, 0.25          # VO starts this long after its cut; gap kept before the next line
TAKEOFF_LF = 312.74                   # underslab takeoff, modelled ABS length (deliverables/underslab/README.md)


def hexrgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


PAL = {k: hexrgb(v) for k, v in FILM["palette"].items()}


def starts():
    t, out = 0.0, []
    for s in FILM["shots"]:
        out.append(t); t += s["dur"]
    return out, t


# ---------------------------------------------------------------- check (CI: stdlib + json only)

def stamp(t):
    ms = round(t * 1000)
    return f"{ms // 3600000:02}:{ms // 60000 % 60:02}:{ms // 1000 % 60:02},{ms % 1000:03}"


def parse_srt(text):
    cues = []
    for block in text.strip().split("\n\n"):
        lines = block.splitlines()
        a, b = lines[1].split(" --> ")
        sec = lambda s: int(s[:2]) * 3600 + int(s[3:5]) * 60 + int(s[6:8]) + int(s[9:]) / 1000
        cues.append((sec(a), sec(b), " ".join(lines[2:])))
    return cues


def check():
    errs = []
    st, total = starts()
    shots = FILM["shots"]
    hero = {s["id"] for s in json.loads((HERE / "hero_shots.json").read_text())["shots"]}
    for s, t in zip(shots, st):
        if s.get("vo") and not s.get("claims"):
            errs.append(f"{s['id']}: VO without claims")
        if s["kind"] == "still" and s["still"] not in hero:
            errs.append(f"{s['id']}: still {s['still']} not in hero_shots.json")
        if s["kind"] == "gpu":
            g = FILM["sources"]["gpu"]
            span = s["from"] + s["dur"] * s["speed"]
            if not (1 <= s["phase"] <= 8 and span <= g["phase_seconds"] + 1e-6):
                errs.append(f"{s['id']}: reads past phase {s['phase']} ({span:.2f} s of {g['phase_seconds']})")
    if not 60 <= total <= 90:
        errs.append(f"running time {total:.1f} s outside 60-90 s")
    spec = json.loads((ROOT / FILM["sources"]["plan"]).read_text())
    lf = sum(e["length_ft"] for u in spec["units"] for e in u["edges"])
    if abs(lf - TAKEOFF_LF) > 0.05:
        errs.append(f"plan routes {lf:.2f} LF != takeoff {TAKEOFF_LF} LF")
    if "not a contract document" not in FILM["disclaimer"]:
        errs.append("disclaimer must say 'not a contract document'")
    # Captions: one cue per VO line, in order, same words, inside its own slot, no overlaps.
    vo = [(s, t) for s, t in zip(shots, st) if s.get("vo")]
    if not SRT.exists():
        errs.append(f"{SRT.name} missing: run --audio")
    else:
        cues = parse_srt(SRT.read_text())
        if [c[2] for c in cues] != [s["vo"] for s, _ in vo]:
            errs.append(f"{SRT.name} text differs from film.json VO: re-run --audio")
        for i, ((a, b, _), (s, t)) in enumerate(zip(cues, vo)):
            nxt = vo[i + 1][1] if i + 1 < len(vo) else total
            if not (t <= a < b <= nxt + VO_LEAD - VO_GAP + 1e-3):
                errs.append(f"{s['id']}: caption {a:.2f}-{b:.2f} outside its slot {t:.2f}-{nxt:.2f}")
    for e in errs:
        print("FAIL", e)
    print(f"{'FAIL' if errs else 'PASS'} — {len(shots)} shots, {total:.1f} s, {len(vo)} VO lines, plan {lf:.2f} LF")
    return not errs


# ---------------------------------------------------------------- audio

def read_wav(path):
    with wave.open(str(path)) as w:
        x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
        return w.getframerate(), x


def write_wav(path, x):
    x = np.clip(x, -1, 1)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1 if x.ndim == 1 else 2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())


def narration(total):
    """Scratch VO with Piper (LJ Speech, public-domain dataset). Replace with a booked voice for release."""
    from piper import PiperVoice, SynthesisConfig
    from scipy.signal import resample_poly
    model = OUT / "voice" / "en_US-ljspeech-high.onnx"
    if not model.exists():
        sys.exit(f"missing {model}: download en_US-ljspeech-high.onnx(+.json) from huggingface.co/rhasspy/piper-voices")
    voice = PiperVoice.load(str(model))
    st, _ = starts()
    vo = [(s, t) for s, t in zip(FILM["shots"], st) if s.get("vo")]
    speech = np.zeros(int(total * SR), np.float32); act = np.zeros_like(speech); cues = []
    for i, (s, t) in enumerate(vo):
        raw = OUT / "voice" / f"{s['id']}.wav"
        with wave.open(str(raw), "wb") as w:
            voice.synthesize_wav(s["vo"], w, SynthesisConfig(length_scale=1.04, noise_scale=0.5, noise_w_scale=0.6))
        rate, x = read_wav(raw)
        hit = np.flatnonzero(np.abs(x) > 0.01)
        x = x[max(0, hit[0] - int(0.06 * rate)):hit[-1] + int(0.15 * rate)]
        a = t + VO_LEAD
        nxt = vo[i + 1][1] if i + 1 < len(vo) else total - 1.0
        room = nxt + VO_LEAD - VO_GAP - a
        tempo = len(x) / rate / room
        if tempo > 1.10:
            sys.exit(f"{s['id']}: VO {len(x) / rate:.2f} s does not fit {room:.2f} s; shorten the line or the shot")
        x = resample_poly(x, SR, rate).astype(np.float32)
        if tempo > 1.0:  # small time-stretch by overlap-add keeps pitch
            x = stretch(x, tempo)
        x *= 0.8 / max(float(np.abs(x).max()), 1e-3)
        f = min(480, len(x) // 4); x[:f] *= np.linspace(0, 1, f); x[-f:] *= np.linspace(1, 0, f)
        o = int(a * SR); speech[o:o + len(x)] += x; act[o:o + len(x)] = 1
        cues.append((a, a + len(x) / SR, s["vo"]))
        print(f"VO {s['id']} {len(x) / SR:.2f}s in {room:.2f}s", flush=True)
    SRT.write_text("\n\n".join(f"{i + 1}\n{stamp(a)} --> {stamp(b)}\n" + "\n".join(textwrap.wrap(txt, 42))
                               for i, (a, b, txt) in enumerate(cues)) + "\n")
    return speech, act


def stretch(x, k, n=2048):
    hop_out = n // 4; hop_in = int(hop_out * k); win = np.hanning(n).astype(np.float32)
    frames = (len(x) - n) // hop_in
    y = np.zeros(frames * hop_out + n, np.float32); norm = np.zeros_like(y)
    for i in range(frames):
        y[i * hop_out:i * hop_out + n] += x[i * hop_in:i * hop_in + n] * win
        norm[i * hop_out:i * hop_out + n] += win
    return y / np.maximum(norm, 1e-3)


def score(total):
    """Original procedural score: D-major pad, arpeggiated keys, soft pulse, cut swells, reverb."""
    from scipy.signal import fftconvolve
    rng = np.random.default_rng(101)
    n = int(total * SR); t_all = np.arange(n) / SR
    L = np.zeros((n, 2), np.float32)
    bpm = 84; beat = 60 / bpm; bar = 4 * beat
    midi = lambda m: 440 * 2 ** ((m - 69) / 12)
    prog = [[50, 57, 62, 66, 69], [47, 54, 59, 62, 66], [43, 50, 55, 59, 62, 66], [45, 52, 57, 61, 64]]  # D Bm G(add) A

    def add(sig, t0, pan=0.0, gain=1.0):
        o = int(t0 * SR)
        if o >= n:
            return
        sig = sig[:n - o] * gain
        L[o:o + len(sig), 0] += sig * (1 - pan) * 0.5 ** 0.5 * 1.2
        L[o:o + len(sig), 1] += sig * (1 + pan) * 0.5 ** 0.5 * 1.2

    # pad: two bars per chord, soft detuned saw (8 harmonics) through a moving one-pole low-pass
    k = 0; t0 = 0.0
    while t0 < total:
        d = 2 * bar + 1.5; tt = np.arange(int(d * SR)) / SR
        env = np.minimum(tt / 1.6, 1) * np.minimum((d - tt) / 1.8, 1)
        for j, m in enumerate(prog[k % 4]):
            f = midi(m); sig = np.zeros_like(tt)
            for det in (-0.12, 0.12):
                for h in range(1, 9):
                    sig += np.sin(2 * np.pi * f * h * (1 + det / 100) * tt + j + h) / h ** 1.6
            add((sig * env * 0.0045).astype(np.float32), t0, pan=(j - 2) / 5)
        t0 += 2 * bar; k += 1
    # arpeggio keys from the routes reveal to the wide shot; rests under the end card
    st, _ = starts()
    a0, a1 = st[2], st[-1]
    k = 0; t0 = a0
    pattern = [0, 2, 3, 4, 3, 2, 1, 2]
    while t0 < a1:
        ch = prog[int((t0 // (2 * bar)) % 4)]
        for i, p in enumerate(pattern):
            m = ch[min(p, len(ch) - 1)] + 12
            tt = np.arange(int(1.6 * SR)) / SR; f = midi(m)
            env = (1 - np.exp(-tt * 300)) * np.exp(-tt * 3.2)
            sig = (np.sin(2 * np.pi * f * tt) + 0.25 * np.sin(4 * np.pi * f * tt) + 0.06 * np.sin(6 * np.pi * f * tt)) * env
            add(sig.astype(np.float32) * 0.010, t0 + i * beat / 2, pan=0.35 * np.sin(i))
        t0 += 4 * beat; k += 1
    # soft pulse (sub thump) from the first site shot to the wide shot
    p0, p1 = st[3], st[-2]
    for tb in np.arange(p0, p1, beat):
        tt = np.arange(int(0.35 * SR)) / SR
        f = 55 * (1 + 1.5 * np.exp(-tt * 30))
        sig = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 9)
        add(sig.astype(np.float32) * 0.05, tb)
    # cut swells: filtered noise rising into selected cuts
    for i, s in enumerate(FILM["shots"]):
        if s["kind"] in ("gpu", "end") or s["id"] == "02-plan":
            d = 0.9; tt = np.arange(int(d * SR)) / SR
            nz = rng.standard_normal(len(tt)).astype(np.float32)
            nz = np.convolve(nz, np.ones(24) / 24, mode="same")
            add(nz * (tt / d) ** 3 * 0.05, st[i] - d)
    # end: sustained D chord to the end
    tt = np.arange(int((total - st[-1]) * SR)) / SR
    for j, m in enumerate([38, 50, 57, 62, 66, 69, 74]):
        env = np.minimum(tt / 0.3, 1) * np.exp(-tt * 0.35)
        sig = sum(np.sin(2 * np.pi * midi(m) * h * tt + j) / h ** 2 for h in (1, 2, 3))
        add((sig * env * 0.010).astype(np.float32), st[-1], pan=(j - 3) / 6)
    # room: exponential-noise impulse response, 2.2 s
    ir_t = np.arange(int(2.2 * SR)) / SR
    for c in range(2):
        ir = rng.standard_normal(len(ir_t)) * np.exp(-ir_t * 3.0); ir[0] = 0; ir /= np.abs(ir).sum() / 6
        wet = fftconvolve(L[:, c], ir.astype(np.float32))[:n]
        L[:, c] = 0.75 * L[:, c] + 0.35 * wet
    fade = np.minimum(t_all / 1.5, 1) * np.minimum((total - t_all) / 2.5, 1)
    return L * fade[:, None]


def audio():
    _, total = starts()
    (OUT / "voice").mkdir(parents=True, exist_ok=True)
    speech, act = narration(total)
    music = score(total)
    duck = np.convolve(act[::480], np.ones(40) / 40, mode="same")
    duck = np.interp(np.arange(len(act)), np.arange(len(duck)) * 480, duck).astype(np.float32)
    music *= (1 - 0.7 * duck)[:, None]
    music *= 0.45 / max(float(np.abs(music).max()), 1e-3)
    write_wav(OUT / "score.wav", music)
    write_wav(OUT / "narration.wav", speech)
    mix = music + speech[:, None] * 0.92
    write_wav(OUT / "mix.wav", mix / max(1.0, float(np.abs(mix).max()) / 0.97))
    print(f"AUDIO {total:.1f}s -> {OUT / 'mix.wav'}; captions -> {SRT.relative_to(ROOT)}")


# ---------------------------------------------------------------- picture

def fonts():
    from PIL import ImageFont
    pick = lambda names: next((p for p in names if Path(p).exists()), None)
    disp = pick(["/usr/share/fonts/opentype/inter/InterDisplay-SemiBold.otf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"])
    text = pick(["/usr/share/fonts/opentype/inter/Inter-Regular.otf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"])
    light = pick(["/usr/share/fonts/opentype/inter/InterDisplay-Light.otf", text])
    return lambda kind, size: ImageFont.truetype({"disp": disp, "text": text, "light": light}[kind], size)


FONT = None


def ease(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


def tracked(draw, xy, txt, font, fill, track=0.0, anchor_center=False):
    """Draw letter-spaced text; returns its width."""
    widths = [draw.textlength(c, font=font) for c in txt]
    wsum = sum(widths) + track * font.size * (len(txt) - 1)
    x, y = xy
    if anchor_center:
        x -= wsum / 2
    for c, w in zip(txt, widths):
        draw.text((x, y), c, font=font, fill=fill); x += w + track * font.size
    return wsum


class Plan:
    """2-D plan graphic from the underslab product's shell and spec JSON (feet, origin grid A/1)."""

    def __init__(self):
        import cv2
        self.cv2 = cv2
        sh = json.loads((ROOT / FILM["sources"]["shell"]).read_text())
        sp = json.loads((ROOT / FILM["sources"]["plan"]).read_text())
        self.env = np.array(sh["envelope_ft"], float)
        self.walls = [np.array(w["ring_ft"], float) for w in sh["walls"]]
        self.units = []
        for u in sp["units"]:
            nodes = {k: (np.array(v["xy_ft"], float), v["flow_ft"]) for k, v in u["nodes"].items()}
            edges = []
            for e in u["edges"]:
                (pa, fa), (pb, fb) = nodes[e["a"]], nodes[e["b"]]
                if fa > fb:
                    pa, fa, pb, fb = pb, fb, pa, fa
                edges.append((pa, pb, fa, fb, e["nominal_in"], e["length_ft"]))
            ends = [nodes[x["node"]][0] for x in u["ends"]]
            pts = np.array([p for p, _ in nodes.values()])
            self.units.append({"name": u["unit"], "edges": edges, "ends": ends, "tie": np.array(u["tie_in"]["xy_ft"]),
                                   "maxflow": max(f for _, f in nodes.values()), "c": pts.mean(0)})
        seg = np.diff(self.env, axis=0); self.env_cum = np.concatenate([[0], np.cumsum(np.hypot(*seg.T))])
        lo, hi = self.env.min(0), self.env.max(0)
        self.mid = (lo + hi) / 2
        self.s0 = min((W - 380) / (hi[0] - lo[0]), (PH - 330) / (hi[1] - lo[1]))

    def xf(self, p, zoom):
        s = self.s0 * zoom
        q = (np.asarray(p) - self.mid) * s + np.array([W / 2, PH / 2 - 10])
        return np.round(q * 16).astype(np.int32)  # cv2 shift=4 sub-pixel

    def frame(self, mode, t, dur):
        cv2 = self.cv2
        img = np.zeros((PH, W, 3), np.float32); img[:] = np.array(PAL["ink"]) / 255
        # faint 10-ft survey grid
        zoom = 1.0 + 0.035 * ease(t / dur)
        for gx in range(-10, 180, 10):
            a, b = self.xf([gx, -10], zoom), self.xf([gx, 70], zoom)
            cv2.line(img, tuple(a), tuple(b), (0.09, 0.11, 0.13), 1, cv2.LINE_AA, 4)
        for gy in range(-10, 75, 10):
            a, b = self.xf([-10, gy], zoom), self.xf([180, gy], zoom)
            cv2.line(img, tuple(a), tuple(b), (0.09, 0.11, 0.13), 1, cv2.LINE_AA, 4)
        paper = np.array(PAL["paper"]) / 255
        if mode == "shell":
            p = ease(t / 2.6); wall_a = ease((t - 1.9) / 1.4)
        else:
            p, wall_a = 1.0, 1.0
        # walls as single-weight outlines
        if wall_a > 0:
            lay = img.copy()
            cv2.polylines(lay, [self.xf(w, zoom) for w in self.walls], True, tuple(paper * 0.75), 1, cv2.LINE_AA, 4)
            k = wall_a * (0.9 if mode == "shell" else 0.5)
            img = img * (1 - k) + lay * k
        # envelope drawn on by perimeter length
        L = p * self.env_cum[-1]; k = np.searchsorted(self.env_cum, L)
        pts = list(self.env[:k])
        if 0 < k < len(self.env):
            f = (L - self.env_cum[k - 1]) / max(self.env_cum[k] - self.env_cum[k - 1], 1e-9)
            pts.append(self.env[k - 1] + f * (self.env[k] - self.env[k - 1]))
        if len(pts) > 1:
            cv2.polylines(img, [self.xf(np.array(pts), zoom)], False, tuple(paper * 0.9), 2, cv2.LINE_AA, 4)
        labels = []
        lf = 0.0
        if mode == "shell":
            la = ease((t - 3.3) / 0.8)
            labels = [(u["name"], np.array([u["c"][0], -9.0]), la) for u in self.units]
        else:
            glow = np.zeros_like(img)
            acc = np.array(PAL["accent"]) / 255
            for i, u in enumerate(self.units):
                prog = ease((t - 0.5 - 1.15 * i) / 2.3)
                thr = prog * u["maxflow"]
                for pa, pb, fa, fb, dia, ln in u["edges"]:
                    if thr <= fa:
                        continue
                    q = 1.0 if thr >= fb else (thr - fa) / max(fb - fa, 1e-9)
                    pe = pa + q * (pb - pa)
                    th = {4: 4, 3: 3}.get(dia, 2)
                    a, b = self.xf(pa, zoom), self.xf(pe, zoom)
                    cv2.line(img, tuple(a), tuple(b), tuple(acc), th, cv2.LINE_AA, 4)
                    cv2.line(glow, tuple(a), tuple(b), tuple(acc), th + 6, cv2.LINE_AA, 4)
                    lf += ln * q
                if prog > 0:
                    c = self.xf(u["tie"], zoom)
                    r = int((10 + 14 * (1 - prog)) * 16)
                    cv2.circle(img, tuple(c), r, tuple(np.array(PAL["warm"]) / 255), 2, cv2.LINE_AA, 4)
                labels.append((u["name"], np.array([u["c"][0], -9.0]), 0.55 + 0.45 * ease(prog * 3)))
            img += cv2.GaussianBlur(glow, (0, 0), 9) * 0.55
        return np.clip(img, 0, 1), labels, lf, zoom


def still_frame(img, move, t, dur):
    import cv2
    h, w = img.shape[:2]
    e = ease(t / dur)
    if move == "push":
        z = 1.0 + 0.09 * e; dx = 0.0
    elif move == "pull":
        z = 1.12 - 0.12 * e; dx = 0.0
    else:
        z = 1.06; dx = (e - 0.5) * 0.04 * w
    s = W / w * z
    M = np.array([[s, 0, W / 2 - s * (w / 2 + dx)], [0, s, PH / 2 - s * h / 2]], np.float32)
    return cv2.warpAffine(img, M, (W, PH), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)


def gpu_frames(shot):
    g = FILM["sources"]["gpu"]
    cw, ch, cx, cy = g["crop"]
    t0 = (shot["phase"] - 1) * g["phase_seconds"] + shot["from"]
    span = shot["dur"] * shot["speed"] + 0.1
    cmd = ["ffmpeg", "-v", "error", "-ss", f"{t0:.3f}", "-i", str(ROOT / g["file"]), "-t", f"{span:.3f}",
           "-vf", f"crop={cw}:{ch}:{cx}:{cy},scale={W}:{PH}:flags=lanczos", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    raw = subprocess.run(cmd, check=True, capture_output=True).stdout
    fr = np.frombuffer(raw, np.uint8).reshape(-1, PH, W, 3)
    n = round(shot["dur"] * FPS)
    idx = np.minimum((np.arange(n) / FPS * shot["speed"] * g["fps"]).astype(int), len(fr) - 1)
    return fr, idx


def grade(pic, i, rng_cache=None):
    """Shared look: gentle toe/shoulder, warm highlights, vignette, fine grain."""
    if rng_cache is None:
        rng_cache = {}
    if "v" not in rng_cache:
        yy, xx = np.mgrid[0:PH, 0:W].astype(np.float32)
        r = np.hypot((xx - W / 2) / (W / 2), (yy - PH / 2) / (PH / 2))
        rng_cache["v"] = (1 - 0.22 * np.clip(r - 0.35, 0, 1) ** 1.6)[..., None].astype(np.float32)
        rng_cache["g"] = np.random.default_rng(7).standard_normal((8, PH // 2, W // 2)).astype(np.float32)
    x = pic.astype(np.float32) / 255
    x = x + 0.06 * x * (1 - x) * (x - 0.5) * -4     # soft S
    x *= np.array([1.02, 1.0, 0.97], np.float32)     # warm
    x *= rng_cache["v"]
    gr = rng_cache["g"][i % 8].repeat(2, 0).repeat(2, 1)[..., None]
    x += gr * 0.012
    return (np.clip(x, 0, 1) * 255).astype(np.uint8)


_SCRIM = {}


def scrim(a):
    """Soft lower-left darkening behind the super, so white type reads over bright floors."""
    from PIL import Image
    if "m" not in _SCRIM:
        yy, xx = np.mgrid[0:PH, 0:W].astype(np.float32)
        r = np.hypot((xx - 60) / 1100, (yy - PH + 40) / 420)
        _SCRIM["m"] = np.clip(1 - r, 0, 1) ** 1.4 * 0.62
    return Image.fromarray((_SCRIM["m"] * a * 255).astype(np.uint8), "L")


def compose(pic, shot, t, lf=None, labels=(), plan=None, zoom=1.0):
    """Letterbox + typography over the graded picture. Returns the full RGB frame."""
    from PIL import Image, ImageDraw
    frame = Image.new("RGB", (W, H), (0, 0, 0))
    if pic is not None:
        frame.paste(Image.fromarray(pic), (0, BAR))
    d = ImageDraw.Draw(frame, "RGBA")
    dur = shot["dur"]
    paper, dim, acc = PAL["paper"], PAL["dim"], PAL["accent"]
    for name, c, a in labels:
        q = plan.xf(c, zoom) / 16
        tracked(d, (q[0], BAR + q[1] - 12), name, FONT("disp", 22), paper + (int(255 * a),), 0.12, True)
    if shot["kind"] == "plan":
        a = ease(t / 1.0) * ease((dur - t) / 0.4)
        x0, y0 = W - 110, BAR + PH - 70
        px = plan.s0 * zoom * 20
        d.line([x0 - px, y0, x0, y0], fill=paper + (int(200 * a),), width=2)
        for k in range(3):
            xx = x0 - px + k * px / 2
            d.line([xx, y0 - 6, xx, y0 + 6], fill=paper + (int(200 * a),), width=2)
        d.text((x0 - px, y0 + 12), "0        10        20 FT", font=FONT("text", 15), fill=dim + (int(255 * a),))
        cap = "PLAN FROM BID SET P2.1 / P1.02  ·  ROUTES DIAGRAMMATIC, FIELD VERIFY"
        f15 = FONT("text", 15)
        cw = sum(d.textlength(c, font=f15) for c in cap) + 0.12 * 15 * (len(cap) - 1)
        tracked(d, (x0 - px - 50 - cw, y0 + 12), cap, f15, dim + (int(255 * a),), 0.12)
    if shot["kind"] in ("title", "end"):
        fade = ease(t / 1.2) * ease((dur - t) / 0.9)
        lines = shot["lines"]
        y = H / 2 - (40 if shot["kind"] == "title" else 70)
        w = tracked(d, (W / 2, y - 30), lines[0], FONT("disp", 54), paper + (int(255 * fade),), 0.32, True)
        rule = ease((t - 0.4) / 1.4) * w * 0.5
        d.rectangle([W / 2 - rule / 2, y + 52, W / 2 + rule / 2, y + 54], fill=acc + (int(255 * fade),))
        for k, ln in enumerate(lines[1:]):
            a = fade * ease((t - 0.7 - 0.3 * k) / 1.0)
            tracked(d, (W / 2, y + 80 + 44 * k), ln, FONT("light", 30), paper + (int(220 * a),), 0.06, True)
        if shot["kind"] == "end":
            tracked(d, (W / 2, H - BAR - 64), FILM["disclaimer"], FONT("text", 20), dim + (int(255 * fade),), 0.02, True)
        return frame
    if shot.get("super"):
        a = ease((t - 0.7) / 0.6) * ease((dur - 0.3 - t) / 0.4)
        rise = 14 * (1 - ease((t - 0.7) / 0.6))
        frame.paste((0, 0, 0), (0, BAR), scrim(a))
        d = ImageDraw.Draw(frame, "RGBA")
        big, small = shot["super"]
        if lf is not None:
            big = f"{int(min(lf, TAKEOFF_LF))} LF"
        x, y = 110, BAR + PH - 210 + rise
        d.rectangle([x - 26, y + 10, x - 22, y + 118], fill=acc + (int(255 * a),))
        d.text((x, y), big, font=FONT("disp", 76), fill=paper + (int(255 * a),))
        d.text((x + 2, y + 92), small.upper(), font=FONT("text", 22), fill=paper + (int(200 * a),))
    # lower bar: identity left, disclaimer right
    ba = 150
    tracked(d, (110, H - BAR + 52), "101 MEYDENBAUER  ·  BUILDING B", FONT("text", 17), dim + (ba,), 0.18)
    txt = FILM["disclaimer"].split(".")[0].upper() + "."
    wt = sum(d.textlength(c, font=FONT("text", 17)) for c in txt) + 0.18 * 17 * (len(txt) - 1)
    tracked(d, (W - 110 - wt, H - BAR + 52), txt, FONT("text", 17), dim + (ba,), 0.18)
    return frame


def video():
    global FONT
    import cv2
    FONT = fonts()
    st, _ = starts()
    plan = Plan()
    stills = {}
    sdir = ROOT / FILM["sources"]["stills"]
    master = OUT / "Meydenbauer-B-film-picture.mp4"
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                            "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "slow", "-crf", "16",
                            "-pix_fmt", "yuv420p", "-tune", "film", str(master)], stdin=subprocess.PIPE)
    sheet = []
    gi = 0
    for s, t0 in zip(FILM["shots"], st):
        n = round(s["dur"] * FPS)
        if s["kind"] == "gpu":
            fr, idx = gpu_frames(s)
        if s["kind"] == "still" and s["still"] not in stills:
            p = sdir / f"{s['still']}.png"
            if not p.exists():
                sys.exit(f"missing {p}: run hero_stills.py")
            stills[s["still"]] = cv2.cvtColor(cv2.imread(str(p)), cv2.COLOR_BGR2RGB).astype(np.float32)
        for i in range(n):
            t = i / FPS
            lf, labels, zoom = None, (), 1.0
            if s["kind"] in ("title", "end"):
                pic = None
            elif s["kind"] == "plan":
                img, labels, lf, zoom = plan.frame(s["reveal"], t, s["dur"])
                pic = grade((img * 255).astype(np.uint8), gi)
                if s["reveal"] == "shell":
                    lf = None
            elif s["kind"] == "still":
                pic = grade(np.clip(still_frame(stills[s["still"]], s["move"], t, s["dur"]), 0, 255).astype(np.uint8), gi)
            else:
                pic = grade(fr[idx[i]], gi)
            # 8-frame dip from black at the head of each picture shot after a card
            if pic is not None and s["kind"] in ("plan",) and i < 8 and s["id"] == "02-plan":
                pic = (pic.astype(np.float32) * (i / 8)).astype(np.uint8)
            im = compose(pic, s, t, lf, labels, plan, zoom)
            enc.stdin.write(im.tobytes()); gi += 1
            if i == int(n * 0.6):
                sheet.append((s["id"], im))
        print(f"SHOT {s['id']} {n} frames", flush=True)
    enc.stdin.close(); enc.wait()
    # contact sheet + poster
    from PIL import Image, ImageDraw
    cols = 4; tw, th = 480, 270
    cs = Image.new("RGB", (cols * tw, -(-len(sheet) // cols) * (th + 28)), (12, 14, 18))
    dd = ImageDraw.Draw(cs)
    for k, (sid, im) in enumerate(sheet):
        x, y = k % cols * tw, k // cols * (th + 28)
        cs.paste(im.resize((tw, th), Image.LANCZOS), (x, y)); dd.text((x + 8, y + th + 6), sid, fill=(180, 186, 194))
    cs.save(OUT / "contact-sheet.jpg", quality=86)
    dict(sheet)["11-after"].save(OUT / "poster.jpg", quality=90)
    mux()


def mux():
    """Master (picture stream copied) and a web encode, both with the mix and the caption track."""
    _, total = starts()
    master = OUT / "Meydenbauer-B-film-picture.mp4"
    for name, vcodec in (("Meydenbauer-B-film-1080p24.mp4", ["-c:v", "copy"]),
                         ("Meydenbauer-B-film-1080p24-web.mp4", ["-c:v", "libx264", "-preset", "slow", "-crf", "23",
                                                                 "-pix_fmt", "yuv420p", "-maxrate", "8M", "-bufsize", "16M"])):
        final = OUT / name
        # -t, not -shortest: the caption stream ends at the last cue, before the end card
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(master), "-i", str(OUT / "mix.wav"), "-i", str(SRT),
                        "-map", "0:v", "-map", "1:a", "-map", "2:0", *vcodec, "-c:a", "aac", "-b:a", "256k",
                        "-af", "loudnorm=I=-16:TP=-1.5:LRA=9,aresample=48000", "-c:s", "mov_text",
                        "-metadata:s:s:0", "language=eng", "-metadata", f"title={FILM['title']}",
                        "-t", f"{total:.3f}", "-movflags", "+faststart", str(final)], check=True)
        print(f"FILM {final} ({total:.1f} s)", flush=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--audio", action="store_true")
    ap.add_argument("--video", action="store_true")
    ap.add_argument("--mux", action="store_true", help="re-mux audio and captions onto the existing picture")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    if a.audio:
        audio()
    if a.video:
        video()
    elif a.mux:
        mux()
    if a.check or not (a.audio or a.video or a.mux):
        sys.exit(0 if check() else 1)


if __name__ == "__main__":
    main()
