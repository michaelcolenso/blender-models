#!/usr/bin/env bash
# Render the 4D film on a RunPod GPU (one RTX 4090), then add the HUD and encode.
#   PLAN=overview (default): all four units together, 8 phases x 4 s = 32 s
#   PLAN=sequence: one unit at a time on the strawman schedule, 101.5 s (3,045 frames at 30 fps)
#   bash projects/meydenbauer-b/products/underslab/runpod_animate.sh setup            # deps, CC0 assets, build + 14 sequence checks
#   bash projects/meydenbauer-b/products/underslab/runpod_animate.sh bench            # 3 frames at full settings, projected hours
#   bash projects/meydenbauer-b/products/underslab/runpod_animate.sh render [workers] # all frames, resumable (default 2 workers)
#   bash projects/meydenbauer-b/products/underslab/runpod_animate.sh finish           # HUD + MP4 + clean master into deliverables/
#   bash projects/meydenbauer-b/products/underslab/runpod_animate.sh hud              # later HUD/text fixes from the clean master (CPU)
# Env: PLAN (overview | sequence), FPS (30 default, as rendered on 2026-10-25; 60 doubles the frames), SAMPLES (128),
#      RES (1.0 = 1920x1080), DEVICE (OPTIX | CUDA)
set -euo pipefail
STAGE=${1:-all}; WORKERS=${2:-2}
PLAN=${PLAN:-overview}; FPS=${FPS:-30}; SAMPLES=${SAMPLES:-128}; RES=${RES:-1.0}; DEVICE=${DEVICE:-OPTIX}
ROOT=$(cd "$(dirname "$0")/../../../.." && pwd); cd "$ROOT"
OUT=build/meydenbauer-b/anim; LOG=$OUT/logs; mkdir -p "$LOG"
# One uv environment from the committed lock. --no-sync: the bpy 5.0.1 wheel mislabels its
# own tag (cp39), so a syncing `uv run` would reinstall bpy under parallel render workers.
BPY=(uv run --frozen --no-sync python)
if [ "$PLAN" = sequence ]; then
  TAG=seq; BENCH="$((20 * FPS)):$((80 * FPS)):$((30 * FPS))"
  END=$("${BPY[@]}" projects/meydenbauer-b/products/underslab/schedule.py --frames "$FPS" 2>/dev/null || echo 0)
else
  TAG=final; BENCH="$((10 * FPS)):$((22 * FPS)):$((6 * FPS))"; END=$((32 * FPS))
fi
FRAMES_DIR=$OUT/frames/$TAG-$FPS

setup() {
  bash projects/meydenbauer-b/products/underslab/runpod_render.sh setup
  command -v ffmpeg >/dev/null || apt-get install -y -q ffmpeg
  "${BPY[@]}" -W ignore projects/meydenbauer-b/products/underslab/animate.py --plan "$PLAN" --fps "$FPS" --no-render 2>&1 | tee "$LOG/setup.log" | grep -E "CHECKS|SAVED"
  grep -q '"ok": true' "$LOG/setup.log"
  END=$("${BPY[@]}" projects/meydenbauer-b/products/underslab/schedule.py --frames "$FPS"); [ "$PLAN" = sequence ] || END=$((32 * FPS))
}

bench() {
  "${BPY[@]}" -W ignore projects/meydenbauer-b/products/underslab/animate.py --plan "$PLAN" --fps "$FPS" --frames "$BENCH" \
    --res "$RES" --samples "$SAMPLES" --device "$DEVICE" --tag "bench-$TAG" 2>&1 | grep -E "FRAME|Error" | tee "$LOG/bench.log"
  awk -v n="$END" '/^FRAME/ {gsub("s","",$3); t+=$3; c++} END {if (c) printf "mean %.1f s/frame -> %.1f h for %d frames on one worker\n", t/c, t/c*n/3600, n}' "$LOG/bench.log"
}

render() {
  pids=()
  for k in $(seq 0 $((WORKERS - 1))); do
    "${BPY[@]}" -W ignore projects/meydenbauer-b/products/underslab/animate.py --plan "$PLAN" --fps "$FPS" --res "$RES" --samples "$SAMPLES" \
      --device "$DEVICE" --tag "$TAG" --worker "$k/$WORKERS" > "$LOG/render-$TAG-$k.log" 2>&1 &
    pids+=($!)
  done
  echo "Rendering $END frames with $WORKERS workers; progress: tail -f $LOG/render-$TAG-*.log | grep FRAME"
  status=0; for p in "${pids[@]}"; do wait "$p" || status=1; done
  n=$(find "$FRAMES_DIR" -name '[0-9]*.png' ! -name '*.tmp.png' | wc -l)
  echo "Frames on disk: $n / $END"
  [ "$status" = 0 ] && [ "$n" = "$END" ]
}

finish() {
  "${BPY[@]}" projects/meydenbauer-b/products/underslab/anim_finish.py --plan "$PLAN" --tag "$TAG-$FPS" --fps "$FPS" --crf 16
  mkdir -p projects/meydenbauer-b/deliverables/underslab/anim
  cp "$OUT/$TAG-$FPS.mp4" "$OUT/$TAG-$FPS-poster.png" "$OUT/$TAG-$FPS-clean.mp4" projects/meydenbauer-b/deliverables/underslab/anim/
  ls -la projects/meydenbauer-b/deliverables/underslab/anim
  echo "Commit projects/meydenbauer-b/deliverables/underslab/anim (MP4s go to Git LFS) before stopping the pod: the clean master"
  echo "is what makes later HUD fixes a CPU job (stage: hud) instead of a re-render."
}

hud() {   # no GPU needed: re-apply the HUD to the saved clean master
  "${BPY[@]}" projects/meydenbauer-b/products/underslab/anim_finish.py --plan "$PLAN" --tag "$TAG-$FPS" --fps "$FPS" --crf 16 \
    --from-video "projects/meydenbauer-b/deliverables/underslab/anim/$TAG-$FPS-clean.mp4"
  cp "$OUT/$TAG-$FPS.mp4" "$OUT/$TAG-$FPS-poster.png" projects/meydenbauer-b/deliverables/underslab/anim/
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
