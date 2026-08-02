from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


SCRIPT = (
    Path(__file__).parents[1]
    / ".agents"
    / "applications_agent"
    / "topology-analysis"
    / "scripts"
    / "define_coordinates_and_boundaries.py"
)
SPEC = importlib.util.spec_from_file_location("coordinate_boundaries", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_parse_fraction_list_sorts_and_deduplicates():
    assert MODULE.parse_fraction_list([0.1, 0.05, 0.1]) == [0.05, 0.1]
    with pytest.raises(ValueError):
        MODULE.parse_fraction_list([0.0])


def test_select_boundary_nodes_uses_axis_extent():
    positions = {
        0: (0.0, 0.0, 0.0),
        1: (0.0, 0.0, 1.0),
        2: (0.0, 0.0, 9.0),
        3: (0.0, 0.0, 10.0),
    }
    result = MODULE.select_boundary_nodes(positions, "z", 0.1)
    assert result["lower_node_ids"] == [0, 1]
    assert result["upper_node_ids"] == [2, 3]
    assert result["overlap_node_ids"] == []


def test_ct_bounds_converts_zyx_shape_to_xyz():
    positions = {0: (836.0, 814.0, 760.0)}
    result = MODULE.check_ct_bounds(positions, (761, 815, 837))
    assert result["ct_shape_xyz"] == [837, 815, 761]
    assert result["status"] == "numerically_plausible"


def test_ct_bounds_rejects_outside_node():
    positions = {0: (837.0, 0.0, 0.0)}
    result = MODULE.check_ct_bounds(positions, (761, 815, 837))
    assert result["status"] == "bounds_mismatch"
    assert result["outside_node_count"] == 1


def test_unique_location_count_handles_duplicate_records():
    positions = {
        0: (1.0, 2.0, 3.0),
        1: (1.0, 2.0, 3.0),
        2: (4.0, 5.0, 6.0),
    }
    assert MODULE.unique_location_count([0, 1, 2], positions) == 2


def test_physical_extents_are_scaled_per_axis():
    extents = {
        "x": {"span": 10.0},
        "y": {"span": 20.0},
        "z": {"span": 30.0},
    }
    result = MODULE.physical_extents(extents, (2.0, 3.0, 4.0))
    assert result["span_um"] == {"x": 20.0, "y": 60.0, "z": 120.0}
