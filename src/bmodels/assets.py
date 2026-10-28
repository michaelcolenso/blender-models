"""Large files live in GitHub Releases, described by a checksum manifest committed next to the work.

Manifest (JSON), paths relative to the manifest's directory unless noted:

    {
      "repository": "owner/repo",
      "tag": "highland-repipe-2026-10-17",
      "storage": "release",                              # or "git-lfs": files are committed via LFS in asset_directory
      "asset_directory": "../../deliverables/x/assets",   # optional local copy checked before downloading
      "assets": [
        {"name": "film-4K.mp4", "bytes": 123, "sha256": "...",
         "dest": "renders/film-4K.mp4",                    # optional: copy here after verifying
         "extract": {"zip/member.blend": "local/path.blend"}}  # optional: zip members to restore
      ]
    }

pull   fetch missing assets — release: into build/assets/<tag>/ (never over committed files); git-lfs:
       `git lfs pull` of asset_directory —
       verify every checksum, then copy `dest` files and extract `extract` members. Restores are
       all-or-nothing: every archive and existing target is checked before anything is written, and a
       locally modified target is preserved (error), never overwritten.
verify check the local copies (asset_directory or the download cache) against the manifest.
push   upload files to the release (created if missing) and record their bytes and sha256.
"""
import hashlib
import json
import shutil
import subprocess
import zipfile
from pathlib import Path

from bmodels.paths import BUILD, ROOT


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def matches(path, record):
    path = Path(path)
    return path.is_file() and path.stat().st_size == record["bytes"] and digest(path) == record["sha256"]


class Manifest:
    def __init__(self, path, extra_dirs=()):
        self.path = Path(path).resolve()
        self.extra_dirs = [Path(d) for d in extra_dirs]
        self.dir = self.path.parent
        self.data = json.loads(self.path.read_text())
        self.tag = self.data["tag"]
        self.repo = self.data.get("repository")
        self.cache = BUILD / "assets" / self.tag

    @property
    def assets(self):
        return self.data.setdefault("assets", [])

    def local(self, record):
        """First verified local copy of an asset, or None."""
        dirs = [*self.extra_dirs, self.cache]
        if self.data.get("asset_directory"):
            dirs.insert(len(self.extra_dirs), self.dir / self.data["asset_directory"])
        candidates = [d / record["name"] for d in dirs]
        return next((c for c in candidates if matches(c, record)), None)

    def save(self):
        self.path.write_text(json.dumps(self.data, indent=2) + "\n")


def _gh(*args):
    subprocess.run(["gh", *args], check=True)


def verify(manifest, extra_dirs=()):
    m = Manifest(manifest, extra_dirs)
    missing = [a["name"] for a in m.assets if not m.local(a)]
    for a in m.assets:
        print(f"{'ok     ' if a['name'] not in missing else 'MISSING'} {a['name']}")
    return not missing


def pull(manifest, names=None, extra_dirs=()):
    m = Manifest(manifest, extra_dirs)
    wanted = [a for a in m.assets if not names or a["name"] in names]
    m.cache.mkdir(parents=True, exist_ok=True)
    if m.data.get("storage") == "git-lfs" and not all(m.local(a) for a in wanted):
        if shutil.which("git-lfs") is None:
            raise SystemExit("These assets are stored in Git LFS: install git-lfs (e.g. `sudo apt-get install git-lfs`), "
                             "or pass --from <dir> with downloaded copies.")
        folder = (m.dir / m.data["asset_directory"]).resolve().relative_to(ROOT)
        subprocess.run(["git", "lfs", "pull", "--include", f"{folder}/*"], cwd=ROOT, check=True)
    for a in wanted:
        if m.local(a):
            continue
        if m.data.get("storage") == "git-lfs":
            raise ValueError(f"LFS checksum mismatch: {a['name']}")
        repo = ["-R", m.repo] if m.repo else []
        _gh("release", "download", m.tag, *repo, "-p", a["name"], "-D", str(m.cache), "--clobber")
        if not matches(m.cache / a["name"], a):
            raise ValueError(f"Release checksum mismatch: {a['name']}")
    sources = {a["name"]: m.local(a) for a in wanted}

    # Check every target before writing any (all-or-nothing; preserve local edits).
    plan = []
    for a in wanted:
        src = sources[a["name"]]
        if a.get("dest"):
            plan.append((m.dir / a["dest"], a["sha256"], lambda out, src=src: shutil.copyfile(src, out)))
        for member, rel in (a.get("extract") or {}).items():
            with zipfile.ZipFile(src) as z, z.open(member) as f:
                want = hashlib.file_digest(f, "sha256").hexdigest()
            def write(out, src=src, member=member):
                with zipfile.ZipFile(src) as z, z.open(member) as f, out.open("xb") as o:
                    shutil.copyfileobj(f, o)
            plan.append((m.dir / rel, want, write))
    for target, want, _ in plan:
        if target.exists() and digest(target) != want:
            raise FileExistsError(f"Preserving a modified local asset: {target}")

    restored = 0
    for target, _, write in plan:
        if target.exists():
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_name(target.name + ".part")
        try:
            write(tmp)
            tmp.replace(target)
        finally:
            tmp.unlink(missing_ok=True)
        restored += 1
    print(f"{len(wanted)} release assets verified; restored {restored} files. Existing matching files preserved.")


def push(manifest, files, title=None):
    m = Manifest(manifest)
    repo = ["-R", m.repo] if m.repo else []
    if subprocess.run(["gh", "release", "view", m.tag, *repo], capture_output=True, check=False).returncode:
        _gh("release", "create", m.tag, *repo, "--title", title or m.tag, "--notes", "")
    _gh("release", "upload", m.tag, *repo, "--clobber", *map(str, files))
    for f in map(Path, files):
        rec = next((a for a in m.assets if a["name"] == f.name), None)
        if rec is None:
            rec = {"name": f.name}
            m.assets.append(rec)
        rec.update(bytes=f.stat().st_size, sha256=digest(f))
    m.save()
    print(f"Uploaded {len(files)} files to {m.tag}; manifest updated: {m.path}")
