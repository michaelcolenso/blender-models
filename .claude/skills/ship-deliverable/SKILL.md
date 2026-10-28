---
name: ship-deliverable
description: Package finished renders, films, .blend/.glb files or viewers as a deliverable in this repo — publish large files to GitHub Releases, write the deliverable README, verify and open a PR. Use when outputs of a product or spec are ready to hand over.
---

# Ship a deliverable

## 1. Where it goes
`projects/<site>/deliverables/<name>/` — the folder listed under `deliverables:` in the product's
`product.yaml` (`uv run bm list --json` shows it). Spec builds land in `build/<site>/<spec>/`; copy what is
handed over from there.

## 2. Large files never go in git
Anything over 1 MB (MP4, .blend, ZIP, EXR, GLB, big GIF/HTML):
```bash
uv run bm publish <site>/<product> <file> [file …]
```
This needs `gh` auth (`bm doctor`) and **creates a public download** on the repo's Releases — confirm with
the user before running it. It records sha256 in the product's `release-assets.json`, adds the files to a
`.gitignore` beside them and prints Markdown links. Commit the manifest and `.gitignore`, not the files.
Keep small previews (PNG/JPG under 1 MB, short GIF) in git so the README renders on GitHub.

## 3. README for the deliverable
Lead with what it is and the preview, then the release links, then:
- sources and their revisions; every assumed or provisional element that is visible;
- "Illustrative, not a contract document" if it can reach a scope, PCO or resident notice;
- how to rebuild: `uv run bm run <site>/<product> <step>` and the product README.
All links relative; `bm check` verifies them.

## 4. Verify and hand off
```bash
uv run bm check                      # links, metadata, large-file guard, tests
uv run bm check-products             # if product code changed
```
Branch, commit, push, `gh pr create`; then read CI (`gh pr checks <n>`). Report what was published
(release tag and links) and what was not verified locally (e.g. bpy or GPU steps that only ran in CI).
