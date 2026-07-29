import unittest

import numpy as np

from src import missing_strut_junction_analyzer as analysis


def intact_path(start, end, node):
    start = np.asarray(start, dtype=float)
    end = np.asarray(end, dtype=float)
    return {
        "start_type": "junction",
        "end_type": "junction",
        "start_node": node,
        "end_node": node + 1,
        "path_length_voxels": float(np.linalg.norm(end - start)),
        "points": np.asarray([start, end]),
    }


class LocalLengthTests(unittest.TestCase):
    def test_same_layer_local_median_rejects_outlier(self):
        paths = [
            intact_path((0, index * 5, 0), (20, index * 5, 0), 2 * index)
            for index in range(6)
        ]
        paths.append(intact_path((0, 40, 0), (200, 40, 0), 20))
        model = analysis.build_local_length_model(paths, minimum_samples=5)
        length, source, count = analysis.local_median_strut_length(
            (10, 12, 0), model
        )
        self.assertAlmostEqual(length, 20.0)
        self.assertEqual(source, "same_layer")
        self.assertGreaterEqual(count, 5)

    def test_global_fallback_when_local_region_is_sparse(self):
        paths = [
            intact_path((0, index * 100, 0), (20, index * 100, 0), 2 * index)
            for index in range(5)
        ]
        model = analysis.build_local_length_model(paths, minimum_samples=5)
        length, source, _ = analysis.local_median_strut_length(
            (10, 0, 0), model
        )
        self.assertAlmostEqual(length, 20.0)
        self.assertEqual(source, "global_fallback")


class ConfigurationTests(unittest.TestCase):
    def test_requested_defaults(self):
        self.assertEqual(analysis.PREDICTION_MERGE_TOLERANCE, 0.60)
        self.assertEqual(analysis.MIN_MERGED_JUNCTION_SUPPORT, 6)
        self.assertEqual(analysis.MISSING_STRUTS_PER_MISSING_JUNCTION, 12)
        self.assertEqual(analysis.LOCAL_LENGTH_MIN_SAMPLES, 5)
        self.assertEqual(
            analysis.POTENTIAL_DEFECT_UNSUPPORTED_RUN_FRACTION, 0.10
        )


class MissingStrutCandidateClassificationTests(unittest.TestCase):
    def test_missing_takes_precedence_at_55_percent_coverage(self):
        self.assertEqual(
            analysis.classify_missing_strut_candidate(0.55, 0.50),
            "missing",
        )

    def test_above_55_percent_with_10_percent_gap_is_potential_defect(self):
        self.assertEqual(
            analysis.classify_missing_strut_candidate(0.550001, 0.10),
            "potential_defect",
        )

    def test_gap_below_10_percent_is_not_reported(self):
        self.assertEqual(
            analysis.classify_missing_strut_candidate(0.70, 0.099999),
            "likely_present",
        )

    def test_threshold_is_configurable(self):
        self.assertEqual(
            analysis.classify_missing_strut_candidate(
                0.70, 0.10, potential_defect_run_fraction=0.15
            ),
            "likely_present",
        )

    def test_fragmented_absence_does_not_form_one_10_percent_gap(self):
        supported = np.ones(100, dtype=bool)
        supported[::5] = False
        longest = analysis._longest_false_fraction(supported)
        self.assertEqual(longest, 0.01)
        self.assertEqual(
            analysis.classify_missing_strut_candidate(0.80, longest),
            "likely_present",
        )


class ScanBoundaryTests(unittest.TestCase):
    def test_scan_boundary_distance_is_signed(self):
        distances = analysis.scan_boundary_distances(
            [[0.0, 5.0, 5.0], [-1.0, 5.0, 5.0], [5.0, 5.0, 5.0]],
            None,
            (11, 11, 11),
        )
        self.assertEqual(distances.tolist(), [0.0, -1.0, 5.0])



if __name__ == "__main__":
    unittest.main()
