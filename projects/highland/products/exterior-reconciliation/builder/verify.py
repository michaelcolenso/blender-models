"""Compare the rebuilt revision 06 scene with the historical delivery records.

Run after build.py and validate.py. Passes only when:
- every "verbatim" builder file is still byte-identical to its archived blob;
- the base scene inventory and all 960 rebuilt architecture mesh hashes equal the
  historical geometry-validation.json (which embeds the 97 north, 815 revision 05
  and 99 R5 controls checked by validate.py);
- every field of the historical delivery-validation.json is reproduced, except the
  saved .blend/.glb file hashes (they embed write metadata) and the PDF hashes when
  the git-ignored PDFs are absent (CI).

Writes a stable summary to deliverables/exterior-reconciliation/native-check.json;
the product check regenerates it and requires no diff.
"""
import hashlib
import json
import sys

import paths

FILE_HASH_FIELDS = {'native_sha256', 'glb_sha256'}
REPORT = paths.PRODUCT.parent.parent / 'deliverables/exterior-reconciliation/native-check.json'


def load(path):
    return json.loads(path.read_text())


def main():
    failures = []
    inputs = load(paths.HERE / 'inputs.json')
    for row in inputs['files']:
        if row['state'] != 'verbatim':
            continue
        data = (paths.HERE / row['file']).read_bytes()
        if (len(data), hashlib.sha256(data).hexdigest()) != (row['bytes'], row['sha256']):
            failures.append(f"verbatim file drifted: {row['file']}")

    old_geometry = load(paths.INPUTS / 'historical-geometry-validation.json')
    new_geometry = load(paths.OUT / 'geometry-validation.json')
    for key in ('before', 'after'):
        old, new = old_geometry[key], new_geometry[key]
        changed = sorted(n for n in old.keys() | new.keys() if old.get(n) != new.get(n))
        if changed:
            failures.append(f"{key}: {len(changed)} mesh hashes differ, e.g. {changed[:5]}")
    for key in ('base_native_sha256', 'base_meshes', 'revised_meshes', 'unchanged_meshes', 'changed_existing',
                'removed', 'added', 'allowed_existing', 'revised_spec_sha256'):
        if old_geometry[key] != new_geometry[key]:
            failures.append(f"geometry-validation.{key} differs")

    old_delivery = load(paths.INPUTS / 'historical-delivery-validation.json')
    new_delivery = load(paths.OUT / 'delivery-validation.json')
    # Compared every run; the PDF hashes only where the git-ignored PDFs are present, so the
    # tracked report below is identical with or without them.
    compared = set(old_delivery) - FILE_HASH_FIELDS - {'source_pdf_sha256'}
    for key in sorted(compared):
        if old_delivery[key] != new_delivery.get(key):
            failures.append(f"delivery-validation.{key} differs")
    for name, value in new_delivery['source_pdf_sha256'].items():
        if value not in ('not present', old_delivery['source_pdf_sha256'][name]):
            failures.append(f"source PDF hash differs: {name}")

    if failures:
        print('NATIVE CHECK FAIL', *failures, sep='\n  ', file=sys.stderr)
        raise SystemExit(1)

    north = load(paths.NORTH_BASELINE)['mesh_hashes']
    rev05 = load(paths.REVISION05_CONTROLS)['mesh_hashes']
    stage1 = load(paths.STAGE1_BASELINE)['core_mesh_hashes']
    after = new_geometry['after']
    report = {
        'status': 'PASS',
        'scope': 'native rebuild of revision 06 from recovered inputs, compared with the historical delivery records',
        'base_scene_sha256': new_geometry['base_native_sha256'],
        'revised_spec_sha256': new_geometry['revised_spec_sha256'],
        'architecture_meshes_rebuilt': len(after),
        'architecture_mesh_hashes_identical_to_historical': len(after),
        'architecture_inventory_sha256': hashlib.sha256(
            json.dumps(after, sort_keys=True, separators=(',', ':')).encode()).hexdigest(),
        'protected_controls_identical': {
            'revision04_north': sum(after.get(n) == h for n, h in north.items()),
            'revision05': sum(after.get(n) == h for n, h in rev05.items()),
            'stage1_r5_core': sum(after.get(n) == h for n, h in stage1.items()),
        },
        'delivery_validation_fields_reproduced': len(compared),
        'delivery_validation_fields_not_compared': sorted(FILE_HASH_FIELDS),
        'source_pdf_hashes': 'compared when the git-ignored PDFs are present in projects/highland/sources/',
        'verbatim_builder_files_checked': sum(row['state'] == 'verbatim' for row in inputs['files']),
        'not_established': [
            'dimensional accuracy (source XY provisional; complete openings, guards and sections assumed)',
            'north stair/MU alignment and R1 north entries (owner-deferred)',
            'visual review of this rebuild (see README for what was inspected and when)',
        ],
        'notice': 'Illustrative, not a contract document.',
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2) + '\n')
    print(f"NATIVE CHECK PASS — {len(after)}/{len(after)} mesh hashes, {len(compared)} delivery fields reproduced")


if __name__ == '__main__':
    main()
