#!/usr/bin/env bash
# Publish the seven archived Meydenbauer scenes (443 MB) to the release in release-assets.json.
# Run from a clone with `gh` logged in; cloud sessions cannot write releases.
#   bash projects/meydenbauer-b/products/vdc-recovery/publish_scenes.sh
# Each scene is extracted from its archive blob and checked against the manifest's sha256 before upload.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
manifest="$here/release-assets.json"
tag="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["tag"])' "$manifest")"
work="$(mktemp -d)"; trap 'rm -rf "$work"' EXIT

git fetch -q origin tag archive/2026-11-03/meydenbauer/4d-fixes tag archive/2026-11-03/meydenbauer/b101-v4-executed
python3 - "$manifest" "$work" <<'EOF'
import hashlib, json, subprocess, sys
manifest, work = sys.argv[1:]
for a in json.load(open(manifest))["assets"]:
    data = subprocess.run(["git", "cat-file", "blob", a["git_blob_sha"]], check=True, capture_output=True).stdout
    assert hashlib.sha256(data).hexdigest() == a["sha256"] and len(data) == a["bytes"], a["name"]
    open(f"{work}/{a['name']}", "wb").write(data)
    print("verified", a["name"])
EOF
gh release view "$tag" >/dev/null 2>&1 || gh release create "$tag" --title "$tag" \
  --notes "Archived Meydenbauer VDC 4D scenes and B101 demolition v4 scene, byte-identical to archive/2026-11-03 tags. Historical review copies; illustrative, not a contract document."
gh release upload "$tag" "$work"/*.blend
echo "uploaded; verify with: uv run bm assets verify $manifest  (after: uv run bm assets pull $manifest)"
