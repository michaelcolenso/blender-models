#!/usr/bin/env bash
# Render the Building B construction-phase views on a RunPod GPU (one RTX 4090 is plenty).
#   bash projects/meydenbauer-b/products/underslab/runpod_render.sh setup          # deps, CC0 assets, model + checks
#   bash projects/meydenbauer-b/products/underslab/runpod_render.sh bench          # one view, low samples, timed
#   bash projects/meydenbauer-b/products/underslab/runpod_render.sh render final   # 2560x1600, 512 spp, all views
#   bash projects/meydenbauer-b/products/underslab/runpod_render.sh render uhd     # 3840x2400, 1024 spp
#   bash projects/meydenbauer-b/products/underslab/runpod_render.sh deliver final  # copy finished PNGs to deliverables/
# Needs only the committed JSON (spec, shell, structure); the source PDFs are not used here.
set -euo pipefail
STAGE=${1:-all}; PROFILE=${2:-final}; DEVICE=${DEVICE:-OPTIX}
ROOT=$(cd "$(dirname "$0")/../../../.." && pwd); cd "$ROOT"
OUT=build/meydenbauer-b/realism; LOG=$OUT/logs; mkdir -p "$LOG"
# One uv environment from the committed lock. --no-sync: the bpy 5.0.1 wheel mislabels its
# own tag (cp39), so a syncing `uv run` would reinstall bpy under parallel render workers.
BPY=(uv run --frozen --no-sync python)
SAMPLES=${SAMPLES:-$([ "$PROFILE" = uhd ] && echo 1024 || echo 512)}
VIEWS=${VIEWS:-b104_plan,b104_overview,b104_master_bath,b104_kitchen_run,section_b103_east}

setup() {
  nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv || true
  if [ ! -f "$LOG/.apt-done" ]; then
    apt-get update -q
    apt-get install -y -q libx11-6 libxrender1 libxfixes3 libxi6 libxext6 libxkbcommon0 libsm6 libice6 libgl1 libegl1 fonts-dejavu-core
    touch "$LOG/.apt-done"
  fi
  command -v uv >/dev/null || curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
  # Python 3.11 (downloaded if the image lacks it) and the locked dependencies; a no-op when current.
  uv sync --frozen
  "${BPY[@]}" projects/meydenbauer-b/products/underslab/assets.py
  "${BPY[@]}" projects/meydenbauer-b/products/underslab/takeoff.py > "$LOG/takeoff.log"
  "${BPY[@]}" -W ignore projects/meydenbauer-b/products/underslab/realism.py --no-render 2>&1 | tee "$LOG/setup.log" | grep -E "CHECKS|SAVED"
  grep -q '"ok": true' "$LOG/setup.log"
}

bench() {
  "${BPY[@]}" -W ignore projects/meydenbauer-b/products/underslab/realism.py --only b104_kitchen_run --device "$DEVICE" --profile "$PROFILE" \
    --samples 64 2>&1 | grep -E "Cycles devices|RENDER|Error" | tee "$LOG/bench-$PROFILE.log"
  echo "Scale RENDER seconds by $SAMPLES/64 for the full render of each view."
}

render() {
  "${BPY[@]}" -W ignore projects/meydenbauer-b/products/underslab/realism.py --only "$VIEWS" --device "$DEVICE" --profile "$PROFILE" \
    --samples "$SAMPLES" 2>&1 | tee "$LOG/render-$PROFILE.log" | grep -E "RENDER|Error"
}

deliver() {
  mkdir -p projects/meydenbauer-b/deliverables/underslab/realism
  for v in ${VIEWS//,/ }; do cp "$OUT/$v-$PROFILE.png" projects/meydenbauer-b/deliverables/underslab/realism/; done
  ls -la projects/meydenbauer-b/deliverables/underslab/realism
  echo "Commit and push from the pod, or download the folder."
}

case "$STAGE" in
  setup) setup ;;
  bench) bench ;;
  render) render ;;
  deliver) deliver ;;
  all) setup; bench; render; deliver ;;
  *) echo "Unknown stage $STAGE"; exit 2 ;;
esac
