"""bm CLI, spec validation and release-asset restore (no bpy, no network)."""
import json
import os
import tempfile
import unittest
import zipfile
from pathlib import Path

from bmodels import assets, checks, cli, project, spec
from bmodels.paths import BUILD, ROOT, TEMPLATES


class SpecTests(unittest.TestCase):
    def test_repo_and_template_specs_validate(self):
        paths = project.all_specs() + sorted((TEMPLATES / "project/specs").glob("*.yaml"))
        self.assertTrue(paths)
        for path in paths:
            with self.subTest(spec=path.name):
                self.assertEqual(spec.check(spec.load(path)), [])

    def test_unsourced_element_fails(self):
        s = {"sources": [], "elements": [{"id": "a", "size": [1, 1, 1], "at": [0, 0, 0], "trade": "t", "status": "confirmed"}]}
        self.assertTrue(any("source" in e for e in spec.check(s)))

    def test_assumed_needs_basis(self):
        s = {"sources": [], "elements": [{"id": "a", "size": [1, 1, 1], "at": [0, 0, 0], "trade": "t", "status": "assumed"}]}
        self.assertTrue(any("basis" in e for e in spec.check(s)))


class AssetTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.downloads = self.tmp / "downloads"
        self.downloads.mkdir()
        (self.downloads / "film.mp4").write_bytes(b"film")
        with zipfile.ZipFile(self.downloads / "model.zip", "w") as z:
            z.writestr("pkg/model.blend", b"blend")
        records = []
        for name in ("film.mp4", "model.zip"):
            p = self.downloads / name
            records.append({"name": name, "bytes": p.stat().st_size, "sha256": assets.digest(p)})
        records[0]["dest"] = "out/film.mp4"
        records[1]["extract"] = {"pkg/model.blend": "models/model.blend"}
        self.manifest = self.tmp / "release-assets.json"
        self.manifest.write_text(json.dumps({"tag": "t", "assets": records}))

    def test_pull_restores_dest_and_extract(self):
        assets.pull(self.manifest, extra_dirs=[self.downloads])
        self.assertEqual((self.tmp / "out/film.mp4").read_bytes(), b"film")
        self.assertEqual((self.tmp / "models/model.blend").read_bytes(), b"blend")
        self.assertTrue(assets.verify(self.manifest, [self.downloads]))

    def test_pull_preserves_modified_target_and_writes_nothing(self):
        (self.tmp / "models").mkdir()
        (self.tmp / "models/model.blend").write_bytes(b"edited")
        with self.assertRaises(FileExistsError):
            assets.pull(self.manifest, extra_dirs=[self.downloads])
        self.assertFalse((self.tmp / "out/film.mp4").exists())  # all-or-nothing

    def test_corrupt_download_is_not_used(self):
        (self.downloads / "film.mp4").write_bytes(b"flim")
        self.assertFalse(assets.verify(self.manifest, [self.downloads]))


class NewSiteTests(unittest.TestCase):
    def test_new_site_from_template_validates(self):
        tmp = Path(tempfile.mkdtemp())
        old = cli.PROJECTS
        cli.PROJECTS = tmp
        try:
            for kind in ("element", "detail"):
                self.assertEqual(cli.main(["new", f"demo-{kind}", "--type", kind, "--name", "Demo"]), 0)
                site = tmp / f"demo-{kind}"
                self.assertIn('name: "Demo"', (site / "project.yaml").read_text())
                self.assertTrue((site / "products/.gitkeep").exists())
                s = spec.load(site / "specs" / f"demo-{kind}-{kind}.yaml")
                self.assertEqual(spec.kind(s), kind)
                self.assertEqual(spec.check(s), [])
                self.assertNotIn("{{", (site / "README.md").read_text())
        finally:
            cli.PROJECTS = old

    def test_large_new_file_is_blocked(self):
        BUILD.mkdir(exist_ok=True)
        big = Path(tempfile.mkdtemp(dir=BUILD)) / "render.mp4"
        big.write_bytes(b"0" * (2 * 1024 * 1024))
        small = big.with_name("poster.png")
        small.write_bytes(b"0" * 1024)
        rel = lambda p: str(p.relative_to(ROOT))
        errors = checks.large_files([rel(big), rel(small)])
        self.assertEqual(len(errors), 1)
        self.assertIn("bm publish", errors[0])

    def test_inventory_lists_every_site_with_steps_and_deliverables(self):
        inv = {s["site"]: s for s in cli.inventory()}
        self.assertEqual(set(inv), {s.name for s in project.sites()})
        for s in inv.values():
            for p in s["products"]:
                self.assertTrue("check" in p["steps"] or p["check_unavailable"],
                                f"{p['ref']} needs a `check` step for CI or check_unavailable")
                for d in p["deliverables"]:
                    self.assertTrue((ROOT / d).is_dir(), f"{p['ref']}: deliverables {d} does not exist")
            for sp in s["specs"]:
                self.assertTrue(sp["build_dir"].startswith(f"build/{s['site']}/"))

    def test_doctor_reports_every_check_with_a_fix(self):
        from bmodels import doctor
        for name, ok, detail, fix, blocks in doctor.checks():
            self.assertIsInstance(ok, bool, name)
            self.assertTrue(fix and blocks, name)

    def test_add_product_scaffolds_a_runnable_check(self):
        tmp = Path(tempfile.mkdtemp())
        old = (project.PROJECTS, cli.PROJECTS)
        project.PROJECTS = cli.PROJECTS = tmp
        try:
            cli.main(["new", "demo"])
            self.assertEqual(cli.main(["add-product", "demo/film", "--kind", "film"]), 0)
            p = project.product("demo/film")
            self.assertEqual(p.meta["kind"], "film")
            self.assertTrue(p.deliverables.is_dir())
            self.assertEqual(cli.main(["run", "demo/film", "check"]), 0)
        finally:
            project.PROJECTS, cli.PROJECTS = old

    def test_paths_point_at_repo(self):
        self.assertTrue((ROOT / "pyproject.toml").exists())


FAKE_GH = """#!/bin/sh
echo "$@" >> "$GH_LOG"
case "$1 $2" in
  "release view") exit 1 ;;
  "repo view") echo owner/repo ;;
esac
"""


class PublishTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        bin_ = self.tmp / "bin"
        bin_.mkdir()
        (bin_ / "gh").write_text(FAKE_GH)
        (bin_ / "gh").chmod(0o755)
        self.log = self.tmp / "gh.log"
        self.env = {"PATH": f"{bin_}:{os.environ['PATH']}", "GH_LOG": str(self.log)}
        self.old_env = {k: os.environ.get(k) for k in self.env}
        os.environ.update(self.env)

    def tearDown(self):
        for k, v in self.old_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def test_publish_creates_manifest_release_and_records_checksums(self):
        site = self.tmp / "projects/demo"
        (site / "products/film").mkdir(parents=True)
        (site / "project.yaml").write_text("name: Demo\nrelease_tag_prefix: demo\n")
        (site / "products/film/product.yaml").write_text("kind: film\nsteps: {render: echo}\n")
        movie = self.tmp / "film.mp4"
        movie.write_bytes(b"x" * 10)
        old = project.PROJECTS
        project.PROJECTS = self.tmp / "projects"
        try:
            self.assertEqual(cli.main(["publish", "demo/film", str(movie), "--tag", "demo-film-test"]), 0)
        finally:
            project.PROJECTS = old
        m = json.loads((site / "products/film/release-assets.json").read_text())
        self.assertEqual((m["repository"], m["tag"], m["storage"]), ("owner/repo", "demo-film-test", "release"))
        self.assertEqual(m["assets"], [{"name": "film.mp4", "bytes": 10, "sha256": assets.digest(movie)}])
        calls = self.log.read_text().splitlines()
        self.assertTrue(any(c.startswith("release create demo-film-test") for c in calls))
        self.assertTrue(any(c.startswith("release upload demo-film-test") and c.endswith("film.mp4") for c in calls))

    def test_publish_refuses_lfs_manifest(self):
        site = self.tmp / "projects/demo"
        (site / "products/old").mkdir(parents=True)
        (site / "project.yaml").write_text("name: Demo\n")
        (site / "products/old/product.yaml").write_text("kind: film\nsteps: {render: echo}\n")
        (site / "products/old/release-assets.json").write_text('{"tag": "t", "storage": "git-lfs", "assets": []}')
        old = project.PROJECTS
        project.PROJECTS = self.tmp / "projects"
        try:
            with self.assertRaises(SystemExit):
                cli.main(["publish", "demo/old", str(self.tmp / "x.mp4")])
        finally:
            project.PROJECTS = old


if __name__ == "__main__":
    unittest.main()
