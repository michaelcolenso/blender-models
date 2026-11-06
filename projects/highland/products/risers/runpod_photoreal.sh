#!/usr/bin/env bash
# Render the Corridor 108 work-sequence stills at full quality on one NVIDIA GPU (e.g. RTX 4090).
#
#   bash projects/highland/products/risers/runpod_photoreal.sh setup       # apt libs, uv, locked deps
#   bash projects/highland/products/risers/runpod_photoreal.sh render      # 10 stills, 3840 x 2160, 512 samples
#   bash projects/highland/products/risers/runpod_photoreal.sh render 1920 1080 256   # width height samples
#
# Reads only committed files (the two riser specs); no source PDFs are needed on the pod.
# DEVICE=CUDA uses CUDA kernels if OptiX is unavailable on the driver. Output: build/highland/risers/photoreal/
set -euo pipefail
STAGE=${1:-render}; W=${2:-3840}; H=${3:-2160}; SAMPLES=${4:-512}; DEVICE=${DEVICE:-OPTIX}
ROOT=$(cd "$(dirname "$0")/../../../.." && pwd); cd "$ROOT"
BPY=(uv run --frozen --no-sync python)

setup() {
  nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv
  apt-get update -q
  apt-get install -y -q libx11-6 libxrender1 libxfixes3 libxi6 libxext6 libxkbcommon0 libsm6 libice6 libgl1 libegl1 fonts-dejavu-core
  command -v uv >/dev/null || curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
  uv sync --frozen
}

render() {
  export PATH="$HOME/.local/bin:$PATH"
  "${BPY[@]}" projects/highland/products/risers/photoreal.py --device "$DEVICE" \
    --width "$W" --height "$H" --samples "$SAMPLES" --save-blend
  ls -la build/highland/risers/photoreal/
}

case "$STAGE" in
  setup) setup ;;
  render) render ;;
  all) setup; render ;;
  *) echo "usage: $0 setup|render|all [width height samples]"; exit 2 ;;
esac
