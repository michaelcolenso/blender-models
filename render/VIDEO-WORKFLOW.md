# Describe a video, then render the existing model

The first shared template is the Highland proposed-installation explainer for
**Unit B / 106**. It combines the existing studio model's geometry, cutaways,
pipe reveals and camera animation with new full-frame titles, projected labels
and the existing narrated soundtrack. It renders the actual 3D scenes again.

[View the rendered storyboard, motion sample and validation](../deliverables/highland-installation/video-template/README.md).

Describe a film in this conversation. The description becomes a saved recipe in
`render/videos/`, which can be reviewed, repeated and changed. There is no
separate AI service to configure for this conversational workflow; the command
line and Actions consume the saved recipe, not free-form text directly.

Example direction:

> Explain the proposed Highland installation to owners. Start outside, introduce
> the shared distribution, then move into the Unit B cutaway. Show preparation,
> the isolated replacement, testing, transfer and restoration. Use the warm
> studio treatment, clear labels and calm narration. Deliver native 1080p/24.
> Retain the field-verification notice.

## What exists now

| Layer | File | Purpose |
| --- | --- | --- |
| Model library | `render/models.json` | Exact model version, scenes, cameras, geometry authority and validation evidence |
| First video brief | `render/videos/highland-installation.json` | Written direction, nine shots, timings, titles, style and audio |
| Planning | `tools/video_plan.py` | Exact source times, output frames, chunk assignments and input fingerprints |
| Rendering | `tools/render_video.py` | Native Cycles image plates and projected model labels |
| Graphics | `tools/video_graphics.py` | Warm paper, serif titles, labels, legend and provenance footer |
| Assembly | `tools/assemble_video.py` | Exact frame-set checks, storyboard or narrated H.264 film |
| Actions | `.github/workflows/render-video.yaml` | Manual CPU/GPU rendering, chunk retries and downloadable artifacts |

The default film retains the checked 90-second sequence:

| Output time | Chapter | Existing model scene |
| --- | --- | --- |
| 0–4 s | Exterior context | Exterior opening |
| 4–8 s | Shared distribution | Shared distribution |
| 8–18 s | Verify and protect | Unit B installation |
| 18–29 s | Open and prepare | Unit B installation |
| 29–45 s | Install isolated replacement | Unit B installation |
| 45–58 s | Complete branches, test and inspect | Unit B installation |
| 58–73 s | Transfer and commission | Unit B installation |
| 73–85 s | Restore and document | Unit B installation |
| 85–90 s | Completed-system overview | Shared distribution |

The ten storyboard views include separate 60 s and 69 s views so isolation and
later schematic flow can be reviewed independently. The exterior transition is
an editorial cut, not a claim that a specific facade opening locates the unit.

## Quality profiles

| Profile | Native model imagery | Purpose |
| --- | --- | --- |
| `storyboard` | Ten selected 960×540 stills, 16 samples | Composition, labels and sequence |
| `preview` | 640×360, 6 rendered fps, 8 samples | Reduced-cost motion review |
| `production1080` | 1920×1080, 24 rendered fps, 128 samples | Native production starting point |
| `production4k` | 3840×2160, 24 rendered fps, 256 samples | Native 4K production starting point |

All use the saved studio lighting/materials, Cycles, denoising and seed 0.
Production renders every delivered frame. Preview repeats its six rendered
samples per second into a 24 fps MP4; **no optical-flow interpolation** is used.
Sampling counts are starting points: inspect thin pipes, shadow-catcher grain
and temporal stability before treating a production render as final.

The output is display-referred RGBA PNG plates plus edited PNGs and H.264 MP4.
The PNG plates already have the scene's AgX transform; the paper is composited
in display-linear sRGB, with text added afterward. This first implementation
does not produce scene-linear multilayer EXR masters or temporal denoising.

## Run the first storyboard

From the repository root, use Python 3.11 and the system libraries from the
Actions workflow. FFmpeg, FFprobe and Git LFS are needed for movie assembly and
large-asset restoration.

```bash
python3.11 -m venv .venv-render
.venv-render/bin/python -m pip install -r render/requirements.txt
.venv-render/bin/python tools/video_plan.py render/videos/highland-installation.json \
  --profile storyboard --output build/highland-video/plan.json
.venv-render/bin/python tools/render_video.py build/highland-video/plan.json \
  --output build/highland-video
.venv-render/bin/python tools/assemble_video.py build/highland-video/plan.json \
  --frames build/highland-video/frames --output build/highland-video/delivery
```

Open `build/highland-video/delivery/storyboard.png` and the individual images in
`frames/`. The model's Git LFS content is restored by checksum into a generated
cache if the checkout contains a pointer. The source model is never overwritten.
Only the requested model and soundtrack are downloaded, not the entire asset
collection. Packed model textures are reused.

For a two-second motion sample centered on the installation poster view:

```bash
.venv-render/bin/python tools/video_plan.py render/videos/highland-installation.json \
  --profile preview --shot install --sample-seconds 2 --output build/highland-sample/plan.json
.venv-render/bin/python tools/render_video.py build/highland-sample/plan.json \
  --output build/highland-sample
.venv-render/bin/python tools/assemble_video.py build/highland-sample/plan.json \
  --frames build/highland-sample/frames --output build/highland-sample/delivery --no-audio
```

The silent sample checks movement and graphics. For the complete default film,
omit `--no-audio` to reuse its narrated soundtrack.

## Change the brief without losing previous work

Copy the recipe to a new filename and ID, then edit the brief, shot selection,
titles, detail text, title positions and durations. Source times address the
existing animated rig. Durations support playback speeds from 0.5× to 2× and
must align to the selected profile's native frame boundaries.

Create a fresh output directory and compile a fresh plan for each revision.
For title/label changes, reuse compatible Blender plates from a completed run:

```bash
.venv-render/bin/python tools/render_video.py build/revised-video/plan.json \
  --output build/revised-video --plates build/highland-video/plates
```

Plate compatibility depends on model version, source moment, camera, render
settings, device and renderer code. Typography changes do not invalidate the
plates. Retimed or newly selected moments render only when no matching plate
exists. The model file retains the editable cameras and animated construction
states; new camera blocking or a different construction sequence requires a rig
revision and the relevant geometry/continuity checks.

The current audio adapter trims and retimes the existing soundtrack by source
shot intervals. The default 90-second edit preserves its order and timing.
A substantially different story needs revised narration and an audio adapter
or timing map suited to that recording; cutting the old voice at arbitrary
times can cut sentences. No voice-generation service is called by this template.

## Use GitHub Actions

After the workflow is on the default branch, select **Actions → Render a model
video → Run workflow**. Choose the recipe, profile, one shot or `all`, and runner.
The default is a CPU storyboard. Commit and push the workflow and recipe before
starting a remote run.

Each render job owns a nonoverlapping range of up to 48 native frames. At 90 s,
native 24 fps production has **2,160 frames in 45 chunks**. Two chunks run at a
time; each has a 180-minute timeout. Successful chunks remain available when a
different chunk fails. Use **Re-run failed jobs** to recover the failed chunks;
artifact replacement avoids mixing partial attempts.

Artifacts retain the plan with input hashes, image plates, edited frames, frame hashes,
raw-image checks, chunk logs and an assembled delivery report for 14 days.
Assembly refuses missing, extra, changed or mismatched frames. Move approved
masters to the normal release/delivery archive before artifacts expire. A full
native 4K frame set can be large; plan storage and retention before running it.

For GPU production, provision a trusted ephemeral NVIDIA runner labeled
`self-hosted`, `linux`, `x64`, `blender-gpu`, with compatible drivers, Python 3.11,
sudo/apt and Git LFS. The `gpu` input selects OptiX and fails if no compatible
device is available. Restrict this manual workflow to trusted revisions and
runner groups. No GPU worker or paid render service is provisioned by this code.

Run a short sample on that worker to measure cost and choose final sampling.
The supplied `render/videos/highland-installation-quality-test.json` renders
four representative frames with a production profile: exterior, shared risers,
installed piping and post-transfer flow. Select that recipe with
`production1080` and `gpu` for the first GPU test. Inspect its frame PNGs and
per-frame timings before scheduling the full film. Its very short MP4 is only
a frame-check container, not a presentation edit.
The Actions workflow requires the GPU input for production profiles. CPU
production remains available through the local CLI for deliberate benchmarks,
but is slow for these scenes. Storyboard validation on this CPU
environment does not establish GPU compatibility or full-film render cost.

## Bringing in the other models

Add each model to the library with a stable ID, content hash, scope, source
specification, validation evidence, scene/camera aliases and dependency handling.
Then add a presentation adapter and recipes for its available motions.

The next candidates are the Highland archviz walkthrough's checked 624-frame
camera route, followed by the Cottage/detail builders. Reuse their source models
and native animation; supply separate visual presets where their presentation
needs differ. The current adapter supports the Highland studio model only.

All physical installation geometry remains assumed. The workflow checks rendering
and prior validation evidence; it does not establish field dimensions, an actual
isolation boundary, hydraulic performance or completed testing. Every automated
delivery report leaves visual review pending.
