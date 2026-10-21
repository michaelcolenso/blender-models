"""Publish the bounded shell reconciliation with explicit remaining differences."""
import json
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak
from PIL import Image as PILImage

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'deliverables/highland-drawings'


def main():
    audit=json.loads((OUT/'opening-audit.json').read_text())
    validation=json.loads((OUT/'delivery-validation.json').read_text())
    shell=json.loads((OUT/'shell-reconciliation.json').read_text())
    north=json.loads((OUT/'elevation-comparison.json').read_text())
    styles=getSampleStyleSheet()
    styles.add(ParagraphStyle(name='SmallNote',fontName='Helvetica',fontSize=8.5,leading=11,textColor=colors.HexColor('#405461')))
    styles['BodyText'].fontSize=9.5;styles['BodyText'].leading=13
    styles['Title'].fontSize=22;styles['Title'].leading=26
    story=[]
    def p(text,style='BodyText'):
        story.append(Paragraph(text,styles[style]));story.append(Spacer(1,7))
    def img(name,maxw=520,maxh=280):
        path=OUT/name
        with PILImage.open(path) as im:w,h=im.size
        scale=min(maxw/w,maxh/h)
        return Image(str(path),width=w*scale,height=h*scale)
    def table(rows,widths):
        cells=[[Paragraph(escape(str(c)),styles['SmallNote']) for c in row] for row in rows]
        t=Table(cells,colWidths=widths,hAlign='LEFT',repeatRows=1)
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e6edf0')),('VALIGN',(0,0),(-1,-1),'TOP'),('BOTTOMPADDING',(0,0),(-1,-1),6),('TOPPADDING',(0,0),(-1,-1),5),('LINEBELOW',(0,0),(-1,0),.5,colors.HexColor('#bccbd2'))]))
        story.append(t);story.append(Spacer(1,9))
    def page(title):story.append(PageBreak());p(title,'Title')

    p('Highland / drawing reconciliation 05','Title')
    p('P1 enclosure and southeast R5 return provisionally reconciled. North dimensional differences remain open.','Heading2')
    p('A2.02 now governs a separate P1 polygon and all fourteen modeled P1 openings. OPEN-01 is restored; the recessed garage gate and adjacent service door follow their plan wall lines. OPEN-14 is restored with the southeast R5 corner, adjoining openings, slab, south roof plate and coping rebuilt together.')
    story.append(img('Highland-daylight-drawing-reconciled.png',520,295));story.append(Spacer(1,8))
    p('Native Cycles daylight image. Illustrative coordination study; complete components and context remain assumed. Not for construction, as-built certification or quantities.','SmallNote')
    table([['Inventory','Disposition'],['Original 16 candidates','15 provisionally located; 1 false R5 repeat rejected'],['Modeled openings','192, including the newly audited P1 service door'],['North R2-R5 comparison',f"{north['max_abs_horizontal_center_delta_px']:.3f} pixels maximum center difference; unchanged"],['Uploaded source set','3 original PDFs / 19 sheets, preserved with exact hashes']],[175,345])
    p('Printed drawing date: 04-02-07. Handwritten ASI/RFI references do not include complete response records. The revision 03 film remains a separate earlier delivery.','SmallNote')

    page('P1 / an independent enclosure')
    p('The previous lower story reused R1. The blue trace below follows A2.02; red shows the displaced R1 outline. The residential south steps, continuous parking perimeter and recessed east garage/service line are now distinct. All twelve inherited P1 opening records were rechecked; OPEN-01 and a service door were added.')
    story.append(Table([[img('source-review/P1-enclosure-reconciled.png',220,300),img('geometry-review/p1-plan.png',285,270)]],colWidths=[230,290]))
    p('Left: full plan trace. Right: saved native P1 only. Green source marks are measured jambs. Orange native components remain assumed.','SmallNote')
    story.append(img('source-review/P1-south-reconciled.png',520,135));story.append(Spacer(1,8))
    story.append(img('source-review/P1-south-elevation.png',520,78));story.append(Spacer(1,8))
    p('The south opening order is checked against A3.01. The east MA/MC/MI group, overhead gate and service door have separate plan picks and elevation evidence in source-review/. No opening is squeezed to the inherited return.','SmallNote')
    p('Limits: the open ventilation shaft, external planters/trellises and parking ramp are excluded from the enclosed slab model. P1 remains a flat, simplified shell; below-grade heights, structural slab design, sill/head dimensions and complete sections are assumed.','SmallNote')

    page('Southeast R5 / coupled return correction')
    p(f"The inner corner moves {abs(shell['r5_inner_corner_shift_in']):.3f} inches west under the independently calibrated A2.07 plan. OPEN-14 keeps its full measured jamb span. Adjacent east MA/MF openings and the final south MO/MU pair are re-registered to fit the revised wall, with no jamb clipping.")
    story.append(Table([[img('source-review/R5-SE-reconciled.png',250,250),img('source-review/R5-roof-comparison.png',250,250)]],colWidths=[260,260]))
    p('A2.07 plan (left) and independently registered A2.08 roof (right). Blue is the revised model centerline; green marks plan jambs. The R5 slab, south roof plate and four adjoining coping pieces follow the revised enclosure. The modeled coping top remains 406.25 ft; its section remains assumed.','SmallNote')
    story.append(img('geometry-review/r5-return.png',520,230));story.append(Spacer(1,8))
    residual=shell['retained_tiein_residuals_in'];roof=shell['roof_source_check']['model_minus_roof_pick_in']
    p(f"Remaining local differences are explicit: the inherited long east line differs from the A2.07 pick by {residual['long_east_line_vs_A2_07_1477px']:.3f} in; the south baseline by {residual['south_baseline_vs_A2_07_920px']:.3f} in. The independent roof step pick differs from the model by {roof[0]:.3f} in X and {roof[1]:.3f} in Y. These are diagnostic residuals, not tolerances or passes.",'SmallNote')
    p('The final south MO/MU internal split remains provisional. Other R5 steps, especially the southwest terrace/enclosure boundary, need a separate full-footprint audit. A4/A5 coping and guard profiles remain unavailable.','SmallNote')

    page('North / unchanged, explicit disagreement')
    p(f"R2-R5 retain six north openings per floor. All {validation['north_meshes_identical_to_revision04']} protected north meshes are identical to revision 04. The blue plan-model projection still differs from A3.02 by up to {north['max_abs_horizontal_center_delta_px']:.3f} pixels on the inherited 1815-pixel overview raster.")
    story.append(img('source-review/north-plan-model-overlay.png',520,270));story.append(Spacer(1,8))
    story.append(img('geometry-review/north.png',520,245));story.append(Spacer(1,8))
    p('The stair/MU pair remains the prominent conflict. Plan/elevation registration, raster picks and simplified wall depth all affect this diagnostic. Plan jambs continue to govern provisional locations. The lower R1 north door/entry pattern still needs audit.','SmallNote')
    p('elevation-comparison.json retains the source center, projected center and signed delta for each of the 24 R2-R5 openings. This is a spec projection, not an independent rendered-edge accuracy certificate. Native frame extents are checked separately against the spec.','SmallNote')

    page('Disposition of the original 16 candidates')
    p('Provisional placement confirms source presence and a modeled plan location. It does not close dimensional alignment, schedule, profile, sill/head, RFI or installed-condition questions.')
    rows=[['ID','Floor / face','Disposition','Model opening']]
    for c in audit['candidates']:
        rows.append([c['id'],c['level']+' / '+c['face'],'Provisional placement' if c['model_opening'] else 'False R5 repeat',c['model_opening'] or 'Not added'])
    table(rows,[58,88,157,217])
    p('OPEN-01 links to south-P1-02 on the separate P1 enclosure. OPEN-14 links to south-R5-09 on the revised southeast return. OPEN-16 remains rejected: the lower-floor MZ does not repeat on R5; two MK windows occur farther east.')
    p('The P1 service door is additional to this original candidate list. The model has 192 opening records. Use the cumulative change ledger and the separate shell-reconciliation record when tracing identities and geometry changes.','SmallNote')

    page('Verification and remaining work')
    table([['Check','Result'],['Saved native mesh inventory',f"{validation['architecture_meshes']} architectural meshes; {validation['unchanged_architecture_meshes']} protected meshes identical to revision 03"],['P1 opening audit','14 records; plan jambs retained without clipping'],['Corrected wall void overlaps','0'],['Slabs / coping','P1 and R5 perimeters, slab areas and levels read back; changed coping tops checked'],['Protected controls','R1/typical footprints, all six floor datums, dimensioned grids, roof plates/split, towers and terrace geometry'],['North continuation',f"{validation['north_meshes_identical_to_revision04']} mesh hashes identical to revision 04"],['Native scenes / saved dusk camera','Daylight + Dusk; all 432 frames checked'],['Packed images / portable GLB','No external image dependencies; every architectural mesh exported'],['Render-workflow regression tests','11 passed, no skips, using bpy 5.0.1']],[230,290])
    p('Opening frame extents and wall-normal locations are read back from the saved native file. Floating-point agreement with the spec verifies reproducibility, not accuracy of the drawing measurements. Source and native review evidence is recorded by exact file hash.','SmallNote')
    p('Continue with source reconciliation','Heading2')
    p('Keep north alignment differences open; audit R1 north entries and the remaining R5 local footprint steps. Review the retained southeast tie-in residuals and the MO/MU split. Confirm P1 ramp/structural details and below-grade sections before extending this exterior shell into a complete P1 model.')
    p('The supplied A2.08 confirms top-elevation callouts but lacks the referenced A4/A5 cornice, coping and exterior guard profiles. A6 stair guards do not establish terrace guards. Window schedules, complete ASI/RFI responses and field verification remain necessary before confirming dimensions or installed conditions.')
    p('Source files: site-and-floor-plans.pdf (A1.01, A2.01-A2.08); exterior-elevations-and-sections.pdf (A3.01, A3.02, A3.11-A3.13); stairs-and-rcp.pdf (A6.01-A6.04, A7.51). Exact hashes and page mapping are in source-inventory.json.','SmallNote')
    def footer(canvas,doc):
        canvas.setFont('Helvetica',8);canvas.setFillColor(colors.HexColor('#586e7b'))
        canvas.drawString(40,24,'200 W. Highland / illustrative source review / not for construction')
        canvas.drawRightString(572,24,str(doc.page))
    SimpleDocTemplate(str(OUT/'Highland-drawing-reconciliation.pdf'),pagesize=(612,792),rightMargin=46,leftMargin=46,topMargin=36,bottomMargin=42).build(story,onFirstPage=footer,onLaterPages=footer)
    (OUT/'README.md').write_text('''# Highland / drawing reconciliation 05

The separate A2.02 P1 enclosure and southeast R5 return are provisionally reconciled. OPEN-01 and OPEN-14 are now placed without clipping; all fourteen P1 openings were rechecked, including the recessed garage gate and newly audited service door. The model has 192 opening records: fifteen of the original sixteen candidates provisionally placed and one false R5 repeat rejected.

- [Source comparison and audit](Highland-drawing-reconciliation.pdf)
- [Editable Blender model](Highland-drawing-reconciled.blend)
- [Portable GLB](Highland-drawing-reconciled.glb)
- [Daylight image](Highland-daylight-drawing-reconciled.png)
- [Editable archive with PDFs and reproduction](Highland-drawing-editable.zip)
- [Continuation handoff](HANDOFF.md)

North dimensional alignment remains open, with the unchanged 42.443-pixel diagnostic maximum. R1 north entries, other R5 footprint steps, southeast tie-in residuals and the final south MO/MU split still need review. P1 ramp/structural details, sill/head dimensions, complete profiles and exterior guards remain assumed or provisional. This is not a verified as-built or construction model.

The native readback, source-bounded mesh allowlist, slab outlines, changed coping tops, no-overlap checks, complete GLB export and all 432 saved dusk camera frames pass. Eleven render-workflow tests pass without skips. See visual-review.json for exact inspected images/report pages and delivery-validation.json for machine checks. The older revision 03 film remains a separate delivery.

Full PDFs and reproduction inputs are included in the editable archive. shell-reconciliation.json records the P1/R5 continuation; change-ledger.json is cumulative from revision 03. elevation-comparison.json retains every north residual.
''')
    print('Wrote source comparison PDF and README.',flush=True)


if __name__=='__main__':main()
