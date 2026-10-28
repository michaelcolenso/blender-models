"""`bm doctor`: what this machine can and cannot do, and the exact fix for each gap.

Agents should run it first: it explains failures that otherwise surface as deep tracebacks
(bpy missing X11 libraries, LFS pointers instead of files, absent source PDFs, no gh auth).
No bpy import in this process; bpy is probed in a subprocess.
"""
import shutil
import subprocess
import sys

from bmodels import project
from bmodels.paths import ROOT

LFS_POINTER = b"version https://git-lfs.github.com/spec/v1"
X11 = "libx11-6 libxrender1 libxfixes3 libxi6 libxext6 libxkbcommon0 libsm6 libice6 libgl1"


def _run(*cmd):
    try:
        p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=False, timeout=120)
    except (OSError, subprocess.TimeoutExpired) as e:
        return 1, str(e)
    return p.returncode, (p.stdout + p.stderr).strip()


def checks():
    """(name, ok, detail, fix, blocks) — blocks says what fails without it."""
    out = []
    ok = sys.version_info[:2] == (3, 11)
    out.append(("python 3.11", ok, sys.version.split()[0], "uv sync", "everything"))

    code, msg = _run(sys.executable, "-c", "import bpy; print(bpy.app.version_string)")
    detail = msg.splitlines()[-1] if msg else ""
    fix = f"sudo apt-get install -y {X11}" if "lib" in detail and ".so" in detail else "uv sync"
    out.append(("bpy imports", code == 0, detail, fix,
                "bm build, check-products steps that use bpy, renders, audit-blends — CI still runs them"))

    code, msg = _run("uv", "lock", "--check")
    out.append(("uv.lock matches pyproject.toml", code == 0, "" if code == 0 else msg.splitlines()[-1],
                "uv lock && uv sync", "CI (checks workflow)"))

    hook = (ROOT / ".git/hooks/pre-commit")
    out.append(("pre-commit hook", hook.exists() and "pre-commit" in hook.read_text(errors="ignore"), "",
                "uvx pre-commit install", "local large-file/provenance guard (CI still checks)"))

    code, msg = _run("gh", "auth", "status")
    out.append(("gh authenticated", code == 0, "" if code == 0 else msg.splitlines()[0] if msg else "gh missing",
                "gh auth login", "bm publish, bm assets pull (releases), PR/CI inspection"))

    pointers = []
    out_ls = _run("git", "lfs", "ls-files", "-n")
    lfs = shutil.which("git-lfs") is not None
    if lfs and out_ls[0] == 0:
        for f in out_ls[1].splitlines():
            p = ROOT / f
            if p.is_file() and p.read_bytes()[:len(LFS_POINTER)] == LFS_POINTER:
                pointers.append(f)
    else:
        code, files = _run("git", "ls-files", "*.blend", "*.mp4", "*.zip", "*.pdf")
        for f in files.splitlines():
            p = ROOT / f
            if p.is_file() and p.stat().st_size < 200 and p.read_bytes()[:len(LFS_POINTER)] == LFS_POINTER:
                pointers.append(f)
    out.append(("LFS files present (not pointers)", not pointers,
                f"{len(pointers)} pointer files, e.g. {pointers[0]}" if pointers else "",
                "sudo apt-get install -y git-lfs && git lfs pull" if not lfs else "git lfs pull",
                "opening those .blend/.mp4 files, installation asset restore"))

    for tool, blocks in [("ffmpeg", "film encodes and video checks"), ("node", "browser viewers and Playwright films"),
                         ("npm", "viewer bundles")]:
        out.append((f"{tool} on PATH", shutil.which(tool) is not None, "", f"install {tool}", blocks))

    code, _ = _run("nvidia-smi")
    out.append(("NVIDIA GPU", code == 0, "", "use RunPod: products/*/runpod_*.sh",
                "GPU Cycles renders (CPU Cycles still works)"))

    missing = []
    for s in project.sites():
        src = s.dir / "sources"
        files = [p for p in src.glob("**/*") if p.is_file() and p.name != "manifest.json"] if src.exists() else []
        if not files:
            missing.append(s.name)
    out.append(("source drawings/photos present", not missing,
                f"none in sources/ for: {', '.join(missing)}" if missing else "",
                "copy them into projects/<site>/sources/ (never committed)",
                "prepare/extract steps that read PDFs; committed specs and takeoff still build"))
    return out


def main(json_out=False):
    results = checks()
    if json_out:
        import json
        print(json.dumps([{"check": n, "ok": ok, "detail": d, "fix": f, "without_it": b}
                          for n, ok, d, f, b in results], indent=2))
    else:
        for n, ok, d, f, b in results:
            print(f"{'ok  ' if ok else 'MISS'}  {n}" + (f" — {d}" if d else ""))
            if not ok:
                print(f"        fix: {f}\n        without it: {b}")
    required = {"python 3.11", "uv.lock matches pyproject.toml"}
    return 1 if any(not ok and n in required for n, ok, *_ in results) else 0
