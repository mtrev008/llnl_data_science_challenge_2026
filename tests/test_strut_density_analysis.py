import unittest

import numpy as np

from src.strut_density_analysis import (
    _centerline_xyz,
    _longest_internal_false_run,
    _low_density_by_slice,
    _otsu_threshold,
    _perpendicular_disk_xyz,
    _validate_weights,
    analyze_density,
)


class DensityHelpersTest(unittest.TestCase):
    def test_weights_must_sum_to_one(self):
        _validate_weights((0.3, 0.3, 0.25, 0.15))
        with self.assertRaises(ValueError):
            _validate_weights((0.3, 0.3, 0.3, 0.3))

    def test_centerline_removes_duplicate_voxels(self):
        line = _centerline_xyz(np.array([0.0, 0.0, 0.0]), np.array([3.0, 0.0, 0.0]))
        self.assertEqual(len(line), 4)

    def test_disk_is_perpendicular_and_bounded(self):
        disk = _perpendicular_disk_xyz(
            np.array([0.0, 0.0, 0.0]), np.array([4.0, 0.0, 0.0]), 2
        )
        self.assertTrue(np.allclose(disk[:, 0], 0.0))
        self.assertTrue(np.all(np.linalg.norm(disk, axis=1) <= 2.0 + 1e-9))

    def test_internal_gap_ignores_terminal_absence(self):
        values = np.array([False, False, True, False, False, True, False])
        self.assertEqual(_longest_internal_false_run(values), 2)

    def test_otsu_separates_two_clusters(self):
        values = np.r_[np.full(20, 0.1), np.full(80, 0.9)]
        threshold = _otsu_threshold(values)
        self.assertGreater(threshold, 0.1)
        self.assertLess(threshold, 0.9)


class SyntheticDensityTest(unittest.TestCase):
    def test_present_and_missing_struts(self):
        shape = (20, 20, 20)
        raw = np.zeros(shape, dtype=np.uint16)
        mask = np.zeros(shape, dtype=np.uint8)
        mask[5:15, 4:7, 4:7] = 1
        raw[5:15, 4:7, 4:7] = 1000
        junctions = {
            0: np.array([5.0, 5.0, 5.0]),
            1: np.array([5.0, 5.0, 14.0]),
            2: np.array([14.0, 14.0, 5.0]),
            3: np.array([14.0, 14.0, 14.0]),
        }
        struts = [
            {
                "id": 0,
                "junction0": 0,
                "junction1": 1,
                "unit_cell_edge_idx": 0,
                "thickness": 0.1,
            },
            {
                "id": 1,
                "junction0": 2,
                "junction1": 3,
                "unit_cell_edge_idx": 1,
                "thickness": 0.1,
            },
        ]
        cells = [{"id": 0, "struts": [0, 1], "indices": [0, 0, 0]}]
        rows, cell_rows, threshold = analyze_density(
            raw,
            mask,
            junctions,
            struts,
            cells,
            target_um=4.0,
            search_radius_voxels=1,
            weights=(0.3, 0.3, 0.25, 0.15),
            uncertainty_margin=0.05,
            signal_disagreement=0.25,
            raw_support_threshold=0.5,
        )
        self.assertEqual(len(rows), 2)
        self.assertEqual(len(cell_rows), 1)
        self.assertGreaterEqual(threshold, 0.0)
        classes = {row["strut_id"]: row["classification"] for row in rows}
        self.assertEqual(classes[1], "missing")
        self.assertGreater(rows[0]["density_score"], rows[1]["density_score"])

    def test_low_density_slice_counts_follow_json_centerline(self):
        rows = [
            {
                "strut_id": 7,
                "classification": "low_density",
                "start_x": 1.0,
                "start_y": 1.0,
                "start_z": 2.0,
                "end_x": 1.0,
                "end_y": 1.0,
                "end_z": 4.0,
            },
            {
                "strut_id": 8,
                "classification": "present",
                "start_x": 1.0,
                "start_y": 1.0,
                "start_z": 2.0,
                "end_x": 1.0,
                "end_y": 1.0,
                "end_z": 4.0,
            },
        ]
        result = _low_density_by_slice(rows, 6)
        self.assertEqual([result[i]["low_density_strut_count"] for i in range(6)], [0, 0, 1, 1, 1, 0])
        self.assertEqual(result[3]["strut_ids"], "7")


if __name__ == "__main__":
    unittest.main()
