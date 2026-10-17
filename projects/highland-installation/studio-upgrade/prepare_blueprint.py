"""Render the same source crop at 400 dpi without altering CAD content."""
import hashlib
import json
from pathlib import Path
import fitz

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent
spec = json.loads((PROJECT/'installation/installation-data.json').read_text())
source = PROJECT/'Highland-original.pdf'
document = fitz.open(source)
page = document[14]
crop = spec['display']['source_crop_normalized']
rect = page.rect
clip = fitz.Rect(crop[0]*rect.width, crop[1]*rect.height, crop[2]*rect.width, crop[3]*rect.height)
target = ROOT/'assets/unit-b-plan-400dpi.png'
target.parent.mkdir(exist_ok=True)
pixmap = page.get_pixmap(matrix=fitz.Matrix(400/72,400/72),clip=clip,alpha=False)
pixmap.save(target)
metadata = {
    'source_pdf_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
    'sheet':'P4.01','pdf_page':15,'dpi':400,'crop_normalized':crop,
    'dimensions_px':[pixmap.width,pixmap.height],
    'vector_paths_on_source_page':len(page.get_drawings()),
    'processing':'Original PDF crop rendered at 400 dpi; no generative enhancement, no change to drawing content.'
}
(ROOT/'assets/blueprint-source.json').write_text(json.dumps(metadata,indent=2)+'\n')
print('BLUEPRINT_PASS',metadata)
