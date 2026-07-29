import csv
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import numpy as np

from src import strut_thickness_analysis as analysis


class TopologySensitivityTests(unittest.TestCase):
    def test_requested_tolerances(self):
        self.assertEqual(analysis.MIN_MISSING_JUNCTION_SUPPORT, 3)
        self.assertEqual(
            analysis.JUNCTION_PREDICTION_POSITION_TOLERANCE, 0.25
        )
        self.assertEqual(analysis.PREDICTION_POSITION_TOLERANCE, 0.35)
        self.assertEqual(analysis.PREDICTION_MERGE_TOLERANCE, 0.60)
        self.assertEqual(analysis.TEMPLATE_ANGLE_TOLERANCE_DEGREES, 15.0)
        self.assertEqual(analysis.TEMPLATE_MIN_LENGTH_RATIO, 0.75)
        self.assertEqual(analysis.TEMPLATE_MAX_LENGTH_RATIO, 1.30)
        self.assertEqual(analysis.ENDPOINT_ANGLE_TOLERANCE_DEGREES, 40.0)
        self.assertEqual(analysis.RELATIVE_THIN_RATIO, 0.60)
        self.assertEqual(analysis.MIN_SUSTAINED_THIN_SAMPLES, 2)
        self.assertEqual(analysis.MAX_TRACK_GAP_SLICES, 2)
        self.assertEqual(analysis.CONSISTENT_STRUCTURE_SAMPLES, 3)
        self.assertEqual(analysis.JUNCTION_MAX_BOUNDARY_EXTENSION_SCALE, 0.30)
        self.assertEqual(analysis.EDGE_EXCLUSION_VOXELS, 2.0)
        self.assertEqual(analysis.STRUT_ENDPOINT_TRIM_FRACTION, 0.05)

    def test_topology_classification_boundaries(self):
        cases = (
            (0.800001, "likely_present"),
            (0.80, "potentially_broken"),
            (0.550001, "potentially_broken"),
            (0.55, "missing"),
            (0.0, "missing"),
        )
        for coverage, expected in cases:
            with self.subTest(coverage=coverage):
                self.assertEqual(
                    analysis.classify_topology_strut(coverage), expected
                )

    def test_slice_counts_separate_topology_classes(self):
        candidates = [
            {
                "candidate_id": 0,
                "slice": 2,
                "evidence": "tiff_topology_missing_strut",
            },
            {
                "candidate_id": 1,
                "slice": 2,
                "evidence": "tiff_topology_potentially_broken_strut",
            },
        ]
        rows = analysis.missing_candidates_by_slice(candidates, 4, [])
        self.assertEqual(rows[2]["missing_struts"], 1)
        self.assertEqual(rows[2]["potentially_broken_struts"], 1)


class ThreeDimensionalTrackingTests(unittest.TestCase):
    @staticmethod
    def observation(z, *, x=None, family=1, kind="missing_strut", confidence=0.8):
        x = float(z - 540) if x is None else float(x)
        return {
            "slice": z,
            "point": np.asarray([z, 100.0, x]),
            "anomaly_type": kind,
            "structural_family": family,
            "confidence": confidence,
            "source_id": 7,
        }

    def test_two_slice_dropout_is_one_full_range(self):
        observations = [
            self.observation(z)
            for z in list(range(540, 551)) + list(range(553, 579))
        ]
        tracks = analysis.track_anomaly_observations(
            observations, position_tolerance=2.0, max_gap_slices=2
        )
        self.assertEqual(len(tracks), 1)
        self.assertEqual((tracks[0]["z_min"], tracks[0]["z_max"]), (540, 578))
        self.assertEqual(tracks[0]["observed_slice_count"], 37)
        self.assertEqual(tracks[0]["bridged_gap_count"], 2)

    def test_three_slice_dropout_ends_track(self):
        observations = [
            self.observation(z)
            for z in list(range(540, 551)) + list(range(554, 579))
        ]
        tracks = analysis.track_anomaly_observations(
            observations, position_tolerance=2.0, max_gap_slices=2
        )
        self.assertEqual(
            [(track["z_min"], track["z_max"]) for track in tracks],
            [(540, 550), (554, 578)],
        )

    def test_structure_and_type_prevent_false_merges(self):
        observations = [
            self.observation(10, x=20, family=1),
            self.observation(11, x=20, family=2),
            self.observation(
                11, x=20, family=1, kind="missing_junction"
            ),
        ]
        tracks = analysis.track_anomaly_observations(
            observations, position_tolerance=5.0
        )
        self.assertEqual(len(tracks), 3)

    def test_short_horizontal_event_is_not_expanded(self):
        observations = [self.observation(42, x=10)]
        track = analysis.track_anomaly_observations(
            observations, position_tolerance=2.0
        )[0]
        self.assertEqual((track["z_min"], track["z_max"]), (42, 42))

    def test_per_slice_output_uses_track_range(self):
        candidate = {
            "candidate_id": 3,
            "slice": 11,
            "z_min": 10,
            "z_max": 12,
            "evidence": "tiff_topology_missing_strut",
        }
        rows = analysis.missing_candidates_by_slice([candidate], 20, [])
        self.assertEqual(
            [row["missing_struts"] for row in rows[9:14]],
            [0, 1, 1, 1, 0],
        )
        self.assertEqual(rows[10]["candidate_ids"], "3")

    def test_json_positions_do_not_affect_structure_priors(self):
        first = {
            "junctions": [
                {"id": 0, "position": [0, 0, 0]},
                {"id": 1, "position": [1, 0, 1]},
            ],
            "struts": [
                {
                    "id": 0,
                    "junction0": 0,
                    "junction1": 1,
                    "unit_cell_edge_idx": 4,
                }
            ],
        }
        second = json.loads(json.dumps(first))
        second["junctions"][0]["position"] = [800, -200, 90]
        second["junctions"][1]["position"] = [810, -150, 140]
        with tempfile.TemporaryDirectory() as directory:
            first_path = Path(directory) / "first.json"
            second_path = Path(directory) / "second.json"
            first_path.write_text(json.dumps(first))
            second_path.write_text(json.dumps(second))
            self.assertEqual(
                analysis.load_expected_structure(first_path),
                analysis.load_expected_structure(second_path),
            )


class JunctionPersistenceTests(unittest.TestCase):
    def test_one_slice_is_not_persistent(self):
        run = analysis.persistent_slice_group([540, 540])
        self.assertEqual(run, [540])
        self.assertLess(len(run), 2)

    def test_two_slices_are_persistent(self):
        self.assertEqual(analysis.persistent_slice_group([540, 541]), [540, 541])

    def test_two_slice_noise_gap_is_bridged(self):
        self.assertEqual(
            analysis.persistent_slice_group([540, 543]),
            [540, 543],
        )

    def test_three_slice_gap_starts_a_new_run(self):
        self.assertEqual(
            analysis.persistent_slice_group([540, 544, 545]),
            [544, 545],
        )

    def test_boundary_ignores_weak_voxels_until_stable_structure(self):
        mask = np.zeros((16, 5, 5), dtype=np.uint8)
        mask[1:4, 2, 2] = 1
        mask[10:13, 2, 2] = 1
        junction = {
            "point": np.asarray([5.5, 2.0, 2.0]),
            "proposal_points": np.asarray(
                [[5.0, 2.0, 2.0], [6.0, 2.0, 2.0]]
            ),
            "z_min": 5,
            "z_max": 6,
        }
        analysis.expand_junction_boundary(
            junction,
            mask,
            np.zeros_like(mask),
            None,
            None,
            None,
            0.0,
            (0, 15),
            20.0,
            0,
        )
        self.assertEqual((junction["z_min"], junction["z_max"]), (4, 9))
        self.assertEqual(junction["evidence_slices"], list(range(4, 10)))


class BoundaryExpansionTests(unittest.TestCase):
    def test_only_literal_two_voxel_hull_edge_is_excluded(self):
        model = {
            "normals": np.asarray([[1.0, 0.0, 0.0]]),
            "offsets": np.asarray([-10.0]),
            "normal_lengths": np.asarray([1.0]),
            "margin": 50.0,
        }
        eligible = analysis.points_in_scan_interior(
            [[7.0, 0.0, 0.0], [9.0, 0.0, 0.0]],
            model,
            margin_voxels=analysis.EDGE_EXCLUSION_VOXELS,
        )
        self.assertEqual(eligible.tolist(), [True, False])

    def test_isolated_support_does_not_truncate_absence(self):
        supported = [True, True, True, False, False, True, False, True, True, True]
        indices = analysis.expanded_absence_indices(supported)
        self.assertEqual(indices.tolist(), [3, 4, 5, 6])

    def test_stable_structure_stops_at_true_boundary(self):
        supported = [True, True, True, False, False, True, True, True]
        indices = analysis.expanded_absence_indices(supported)
        self.assertEqual(indices.tolist(), [3, 4])

    def test_all_absent_samples_retain_full_extent(self):
        indices = analysis.expanded_absence_indices([False] * 7)
        self.assertEqual(indices.tolist(), list(range(7)))


class VisualizationSelectionTests(unittest.TestCase):
    @staticmethod
    def defect(identifier, z_min, z_max, primary=True):
        return {
            "defect_id": identifier,
            "kind": "missing strut" if primary else "potentially broken strut",
            "source": {"strut_id": int(identifier.split(":")[-1])},
            "points": np.asarray(
                [
                    [z, 10.0 + z - z_min, 20.0 + z - z_min]
                    for z in range(z_min, z_max + 1)
                ]
            ),
            "z_min": z_min,
            "z_max": z_max,
            "evidence_slices": list(range(z_min, z_max + 1)),
            "evidence_center": 0.5 * (z_min + z_max),
            "primary": primary,
        }

    def test_one_layer_primary_then_only_needed_extra_slice(self):
        defects = [
            self.defect("topology:0", 10, 20),
            self.defect("topology:1", 12, 22),
            self.defect("topology:2", 15, 18),
            self.defect("topology:3", 21, 25, primary=False),
        ]
        selected, assignment = analysis.select_visualization_slices(defects, 40)
        self.assertEqual(selected, [17, 21])
        self.assertEqual(assignment["topology:0"], 17)
        self.assertEqual(assignment["topology:1"], 17)
        self.assertEqual(assignment["topology:2"], 17)
        self.assertEqual(assignment["topology:3"], 21)

    def test_separate_observed_layer_gets_its_own_primary(self):
        defects = [
            self.defect("topology:0", 10, 20),
            self.defect("topology:1", 52, 60),
        ]
        selected, _ = analysis.select_visualization_slices(defects, 40)
        self.assertEqual(selected, [15, 56])

    def test_single_defect_layer_is_never_skipped(self):
        defects = [
            self.defect("topology:0", 380, 402),
            self.defect("topology:1", 425, 425),
        ]
        selected, assignment = analysis.select_visualization_slices(defects, 40)
        self.assertIn(425, selected)
        self.assertEqual(assignment["topology:1"], 425)

    def test_range_overlap_without_evidence_does_not_cover_defect(self):
        first = self.defect("topology:0", 380, 420)
        second = self.defect("topology:1", 390, 430)
        second["evidence_slices"] = [425]
        second["evidence_center"] = 425.0
        selected, assignment = analysis.select_visualization_slices(
            [first, second], 40
        )
        self.assertIn(425, selected)
        self.assertEqual(assignment["topology:1"], 425)

    def test_interpolated_marker_matches_selected_slice(self):
        point = analysis._trajectory_point_at_slice(
            [[10, 100, 200], [20, 120, 240]],
            15,
        )
        self.assertEqual(point.tolist(), [15.0, 110.0, 220.0])


class ThicknessPauseTests(unittest.TestCase):
    def setUp(self):
        points = np.asarray(
            [[1, 5, 5], [2, 5, 5], [3, 5, 5], [4, 5, 5]],
            dtype=np.int32,
        )
        self.path = {
            "id": 0,
            "start_node": 0,
            "end_node": 1,
            "start_type": "junction",
            "end_type": "junction",
            "points": points,
            "thickness": np.asarray([10.0, 10.0, 2.0, 2.0]),
            "shaft_points": points,
            "shaft_thickness": np.asarray([10.0, 10.0, 2.0, 2.0]),
            "thickness_median_um": 6.0,
            "low_thickness": 2.0,
            "path_length_voxels": 13.0,
            "path_length_um": 13.0,
            "straight_length_voxels": 3.0,
            "straight_length_um": 3.0,
            "recentered_fraction": 0.0,
        }
        self.mask = np.zeros((8, 12, 12), dtype=np.uint8)
        self.skeleton = np.zeros_like(self.mask)

    def classify(self, enabled):
        with mock.patch.object(
            analysis,
            "sustained_relative_thin_evidence",
            return_value=(
                [3, 4],
                self.path["points"][2:],
                2,
            ),
        ):
            return analysis.classify_paths(
                [self.path],
                self.mask,
                self.skeleton,
                None,
                None,
                None,
                0.0,
                10.0,
                5.0,
                10.0,
                1.0,
                (1.0, 1.0, 1.0),
                enabled,
            )[0]

    def test_thickness_warning_is_paused_by_default(self):
        row = self.classify(False)
        self.assertEqual(row["classification"], "normal")
        self.assertEqual(row["evidence"], "none")
        self.assertEqual(row["evidence_slices"], "")

    def test_switch_reenables_preserved_thickness_warning(self):
        row = self.classify(True)
        self.assertEqual(row["classification"], "potentially_broken")
        self.assertEqual(row["evidence"], "thin")
        self.assertEqual(row["evidence_slices"], "3;4")


class TopologyPauseTests(unittest.TestCase):
    def test_topology_warning_is_paused_by_default(self):
        rows = [
            {"classification": "missing", "strut_id": 1},
            {"classification": "potentially_broken", "strut_id": 2},
        ]
        selected = analysis.reportable_topology_struts(rows)
        self.assertEqual([row["strut_id"] for row in selected], [1])

    def test_switch_reenables_preserved_topology_warning(self):
        rows = [
            {"classification": "missing", "strut_id": 1},
            {"classification": "potentially_broken", "strut_id": 2},
        ]
        selected = analysis.reportable_topology_struts(
            rows, include_potentially_broken=True
        )
        self.assertEqual([row["strut_id"] for row in selected], [1, 2])


class ValidatedBaselineTests(unittest.TestCase):
    def test_generated_output_retains_validated_56_endpoint_pairs(self):
        path = (
            Path(__file__).parents[1]
            / "data/missing_struts/analysis/strut_thickness_analysis"
            / "topology_strut_defects.csv"
        )
        with path.open(newline="", encoding="utf-8") as stream:
            rows = list(csv.DictReader(stream))
        endpoint_pairs = ";".join(
            sorted(
                ":".join(
                    sorted(
                        (row["endpoint0"], row["endpoint1"]),
                        key=int,
                    )
                )
                for row in rows
            )
        )
        self.assertEqual(len(rows), 56)
        self.assertTrue(
            all(row["classification"] == "missing" for row in rows)
        )
        self.assertEqual(
            hashlib.sha256(endpoint_pairs.encode()).hexdigest(),
            "dbeab2265599d45b87d3e941d9b3291385e66b0717533ad61a8286e73c7b30ae",
        )


if __name__ == "__main__":
    unittest.main()
