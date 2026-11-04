from pathlib import Path

import pymupdf
from PIL import Image

HERE = Path(__file__).parent
ROOT = HERE.parents[3]
SOURCE = ROOT / "projects/highland/sources/200 W. Highland Construction Plans - Complete.pdf"
BUILD = ROOT / "build/highland-water/p1-source"
REVIEW = HERE / "source-review"
SHEETS = {"A2.02": 46, "P2.2": 183}

BUILD.mkdir(parents=True, exist_ok=True)
REVIEW.mkdir(exist_ok=True)
doc = pymupdf.open(SOURCE)
for sheet, page_number in SHEETS.items():
    pix = doc[page_number - 1].get_pixmap(matrix=pymupdf.Matrix(2, 2), colorspace=pymupdf.csRGB)
    image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    image.save(BUILD / f"{sheet}.png")
    image.thumbnail((1800, 1800))
    image.save(REVIEW / f"p1-{sheet}.jpg", quality=90)
    print(f"{sheet}: PDF page {page_number}; {pix.width} x {pix.height} working pixels")
