"""Check the showcase shot list (bpy-free, runs in the root environment and in CI).

  python projects/highland/products/showcase/build.py --check
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BEAT = 60/80  # seconds per beat at 80 BPM
FORBIDDEN = ('highland', '200 w', 'a2.', 'a3.', 'p2.', 'p3.', 'seattle')  # generalized: nothing identifying on screen


def check():
    spec = json.loads((HERE/'shots.json').read_text())
    errors = []
    total = 0.
    for m in spec['movements']:
        for key in ('id', 'seconds', 'title', 'picture', 'features'):
            if key not in m:
                errors.append(f"{m.get('id')}: missing {key}")
        beats = m['seconds']/BEAT
        if abs(beats-round(beats)) > 1e-6:
            errors.append(f"{m['id']}: {m['seconds']} s is not a whole number of beats")
        on_screen = (m['title']+' '+m['picture']).lower()
        errors += [f"{m['id']}: identifying text '{w}' on screen" for w in FORBIDDEN if w in on_screen]
        total += m['seconds']
    if not 45 <= total <= 75:
        errors.append(f'runtime {total} s outside 45-75 s')
    for e in errors:
        print('FAIL', e)
    print(f"{len(spec['movements'])} movements, {total:.1f} s" + ('' if errors else ', ok'))
    return not errors


if __name__ == '__main__':
    sys.exit(0 if check() else 1)
