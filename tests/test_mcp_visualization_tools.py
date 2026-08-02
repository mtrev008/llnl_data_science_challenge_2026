"""Tests for visualization tools on the repository's single MCP server."""

from __future__ import annotations

import asyncio
import inspect
import json
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np
import pandas as pd
import tifffile


ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "src"))
import mcp_server as server  # noqa: E402


class MCPVisualizationToolTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        z, y, x = np.mgrid[:5, :10, :12]
        self.volume = (x + 2 * y + 3 * z).astype(np.float32)
        self.mask = (((x - 6) ** 2 + (y - 5) ** 2) < 9) & (z > 0)
        self.prediction = self.mask.copy()
        self.prediction[:, 1:3, 1:3] = True
        self.npy = self.root / "volume.npy"
        self.mask_npy = self.root / "mask.npy"
        self.prediction_npy = self.root / "prediction.npy"
        self.tiff = self.root / "volume.tif"
        self.csv = self.root / "metrics.csv"
        self.graph = self.root / "graph.json"
        self.validation = self.root / "validation.json"
        np.save(self.npy, self.volume)
        np.save(self.mask_npy, self.mask.astype(np.uint8))
        np.save(self.prediction_npy, self.prediction.astype(np.uint8))
        tifffile.imwrite(
            self.tiff,
            self.volume.astype(np.uint16),
            photometric="minisblack",
        )
        pd.DataFrame({
            "value": self.volume.reshape(-1)[:200],
            "category": ["a", "b"] * 100,
        }).to_csv(self.csv, index=False)
        self.graph.write_text(json.dumps({
            "nodes": [
                {"id": 0, "position": [0, 0, 0]},
                {"id": 1, "position": [1, 0, 0]},
                {"id": 2, "position": [0, 1, 0]},
            ],
            "edges": [
                {"source": 0, "target": 1},
                {"source": 1, "target": 2},
            ],
        }), encoding="utf-8")
        self.validation.write_text(json.dumps({
            "decision": "PASS_WITH_WARNINGS",
            "all_warnings": ["Synthetic upstream warning"],
        }), encoding="utf-8")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def output(self, name: str) -> str:
        return str(self.root / name)

    def tool_names(self) -> set[str]:
        tools = asyncio.run(server.mcp.list_tools())
        return {tool.name for tool in tools}

    def test_01_single_fastmcp_server_imports(self):
        self.assertEqual(server.mcp.name, "LLNL Data Science Challenge Tools")

    def test_02_renderer_loads_repository_relatively(self):
        self.assertTrue(server.VISUALIZATION_SCRIPT.is_file())
        self.assertEqual(
            Path(server.visualization.__file__).resolve(),
            server.VISUALIZATION_SCRIPT.resolve(),
        )
        self.assertTrue(server.SURFACE_EXPORT_SCRIPT.is_file())
        self.assertEqual(
            Path(server.surface_export.__file__).resolve(),
            server.SURFACE_EXPORT_SCRIPT.resolve(),
        )

    def test_03_visualization_tools_are_registered(self):
        expected = {
            "inspect_visualization_input",
            "create_histogram",
            "create_bar_chart",
            "visualize_slice",
            "create_orthogonal_views",
            "plot_slice_trend",
            "overlay_segmentation",
            "compare_masks",
            "render_graph",
            "export_ct_as_built_surface",
        }
        self.assertTrue(expected.issubset(self.tool_names()))

    def test_04_mcp_signatures_are_explicit(self):
        functions = [
            server.create_histogram,
            server.create_bar_chart,
            server.visualize_slice,
            server.create_orthogonal_views,
            server.plot_slice_trend,
            server.overlay_segmentation,
            server.compare_masks,
            server.render_graph,
            server.export_ct_as_built_surface,
        ]
        for function in functions:
            for parameter in inspect.signature(function).parameters.values():
                self.assertNotIn(
                    parameter.kind,
                    {
                        inspect.Parameter.VAR_POSITIONAL,
                        inspect.Parameter.VAR_KEYWORD,
                    },
                )

    def test_05_inspect_npy_input(self):
        item = server.inspect_visualization_input(str(self.npy))
        self.assertEqual(item["status"], "success")
        self.assertEqual(item["input_type"], "npy")
        self.assertEqual(item["shape"], list(self.volume.shape))

    def test_06_inspect_csv_input(self):
        item = server.inspect_visualization_input(str(self.csv))
        self.assertEqual(item["rows"], 200)
        self.assertEqual(item["columns"], ["value", "category"])

    def test_06a_inspect_3d_tiff_advertises_surface_export(self):
        item = server.inspect_visualization_input(str(self.tiff))
        self.assertEqual(item["status"], "success")
        self.assertIn(
            "ct_as_built_surface",
            item["supported_visualizations"],
        )

    def test_07_histogram_without_validation(self):
        item = server.create_histogram(
            str(self.csv),
            self.output("histogram.png"),
            column="value",
        )
        self.assertEqual(item["status"], "success")
        self.assertNotIn("upstream_validation", item)

    def test_08_streaming_tiff_histogram(self):
        item = server.create_histogram(
            str(self.tiff),
            self.output("tiff-histogram.png"),
        )
        self.assertEqual(item["statistics"]["count"], self.volume.size)
        self.assertEqual(
            item["provenance"]["statistics_source"],
            "streamed_tiff_pages",
        )

    def test_09_bar_chart(self):
        item = server.create_bar_chart(
            str(self.csv),
            self.output("bar.png"),
            column="category",
        )
        self.assertEqual(item["statistics"]["category_count"], 2)

    def test_10_slice_visualization(self):
        item = server.visualize_slice(
            str(self.npy),
            self.output("slice.png"),
            slice_index=2,
        )
        self.assertEqual(item["status"], "success")
        self.assertEqual(item["statistics"]["selected_index"], 2)

    def test_11_orthogonal_views(self):
        item = server.create_orthogonal_views(
            str(self.npy),
            self.output("orthogonal.png"),
        )
        self.assertEqual(item["statistics"]["indices"], [2, 5, 6])

    def test_12_slice_trend(self):
        item = server.plot_slice_trend(
            str(self.tiff),
            self.output("trend.png"),
        )
        self.assertEqual(item["provenance"]["pages_processed"], 5)

    def test_13_segmentation_overlay(self):
        item = server.overlay_segmentation(
            str(self.npy),
            str(self.mask_npy),
            self.output("overlay.png"),
            slice_index=2,
        )
        self.assertGreater(item["statistics"]["foreground_pixels"], 0)

    def test_14_mask_comparison(self):
        item = server.compare_masks(
            str(self.prediction_npy),
            str(self.mask_npy),
            self.output("compare.png"),
            slice_index=2,
        )
        self.assertGreater(item["statistics"]["false_positive"], 0)
        self.assertLess(item["statistics"]["dice"], 1.0)

    def test_15_generic_graph_rendering(self):
        item = server.render_graph(
            str(self.graph),
            self.output("graph.png"),
        )
        self.assertEqual(item["statistics"]["junction_count"], 3)
        self.assertEqual(item["statistics"]["strut_count"], 2)

    def test_16_optional_validation_context(self):
        item = server.create_histogram(
            str(self.csv),
            self.output("validated.png"),
            column="value",
            validation_report_filepath=str(self.validation),
        )
        self.assertEqual(
            item["upstream_validation"]["decision"],
            "PASS_WITH_WARNINGS",
        )
        self.assertIn("Synthetic upstream warning", item["warnings"])

    def test_17_manifest_update(self):
        manifest = self.root / "manifest.json"
        item = server.create_bar_chart(
            str(self.csv),
            self.output("manifested.png"),
            column="category",
            manifest_filepath=str(manifest),
        )
        stored = json.loads(manifest.read_text(encoding="utf-8"))
        self.assertEqual(item["status"], "success")
        self.assertEqual(len(stored["artifacts"]), 1)

    def test_18_overwrite_protection(self):
        output = self.output("protected.png")
        first = server.visualize_slice(str(self.npy), output, slice_index=2)
        second = server.visualize_slice(str(self.npy), output, slice_index=2)
        self.assertEqual(first["status"], "success")
        self.assertEqual(second["status"], "error")

    def test_19_invalid_input_is_structured_error(self):
        item = server.create_histogram(
            str(self.root / "missing.csv"),
            self.output("missing.png"),
            column="value",
        )
        self.assertEqual(item["status"], "error")
        self.assertEqual(item["error_type"], "ValueError")
        self.assertIsNone(item["output_path"])

    def test_20_existing_challenge_tools_remain_registered(self):
        names = self.tool_names()
        self.assertIn("segment_ct_global_threshold", names)
        self.assertIn("segment_ct_brightness_corrected", names)
        self.assertIn("skeletonize", names)
        self.assertIn("inspect_lattice_dataset", names)

    def test_21_global_segmentation_is_explicit_baseline(self):
        output = self.root / "global-mask.tif"
        result = server.segment_ct_global_threshold(
            str(self.tiff),
            str(output),
            threshold=15,
        )
        stored = tifffile.imread(output)
        self.assertEqual(result["method"], "global_threshold")
        self.assertEqual(result["mask_encoding"], "0/255")
        self.assertTrue(set(np.unique(stored)).issubset({0, 255}))

    def test_22_brightness_corrected_wrapper_delegates(self):
        output = self.root / "adaptive-mask.tif"
        result = server.segment_ct_brightness_corrected(
            str(self.tiff),
            str(output),
            reference_slice=2,
            reference_threshold=15,
            smoothing_sigma=0,
        )
        self.assertEqual(
            result["method"],
            "smoothed_slice_median_brightness_correction",
        )
        self.assertTrue(output.is_file())

    def test_23_skeleton_mcp_wrapper_executes(self):
        output = self.root / "skeleton.tif"
        message = server.skeletonize(str(self.mask_npy), str(output))
        self.assertTrue(output.is_file())
        self.assertIn("Skeletonized", message)


if __name__ == "__main__":
    unittest.main()
