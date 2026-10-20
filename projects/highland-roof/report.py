"""Produce a fresh source comparison for the changed geometry and finished film."""
import io
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'deliverables/highland-roof'
SOURCE=ROOT/'projects/highland-exterior/source-review'


def main():
    cfg=json.loads((ROOT/'projects/highland-roof/geometry.json').read_text())
    fit=json.loads((OUT/'camera-fit.json').read_text())
    geo=json.loads((OUT/'geometry-validation.json').read_text())
    measure=json.loads((OUT/'source-measurements.json').read_text())
    photo=Image.open(ROOT/fit['source_photo']).convert('RGB').resize((1330,882))
    draw=ImageDraw.Draw(photo)
    for i,p in enumerate(fit['landmarks']):
        a=tuple(v*2 for v in p['pixel']);b=tuple(v*2 for v in p['projected_pixel'])
        draw.ellipse((a[0]-6,a[1]-6,a[0]+6,a[1]+6),outline='#ffd45a',width=3)
        draw.line((b[0]-6,b[1],b[0]+6,b[1]),fill='#00eaff',width=3)
        draw.line((b[0],b[1]-6,b[0],b[1]+6),fill='#00eaff',width=3)
        draw.text((a[0]+8,a[1]),str(i+1),font=ImageFont.load_default(size=18),fill='white',stroke_width=2,stroke_fill='#173544')
    photo.save(OUT/'Highland-revised-camera-landmarks.png')
    Image.open(OUT/'Highland-source-height-picks.png').crop((0,410,Image.open(OUT/'Highland-source-height-picks.png').width,1150)).save(OUT/'Highland-source-height-detail.png')
    w,h=landscape(A4);navy=HexColor('#173544');gray=HexColor('#485c68')
    c=canvas.Canvas(str(OUT/'Highland-roof-terrace-source-comparison.pdf'),pagesize=(w,h))
    c.setTitle('200 West Highland / revision 03 source and geometry review')
    style=ParagraphStyle('body',fontName='Helvetica',fontSize=10,leading=14,textColor=gray)
    def header(subtitle,num):
        c.setFillColor(navy);c.setFont('Helvetica',23);c.drawString(34,h-43,'200 WEST HIGHLAND')
        c.setFillColor(gray);c.setFont('Helvetica',12);c.drawString(34,h-66,subtitle)
        c.setStrokeColor(HexColor('#dce4e8'));c.line(34,h-80,w-34,h-80)
        c.setFont('Helvetica',8);c.drawString(34,19,'Illustrative exterior study / 20 October 2026 / provisional and assumed geometry remains.')
        c.drawRightString(w-34,19,str(num))
    def picture(path,x,y,width,height):
        with Image.open(path) as im:
            im=im.convert('RGB');iw,ih=im.size;im.thumbnail((2200,1600));b=io.BytesIO();im.save(b,format='JPEG',quality=94);b.seek(0)
        s=min(width/iw,height/ih);c.setFillColor(HexColor('#eef2f4'));c.rect(x,y,width,height,fill=1,stroke=0)
        c.drawImage(ImageReader(b),x+(width-iw*s)/2,y+(height-ih*s)/2,width=iw*s,height=ih*s)
    def text(body,x,y,width):
        p=Paragraph(body,style);_,ph=p.wrap(width,h);p.drawOn(c,x,y-ph)
    def label(body,x,y):
        c.setFillColor(navy);c.setFont('Helvetica-Bold',10);c.drawString(x,y,body)
    panel=(w-84)/2
    header('Photo reference and corrected native daylight study',1)
    picture(SOURCE/'user-photo-02.jpg',34,235,panel,252)
    picture(OUT/'Highland-daylight-geometry-revised.png',50+panel,235,panel,252)
    label('Owner-supplied photo-02',34,216);label('Revision 03 / Cycles daylight',50+panel,216)
    text('<b>Geometry correction.</b> Added the missing central brick parapet and pale southwest/southeast terrace cornices. Corrected coping tops and two wall headers at the inherited roof-level split. Mirrored the eight MN window dividers to follow the elevation pattern.',34,193,panel)
    text('<b>Source limits.</b> Terrace heights and pane ratios are provisional interpretations. Complete sections, returns, guard layout, finish properties and site remain assumed. The original architectural PDF and opening schedule are absent.',50+panel,193,panel)
    text(f'<b>Scope held.</b> Registered plan polygons, six floor elevations and grid spans remain unchanged. {geo["unchanged_meshes"]} architectural meshes are identical to revision 02. All 175 opening records, extents, glass panels and sills are retained; all 16 conflicts remain unresolved. This comparison does not establish surveyed accuracy.',34,99,w-68)
    c.showPage()

    header('Recorded source picks / provisional terrace heights and pane proportions',2)
    picture(OUT/'Highland-source-height-detail.png',34,310,w-68,185)
    text(f'<b>Vertical registration.</b> R5 at y=591 / z=627 in and R4 at y=853 / z=501 in establish {measure["pixels_per_inch"]:.4f} pixels/in. The R3 check is {measure["holdout_residual_px"]:.2f} px from prediction. This is a local scan check; it is not an independent dimensional tolerance.',34,289,w-68)
    picture(OUT/'Highland-MN-window-source.png',34,109,panel,125)
    text('<b>Modeled heights above R5.</b> Central brick: 28 in; southwest cornice: 26 in; southeast corner: 30 in. Manual source-pick allowance: about +/-3 in. Coping profiles and return extents remain assumed.',50+panel,230,panel)
    text('<b>Mirrored MN windows.</b> Internal bars are placed at about 65% and 35% of opening width from west to east, repeated on R1-R4. Ratios are provisional, about +/-0.03. Only each internal vertical bar moves; perimeter frames and horizontal rails stay fixed.',50+panel,142,panel)
    text('<b>Roof top controls.</b> Complete south/north parapet tops: 406.25 / 407.75 ft. Elevator/stair: 415.00 / 414.41 ft. These documented datums do not confirm complete coping or tower sections.',34,70,w-68)
    c.showPage()

    header('South elevation / fixed-camera geometry comparison',3)
    picture(SOURCE/'south.png',34,337,w-68,157)
    picture(OUT/'geometry-review/before-south.png',34,105,panel,212)
    picture(OUT/'geometry-review/after-south.png',50+panel,105,panel,212)
    label('Revision 02 / original orthographic camera',34,88);label('Revision 03 / identical orthographic camera',50+panel,88)
    text('The source panel is fitted independently for qualitative comparison. The before/after model panels share the same orthographic scale and camera. Orange denotes complete components with assumed geometry. Roof/terrace changes follow the recorded datum and scan picks; no edge-agreement or as-built claim is made.',34,67,w-68)
    c.showPage()

    header('Fresh provenance review / corrected architectural geometry',4)
    for i,(view,title) in enumerate([('south','South'),('east','East'),('plan','Plan'),('iso','Isometric')]):
        x=34+(i%2)*(panel+16);y=294 if i<2 else 90
        picture(OUT/f'geometry-review/after-{view}.png',x,y,panel,190 if i<2 else 176);label(title,x,y-14)
    text('Orange: complete components remain assumed. Confirmed top datums and provisional heights/ratios are separate element properties. Detail records and all source/basis tags are included in element-provenance.csv and the editable Blender/GLB files.',34,62,w-68)
    c.showPage()

    header('Continuous dusk move / camera fit and remaining limits',5)
    style.fontSize=9
    style.leading=12
    for i,f in enumerate([0,72,144,216,288,360,431]):
        col=i%4;row=i//4;width=(w-92)/4;x=34+col*(width+8);y=363-row*124
        picture(OUT/f'film-review/frame-{f:03}.png',x,y,width,105)
        label(f'{f/24:.1f} s',x,y-14)
    text('<b>Movie.</b> 18 seconds, 1920 x 1080, 24 fps. Uses the 432-frame native Blender camera path with Three.js PBR materials, approximate lighting/context and documented foliage simplification. Architecture is not decimated. Four-sample MSAA on rails/window frames plus full-frame FXAA improves thin edges; Cycles is the native still material reference.',34,210,panel)
    text(f'<b>Refitted daylight camera.</b> Nine selected manual points; {fit["lens_mm"]:.2f} mm lens. Residual RMS {fit["landmark_rmse_px"]:.2f} px versus {fit["same_geometry_previous_camera_rmse_px"]:.2f} px for the previous camera on the same revised geometry, at 665 x 441 pixels. These are fitting residuals, not independent accuracy.',50+panel,210,panel)
    text('<b>Unresolved source decisions.</b> Eight south and eight north opening candidates remain in the inherited ledger. No opening was added to meet a count. Retained evidence is in opening-audit.json/csv. Original A2.03/A2.04/A2.07 and A3.01/A3.02 sheets, an opening schedule and clearer north/return photographs are needed for the next reconciliation.',34,120,w-68)
    text('<b>Rendering limits.</b> The film approximates glass, area lights and background geometry; reflective/material agreement with native Cycles is not exact. Fine rails may still shimmer. Landscape, neighborhood heights and facade details remain illustrative.',34,72,w-68)
    c.save()
    print(OUT/'Highland-roof-terrace-source-comparison.pdf')


if __name__=='__main__':
    main()
