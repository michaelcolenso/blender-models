"""{{name}}: replace with the product's pipeline. `--check` must be fast, CPU-only and need no source PDFs."""
import argparse

from bmodels.paths import ROOT

OUT = ROOT / "build" / "{{site}}" / "{{name}}"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true", help="validate committed inputs/outputs only")
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    print(f"{'check' if a.check else 'build'}: nothing to do yet ({OUT})")


if __name__ == "__main__":
    main()
