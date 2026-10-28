"""Repo checks behind `bm check`: spec provenance, site/product metadata, file sizes, markdown links."""
import fnmatch
import re
import subprocess

import yaml

from bmodels import project, spec
from bmodels.paths import ROOT

CONFIG = ROOT / ".bmcheck.yaml"
LINK = re.compile(r'\]\(<?([^)\s>]+)>?(?:\s+"[^"]*")?\)')


def config():
    return yaml.safe_load(CONFIG.read_text()) if CONFIG.exists() else {}


def _git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout.split("\n")


def specs():
    errors = []
    for sp in project.all_specs():
        try:
            errs = spec.check(spec.load(sp))
        except (yaml.YAMLError, KeyError, TypeError, AttributeError) as e:  # malformed YAML / missing top-level keys
            errs = [f"unreadable: {e}"]
        errors += [f"{sp.relative_to(ROOT)}: {e}" for e in errs]
    return errors


def metadata():
    errors = []
    for s in project.sites():
        if not s.meta.get("name"):
            errors.append(f"{s.dir.relative_to(ROOT)}/project.yaml: needs 'name'")
        for p in s.products:
            where = f"{p.dir.relative_to(ROOT)}/product.yaml"
            if not p.meta.get("kind"):
                errors.append(f"{where}: needs 'kind'")
            steps = p.meta.get("steps") or {}
            if not isinstance(steps, dict) or not steps:
                errors.append(f"{where}: needs 'steps' (name -> command or list of commands)")
            elif "check" not in steps and not p.meta.get("check_unavailable"):
                errors.append(f"{where}: needs a `check` step (CPU, no source PDFs; CI runs it) "
                              "or `check_unavailable: <reason>`")
            for name, cmd in (steps.items() if isinstance(steps, dict) else []):
                if not (isinstance(cmd, str) or (isinstance(cmd, list) and all(isinstance(c, str) for c in cmd))):
                    errors.append(f"{where}: step '{name}' must be a command or list of commands")
    return errors


def changed_files(staged=False, base=None):
    """(status, path) for added (A) or modified (M) files: staged ones, or the diff since base."""
    if staged:
        out = _git("diff", "--cached", "--name-status", "--diff-filter=AM")
    elif base:
        out = _git("diff", "--name-status", "--diff-filter=AM", f"{base}...HEAD")
    else:
        return []
    return [tuple(line.split("\t", 1)) for line in out if line]


def large_files(files):
    """Files over the limit. Updates to files already in Git LFS pass; new ones go to Releases."""
    cfg = config()
    limit = cfg.get("large_file_mb", 1) * 1024 * 1024
    allow = cfg.get("large_file_allow") or []
    errors = []
    for status, f in (x if isinstance(x, tuple) else ("A", x) for x in files):
        p = ROOT / f
        if not p.is_file() or p.stat().st_size <= limit or any(fnmatch.fnmatch(f, g) for g in allow):
            continue
        if status == "M" and _git("check-attr", "filter", "--", f)[0].endswith(": lfs"):
            continue
        errors.append(f"{f}: {p.stat().st_size / 1e6:.1f} MB — publish with `bm publish <site>/<product> <file>` "
                      "and link the release, or add to large_file_allow in .bmcheck.yaml with a reason")
    return errors


def links():
    allow = set(config().get("broken_link_allow") or [])
    errors = []
    for f in _git("ls-files", "*.md"):
        if not f or f in allow or f.startswith("templates/"):  # templates hold {{placeholder}} links
            continue
        text = re.sub(r"```.*?```", "", (ROOT / f).read_text(errors="ignore"), flags=re.DOTALL)
        for m in LINK.finditer(text):
            url = m.group(1)
            if re.match(r"[a-z][a-z0-9+.-]*:", url) or url.startswith("#"):
                continue
            target = url.split("#")[0].split("?")[0]
            if target and not (ROOT / f).parent.joinpath(target).exists():
                errors.append(f"{f}: broken link {url}")
    return errors
