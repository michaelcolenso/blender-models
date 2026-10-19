"""Failure checks that keep the render matrix and output QA trustworthy."""
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from render_plan import load_shots, select_shots
from render_scene import validate_image


class RenderWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        (self.root / "model.blend").write_bytes(b"test placeholder")
        self.catalog = self.root / "scenes.json"
        self.shot = {"id": "overview", "blend": "model.blend", "scene": "Scene",
                     "camera": "Camera", "frame": 1, "notice": "Assumed geometry"}

    def load(self, shots):
        self.catalog.write_text(json.dumps({"schema_version": 1, "shots": shots}))
        return load_shots(self.catalog, self.root)

    def test_catalog_and_selection(self):
        shots = self.load([self.shot])
        self.assertEqual(select_shots(shots, "overview"), shots)
        with self.assertRaisesRegex(ValueError, "Unknown shot"):
            select_shots(shots, "missing")

    def test_duplicate_and_unsafe_ids(self):
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            self.load([self.shot, self.shot])
        for bad_id in ("../escape", "shot\noutput=bad", "ALL", "all", ""):
            with self.subTest(bad_id=bad_id), self.assertRaises(ValueError):
                self.load([{**self.shot, "id": bad_id}])

    def test_missing_or_escaping_model(self):
        for model in ("missing.blend", "../outside.blend", str(self.root / "model.blend")):
            with self.subTest(model=model), self.assertRaises(ValueError):
                self.load([{**self.shot, "blend": model}])

    def test_frame_and_notice_required(self):
        for field, value in (("frame", True), ("frame", 1.5), ("frame", -1), ("notice", "")):
            shot = copy.deepcopy(self.shot)
            shot[field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                self.load([shot])

    def test_blank_transparent_and_wrong_size_images_fail(self):
        path = self.root / "test.png"
        for color in ((0, 0, 0, 255), (255, 255, 255, 255), (10, 20, 30, 0)):
            Image.new("RGBA", (64, 64), color).save(path)
            with self.subTest(color=color), self.assertRaises(ValueError):
                validate_image(path, 64, 64)
        with self.assertRaisesRegex(ValueError, "Wrong image size"):
            validate_image(path, 128, 128)

    def test_nonblank_image_passes(self):
        path = self.root / "test.png"
        image = Image.new("RGB", (64, 64), "white")
        ImageDraw.Draw(image).rectangle((16, 16, 48, 48), fill="black")
        image.save(path)
        self.assertTrue(validate_image(path, 64, 64)["nonblank"])


if __name__ == "__main__":
    unittest.main()
