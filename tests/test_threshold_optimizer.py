"""Tests for brightness-corrected CT segmentation."""

from __future__ import annotations

import csv
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np
import tifffile


ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "src"))
from threshold_optimizer import (  # noqa: E402
    brightness_corrected_thresholds,
    segment_brightness_corrected,
)


class ThresholdOptimizerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        z, y, x = np.mgrid[:7, :8, :9]
        self.volume = (100 + 10 * z + x + y).astype(np.uint16)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_thresholds_preserve_reference_and_track_drift(self) -> None:
        thresholds, medians, profile = brightness_corrected_thresholds(
            self.volume,
            reference_slice=3,
            reference_threshold=150,
            smoothing_sigma=0,
        )
        self.assertEqual(thresholds[3], 150)
        np.testing.assert_array_equal(medians, profile)
        self.assertGreater(thresholds[-1], thresholds[0])

    def test_tiff_segmentation_writes_profile_and_statistics(self) -> None:
        source = self.root / "volume.tif"
        output = self.root / "segmented_mask.tif"
        tifffile.imwrite(source, self.volume, photometric="minisblack")

        result = segment_brightness_corrected(
            source,
            output,
            reference_slice=3,
            reference_threshold=150,
            smoothing_sigma=0,
        )

        stored = tifffile.imread(output)
        self.assertEqual(stored.shape, self.volume.shape)
        self.assertTrue(set(np.unique(stored)).issubset({0, 255}))
        self.assertEqual(result["input_dtype"], "uint16")
        profile_path = Path(str(result["threshold_profile"]))
        self.assertTrue(profile_path.is_file())
        with profile_path.open(newline="", encoding="utf-8") as stream:
            rows = list(csv.DictReader(stream))
        self.assertEqual(len(rows), self.volume.shape[0])

    def test_invalid_reference_slice_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "outside"):
            brightness_corrected_thresholds(
                self.volume,
                reference_slice=20,
                reference_threshold=150,
            )

    def test_input_overwrite_is_rejected(self) -> None:
        source = self.root / "volume.npy"
        np.save(source, self.volume)
        with self.assertRaisesRegex(ValueError, "overwrite"):
            segment_brightness_corrected(
                source,
                source,
                reference_slice=3,
                reference_threshold=150,
            )


if __name__ == "__main__":
    unittest.main()
