"""Failure checks that keep the render matrix and output QA trustworthy."""
import copy
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

from bmodels.render_plan import load_shots, select_shots
from bmodels.render_scene import validate_image
from bmodels.render_assets import validate_scene_assets

try:
    import bpy
except ImportError:
    bpy = None


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


@unittest.skipIf(bpy is None, "Blender runtime required for asset dependency regressions")
class BlenderAssetDependencyTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.folder = Path(self.directory.name)
        bpy.ops.wm.read_factory_settings(use_empty=True)
        self.scene = bpy.context.scene

    def image_material(self, filename="texture.png"):
        path = self.folder / filename
        Image.new("RGB", (4, 4), "green").save(path)
        image = bpy.data.images.load(str(path))
        material = bpy.data.materials.new("Asset test material")
        material.use_nodes = True
        material.node_tree.nodes.new("ShaderNodeTexImage").image = image
        mesh = bpy.data.meshes.new("Asset test mesh")
        mesh.materials.append(material)
        obj = bpy.data.objects.new("Asset test object", mesh)
        self.scene.collection.objects.link(obj)
        return path, image, material

    def test_relocated_model_ignores_missing_saved_brush_catalog(self):
        source = Path(__file__).resolve().parents[1] / "deliverables/highland-water/Highland-domestic-water.blend"
        relocated = self.folder / "relocated.blend"
        shutil.copy2(source, relocated)
        bpy.ops.wm.open_mainfile(filepath=str(relocated), load_ui=False, use_scripts=False)
        missing_ui_paths = [path for path in bpy.utils.blend_paths(absolute=True, packed=True)
                            if "essentials_brushes-gp_draw.blend" in path and not Path(path).is_file()]
        self.assertTrue(missing_ui_paths, "Fixture must reproduce the missing brush catalog")
        self.assertEqual(validate_scene_assets(bpy, bpy.context.scene), [])

    def test_referenced_texture_is_required(self):
        path, _, _ = self.image_material()
        self.assertEqual(validate_scene_assets(bpy, self.scene), [str(path)])
        path.unlink()
        with self.assertRaisesRegex(ValueError, "texture.png"):
            validate_scene_assets(bpy, self.scene)

    def test_packed_texture_does_not_require_its_original_file(self):
        path, image, _ = self.image_material()
        image.pack()
        path.unlink()
        self.assertEqual(validate_scene_assets(bpy, self.scene), [])

    def test_unrelated_missing_image_does_not_block_this_scene(self):
        path, _, _ = self.image_material()
        unused = bpy.data.images.new("Unused image", width=1, height=1)
        unused.source = "FILE"
        unused.filepath = str(self.folder / "unused-missing.png")
        unused.use_fake_user = True
        self.assertEqual(validate_scene_assets(bpy, self.scene), [str(path)])

    def test_linked_library_and_relative_texture_are_required(self):
        path, image, material = self.image_material()
        image.filepath = "//texture.png"
        library_path = self.folder / "materials.blend"
        bpy.data.libraries.write(str(library_path), {material})
        bpy.ops.wm.read_factory_settings(use_empty=True)
        self.scene = bpy.context.scene
        with bpy.data.libraries.load(str(library_path), link=True) as (source, target):
            target.materials = source.materials
        mesh = bpy.data.meshes.new("Linked asset mesh")
        mesh.materials.append(target.materials[0])
        obj = bpy.data.objects.new("Linked asset object", mesh)
        self.scene.collection.objects.link(obj)
        self.assertEqual(set(validate_scene_assets(bpy, self.scene)), {str(path), str(library_path)})
        path.unlink()
        with self.assertRaisesRegex(ValueError, "texture.png"):
            validate_scene_assets(bpy, self.scene)
        library_path.unlink()
        with self.assertRaisesRegex(ValueError, "materials.blend"):
            validate_scene_assets(bpy, self.scene)


if __name__ == "__main__":
    unittest.main()
