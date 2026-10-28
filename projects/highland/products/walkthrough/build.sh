#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../../../.."
for tool in python3 npm node chromium ffmpeg ffprobe; do
    command -v "$tool" >/dev/null || { echo "Missing required tool: $tool" >&2; exit 1; }
done
python3 -c 'import numpy, PIL' || { echo 'Install numpy and Pillow before building.' >&2; exit 1; }
python3 projects/highland/products/walkthrough/prepare.py
if [ ! -d projects/highland/products/walkthrough/node_modules ]; then
    mkdir -p build/npm-cache
    npm --cache "$PWD/build/npm-cache" --prefix projects/highland/products/walkthrough ci --no-audit --no-fund
fi
npm --prefix projects/highland/products/walkthrough run bundle
python3 projects/highland/products/walkthrough/package.py
node projects/highland/products/walkthrough/render.cjs --review-only
node projects/highland/products/walkthrough/render.cjs
python3 projects/highland/products/walkthrough/audio.py
python3 projects/highland/products/walkthrough/finish.py
echo 'Finished: projects/highland/deliverables/drone/Highland-corridor-drone.mp4'
