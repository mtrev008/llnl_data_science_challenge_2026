from __future__ import annotations

import importlib.util
from pathlib import Path

import networkx as nx


SCRIPT = (
    Path(__file__).parents[1]
    / ".agents"
    / "applications_agent"
    / "topology-analysis"
    / "scripts"
    / "analyze_lattice_topology.py"
)
SPEC = importlib.util.spec_from_file_location("topology_analysis", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_boundary_edge_connectivity_counts_disjoint_routes():
    graph = nx.Graph()
    graph.add_edges_from(
        [
            ("lower", "a"),
            ("a", "upper"),
            ("lower", "b"),
            ("b", "upper"),
        ]
    )
    assert MODULE.boundary_edge_connectivity(graph, ["lower"], ["upper"]) == 2


def test_boundary_edge_connectivity_is_zero_when_disconnected():
    graph = nx.Graph()
    graph.add_edges_from([("lower", "a"), ("upper", "b")])
    assert MODULE.boundary_edge_connectivity(graph, ["lower"], ["upper"]) == 0
