"""Phase 4.5 tests for the visualization-expert deterministic renderer."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np
import pandas as pd
import tifffile


SCRIPT = (
    Path(__file__).parents[1]
    / ".agents"
    / "skills"
    / "visualization-expert"
    / "scripts"
    / "generate_visualization.py"
)
SPEC = importlib.util.spec_from_file_location("generate_visualization", SCRIPT)
viz = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(viz)


class VisualizationStreamingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.volume = np.arange(4 * 6 * 8, dtype=np.uint16).reshape(4, 6, 8)
        self.tiff = self.root / "volume.tif"
        self.compressed_tiff = self.root / "compressed.tif"
        tifffile.imwrite(self.tiff, self.volume, photometric="minisblack")
        tifffile.imwrite(
            self.compressed_tiff,
            self.volume,
            photometric="minisblack",
            compression="deflate",
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def histogram_args(self, source: Path, name: str = "histogram.png", **changes):
        values = {
            "input": str(source),
            "output": str(self.root / name),
            "manifest": None,
            "validation_report": None,
            "overwrite": False,
            "title": None,
            "column": None,
            "bins": "auto",
            "x_label": None,
            "threshold": None,
            "show_mean": True,
            "show_median": True,
            "log_count": False,
            "command": "histogram",
        }
        values.update(changes)
        return argparse.Namespace(**values)

    def trend_args(self, metric: str, name: str):
        return argparse.Namespace(
            input=str(self.tiff),
            output=str(self.root / name),
            manifest=None,
            validation_report=None,
            overwrite=False,
            title=None,
            column=None,
            axis=0,
            metric=metric,
            command="slice-trend",
        )

    def test_01_inspect_uncompressed_tiff(self):
        metadata = viz.inspect_tiff(self.tiff)
        self.assertEqual(metadata["shape"], list(self.volume.shape))
        self.assertEqual(metadata["dtype"], "uint16")
        self.assertEqual(metadata["page_count"], 4)

    def test_02_iterate_tiff_pages(self):
        pages = list(viz.iterate_tiff_pages(self.tiff))
        self.assertEqual(len(pages), 4)
        np.testing.assert_array_equal(pages[2][1], self.volume[2])

    def test_03_exact_uint16_histogram_counts(self):
        counts, edges, _, provenance = viz.stream_tiff_histogram(self.tiff, "auto")
        self.assertEqual(int(counts.sum()), self.volume.size)
        self.assertEqual(int(np.count_nonzero(counts)), self.volume.size)
        self.assertEqual(provenance["histogram_count_coverage"], 1.0)

    def test_04_exact_uint16_histogram_statistics(self):
        _, _, summary, _ = viz.stream_tiff_histogram(self.tiff, "auto")
        self.assertEqual(summary["minimum"], float(self.volume.min()))
        self.assertEqual(summary["maximum"], float(self.volume.max()))
        self.assertAlmostEqual(summary["mean"], float(self.volume.mean()))
        self.assertAlmostEqual(
            summary["standard_deviation"], float(self.volume.std(ddof=1))
        )

    def test_05_tiff_threshold_count(self):
        threshold = 100.0
        item = viz.histogram(
            self.histogram_args(self.tiff, threshold=threshold)
        )
        expected = int(np.count_nonzero(self.volume >= threshold))
        self.assertEqual(
            item["statistics"]["threshold_analysis"]["count_at_or_above"],
            expected,
        )

    def test_06_compressed_tiff_streaming(self):
        counts, _, _, provenance = viz.stream_tiff_histogram(
            self.compressed_tiff, "auto"
        )
        self.assertEqual(int(counts.sum()), self.volume.size)
        self.assertEqual(provenance["pages_processed"], 4)

    def test_07_streamed_axis_zero_mean_trend(self):
        item = viz.slice_trend(self.trend_args("mean", "mean.png"))
        self.assertEqual(
            item["provenance"]["statistics_source"], "streamed_tiff_pages"
        )
        self.assertEqual(item["provenance"]["pages_processed"], 4)
        self.assertAlmostEqual(
            item["statistics"]["mean"],
            float(self.volume.mean(axis=(1, 2)).mean()),
        )

    def test_08_streamed_axis_zero_std_trend(self):
        item = viz.slice_trend(self.trend_args("std", "std.png"))
        expected = self.volume.std(axis=(1, 2))
        self.assertAlmostEqual(item["statistics"]["mean"], float(expected.mean()))

    def test_09_small_display_window_not_sampled(self):
        metadata = viz.calculate_display_window(self.volume[0], 1, 99)
        self.assertFalse(metadata["sampled"])
        self.assertEqual(metadata["stride"], 1)

    def test_10_large_display_window_records_sampling(self):
        values = np.arange(viz.MAX_DISPLAY_SAMPLES + 1, dtype=np.float32)
        metadata = viz.calculate_display_window(values, 1, 99)
        self.assertTrue(metadata["sampled"])
        self.assertEqual(metadata["sampling_method"], "regular_stride")
        self.assertGreater(metadata["stride"], 1)

    def test_11_render_dimension_limit(self):
        old_width, old_height = viz.MAX_RENDER_WIDTH, viz.MAX_RENDER_HEIGHT
        viz.MAX_RENDER_WIDTH = 4
        viz.MAX_RENDER_HEIGHT = 3
        try:
            rendered, metadata = viz.prepare_display_image(
                np.arange(10 * 12).reshape(10, 12)
            )
        finally:
            viz.MAX_RENDER_WIDTH, viz.MAX_RENDER_HEIGHT = old_width, old_height
        self.assertLessEqual(rendered.shape[0], 3)
        self.assertLessEqual(rendered.shape[1], 4)
        self.assertTrue(metadata["render_downsampled"])

    def test_12_mask_reduction_uses_regular_grid_values(self):
        old_width, old_height = viz.MAX_RENDER_WIDTH, viz.MAX_RENDER_HEIGHT
        viz.MAX_RENDER_WIDTH = 2
        viz.MAX_RENDER_HEIGHT = 2
        mask = np.arange(16, dtype=np.uint8).reshape(4, 4)
        try:
            rendered, metadata = viz.prepare_display_image(mask)
        finally:
            viz.MAX_RENDER_WIDTH, viz.MAX_RENDER_HEIGHT = old_width, old_height
        np.testing.assert_array_equal(rendered, mask[::2, ::2])
        self.assertEqual(metadata["render_sampling_method"], "regular_grid")

    def test_13_npy_disallows_pickle(self):
        path = self.root / "objects.npy"
        np.save(path, np.array([{"unsafe": True}], dtype=object))
        with self.assertRaises(ValueError):
            viz.numeric_values(path, None)

    def test_14_csv_histogram_compatibility(self):
        path = self.root / "values.csv"
        pd.DataFrame({"value": [1, 2, 3, np.nan]}).to_csv(path, index=False)
        item = viz.histogram(
            self.histogram_args(path, "csv.png", column="value")
        )
        self.assertEqual(item["status"], "success")
        self.assertEqual(item["statistics"]["count"], 3)
        self.assertEqual(item["statistics"]["discarded_value_count"], 1)

    def test_15_manifest_preserves_streaming_metadata(self):
        item = viz.histogram(self.histogram_args(self.tiff, "manifested.png"))
        manifest = self.root / "manifest.json"
        viz.update_manifest(str(manifest), item)
        stored = json.loads(manifest.read_text(encoding="utf-8"))
        artifact = stored["artifacts"][0]
        self.assertEqual(
            artifact["provenance"]["statistics_source"],
            "streamed_tiff_pages",
        )
        self.assertEqual(artifact["provenance"]["histogram_count_coverage"], 1.0)

    def test_16_refuses_unsafe_compressed_eager_load(self):
        old_limit = viz.MAX_EAGER_BYTES
        viz.MAX_EAGER_BYTES = 1
        try:
            with self.assertRaises(ValueError):
                viz.load_array(self.compressed_tiff)
        finally:
            viz.MAX_EAGER_BYTES = old_limit

    def test_17_streaming_does_not_modify_source(self):
        before_bytes = self.tiff.read_bytes()
        before_hash = hashlib.sha256(before_bytes).hexdigest()
        before_mtime = self.tiff.stat().st_mtime_ns
        viz.stream_tiff_histogram(self.tiff, "auto")
        after_hash = hashlib.sha256(self.tiff.read_bytes()).hexdigest()
        self.assertEqual(before_hash, after_hash)
        self.assertEqual(before_mtime, self.tiff.stat().st_mtime_ns)


if __name__ == "__main__":
    unittest.main()
