from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np


SCRIPT = (
    Path(__file__).parents[1]
    / ".agents"
    / "applications_agent"
    / "topology-analysis"
    / "scripts"
    / "map_candidates_to_edges.py"
)
SPEC = importlib.util.spec_from_file_location("candidate_edge_mapping", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_rank_edges_uses_finite_segments():
    edges = [
        {"id": 10, "junction0": 0, "junction1": 1},
        {"id": 11, "junction0": 2, "junction1": 3},
    ]
    positions = {
        0: np.array([0.0, 0.0, 0.0]),
        1: np.array([10.0, 0.0, 0.0]),
        2: np.array([0.0, 5.0, 0.0]),
        3: np.array([10.0, 5.0, 0.0]),
    }
    starts, _, vectors, squared = MODULE.build_edge_arrays(positions, edges)
    ranked = MODULE.rank_edges(
        np.array([4.0, 1.0, 0.0]), edges, starts, vectors, squared
    )
    assert ranked[0]["id"] == 10
    assert ranked[0]["distance"] == 1.0
    assert ranked[0]["projection_fraction"] == 0.4


def test_initial_status_applies_distance_and_separation_gates():
    best = {"distance": 2.0}
    second = {"distance": 10.0}
    assert MODULE.initial_status(best, second, 6.0, 3.0)[0] == "geometry_validated_unique"
    assert MODULE.initial_status({"distance": 7.0}, second, 6.0, 3.0)[0] == "unmatched"
    assert MODULE.initial_status(best, {"distance": 4.0}, 6.0, 3.0)[0] == "ambiguous"


def test_duplicate_edge_assignments_are_rejected():
    positions = {
        0: np.array([0.0, 0.0, 0.0]),
        1: np.array([10.0, 0.0, 0.0]),
        2: np.array([0.0, 20.0, 0.0]),
        3: np.array([10.0, 20.0, 0.0]),
    }
    edges = [
        {"id": 10, "junction0": 0, "junction1": 1},
        {"id": 11, "junction0": 2, "junction1": 3},
    ]
    candidates = [
        {"candidate_id": 1, "classification": "missing", "source_endpoint0": 8, "source_endpoint1": 9, "point_xyz": np.array([2.0, 1.0, 0.0])},
        {"candidate_id": 2, "classification": "missing", "source_endpoint0": 9, "source_endpoint1": 10, "point_xyz": np.array([8.0, 1.0, 0.0])},
    ]
    rows = MODULE.map_candidates(candidates, positions, edges, 1.0, 6.0, 3.0)
    assert {row["mapping_status"] for row in rows} == {"ambiguous_duplicate_edge"}
