# Building B presentation film: *Home, Uninterrupted*

A 74.5-second presentation film of the proposed under-slab waste re-pipe at 101 Meydenbauer,
Building B. It is made for an owner, board or property-manager presentation. **Illustrative, not a
contract document.** The sequence, protection, depths and fixtures are assumed, and the routes are
diagrammatic. The script, sources and limits are in the
[product README](../../products/agency-film/README.md).

| File | What it is |
| --- | --- |
| `poster.jpg` | The *after* frame (shot 11). Written by the `video` step; not committed yet |
| `contact-sheet.jpg` | One frame from each of the 13 shots. Written by the `video` step; not committed yet |
| [Meydenbauer-B-film.srt](../../products/agency-film/Meydenbauer-B-film.srt) | Captions, timed to the narration |
| `Meydenbauer-B-film-1080p24.mp4` | The film: H.264, AAC at −16 LUFS, with an embedded caption track. It is over 1 MB, so it is not in Git. Publish it with `uv run bm publish meydenbauer-b/agency-film build/meydenbauer-b/agency-film/Meydenbauer-B-film-1080p24.mp4` and link the printed URL here. |

**Before any external use:**

- Replace the scratch TTS narration with a booked voice.
- Confirm the cited claims against the bid set: Sch 40 ABS at ¼"/ft, the 2'-0" trench, the 5"
  pour-back, the water test, and the nightly toilet and sink. This film reuses the underslab
  product's citations.
- Decide whether the footage, which shows all four units working at once, may run under the
  "unit by unit" line. Otherwise, render the sequence film on RunPod.
