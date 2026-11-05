"""One-off: copy the small VDC and B101 v4 data byte-for-byte from the archive tags.

    git fetch origin tag archive/2026-11-03/meydenbauer/4d-fixes tag archive/2026-11-03/meydenbauer/b101-v4-executed
    uv run python projects/meydenbauer-b/products/vdc-recovery/recover.py

Only text data (CSV/JSON/Markdown/text/scripts/logs) is recovered. Saved .blend scenes,
renders and .xlsx workbooks stay in the archive tags (sizes listed in recovery.json).
Files over 1 MB are stored gzip-compressed; their recorded hashes are of the original bytes.
The archived `sources/` folder is stored as `archived-sources/` (repo-wide `sources/` is git-ignored).
`check.py` verifies every snapshot against recovery.json without network or the tags.
"""
import gzip
import hashlib
import json
import subprocess
from pathlib import Path

from bmodels.paths import ROOT

HERE = Path(__file__).resolve().parent
SOURCES = {
    'vdc': ('archive/2026-11-03/meydenbauer/4d-fixes', '87d21bf145100fe7d95f3aeba7db95b822aa5764',
            'deliverables/meydenbauer-b/vdc'),
    'b101': ('archive/2026-11-03/meydenbauer/b101-v4-executed', '70fc8d60ef50006c27222ad7fbd50bf519815cac',
             'deliverables/meydenbauer-b/b101-v4'),
}
TEXT = {'.csv', '.json', '.md', '.txt', '.py', '.log', '.sha256', '.sh', '.ps1', '.bat'}
LIMIT = 1_000_000


def git(*args):
    return subprocess.run(['git', *args], cwd=ROOT, check=True, capture_output=True).stdout


def main():
    files, left = [], []
    for key, (tag, commit, prefix) in SOURCES.items():
        assert git('rev-parse', f'{tag}^{{commit}}').decode().strip() == commit, tag
        for line in git('ls-tree', '-r', '-l', commit, prefix).decode().splitlines():
            meta, path = line.split('\t')
            _, _, blob, size = meta.split()
            rel = path[len(prefix) + 1:]
            if Path(rel).suffix.lower() not in TEXT or int(size) == 0:
                left.append({'source': key, 'path': path, 'bytes': int(size), 'git_blob_sha': blob})
                continue
            data = git('cat-file', 'blob', blob)
            # `sources/` folders are git-ignored repo-wide (drawing PDFs); keep the archived one tracked.
            rel = rel.replace('sources/', 'archived-sources/', 1) if rel.startswith('sources/') else rel
            target = HERE / 'snapshots' / key / rel
            stored = 'raw'
            if len(data) > LIMIT:
                target, stored = target.with_name(target.name + '.gz'), 'gzip'
                payload = gzip.compress(data, compresslevel=9, mtime=0)
            else:
                payload = data
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(payload)
            files.append({'file': target.relative_to(HERE).as_posix(), 'source': key, 'source_path': path,
                          'git_blob_sha': blob, 'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data),
                          'stored': stored})
    record = {'schema_version': 1,
              'sources': {k: {'tag': t, 'commit': c, 'prefix': p} for k, (t, c, p) in SOURCES.items()},
              'note': 'Byte-identical recovered text data. Hashes are of the original bytes (before gzip).',
              'files': files, 'left_in_archive': left}
    (HERE / 'recovery.json').write_text(json.dumps(record, indent=2) + '\n')
    print(f'recovered {len(files)} files; left in archive {len(left)} '
          f'({sum(x["bytes"] for x in left) / 1e6:.0f} MB)')


if __name__ == '__main__':
    main()
