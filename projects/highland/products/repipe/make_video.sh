#!/usr/bin/env bash
# Render the repipe film, its preview GIF, the cutover still and validation.json into build/highland-repipe/.
# Run from the repo root after the package step: bm run highland/repipe video
# Uses the Node dependencies pinned in ../water/package.json (three, esbuild, playwright).
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
mods="$here/../water/node_modules"
out="build/highland-repipe"
[ -f "$out/Highland-repipe-sequence.html" ] || { echo "missing $out/Highland-repipe-sequence.html: run the package step first" >&2; exit 1; }
(cd "$here/../water" && npx playwright install chromium >/dev/null)

port="$(uv run --no-sync python -c 'import socket;s=socket.socket();s.bind(("127.0.0.1",0));print(s.getsockname()[1])')"
uv run --no-sync python -m http.server "$port" --bind 127.0.0.1 --directory "$out" >/dev/null 2>&1 &
server=$!
trap 'kill $server 2>/dev/null' EXIT
for _ in $(seq 50); do curl -sf "http://127.0.0.1:$port/" >/dev/null && break; sleep 0.1; done

NODE_PATH="$mods" node "$here/render.cjs" "http://127.0.0.1:$port/Highland-repipe-sequence.html" "$out"

mp4="$out/Highland-repipe-strategy.mp4"
# Preview GIF: the full 32 s at 6 fps, 800 px wide. Cutover still: the phase-5 review capture.
ffmpeg -v error -y -i "$mp4" \
  -vf "fps=6,scale=800:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=128[p];[b][p]paletteuse=dither=bayer:bayer_scale=4" \
  "$out/Highland-repipe-preview.gif"
cp "$out/phase-5.png" "$out/Cutover-preview.png"

ffmpeg -v error -xerror -i "$mp4" -f null -
decoded="$(ffprobe -v error -count_frames -select_streams v:0 -show_entries stream=nb_read_frames -of csv=p=0 "$mp4")"
uv run --no-sync python - "$out/validation.json" "$decoded" <<'PY'
import json, sys
path, decoded = sys.argv[1], int(sys.argv[2])
v = json.load(open(path))
if decoded != v["frames"]:
    sys.exit(f"decoded {decoded} frames, captured {v['frames']}")
v.update(ffmpeg_full_decode="passed", decoded_frames=decoded)
json.dump(v, open(path, "w"), indent=2)
print(f"video ok: {decoded} frames decoded")
PY
