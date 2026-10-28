"""Poly Haven CC0 textures and props for the Building B realism model.

Configures the shared Poly Haven pipeline (bmodels.polyhaven) with this
project's own list and lock file. Files download to build/assets/polyhaven and are checked
against the MD5s in assets/polyhaven.lock.json; nothing large is committed.

    python projects/meydenbauer-b/products/underslab/assets.py --lock   # re-resolve URLs and checksums
    python projects/meydenbauer-b/products/underslab/assets.py          # fetch and verify
"""
import sys
from pathlib import Path

from bmodels import polyhaven as ca

HERE = Path(__file__).resolve().parent

ca.LOCK = HERE / "assets/polyhaven.lock.json"
ca.TEXTURES = {"excavated_soil_wall": "2k", "gravel": "2k", "brushed_concrete": "2k", "concrete": "2k",
               "wood_floor": "2k", "white_plaster_02": "2k", "marble_01": "2k"}
ca.MODELS = {"rusted_spade_01": "1k", "sledgehammer_01": "1k", "plastic_crate_01": "1k", "cement_bag": "1k",
             "metal_toolbox": "1k", "plastic_broom": "1k", "dustpan": "1k", "trashbag": "1k",
             "cardboard_box_01": "1k"}
ca.PARTS = {}

lock, fetch, pbr, library, instance = ca.lock, ca.fetch, ca.pbr, ca.library, ca.instance

if __name__ == "__main__":
    if "--lock" in sys.argv:
        d = lock(); print(f'Locked {len(d["files"])} files, {d["total_mb"]} MB')
    d = fetch(); print(f'Fetched and verified {len(d["files"])} files into {ca.CACHE}')
