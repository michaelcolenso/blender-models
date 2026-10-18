#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
for tool in python3 npm node chromium ffmpeg ffprobe; do
    command -v "$tool" >/dev/null || { echo "Missing required tool: $tool" >&2; exit 1; }
done
python3 -c 'import numpy, PIL' || { echo 'Install numpy and Pillow before building.' >&2; exit 1; }
python3 projects/highland-drone/prepare.py
if [ ! -d projects/highland-drone/node_modules ]; then
    mkdir -p build/npm-cache
    npm --cache "$PWD/build/npm-cache" --prefix projects/highland-drone ci --no-audit --no-fund
fi
npm --prefix projects/highland-drone run bundle
python3 projects/highland-drone/package.py
node projects/highland-drone/render.cjs --review-only
node projects/highland-drone/render.cjs
python3 projects/highland-drone/audio.py
python3 projects/highland-drone/finish.py
echo 'Finished: deliverables/highland-drone/Highland-corridor-drone.mp4'
