"""Reconcile the recovered VDC and B101 v4 data against canonical Meydenbauer state (CPU, read-only inputs).

    python reconcile.py            # verify snapshots, write deliverables/vdc-recovery/reconciliation.json
    python reconcile.py --check    # same, but fail if the tracked report would change

Nothing is imported into project-state.json. The VDC model and the canonical takeoff use
different geometry, identifiers, quantity methods and schedule structures; this report says
where they agree, where they differ, and why, so a later slice can decide what to adopt.
"""
import argparse
import csv
import gzip
import hashlib
import io
import json
import math
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

from bmodels.paths import ROOT

HERE = Path(__file__).resolve().parent
SITE = ROOT / 'projects/meydenbauer-b'
STATE = SITE / 'state/project-state.json'
SPEC = SITE / 'products/underslab/meydenbauer-b.spec.json'
REPORT = SITE / 'deliverables/vdc-recovery/reconciliation.json'
UNITS = ('B101', 'B102', 'B103', 'B104')
CF_PER_CY = 27.0


def r(x, n=2):
    return None if x is None else round(x, n)


def load_snapshots():
    recovery = json.loads((HERE / 'recovery.json').read_text())
    data = {}
    for row in recovery['files']:
        raw = (HERE / row['file']).read_bytes()
        if row['stored'] == 'gzip':
            raw = gzip.decompress(raw)
        blob = hashlib.sha1(f'blob {len(raw)}\0'.encode() + raw).hexdigest()
        if (len(raw), hashlib.sha256(raw).hexdigest(), blob) != (row['bytes'], row['sha256'], row['git_blob_sha']):
            raise SystemExit(f"snapshot drift: {row['file']}")
        data[(row['source'], row['source_path'].split('/', 3)[-1])] = raw
    return recovery, data


def table(data, source, name):
    return list(csv.DictReader(io.StringIO(data[(source, name)].decode('utf-8-sig'))))


def seg_distance(p, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    length = dx * dx + dy * dy
    t = 0 if length == 0 else max(0, min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / length))
    return math.hypot(p[0] - a[0] - t * dx, p[1] - a[1] - t * dy)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()

    recovery, data = load_snapshots()
    state = json.loads(STATE.read_text())
    spec = json.loads(SPEC.read_text())
    meta = state['metadata']

    # ---- canonical side
    canon_lf = {UNITS[i]: 0.0 for i in range(4)}
    pipe_units = {e['id']: e['properties']['unit'].replace('-', '') for e in state['elements'] if e['kind'] == 'pipe'}
    for q in state['quantities']:
        if q['measure'] == 'pipe_length' and q['element_id'] in pipe_units:
            canon_lf[pipe_units[q['element_id']]] += q['value']
    by_scenario = defaultdict(dict)
    for q in state['quantities']:
        kind = q['element_id'].split(':')[1]
        if q['measure'] in ('slab_cut', 'excavation_bank') and q['scenario_id']:
            key = q['element_id'].split(':')[2].replace('-', '').upper() if kind == 'unit' else 'TOTAL'
            by_scenario[(q['measure'], q['scenario_id'].split(':')[-1])][key] = (q['value'], q['unit'])
    segments = {}
    for u in spec['units']:
        nodes = u['nodes']
        segments[u['unit'].replace('-', '')] = [(nodes[e['a']]['xy_ft'], nodes[e['b']]['xy_ft']) for e in u['edges']]

    # ---- VDC side
    register = list(csv.DictReader(io.StringIO(data[('vdc', 'Meydenbauer_VDC_Element_Register.csv')].decode())))
    ids = [row['element_id'] for row in register]
    routes = table(data, 'vdc', 'Meydenbauer_VDC_Phase2_Route_Diagnostics.csv')
    takeoff = table(data, 'vdc', 'Meydenbauer_VDC_Phase4_Takeoff.csv')
    schedule = table(data, 'vdc', 'Meydenbauer_VDC_Schedule.csv')
    issues = table(data, 'vdc', 'Meydenbauer_VDC_Phase2_Issue_Register.csv')

    def register_sum(status, component, unit_field='unit'):
        out = defaultdict(float)
        for row in register:
            if row['status'] == status and row['component_type'] == component and row['quantity_value'] not in ('', 'NA'):
                out[row[unit_field]] += float(row['quantity_value'])
        return out

    new_lf = register_sum('NEW', 'PIPE_ROUTE')
    demo_lf = register_sum('DEMOLITION', 'PIPE_ROUTE')
    takeoff_by = defaultdict(float)
    for row in takeoff:
        takeoff_by[(row['Component Type'], row['Unit'], row['Qty Unit'])] += float(row['Qty'])

    def takeoff_unit(component, qty_unit):
        return {u: takeoff_by.get((component, u, qty_unit), 0.0) for u in UNITS}

    slab_vdc = takeoff_unit('SLAB_CUT_AREA', 'SF')
    bedding = takeoff_unit('BEDDING_VOLUME', 'CF')
    backfill = takeoff_unit('BACKFILL_VOLUME', 'CF')

    # ---- per-route endpoint proximity (endpoints only: diagnostics give chords, not curves)
    route_rows = []
    for row in routes:
        if row['status'] != 'NEW':
            continue
        ends = [json.loads(row['start_xyz'])[:2], json.loads(row['end_xyz'])[:2]]
        d = [min(seg_distance(p, *s) for s in segments[row['unit']]) for p in ends]
        route_rows.append({'vdc_element_id': row['element_id'], 'name': row['name'], 'unit': row['unit'],
                           'length_ft': float(row['length_ft']), 'nominal_in': float(row['nominal_diameter_in']),
                           'endpoint_offsets_ft': [r(x) for x in d],
                           'slope_check': row['slope_check']})
    offsets = [x for row in route_rows for x in row['endpoint_offsets_ft']]
    far = [row['name'] for row in route_rows if max(row['endpoint_offsets_ft']) > 5]

    # ---- B101 v4 controls against canonical B-101 segments
    controls = table(data, 'b101', 'data/b101_route_controls_calibrated_v2.csv')
    control_offsets = defaultdict(list)
    for row in controls:
        p = (float(row['x_ft_north_to_south']), float(row['y_ft_east_to_west']))
        control_offsets[row['role']].append(min(seg_distance(p, *s) for s in segments['B101']))
    b101_md = data[('b101', 'docs/b101_calibration_report.md')].decode()

    unit_rows = []
    for u in UNITS:
        s2 = by_scenario[('slab_cut', 's2')].get(u, (None,))[0]
        ex2 = by_scenario[('excavation_bank', 's2')].get(u, (None,))[0]
        unit_rows.append({
            'unit': u, 'canonical_id': f'meydenbauer-b:unit:{u[0].lower()}-{u[1:]}',
            'new_abs_lf': {'vdc': r(new_lf[u]), 'canonical': r(canon_lf[u]), 'delta': r(new_lf[u] - canon_lf[u])},
            'vdc_demolition_lf': r(demo_lf[u]),
            'slab_cut_sf': {'vdc': r(slab_vdc[u]), 'canonical_s2': r(s2)},
            'excavation_cy': {'vdc_bedding_plus_backfill': r((bedding[u] + backfill[u]) / CF_PER_CY),
                              'canonical_s2_bank': r(ex2)},
        })

    totals = {
        'new_abs_lf': {'vdc': r(sum(new_lf.values()), 3), 'canonical': r(sum(canon_lf.values()), 3)},
        'slab_cut_sf': {'vdc': r(sum(slab_vdc.values())),
                        **{f'canonical_{s}': r(by_scenario[('slab_cut', s)]['TOTAL'][0]) for s in ('s1', 's2', 's3')}},
        'excavation_cy': {'vdc_bedding_plus_backfill': r((sum(bedding.values()) + sum(backfill.values())) / CF_PER_CY),
                          **{f'canonical_{s}_bank': r(by_scenario[('excavation_bank', s)]['TOTAL'][0])
                             for s in ('s1', 's2', 's3')}},
    }
    totals['new_abs_lf']['delta_pct'] = r(100 * (totals['new_abs_lf']['vdc'] / totals['new_abs_lf']['canonical'] - 1), 2)

    vdc_days = sum(float(row['Duration (wd)']) for row in schedule)
    report = {
        'status': 'RECOVERED_FOR_INSPECTION',
        'scope': 'VDC (4d-fixes) and B101 v4 data compared with canonical state; nothing imported',
        'sources': recovery['sources'],
        'recovered_files': len(recovery['files']),
        'left_in_archive': {'files': len(recovery['left_in_archive']),
                            'megabytes': r(sum(x['bytes'] for x in recovery['left_in_archive']) / 1e6, 1)},
        'identifiers': {
            'vdc_scheme': 'DISCIPLINE-UNIT-STATUS-TYPE-NNNN (e.g. PLM-B101-NEW-PIPE-0001); one per Blender object',
            'canonical_scheme': 'meydenbauer-b:<kind>:<unit>:<node_a>:<node_b> from the P1.02 vector extraction',
            'vdc_objects': len(ids), 'vdc_ids_unique': len(set(ids)) == len(ids),
            'vdc_ids_in_canonical': len(set(ids) & {e['id'] for e in state['elements']}),
            'crosswalk': 'unit level only (B101 -> meydenbauer-b:unit:b-101). VDC new pipe is 30 schematic routes; '
                         'canonical is 136 extracted segments. No 1:1 element mapping exists.',
            'vdc_by_discipline_status': {f'{k[0]}/{k[1]}': n for k, n in
                                         sorted(Counter((x['discipline'], x['status']) for x in register).items())},
        },
        'units_and_methods': {
            'coordinates': 'Both in feet in the same plan frame: VDC new-route endpoints lie a median '
                           f'{r(statistics.median(offsets))} ft from canonical segments of the same unit.',
            'vdc_quantities': 'Blender final-state geometry at frame 672: curve centerline length, mesh areas/volumes (CF).',
            'canonical_quantities': 'P1.02 extraction: segment length (LF); slab cut and excavation by scenario '
                                    'footprint and depth field (SF, CY bank).',
            'comparable': ['new ABS length'],
            'not_like_for_like': ['VDC slab cut is one modeled cut set; canonical carries S1/S2/S3 scenarios',
                                  'VDC bedding+backfill volume is not canonical bank excavation (different boundary)'],
        },
        'by_unit': unit_rows,
        'totals': totals,
        'routes': {'new_routes': len(route_rows), 'endpoint_offset_median_ft': r(statistics.median(offsets)),
                   'endpoint_offset_max_ft': r(max(offsets)), 'routes_over_5ft_from_canonical': far,
                   'detail': route_rows},
        'b101_v4': {
            'calibration_report_states_pass': 'Static route/network validation: PASS' in b101_md,
            'new_main_plan_length_ft': 27.40, 'retained_prior_abs_plan_length_ft': 26.83,
            'scope_correction': 'Previously repaired kitchen/dining 4in ABS is retained, not new work (B101 v4).',
            'vdc_b101_new_lf': r(new_lf['B101']), 'canonical_b101_lf': r(canon_lf['B101']),
            'control_points': len(controls),
            'control_offset_ft_by_role': {k: {'n': len(v), 'median': r(statistics.median(v)), 'max': r(max(v))}
                                          for k, v in sorted(control_offsets.items())},
        },
        'schedule': {
            'vdc': {'id': 'MEYD-BL-001', 'activities': len(schedule), 'working_days': vdc_days,
                    'start': schedule[0]['Start'], 'finish': schedule[-1]['Finish'],
                    'structure': 'eight serial project-wide phases; retimes the existing 672-frame animation'},
            'canonical': {'activities': len(state['activities']), 'working_days': meta['working_days'],
                          'calendar_days_approx': meta['calendar_days_approx'],
                          'structure': 'eight activities per unit, four units chained; S2 @ 3.5 ft strawman'},
            'comparable': False,
            'why': 'Different structure (project-wide phases vs unit-by-unit occupied sequence) and different '
                   'scope, crew and occupancy assumptions. Neither duration is an alternative to the other until '
                   'those assumptions are reconciled.',
        },
        'issues': {
            'vdc': [{k: row[k] for k in ('issue_id', 'severity', 'category', 'status', 'unit', 'element_name')}
                    for row in issues],
            'canonical': [{k: i[k] for k in ('id', 'title', 'severity', 'resolution_status')} for i in state['issues']],
        },
        'scope_coverage': {
            'vdc_only': sorted({row['Component Type'] for row in takeoff} - {'PIPE_ROUTE', 'SLAB_CUT_AREA',
                                                                             'BEDDING_VOLUME', 'BACKFILL_VOLUME'}),
            'canonical_only': ['S1/S2/S3 trench scenarios', 'allowance decisions', 'logistics haul routes',
                               'unit-by-unit occupied sequence'],
        },
        'notice': 'Illustrative, not a contract document. Recovered data is provisional or assumed as labelled in '
                  'its sources; nothing here is field-verified.',
    }
    text = json.dumps(report, indent=2) + '\n'
    if args.check:
        if not REPORT.exists() or REPORT.read_text() != text:
            raise SystemExit('reconciliation.json is stale; run reconcile.py')
    else:
        REPORT.parent.mkdir(parents=True, exist_ok=True)
        REPORT.write_text(text)
    t = report['totals']
    print(f"RECONCILED {report['recovered_files']} files — new ABS {t['new_abs_lf']['vdc']} vs "
          f"{t['new_abs_lf']['canonical']} LF ({t['new_abs_lf']['delta_pct']}%)")


if __name__ == '__main__':
    sys.exit(main())
