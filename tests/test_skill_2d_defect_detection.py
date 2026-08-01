import unittest
from src.skill_2d_defect_detection import classify


class CandidateLabelsTest(unittest.TestCase):
    def test_only_contract_labels_are_possible(self):
        cases = [
            ({"fill_ratio": .01, "max_gap_length": 20, "connectivity": False}, "possible_missing"),
            ({"fill_ratio": .16, "max_gap_length": 12, "connectivity": False}, "uncertain"),
            ({"fill_ratio": .55, "max_gap_length": 10, "connectivity": False}, "possible_broken"),
        ]
        for metrics, expected in cases:
            self.assertEqual(classify(metrics, 1., 7)[0], expected)

