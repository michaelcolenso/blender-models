"""Protect native timing, source versioning, frame coverage and assembly provenance."""
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from assemble_video import verify_frames
from video_common import ROOT, asset_identity, compile_plan, digest, load_plan

RECIPE = "render/videos/highland-installation.json"


class VideoWorkflowTests(unittest.TestCase):
    def setUp(self):
        (ROOT / "build").mkdir(exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(dir=ROOT / "build")
        self.addCleanup(self.temporary.cleanup)
        self.folder = Path(self.temporary.name)

    def test_native_production_and_exact_chunk_coverage(self):
        plan = compile_plan(RECIPE, "production1080")
        self.assertEqual(len(plan["frames"]), 90 * 24)
        self.assertEqual(plan["settings"]["native_fps"], plan["delivery_fps"])
        self.assertEqual(plan["frames"][0]["source_time"], 0)
        self.assertAlmostEqual(plan["frames"][-1]["source_time"], 90 - 1 / 24)
        indices = [i for chunk in plan["chunks"] for i in range(chunk["first"], chunk["last"] + 1)]
        self.assertEqual(indices, list(range(2160)))

    def test_storyboard_includes_both_transfer_states(self):
        plan = compile_plan(RECIPE, "storyboard")
        self.assertEqual(len(plan["frames"]), 10)
        self.assertEqual([f["source_time"] for f in plan["frames"] if f["shot"] == "transfer"], [60, 69])
        self.assertEqual([f["output_time"] for f in plan["frames"] if f["shot"] == "transfer"], [60, 69])

    def test_short_preview_samples_the_named_shot(self):
        plan = compile_plan(RECIPE, "preview", "install", 2)
        self.assertEqual(len(plan["frames"]), 12)
        self.assertEqual(plan["duration"], 2)
        self.assertEqual(plan["frames"][0]["source_time"], 41.5)
        self.assertEqual(plan["settings"]["native_fps"], 6)

    def test_bad_selection_and_sample_requests_fail(self):
        for args in (("preview", "missing", None), ("production1080", "install", 2), ("preview", "all", 2)):
            with self.subTest(args=args), self.assertRaises(ValueError):
                compile_plan(RECIPE, *args)

    def test_bad_shot_intervals_duplicate_ids_and_nonfinite_durations_fail(self):
        original = json.loads((ROOT / RECIPE).read_text())
        for changes in ({"source_out": 200}, {"duration": float("nan")}, {"duration": .01}, {"scene": "unknown"}, {"id": "../escape"}):
            recipe = copy.deepcopy(original)
            recipe["shots"][0].update(changes)
            path = self.folder / "bad.json"
            path.write_text(json.dumps(recipe))
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                compile_plan(str(path.relative_to(ROOT)), "preview")
        original["shots"][1]["id"] = original["shots"][0]["id"]
        path.write_text(json.dumps(original))
        with self.assertRaisesRegex(ValueError, "unique"):
            compile_plan(str(path.relative_to(ROOT)), "preview")

    def test_lfs_pointer_records_content_hash(self):
        path = self.folder / "model.blend"
        expected = "a" * 64
        path.write_text(f"version https://git-lfs.github.com/spec/v1\noid sha256:{expected}\nsize 123\n")
        self.assertEqual(asset_identity(path), (expected, True))

    def test_modified_signed_plan_is_rejected(self):
        plan = compile_plan(RECIPE, "storyboard")
        plan["frames"][0]["source_time"] = 80
        path = self.folder / "plan.json"
        path.write_text(json.dumps(plan))
        with self.assertRaisesRegex(ValueError, "signature"):
            load_plan(path)

    def test_title_edits_reuse_compatible_image_plates(self):
        original = compile_plan(RECIPE, "storyboard")
        recipe = json.loads((ROOT / RECIPE).read_text())
        recipe["shots"][0]["title"] = "A revised title"
        path = self.folder / "revised.json"
        path.write_text(json.dumps(recipe))
        revised = compile_plan(str(path.relative_to(ROOT)), "storyboard")
        self.assertNotEqual(original["plan_id"], revised["plan_id"])
        self.assertEqual(original["plate_id"], revised["plate_id"])

    def frame_fixture(self):
        path = self.folder / "f000000.png"
        Image.new("RGB", (64, 64), "white").save(path)
        path.with_suffix(".json").write_text(json.dumps({"index": 0, "plan_id": "known-plan", "sha256": digest(path), "raw_checks": {"nonblank": True}}))
        return {"plan_id": "known-plan", "frames": [{"index": 0}], "settings": {"width": 64, "height": 64}}

    def test_missing_and_extra_frames_cannot_be_assembled(self):
        plan = self.frame_fixture()
        verify_frames(plan, self.folder)
        extra = self.folder / "f000001.png"
        Image.new("RGB", (64, 64)).save(extra)
        with self.assertRaisesRegex(ValueError, "Frame set mismatch"):
            verify_frames(plan, self.folder)
        extra.unlink()
        (self.folder / "f000000.png").unlink()
        with self.assertRaisesRegex(ValueError, "Frame set mismatch"):
            verify_frames(plan, self.folder)

    def test_changed_pixels_cannot_reuse_old_frame_evidence(self):
        plan = self.frame_fixture()
        Image.new("RGB", (64, 64), "black").save(self.folder / "f000000.png")
        with self.assertRaisesRegex(ValueError, "provenance"):
            verify_frames(plan, self.folder)


if __name__ == "__main__":
    unittest.main()
