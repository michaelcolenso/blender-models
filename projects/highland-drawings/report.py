"""Build the source-backed five-page review and concise delivery notes."""
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
    calibration=json.loads((OUT/'plan-registration.json').read_text())
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
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e6edf0')),('VALIGN',(0,0),(-1,-1),'TOP'),('BOTTOMPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),6),('LINEBELOW',(0,0),(-1,0),.5,colors.HexColor('#bccbd2'))]))
        story.append(t);story.append(Spacer(1,10))
    p('Highland / drawing reconciliation 04','Title')
    p('13 candidates placed provisionally; 1 false repeat rejected; 2 footprint conflicts remain. The editable model now contains 189 opening records.','Heading2')
    p('The three uploaded PDFs supply 19 sheets: site/floor/roof plans, exterior elevations/building sections, stair/core sheets and a lobby RCP. Printed date: 04-02-07. Handwritten ASI/RFI references do not include complete response records.')
    story.append(img('Highland-daylight-drawing-reconciled.png',520,280));story.append(Spacer(1,9))
    p('Native Cycles daylight image. This is an illustrative exterior study; measured jamb positions are provisional, complete components and context remain assumed. Not for construction or quantities.','SmallNote')
    table([['Source PDF','Sheets'],['Site and floor plans','A1.01, A2.01-A2.08'],['Stairs and RCP','A6.01-A6.04, A7.51'],['Exterior elevations and sections','A3.01, A3.02, A3.11-A3.13']],[205,315])
    p('Complete PDFs are included in the editable archive. Exact file hashes and page mapping: source-inventory.json. The prior revision 03 movie is a separate earlier output.','SmallNote')

    story.append(PageBreak());p('Disposition of the 16 candidates','Title')
    p('Accepted means visible in the elevation and placed provisionally using the plan. It does not confirm a scheduled size, installed location, sill/head or complete frame section.')
    rows=[['ID','Floor / face','Disposition','Model opening']]
    for c in audit['candidates']:
        decision='Provisional placement' if c['decision'].startswith('accepted') else 'False R5 repeat' if c['decision'].startswith('rejected') else 'Footprint conflict'
        rows.append([c['id'],c['level']+' / '+c['face'],decision,c['model_opening'] or 'Not added'])
    table(rows,[58,88,157,217])
    p('OPEN-01 / P1: A2.02 shows a different stepped residential enclosure from the inherited R1-based lower shell. Reconcile the complete P1 polygon and related openings together.')
    p('OPEN-14 / southeast R5: the plan jamb crosses the inherited return. Reconcile the local step, east elevation, slab and roof/coping above; clipping the window would conceal the conflict.')
    p('OPEN-16 / R5 north: no window appears at the repeated lower-floor MZ position. The actual R5 row has two MK windows farther east.','SmallNote')

    story.append(PageBreak());p('North rows / explicit residual differences','Title')
    p('R2-R5 now contain six north openings per floor. Blue outlines below project the plan-governed model specification onto A3.02. The maximum horizontal center difference is 42.443 pixels on the inherited 1815-pixel overview raster. This is a diagnostic comparison, not an accuracy pass.')
    story.append(img('source-review/north-plan-model-overlay.png',520,270));story.append(Spacer(1,8))
    story.append(img('geometry-review/north.png',520,255));story.append(Spacer(1,8))
    p('The stair/MU pair still disagrees with the elevation projection. Simplified wall depth, plan/elevation registration and raster picks all affect this comparison. Keep the plan placements provisional pending detail/RFI/field reconciliation. The lower R1 north door/entry pattern remains outside this patch. Orange denotes assumed complete components.','SmallNote')

    story.append(PageBreak());p('South returns and retained footprint conflicts','Title')
    p('R1-R4 column 02 is restored on its stepped return. Existing columns 03/04 move to the next two returns, and the unsupported column-03 recess/guard is removed. The restored openings no longer overlap inherited misplaced openings. Two R5 return windows are also added.')
    story.append(img('geometry-review/south.png',520,225));story.append(Spacer(1,10))
    p('The two remaining footprint conflicts have direct source evidence:','Heading2')
    t=Table([[img('source-review/P1-unresolved.png',250,155),img('source-review/R5-SE-unresolved.png',250,155)]],colWidths=[260,260]);story.append(t)
    table([['OPEN-01 / P1','OPEN-14 / southeast R5'],['A2.02 / trace the lower enclosure before adding its residential door.','A2.07 / reconcile the short return and the facade/roof geometry it supports.']],[260,260])
    p('Annotated plan jamb picks for all corrected floors are included under source-review/. Exact opening changes and retained IDs are recorded in change-ledger.json.','SmallNote')

    story.append(PageBreak());p('Verification and continuation','Title')
    p('The saved native file passes the local geometry and portability checks. Four native provenance views and the source picks were inspected. The separate visual-review record binds the final images and report to exact hashes.')
    table([['Check','Result'],['Opening records / remaining footprint conflicts','189 / 2'],['Architecture meshes / identical to revision 03',f"{validation['architecture_meshes']} / {validation['unchanged_architecture_meshes']}"],['Corrected wall void overlaps','0'],['Footprint, six floor/grid controls and roof/terrace geometry','Unchanged'],['Native scenes / saved dusk camera','Daylight + Dusk / 432 frames checked'],['Packed images / GLB architecture','No external dependencies / all architecture exported'],['Existing render-workflow regression tests','11 passed locally']],[275,245])
    p('Each plan sheet was calibrated independently from its 16 ft 3 in, 27 ft 9 in, 27 ft 9 in and 31 ft 3 in grid spans. Source picks are provisional; floating-point readback precision is not drawing accuracy.','SmallNote')
    table([['Floor','Own grid picks (0.6 raster)'],*[[level,', '.join(f'{v:.3f}' for v in c['grid_x_pixels'])] for level,c in calibration.items()]],[60,460])
    p('Terrace and guard limits','Heading2')
    p('Terrace-band heights remain provisional. The supplied A2.08 confirms the inherited top-elevation callouts but does not provide the referenced A4/A5 cornice, coping or exterior guard sections. A6 stair guards do not establish terrace guards. Finish products, context and landscape remain assumed.')
    p('Next work: reconcile the P1 enclosure and southeast R5 step from the now-available plans; audit R1 north entries; investigate the north projection differences. The window schedule, A4/A5 details, complete RFI responses and field verification are needed before dimensions or profiles can be confirmed.')
    def footer(canvas,doc):
        canvas.setFont('Helvetica',8);canvas.setFillColor(colors.HexColor('#586e7b'))
        canvas.drawString(40,24,'200 W. Highland / illustrative source review / not for construction')
        canvas.drawRightString(572,24,str(doc.page))
    SimpleDocTemplate(str(OUT/'Highland-drawing-reconciliation.pdf'),pagesize=(612,792),rightMargin=46,leftMargin=46,topMargin=36,bottomMargin=42).build(story,onFirstPage=footer,onLaterPages=footer)
    notes='''# Highland / drawing reconciliation 04

The three uploaded PDFs (19 sheets) now support thirteen provisional candidate placements and rejection of one false R5 repeat. Two footprint conflicts remain. The editable model contains 189 opening records, both native scenes and the full dusk camera.

- [Source comparison and audit](Highland-drawing-reconciliation.pdf)
- [Editable Blender model](Highland-drawing-reconciled.blend)
- [Portable GLB](Highland-drawing-reconciled.glb)
- [Daylight image](Highland-daylight-drawing-reconciled.png)
- [Editable archive with PDFs and reproduction](Highland-drawing-editable.zip)
- [Continuation handoff](HANDOFF.md)

The north overlay still shows model/elevation disagreement, particularly at the stair/MU pair. Thirteen accepted candidates establish visible presence and provisional plan locations; they are not fully reconciled dimensions. OPEN-01 needs the P1 footprint corrected; OPEN-14 needs the southeast R5 step corrected. R1 north entry geometry remains assumed. Window sizes, sill/head levels, complete sections, terrace profiles and guards are not confirmed.

The revision changes openings and their affected walls, retaining every inherited polygon, floor/grid control and roof/terrace mesh. The local native validation passes with no overlaps on corrected walls, no external images and complete GLB architecture. All 432 saved dusk camera frames pass framing checks. The earlier revision 03 film remains a separate older delivery.

See opening-audit.json/CSV, change-ledger.json, plan-registration.json, elevation-comparison.json, delivery-validation.json, element-provenance.csv and visual-review.json for exact evidence. Full uploaded PDFs and build instructions are preserved in the editable ZIP. This model remains illustrative and unsuitable for construction dimensions or quantities.
'''
    (OUT/'README.md').write_text(notes)
    print('Wrote source comparison PDF and README.',flush=True)


if __name__=='__main__':main()
