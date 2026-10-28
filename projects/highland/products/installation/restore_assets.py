"""Restore large project inputs from the checksum-verified release assets.

Kept for old instructions; same as `uv run bm assets pull projects/highland/products/installation/release-assets.json`.
The archive members and destinations now live in release-assets.json.
"""
import sys
from pathlib import Path

from bmodels import assets

if __name__ == '__main__':
    assets.pull(Path(__file__).resolve().parent / 'release-assets.json', extra_dirs=sys.argv[1:])
