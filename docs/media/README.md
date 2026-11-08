# docs/media

Preview images used by the docs. **Synthetic and illustrative: not a contract document, not a real project.**

| File | Shows |
|---|---|
| [sample-bay-review-iso.png](sample-bay-review-iso.png) | Isometric review render of the fictional `sample/sample-bay` balcony framing bay |
| [sample-bay-review-front.png](sample-bay-review-front.png) | Front review render of the same model |

Caption: *Synthetic sample review render with provenance strip. Illustrative coordination model — not a contract
document.* Colors: green confirmed, yellow provisional, orange assumed. The strip under the render (record kind,
field-verification status, provenance counts) is part of the image and must not be cropped.

## How they were generated

```bash
uv run bm build sample/sample-bay        # writes build/sample/sample-bay/sample-bay_review_{iso,front}.png
```

Built 2026-11-08 on Blender 5.0.1 (CPU Cycles), `**PASS** — 20/20 checks`. The two PNGs were resized from 1600 px to 1100 px
wide with Pillow (Lanczos) to stay under the 1 MB repo limit; nothing else was changed. The plan view is not included: it
shows only the decking and hides the framing. Both images were viewed after generation.

Regenerate them if the sample spec or the review renderer changes. Real-project imagery is deliberately not used here; that
needs the owner's approval.
