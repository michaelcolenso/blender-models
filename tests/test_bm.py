"""bm CLI, spec validation and release-asset restore (no bpy, no network)."""
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from bmodels import assets, cli, project, spec
from bmodels.paths import ROOT, TEMPLATES


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

    def test_paths_point_at_repo(self):
        self.assertTrue((ROOT / "pyproject.toml").exists())


if __name__ == "__main__":
    unittest.main()
