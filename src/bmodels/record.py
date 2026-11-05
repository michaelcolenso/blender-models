"""Basis of record in reports and on renders. No bpy (Pillow only), so it is testable anywhere.

Every review render gets a label strip appended below the image, never drawn over the geometry:
"illustrative, not a contract document", the record the model reflects, and the provenance counts.
"""
from bmodels.spec import STATUS_COLORS

LABEL = "ILLUSTRATIVE: coordination model, not a contract document"


def _font(size, bold=False):
    from PIL import ImageFont
    try:
        return ImageFont.truetype("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf", size)
    except OSError:
        return ImageFont.load_default(size=size)


def _fit(draw, text, size, max_w, bold=False, min_size=11):
    while size > min_size and draw.textlength(text, font=_font(size, bold)) > max_w:
        size -= 1
    return _font(size, bold)


def _srgb(c):  # Base Color is linear; review renders use the Standard view transform
    return int(round(255 * (c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055)))


def stamp_render(path, spec, status_counts, mode="review"):
    """Append the label strip under the image at `path`, in place. Call after the blank-render
    guard, so the strip cannot hide a blank frame."""
    from PIL import Image, ImageDraw
    b = spec["basis_of_record"]
    im = Image.open(path).convert("RGB")
    W, H = im.size
    fs = max(14, H // 48)
    canvas = Image.new("RGB", (W, H + fs * 4 + 24), "white")
    canvas.paste(im, (0, 0))
    d = ImageDraw.Draw(canvas)
    y = H + 10
    d.text((16, y), LABEL, fill=(160, 30, 30), font=_fit(d, LABEL, fs + 2, W - 32, bold=True))
    y += fs + 10
    line = f"{spec.get('project', '')} · record: {b['kind']} · field verification: {b['field_verified']}"
    d.text((16, y), line, fill=(40, 40, 40), font=_fit(d, line, fs, W - 32))
    y += fs + 10
    n = lambda k: status_counts.get(k, 0)  # noqa: E731
    if mode == "review":
        x, f = 16, _font(fs)
        for k in ("confirmed", "provisional", "assumed"):
            d.rectangle([x, y + 2, x + fs, y + 2 + fs], fill=tuple(_srgb(c) for c in STATUS_COLORS[k][:3]),
                        outline=(80, 80, 80))
            t = f"{k} {n(k)}"
            d.text((x + fs + 8, y), t, fill=(40, 40, 40), font=f)
            x += fs + 8 + int(d.textlength(t, font=f)) + 28
    else:
        t = (f"{n('assumed')} elements assumed: colors, finishes and items not shown on documents (see report)"
             if n("assumed") else "No assumed elements.")
        d.text((16, y), t, fill=(40, 40, 40), font=_fit(d, t, fs, W - 32))
    canvas.save(path)


def record_md(spec):
    b = spec["basis_of_record"]
    md = ["", "## Basis of record", f"- Built from: {b['documents']}",
          f"- Record kind: `{b['kind']}` · field verification: `{b['field_verified']}`"]
    if b.get("note"):
        md.append(f"- Note: {b['note']}")
    if b["field_verified"] != "verified":
        md.append("- ⚠️ Geometry reflects the record above, **not** a confirmed built condition.")
    return md


def conflicts_md(spec, results):
    items = [f"- **{c['topic']}**: modeled per `{c['modeled_per']}`"
             + (f" (sources: {', '.join(map(str, c['sources']))})" if c.get("sources") else "") + f". {c['note']}"
             for c in (spec.get("conflicts") or [])]
    items += [f"- ⚠️ {r['check']}: callout {r['expected']} vs drawn {r['actual']} ({r.get('source') or 'no source'})"
              for r in results if r.get("warn")]
    return ["", "## Source conflicts"] + (items or ["None recorded."])


def review_md(spec):
    r = spec.get("review")
    if not r:
        return ["", "## Visual review",
                "**NOT RECORDED.** Passing checks is not a visual review. Look at the review renders and "
                "overlays, then record the result in the spec's `review:` block."]
    md = ["", "## Visual review", f"- {r['date']} by {r['by']}; views: {', '.join(map(str, r['views']))}"]
    for o in r.get("overlays") or []:
        pct = f" {o['edge_pct']}% edge agreement," if o.get("edge_pct") is not None else ""
        md.append(f"- overlay {o['view']}:{pct} verdict **{o['verdict']}**" + (f" ({o['note']})" if o.get("note") else ""))
    if r.get("note"):
        md.append(f"- {r['note']}")
    return md


def assumptions_md(spec):
    return [f"- `{a['id']}` (parameter): {a['basis']}" for a in (spec.get("assumptions") or [])]


def report_fields(spec):
    """Fields added to report.json."""
    return {"basis_of_record": spec["basis_of_record"], "conflicts": spec.get("conflicts") or [],
            "assumptions": spec.get("assumptions") or [], "review": spec.get("review"), "renders_labeled": True}
