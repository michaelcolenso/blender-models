"""Composite the HUD over the rendered sequence frames and encode the MP4.

HUD (Pillow, per frame): phase number and title with a cross-fade at each phase change, a
one-line source note per phase, an 8-segment progress bar along the bottom, and the
standing disclaimer. Frames may be a subset (frame step); timing comes from frame numbers.

Usage:
  python projects/meydenbauer-b/anim_finish.py --tag proxy-60 --fps 60
  python projects/meydenbauer-b/anim_finish.py --tag final-30 --fps 30 --crf 16
  python projects/meydenbauer-b/anim_finish.py --tag final-30 --fps 30 --from-video final-30-clean.mp4
Writes build/meydenbauer-b/anim/<tag>.mp4, <tag>-poster.png and, from rendered frames, <tag>-clean.mp4
(no HUD, CRF 10). Keep the clean master: a HUD or note change is then a CPU re-composite, not a re-render.
"""
import argparse, subprocess, sys
from fractions import Fraction
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
from animate import PHASES, PHASE_S  # noqa: E402

NOTES = [  # each line cites where it comes from
    "Locate and mark existing cast iron; verify depths and stacks before demolition (P1.01 contractor's note)",
    "Protect finishes, set dust containment, remove fixtures (P1.01 keynote 10)",
    "Saw-cut slab and excavate to existing pipe; trench 2'-0\" typical (detail 10/P5.1)",
    "Remove cast iron; new Sch 40 ABS at 1/4\" per ft, tie in at 2-way cleanouts (P1.02)",
    "Leak test per City of Bellevue standards; do not air test (SOR WP #2)",
    "Backfill, vapor barrier, 5\" minimum pour-back (detail 10/P5.1)",
    "Patch finishes to match existing (SOR WP #1; Allowances 1-6)",
    "Reset fixtures, restore service, unit owner sign-off (SOR general notes)",
]
DISCLAIMER = ("Illustrative sequence for internal planning, not a contract document. Routes from bid set P1.01/P1.02; "
              "depths, protection layout and fixtures assumed.")
INK = (236, 240, 246); DIM = (150, 160, 175); ACCENT = (64, 214, 255); BG = (11, 16, 23)


def fonts(h):
    k = h / 1080
    load = lambda name, size: ImageFont.truetype(name, max(8, int(size * k)))
    return dict(num=load("DejaVuSans-Bold.ttf", 54), title=load("DejaVuSans-Bold.ttf", 38),
                note=load("DejaVuSans.ttf", 21), small=load("DejaVuSans.ttf", 15),
                seg=load("DejaVuSans-Bold.ttf", 13), brand=load("DejaVuSans-Bold.ttf", 17)), k


def hud(im, t, total_s):
    w, h = im.size
    F, k = fonts(h)
    ov = Image.new("RGBA", im.size, (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    i = min(int(t // PHASE_S), len(PHASES) - 1)
    local = t - i * PHASE_S
    fade = min(1.0, local / 0.4) if i > 0 else min(1.0, t / 0.4 + 0.2)
    out = max(0.0, min(1.0, (PHASE_S - local) / 0.3)) if i < len(PHASES) - 1 else 1.0
    a = int(255 * min(fade, out))
    # top-left phase card
    pad = int(36 * k)
    num, title = PHASES[i].split(" ", 1)
    cw = max(92 * k + d.textlength(title, font=F["title"]), 2 * k + d.textlength(NOTES[i], font=F["note"])) + 24 * k
    d.rounded_rectangle([pad - 16 * k, pad - 12 * k, pad + cw, pad + 128 * k], radius=12 * k, fill=(*BG, int(150 * a / 255)))
    d.text((pad, pad), num, font=F["num"], fill=(*ACCENT, a))
    d.text((pad + 92 * k, pad + 10 * k), title, font=F["title"], fill=(*INK, a))
    d.text((pad + 2 * k, pad + 76 * k), NOTES[i], font=F["note"], fill=(*DIM, a))
    # brand, top right
    brand = "101 MEYDENBAUER  ·  BUILDING B  ·  UNDER-SLAB WASTE RE-PIPE"
    if w - pad - d.textlength(brand, font=F["brand"]) > pad + cw + 24 * k:      # only where it clears the card
        d.text((w - pad - d.textlength(brand, font=F["brand"]), pad), brand, font=F["brand"], fill=(*INK, 200))
    # progress bar
    by = h - int(78 * k); bh = int(6 * k); gap = int(6 * k)
    x0, x1 = pad, w - pad
    segw = (x1 - x0 - gap * (len(PHASES) - 1)) / len(PHASES)
    d.rectangle([0, by - 34 * k, w, h], fill=(*BG, 175))
    for j, name in enumerate(PHASES):
        sx = x0 + j * (segw + gap)
        d.rectangle([sx, by, sx + segw, by + bh], fill=(60, 70, 85, 255))
        p = 1.0 if j < i else (local / PHASE_S if j == i else 0.0)
        if p > 0:
            d.rectangle([sx, by, sx + segw * p, by + bh], fill=(*ACCENT, 255))
        col = INK if j == i else DIM
        label = name if d.textlength(name, font=F["seg"]) < segw - 4 * k else name.split(" ")[0]
        d.text((sx, by - 24 * k), label, font=F["seg"], fill=(*col, 255 if j == i else 170))
    clock = f"{t:4.1f}s / {total_s:.0f}s"
    disc = DISCLAIMER
    while d.textlength(disc, font=F["small"]) > x1 - x0 - d.textlength(clock, font=F["small"]) - 20 * k:
        disc = disc.rsplit(" ", 1)[0]
    d.text((x0, by + 16 * k), disc if disc == DISCLAIMER else disc.rstrip(";,") + " ...", font=F["small"], fill=(*DIM, 220))
    d.text((x1 - d.textlength(clock, font=F["small"]), by + 16 * k), clock, font=F["small"], fill=(*DIM, 220))
    return Image.alpha_composite(im.convert("RGBA"), ov).convert("RGB")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", required=True)
    ap.add_argument("--fps", type=int, default=60, help="timeline fps the frames were rendered on")
    ap.add_argument("--crf", type=int, default=18)
    ap.add_argument("--from-video", default="", help="clean master MP4 to re-apply the HUD to (no re-render)")
    a = ap.parse_args()
    anim = ROOT / "build/meydenbauer-b/anim"
    if a.from_video:
        # Re-apply the HUD to a clean master: no GPU, minutes on CPU.
        src = anim / "frames" / f"{a.tag}-from-clean"; src.mkdir(parents=True, exist_ok=True)
        for old in src.glob("*.png"):
            old.unlink()
        rate_in = float(Fraction(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                                 "stream=r_frame_rate", "-of", "csv=p=0", a.from_video],
                                                capture_output=True, text=True, check=True).stdout.strip()))
        step = round(a.fps / rate_in)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", a.from_video, "-start_number", "0",
                        str(src / "%05d.png")], check=True)
        for p in sorted(src.glob("*.png")):
            p.rename(src / f"{1 + int(p.stem) * step:04d}.png")
    else:
        src = anim / "frames" / a.tag
    frames = sorted(p for p in src.glob("[0-9]*.png") if not p.name.endswith(".tmp.png"))
    if not frames:
        sys.exit(f"no frames in {src}")
    nums = [int(p.stem) for p in frames]
    step = nums[1] - nums[0] if len(nums) > 1 else 1
    missing = sorted(set(range(nums[0], nums[-1] + 1, step)) - set(nums))
    if missing:
        sys.exit(f"{len(missing)} frames missing, first {missing[:5]}")
    rate = a.fps / step

    def encode(pattern, out, crf):
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", f"{rate:g}", "-i", pattern,
                        "-c:v", "libx264", "-preset", "slow", "-crf", str(crf), "-pix_fmt", "yuv420p",
                        "-movflags", "+faststart", str(out)], check=True)
    if not a.from_video:
        # Clean master (no HUD), near-lossless: keep it, and HUD fixes never need the GPU again.
        lst = anim / f"{a.tag}-clean.txt"
        lst.write_text("".join(f"file '{p}'\nduration {1 / rate:.6f}\n" for p in frames))
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst),
                        "-r", f"{rate:g}", "-c:v", "libx264", "-preset", "slow", "-crf", "10", "-pix_fmt", "yuv420p",
                        "-movflags", "+faststart", str(anim / f"{a.tag}-clean.mp4")], check=True)
        lst.unlink()
    total_s = len(PHASES) * PHASE_S
    tmp = src.parent / f"{a.tag}-hud"; tmp.mkdir(exist_ok=True)
    for j, p in enumerate(frames):
        t = (int(p.stem) - 1) / a.fps
        hud(Image.open(p), t, total_s).save(tmp / f"{j:05d}.png")
    out = anim / f"{a.tag}.mp4"
    encode(str(tmp / "%05d.png"), out, a.crf)
    poster = len(frames) * 21 // 32                   # inside the water test
    Image.open(tmp / f"{poster:05d}.png").save(out.with_name(f"{a.tag}-poster.png"))
    probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=width,height,r_frame_rate,nb_frames",
                            "-of", "default=nw=1", str(out)], capture_output=True, text=True).stdout.split()
    print("WROTE", out, " ".join(probe))


if __name__ == "__main__":
    main()
