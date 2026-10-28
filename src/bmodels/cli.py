"""`bm` — one entry point for every construction project in the repo.

    bm list [--markdown]                       sites, specs and products
    bm new <site> [--type element|detail]      start a site from templates/project
    bm build [target ...] [--changed BASE]     build + verify specs (path, site, or site/spec)
    bm run <site>/<product> <step> [args]      run a product step from its product.yaml
    bm check-products [--changed BASE]         run every product's `check` step (CI)
    bm assets pull|verify|push <manifest> ...  release assets with checksums
    bm publish <site>/<product> <file ...>     upload outputs to the product's GitHub Release
    bm check [--staged | --base REF]           specs, metadata, large files, links, tests
    bm <tool> [args]                           calibrate, extract, overlay, detail-overlay, render,
                                               render-plan, animate-house, animate-sequence,
                                               room, skp, usdz, audit-blends

Run through uv: `uv run bm …`. Nothing here imports bpy; Blender work runs in a subprocess.
"""
import argparse
import json
import os
import shlex
import subprocess
import sys
from datetime import date
from pathlib import Path

from bmodels import assets, checks, project, spec
from bmodels.paths import PROJECTS, ROOT, TEMPLATES

TOOLS = {  # bm <name> -> python -m bmodels.<module>
    "calibrate": "calibrate",
    "extract": "extract_plan",
    "overlay": "overlay",
    "detail-overlay": "detail_overlay",
    "render": "render_scene",
    "render-plan": "render_plan",
    "animate-house": "animate_house",
    "animate-sequence": "animate_sequence",
    "room": "room",
    "skp": "skp_code",
    "usdz": "export_usdz",
    "audit-blends": "blend_audit",
}
# Anything under these paths can change every build, so a change rebuilds every spec.
REBUILD_ALL = ("src/", "pyproject.toml", "uv.lock", ".github/")


def rel(p):
    p = Path(p).resolve()
    return p.relative_to(ROOT) if p.is_relative_to(ROOT) else p


# ----------------------------------------------------------------------------- list / new
def cmd_list(a):
    rows = []
    for s in project.sites():
        rows.append((s.name, s.meta.get("name", ""), [sp.stem for sp in s.specs], [p.name for p in s.products]))
    legacy = project.legacy_specs()
    if a.markdown:
        print("| Site | Name | Specs | Products |\n|---|---|---|---|")
        for site, name, sps, prods in rows:
            print(f"| [{site}](projects/{site}/) | {name} | {', '.join(sps) or '—'} | {', '.join(prods) or '—'} |")
        if legacy:
            print(f"| specs/ (unassigned) | | {', '.join(sp.stem for sp in legacy)} | |")
        return 0
    for site, name, sps, prods in rows:
        print(f"{site}  {name}")
        for sp in sps:
            print(f"  spec     {site}/{sp}  [{spec.kind(spec.load(PROJECTS / site / 'specs' / f'{sp}.yaml'))}]")
        for p in prods:
            print(f"  product  {site}/{p}")
    if legacy:
        print("specs/ (not yet assigned to a site)")
        for sp in legacy:
            print(f"  spec     {rel(sp)}  [{spec.kind(spec.load(sp))}]")
    return 0


def cmd_new(a):
    dest = PROJECTS / a.site
    if dest.exists():
        raise SystemExit(f"{rel(dest)} already exists")
    tpl = TEMPLATES / "project"
    fill = {"{{site}}": a.site, "{{name}}": a.name or a.site}

    def render(src, out):
        text = src.read_text()
        for k, v in fill.items():
            text = text.replace(k, v)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text)

    for src in tpl.rglob("*"):
        if src.is_dir() or src.parent.name == "specs":
            continue
        out = dest / src.relative_to(tpl)
        if src.name == ".gitkeep":
            out.parent.mkdir(parents=True, exist_ok=True)
            out.touch()
        else:
            render(src, out)
    render(tpl / "specs" / f"{a.type}.yaml", dest / "specs" / f"{a.site}-{a.type}.yaml")
    print(f"Created {rel(dest)}/ — fill project.yaml and sources/manifest.json, then edit "
          f"specs/{a.site}-{a.type}.yaml and run: uv run bm build {a.site}")
    return 0


# ----------------------------------------------------------------------------- build
def changed_specs(base):
    try:
        files = checks._git("diff", "--name-only", f"{base}...HEAD")
    except subprocess.CalledProcessError:
        files = checks._git("diff", "--name-only", base, "HEAD")
    files = [f for f in files if f]
    if any(f.startswith(REBUILD_ALL) for f in files):
        return project.all_specs()
    picked = set()
    for s in project.sites():
        d = str(rel(s.dir)) + "/"
        # specs read takeoff/sources data from anywhere in the site except products and deliverables
        if any(f.startswith(d) and not f.startswith((d + "products/", d + "deliverables/")) for f in files):
            picked.update(s.specs)
    picked.update(ROOT / f for f in files if f.startswith("specs/") and f.endswith(".yaml") and (ROOT / f).exists())
    return sorted(picked)


def cmd_build(a):
    specs = changed_specs(a.changed) if a.changed else project.resolve_specs(a.targets)
    if not specs:
        print("No specs to build.")
        return 0
    flags = (["--realistic"] if a.realistic else []) + (["--no-render"] if a.no_render else [])
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    failed = []
    for sp in specs:
        out = project.build_dir(sp)
        gh = bool(os.environ.get("GITHUB_ACTIONS"))
        print(f"::group::{rel(sp)}" if gh else f"== {rel(sp)} -> {rel(out)}/{sp.stem}/", flush=True)
        code = subprocess.run([sys.executable, "-m", "bmodels.build", str(sp), "--out", str(out), *flags], check=False).returncode
        if gh:
            print("::endgroup::")
        if code:
            failed.append(rel(sp))
        report = out / sp.stem / "report.md"
        if summary and report.exists():
            with open(summary, "a") as f:
                f.write(report.read_text() + "\n")
    print(f"\n{len(specs) - len(failed)}/{len(specs)} specs passed" + (f"; failed: {', '.join(map(str, failed))}" if failed else ""))
    return 1 if failed else 0


# ----------------------------------------------------------------------------- run / tools
def cmd_run(a):
    p = project.product(a.product)
    steps = p.meta.get("steps") or {}
    if a.step not in steps:
        raise SystemExit(f"{p.ref} has no step '{a.step}'. Steps: {', '.join(steps)}")
    cmds = steps[a.step] if isinstance(steps[a.step], list) else [steps[a.step]]
    env = {**os.environ, "BM_SITE": p.site.name, "BM_PRODUCT": p.name, "BM_PRODUCT_DIR": str(p.dir),
           "BM_BUILD": str(p.build), "BM_DELIVERABLES": str(p.deliverables)}
    for i, cmd in enumerate(cmds):
        if a.args and i == len(cmds) - 1:
            cmd += " " + " ".join(map(shlex.quote, a.args))
        print(f"$ {cmd}", flush=True)
        code = subprocess.run(["bash", "-c", cmd], cwd=ROOT, env=env, check=False).returncode
        if code:
            return code
    return 0


def cmd_check_products(a):
    products = [p for s in project.sites() for p in s.products if "check" in (p.meta.get("steps") or {})]
    if a.changed:
        files = [f for f in checks._git("diff", "--name-only", f"{a.changed}...HEAD") if f]
        if not any(f.startswith(REBUILD_ALL) for f in files):
            products = [p for p in products if any(f.startswith(f"{rel(p.dir)}/") for f in files)]
    failed = []
    for p in products:
        print(f"== {p.ref} check", flush=True)
        if cmd_run(argparse.Namespace(product=p.ref, step="check", args=[])):
            failed.append(p.ref)
    print(f"\n{len(products) - len(failed)}/{len(products)} product checks passed"
          + (f"; failed: {', '.join(failed)}" if failed else ""))
    return 1 if failed else 0


def run_tool(module, args):
    return subprocess.run([sys.executable, "-m", f"bmodels.{module}", *args], check=False).returncode


# ----------------------------------------------------------------------------- assets / check
def cmd_assets(a):
    if a.action == "verify":
        return 0 if assets.verify(a.manifest, a.from_dirs) else 1
    if a.action == "pull":
        assets.pull(a.manifest, a.names or None, a.from_dirs)
        return 0
    if not a.names:
        raise SystemExit("bm assets push <manifest> <file> [file ...]")
    assets.push(a.manifest, a.names)
    return 0


def cmd_publish(a):
    """Large outputs go to GitHub Releases, not git: upload, record checksums, print links."""
    p = project.product(a.product)
    manifest = p.dir / (p.meta.get("assets") or "release-assets.json")
    if not manifest.exists():
        repo = subprocess.run(["gh", "repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"],
                              cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
        prefix = p.site.meta.get("release_tag_prefix") or p.site.name
        tag = a.tag or f"{prefix}-{p.name}-{date.today().isoformat()}"
        assets.new_manifest(manifest, repo, tag)
        print(f"New release manifest {rel(manifest)} (tag {tag}); commit it with the README links below.")
    elif json.loads(manifest.read_text()).get("storage") == "git-lfs":
        raise SystemExit(f"{rel(manifest)} records Git LFS storage; new outputs go to Releases: pass a product "
                         "whose manifest uses storage 'release', or move this one over deliberately.")
    links = assets.push(manifest, a.files, title=f"{p.site.meta.get('name', p.site.name)} — {p.name}")
    print("\nMarkdown links:")
    for f, link in zip(a.files, links):
        print(f"- [{Path(f).name}]({link})")
    return 0


def cmd_check(a):
    sections = [("specs", checks.specs()), ("site/product metadata", checks.metadata())]
    files = checks.changed_files(a.staged, a.base)
    if a.staged or a.base:
        sections.append(("large files", checks.large_files(files)))
    if not a.staged:
        sections.append(("markdown links", checks.links()))
    failed = False
    for name, errors in sections:
        print(f"{'FAIL' if errors else 'ok  '}  {name}" + "".join(f"\n      {e}" for e in errors))
        failed |= bool(errors)
    if not a.no_tests and not a.staged:
        failed |= subprocess.run([sys.executable, "-m", "pytest", "-q"], cwd=ROOT, check=False).returncode not in (0, 5)
    return 1 if failed else 0


# ----------------------------------------------------------------------------- main
def parser():
    ap = argparse.ArgumentParser(prog="bm", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("list", help="sites, specs and products")
    p.add_argument("--markdown", action="store_true")
    p.set_defaults(fn=cmd_list)

    p = sub.add_parser("new", help="start a site from templates/project")
    p.add_argument("site", help="folder name, lowercase-hyphenated (e.g. qp-cottage-a)")
    p.add_argument("--name", help="display name (default: the site folder)")
    p.add_argument("--type", choices=["element", "detail"], default="element", help="starter spec")
    p.set_defaults(fn=cmd_new)

    p = sub.add_parser("build", help="build and verify specs")
    p.add_argument("targets", nargs="*", help="spec path, site, or site/spec (default: all)")
    p.add_argument("--changed", metavar="BASE", help="only specs affected by changes since BASE")
    p.add_argument("--realistic", action="store_true")
    p.add_argument("--no-render", action="store_true")
    p.set_defaults(fn=cmd_build)

    p = sub.add_parser("run", help="run a product step from its product.yaml")
    p.add_argument("product", help="site/product")
    p.add_argument("step")
    p.add_argument("args", nargs=argparse.REMAINDER, help="appended to the step's last command")
    p.set_defaults(fn=cmd_run)

    p = sub.add_parser("check-products", help="run every product's `check` step")
    p.add_argument("--changed", metavar="BASE", help="only products with changes since BASE")
    p.set_defaults(fn=cmd_check_products)

    p = sub.add_parser("assets", help="release assets with checksums")
    p.add_argument("action", choices=["pull", "verify", "push"])
    p.add_argument("manifest", type=Path)
    p.add_argument("names", nargs="*", help="pull: asset names (default all); push: files to upload")
    p.add_argument("--from", dest="from_dirs", action="append", default=[], metavar="DIR",
                   help="also look for verified copies here (e.g. manually downloaded ZIPs)")
    p.set_defaults(fn=cmd_assets)

    p = sub.add_parser("publish", help="upload outputs to the product's GitHub Release")
    p.add_argument("product", help="site/product")
    p.add_argument("files", nargs="+")
    p.add_argument("--tag", help="release tag for a new manifest (default <prefix>-<product>-<date>)")
    p.set_defaults(fn=cmd_publish)

    p = sub.add_parser("check", help="specs, metadata, large files, links, tests")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--staged", action="store_true", help="pre-commit: staged files only, fast checks")
    g.add_argument("--base", metavar="REF", help="CI: also check files added since REF")
    p.add_argument("--no-tests", action="store_true")
    p.set_defaults(fn=cmd_check)

    for name, module in TOOLS.items():  # listed for --help; dispatched in main() before parsing
        sub.add_parser(name, help=f"python -m bmodels.{module} (args passed through)")
    return ap


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv and argv[0] in TOOLS:
        return run_tool(TOOLS[argv[0]], argv[1:])
    a = parser().parse_args(argv)
    return a.fn(a) or 0


if __name__ == "__main__":
    sys.exit(main())
