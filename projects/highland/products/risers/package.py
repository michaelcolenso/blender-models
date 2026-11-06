"""Copy the review renders into the deliverable folder as JPEGs (each well under 1 MB)."""
import os
import shutil
from pathlib import Path

from PIL import Image

from bmodels.paths import BUILD, PROJECTS

SRC = Path(os.environ.get("BM_BUILD") or BUILD / "highland" / "risers")
DST = Path(os.environ.get("BM_DELIVERABLES") or PROJECTS / "highland" / "deliverables" / "risers")
DST.mkdir(parents=True, exist_ok=True)
for spec in ("existing", "proposed"):
    for view in ("iso", "plan", "south", "east"):
        im = Image.open(SRC / f"{spec}-{view}.png").convert("RGB")
        im.thumbnail((1400, 1400))
        im.save(DST / f"{spec}-{view}.jpg", quality=82, optimize=True)
    shutil.copy(SRC / f"{spec}-report.md", DST / f"{spec}-report.md")
photo = SRC / "photoreal"
if photo.exists():
    for f in sorted(photo.glob("*.png")):
        im = Image.open(f).convert("RGB"); im.thumbnail((1600, 1600))
        im.save(DST / (f.stem + ".jpg"), quality=85, optimize=True)
print("packaged", sorted(p.name for p in DST.iterdir()))
