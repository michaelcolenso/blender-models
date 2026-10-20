# Render the cinematic film on a RunPod GPU

One RTX 4090 is enough. The whole film is 630 rendered frames: the end card is 2D.
`runpod_render.sh` installs the pinned stack, rebuilds and validates the scenes,
benchmarks the GPU, renders with parallel processes, then grades, scores and
encodes. It can resume after an interruption.

## Why the GPU helps, and what it doesn't change

The time goes into path tracing, not scene setup. Measured on the 4-vCPU
development container with Cycles phase timestamps, a 1920 × 804 frame breaks down as:

| Phase | Time per frame |
|---|---|
| Scene sync, BVH, light tree | ≈ 2 s |
| Sky importance map | ≈ 1.6 s, removed in this branch: the section void is now a backdrop object rather than an animated world |
| Path tracing | ≈ 7–13 s per sample |
| Compositing and 16-bit PNG write | ≈ 1 s |

Path tracing is the work a 4090 parallelizes. Fixed per-frame costs stay
CPU-bound. Running two render processes on the one GPU overlaps one process's
sync and save with the other's sampling; that is what the `workers` argument does.

The GPU removes the CPU compromises: 1280-wide frames upscaled 1.5×, 20 samples,
and denoiser texture in motion blur and depth of field. Scene detail comes from the
scanned CC0 materials and models in `cinema_assets.py`, which `setup` downloads.

## Pod

- **GPU:** 1 × RTX 4090. The `bpy==5.0.1` wheel ships OptiX PTX and `sm_89` CUDA
  kernels, the 4090's architecture. This was confirmed in the wheel contents, but
  not yet run on a 4090.
- **Template:** any Ubuntu image with the NVIDIA driver exposed, for example RunPod's
  PyTorch template. The script installs Python 3.11 with `uv` if the image lacks it.
- **Storage:** clone the repository into the persistent volume, usually `/workspace`,
  so frames survive a pod stop. The Poly Haven assets add about 190 MB.

| Profile | Picture | Frames on disk | Plus lossless master and venvs | Volume |
|---|---|---|---|---|
| `uhd` (4K master + 1080p cut, default) | 3840 × 1608 | ≈ 16 GB | ≈ 7 GB | 50 GB |
| `final` (1080p master only) | 1920 × 804 | ≈ 4 GB | ≈ 3 GB | 20 GB |

## Steps

The repository is private. Use a fine-grained GitHub token with read access to
this repository, plus write access if the pod should push the finished film back.

```bash
cd /workspace
GIT_LFS_SKIP_SMUDGE=1 git clone https://github.com/michaelcolenso/blender-models.git   # username + token
cd blender-models

bash projects/highland-drone/runpod_render.sh setup          # ≈ 5–10 min, CPU; downloads CC0 assets
bash projects/highland-drone/runpod_render.sh bench uhd       # one frame per shot + projection
```

`GIT_LFS_SKIP_SMUDGE=1` skips the large installation-film LFS files. The cinema
does not use them.

`bench` writes `build/highland-cinema/bench-uhd.json` and prints `projected_hours_one_worker`.
It renders one warm-up frame first, because OptiX compiles its kernels once per pod.
Look at the bench frames in `build/highland-cinema/frames/bench-uhd/` before
committing to the full render. Then run:

```bash
bash projects/highland-drone/runpod_render.sh render uhd 2   # leave running; resumes if restarted
tail -f build/highland-cinema/logs/render-uhd-*.log | grep SHOT
bash projects/highland-drone/runpod_render.sh finish uhd      # ≈ 20–30 min on CPU; writes deliverables/highland-cinema/
```

Use `final` in place of `uhd` for a quicker 1080p-only film. If the GPU sits below about 90%
utilization in `nvidia-smi` with two workers, try three. If OptiX is unavailable
on the pod's driver, prefix the commands with `DEVICE=CUDA`.

Run `render` inside `tmux` or with `nohup`, so a closed browser tab doesn't stop it.

## Bring the film back

`deliverables/highland-cinema/` then holds the 4K master (about 120 MB, tracked by
Git LFS through the folder's `.gitattributes`), the 1080p cut (about 38 MB), stills,
the shot sheet, the GIF and the checks. With a token that can write to the
repository, push them on a new branch and open a pull request:

```bash
git checkout -b cinema/highland-gpu-film
git add deliverables/highland-cinema
git commit -m "Add native GPU render of the Highland cinematic film"   # set git user.name/email first
git push -u origin cinema/highland-gpu-film
```

Git LFS storage and bandwidth count against the account's LFS quota. The 76 MB
editable scene is not committed; `cinema.py` rebuilds it from the locked assets.

## Checks

The finish step fails if any of these fail:

- frame count, size, codec, frame rate and duration;
- stereo 48 kHz AAC;
- loudness within ±1 LU of −16 LUFS and true peak at or below −1 dBTP;
- a non-blank picture in every shot.

Camera clearance and smoothness checks run during `setup` (`cinema-validation.json`).
These checks do not judge the look; review the film itself.
