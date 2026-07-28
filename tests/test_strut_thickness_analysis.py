import unittest

from src import strut_thickness_analysis as analysis


class TopologySensitivityTests(unittest.TestCase):
    def test_requested_tolerances(self):
        self.assertEqual(analysis.MIN_MISSING_JUNCTION_SUPPORT, 2)
        self.assertEqual(analysis.PREDICTION_POSITION_TOLERANCE, 0.25)
        self.assertEqual(analysis.PREDICTION_MERGE_TOLERANCE, 0.60)
        self.assertEqual(analysis.TEMPLATE_ANGLE_TOLERANCE_DEGREES, 15.0)
        self.assertEqual(analysis.TEMPLATE_MIN_LENGTH_RATIO, 0.75)
        self.assertEqual(analysis.TEMPLATE_MAX_LENGTH_RATIO, 1.30)
        self.assertEqual(analysis.ENDPOINT_ANGLE_TOLERANCE_DEGREES, 30.0)

    def test_topology_classification_boundaries(self):
        cases = (
            (0.700001, "likely_present"),
            (0.70, "potentially_broken"),
            (0.450001, "potentially_broken"),
            (0.45, "missing"),
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


if __name__ == "__main__":
    unittest.main()
