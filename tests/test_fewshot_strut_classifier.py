from __future__ import annotations

import json
import unittest
from pathlib import Path

from src.fewshot_strut_classifier import CLASS_DEFINITIONS, choose_example_records, orientation_bucket


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = PROJECT_ROOT / "data" / "missing_struts" / "analysis" / "fewshot_strut_classifier" / "slice_review_manifest.json"
SEQUENCE_METADATA_PATH = (
    PROJECT_ROOT
    / "data"
    / "missing_struts"
    / "analysis"
    / "fewshot_strut_classifier"
    / "full_slice_review"
    / "sequence_001"
    / "metadata.json"
)
OUTPUT_PATH = PROJECT_ROOT / "data" / "missing_struts" / "analysis" / "per_strut_fewshot_defects.json"
class FewShotClassifierTests(unittest.TestCase):
    def test_orientation_bucket(self) -> None:
        self.assertEqual(orientation_bucket([1.0, 1.0, 1.0]), "xyz-diagonal")
        self.assertEqual(orientation_bucket([1.0, 1.0, 0.1]), "xy-diagonal")
        self.assertEqual(orientation_bucket([0.9, 0.1, 0.1]), "x-dominant")

    def test_choose_example_records_prefers_orientation_diversity(self) -> None:
        records = [
            {"predicted_label": "missing", "confidence": 0.9, "orientation_bucket": "xy-diagonal", "strut_id": 1},
            {"predicted_label": "missing", "confidence": 0.8, "orientation_bucket": "xy-diagonal", "strut_id": 2},
            {"predicted_label": "missing", "confidence": 0.7, "orientation_bucket": "xz-diagonal", "strut_id": 3},
            {"predicted_label": "present", "confidence": 0.9, "orientation_bucket": "xyz-diagonal", "strut_id": 4},
        ]
        selected = choose_example_records(records, max_examples_per_class=2)
        self.assertEqual([item["strut_id"] for item in selected["missing"]], [1, 3])

    def test_runtime_metadata_declares_clustering_exclusion(self) -> None:
        self.assertTrue(OUTPUT_PATH.exists(), "Classifier output JSON is missing; run the classifier first.")
        data = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
        self.assertEqual(
            data["metadata"]["runtime_inputs_exclude"],
            [
                "data/missing_struts/analysis/cluster_summary.json",
                "data/missing_struts/analysis/cluster_labels.json",
                "data/missing_struts/analysis/per_strut_defects.json",
            ],
        )

    def test_full_slice_review_manifest_schema(self) -> None:
        self.assertTrue(MANIFEST_PATH.exists(), "Slice review manifest is missing; run the classifier first.")
        data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        self.assertIn("metadata", data)
        self.assertEqual(data["metadata"]["review_type"], "single_full_tif_slice_sequence")
        self.assertEqual(data["metadata"]["image_type"], "raw_tif_full_slice")
        self.assertIn("sequences", data)
        self.assertEqual(len(data["sequences"]), 1)
        sequence = data["sequences"][0]
        self.assertEqual(sequence["sequence_id"], "sequence_001")
        self.assertEqual(
            sequence["slice_indices"],
            list(range(sequence["slice_indices"][0], sequence["slice_indices"][-1] + 1)),
        )
        self.assertTrue(any(path.endswith("slice_000.png") for path in sequence["slice_pngs"]))

    def test_full_slice_sequence_metadata_schema(self) -> None:
        self.assertTrue(SEQUENCE_METADATA_PATH.exists(), "Full-slice sequence metadata is missing.")
        data = json.loads(SEQUENCE_METADATA_PATH.read_text(encoding="utf-8"))
        self.assertEqual(data["image_type"], "raw_tif_full_slice")
        self.assertIsNone(data["crop_box_xyxy"])
        self.assertEqual(len(data["row_labels"]), len(data["slice_indices"]))
        for row_entry in data["row_labels"]:
            self.assertIn("slice_index", row_entry)
            self.assertIn("png", row_entry)
            self.assertGreater(row_entry["row_count"], 0)
            self.assertEqual(row_entry["row_count"], len(row_entry["rows"]))
            for row in row_entry["rows"]:
                self.assertIn("row", row)
                self.assertEqual(row["row_order"], "top_to_bottom")
                self.assertEqual(row["strut_order"], "left_to_right")
                self.assertNotIn("order", row)
                self.assertIn("strut_count", row)
                self.assertEqual(row["strut_count"], len(row["struts"]))
                self.assertGreater(row["strut_count"], 0)
                for strut in row["struts"]:
                    self.assertIn("position_in_row", strut)
                    self.assertIn("strut_id", strut)
                    self.assertIsNone(strut["label"])

    def test_output_schema(self) -> None:
        self.assertTrue(OUTPUT_PATH.exists(), "Classifier output JSON is missing; run the classifier first.")
        data = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
        self.assertEqual(data["status"], "passed")
        self.assertIn("metadata", data)
        self.assertEqual(data["metadata"]["slice_review_manifest_status"], "pending_human_review")
        self.assertIn("strut_records", data)
        self.assertGreater(len(data["strut_records"]), 0)
        first = data["strut_records"][0]
        for key in (
            "strut_id",
            "junction0",
            "junction1",
            "predicted_label",
            "confidence",
            "rationale",
            "evidence_bundle",
            "example_ids_used",
            "backend",
        ):
            self.assertIn(key, first)


if __name__ == "__main__":
    unittest.main()
