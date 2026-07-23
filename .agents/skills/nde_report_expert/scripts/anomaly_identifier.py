#!/usr/bin/env python3
"""Build an observed lattice JSON and compare it with a registered design JSON."""

import argparse
from collections import Counter
import json
from pathlib import Path

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from scipy.spatial import cKDTree
import tifffile


def load_volume(path):
    if Path(path).suffix.lower() == ".npy":
        return np.load(path, mmap_mode="r", allow_pickle=False)
    return tifffile.memmap(path)


def observed_graph(segmentation, skeleton):
    skeleton_points = np.argwhere((np.asarray(skeleton) > 0) & (segmentation > 0))
    pairs = cKDTree(skeleton_points).query_pairs(
        np.sqrt(3) + 1e-6, output_type="ndarray"
    )
    rows = np.concatenate((pairs[:, 0], pairs[:, 1]))
    columns = np.concatenate((pairs[:, 1], pairs[:, 0]))
    graph = coo_matrix(
        (np.ones(len(rows), dtype=np.uint8), (rows, columns)),
        shape=(len(skeleton_points), len(skeleton_points)),
    ).tocsr()

    node_voxels = np.flatnonzero(np.diff(graph.indptr) != 2)
    node_graph = graph[node_voxels][:, node_voxels]
    node_count, node_labels = connected_components(node_graph, directed=False)
    voxel_node = np.full(len(skeleton_points), -1, dtype=np.int32)
    voxel_node[node_voxels] = node_labels

    junctions = []
    for node_id in range(node_count):
        coordinates = skeleton_points[node_voxels[node_labels == node_id]].mean(axis=0)
        junctions.append(
            {"id": node_id, "position": np.round(coordinates[::-1], 3).tolist()}
        )

    visited = np.zeros(len(skeleton_points), dtype=bool)
    connections = {}
    for voxel in node_voxels:
        start_node = int(voxel_node[voxel])
        for neighbor in graph.indices[graph.indptr[voxel] : graph.indptr[voxel + 1]]:
            if voxel_node[neighbor] >= 0 or visited[neighbor]:
                continue

            previous, current = voxel, int(neighbor)
            path = [voxel]
            while voxel_node[current] < 0:
                path.append(current)
                visited[current] = True
                neighbors = graph.indices[
                    graph.indptr[current] : graph.indptr[current + 1]
                ]
                next_voxel = neighbors[0] if neighbors[1] == previous else neighbors[1]
                previous, current = current, int(next_voxel)

            end_node = int(voxel_node[current])
            if start_node != end_node:
                path.append(current)
                connection = tuple(sorted((start_node, end_node)))
                if connection not in connections or len(path) > len(
                    connections[connection]
                ):
                    connections[connection] = path

    struts = [
        {
            "id": strut_id,
            "junction0": connection[0],
            "junction1": connection[1],
            "points": skeleton_points[path][:, ::-1].tolist(),
        }
        for strut_id, (connection, path) in enumerate(connections.items())
    ]
    return {"junctions": junctions, "struts": struts}


def longest_run(values):
    edges = np.diff(np.pad(values.astype(np.int8), 1))
    starts = np.flatnonzero(edges == 1)
    lengths = np.flatnonzero(edges == -1) - starts
    if not len(lengths):
        return 0, 0
    longest = int(np.argmax(lengths))
    return int(starts[longest]), int(lengths[longest])


def compare_graphs(reference, observed, matching_tolerance, maximum_gap_length):
    reference_junctions = {
        int(junction["id"]): np.asarray(junction["position"])
        for junction in reference["junctions"]
    }
    observed_points = np.vstack(
        [strut["points"] for strut in observed["struts"]]
        + [[junction["position"]] for junction in observed["junctions"]]
    )
    observed_tree = cKDTree(observed_points)

    anomalies = []
    for strut in reference["struts"]:
        start = reference_junctions[int(strut["junction0"])]
        end = reference_junctions[int(strut["junction1"])]
        count = int(np.ceil(np.linalg.norm(end - start))) + 1
        points = np.linspace(start, end, count)
        unsupported = observed_tree.query(points)[0] > matching_tolerance
        gap_start, gap_length = longest_run(unsupported)
        if gap_length > maximum_gap_length:
            anomalies.append(
                {
                    "strut_id": int(strut["id"]),
                    "points": points,
                    "slice": int(
                        round(points[gap_start + gap_length // 2, 2])
                    ),
                }
            )
    return anomalies


def local_maximum(volume, points, radius):
    voxels = np.rint(points).astype(int)
    values = np.full(len(points), -np.inf)
    shape = np.asarray(volume.shape)
    for offset in np.ndindex(*(2 * radius + 1,) * 3):
        coordinates = voxels + np.asarray(offset) - radius
        valid = np.all((coordinates >= 0) & (coordinates < shape), axis=1)
        coordinates = coordinates[valid]
        values[valid] = np.maximum(
            values[valid],
            volume[
                coordinates[:, 0],
                coordinates[:, 1],
                coordinates[:, 2],
            ],
        )
    return values


def verify_candidates(
    candidates,
    segmentation,
    raw_volume,
    minimum_strut_coverage,
    maximum_gap_length,
    minimum_raw_intensity,
    sampling_radius=2,
):
    slice_ranges = {}
    confirmed = []
    weak_segmentation = []

    for candidate in candidates:
        points = candidate["points"][:, ::-1]
        mask_present = local_maximum(segmentation, points, sampling_radius) > 0
        raw_values = local_maximum(raw_volume, points, sampling_radius)
        slices = np.clip(
            np.rint(points[:, 0]).astype(int), 0, raw_volume.shape[0] - 1
        )

        normalized = np.empty(len(points))
        for slice_index in np.unique(slices):
            if slice_index not in slice_ranges:
                image = np.asarray(raw_volume[slice_index])
                low = float(np.median(image))
                high = float(np.percentile(image, 99.5))
                slice_ranges[slice_index] = (low, max(high - low, 1.0))
            low, scale = slice_ranges[slice_index]
            selected = slices == slice_index
            normalized[selected] = np.clip(
                (raw_values[selected] - low) / scale, 0, 1
            )

        raw_present = normalized >= minimum_raw_intensity
        _, gap_length = longest_run(~(mask_present | raw_present))
        mask_coverage = float(mask_present.mean())
        raw_coverage = float(raw_present.mean())
        result = {
            "strut_id": candidate["strut_id"],
            "slice": candidate["slice"],
            "mask_coverage": mask_coverage,
            "raw_coverage": raw_coverage,
            "gap_length": gap_length,
        }

        if (
            mask_coverage >= minimum_strut_coverage
            or raw_coverage >= minimum_strut_coverage
            or gap_length <= maximum_gap_length
        ):
            weak_segmentation.append(result)
        else:
            confirmed.append(result)
    return confirmed, weak_segmentation


def markdown_summary(
    reference,
    candidates,
    confirmed,
    weak_segmentation,
    minimum_strut_coverage,
    maximum_gap_length,
    minimum_raw_intensity,
):
    expected = len(reference["struts"])
    percentage = 100 * len(confirmed) / expected
    top_slices = Counter(anomaly["slice"] for anomaly in confirmed).most_common(30)
    rows = "\n".join(
        f"| {slice_index} | {count} |" for slice_index, count in top_slices
    )
    return (
        "# 9x9x9 Lattice Anomaly Summary\n\n"
        f"- Total expected struts: **{expected}**\n"
        f"- Graph-level candidates: **{len(candidates)}**\n"
        f"- Weak-segmentation candidates: **{len(weak_segmentation)}**\n"
        f"- Confirmed anomalies: **{len(confirmed)}**\n"
        f"- Confirmed anomaly percentage: **{percentage:.2f}%**\n\n"
        "## Thresholds\n\n"
        f"- Minimum strut coverage: **{minimum_strut_coverage:.2f}**\n"
        f"- Maximum allowed gap length: **{maximum_gap_length} voxels**\n"
        f"- Minimum normalized raw CT intensity: **{minimum_raw_intensity:.2f}**\n\n"
        "## Top 30 slices with the most anomalies\n\n"
        "| Slice | Anomalies |\n"
        "|---:|---:|\n"
        f"{rows}\n"
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("segmentation", type=Path)
    parser.add_argument("skeleton", type=Path)
    parser.add_argument("raw_volume", type=Path)
    parser.add_argument("reference_json", type=Path)
    parser.add_argument("observed_json", type=Path)
    parser.add_argument("summary", type=Path)
    parser.add_argument("--matching-tolerance", type=float, default=10.0)
    parser.add_argument("--minimum-strut-coverage", type=float, default=0.35)
    parser.add_argument("--maximum-gap-length", type=int, default=10)
    parser.add_argument("--minimum-raw-intensity", type=float, default=0.50)
    args = parser.parse_args()

    segmentation = load_volume(args.segmentation)
    skeleton = load_volume(args.skeleton)
    raw_volume = load_volume(args.raw_volume)
    if not (segmentation.shape == skeleton.shape == raw_volume.shape):
        raise ValueError("segmentation, skeleton, and raw volume shapes differ")

    observed = observed_graph(segmentation, skeleton)
    args.observed_json.write_text(json.dumps(observed, indent=2) + "\n")

    reference = json.loads(args.reference_json.read_text())
    candidates = compare_graphs(
        reference, observed, args.matching_tolerance, args.maximum_gap_length
    )
    confirmed, weak_segmentation = verify_candidates(
        candidates,
        segmentation,
        raw_volume,
        args.minimum_strut_coverage,
        args.maximum_gap_length,
        args.minimum_raw_intensity,
    )
    args.summary.write_text(
        markdown_summary(
            reference,
            candidates,
            confirmed,
            weak_segmentation,
            args.minimum_strut_coverage,
            args.maximum_gap_length,
            args.minimum_raw_intensity,
        )
    )
    print(f"Observed lattice: {args.observed_json}")
    print(f"Anomaly summary: {args.summary}")


if __name__ == "__main__":
    main()
