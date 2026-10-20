"""Make a readable continuation brief and add it to a copy of the delivered ZIP."""
import csv
import hashlib
import json
import re
import shutil
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle,getSampleStyleSheet
from reportlab.platypus import Paragraph,Preformatted,SimpleDocTemplate,Spacer,Table,TableStyle

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
OUT=ROOT/'deliverables/highland-refined'

def details(path):
    return {'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}

source=ROOT/'projects/highland-refined/exterior-revised.spec.json'
spec=json.loads(source.read_text())
pending=spec['rejected_candidates']
assert len(pending)==16
assert sum(e['face']=='south' for e in pending)==8
assert sum(e['face']=='north' for e in pending)==8
csv_path=OUT/'unresolved-openings.csv'
with csv_path.open('w',newline='') as f:
    w=csv.writer(f)
    w.writerow(['handoff_id','source_ledger_index_zero_based','face','level','ledger_pixel_start','ledger_pixel_end','reason'])
    for i,e in enumerate(pending):w.writerow([f'OPEN-{i+1:02}',i,e['face'],e['level'],*e['pixels'],e['reason']])
md=OUT/'Highland-HANDOFF.md'
shutil.copyfile(HERE/'HANDOFF.md',md)
pdf=OUT/'Highland-handoff.pdf'

styles=getSampleStyleSheet()
navy=colors.HexColor('#193246')
body=ParagraphStyle('Handoff body',fontName='Helvetica',fontSize=9.2,leading=12.5,spaceAfter=5,textColor=colors.HexColor('#263943'))
title=ParagraphStyle('Handoff title',parent=body,fontSize=19,leading=23,textColor=navy,spaceAfter=10,keepWithNext=True)
heading=ParagraphStyle('Handoff heading',parent=body,fontName='Helvetica-Bold',fontSize=12,leading=15,spaceBefore=10,spaceAfter=6,keepWithNext=True)
cell=ParagraphStyle('Handoff cell',parent=body,fontSize=8.3,leading=10.6,spaceAfter=0)
code=ParagraphStyle('Handoff code',fontName='Courier',fontSize=7.1,leading=9.2,backColor=colors.HexColor('#f1f4f6'),borderPadding=7,spaceBefore=6,spaceAfter=8)
bullet=ParagraphStyle('Handoff bullet',parent=body,leftIndent=13,firstLineIndent=0,bulletIndent=0)
doc=SimpleDocTemplate(str(pdf),pagesize=A4,rightMargin=36,leftMargin=36,topMargin=38,bottomMargin=38,title='200 W Highland - continuation handoff',author='Project handoff')

def inline(text):
    text=escape(text)
    text=re.sub(r'`([^`]+)`',r'<font name="Courier" size="7.5">\1</font>',text)
    text=re.sub(r'\*\*([^*]+)\*\*',r'<b>\1</b>',text)
    return text

lines=md.read_text().splitlines();story=[];i=0
while i<len(lines):
    line=lines[i]
    if not line.strip():i+=1;continue
    if line.startswith('```'):
        block=[];i+=1
        while i<len(lines) and not lines[i].startswith('```'):block.append(lines[i]);i+=1
        story.append(Preformatted('\n'.join(block),code,maxLineLength=110));i+=1;continue
    if line.startswith('|'):
        rows=[]
        while i<len(lines) and lines[i].startswith('|'):
            row=[s.strip() for s in lines[i].strip().strip('|').split('|')]
            if not all(re.fullmatch(r':?-+:?',s) for s in row):rows.append([Paragraph(inline(s),cell) for s in row])
            i+=1
        t=Table(rows,colWidths=[doc.width*.45,doc.width*.55],repeatRows=1,hAlign=TA_LEFT)
        t.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e4edf3')),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#f7f9fa')]),('LEFTPADDING',(0,0),(-1,-1),6),('RIGHTPADDING',(0,0),(-1,-1),6),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5),('LINEBELOW',(0,0),(-1,0),.5,colors.HexColor('#aebfca'))]))
        story.extend([t,Spacer(1,6)]);continue
    if line.startswith('# '):story.append(Paragraph(inline(line[2:]),title));i+=1;continue
    if line.startswith('## '):story.append(Paragraph(inline(line[3:]),heading));i+=1;continue
    match=re.match(r'^(\d+)\.\s+(.*)',line)
    if line.startswith('- ') or match:
        text=line[2:] if line.startswith('- ') else match[2]
        mark='\u2022' if line.startswith('- ') else match[1]+'.'
        story.append(Paragraph(inline(text),bullet,bulletText=mark));i+=1;continue
    paragraph=[line];i+=1
    while i<len(lines) and lines[i].strip() and not re.match(r'^(#|\||```|- |\d+\. )',lines[i]):paragraph.append(lines[i]);i+=1
    story.append(Paragraph(inline(' '.join(paragraph)),body))

def footer(canvas,document):
    canvas.saveState();canvas.setStrokeColor(colors.HexColor('#d8e1e6'));canvas.line(36,29,A4[0]-36,29)
    canvas.setFillColor(colors.HexColor('#566b78'));canvas.setFont('Helvetica',7.2)
    canvas.drawString(36,18,'200 W Highland | Continuation handoff | October 20, 2026')
    canvas.drawRightString(A4[0]-36,18,str(document.page));canvas.restoreState()

doc.build(story,onFirstPage=footer,onLaterPages=footer)
print('Created',md.name,pdf.name,csv_path.name,flush=True)

original=OUT/'Highland-revised-editable-package.zip'
original_check=json.loads((OUT/'archive-validation.json').read_text())
assert details(original)['sha256']==original_check['sha256']
additions={
    'START-HERE.md':md,
    pdf.name:pdf,
    csv_path.name:csv_path,
    'archive-validation.json':OUT/'archive-validation.json',
    'reproduction/projects/highland-refined/HANDOFF.md':HERE/'HANDOFF.md',
    'reproduction/projects/highland-refined/create-handoff.py':Path(__file__),
}
manifest={'purpose':'Continuation handoff; original render/model files are unchanged.','base_archive':{'name':original.name,**details(original)},'new_files':{name:details(path) for name,path in additions.items()}}
manifest_path=OUT/'handoff-manifest.json';manifest_path.write_text(json.dumps(manifest,indent=2)+'\n')
archive=OUT/'Highland-continuation-handoff.zip'
with zipfile.ZipFile(original) as src,zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as dst:
    for item in src.infolist():dst.writestr(item,src.read(item.filename))
    for name,path in additions.items():dst.write(path,name)
    dst.write(manifest_path,manifest_path.name)
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    result={'file':archive.name,'entries':len(z.infolist()),'crc_verified':True,**details(archive)}
(OUT/'handoff-archive-validation.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2),flush=True)
