"""Full-frame studio graphics, separate from the reusable Blender image plates."""
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from video_common import repo_path


def paper_over(image, paper):
    """Composite AgX PNG over display paper in display-linear sRGB."""
    pixels = np.asarray(image.convert("RGBA"), dtype=np.float32) / 255
    color = np.array([int(paper[i:i+2], 16) for i in (1, 3, 5)], dtype=np.float32) / 255
    linear = lambda x: np.where(x <= .04045, x / 12.92, ((x + .055) / 1.055) ** 2.4)
    combined = linear(pixels[:, :, :3]) * pixels[:, :, 3:4] + linear(color) * (1 - pixels[:, :, 3:4])
    display = np.where(combined <= .0031308, combined * 12.92, 1.055 * np.maximum(combined, 0) ** (1 / 2.4) - .055)
    return Image.fromarray(np.rint(np.clip(display, 0, 1) * 255).astype(np.uint8))


def wrap(draw, text, font, width):
    lines = []
    for paragraph in text.splitlines():
        line = ""
        for word in paragraph.split():
            candidate = f"{line} {word}".strip()
            if line and draw.textlength(candidate, font=font) > width:
                lines.append(line)
                line = word
            else:
                line = candidate
        lines.append(line)
    return "\n".join(lines)


def compose(raw, plan, frame, pins):
    style = plan["recipe"]["style"]
    image = paper_over(raw, style["paper"])
    w, h = image.size
    scale = w / 1920
    shot = next(s for s in plan["shots"] if s["id"] == frame["shot"])
    font = lambda size, serif=False: ImageFont.truetype(str(repo_path(style["serif_font" if serif else "sans_font"])), max(8, round(size * scale)))
    layer = Image.new("RGBA", image.size)
    draw = ImageDraw.Draw(layer)
    x, y = shot.get("title_position", style["title_position"])
    x, y = round(x * w), round(y * h)
    title_font = font(shot.get("title_size", style.get("title_size", 94)), True)
    title = wrap(draw, shot["title"], title_font, w * .36)
    draw.multiline_text((x, y), title, font=title_font, fill=style["ink"], spacing=round(8 * scale))
    box = draw.multiline_textbbox((x, y), title, font=title_font, spacing=round(8 * scale))
    detail_font = font(30)
    detail = shot["detail"]
    if shot["id"] == "transfer" and frame["source_time"] >= 67:
        detail = "Flush. Check. Balance the return."
    draw.multiline_text((x + round(3 * scale), box[3] + round(24 * scale)),
                        wrap(draw, detail, detail_font, w * .35), font=detail_font,
                        fill=style["ink"], spacing=round(6 * scale))
    # Titles arrive and leave gently; storyboard frames keep complete titles.
    if plan["profile"] != "storyboard":
        progress = (frame["source_time"] - shot["source_in"]) / (shot["source_out"] - shot["source_in"])
        local = progress * shot["duration"]
        opacity = max(0, min(1, local / .6, (shot["duration"] - local) / .6))
        layer.putalpha(layer.getchannel("A").point(lambda a: round(a * opacity)))
    image = Image.alpha_composite(image.convert("RGBA"), layer).convert("RGB")
    draw = ImageDraw.Draw(image)
    label_font = font(24)
    # Labels are projected from the model; no old inset-coordinate transforms.
    for pin in pins:
        ax, ay = pin["u"] * w, pin["v"] * h
        text = pin["text"]
        width = draw.textlength(text, font=label_font) + 20 * scale
        bx = max(12 * scale, min(w - width - 12 * scale, ax - width - 30 * scale))
        by = max(18 * scale, min(h - 145 * scale, ay - 38 * scale))
        color = "#98621D" if pin["warning"] else "#606A6B"
        draw.line((ax, ay, bx + width, by + 16 * scale), fill=color, width=max(1, round(2 * scale)))
        draw.rounded_rectangle((bx, by, bx + width, by + 36 * scale), radius=max(2, round(5 * scale)),
                               fill=style["paper"], outline=color)
        draw.text((bx + 10 * scale, by + 4 * scale), text, font=label_font, fill=style["ink"])
    t = frame["source_time"]
    if frame["scene"] == "unit" and 29 <= t < 85:
        for n, (name, color) in enumerate((("Cold", "#147ECC"), ("Hot", "#D94736"), ("Return", "#E7772C"), ("Access", "#98621D"))):
            draw.text((w - (445 - n * 105) * scale, h - 83 * scale), "• " + name, font=font(26), fill=color)
        qualifier = ("Assembly reveal - isolated replacement" if t < 45 else
                     "Required test before service transfer" if t < 58 else
                     "Proposed service transfer - field verify" if t < 67 else
                     "Schematic flow - after depicted transfer")
        draw.text((36 * scale, h - 83 * scale), qualifier, font=font(22), fill=style["ink"])
    if frame["scene"] == "shared":
        draw.text((36 * scale, h - 83 * scale), "Unit 101 / 302 exceptions require separate review", font=font(22), fill=style["ink"])
    draw.rectangle((0, h - 45 * scale, w, h), fill=style["paper"])
    draw.text((36 * scale, h - 36 * scale), plan["model"]["notice"], font=font(21), fill=style["ink"])
    if plan["profile"] in ("preview", "storyboard"):
        draw.text((36 * scale, 18 * scale), "STORYBOARD" if plan["profile"] == "storyboard" else "PREVIEW - reduced resolution and frame rate", font=font(22), fill=style["ink"])
    return image
