#!/usr/bin/env bash
# Render the Unit 107 film, its preview GIF, the three viewer preview PNGs and video-validation.json
# into build/highland-water/.
# Run from the repo root after the build and viewer steps: bm run highland/water video
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
out="build/highland-water"
[ -f "$out/Highland-plumbing-3D.html" ] || { echo "missing $out/Highland-plumbing-3D.html: run the viewer step first" >&2; exit 1; }
(cd "$here" && npx playwright install chromium >/dev/null)

port="$(uv run --no-sync python -c 'import socket;s=socket.socket();s.bind(("127.0.0.1",0));print(s.getsockname()[1])')"
uv run --no-sync python -m http.server "$port" --bind 127.0.0.1 --directory "$out" >/dev/null 2>&1 &
server=$!
trap 'kill $server 2>/dev/null' EXIT
for _ in $(seq 50); do curl -sf "http://127.0.0.1:$port/" >/dev/null && break; sleep 0.1; done

NODE_PATH="$here/node_modules" node "$here/render_video.cjs" "http://127.0.0.1:$port/Highland-plumbing-3D.html" "$out"
NODE_PATH="$here/node_modules" node "$here/render_previews.cjs" "http://127.0.0.1:$port/Highland-plumbing-3D.html" "$out"

mp4="$out/Unit-107-plumbing-animation.mp4"
gif="$out/Unit-107-plumbing-preview.gif"
# Preview GIF: shot 1 (bathroom orbit, first 10 s) at 10 fps, 800 px wide.
ffmpeg -v error -y -t 10 -i "$mp4" \
  -vf "fps=10,scale=800:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=128[p];[b][p]paletteuse=dither=bayer:bayer_scale=4" \
  "$gif"

# Full decode check, then record decoded and GIF frame counts.
ffmpeg -v error -xerror -i "$mp4" -f null -
decoded="$(ffprobe -v error -count_frames -select_streams v:0 -show_entries stream=nb_read_frames -of csv=p=0 "$mp4")"
gif_frames="$(ffprobe -v error -count_frames -show_entries stream=nb_read_frames -of csv=p=0 "$gif")"
uv run --no-sync python - "$out/video-validation.json" "$decoded" "$gif_frames" <<'PY'
import json, sys
path, decoded, gif = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
v = json.load(open(path))
if decoded != v["frames"]:
    sys.exit(f"decoded {decoded} frames, captured {v['frames']}")
v.update(ffmpeg_full_decode="passed", decoded_frames=decoded, preview_gif_frames=gif)
json.dump(v, open(path, "w"), indent=2)
print(f"video ok: {decoded} frames decoded, preview GIF {gif} frames")
PY
