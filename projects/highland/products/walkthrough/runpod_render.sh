#!/usr/bin/env bash
# Render and finish the Highland cinematic film on one NVIDIA GPU (e.g. RTX 4090).
#
#   bash projects/highland/products/walkthrough/runpod_render.sh setup          # Python 3.11, bpy 5.0.1, assets, scene checks
#   bash projects/highland/products/walkthrough/runpod_render.sh bench uhd       # one frame per shot, projected hours
#   bash projects/highland/products/walkthrough/runpod_render.sh render uhd 2    # all frames, 2 processes sharing the GPU
#   bash projects/highland/products/walkthrough/runpod_render.sh finish uhd      # grade, titles, score, encode 4K + 1080p, checks
#   bash projects/highland/products/walkthrough/runpod_render.sh all uhd 2       # everything above in order
#
# Profiles: uhd   = 3840 x 1608, 96 samples: 4K master plus a 1080p cut (default);
#           final = native 1920 x 804, 128 samples: 1080p master only.
# Rendering resumes where it stopped; existing frames are skipped.
# DEVICE=CUDA uses CUDA kernels if OptiX is unavailable on the driver.
set -euo pipefail
STAGE=${1:-all}; PROFILE=${2:-uhd}; WORKERS=${3:-2}; DEVICE=${DEVICE:-OPTIX}
ROOT=$(cd "$(dirname "$0")/../../../.." && pwd); cd "$ROOT"
LOG=build/highland-cinema/logs; mkdir -p "$LOG"
# One uv environment from the committed lock. --no-sync: the bpy 5.0.1 wheel mislabels its
# own tag (cp39), so a syncing `uv run` would reinstall bpy under the parallel render workers.
BPY=(uv run --frozen --no-sync python); FIN=("${BPY[@]}")
MASTER=1080; [ "$PROFILE" = uhd ] && MASTER=2160

setup() {
  nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv
  if [ ! -f "$LOG/.apt-done" ]; then
    apt-get update -q
    apt-get install -y -q ffmpeg git-lfs libx11-6 libxrender1 libxfixes3 libxi6 libxext6 libxkbcommon0 libsm6 libice6 libgl1 libegl1
    git lfs install --skip-smudge
    touch "$LOG/.apt-done"
  fi
  command -v uv >/dev/null || curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
  # Python 3.11 (downloaded if the image lacks it) and the locked dependencies; a no-op when current.
  uv sync --frozen --group vision
  # Poly Haven CC0 textures and models, verified against the committed lock (about 190 MB).
  "${BPY[@]}" projects/highland/products/walkthrough/cinema_assets.py
  # cinema.py rebuilds the base walkthrough unless its own validation report is clean and
  # current, then prepares the cinema scene and checks every film camera; CPU, a few minutes.
  # A failed camera check must stop the pipeline before any GPU time is spent.
  if ! "${BPY[@]}" projects/highland/products/walkthrough/cinema.py --validate --only 0 > "$LOG/setup-cinema.log" 2>&1; then
    tail -20 "$LOG/setup-cinema.log"; echo "Cinema scene preparation or camera validation failed"; exit 1
  fi
  grep -E "validated" "$LOG/setup-cinema.log"
}

bench() {
  "${BPY[@]}" projects/highland/products/walkthrough/cinema.py --reuse --device "$DEVICE" --profile "$PROFILE" --bench 2>&1 \
    | grep -E "Cycles devices|BENCH|SHOT|Error|refusing" | tee "$LOG/bench-$PROFILE.log"
}

render() {
  # Bind the frame folder to the prepared scene once; stale frames are moved aside.
  if ! "${BPY[@]}" projects/highland/products/walkthrough/cinema.py --reuse --profile "$PROFILE" --claim-frames > "$LOG/claim-$PROFILE.log" 2>&1; then
    tail -5 "$LOG/claim-$PROFILE.log"; exit 1
  fi
  grep -E "Moved" "$LOG/claim-$PROFILE.log" || true
  pids=()
  for k in $(seq 0 $((WORKERS-1))); do
    "${BPY[@]}" projects/highland/products/walkthrough/cinema.py --reuse --device "$DEVICE" --profile "$PROFILE" --worker "$k/$WORKERS" \
      > "$LOG/render-$PROFILE-$k.log" 2>&1 &
    pids+=($!)
  done
  echo "Rendering with $WORKERS workers; follow progress with: tail -f $LOG/render-$PROFILE-*.log | grep SHOT"
  status=0; for p in "${pids[@]}"; do wait "$p" || status=1; done
  total=$(find "build/highland-cinema/frames/$PROFILE" -name '[0-9]*.png' ! -name '*.tmp.png' | wc -l)
  echo "Frames on disk: $total / 630"
  [ "$status" = 0 ] && [ "$total" = 630 ]
}

finish() {
  "${FIN[@]}" projects/highland/products/walkthrough/cinema_finish.py --profile "$PROFILE" --master "$MASTER"
  ls -la deliverables/highland-cinema
}

case "$STAGE" in
  setup) setup ;;
  bench) bench ;;
  render) render ;;
  finish) finish ;;
  all) setup; bench; render; finish ;;
  *) echo "Unknown stage $STAGE"; exit 2 ;;
esac
