"""Package source comparisons, the camera residuals and all opening decisions."""
import io
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, Table, TableStyle

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "deliverables/highland-daylight"
SOURCE = ROOT / "projects/highland-exterior/source-review"
OLD = ROOT / "deliverables/highland-refined"


def main():
    fit = json.loads((OUT / "camera-fit.json").read_text())
    audit = json.loads((OUT / "opening-audit.json").read_text())
    overlay = Image.open(ROOT/fit["source_photo"]).convert("RGB").resize((1330, 882))
    draw = ImageDraw.Draw(overlay)
    font = ImageFont.load_default(size=17)
    for i, point in enumerate(fit["landmarks"]):
        p = tuple(2*v for v in point["pixel"])
        q = tuple(2*v for v in point["projected_pixel"])
        draw.line((p, q), fill="#ffffff", width=2)
        draw.ellipse((p[0]-5, p[1]-5, p[0]+5, p[1]+5), outline="#ffd45a", width=3)
        draw.line((q[0]-5, q[1], q[0]+5, q[1]), fill="#22eaff", width=3)
        draw.line((q[0], q[1]-5, q[0], q[1]+5), fill="#22eaff", width=3)
        draw.text((p[0]+7, p[1]-19), str(i+1), font=font, fill="white", stroke_width=2, stroke_fill="#172a35")
    overlay.save(OUT / "Highland-camera-landmarks.png")
    w, h = landscape(A4)
    c = canvas.Canvas(str(OUT / "Highland-daylight-source-comparison.pdf"), pagesize=(w, h))
    c.setTitle("200 West Highland / daylight revision 02 and source review")
    navy = HexColor("#173544")
    gray = HexColor("#485c68")
    style = ParagraphStyle("body", fontName="Helvetica", fontSize=10, leading=14, textColor=gray)
    panel = (w-84)/2

    def header(subtitle, number):
        c.setFillColor(navy)
        c.setFont("Helvetica", 23)
        c.drawString(34, h-43, "200 WEST HIGHLAND")
        c.setFillColor(gray)
        c.setFont("Helvetica", 12)
        c.drawString(34, h-66, subtitle)
        c.setStrokeColor(HexColor("#dce4e8"))
        c.line(34, h-80, w-34, h-80)
        c.setFont("Helvetica", 8)
        c.drawString(34, 19, "Illustrative exterior study / 20 October 2026 / geometry and source limitations remain.")
        c.drawRightString(w-34, 19, str(number))

    def picture(path, x, y, width, height):
        with Image.open(path) as im:
            im = im.convert("RGB")
            iw, ih = im.size
            im.thumbnail((2200, 1600))
            resource = io.BytesIO()
            im.save(resource, format="JPEG", quality=94)
            resource.seek(0)
        scale = min(width/iw, height/ih)
        c.setFillColor(HexColor("#eef2f4"))
        c.rect(x, y, width, height, fill=1, stroke=0)
        c.drawImage(ImageReader(resource), x+(width-iw*scale)/2, y+(height-ih*scale)/2,
                    width=iw*scale, height=ih*scale, mask="auto")

    def text(body, x, y, width):
        p = Paragraph(body, style)
        _, height = p.wrap(width, h)
        p.drawOn(c, x, y-height)

    def label(body, x, y):
        c.setFillColor(navy)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(x, y, body)

    header("Photo reference and revised Cycles daylight study", 1)
    picture(SOURCE/"user-photo-02.jpg", 34, 235, panel, 252)
    picture(OUT/"Highland-daylight-photo-study.png", 50+panel, 235, panel, 252)
    label("Owner-supplied photo-02", 34, 216)
    label("Daylight revision 02 / native Cycles", 50+panel, 216)
    text("<b>Camera first.</b> A reproducible pinhole fit uses nine manually selected facade and floor correspondences. The viewpoint is closer to the source, with less foreground lawn and a stronger corner perspective.", 34, 193, panel)
    text("<b>Presentation revision.</b> Warmer, less mottled brick; a clear procedural daylight sky; reflective glazing with varied open curtains; pale concrete trim; and layered planted terrace edges.", 50+panel, 193, panel)
    text("<b>What the comparison establishes.</b> Visual agreement at selected interpreted landmarks has improved. The roof silhouette, openings and site still differ from the photograph. All 955 protected architectural meshes retain the handoff geometry. The model still has 175 openings and 16 unresolved candidates. No surveyed accuracy or color calibration is claimed.", 34, 103, w-68)
    c.showPage()

    header("Selected camera landmarks and recorded residuals", 2)
    picture(OUT/"Highland-camera-landmarks.png", 34, 166, 500, 330)
    label("Yellow circles: manual photo picks / cyan crosses: projected model", 34, 148)
    text(f"<b>Fit method.</b> Robust least squares, centered principal point, square pixels, 36 mm horizontal sensor and no lens distortion. Fitted lens: {fit['lens_mm']:.2f} mm.", 554, 478, w-588)
    text(f"<b>Selected-point error.</b> Root-mean-square residual: {fit['landmark_rmse_px']:.2f} px, compared with {fit['previous_camera_rmse_px']:.2f} px for the previous camera, at the supplied 665 x 441 image size. Largest residual: {fit['maximum_landmark_error_px']:.2f} px.", 554, 365, w-588)
    text("<b>Limits.</b> These are fitting residuals on the same manual points used to fit the camera. They are not independent accuracy measurements. Unknown cropping, lens distortion and simplified geometry remain. Manual pick uncertainties are 4-10 pixels.", 554, 230, w-588)
    text("The numbered correspondences, their 3D positions, manual pixel picks, bounds and individual errors are saved in <b>camera-fit.json</b>. Blender's native camera projections are checked against the optimizer. No source element is promoted to confirmed status by the fit.", 34, 103, w-68)
    c.showPage()

    header("Source elevation patterns / retained architectural geometry", 3)
    for i, (face, sheet) in enumerate((("south", "A3.01 south elevation"), ("east", "A3.01 east elevation"))):
        y = h-290-i*222+(14 if i else 0)
        height = 160 if i else 174
        picture(SOURCE/(face+".png"), 34, y, panel, height)
        picture(OLD/"source-review"/(face+".png"), 50+panel, y, panel, height)
        label(sheet, 34, y-17)
        label("Handoff orthographic / geometry retained", 50+panel, y-17)
    text("These are independently fitted qualitative panels, not measured overlays. The orthographic images are retained from the handoff because the architectural mesh hash is unchanged. The original architectural PDF is absent; original plan/elevation sheets and clearer return photographs are needed to resolve the remaining conflicts.", 34, 67, w-68)
    c.showPage()

    header("All 16 opening conflicts reviewed / no unsupported additions", 4)
    rows = [["Record", "Face", "Level", "Center (in)", "Width (in)", "Recomputed conflict"]]
    for item in audit["candidates"]:
        reason = "Outside outward-facing plan spans" if not item["outward_facing_matches"] else "Does not fit return with jamb margin"
        rows.append([item["id"], item["face"], item["level"], f"{item['projected_center_in']:.1f}", f"{item['projected_width_in']:.1f}", reason])
    table = Table(rows, colWidths=[55, 47, 40, 78, 78, w-466], rowHeights=21)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), navy), ("TEXTCOLOR", (0, 0), (-1, 0), HexColor("#ffffff")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [HexColor("#eef3f5"), HexColor("#ffffff")]),
        ("LINEBELOW", (0, 0), (-1, -1), .3, HexColor("#d3dfe4"))]))
    table.wrapOn(c, w-68, h)
    table.drawOn(c, 34, h-100-len(rows)*21)
    text("<b>Decision.</b> Retain every candidate as unresolved. Pixel registration and outward-facing plan returns cannot establish revised jamb locations from these crops. The inherited six-inch jamb allowance is an assumption, not a documented minimum. Centers and widths above are projected scan coordinates, not verified installed dimensions.", 34, 114, w-68)
    text("<b>Next source request.</b> Original A2.03/A2.04/A2.07 and A3.01/A3.02 sheets, an opening schedule, and clearer north/return photographs. Detailed evidence is in opening-audit.json and opening-audit.csv.", 34, 59, w-68)
    c.save()
    print(OUT / "Highland-daylight-source-comparison.pdf")


if __name__ == "__main__":
    main()
