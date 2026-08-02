"""Contract tests for the specimen and spatial-calibration registry."""

from __future__ import annotations

import json
import math
from pathlib import Path
import unittest


ROOT = Path(__file__).parents[1]
REGISTRY = ROOT / "config" / "specimen_metadata.json"
ALLOWED_STATUSES = {
    "verified",
    "provided",
    "inferred",
    "assumed",
    "unknown",
    "conflicting",
}


class SpecimenMetadataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        cls.defaults = cls.registry["defaults"]
        cls.specimens = cls.registry["specimens"]

    def test_registry_contract(self) -> None:
        self.assertEqual(self.registry["schema_version"], "1.0")
        self.assertEqual(
            set(self.registry["metadata_status_vocabulary"]),
            ALLOWED_STATUSES,
        )
        self.assertEqual(
            self.defaults["voxel_size_order"],
            ["x", "y", "z"],
        )
        self.assertEqual(
            self.defaults["array_axis_order"],
            ["z", "y", "x"],
        )
        self.assertEqual(
            self.defaults["voxel_size_units"],
            "micrometer",
        )

    def test_specimen_ids_and_aliases_are_unique(self) -> None:
        specimen_ids = [item["specimen_id"] for item in self.specimens]
        self.assertEqual(len(specimen_ids), len(set(specimen_ids)))

        aliases: dict[str, str] = {}
        for specimen in self.specimens:
            self.assertIn(specimen["specimen_id"], specimen["aliases"])
            for alias in specimen["aliases"]:
                normalized = alias.casefold().strip()
                self.assertNotIn(
                    normalized,
                    aliases,
                    msg=(
                        f"alias {alias!r} is shared by "
                        f"{aliases.get(normalized)!r} and "
                        f"{specimen['specimen_id']!r}"
                    ),
                )
                aliases[normalized] = specimen["specimen_id"]

    def test_voxel_sizes_are_positive_xyz_triplets(self) -> None:
        for specimen in self.specimens:
            spacing = specimen["voxel_size_xyz_um"]
            self.assertEqual(len(spacing), 3, specimen["specimen_id"])
            for value in spacing:
                self.assertIsInstance(value, (int, float))
                self.assertTrue(math.isfinite(value))
                self.assertGreater(value, 0)

            self.assertIn(
                specimen["voxel_size_status"],
                ALLOWED_STATUSES,
            )
            self.assertIn(
                specimen["axis_mapping_status"],
                ALLOWED_STATUSES,
            )
            self.assertIn(
                specimen["voxel_size_source"],
                self.registry["sources"],
            )

    def test_design_metadata_is_conservative(self) -> None:
        for specimen in self.specimens:
            missing = specimen["intended_missing_strut_percent"]
            if missing is not None:
                self.assertGreaterEqual(missing, 0.0)
                self.assertLessEqual(missing, 100.0)

            self.assertIn(
                specimen["design_family_status"],
                ALLOWED_STATUSES,
            )
            self.assertIn(
                specimen["intended_missing_strut_status"],
                ALLOWED_STATUSES,
            )

        cubic = {
            item["specimen_id"]: item
            for item in self.specimens
            if item["specimen_id"].endswith("_cubic")
        }
        self.assertEqual(set(cubic), {"0_1_cubic", "0_2_cubic"})
        for specimen in cubic.values():
            self.assertEqual(specimen["lattice_type"], "unknown")
            self.assertEqual(specimen["design_family_status"], "unknown")
            self.assertIsNone(
                specimen["intended_missing_strut_percent"]
            )

    def test_nominal_values_are_not_acceptance_rules(self) -> None:
        self.assertEqual(
            self.defaults["nominal_strut_diameter_um"],
            350.0,
        )
        self.assertEqual(
            self.defaults["nominal_relative_density_fraction"],
            0.1,
        )
        self.assertFalse(
            self.defaults[
                "nominal_strut_diameter_is_acceptance_threshold"
            ]
        )
        self.assertEqual(
            self.defaults["thickness_analysis_mode"],
            "exploratory_distribution",
        )
        self.assertFalse(
            self.defaults["thin_defect_classification_permitted"]
        )


if __name__ == "__main__":
    unittest.main()
