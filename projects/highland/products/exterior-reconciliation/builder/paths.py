"""Where the ported revision 06 builder reads its inputs and writes its outputs.

The historical builder lived in projects/highland-drawings/ and wrote to
deliverables/highland-drawings/. In the current layout every input is a
byte-identical recovered file (recovery.json and builder/inputs.json), the base
scene is a checksum-verified release asset, and outputs go to build/ (git-ignored).
"""
import json
import os
from pathlib import Path

from bmodels.paths import BUILD, ROOT

HERE = Path(__file__).resolve().parent
PRODUCT = HERE.parent
SNAPSHOTS = PRODUCT / 'snapshots'
INPUTS = HERE / 'inputs'
SOURCES = ROOT / 'projects/highland/sources'
OUT = Path(os.environ.get('BM_BUILD') or BUILD / 'highland/exterior-reconciliation')

SPEC = SNAPSHOTS / 'reconciled.spec.json'
DECISIONS = SNAPSHOTS / 'decisions.json'
BASE_SPEC = SNAPSHOTS / 'base-roof.spec.json'          # was projects/highland-roof/geometry-revision.spec.json
NORTH_BASELINE = SNAPSHOTS / 'revision04-north-baseline.json'
REVISION05_CONTROLS = SNAPSHOTS / 'revision05-controls.json'
STAGE1_BASELINE = SNAPSHOTS / 'stage1-r5-baseline.json'
LEDGER = INPUTS / 'change-ledger.json'                 # was deliverables/highland-drawings/change-ledger.json
OPENING_AUDIT = INPUTS / 'opening-audit.json'
EXTERIOR_MESH_FUNCTIONS = INPUTS / 'highland-exterior/build.py'   # parsed with ast; never executed whole
ASSETS = HERE / 'release-assets.json'

NATIVE = OUT / 'Highland-drawing-reconciled.blend'
GLB = OUT / 'Highland-drawing-reconciled.glb'


def base_blend():
    """Verified local copy of the revision 03 base scene (`bm assets pull builder/release-assets.json`)."""
    from bmodels.assets import Manifest
    manifest = Manifest(ASSETS)
    record = manifest.assets[0]
    path = manifest.local(record)
    if path is None:
        raise SystemExit(f"Base scene missing or wrong hash; run: uv run bm assets pull {ASSETS.relative_to(ROOT)}")
    return path


def sources():
    return json.loads(DECISIONS.read_text())['sources']
