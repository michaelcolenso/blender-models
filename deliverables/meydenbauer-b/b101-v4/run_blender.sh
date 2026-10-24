#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

find_blender() {
  if [[ -n "${BLENDER_BIN:-}" && -x "${BLENDER_BIN}" ]]; then
    printf '%s\n' "$BLENDER_BIN"; return 0
  fi
  if command -v blender >/dev/null 2>&1; then
    command -v blender; return 0
  fi
  if [[ -x /Applications/Blender.app/Contents/MacOS/Blender ]]; then
    printf '%s\n' /Applications/Blender.app/Contents/MacOS/Blender; return 0
  fi
  for p in /Applications/Blender*.app/Contents/MacOS/Blender; do
    [[ -x "$p" ]] && { printf '%s\n' "$p"; return 0; }
  done
  return 1
}

BLENDER="$(find_blender || true)"
if [[ -z "$BLENDER" ]]; then
  echo "ERROR: Blender executable not found. Set BLENDER_BIN=/full/path/to/blender and rerun." >&2
  exit 127
fi

if command -v python3 >/dev/null 2>&1; then
  python3 "$ROOT/scripts/preflight.py" | tee "$ROOT/logs/preflight.log"
else
  "$BLENDER" --background --factory-startup --python "$ROOT/scripts/preflight.py" 2>&1 | tee "$ROOT/logs/preflight.log"
fi

echo "Using Blender: $BLENDER"
"$BLENDER" --version | head -n 3 | tee "$ROOT/logs/blender_version.log"

# Pass any extra arguments (for example --render-keyframes) to the Blender-side runner.
"$BLENDER" --background --factory-startup \
  --python "$ROOT/scripts/run_build_and_verify.py" -- \
  --fail-on-warning "$@" \
  2>&1 | tee "$ROOT/logs/build.log"

BLEND="$ROOT/output/Meydenbauer_B101_Demolition_v4.blend"
"$BLENDER" --background "$BLEND" \
  --python "$ROOT/scripts/verify_saved_blend.py" -- \
  --fail-on-warning \
  2>&1 | tee "$ROOT/logs/verify_saved_blend.log"

echo
echo "Handoff verification complete."
echo "Blend:   $BLEND"
echo "Reports: $ROOT/output/build_validation_report.json"
echo "         $ROOT/output/saved_blend_verification.json"
