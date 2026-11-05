"""VDC scope quantities adopted into canonical state (owner decision, 2026-11-05).

Read by `state/build_from_artifacts.py`. Returns per-unit quantities for scope items the
canonical under-slab takeoff does not carry, summed from the VDC phase-4 element-level
takeoff backing joined to the element register's status. Snapshot hashes are verified first.

Adopted (work items only): fixtures/casework/finishes reinstalled; new cleanouts, firestops,
fittings and framing; new patch area; wall-opening demolition; temporary protection.

Not adopted, and why:
- Route-geometry quantities (pipe, slab cut, bedding, backfill, pourback, vapor barrier,
  hydro-test and installation segments, inspection paths, tracer wire): canonical computes
  these from its own P1.02 geometry and S1/S2/S3 scenarios.
- Context objects (slab, walls, soil, footings, reinforcement, in-slab utilities, coatings,
  membranes, staging, callouts) and EXISTING_REMAIN items: not scope.
- Fittings measured in FT (P-traps as curve length): not a usable takeoff unit.
- Anything on the B103 raised-floor route, including the sleeve PIPE_SLEEVE line: excluded by
  owner decision (route not in scope).

VDC modeled a typical unit: most of these values are identical in all four units, so they are
templated counts, carried as ASSUMED / low confidence, not unit-specific takeoffs.
"""
import csv
import importlib.util
import io
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
BACKING = 'deliverables/meydenbauer-b/vdc/Meydenbauer_VDC_Phase4_Takeoff_Backing.csv'
REGISTER = 'deliverables/meydenbauer-b/vdc/Meydenbauer_VDC_Element_Register.csv'
RAISED_FLOOR = 'NEW_ABS_B103_4in_RAISED_FLOOR'

# (component_type, register status, unit of measure) -> canonical measure
ADOPTED = {
    ('FIXTURE', 'REINSTALLED', 'EA'): 'fixtures_reinstalled',
    ('CASEWORK', 'REINSTALLED', 'EA'): 'casework_reinstalled',
    ('FINISH', 'REINSTALLED', 'EA'): 'finishes_reinstalled',
    ('CLEANOUT', 'NEW', 'EA'): 'cleanouts_new',
    ('FIRESTOP', 'NEW', 'EA'): 'firestops_new',
    ('FITTING', 'NEW', 'EA'): 'fittings_new',
    ('FRAMING_MEMBER', 'NEW', 'EA'): 'framing_members_new',
    ('PATCH_AREA', 'NEW', 'SF'): 'patch_area_new',
    ('WALL_OPENING_AREA', 'DEMOLITION', 'SF'): 'wall_opening_demolition',
    ('PROTECTION_AREA', 'TEMPORARY', 'SF'): 'protection_area_temporary',
}


def _reconcile():
    spec = importlib.util.spec_from_file_location('vdc_reconcile', HERE / 'reconcile.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def scope_quantities():
    """[(unit 'B101', measure, value, uom)], evidence checksums {source_path: sha256}."""
    recovery, data = _reconcile().load_snapshots()  # raises on any snapshot drift
    sha = {row['source_path'].split('/', 3)[-1]: row['sha256'] for row in recovery['files']}
    register = {row['element_id']: row for row in csv.DictReader(io.StringIO(data[('vdc', REGISTER.split('/', 3)[-1])].decode()))}
    backing = csv.DictReader(io.StringIO(data[('vdc', BACKING.split('/', 3)[-1])].decode()))
    totals = defaultdict(float)
    for row in backing:
        element = register.get(row['Element ID'])
        if element is None or RAISED_FLOOR in (element['name'], element['parent_route_name']):
            continue  # no register entry (the phase-2 sleeve) or on the excluded route
        measure = ADOPTED.get((element['component_type'], element['status'], row['Qty Unit']))
        if measure:
            totals[(element['unit'], measure, row['Qty Unit'])] += float(row['Qty'])
    rows = [(unit, measure, round(value, 4), uom) for (unit, measure, uom), value in sorted(totals.items())]
    evidence = {path: sha[path.split('/', 3)[-1]] for path in (BACKING, REGISTER)}
    return rows, evidence
