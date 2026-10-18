"""Synthesize a quiet architectural score and mux it with the browser render."""
from pathlib import Path
import subprocess
import wave

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
BUILD = ROOT / "build/highland-drone"
SAMPLE_RATE = 44_100
DURATION = 26.0


def envelope(time):
    return np.minimum(np.minimum(time / 1.25, (DURATION - time) / 1.4), 1).clip(0, 1)


def synthesize():
    """Fmaj9 pad, filtered street air, glazing sweep, elevator chimes and riser."""
    time = np.arange(round(DURATION * SAMPLE_RATE), dtype=np.float64) / SAMPLE_RATE
    left = np.zeros_like(time)
    right = np.zeros_like(time)
    for index, frequency in enumerate((87.31, 130.81, 174.61, 220, 261.63, 329.63, 392)):
        phase = 2 * np.pi * frequency * time + .035 * np.sin(2 * np.pi * (.12 + .02 * index) * time)
        tone = np.sin(phase) * (.028 / (1 + index * .25))
        pan = .2 + .6 * index / 6
        left += tone * (1 - pan)
        right += tone * pan

    rng = np.random.default_rng(200)
    noise = rng.standard_normal(len(time))
    spectrum = np.fft.rfft(noise)
    frequencies = np.fft.rfftfreq(len(time), 1 / SAMPLE_RATE)
    spectrum *= 1 / np.sqrt(1 + (frequencies / 125) ** 4)
    breeze = np.fft.irfft(spectrum, len(time))
    breeze /= max(np.max(np.abs(breeze)), 1)
    outside = (1 - np.clip((time - 4.5) / 1.1, 0, 1)) * .032
    left += breeze * outside
    right += breeze * outside * .86

    # A brighter overtone is acoustically swept away at the lobby glazing.
    sweep = .012 * np.sin(2 * np.pi * 670 * time)
    sweep *= 1 - np.clip((time - 4.7) / 1.3, 0, 1)
    left += sweep
    right += sweep * .78

    for at, frequency, pan in ((14.2, 523.25, .38), (14.45, 659.25, .62), (19, 783.99, .5)):
        dt = time - at
        active = (dt >= 0) & (dt < 2.2)
        d = dt[active]
        tone = (.065 * np.sin(2 * np.pi * frequency * d) +
                .018 * np.sin(4 * np.pi * frequency * d)) * np.exp(-2.8 * d)
        left[active] += tone * (1 - pan)
        right[active] += tone * pan

    active = (time >= 14.8) & (time <= 18.8)
    dt = time[active] - 14.8
    phase = 2 * np.pi * (110 * dt + (55 / 12) * dt ** 3 / 4)
    riser = .028 * np.sin(phase) * np.sin(np.pi * dt / 4)
    left[active] += riser
    right[active] += riser

    stereo = np.stack((left, right), axis=1) * envelope(time)[:, None] * 3.5
    peak = np.max(np.abs(stereo))
    if peak > .9:
        stereo *= .9 / peak
    wav_path = BUILD / "Highland-soundtrack.wav"
    with wave.open(str(wav_path), "wb") as output:
        output.setnchannels(2)
        output.setsampwidth(2)
        output.setframerate(SAMPLE_RATE)
        output.writeframes((stereo * 32767).astype("<i2").tobytes())
    return wav_path


def main():
    silent = BUILD / "Highland-corridor-drone-silent.mp4"
    video = BUILD / "Highland-corridor-drone.mp4"
    assert silent.exists(), f"Render first: {silent}"
    soundtrack = synthesize()
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error", "-i", str(silent), "-i", str(soundtrack),
        "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k",
        "-af", "alimiter=limit=0.95", "-movflags", "+faststart", "-shortest", str(video),
    ], check=True)
    print(f"Stereo soundtrack and H.264 video: {video}")


if __name__ == "__main__":
    main()
