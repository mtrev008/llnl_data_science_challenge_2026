import json
from collections import Counter
from pathlib import Path
import tempfile
import unittest

import numpy as np

from src import missing_strut_junction_analyzer as analysis


class PerfectDesignPriorTests(unittest.TestCase):
    def test_json_coordinates_do_not_affect_topology_priors(self):
        design = {
            "junctions": [
                {"id": 1, "position": [7, 6, 5]},
                {"id": 2, "position": [9, 8, 7]},
            ],
            "struts": [
                {
                    "id": 3,
                    "junction0": 1,
                    "junction1": 2,
                    "unit_cell_edge_idx": 4,
                }
            ],
        }
        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "first.json"
            second = Path(directory) / "second.json"
            first.write_text(json.dumps(design))
            design["junctions"][0]["position"] = [900, -40, 17]
            design["junctions"][1]["position"] = [-300, 810, 61]
            second.write_text(json.dumps(design))
            self.assertEqual(
                analysis.load_expected_structure(first),
                analysis.load_expected_structure(second),
            )


class ExhaustiveTrackingTests(unittest.TestCase):
    @staticmethod
    def observation(z, source, *, y=4.0, family=2, kind="missing_strut"):
        return {
            "slice": z,
            "point": np.asarray([z, y, 4.0]),
            "anomaly_type": kind,
            "structural_family": family,
            "confidence": 0.9,
            "source_id": source,
        }

    def test_single_slice_anomaly_is_retained(self):
        tracks = analysis.track_anomaly_observations(
            [self.observation(8, 10)],
            position_tolerance=5.0,
        )
        self.assertEqual(len(tracks), 1)
        self.assertEqual(tracks[0]["representative_slice"], 8)

    def test_multiple_anomalies_on_one_slice_remain_independent(self):
        tracks = analysis.track_anomaly_observations(
            [
                self.observation(8, 10, y=4.0),
                self.observation(8, 11, y=9.0),
            ],
            position_tolerance=10.0,
        )
        self.assertEqual(len(tracks), 2)
        self.assertEqual(
            sorted(track["source_ids"][0] for track in tracks),
            [10, 11],
        )

    def test_consecutive_slices_merge_for_same_source(self):
        tracks = analysis.track_anomaly_observations(
            [self.observation(z, 10) for z in (8, 9, 10)],
            position_tolerance=5.0,
        )
        self.assertEqual(len(tracks), 1)
        self.assertEqual(
            (tracks[0]["z_min"], tracks[0]["z_max"]),
            (8, 10),
        )
        self.assertEqual(tracks[0]["representative_slice"], 9)

    def test_distinct_sources_do_not_merge_across_slices(self):
        tracks = analysis.track_anomaly_observations(
            [
                self.observation(3, 10),
                self.observation(4, 11),
            ],
            position_tolerance=5.0,
        )
        self.assertEqual(len(tracks), 2)

    def test_structure_and_type_prevent_false_merges(self):
        tracks = analysis.track_anomaly_observations(
            [
                self.observation(3, 10, family=1),
                self.observation(4, 10, family=2),
                self.observation(4, 10, family=1, kind="missing_junction"),
            ],
            position_tolerance=5.0,
        )
        self.assertEqual(len(tracks), 3)


class DetectionSelectionTests(unittest.TestCase):
    def test_requested_angle_tolerances_are_independent(self):
        self.assertEqual(analysis.ENDPOINT_ANGLE_TOLERANCE_DEGREES, 45.0)
        self.assertEqual(analysis.TEMPLATE_ANGLE_TOLERANCE_DEGREES, 15.0)

    def test_material_support_cutoffs_are_two_percent(self):
        self.assertEqual(analysis.RAW_MATERIAL_SUPPORT_FRACTION, 0.02)
        self.assertEqual(analysis.LOCAL_MATERIAL_SUPPORT_FRACTION, 0.02)

    def test_rule_counts_reconcile(self):
        diagnostics = Counter(
            {
                "template_paths_started": 20,
                "template_length_rejected": 2,
                "template_family_rejected": 3,
                "template_vectors_retained": 15,
                "template_projections_started": 100,
                "endpoint_match_rejected": 40,
                "self_pair_rejected": 5,
                "observed_connection_rejected": 20,
                "duplicate_pair_rejected": 10,
                "unique_candidate_pairs": 25,
                "direction_tolerance_rejected": 4,
                "outside_valid_volume_rejected": 3,
                "insufficient_samples_rejected": 0,
                "material_evaluated": 18,
                "coverage_classified_present": 12,
                "coverage_classified_missing": 6,
                "final_missing_output": 6,
            }
        )
        analysis.validate_strut_rule_counts(diagnostics)
        summary = "\n".join(
            analysis.strut_rule_summary_lines(diagnostics, 18468, 0.55)
        )
        self.assertIn("coverage > 55%): 12", summary)
        self.assertIn("coverage <= 55%): 6", summary)
        self.assertIn("final missing-strut output: 6", summary)

    def test_rule_count_mismatch_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "template projections"):
            analysis.validate_strut_rule_counts(
                Counter({"template_projections_started": 1})
            )

    def test_only_missing_topology_struts_are_reported(self):
        struts = [
            {"strut_id": 1, "classification": "missing"},
            {"strut_id": 2, "classification": "potentially_broken"},
            {"strut_id": 3, "classification": "likely_present"},
        ]
        selected = analysis.reportable_topology_struts(struts)
        self.assertEqual([row["strut_id"] for row in selected], [1])

    def test_visualization_selection_covers_isolated_defect(self):
        defects = [
            {
                "defect_id": "topology:1",
                "kind": "missing strut",
                "source": {},
                "points": np.asarray([[425.0, 20.0, 30.0]]),
                "z_min": 425,
                "z_max": 425,
                "evidence_slices": [425],
                "evidence_center": 425.0,
                "primary": True,
            }
        ]
        selected, assignment = analysis.select_visualization_slices(defects, 40)
        self.assertEqual(selected, [425])
        self.assertEqual(assignment["topology:1"], 425)

    def test_missing_categories_keep_existing_visualization_colors(self):
        styles = analysis.VISUALIZATION_STYLES
        colors = {
            styles["missing strut"][0],
            styles["missing junction"][0],
        }
        self.assertEqual(colors, {"yellow", "magenta"})
        self.assertEqual(styles["potential defect"][0], "red")

    def test_summary_keeps_components_and_potential_defects_separate(self):
        direct = [{"local_length_source": "same_layer"}] * 2
        potential = [{"local_length_source": "same_layer"}] * 4
        junctions = [{"local_length_source": "same_layer"}]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "summary.md"
            analysis.write_missing_topology_summary(
                path,
                {"strut_count": None, "junction_count": None},
                [],
                direct,
                potential,
                junctions,
                (0, 10),
                [],
                2,
                Counter(),
                0.55,
            )
            summary = path.read_text()
        self.assertIn("- Missing struts: **14**", summary)
        self.assertIn("- Direct interior missing struts: **2**", summary)
        self.assertIn("- Junction-implied missing struts: **12**", summary)
        self.assertIn("- Potential defects: **4**", summary)


if __name__ == "__main__":
    unittest.main()
