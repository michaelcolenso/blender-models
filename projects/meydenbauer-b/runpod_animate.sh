#!/usr/bin/env bash
# Render the 8-phase 4D sequence on a RunPod GPU (one RTX 4090), then add the HUD and encode.
#   bash projects/meydenbauer-b/runpod_animate.sh setup            # deps, CC0 assets, build + 14 sequence checks
#   bash projects/meydenbauer-b/runpod_animate.sh bench            # 3 frames at full settings, projected hours
#   bash projects/meydenbauer-b/runpod_animate.sh render [workers] # all frames, resumable (default 2 workers)
#   bash projects/meydenbauer-b/runpod_animate.sh finish           # HUD + MP4 + clean master into deliverables/
#   bash projects/meydenbauer-b/runpod_animate.sh hud              # later HUD/text fixes from the clean master (CPU)
# Env: FPS (30 default, as rendered on 2026-10-25; 60 doubles the frames), SAMPLES (128), RES (1.0 = 1920x1080), DEVICE (OPTIX | CUDA)
set -euo pipefail
STAGE=${1:-all}; WORKERS=${2:-2}
FPS=${FPS:-30}; SAMPLES=${SAMPLES:-128}; RES=${RES:-1.0}; DEVICE=${DEVICE:-OPTIX}
ROOT=$(cd "$(dirname "$0")/../.." && pwd); cd "$ROOT"
OUT=build/meydenbauer-b/anim; LOG=$OUT/logs; mkdir -p "$LOG"
BPY=.venv-bpy/bin/python
TAG=final; FRAMES_DIR=$OUT/frames/$TAG-$FPS
END=$((32 * FPS))

setup() {
  bash projects/meydenbauer-b/runpod_render.sh setup
  command -v ffmpeg >/dev/null || apt-get install -y -q ffmpeg
  "$BPY" -W ignore projects/meydenbauer-b/animate.py --fps "$FPS" --no-render 2>&1 | tee "$LOG/setup.log" | grep -E "CHECKS|SAVED"
  grep -q '"ok": true' "$LOG/setup.log"
}

bench() {
  "$BPY" -W ignore projects/meydenbauer-b/animate.py --fps "$FPS" --frames "$((10 * FPS)):$((22 * FPS)):$((6 * FPS))" \
    --res "$RES" --samples "$SAMPLES" --device "$DEVICE" --tag bench 2>&1 | grep -E "FRAME|Error" | tee "$LOG/bench.log"
  awk -v n="$END" '/^FRAME/ {gsub("s","",$3); t+=$3; c++} END {if (c) printf "mean %.1f s/frame -> %.1f h for %d frames on one worker\n", t/c, t/c*n/3600, n}' "$LOG/bench.log"
}

render() {
  pids=()
  for k in $(seq 0 $((WORKERS - 1))); do
    "$BPY" -W ignore projects/meydenbauer-b/animate.py --fps "$FPS" --res "$RES" --samples "$SAMPLES" --device "$DEVICE" \
      --tag "$TAG" --worker "$k/$WORKERS" > "$LOG/render-$k.log" 2>&1 &
    pids+=($!)
  done
  echo "Rendering $END frames with $WORKERS workers; progress: tail -f $LOG/render-*.log | grep FRAME"
  status=0; for p in "${pids[@]}"; do wait "$p" || status=1; done
  n=$(find "$FRAMES_DIR" -name '[0-9]*.png' ! -name '*.tmp.png' | wc -l)
  echo "Frames on disk: $n / $END"
  [ "$status" = 0 ] && [ "$n" = "$END" ]
}

finish() {
  "$BPY" projects/meydenbauer-b/anim_finish.py --tag "$TAG-$FPS" --fps "$FPS" --crf 16
  mkdir -p deliverables/meydenbauer-b/anim
  cp "$OUT/$TAG-$FPS.mp4" "$OUT/$TAG-$FPS-poster.png" "$OUT/$TAG-$FPS-clean.mp4" deliverables/meydenbauer-b/anim/
  ls -la deliverables/meydenbauer-b/anim
  echo "Commit deliverables/meydenbauer-b/anim (MP4s go to Git LFS) before stopping the pod: the clean master"
  echo "is what makes later HUD fixes a CPU job (stage: hud) instead of a re-render."
}

hud() {   # no GPU needed: re-apply the HUD to the saved clean master
  "$BPY" projects/meydenbauer-b/anim_finish.py --tag "$TAG-$FPS" --fps "$FPS" --crf 16 \
    --from-video "deliverables/meydenbauer-b/anim/$TAG-$FPS-clean.mp4"
  cp "$OUT/$TAG-$FPS.mp4" "$OUT/$TAG-$FPS-poster.png" deliverables/meydenbauer-b/anim/
}

case "$STAGE" in
  setup) setup ;;
  bench) bench ;;
  render) render ;;
  finish) finish ;;
  hud) hud ;;
  all) setup; bench; render; finish ;;
  *) echo "Unknown stage $STAGE"; exit 2 ;;
esac
