"""`bm doctor`: what this machine can and cannot do, and the exact fix for each gap.

Agents should run it first: it explains failures that otherwise surface as deep tracebacks
(bpy missing X11 libraries, LFS pointers instead of files, absent source PDFs, no gh auth).
No bpy import in this process; bpy is probed in a subprocess.
"""
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from bmodels import project
from bmodels.paths import ROOT

LFS_POINTER = b"version https://git-lfs.github.com/spec/v1"
X11 = "libx11-6 libxrender1 libxfixes3 libxi6 libxext6 libxkbcommon0 libsm6 libice6 libgl1"
# Stable Ubuntu/Debian package names; Playwright resolves release-specific names such as libasound2[t64].
CHROMIUM_LIBS = {"libnss3.so": "libnss3", "libnssutil3.so": "libnss3", "libsmime3.so": "libnss3",
                 "libnspr4.so": "libnspr4", "libplc4.so": "libnspr4", "libplds4.so": "libnspr4"}
PLAYWRIGHT_PRODUCT = Path("projects/highland/products/water")
PLAYWRIGHT_SETUP = f"cd {PLAYWRIGHT_PRODUCT} && npm ci"
PLAYWRIGHT_INSTALL = f"{PLAYWRIGHT_SETUP} && npx playwright install chromium"
PLAYWRIGHT_DEPS = f"{PLAYWRIGHT_SETUP} && npx playwright install-deps chromium"


def _run(*cmd):
    try:
        p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=False, timeout=120)
    except (OSError, subprocess.TimeoutExpired) as e:
        return 1, str(e)
    return p.returncode, (p.stdout + p.stderr).strip()


def playwright_chromium():
    """Film's explicit override, or the headless shell required by its installed Playwright."""
    if binary := os.environ.get("CHROMIUM_PATH"):
        return ROOT / binary
    core = ROOT / PLAYWRIGHT_PRODUCT / "node_modules/playwright-core"
    try:
        browsers = json.loads((core / "browsers.json").read_text())["browsers"]
        revision = next(b["revision"] for b in browsers if b["name"] == "chromium-headless-shell")
    except (OSError, UnicodeError, ValueError, KeyError, TypeError, StopIteration):
        return None
    if not re.fullmatch(r"\d+", str(revision)):
        return None
    configured = os.environ.get("PLAYWRIGHT_BROWSERS_PATH")
    if configured == "0":
        cache = core / ".local-browsers"
    elif configured:
        cache = Path(os.environ.get("INIT_CWD") or ROOT) / configured
    else:
        cache = Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache") / "ms-playwright"
    shells = cache.glob(f"chromium_headless_shell-{revision}/chrome-headless-shell-*/chrome-headless-shell")
    return next((p for p in shells if p.is_file()), None)


def missing_libs(ldd_output):
    """Library names `ldd` reports as 'not found'."""
    return sorted(set(re.findall(r"^\s*(\S+)\s+=>\s+not found\s*$", ldd_output, re.MULTILINE)))


def chromium_fix(libs):
    if any(lib not in CHROMIUM_LIBS for lib in libs):
        return PLAYWRIGHT_DEPS
    pkgs = sorted({CHROMIUM_LIBS[lib] for lib in libs if lib in CHROMIUM_LIBS})
    return f"sudo apt-get install -y {' '.join(pkgs)}" if pkgs else ""


def chromium_check():
    """Check shared libraries without launching a browser or importing bpy."""
    name = "Playwright Chromium libraries"
    blocks = "Playwright films, viewer previews and browser checks (bm run highland/water video; highland/repipe video)"
    if not sys.platform.startswith("linux"):
        return name, True, "not Linux; library check skipped", PLAYWRIGHT_INSTALL, blocks
    shell = playwright_chromium()
    install = ("unset CHROMIUM_PATH && " if os.environ.get("CHROMIUM_PATH") else "") + PLAYWRIGHT_INSTALL
    if shell is None:
        return name, False, "no Playwright Chromium matching the product metadata; run the install step", install, blocks
    if shutil.which("ldd") is None:
        return name, False, "ldd is not on PATH", "sudo apt-get install -y libc-bin", blocks
    code, msg = _run("ldd", str(shell))
    libs = missing_libs(msg)
    if libs:
        return name, False, f"{shell.name}: missing {', '.join(libs)}", chromium_fix(libs), blocks
    if code:
        return name, False, f"ldd failed for {shell}: {msg}", install, blocks
    return name, True, f"{shell}: shared libraries resolved (launch not tested)", install, blocks


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

    out.append(chromium_check())

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
        print(json.dumps([{"check": n, "ok": ok, "detail": d, "fix": f, "without_it": b}
                          for n, ok, d, f, b in results], indent=2))
    else:
        for n, ok, d, f, b in results:
            print(f"{'ok  ' if ok else 'MISS'}  {n}" + (f" — {d}" if d else ""))
            if not ok:
                print(f"        fix: {f}\n        without it: {b}")
    required = {"python 3.11", "uv.lock matches pyproject.toml"}
    return 1 if any(not ok and n in required for n, ok, *_ in results) else 0
