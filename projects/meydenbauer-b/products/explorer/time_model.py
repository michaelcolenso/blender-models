"""Export a browser projection of canonical state; construction math stays upstream."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from bmodels.paths import ROOT

HERE = Path(__file__).resolve().parent
STATE = ROOT / "projects/meydenbauer-b/state/project-state.json"
OUT = HERE / "time-state.json"


def build_projection(state=None) -> dict:
    state = state if state is not None else json.loads(STATE.read_text())
    return {**state["metadata"]["timeline"], "scenarios": state["metadata"]["decisions"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    content = json.dumps(build_projection(), indent=2) + "\n"
    if args.check:
        if OUT.read_text() != content:
            raise SystemExit("time-state.json drift; regenerate with time_model.py")
        print("ok canonical time projection")
    else:
        OUT.write_text(content)
        print(f"wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
