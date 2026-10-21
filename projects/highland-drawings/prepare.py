"""Inventory uploaded PDFs and reconcile openings and source-bounded shell geometry."""
from shell import reconcile as reconcile_shell
from r5 import reconcile as reconcile_r5
from terraces import reconcile as reconcile_terraces
import argparse
import copy
import csv
import hashlib
import json
from pathlib import Path

import fitz
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
OUT = ROOT / 'deliverables/highland-drawings'
CFG = json.loads((HERE / 'decisions.json').read_text())
X = [0, 195, 528, 861, 1236]
FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def interp(v, ps):
    i = next((i for i in range(4) if v <= ps[i+1]), 3)
    return X[i] + (v-ps[i]) / (ps[i+1]-ps[i]) * (X[i+1]-X[i])


def raster(page, box, dpi=200):
    pix = page.get_pixmap(matrix=fitz.Matrix(dpi/72, dpi/72),
                         clip=fitz.Rect(*(v/.6 for v in box)), alpha=False)
    return Image.frombytes('RGB', (pix.width, pix.height), pix.samples)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--stage',choices=('r5','terraces','presentation'),default='presentation');args=parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    review = OUT / 'source-review'
    review.mkdir(exist_ok=True)
    inventory = []
    for source in CFG['sources']:
        path = HERE / 'references' / source['file']
        doc = fitz.open(path)
        assert len(doc) == len(source['sheets'])
        inventory.append({**source, 'sha256': sha(path), 'bytes': path.stat().st_size,
                          'pages': len(doc), 'sheet_size_pt': list(doc[0].rect),
                          'printed_date': '2007-04-02', 'annotation_dates': 'not established'})
    (OUT / 'source-inventory.json').write_text(json.dumps(inventory, indent=2)+'\n')
    plans = fitz.open(HERE / 'references/site-and-floor-plans.pdf')
    elevations = fitz.open(HERE / 'references/exterior-elevations-and-sections.pdf')
    registrations = {}
    for level, cfg in CFG['plan_registration'].items():
        box = (840, 60, 1460, 112)
        im = raster(plans[cfg['page']-1], box)
        a = np.array(im).min(axis=2)
        sc = 200/72/.6
        # Dimension tick/grid centerline: inspect the vertical line below the bubble.
        score = (a[round((76-60)*sc):round((89-60)*sc)] < 130).sum(axis=0)
        picked = []
        for expected in cfg['expected_x']:
            lo, hi = [round((v-840)*sc) for v in (expected-7, expected+7)]
            best = lo + int(np.argmax(score[lo:hi+1]))
            picked.append(round(840+best/sc, 3))
        scales = [(picked[i+1]-picked[i])/(X[i+1]-X[i]) for i in range(4)]
        assert max(scales)/min(scales) < 1.04, (level, picked, scales)
        registrations[level] = {**cfg, 'grid_x_pixels': picked, 'grid_x_inches': X,
            'dimension_strings': ['16 ft 3 in', '27 ft 9 in', '27 ft 9 in', '31 ft 3 in'],
            'pixels_per_inch_by_span': scales,
            'method': '200 dpi dimension-tick/grid line picks; piecewise interpolation on this sheet only. Inspect annotated grid image.',
            'pick_uncertainty_in': 3, 'status': 'provisional'}
        draw = ImageDraw.Draw(im)
        for px, label in zip(picked, ('6', '7', '8', '9', '10')):
            xx = (px-840)*sc
            draw.line((xx, 0, xx, im.height), fill='#ce463c', width=2)
            draw.text((xx+5, im.height-30), label, fill='#ce463c', font=ImageFont.truetype(FONT, 23))
        im.save(review / f'{level}-grid-calibration.png')
        print('REGISTER', level, picked, flush=True)
    (OUT / 'plan-registration.json').write_text(json.dumps(registrations, indent=2)+'\n')

    spec = json.loads((ROOT / CFG['base_spec']).read_text())
    before = copy.deepcopy(spec)
    changes = []
    evidence = []

    def opening(level, face, row):
        pk = 'r1' if level == 'R1' else 'r5' if level == 'R5' else 'typical'
        poly = spec['polygons'][pk]
        a, b = poly[row['segment']], poly[(row['segment']+1) % len(poly)]
        lo, hi = sorted(interp(px, registrations[level]['grid_x_pixels']) for px in row['jamb_pixels'])
        assert abs(a[1]-b[1]) < .001
        assert min(a[0], b[0])+3 < lo < hi < max(a[0], b[0])-3, (level, face, row, lo, hi, a, b)
        ident = f'{face}-{level}-{row["column"]:02}'
        z = next(x['z'] for x in spec['levels'] if x['name'] == level)
        source = f'{registrations[level]["sheet"]} plan / A3.0{1 if face == "south" else 2} {face} elevation; uploaded PDFs'
        old = next((e for e in before['openings'] if e['id'] == ident), None)
        source_pixels = row.get('elevation_pixels')
        if source_pixels is None:
            source_pixels = old['source_pixels'] if old else ([996,1026] if level != 'R5' else [996,1015] if row['column'] == 1 else [1042,1073])
        e = dict(id=ident, face=face, level=level, polygon=pk, segment=row['segment'],
            u=round((lo+hi)/2, 3), width=round(hi-lo, 3),
            z=z+row.get('sill_in', 18 if level == 'R5' else 9),
            height=row.get('height_in', 84 if level == 'R5' else 90),
            kind='small' if row.get('mark') == 'MDD' else 'window',
            status='assumed', xy_status='provisional', source=source,
            source_pixels=source_pixels,
            plan_depth_in=a[1], source_width_in=round(hi-lo, 3),
            drawing_mark=row.get('mark', 'MO'), plan_jamb_pixels=row['jamb_pixels'],
            plan_wall_y_pixel=row['wall_y_pixel'], geometry_revision=CFG['revision'],
            basis='Plan jambs measured on the uploaded sheet and assigned to the matching stepped wall; elevation controls presence, opening order and mark. Complete window sections and standardized sill/head dimensions remain assumed. Inherited wall depth is retained; no new global dimensional tolerance is established.')
        changes.append({'id': ident, 'old': old, 'new': e})
        evidence.append({'id': ident, 'level': level, 'row': row, 'opening': e})
        return e

    for row in CFG['south_restorations']:
        spec['openings'].append(opening(row['level'], 'south', row))
    # The old third south column shared the second column's wrong short return.
    # Move it to the next south-facing plan return before restoring column 02.
    for level in ('R1','R2','R3','R4'):
        for column,segment,pixels,yy in [(3,26,[1041,1084],841),(4,24,[1075,1085],868)]:
            ident=f'south-{level}-{column:02}'
            spec['openings']=[e for e in spec['openings'] if e['id'] != ident]
            row={'column':column,'segment':segment,'jamb_pixels':pixels,
                 'wall_y_pixel':yy,'mark':'return / schedule pending'}
            spec['openings'].append(opening(level,'south',row))
    spec['openings'] = [e for e in spec['openings'] if not(e['face'] == 'north' and e['level'] in ('R2', 'R3', 'R4', 'R5'))]
    for level in ('R2', 'R3', 'R4', 'R5'):
        for row in CFG['north_r5' if level == 'R5' else 'north_typical']:
            spec['openings'].append(opening(level, 'north', row))
    assert len(spec['openings']) == 189
    assert len({e['id'] for e in spec['openings']}) == 189
    shell = reconcile_shell(spec, registrations, OUT, plans, raster)
    completion = reconcile_r5(spec, registrations, OUT, plans, raster)
    spec['completed_geometry_stage']=1
    if args.stage in ('terraces','presentation'):
        reconcile_terraces(spec, registrations, OUT, plans, raster)
        spec['completed_geometry_stage']=2
    if args.stage=='presentation':
        spec['presentation_refresh']=json.loads((HERE/'presentation.json').read_text())
    (OUT / 'plan-registration.json').write_text(json.dumps(registrations, indent=2)+'\n')
    changes = [{'id': e['id'], 'old': next((old for old in before['openings'] if old['id'] == e['id']), None), 'new': e}
               for e in spec['openings'] if e != next((old for old in before['openings'] if old['id'] == e['id']), None)]
    inherited_audit = json.loads((ROOT / 'deliverables/highland-roof/opening-audit.json').read_text())
    accepted = {r['candidate']: f'south-{r["level"]}-{r["column"]:02}' for r in CFG['south_restorations']}
    for candidate, level, col in [('OPEN-04','R2',1),('OPEN-05','R2',6),('OPEN-07','R3',1),('OPEN-08','R3',6),('OPEN-10','R4',1),('OPEN-11','R4',6),('OPEN-15','R5',6)]:
        accepted[candidate] = f'north-{level}-{col:02}'
    accepted.update({'OPEN-01': 'south-P1-02', 'OPEN-14': 'south-R5-09'})
    audit = []
    for candidate in inherited_audit['candidates']:
        ident = candidate['id']
        if ident in accepted:
            linked = next(e for e in spec['openings'] if e['id'] == accepted[ident])
            decision = 'accepted / provisionally located'
            reason = 'Plan wall and jambs paired with the actual elevation row; the previous projection was not retained.'
        elif ident in CFG['rejected']:
            linked = None; decision = 'rejected / absent from this floor'; reason = CFG['rejected'][ident]
        else:
            linked = None; decision = 'unresolved / footprint reconciliation'; reason = CFG['unresolved'][ident]
        audit.append({'id': ident, 'level': candidate['level'], 'face': candidate['face'],
                      'previous_pixels': candidate['pixels'], 'decision': decision, 'reason': reason,
                      'model_opening': linked['id'] if linked else None,
                      'source': linked['source'] if linked else 'Uploaded A2.02/A2.07/A3.01/A3.02 PDFs',
                      'plan_jamb_pixels': linked.get('plan_jamb_pixels') if linked else None})
    report = {'base_openings':175, 'revised_openings':192, 'reviewed_candidates':16,
              'accepted_candidates':15, 'rejected_candidates':1, 'remaining_unresolved':0,
              'north_row_note':'R2-R5 north rows reconstructed from six actual elevation openings each. Existing column IDs are reassigned; use the change ledger rather than assuming ID continuity means an unchanged window.',
              'candidates':audit, 'limits':spec['limitations'], 'dimensional_alignment_status':'Not closed: north residuals and remaining source limitations are explicit; candidate disposition is not dimensional verification.'}
    (OUT / 'opening-audit.json').write_text(json.dumps(report, indent=2)+'\n')
    with (OUT / 'opening-audit.csv').open('w', newline='') as f:
        writer=csv.DictWriter(f, fieldnames=list(audit[0]));writer.writeheader();writer.writerows(audit)
    spec['rejected_candidates'] = [e for e in before['rejected_candidates'] if (e['level'],e['face'],e['pixels']) in [(c['level'],c['face'],c['previous_pixels']) for c in audit if c['decision'].startswith('unresolved')]]
    spec['drawing_reconciliation'] = {'revision':CFG['revision'], 'sources':inventory,
        'calibration':registrations, 'complete_component_status':'assumed', 'limits':CFG['limits']}
    spec['limitations'].extend(CFG['limits'])
    assert spec['polygons']['r1'] == before['polygons']['r1']
    assert spec['polygons']['typical'] == before['polygons']['typical']
    assert [(e['name'], e['z']) for e in spec['levels']] == [(e['name'], e['z']) for e in before['levels']]
    assert spec['roof_features'][:2]==before['roof_features'][:2]
    assert [e['top'] for e in spec['roof_features']]==[e['top'] for e in before['roof_features']]
    for key in ('grid_dimensions_in','roof_plate_z','north_roof_plate_z','north_roof_split_y'):
        assert spec[key] == before[key], key
    (HERE / 'reconciled.spec.json').write_text(json.dumps(spec, indent=2)+'\n')
    (OUT / 'reconciled.spec.json').write_text(json.dumps(spec, indent=2)+'\n')
    (OUT / 'change-ledger.json').write_text(json.dumps({'revision':CFG['revision'], 'opening_changes':changes, 'coupled_south_correction':'Columns 02 and 03 previously shared one short return, while column 04 occupied the next return. Columns 03/04 are reassigned to their successive plan returns. The unsupported column-03 recess/guard is removed; source openings no longer overlap.', 'r5_completion':completion, 'shell_changes':shell['polygon_changes'], 'protected_controls':['R1 and typical polygons','All six floor elevations','Dimensioned grid spans','Roof plate levels/split','Elevator/stair towers and established roof top datums'], 'roof_changes':['Both split roof plates','R5 perimeter coping','Roof step closure','Source terrace/guard/band paths','South clerestory footprint']}, indent=2)+'\n')

    for level in registrations:
        selected = [e for e in evidence if e['level'] == level]
        for face in ('south','north'):
            picks = [e for e in selected if e['opening']['face'] == face]
            if not picks: continue
            box = (920,200,1530,290) if face == 'north' else (960,460,1110,890) if level == 'R5' else (960,610,1110,890)
            im = raster(plans[registrations[level]['page']-1], box)
            draw = ImageDraw.Draw(im);sc=200/72/.6
            font=ImageFont.truetype(FONT, 17)
            for e in picks:
                a,b=e['row']['jamb_pixels'];y=e['row']['wall_y_pixel']
                p0,p1=(a-box[0])*sc,(b-box[0])*sc;yy=(y-box[1])*sc
                draw.rectangle((p0,yy-12,p1,yy+12),outline='#d54427',width=4)
                label=e['opening']['id']+' / '+e['opening']['drawing_mark']
                label_y=yy+20 if e['row']['column']%2 else yy-45
                draw.text((max(0,p0-10),max(0,label_y)), label, fill='#a92d1b',font=font,stroke_width=1,stroke_fill='white')
            im.save(review / f'{level}-{face}-plan-picks.png')
    for pg,name,box in [(2,'A3.02-north',(825,20,1515,445)),(1,'A3.01-south',(830,30,1535,525))]:
        raster(elevations[pg-1],box).save(review/(name+'.png'))
    for pg,name,box in [(3,'P1-initial-conflict-detail',(850,810,1040,1040)),(8,'R5-SE-initial-conflict-detail',(1400,795,1490,855)),(9,'A2.08-roof-top-callouts',(1120,200,1470,940))]:
        raster(plans[pg-1],box).save(review/(name+'.png'))
    for pg,name,box in [(1,'P1-east-elevation',(630,1082,1030,1140)),(1,'P1-south-elevation',(855,443,1510,517)),(1,'R5-east-elevation',(730,780,950,856)),(1,'R5-south-elevation',(970,150,1515,221))]:
        raster(elevations[pg-1],box).save(review/(name+'.png'))
    print('Prepared 192 openings; 15 candidates provisionally located, 1 rejected. North dimensional alignment remains unresolved.', flush=True)


if __name__ == '__main__':
    main()
