"""Shared helpers for sequence animations: captioned frames -> MP4."""
import subprocess
from pathlib import Path


def fit_font(draw, text, path, size, max_w, min_size=12):
    from PIL import ImageFont
    while size >= min_size:
        try:
            f = ImageFont.truetype(path, size)
        except OSError:
            return ImageFont.load_default()
        if draw.textlength(text, font=f) <= max_w:
            return f
        size -= 1
    return ImageFont.truetype(path, min_size)


def current_step(timeline, fr):
    """Index of the timeline entry on screen at frame fr (the latest one that has started)."""
    idx = 0
    for i, (a0, _a1, _t) in enumerate(timeline):
        if fr >= a0:
            idx = i
    return idx


def caption(png, fr, timeline, title, footer="model — see report for provenance"):
    from PIL import Image, ImageDraw
    im = Image.open(png).convert("RGB"); d = ImageDraw.Draw(im)
    rx, ry = im.size
    i = current_step(timeline, fr)
    cap = timeline[i][2]
    band = ry // 6
    d.rectangle([0, ry - band, rx, ry], fill=(255, 255, 255))
    fb = fit_font(d, cap, "DejaVuSans-Bold.ttf", max(18, ry // 22), rx - 32)
    d.text((16, ry - band + 8), cap, fill=(20, 20, 20), font=fb)
    sub = f"{title}   ·   step {i}/{len(timeline) - 1}   ·   {footer}"
    fs = fit_font(d, sub, "DejaVuSans.ttf", max(14, ry // 34), rx - 32, 10)
    d.text((16, ry - ry // 14), sub, fill=(110, 110, 110), font=fs)
    im.save(png)


def encode(fdir, fps, mp4):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(fps), "-i", str(Path(fdir) / "f%05d.png"),
                    "-vf", "fps=24,format=yuv420p", "-c:v", "libx264", "-crf", "22", "-movflags", "+faststart",
                    str(mp4)], check=True)
