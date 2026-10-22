"""Publish the ordered R5 enclosure, terrace and presentation review."""
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
    validation=json.loads((OUT/'delivery-validation.json').read_text())
    north=json.loads((OUT/'elevation-comparison.json').read_text())
    r5=json.loads((OUT/'r5-completion.json').read_text())
    elevation=json.loads((OUT/'r5-elevation-comparison.json').read_text())
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
    def pair(left,right,height=240):
        story.append(Table([[img(left,250,height),img(right,250,height)]],colWidths=[260,260]))
        story.append(Spacer(1,8))
    def page(title):story.append(PageBreak());p(title,'Title')

    p('Highland / drawing reconciliation 06','Title')
    p('R5 enclosure, terrace arrangement and refreshed exterior studies','Heading2')
    p('Completed in order: the remaining R5 enclosure and non-north openings; terrace edges, coping and guards; then whole-building review and fresh native day/dusk images. North stair/MU alignment and R1 north entries remain deferred at the owner\'s request.')
    story.append(img('Highland-daylight-drawing-reconciled.png',520,315));story.append(Spacer(1,8))
    p('Native Cycles daylight image. Plan XY is provisional; complete profiles, guards, sill/head dimensions and site context remain assumed. This is an illustrative coordination model, not a verified as-built or construction model.','SmallNote')
    table([['Review','Result'],['Opening inventory','192; 15 original candidates provisionally placed, 1 false repeat rejected'],['R5 enclosure','14 vertices; 28 south/east/west openings rechecked; north preserved'],['Terraces','5 walking surfaces + gravel planter; 5 guard paths; 3 band paths'],['Source set','3 original PDFs / 19 sheets, preserved with exact hashes']],[160,360])
    p('Printed drawing date: 04-02-07. Complete ASI/RFI responses, window schedules and the referenced A4/A5 profiles were not supplied.','SmallNote')

    page('1 / R5 enclosure and openings')
    p('A2.07 separates the west terraces from enclosed rooms. The southwest steps now follow those room boundaries rather than enclosing the terraces. The long east line and south baseline follow the selected plan picks; both prior local tie-in residuals are zero against those picks. This does not establish source accuracy or resolve plan/elevation disagreements.')
    pair('source-review/R5-enclosure-completed.png','geometry-review/r5-plan.png',275)
    p('Left: calibrated plan and revised trace. Right: saved native R5 enclosure and openings only. Orange means complete components remain assumed; measured plan positions are provisional.','SmallNote')
    pair('source-review/R5-SW-completed.png','geometry-review/r5-southwest.png',190)
    p('All 28 non-north R5 openings were assigned to their actual stepped wall segments, with full jamb spans. The southwest MT is a wide opening on the terrace return. The final south pair is MO/MJ: MJ corrects the prior MU transcription. Its contiguous records share one interface, removing the invented masonry gap; complete pane profiles remain assumed.','SmallNote')
    p('The six north R5 openings and north-facing wall are unchanged. Upper east/west lines tie into the preserved north endpoints; the retained source registration differences are listed on page 4.','SmallNote')

    page('2 / Terrace, guard and coping arrangement')
    p('The old broad terrace surface is replaced by five walking terraces and a separate south gravel planter. Exposed edges receive five open guard paths; room walls and glazing receive none. The east MR-window projection labeled as a cornice line above is not treated as another occupied terrace.')
    pair('source-review/R5-terrace-arrangement.png','geometry-review/terrace-plan.png',240)
    p('Source arrangement (left) and native terrace/enclosure plan (right). The south walking strip, gravel planter and projecting southwest/southeast bands are distinct. The middle-west and lower-west terraces now remain outside the room shell.','SmallNote')
    story.append(img('source-review/R5-south-terraces.png',520,135));story.append(Spacer(1,8))
    table([['Component','Source / remaining assumption'],['Three band paths','26 / 28 / 30 in source-scaled top heights retained provisionally; complete profiles and construction assumed'],['Exterior guards','Arrangement provisional; representative 42 in height, posts, infill, connections and compliance unverified'],['South clerestory','Footprint re-registered to A2.08; 407.75 ft complete top retained; four glazing fields and cap sections assumed']],[145,375])
    p('The split roof plates, step closure and perimeter coping follow the corrected enclosure. North and south complete coping tops remain 407.75 ft and 406.25 ft. A6 stair guard details do not establish exterior terrace guard sections. Drainage, waterproofing and thresholds remain undeveloped.','SmallNote')

    page('Source differences / north deferred')
    p('Plan jambs govern provisional XY. Independent elevation projections retain the following diagnostic center differences; geometry has not been averaged between conflicting sources. These are overview-raster pixels, not a construction tolerance or an independent rendered-edge accuracy certificate.')
    rows=[['Diagnostic','Maximum absolute center difference']]
    for face,delta in elevation['by_face_max_abs_center_delta_px'].items():rows.append(['R5 '+face,f'{delta:.3f} px'])
    rows.append(['North R2-R5',f"{north['max_abs_horizontal_center_delta_px']:.3f} px; unchanged and deferred"])
    table(rows,[220,300])
    residual=r5['retained_north_tiein_model_minus_plan_in']
    p(f"The preserved north tie-in differs from the selected A2.07 registration by {residual['west_x']:+.3f} in at west X, {residual['east_x']:+.3f} in at east X and {residual['north_y']:+.3f} in at north Y. J-west and K-east-door terraces follow those same preserved wall endpoints.")
    story.append(img('source-review/north-plan-model-overlay.png',520,180));story.append(Spacer(1,8))
    story.append(img('geometry-review/north.png',520,155));story.append(Spacer(1,8))
    p(f"All {validation['north_meshes_identical_to_revision04']} protected north meshes remain identical to revision 04. Six north openings per typical floor does not establish alignment. North stair/MU and R1 entry work remain deferred; their residuals and unaudited status remain explicit.",'SmallNote')
    p('R5 source centers, projected centers and signed differences are in r5-elevation-comparison.json. The 24 north comparisons remain in elevation-comparison.json. The historical shell-reconciliation.json describes revision 05; r5-completion.json supersedes its remaining R5 footprint limits.','SmallNote')

    page('3 / Whole-building and dusk review')
    p('Ten fresh provenance views cover north, south, east, west, roof plan, isometric, southeast return, isolated R5 enclosure, southwest terraces and terrace plan. Apartment dressing was moved with the corrected non-north glazing, while retaining illustrative materials and lighting. The architectural inventory is unchanged by this presentation pass.')
    story.append(img('Highland-dusk-drawing-reconciled.png',520,295));story.append(Spacer(1,8))
    p('Fresh native Cycles dusk image, frame 217 of the existing 432-frame camera path. The complete camera path was checked for framing. This delivery includes stills, not a newly rendered film.','SmallNote')
    pair('dusk-review/frame-001.png','dusk-review/frame-432.png',160)
    p('Saved dusk camera endpoints: frame 1 (left), frame 432 (right). The older revision 03 movie remains a separate earlier delivery.','SmallNote')
    table([['Native readback','Result'],['Apartment dressing',f"{validation['presentation_validation']['objects_refreshed']} objects across {validation['presentation_validation']['openings_refreshed']} openings; no north dressing refreshed"],['Presentation protection','Architecture hashes unchanged by dressing refresh'],['Source status','Rendered detail, room dressing, landscape and light behavior remain illustrative']],[180,340])

    page('Verification and handoff')
    table([['Check','Result'],['Saved native inventory',f"{validation['architecture_meshes']} architectural meshes; {validation['unchanged_architecture_meshes']} unchanged from revision 03"],['Revision 05 protection',f"{validation['revision05_protected_meshes']} protected architecture hashes preserved, including P1 and lower stories"],['Opening voids / frame extents','192 records; 0 overlapping corrected voids; native frames read back without clipping'],['R5 stage protection','99 stage-1 core mesh hashes preserved through terrace and presentation work'],['Terrace intersections','0 surface-room overlaps; 0 guard centerlines inside rooms'],['Slabs / roof / coping','Actual slab outlines, areas and levels; split roof coverage; coping tops and joints checked'],['Native scenes / portability','Daylight + Dusk; all 432 camera frames checked; packed images; complete architecture in GLB'],['Workflow checks','11 render-workflow tests pass without skips; catalog resolves 5 shots']],[220,300])
    p('P1 remains as reconciled in revision 05: a separate A2.02 enclosure with fourteen openings, recessed garage gate and service door. The parking ramp, below-grade construction, open ventilation shaft and external trellises are outside this simplified enclosure scope.')
    p('Remaining development','Heading2')
    p('The ordered R5 work is complete at provisional coordination level. Remaining decisions require window schedules, A4/A5 cornice/coping/guard profiles, complete ASI/RFI responses or installed-condition evidence. P1 ramp and below-grade details can be developed separately. North stair/MU and R1 entries remain deferred.')
    p('Exact inspected source, native review, still and report hashes are in visual-review.json. delivery-validation.json contains machine checks; stage1-validation.json and stage2-validation.json preserve intermediate gates. The editable archive includes original PDFs, the base native model, scripts, decisions and reproduction inputs. Floating-point agreement verifies the model follows its specification; it does not certify the raster measurements.','SmallNote')
    p('Sources: site-and-floor-plans.pdf (A1.01, A2.01-A2.08); exterior-elevations-and-sections.pdf (A3.01, A3.02, A3.11-A3.13); stairs-and-rcp.pdf (A6.01-A6.04, A7.51). See source-inventory.json for page mapping and exact source hashes.','SmallNote')
    def footer(canvas,doc):
        canvas.setFont('Helvetica',8);canvas.setFillColor(colors.HexColor('#586e7b'))
        canvas.drawString(40,24,'200 W. Highland / illustrative source review / not for construction')
        canvas.drawRightString(572,24,str(doc.page))
    SimpleDocTemplate(str(OUT/'Highland-drawing-reconciliation.pdf'),pagesize=(612,792),rightMargin=46,leftMargin=46,topMargin=36,bottomMargin=42).build(story,onFirstPage=footer,onLaterPages=footer)
    print('Wrote revision 06 source comparison PDF.',flush=True)


if __name__=='__main__':main()
