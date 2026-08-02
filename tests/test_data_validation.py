"""Unit tests for specimen resolution and physical CT calibration."""

from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from data_validation_updated import (  # noqa: E402
    build_dataset_handoff,
    json_field_axis_labels,
    load_specimen_registry,
    resolve_spatial_calibration,
    resolve_specimen_metadata,
    validate_voxel_size_xyz,
)


REGISTRY_PATH = ROOT / "config" / "specimen_metadata.json"


class DataValidationCalibrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.registry = load_specimen_registry(REGISTRY_PATH)

    def specimen(self, specimen_id: str) -> dict:
        return next(
            item
            for item in self.registry["specimens"]
            if item["specimen_id"] == specimen_id
        )

    def test_anisotropic_0_1_xyz_to_zyx_calibration(self) -> None:
        result = resolve_spatial_calibration(
            shape=[100, 200, 300],
            tiff_axes="ZYX",
            registry_defaults=self.registry["defaults"],
            specimen_metadata=self.specimen("0-1"),
        )

        self.assertEqual(
            result["voxel_size_xyz_um"],
            [55.32, 58.41, 56.54],
        )
        self.assertEqual(
            result["array_spacing_um"],
            [56.54, 58.41, 55.32],
        )
        self.assertEqual(result["array_axis_order"], ["z", "y", "x"])
        self.assertEqual(
            result["physical_extent_xyz_mm"],
            [16.596, 11.682, 5.654],
        )
        self.assertTrue(
            result["measurement_readiness"][
                "physical_thickness_measurement_permitted"
            ]
        )
        self.assertFalse(
            result["measurement_readiness"][
                "thin_defect_classification_permitted"
            ]
        )
        self.assertLess(
            min(result["nominal_strut_voxels_across_xyz"]),
            10,
        )

    def test_explicit_axis_order_supports_nonstandard_arrays(self) -> None:
        result = resolve_spatial_calibration(
            shape=[300, 100, 200],
            tiff_axes="QYX",
            registry_defaults=self.registry["defaults"],
            specimen_metadata=self.specimen("0-1"),
            explicit_array_axis_order=["x", "z", "y"],
        )

        self.assertEqual(result["axis_mapping_status"], "provided")
        self.assertEqual(
            result["array_spacing_um"],
            [55.32, 56.54, 58.41],
        )
        self.assertEqual(
            result["physical_extent_xyz_mm"],
            [16.596, 11.682, 5.654],
        )

    def test_unknown_calibration_blocks_physical_measurement(self) -> None:
        result = resolve_spatial_calibration(
            shape=[10, 20, 30],
            tiff_axes="QYX",
            registry_defaults=self.registry["defaults"],
            specimen_metadata=None,
        )

        self.assertIsNone(result["voxel_size_xyz_um"])
        self.assertIsNone(result["physical_extent_xyz_mm"])
        self.assertFalse(
            result["measurement_readiness"][
                "physical_thickness_measurement_permitted"
            ]
        )
        self.assertTrue(
            result["measurement_readiness"]["segmentation_permitted"]
        )

    def test_explicit_registry_conflict_is_an_error(self) -> None:
        result = resolve_spatial_calibration(
            shape=[10, 20, 30],
            tiff_axes="ZYX",
            registry_defaults=self.registry["defaults"],
            specimen_metadata=self.specimen("0-1"),
            explicit_voxel_size_xyz_um=[58.1, 58.1, 58.1],
        )

        self.assertEqual(result["voxel_size_status"], "conflicting")
        self.assertTrue(result["errors"])
        self.assertFalse(
            result["measurement_readiness"][
                "physical_thickness_measurement_permitted"
            ]
        )

    def test_voxel_size_validation_rejects_invalid_values(self) -> None:
        for invalid in (
            [1.0, 2.0],
            [1.0, 2.0, 0.0],
            [1.0, -2.0, 3.0],
            [1.0, float("nan"), 3.0],
        ):
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):
                    validate_voxel_size_xyz(invalid)

    def test_json_plot_labels_do_not_invent_units(self) -> None:
        self.assertEqual(
            json_field_axis_labels("junctions", "position.x"),
            ("position.x (unit unknown)", "Junction count (records)"),
        )
        self.assertEqual(
            json_field_axis_labels("struts", "thickness"),
            ("thickness (unit unknown)", "Strut count (records)"),
        )
        self.assertEqual(
            json_field_axis_labels("unit_cells", "indices.i"),
            (
                "indices.i (index; dimensionless)",
                "Unit cell count (records)",
            ),
        )
        self.assertEqual(
            json_field_axis_labels(
                "unit_cells",
                "struts.__length__",
            ),
            (
                "struts per record (count; dimensionless)",
                "Unit cell count (records)",
            ),
        )

    def test_explicit_specimen_resolution(self) -> None:
        result = resolve_specimen_metadata(
            registry=self.registry,
            specimen_id="0-1",
            source_path=Path("unrelated-name.tif"),
        )
        self.assertEqual(result["status"], "provided")
        self.assertEqual(result["metadata"]["specimen_id"], "0-1")

    def test_unique_filename_alias_resolution(self) -> None:
        result = resolve_specimen_metadata(
            registry=self.registry,
            specimen_id=None,
            source_path=Path(
                "210127_Brian_Tran_strut_lattices_"
                "0point5dash1 1 Slices.tif"
            ),
        )
        self.assertEqual(result["status"], "inferred")
        self.assertEqual(result["metadata"]["specimen_id"], "0.5-1")

    def test_ambiguous_alias_is_not_guessed(self) -> None:
        registry = json.loads(json.dumps(self.registry))
        registry["specimens"][0]["aliases"] = ["shared"]
        registry["specimens"][1]["aliases"] = ["shared"]

        result = resolve_specimen_metadata(
            registry=registry,
            specimen_id=None,
            source_path=Path("scan_shared.tif"),
        )
        self.assertEqual(result["status"], "conflicting")
        self.assertIsNone(result["metadata"])
        self.assertEqual(set(result["candidates"]), {"0-1", "0-2"})

    def test_handoff_preserves_measurement_safeguards(self) -> None:
        specimen = self.specimen("0-1")
        resolution = {
            "status": "provided",
            "method": "explicit_specimen_id",
            "metadata": specimen,
            "candidates": ["0-1"],
        }
        calibration = resolve_spatial_calibration(
            shape=[100, 200, 300],
            tiff_axes="ZYX",
            registry_defaults=self.registry["defaults"],
            specimen_metadata=specimen,
        )
        report = {
            "decision": "PASS_WITH_WARNINGS",
            "errors": [],
            "warnings": calibration["warnings"],
            "inputs": {
                "tiff": "scan.tif",
                "json": "graph.json",
            },
            "tiff": {
                "shape": [100, 200, 300],
                "axes": "ZYX",
                "dtype": "uint16",
            },
            "specimen_resolution": resolution,
            "spatial_calibration": calibration,
        }

        handoff = build_dataset_handoff(
            report,
            self.registry["defaults"],
        )

        self.assertEqual(handoff["schema_version"], "1.0")
        self.assertEqual(
            handoff["specimen_resolution"]["specimen"]["specimen_id"],
            "0-1",
        )
        self.assertEqual(
            handoff["spatial_calibration"]["array_spacing_um"],
            [56.54, 58.41, 55.32],
        )
        self.assertTrue(
            handoff["measurement_permissions"][
                "physical_thickness_measurement_permitted"
            ]
        )
        self.assertFalse(
            handoff["measurement_permissions"][
                "thin_defect_classification_permitted"
            ]
        )
        self.assertIsNone(
            handoff["thickness_analysis_policy"][
                "acceptance_threshold_um"
            ]
        )
        self.assertFalse(
            handoff["nominal_geometry"][
                "strut_diameter_is_acceptance_threshold"
            ]
        )
        self.assertFalse(
            handoff["graph"][
                "coordinate_bounds_check_is_registration"
            ]
        )


if __name__ == "__main__":
    unittest.main()
