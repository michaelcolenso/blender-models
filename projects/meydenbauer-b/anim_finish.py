"""Composite the HUD over the rendered sequence frames and encode the MP4.

HUD (Pillow, per frame): phase number and title with a cross-fade at each phase change, a
one-line source note per phase, an 8-segment progress bar along the bottom, and the
standing disclaimer. Frames may be a subset (frame step); timing comes from frame numbers.

--plan sequence (one unit at a time): unit and phase card, a working-day counter, haul and
SOR note 21 chips, and a Gantt of the strawman schedule with a playhead, from schedule.py and
meydenbauer-b.logistics.json. --upscale lets a small proxy carry a legible HUD.

Usage:
  python projects/meydenbauer-b/anim_finish.py --tag proxy-60 --fps 60
  python projects/meydenbauer-b/anim_finish.py --plan sequence --tag seqproxy-30 --fps 30 --upscale 540
  python projects/meydenbauer-b/anim_finish.py --tag final-30 --fps 30 --crf 16
  python projects/meydenbauer-b/anim_finish.py --tag final-30 --fps 30 --from-video final-30-clean.mp4
Writes build/meydenbauer-b/anim/<tag>.mp4, <tag>-poster.png and, from rendered frames, <tag>-clean.mp4
(no HUD, CRF 10). Keep the clean master: a HUD or note change is then a CPU re-composite, not a re-render.
"""
import argparse, json, math, subprocess, sys
from fractions import Fraction
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
from animate import PHASES, PHASE_S  # noqa: E402
import schedule as SCHED  # noqa: E402

SPEC = json.loads((HERE / "meydenbauer-b.spec.json").read_text())

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
AMBER = (255, 160, 60); GREEN = (90, 220, 130)
PHASE_RGB = [(255, 140, 40), (205, 185, 140), (240, 100, 55), (64, 214, 255), (70, 140, 255), (170, 172, 180),
             (196, 146, 96), (90, 210, 120)]
PHASE_SHORT = ["Locate", "Stage", "Demo + dig", "ABS", "Test", "Backfill + pour", "Cure + finish", "Reset"]
SEQ_DISCLAIMER = ("Illustrative sequence for internal planning, not a contract document. Schedule, order, haul routes, "
                  "staging layout and depths assumed; pipe routes from bid set P1.01/P1.02.")


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


def fit_text(d, text, font, width):
    if d.textlength(text, font=font) <= width:
        return text
    while text and d.textlength(text + " ...", font=font) > width:
        text = text.rsplit(" ", 1)[0] if " " in text else text[:-1]
    return text.rstrip(";,·") + " ..."


def hud_seq(im, t, total_s, plan, W, L):
    """Sequence HUD: card (unit, phase, note), day counter, chips, Gantt with playhead."""
    w, h = im.size
    F, k = fonts(h)
    ov = Image.new("RGBA", im.size, (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    pad = int(36 * k)
    day, unit, i = SCHED.day_at(plan, W, t)
    order = [u["unit"] for u in plan["units"]]
    first, last = W[order[0]][0][0], W[order[-1]][-1][1]
    if unit is None:
        t0, t1 = (0.0, first) if t < first else (last, total_s)
        num, title = "", "Site overview"
        sub = "BUILDING B  ·  ONE UNIT AT A TIME"
        note = (f'Order {" > ".join(order)} (assumed); haul through one core entry at a time (00 22 13 1.14.B)' if t < first
                else f'{plan["working_days"]:g} working days, about {plan["calendar_days_approx"]} calendar days, no holidays (strawman)')
    else:
        t0, t1 = W[unit][i]
        num, title = PHASES[i].split(" ", 1)
        sub = f"UNIT {unit}  ·  {order.index(unit) + 1} OF {len(order)}"
        note = NOTES[i]
    ramp = min(0.35, 0.25 * (t1 - t0))
    a = int(255 * max(0.0, min(1.0, (t - t0) / ramp + (0.2 if t0 == 0 else 0), (t1 - t) / ramp if t1 < total_s else 1.0)))
    # top-left card
    tx = pad + (92 * k if num else 0)
    note = fit_text(d, note, F["note"], w * 0.62)
    cw = max(tx - pad + d.textlength(title, font=F["title"]), d.textlength(note, font=F["note"]),
             d.textlength(sub, font=F["brand"])) + 24 * k
    d.rounded_rectangle([pad - 16 * k, pad - 12 * k, pad + cw, pad + 150 * k], radius=12 * k, fill=(*BG, int(150 * a / 255)))
    d.text((pad + 2 * k, pad - 2 * k), sub, font=F["brand"], fill=(*ACCENT, a))
    if num:
        d.text((pad, pad + 20 * k), num, font=F["num"], fill=(*ACCENT, a))
    d.text((tx, pad + 30 * k), title, font=F["title"], fill=(*INK, a))
    d.text((pad + 2 * k, pad + 98 * k), note, font=F["note"], fill=(*DIM, a))
    # top-right day counter
    shown = 0 if unit is None and t < first else min(math.ceil(day - 1e-9), plan["working_days"])
    big = f"DAY {shown:g}"
    small = f'of {plan["working_days"]:g} working days  ·  week {max(1, math.ceil(day / 5 - 1e-9))}'
    x1 = w - pad
    d.text((x1 - d.textlength(big, font=F["num"]), pad - 6 * k), big, font=F["num"], fill=(*INK, 235))
    d.text((x1 - d.textlength(small, font=F["note"]), pad + 58 * k), small, font=F["note"], fill=(*DIM, 230))
    # chips under the counter
    chips = []
    if unit is not None:
        r, q = L["routes"][unit], L["haul"][unit]
        if 1 <= i <= 6:
            stacks = 2 <= i <= 5 and any(e["kind"].startswith("STACK") for su in SPEC["units"] if su["unit"] == unit
                                         for e in su["ends"])
            chips.append((GREEN, "SERVICE  1 toilet + 1 sink by 5 PM (SOR 21)  ·  stacks on bypass (P2.1)" if stacks
                          else "SERVICE  1 toilet + 1 sink in use by 5:00 PM daily (SOR note 21)"))
        if i == 2:
            chips.append((AMBER, f'HAUL OUT  {q["out_cy_loose"]:g} CY loose  ·  {r["out_length_ft"]} ft via {r["entry"]} core  ·  '
                                 f'{q["bin_swaps"]} bin swaps'))
        if i == 5:
            chips.append((ACCENT, f'HAUL IN  {q["in_cy"]:g} CY bedding + backfill  ·  {q["concrete_cy"]:g} CY concrete'))
        if i == 6:
            chips.append((DIM, f'Includes {plan["rates"]["cure_days"]:g}-day cure before floor finishes (assumed)'))
    cy = pad + 92 * k
    for col, text in chips:
        text = fit_text(d, text, F["note"], w * 0.45)
        tw = d.textlength(text, font=F["note"])
        d.rounded_rectangle([x1 - tw - 26 * k, cy, x1, cy + 32 * k], radius=8 * k, fill=(*BG, int(170 * a / 255)))
        d.rectangle([x1 - tw - 26 * k, cy, x1 - tw - 20 * k, cy + 32 * k], fill=(*col, a))
        d.text((x1 - tw - 10 * k, cy + 5 * k), text, font=F["note"], fill=(*INK, a))
        cy += 40 * k
    # Gantt band
    by = h - int(196 * k)
    d.rectangle([0, by, w, h], fill=(*BG, 175))
    gx0, gx1 = pad + 70 * k, w - pad
    X = lambda dd: gx0 + dd / plan["working_days"] * (gx1 - gx0)
    lx = gx0
    for j, name in enumerate(PHASE_SHORT):                       # legend
        lab = f"{j + 1:02d} {name}"
        if lx + 18 * k + d.textlength(lab, font=F["small"]) > gx1:
            break
        d.rectangle([lx, by + 12 * k, lx + 11 * k, by + 23 * k], fill=(*PHASE_RGB[j], 255))
        d.text((lx + 16 * k, by + 9 * k), lab, font=F["small"], fill=(*DIM, 230))
        lx += 28 * k + d.textlength(lab, font=F["small"])
    ry, rh, rg = by + 40 * k, 16 * k, 5 * k
    for dd in range(0, int(plan["working_days"]) + 1, 5):
        d.line([X(dd), ry - 3 * k, X(dd), ry + 4 * (rh + rg)], fill=(*DIM, 50), width=max(1, int(k)))
        if dd % 10 == 0:
            d.text((X(dd) - 4 * k, ry + 4 * (rh + rg) + 2 * k), f"D{dd}", font=F["small"], fill=(*DIM, 200))
    for r_, u in enumerate(plan["units"]):
        y0 = ry + r_ * (rh + rg)
        active = u["unit"] == unit
        d.text((pad, y0 - 1 * k), u["unit"], font=F["seg"], fill=(*(INK if active else DIM), 255 if active else 190))
        for j, (s0, dd) in enumerate(zip(u["phase_start_day"], u["days"])):
            xa, xb = X(s0), X(s0 + dd)
            d.rectangle([xa, y0, xb - max(1, k), y0 + rh], fill=(*PHASE_RGB[j], 70))
            done = min(max(day - s0, 0.0), dd)
            if done > 0:
                d.rectangle([xa, y0, X(s0 + done) - max(1, k), y0 + rh], fill=(*PHASE_RGB[j], 240))
    px = X(day)
    d.line([px, ry - 7 * k, px, ry + 4 * (rh + rg) - 2 * k], fill=(*INK, 255), width=max(1, int(2 * k)))
    d.polygon([(px - 5 * k, ry - 11 * k), (px + 5 * k, ry - 11 * k), (px, ry - 4 * k)], fill=(*INK, 255))
    clock = f"{t:5.1f}s / {total_s:.1f}s"
    dy = h - int(30 * k)
    d.text((pad, dy), fit_text(d, SEQ_DISCLAIMER, F["small"], x1 - pad - d.textlength(clock, font=F["small"]) - 20 * k),
           font=F["small"], fill=(*DIM, 220))
    d.text((x1 - d.textlength(clock, font=F["small"]), dy), clock, font=F["small"], fill=(*DIM, 220))
    return Image.alpha_composite(im.convert("RGBA"), ov).convert("RGB")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", required=True)
    ap.add_argument("--fps", type=int, default=60, help="timeline fps the frames were rendered on")
    ap.add_argument("--crf", type=int, default=18)
    ap.add_argument("--from-video", default="", help="clean master MP4 to re-apply the HUD to (no re-render)")
    ap.add_argument("--plan", default="overview", choices=["overview", "sequence"])
    ap.add_argument("--upscale", type=int, default=0, help="scale frames to this height before the HUD (proxies)")
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
    if a.plan == "sequence":
        plan = SCHED.build(); W, total_s = SCHED.windows(plan)
        L = json.loads((HERE / "meydenbauer-b.logistics.json").read_text())
        draw = lambda im, t: hud_seq(im, t, total_s, plan, W, L)
        w4 = W[plan["order"][-1]][2]                     # B-104 demolition: the longest haul, on the haul shot
        t_poster = w4[0] + 0.8 * (w4[1] - w4[0])
    else:
        total_s = len(PHASES) * PHASE_S
        draw = lambda im, t: hud(im, t, total_s)
        t_poster = total_s * 21 / 32                     # inside the water test
    tmp = src.parent / f"{a.tag}-hud"; tmp.mkdir(exist_ok=True)
    for old in tmp.glob("*.png"):
        old.unlink()
    for j, p in enumerate(frames):
        im = Image.open(p)
        if a.upscale:
            im = im.resize((round(im.width * a.upscale / im.height / 2) * 2, a.upscale), Image.LANCZOS)
        draw(im, (int(p.stem) - 1) / a.fps).save(tmp / f"{j:05d}.png")
    out = anim / f"{a.tag}.mp4"
    encode(str(tmp / "%05d.png"), out, a.crf)
    poster = min(range(len(frames)), key=lambda j: abs((int(frames[j].stem) - 1) / a.fps - t_poster))
    Image.open(tmp / f"{poster:05d}.png").save(out.with_name(f"{a.tag}-poster.png"))
    probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=width,height,r_frame_rate,nb_frames",
                            "-of", "default=nw=1", str(out)], capture_output=True, text=True).stdout.split()
    print("WROTE", out, " ".join(probe))


if __name__ == "__main__":
    main()
