# 200 W Highland — installation models and 90-second animation

**Current presentation:** [Full-frame architectural cut and editable titles](immersive-film/README.md) · [Watch the complete 90-second review](../../deliverables/highland-installation/immersive-film/Highland-repipe-immersive-90s-1080p.mp4).

[Studio revision: exterior opening, depth, cameras and callouts](studio-upgrade/README.md) · [Revised film and upgrade guide](../../deliverables/highland-installation/studio-upgrade/README.md)

The proposed CPVC replacement sequence follows shared distribution into the **Unit B / 106 pilot**, then shows verification, access, new distribution, branches, testing, service transfer and restoration. This is a separate pilot from the earlier Unit A / 107 strategy study in `projects/highland-repipe/`.

[Watch or download the films and editable models](https://github.com/michaelcolenso/blender-models/releases/tag/highland-repipe-2026-10-17) · [Eight-frame preview](../../deliverables/highland-installation/README.md)

The delivery contains the 90-second 4K and 1080p H.264 movies, eight-page storyboard, editable animation package and original installation-model package. Git contains the governing specifications, scripts, source crops, individual storyboard frames and review evidence. The five large downloads use **Git LFS** in `deliverables/highland-installation/assets/`; the release page links to those files. `release-assets.json` records their sizes and SHA-256 hashes.

## Source and status

- [Installation specification](installation/highland-installation-proposed.yaml) governs the proposed geometry. Every new physical element is **assumed**; source drawings establish relationships, not measured installation dimensions.
- [Existing-reference specification](installation/highland-installation-existing-reference.yaml) remains separate. The user's report of failing CPVC does not establish surveyed existing routes.
- [Animation specification](animation-90s/animation-spec.json) governs the exact eight-shot, 90-second timeline. Flow markers begin only after the depicted transfer.
- [Source manifest](source-manifest.json) records the supplied 19-sheet plumbing set issued 29 October 2007. P3.02 supplies the shared schematic; P4.01 supplies Unit B / 106 context. Unit 101 irrigation and Unit 302 alternate-wall notes require separate review.

The source title says 200 West Highland; its location block says 202 W Highland. That discrepancy and the governing revision remain unresolved. The models establish no verified pipe sizes, material selection, isolation boundaries, opening dimensions, hydraulic performance, test results or shutdown duration. Fixture symbols represent groups rather than verified individual counts.

## Restore the editable project

Use Python 3.11 and Git LFS, with GitHub access to this private repository. Run these commands from the repository root:

```bash
git lfs install
git lfs pull --include='deliverables/highland-installation/assets/*'
uv run python projects/highland-installation/restore_assets.py
```

The restoration script verifies both archives before writing, restores the original PDF, Blender/GLB models, PDFs, short installation movie and audio stems, and preserves modified local assets by refusing to overwrite them. It leaves tracked source files intact. The two 90-second movie masters remain in the delivery assets folder. To use ZIPs downloaded through GitHub's **Download raw file** button instead, pass their directory as the script's optional argument.

Open `animation-90s/Highland-repipe-90s.blend` at **MASTER - 90 seconds**. Its two source-derived 3D scenes, camera keyframes, construction reveals, native graphics and relative audio/image references remain editable. Keep the folder structure intact. The original installation Blender files remain separate and unchanged.

## Rebuild and verify

FFmpeg/FFprobe and the DejaVu Sans regular/bold fonts are system prerequisites. `uv sync --group vision --group pdf` (from the repo root) installs Python 3.11 and the locked dependencies; the generic house/detail builder does not implement this plumbing-method model.

```bash
uv sync --group vision --group pdf
uv run python projects/highland-installation/installation/validate_installation.py
```

For geometry revisions, edit `installation/highland-installation-proposed.yaml`, run `build_installation.py` and `verify_blends.py`, then `package_installation.py` and `validate_installation.py`. The packaging step refreshes `installation-data.json` from YAML. `prepare_spec.py` recreates the initial specification and must not overwrite later field edits.

For visual re-rendering, use `animation-90s/animate_highland.py --resume`, `compose_film.py --watch`, `finalize_blender.py`, then `deliver_animation.py`. Run the scripts with the prepared environment. A fresh render generates the omitted frame cache; final delivery validation requires that cache and both finished MP4s. To create a new rig from changed source models, run `animate_highland.py` without `--resume`. Update the animation specification and source hashes when intentionally revising its source models.

The supplied audio stems avoid a voice-model download. Audio regeneration additionally needs `uv sync --group audio` and the `en_US-ljspeech-high` Piper model and configuration referenced in `animation-90s/audio/CREDITS.txt`; voice weights are not committed.

## Validation and production limits

The delivered installation passed 42 checks. The animation passed 50 delivery checks, with saved geometry comparisons for 94 unit elements and 45 shared elements. [Installation review](installation/VISUAL-REVIEW.md), [animation review](animation-90s/VISUAL-REVIEW.md) and their JSON records describe the actual checks. These are production evidence, not field acceptance.

The 4K master combines 1600 × 900 model imagery rendered at six scene samples per second, interpolated to 24 fps, with native 4K editorial graphics. The editable rig retains full 24 fps animation for higher-sampling renders. Narration is synthesized; the instrumental score and cues are original procedural audio. The footer reads **“Proposed installation sequence · Field verification required.”**
