"""Compile an editable video recipe into exact frame/chunk assignments."""
import argparse
import json
from pathlib import Path

from video_common import PROFILES, compile_plan


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("recipe")
    parser.add_argument("--profile", choices=PROFILES, default="storyboard")
    parser.add_argument("--shot", default="all")
    parser.add_argument("--sample-seconds", type=float)
    parser.add_argument("--chunk-size", type=int, default=48)
    parser.add_argument("--device", choices=("CPU", "OPTIX", "CUDA"), default="CPU")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--github-output", type=Path)
    args = parser.parse_args()
    plan = compile_plan(args.recipe, args.profile, args.shot, args.sample_seconds, args.chunk_size, args.device)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(plan, indent=2) + "\n")
    print(f"{plan['recipe']['id']}: {len(plan['frames'])} native frames, {len(plan['chunks'])} chunks; {plan['profile']}")
    if args.github_output:
        matrix = {"include": [{"chunk": c["id"]} for c in plan["chunks"]]}
        with args.github_output.open("a") as stream:
            stream.write("matrix=" + json.dumps(matrix, separators=(",", ":")) + "\n")


if __name__ == "__main__":
    main()
