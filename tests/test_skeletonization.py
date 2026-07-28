"""Tests for the production 3D skeletonization implementation."""

from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np
import tifffile


ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "src"))
from skeletonization import skeletonize_mask  # noqa: E402


class SkeletonizationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.mask = np.zeros((7, 9, 11), dtype=np.uint8)
        self.mask[2:5, 3:6, 1:10] = 255

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_npy_round_trip_and_containment(self) -> None:
        source = self.root / "mask.npy"
        output = self.root / "skeleton.npy"
        np.save(source, self.mask)

        result = skeletonize_mask(str(source), str(output))

        stored = np.load(output, allow_pickle=False)
        self.assertEqual(result.shape, self.mask.shape)
        self.assertTrue(np.array_equal(stored, result))
        self.assertTrue(np.all((~result) | (self.mask > 0)))
        self.assertGreater(np.count_nonzero(result), 0)

    def test_tiff_output_is_binary_0_255(self) -> None:
        source = self.root / "mask.tif"
        output = self.root / "skeleton.tif"
        tifffile.imwrite(source, self.mask, photometric="minisblack")

        skeletonize_mask(str(source), str(output))

        stored = tifffile.imread(output)
        self.assertEqual(stored.shape, self.mask.shape)
        self.assertEqual(set(np.unique(stored).tolist()), {0, 255})
        self.assertTrue(np.all((stored == 0) | (self.mask > 0)))

    def test_rejects_non_3d_input(self) -> None:
        source = self.root / "mask.npy"
        np.save(source, np.zeros((5, 5), dtype=np.uint8))

        with self.assertRaisesRegex(ValueError, "3D"):
            skeletonize_mask(str(source), str(self.root / "skeleton.npy"))

    def test_rejects_input_overwrite(self) -> None:
        source = self.root / "mask.npy"
        np.save(source, self.mask)

        with self.assertRaisesRegex(ValueError, "overwrite"):
            skeletonize_mask(str(source), str(source))


if __name__ == "__main__":
    unittest.main()
