"""Poly Haven CC0 textures and models for the Highland cinematic film.

Configures the shared bmodels.polyhaven pipeline with this film's list and lock file
(assets/polyhaven-cinema.lock.json). Files download to build/assets/polyhaven and are checked
against the locked MD5s; nothing large is committed.

    uv run python projects/highland/products/walkthrough/cinema_assets.py --lock   # re-resolve URLs and checksums
    uv run python projects/highland/products/walkthrough/cinema_assets.py          # fetch and verify
"""
import sys
from pathlib import Path

from bmodels import polyhaven as ph
from bmodels.polyhaven import *  # noqa: F403  (cinema.py uses this module as the asset API)

HERE = Path(__file__).resolve().parent
ph.LOCK = LOCK = HERE/'assets/polyhaven-cinema.lock.json'
# id: resolution. Walnut is 4K for the 50 mm slat insert in the 4K master.
ph.TEXTURES = TEXTURES = {'american_walnut_veneer': '4k', 'brick_wall_001': '2k', 'clean_asphalt': '2k',
                          'concrete_pavement': '2k', 'marble_01': '2k', 'white_plaster_02': '2k'}
ph.MODELS = MODELS = {'tree_small_02': '1k', 'potted_plant_01': '1k', 'mid_century_lounge_chair': '1k',
                      'side_table_01': '1k', 'street_lamp_01': '1k', 'fire_hydrant': '1k'}
# Some model files hold variants side by side; keep one complete object set.
ph.PARTS = PARTS = {'tree_small_02': lambda name: name == 'tree_small_02_LOD0',
                    'fire_hydrant': lambda name: '_aged' not in name}

if __name__ == '__main__':
    if '--lock' in sys.argv:
        d = ph.lock(); print(f'Locked {len(d["files"])} files, {d["total_mb"]} MB')
    d = ph.fetch(); print(f'Fetched and verified {len(d["files"])} files into {ph.CACHE}')
