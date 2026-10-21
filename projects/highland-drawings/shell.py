"""Source-governed P1 enclosure and bounded southeast R5 continuation."""
import copy
import json
from pathlib import Path

from PIL import ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
CFG = json.loads((HERE / 'shell-decisions.json').read_text())


def interpolate(value, pixels, inches):
    pairs = sorted(zip(pixels, inches))
    index = next((i for i in range(len(pairs)-1) if value <= pairs[i+1][0]), len(pairs)-2)
    a, b = pairs[index:index+2]
    return a[1] + (value-a[0])/(b[0]-a[0])*(b[1]-a[1])


def reconcile(spec, registrations, out, plans, raster):
    before = copy.deepcopy(spec)
    for level, key in [('P1', 'p1'), ('R5', 'r5')]:
        registrations[level].update({k: CFG[key][k] for k in ('grid_y_pixels', 'grid_y_inches')})
        registrations[level]['y_method'] = '200 dpi horizontal grid/tick picks at the right-hand dimension chain, checked against A-H dimensions.'
    registrations['Roof'].update(grid_y_pixels=[224.624,389.0,534.584,628.976,723.368,820.136,952.328,1033.112],
                                 grid_y_inches=CFG['r5']['grid_y_inches'])

    def xy(level, pixel, axis):
        reg = registrations[level]
        return round(interpolate(pixel, reg[f'grid_{axis}_pixels'], reg[f'grid_{axis}_inches']), 3)

    spec['polygons']['p1'] = [[xy('P1', x, 'x'), xy('P1', y, 'y')] for x, y in CFG['p1']['polygon_pixels']]
    spec['levels'][0]['polygon'] = 'p1'
    r5 = spec['polygons']['r5']
    r5[4][1] = r5[5][1] = xy('R5', CFG['r5']['return_y_pixel'], 'y')
    r5[5][0] = r5[6][0] = xy('R5', CFG['r5']['inner_corner_x_pixel'], 'x')
    touched = []
    for level, key in [('P1', 'p1'), ('R5', 'r5')]:
        poly = spec['polygons'][key]
        for row in CFG[key]['openings']:
            old = next((e for e in spec['openings'] if e['id'] == row['id']), None)
            axis = 'x' if row['face'] == 'south' else 'y'
            low, high = sorted(xy(level, p, axis) for p in row['jamb_pixels'])
            a, b = poly[row['segment']], poly[(row['segment']+1) % len(poly)]
            k = 0 if axis == 'x' else 1
            assert min(a[k], b[k])+3 < low < high < max(a[k], b[k])-3, (row['id'], low, high, a, b)
            z = next(e['z'] for e in spec['levels'] if e['name'] == level)
            source = f"{CFG[key]['sheet']} plan / A3.01 {row['face']} elevation; uploaded PDFs"
            entry = dict(id=row['id'], face=row['face'], level=level, polygon=key,
                segment=row['segment'], u=round((low+high)/2, 3), width=round(high-low, 3),
                z=z+row['sill_in'], height=row['height_in'], kind=row['kind'],
                status='assumed', xy_status='provisional', source=source,
                source_pixels=row.get('elevation_pixels', (old or {}).get('source_pixels')),
                plan_depth_in=a[1-k], source_width_in=round(high-low, 3),
                drawing_mark=row['mark'], plan_jamb_pixels=row['jamb_pixels'],
                plan_wall_pixel=row['wall_pixel'], geometry_revision=CFG['revision'],
                basis='Jambs measured on the independently calibrated plan and paired with the elevation; no jamb clipping. Sill/head dimensions and sections remain assumed. '+row.get('note', ''))
            spec['openings'] = [e for e in spec['openings'] if e['id'] != row['id']]
            spec['openings'].append(entry)
            touched.append({'id': entry['id'], 'old': old, 'new': entry})
    assert len(spec['openings']) == 192
    # Keep old limitations as history only where they still describe this model.
    spec['limitations'] = [s for s in spec['limitations'] if 'P1 plan was not supplied' not in s and 'inherited footprint remains unchanged' not in s.lower()]
    spec['limitations'].extend(CFG['limits'])
    spec['shell_reconciliation'] = {
        'revision': CFG['revision'], 'p1_basis': CFG['p1']['basis'], 'r5_basis': CFG['r5']['basis'],
        'changed_r5_vertices': [4, 5, 6], 'changed_r5_segments': [3, 4, 5, 6],
        'limits': CFG['limits'], 'p1_opening_count': 14,
        'north_alignment_status': 'unresolved / unchanged diagnostic residuals',
        'roof_coping': json.loads((HERE.parent/'highland-roof/geometry.json').read_text())['roof_coping']}
    report = {'revision': CFG['revision'], 'polygon_changes': {
        'p1': {'old_level_polygon': 'r1', 'new': spec['polygons']['p1'], 'source': 'A2.02', 'basis': CFG['p1']['basis']},
        'r5': {'old': before['polygons']['r5'], 'new': r5, 'source': 'A2.07 / A2.08', 'basis': CFG['r5']['basis']}},
        'opening_changes': touched, 'limits': CFG['limits'],
        'r5_inner_corner_shift_in': round(r5[5][0]-before['polygons']['r5'][5][0], 3),
        'r5_return_y_shift_in': round(r5[5][1]-before['polygons']['r5'][5][1], 3),
        'retained_tiein_residuals_in': {
            'long_east_line_vs_A2_07_1477px': round(r5[4][0]-xy('R5',1477,'x'),3),
            'south_baseline_vs_A2_07_920px': round(r5[6][1]-xy('R5',920,'y'),3)},
        'roof_source_check': {
            'sheet':'A2.08', 'inner_step_x_pixel':1430, 'return_y_pixel':822,
            'model_minus_roof_pick_in':[round(r5[5][0]-xy('Roof',1430,'x'),3),round(r5[5][1]-xy('Roof',822,'y'),3)],
            'status':'provisional comparison / not a dimensional pass',
            'basis':'Independent roof grid registration; local linework, wall/coping face convention and raster picks differ. A2.07 governs the wall; the modeled roof and coping follow it.'},
        'p1_openings_rechecked': [e['id'] for e in spec['openings'] if e['level'] == 'P1']}
    (out/'shell-reconciliation.json').write_text(json.dumps(report, indent=2)+'\n')
    # Reusable evidence: full separate P1 trace and the actual R5 local tie-ins.
    font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 20)
    for level, key, box, name in [('P1','p1',(840,200,1530,1060),'P1-enclosure-reconciled'),
                                   ('R5','r5',(1360,790,1510,940),'R5-SE-reconciled')]:
        im = raster(plans[CFG[key]['page']-1], box)
        draw = ImageDraw.Draw(im); scale = 200/72/.6
        def point(p): return ((p[0]-box[0])*scale, (p[1]-box[1])*scale)
        reg = registrations[level]
        pixel_poly = [[interpolate(x, reg['grid_x_inches'], reg['grid_x_pixels']),
                       interpolate(y, reg['grid_y_inches'], reg['grid_y_pixels'])] for x,y in spec['polygons'][key]]
        draw.line([point(p) for p in pixel_poly+[pixel_poly[0]]], fill='#1265c4', width=5)
        if level == 'P1':
            # Old R1-derived shell is diagnostic only, shown in red.
            old = [[interpolate(x, reg['grid_x_inches'], reg['grid_x_pixels']),
                    interpolate(y, reg['grid_y_inches'], reg['grid_y_pixels'])] for x,y in before['polygons']['r1']]
            draw.line([point(p) for p in old+[old[0]]], fill='#bd473f', width=3)
        for row in CFG[key]['openings']:
            lo,hi=row['jamb_pixels'];c=row['wall_pixel']
            ends=([lo,c],[hi,c]) if row['face']=='south' else ([c,lo],[c,hi])
            draw.line([point(p) for p in ends],fill='#008663',width=9)
            px,py=point(ends[0]);draw.text((px+8,py+12),row['id'],fill='#007755',font=font,stroke_width=1,stroke_fill='white')
        draw.text((12,12),'Blue: revised model | Green: plan jambs'+(' | Red: inherited R1 shell' if level=='P1' else ''),fill='#1265c4',font=font,stroke_width=1,stroke_fill='white')
        im.save(out/'source-review'/f'{name}.png')
        if level=='P1':
            # Readable south/east opening evidence in addition to the full trace.
            im.crop((0,int((900-box[1])*scale),im.width,im.height)).save(out/'source-review/P1-south-reconciled.png')
    box=(1380,785,1500,940);scale=200/72/.6
    im=raster(plans[8],box);draw=ImageDraw.Draw(im)
    reg=registrations['Roof']
    projected=[[interpolate(x,reg['grid_x_inches'],reg['grid_x_pixels']),
                interpolate(y,reg['grid_y_inches'],reg['grid_y_pixels'])] for x,y in r5]
    draw.line([((x-box[0])*scale,(y-box[1])*scale) for x,y in projected+[projected[0]]],fill='#1265c4',width=4)
    draw.text((8,8),'A2.08 / blue: modeled roof edge',font=font,fill='#1265c4',stroke_fill='white',stroke_width=1)
    im.save(out/'source-review/R5-roof-comparison.png')
    return report
