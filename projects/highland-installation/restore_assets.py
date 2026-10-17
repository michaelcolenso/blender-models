"""Restore large project inputs from the checksum-verified delivery ZIPs."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

ROOT = Path(__file__).resolve().parent


def digest(path):
    result = hashlib.sha256()
    with path.open('rb') as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            result.update(chunk)
    return result.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        'asset_directory', nargs='?', type=Path,
        default=ROOT.parent.parent / 'deliverables/highland-installation/assets',
        help='Directory containing both ZIPs (default: the Git LFS delivery assets)',
    )
    args = parser.parse_args()
    manifest = json.loads((ROOT / 'release-assets.json').read_text())
    records = {asset['name']: asset for asset in manifest['assets']}
    installation = [
        'Highland-installation-unit-B.blend',
        'Highland-installation-shared.blend',
        'Highland-installation-unit-B.glb',
        'Highland-installation-shared.glb',
        'Highland-installation-storyboard.pdf',
        'Highland-installation-sequence.mp4',
    ]
    animation = [
        'Highland-repipe-90s.blend',
        'Highland-repipe-storyboard.pdf',
        'audio/mix.wav',
        'audio/narration.wav',
        'audio/original-score.wav',
    ]
    archives = {
        'Highland-installation-model.zip': {
            'Highland-original.pdf': 'Highland-original.pdf',
            **{'Highland-installation/' + name: 'installation/' + name for name in installation},
        },
        'Highland-repipe-animation-editable.zip': {
            'Highland-repipe/animation-90s/' + name: 'animation-90s/' + name
            for name in animation
        },
    }

    # Verify every archive and conflict before writing any asset. Only explicitly
    # listed members are used; archive filenames never determine output paths.
    for name, members in archives.items():
        path = args.asset_directory / name
        record = records[name]
        if path.stat().st_size != record['bytes'] or digest(path) != record['sha256']:
            raise ValueError(f'Release checksum mismatch: {name}')
        with zipfile.ZipFile(path) as archive:
            for member, relative in members.items():
                info = archive.getinfo(member)
                target = ROOT / relative
                if target.exists():
                    with archive.open(info) as source:
                        expected = hashlib.file_digest(source, 'sha256').hexdigest()
                    if digest(target) != expected:
                        raise FileExistsError(f'Preserving a modified local asset: {target}')

    restored = 0
    for name, members in archives.items():
        with zipfile.ZipFile(args.asset_directory / name) as archive:
            for member, relative in members.items():
                target = ROOT / relative
                if target.exists():
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                temporary = target.with_name(target.name + '.part')
                try:
                    with archive.open(member) as source, temporary.open('xb') as output:
                        shutil.copyfileobj(source, output)
                    temporary.replace(target)
                finally:
                    temporary.unlink(missing_ok=True)
                restored += 1
    print(f'Release archives verified; restored {restored} assets. Existing matching assets preserved.')


if __name__ == '__main__':
    main()
