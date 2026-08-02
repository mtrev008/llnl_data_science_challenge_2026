"""Tests for the CT-derived as-built surface exporter."""

from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest

import numpy as np
import tifffile
import trimesh


SCRIPT = (
    Path(__file__).parents[1]
    / ".agents"
    / "skills"
    / "visualization-expert"
    / "scripts"
    / "export_ct_surface.py"
)
SPEC = importlib.util.spec_from_file_location("export_ct_surface", SCRIPT)
surface = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(surface)


class SurfaceMeshExportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.mask = np.zeros((12, 14, 16), dtype=np.uint8)
        self.mask[2:10, 3:11, 4:13] = 255
        self.mask_path = self.root / "mask.tif"
        tifffile.imwrite(self.mask_path, self.mask, photometric="minisblack")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def export(self, name: str = "surface", **changes):
        values = {
            "mask_filepath": str(self.mask_path),
            "output_filepath": str(self.root / f"{name}.stl"),
            "voxel_size_xyz": (0.5, 1.0, 2.0),
            "preview_filepath": str(self.root / f"{name}.png"),
            "metrics_filepath": str(self.root / f"{name}.json"),
            "slab_depth": 4,
            "slab_overlap": 1,
        }
        values.update(changes)
        return surface.export_ct_surface(**values)

    def test_01_exports_reloadable_stl_metrics_and_required_preview(self):
        item = self.export()
        self.assertEqual(item["status"], "success")
        self.assertTrue(Path(item["output_path"]).is_file())
        self.assertTrue(Path(item["preview_path"]).is_file())
        self.assertGreater(Path(item["preview_path"]).stat().st_size, 0)
        self.assertTrue(Path(item["metrics_path"]).is_file())
        mesh = trimesh.load(item["output_path"], force="mesh", process=False)
        self.assertGreater(len(mesh.vertices), 0)
        self.assertGreater(len(mesh.faces), 0)

    def test_02_coordinate_order_and_anisotropic_scale(self):
        item = self.export("scaled")
        bounds = np.asarray(item["statistics"]["bounds_xyz"])
        extents = bounds[1] - bounds[0]
        # Occupied X, Y, Z spans are 9, 8, 8 voxels respectively.
        np.testing.assert_allclose(extents, [4.5, 8.0, 16.0], atol=1e-6)

    def test_03_multiple_components_are_preserved_by_default(self):
        self.mask[0, 0, 0] = 255
        tifffile.imwrite(self.mask_path, self.mask, photometric="minisblack")
        item = self.export("components")
        self.assertEqual(item["statistics"]["source_component_count"], 2)
        self.assertEqual(item["statistics"]["removed_component_count"], 0)
        self.assertGreaterEqual(item["statistics"]["connected_component_count"], 2)

    def test_04_component_filter_is_explicit_and_recorded(self):
        self.mask[0, 0, 0] = 255
        tifffile.imwrite(self.mask_path, self.mask, photometric="minisblack")
        item = self.export("filtered", minimum_component_voxels=2)
        self.assertTrue(item["statistics"]["component_filter_applied"])
        self.assertEqual(item["statistics"]["removed_component_count"], 1)

    def test_05_invalid_voxel_size_is_rejected(self):
        with self.assertRaises(ValueError):
            self.export("bad-spacing", voxel_size_xyz=(0.5, 0.0, 2.0))

    def test_06_empty_mask_is_rejected(self):
        tifffile.imwrite(
            self.mask_path,
            np.zeros_like(self.mask),
            photometric="minisblack",
        )
        with self.assertRaises(ValueError):
            self.export("empty")

    def test_07_nonbinary_mask_requires_threshold(self):
        values = self.mask.copy()
        values[0, 0, 0] = 127
        tifffile.imwrite(self.mask_path, values, photometric="minisblack")
        with self.assertRaises(ValueError):
            self.export("nonbinary")
        item = self.export("thresholded", mask_threshold=200)
        self.assertEqual(item["parameters"]["mask_threshold"], 200.0)

    def test_08_overwrite_is_refused(self):
        self.export("protected")
        with self.assertRaises(ValueError):
            self.export("protected")

    def test_09_source_is_not_modified(self):
        before = hashlib.sha256(self.mask_path.read_bytes()).hexdigest()
        before_mtime = self.mask_path.stat().st_mtime_ns
        self.export("immutable")
        after = hashlib.sha256(self.mask_path.read_bytes()).hexdigest()
        self.assertEqual(before, after)
        self.assertEqual(before_mtime, self.mask_path.stat().st_mtime_ns)

    def test_10_chunked_bounds_match_single_slab_bounds(self):
        chunked = self.export("chunked", slab_depth=3)
        single = self.export("single", slab_depth=self.mask.shape[0])
        np.testing.assert_allclose(
            chunked["statistics"]["bounds_xyz"],
            single["statistics"]["bounds_xyz"],
            atol=1e-6,
        )

    def test_11_large_default_path_thresholds_by_slab(self):
        old_limit = surface.MAX_COMPONENT_INVENTORY_BYTES
        surface.MAX_COMPONENT_INVENTORY_BYTES = 1
        try:
            item = self.export("streamed")
        finally:
            surface.MAX_COMPONENT_INVENTORY_BYTES = old_limit
        self.assertIsNone(item["statistics"]["source_component_count"])
        self.assertIn(
            "eager component-inventory limit",
            " ".join(item["warnings"]),
        )
        self.assertGreater(item["statistics"]["processed_slab_count"], 1)


if __name__ == "__main__":
    unittest.main()
