# Productization notes (exploratory)

Feasibility notes only. **No package, service or release is proposed or authorized here**, and nothing in the repo
was changed for it. Written 2026-11-08 from the repo as it stands on `main` (`db72f54`).

## What already exists

- A console entry point: `bm = bmodels.cli:main` (`pyproject.toml` `[project.scripts]`).
- A real build backend: `uv_build`, with two modules, `bmodels` (CLI/pipeline) and `cie` (semantic kernel)
  (`[tool.uv.build-backend] module-name`).
- A spec format with provenance enforcement, a bpy-free spec loader (`spec.py`), and checks that run without Blender
  (`bm check`, many tests).
- A synthetic sample and starter template, so a first run needs no real data ([GETTING_STARTED.md](GETTING_STARTED.md)).

## What would block a clean install from a wheel (read from source; install not tried)

1. **Repo-root path assumption.** `src/bmodels/paths.py` sets `ROOT = parents[2]` ("editable install") and the CLI uses
   `PROJECTS`, `TEMPLATES` and `BUILD` under it; `bm new`, `bm build`, `bm run` and `bm check` operate on a checkout, not
   a user's working directory. A wheel install would put `ROOT` inside `site-packages`, and `templates/` is outside the
   two declared modules, so it is probably not packaged. Not tested.
2. **Heavy, pinned runtime.** `bpy==5.0.1` (large wheel, Python 3.11 only) with NumPy and OpenCV pins
   ([BLENDER_VERSION.md](BLENDER_VERSION.md)). It would restrict who can install it and how.
3. **No license file.** The repo has no `LICENSE*` and `pyproject.toml` has no license field. Redistribution rights
   are unstated. Bundled assets ("shared CC0 assets" in `assets/`) and the vendored skill content under `.claude/skills/`
   have their own provenance that has not been audited here.
4. **Real-project data in the same repo.** `projects/` holds client-site specs, takeoffs and deliverables.
   A public package or hosted service must not include or expose them; splitting sample/template from real projects
   would be required. This needs an owner decision.
5. **Isolation for any hosted use.** Running user-supplied specs headless through bpy means CPU-heavy jobs and
   file I/O from untrusted input; a service would need sandboxing, quotas and storage design. Unscoped.

## Who might use it, and what they do today

Not researched. The README targets restoration/defect-repair coordination in occupied multifamily buildings. Before any
build, answer: who pays, what they do instead (hand sketches, generic BIM, photos and PDFs), how they would find it, and
what it costs to maintain. The smallest credible validation would be giving the sample workflow to two or three
practitioners and observing whether they model a real detail with it. Stop if none do.

## Owner decisions needed first

License; whether any real-project material can be shown; whether any packaging spike is worth time at all.
