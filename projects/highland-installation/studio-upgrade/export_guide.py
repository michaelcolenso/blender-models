"""Create a readable standalone PDF of the Markdown production guide."""
import html
import re
from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Preformatted

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'output'
OUT.mkdir(exist_ok=True)
pdfmetrics.registerFont(TTFont('GuideSans','/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'))
pdfmetrics.registerFont(TTFont('GuideBold','/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'))
pdfmetrics.registerFont(TTFont('GuideMono','/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf'))
pdfmetrics.registerFontFamily('GuideSans',normal='GuideSans',bold='GuideBold')
styles=getSampleStyleSheet()
styles.add(ParagraphStyle('GuideBody',fontName='GuideSans',fontSize=9,leading=13,spaceAfter=7,textColor=colors.HexColor('#29343A')))
styles.add(ParagraphStyle('GuideTitle',parent=styles['GuideBody'],fontName='GuideBold',fontSize=22,leading=28,spaceAfter=18))
styles.add(ParagraphStyle('GuideH2',parent=styles['GuideBody'],fontName='GuideBold',fontSize=14,leading=19,spaceBefore=14,spaceAfter=8,keepWithNext=True))
styles.add(ParagraphStyle('GuideH3',parent=styles['GuideBody'],fontName='GuideBold',fontSize=11,leading=16,spaceBefore=9,keepWithNext=True))
styles.add(ParagraphStyle('GuideCell',parent=styles['GuideBody'],fontSize=7.5,leading=11,spaceAfter=0))
styles.add(ParagraphStyle('GuideCode',fontName='GuideMono',fontSize=6.6,leading=9,spaceAfter=10,backColor=colors.HexColor('#ECEDE8'),borderPadding=8))


def markup(text):
    text=html.escape(text)
    text=re.sub(r'\*\*(.+?)\*\*',r'<b>\1</b>',text)
    return re.sub(r'`(.+?)`',r'<font name="GuideMono">\1</font>',text)


def footer(canvas,doc):
    canvas.setFillColor(colors.HexColor('#F7F6F2'))
    canvas.rect(0,0,612,792,fill=1,stroke=0)
    canvas.setFont('GuideSans',7)
    canvas.setFillColor(colors.HexColor('#66757B'))
    canvas.drawString(42,24,'200 W Highland · Studio visualization guide · Conceptual geometry requires field verification')
    canvas.drawRightString(570,24,str(doc.page))


def main():
    lines=(ROOT/'UPGRADE-GUIDE.md').read_text().splitlines()
    story=[];i=0
    while i<len(lines):
        line=lines[i]
        if not line.strip():i+=1;continue
        if line.startswith('```'):
            code=[];i+=1
            while i<len(lines) and not lines[i].startswith('```'):
                code.append(lines[i]);i+=1
            story.append(Preformatted('\n'.join(code),styles['GuideCode'],maxLineLength=112));i+=1;continue
        if line.startswith('|'):
            rows=[]
            while i<len(lines) and lines[i].startswith('|'):
                parts=[s.strip() for s in lines[i].strip('|').split('|')]
                if not all(re.fullmatch(r'[:\- ]+',s) for s in parts):rows.append(parts)
                i+=1
            count=len(rows[0]);width=528/count
            cells=[[Paragraph(markup(s),styles['GuideCell']) for s in row] for row in rows]
            table=Table(cells,colWidths=[width]*count,repeatRows=1,hAlign='LEFT')
            table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#E6EAE5')),('VALIGN',(0,0),(-1,-1),'TOP'),('LINEBELOW',(0,0),(-1,0),.5,colors.HexColor('#B7C1BD')),('LEFTPADDING',(0,0),(-1,-1),6),('RIGHTPADDING',(0,0),(-1,-1),6),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5)]))
            story.extend([table,Spacer(1,10)]);continue
        if line.startswith('# '):style='GuideTitle';line=line[2:]
        elif line.startswith('## '):style='GuideH2';line=line[3:]
        elif line.startswith('### '):style='GuideH3';line=line[4:]
        else:style='GuideBody'
        story.append(Paragraph(markup(line),styles[style]));i+=1
    doc=SimpleDocTemplate(str(OUT/'Highland-studio-upgrade-guide.pdf'),pagesize=(612,792),leftMargin=42,rightMargin=42,topMargin=40,bottomMargin=42,title='Highland studio visualization upgrade',author='Highland project')
    doc.build(story,onFirstPage=footer,onLaterPages=footer)
    print('GUIDE_PDF_COMPLETE')


if __name__=='__main__':main()
