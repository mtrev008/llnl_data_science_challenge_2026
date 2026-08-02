#!/usr/bin/env python
"""Map spatial defect markers to registered lattice edges and write one CSV."""
from __future__ import annotations

import argparse
import csv
import json
import math
from collections import Counter
from pathlib import Path

import numpy as np


def load_graph(path: Path) -> tuple[dict[int, np.ndarray], list[dict]]:
    """Load and validate registered graph junctions and struts."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    positions: dict[int, np.ndarray] = {}
    for record in payload.get("junctions", []):
        node_id, position = record.get("id"), record.get("position")
        if not isinstance(node_id, int) or node_id in positions:
            raise ValueError(f"invalid or duplicate junction ID: {node_id!r}")
        if (
            not isinstance(position, list)
            or len(position) != 3
            or not all(isinstance(value, (int, float)) and math.isfinite(value) for value in position)
        ):
            raise ValueError(f"junction {node_id!r} has an invalid position")
        positions[node_id] = np.asarray(position, dtype=float)

    edges: list[dict] = []
    edge_ids: set[int] = set()
    for record in payload.get("struts", []):
        edge_id = record.get("id")
        first, second = record.get("junction0"), record.get("junction1")
        if not isinstance(edge_id, int) or edge_id in edge_ids:
            raise ValueError(f"invalid or duplicate strut ID: {edge_id!r}")
        if first not in positions or second not in positions or first == second:
            raise ValueError(f"strut {edge_id!r} has invalid endpoints")
        edge_ids.add(edge_id)
        edges.append({"id": edge_id, "junction0": first, "junction1": second})
    if not positions or not edges:
        raise ValueError("graph must contain valid junctions and struts")
    return positions, edges


def load_candidates(path: Path) -> list[dict]:
    """Load defect candidates and convert their ZYX marker to canonical XYZ."""
    required = {"strut_id", "endpoint0", "endpoint1", "z", "y", "x", "classification"}
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise ValueError(f"candidate CSV must contain {sorted(required)}")
        rows = list(reader)

    candidates, seen_ids = [], set()
    for row in rows:
        candidate_id = int(row["strut_id"])
        if candidate_id in seen_ids:
            raise ValueError(f"duplicate candidate ID: {candidate_id}")
        seen_ids.add(candidate_id)
        point = np.asarray([float(row["x"]), float(row["y"]), float(row["z"])], dtype=float)
        if not np.all(np.isfinite(point)):
            raise ValueError(f"candidate {candidate_id} has non-finite coordinates")
        candidates.append(
            {
                "candidate_id": candidate_id,
                "classification": row["classification"],
                "source_endpoint0": int(row["endpoint0"]),
                "source_endpoint1": int(row["endpoint1"]),
                "point_xyz": point,
            }
        )
    return candidates


def build_edge_arrays(
    positions: dict[int, np.ndarray],
    edges: list[dict],
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Create vectorized edge endpoint and direction arrays."""
    starts = np.asarray([positions[edge["junction0"]] for edge in edges])
    ends = np.asarray([positions[edge["junction1"]] for edge in edges])
    vectors = ends - starts
    squared_lengths = np.einsum("ij,ij->i", vectors, vectors)
    if np.any(~np.isfinite(squared_lengths)) or np.any(squared_lengths <= 0):
        raise ValueError("graph contains a non-finite or zero-length strut")
    return starts, ends, vectors, squared_lengths


def rank_edges(
    point: np.ndarray,
    edges: list[dict],
    starts: np.ndarray,
    vectors: np.ndarray,
    squared_lengths: np.ndarray,
    count: int = 2,
) -> list[dict]:
    """Rank registered finite edge segments by Euclidean point distance."""
    projection = np.einsum("ij,ij->i", point - starts, vectors) / squared_lengths
    clamped = np.clip(projection, 0.0, 1.0)
    closest = starts + clamped[:, None] * vectors
    distances = np.linalg.norm(point - closest, axis=1)
    edge_id_array = np.asarray([edge["id"] for edge in edges])
    order = np.lexsort((edge_id_array, distances))[:count]
    return [
        {
            **edges[int(index)],
            "distance": float(distances[index]),
            "projection_fraction": float(clamped[index]),
            "unclamped_projection_fraction": float(projection[index]),
            "closest_point": closest[index],
        }
        for index in order
    ]


def initial_status(
    best: dict,
    second: dict,
    maximum_distance: float,
    minimum_runner_up_gap: float,
) -> tuple[str, str]:
    """Apply deterministic geometric validation gates."""
    if best["distance"] > maximum_distance:
        return "unmatched", "nearest edge exceeds maximum distance"
    gap = second["distance"] - best["distance"]
    if gap < minimum_runner_up_gap:
        return "ambiguous", "nearest and second-nearest edges are insufficiently separated"
    return "geometry_validated_unique", "distance and runner-up separation gates passed"


def map_candidates(
    candidates: list[dict],
    positions: dict[int, np.ndarray],
    edges: list[dict],
    voxel_size_um: float,
    maximum_distance: float,
    minimum_runner_up_gap: float,
) -> list[dict]:
    """Map candidates, then reject duplicate candidate assignments."""
    starts, _, vectors, squared_lengths = build_edge_arrays(positions, edges)
    results = []
    for candidate in candidates:
        best, second = rank_edges(
            candidate["point_xyz"], edges, starts, vectors, squared_lengths, count=2
        )
        status, reason = initial_status(
            best, second, maximum_distance, minimum_runner_up_gap
        )
        point = candidate["point_xyz"]
        results.append(
            {
                "candidate_id": candidate["candidate_id"],
                "classification": candidate["classification"],
                "candidate_x": float(point[0]),
                "candidate_y": float(point[1]),
                "candidate_z": float(point[2]),
                "source_endpoint0": candidate["source_endpoint0"],
                "source_endpoint1": candidate["source_endpoint1"],
                "matched_edge_id": best["id"],
                "matched_junction0": best["junction0"],
                "matched_junction1": best["junction1"],
                "nearest_distance_voxels": best["distance"],
                "nearest_distance_um": best["distance"] * voxel_size_um,
                "projection_fraction": best["projection_fraction"],
                "closest_point_x": float(best["closest_point"][0]),
                "closest_point_y": float(best["closest_point"][1]),
                "closest_point_z": float(best["closest_point"][2]),
                "second_edge_id": second["id"],
                "second_distance_voxels": second["distance"],
                "best_second_gap_voxels": second["distance"] - best["distance"],
                "mapping_method": "nearest_registered_finite_edge_segment",
                "mapping_status": status,
                "validation_reason": reason,
                "manual_review_required": status != "geometry_validated_unique",
            }
        )

    accepted_counts = Counter(
        row["matched_edge_id"]
        for row in results
        if row["mapping_status"] == "geometry_validated_unique"
    )
    for row in results:
        if (
            row["mapping_status"] == "geometry_validated_unique"
            and accepted_counts[row["matched_edge_id"]] > 1
        ):
            row["mapping_status"] = "ambiguous_duplicate_edge"
            row["validation_reason"] = "multiple candidates select the same registered edge"
            row["manual_review_required"] = True
    return sorted(results, key=lambda row: row["candidate_id"])


def write_csv(path: Path, rows: list[dict]) -> None:
    """Write the single requested mapping artifact."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0]) if rows else [
        "candidate_id",
        "mapping_status",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--graph", required=True, type=Path)
    parser.add_argument("--candidates", required=True, type=Path)
    parser.add_argument("--voxel-size-um", required=True, type=float)
    parser.add_argument("--maximum-distance-voxels", type=float, default=6.0)
    parser.add_argument("--minimum-runner-up-gap-voxels", type=float, default=3.0)
    parser.add_argument("--output-csv", required=True, type=Path)
    args = parser.parse_args()
    if args.voxel_size_um <= 0:
        raise ValueError("--voxel-size-um must be positive")
    if args.maximum_distance_voxels <= 0:
        raise ValueError("--maximum-distance-voxels must be positive")
    if args.minimum_runner_up_gap_voxels < 0:
        raise ValueError("--minimum-runner-up-gap-voxels must be nonnegative")

    positions, edges = load_graph(args.graph)
    candidates = load_candidates(args.candidates)
    rows = map_candidates(
        candidates,
        positions,
        edges,
        args.voxel_size_um,
        args.maximum_distance_voxels,
        args.minimum_runner_up_gap_voxels,
    )
    write_csv(args.output_csv, rows)
    counts = Counter(row["mapping_status"] for row in rows)
    print(
        json.dumps(
            {
                "output_csv": str(args.output_csv),
                "candidate_count": len(rows),
                "mapping_status_counts": dict(counts),
            }
        )
    )


if __name__ == "__main__":
    main()
