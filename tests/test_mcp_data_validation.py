"""Integration tests for the complete MCP data-validation tool."""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np
import tifffile


ROOT = Path(__file__).parents[1]
os.environ.setdefault(
    "MPLCONFIGDIR",
    str(ROOT / "tmp" / "matplotlib-validation"),
)
sys.path.insert(0, str(ROOT / "src"))
import mcp_server as server  # noqa: E402


class MCPDataValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.tiff = self.root / "synthetic_0-1.tif"
        self.graph = self.root / "synthetic_0-1.json"
        self.output = self.root / "validation"

        z, y, x = np.mgrid[:4, :8, :10]
        volume = (100 + x + 2 * y + 3 * z).astype(np.uint16)
        tifffile.imwrite(
            self.tiff,
            volume,
            photometric="minisblack",
        )
        self.graph.write_text(
            json.dumps({
                "junctions": [
                    {"id": 0, "position": [1, 1, 1]},
                    {"id": 1, "position": [5, 1, 1]},
                    {"id": 2, "position": [5, 5, 2]},
                ],
                "struts": [
                    {"id": 0, "junction0": 0, "junction1": 1},
                    {"id": 1, "junction0": 1, "junction1": 2},
                ],
                "unit_cells": [],
            }),
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_complete_validation_tool_is_registered(self) -> None:
        tools = asyncio.run(server.mcp.list_tools())
        names = {tool.name for tool in tools}
        self.assertIn("validate_lattice_dataset", names)

    def test_complete_validation_writes_handoff_and_reports(self) -> None:
        result = server.validate_lattice_dataset(
            tiff_filepath=str(self.tiff),
            json_filepath=str(self.graph),
            output_directory=str(self.output),
            specimen_id="0-1",
            array_axis_order=["z", "y", "x"],
        )

        self.assertEqual(result["status"], "success")
        self.assertIn(
            result["decision"],
            {"PASS", "PASS_WITH_WARNINGS"},
        )
        self.assertEqual(result["specimen_id"], "0-1")
        self.assertTrue(
            result["measurement_permissions"][
                "physical_thickness_measurement_permitted"
            ]
        )
        self.assertFalse(
            result["measurement_permissions"][
                "thin_defect_classification_permitted"
            ]
        )

        for key in (
            "validation_report_json",
            "validation_report_markdown",
            "dataset_handoff_json",
        ):
            self.assertTrue(Path(result[key]).is_file(), key)

        plot_directory = Path(result["plot_directory"])
        self.assertFalse((plot_directory / "tiff_slice_mean.png").exists())
        self.assertFalse(
            (plot_directory / "tiff_slice_standard_deviation.png").exists()
        )

        handoff = json.loads(
            Path(result["dataset_handoff_json"]).read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(
            handoff["specimen_resolution"]["specimen"]["specimen_id"],
            "0-1",
        )
        self.assertIsNone(
            handoff["thickness_analysis_policy"][
                "acceptance_threshold_um"
            ]
        )

    def test_validation_tool_returns_structured_input_error(self) -> None:
        result = server.validate_lattice_dataset(
            tiff_filepath=str(self.root / "missing.tif"),
            json_filepath=str(self.graph),
            output_directory=str(self.output),
        )
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["error_type"], "FileNotFoundError")
        self.assertIsNone(result["dataset_handoff_json"])


if __name__ == "__main__":
    unittest.main()
