#!/usr/bin/env python3
"""Identify likely breaks in a segmented lattice using its 3-D skeleton.

The detector finds skeleton endpoints, removes endpoints that naturally occur on
the exterior of the lattice, pairs nearby internal endpoints that face a common
gap, and confirms that the line between them is predominantly background in the
segmented mask. Unpaired internal endpoints are reported as possible missing or
broken struts. A completely absent strut that leaves no skeleton trace cannot be
confirmed without a CAD/reference model.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
from scipy import ndimage as ndi
from scipy.spatial import cKDTree
import tifffile


NEIGHBORHOOD_26 = np.ones((3, 3, 3), dtype=np.uint8)
NEIGHBORHOOD_26[1, 1, 1] = 0


def load_volume(path: Path, *, skeleton: bool = False) -> np.ndarray:
    """Memory-map a 3-D NPY or TIFF volume and validate its shape."""
    suffix = path.suffix.lower()
    if suffix == ".npy":
        volume = np.load(path, mmap_mode="r", allow_pickle=False)
    elif suffix in {".tif", ".tiff"} and not skeleton:
        try:
            volume = tifffile.memmap(path)
        except ValueError:
            volume = tifffile.imread(path)
    else:
        expected = ".npy" if skeleton else ".npy, .tif, or .tiff"
        raise ValueError(f"{path} must be a {expected} file")
    if volume.ndim != 3:
        raise ValueError(f"expected a 3-D volume at {path}, got {volume.shape}")
    return volume


def foreground_bounds(volume: np.ndarray, chunk_depth: int) -> tuple[np.ndarray, np.ndarray]:
    """Return inclusive foreground bounds without materializing the full volume."""
    lower = np.asarray(volume.shape, dtype=int)
    upper = np.full(3, -1, dtype=int)
    for start in range(0, volume.shape[0], chunk_depth):
        stop = min(start + chunk_depth, volume.shape[0])
        block = np.asarray(volume[start:stop]) > 0
        points = np.argwhere(block)
        if points.size == 0:
            continue
        points[:, 0] += start
        lower = np.minimum(lower, points.min(axis=0))
        upper = np.maximum(upper, points.max(axis=0))
    if np.any(upper < 0):
        raise ValueError("the skeleton contains no foreground voxels")
    return lower, upper


def find_endpoints(skeleton: np.ndarray, chunk_depth: int) -> np.ndarray:
    """Find 26-connected skeleton voxels having exactly one neighbor."""
    endpoints: list[np.ndarray] = []
    depth = skeleton.shape[0]
    for start in range(0, depth, chunk_depth):
        stop = min(start + chunk_depth, depth)
        halo_start = max(0, start - 1)
        halo_stop = min(depth, stop + 1)
        block = np.asarray(skeleton[halo_start:halo_stop]) > 0
        neighbors = ndi.convolve(
            block.astype(np.uint8), NEIGHBORHOOD_26, mode="constant", cval=0
        )
        core_start = start - halo_start
        core_stop = core_start + (stop - start)
        core = block[core_start:core_stop]
        coords = np.argwhere(core & (neighbors[core_start:core_stop] == 1))
        if coords.size:
            coords[:, 0] += start
            endpoints.append(coords)
    return np.vstack(endpoints) if endpoints else np.empty((0, 3), dtype=int)


def internal_endpoints(
    endpoints: np.ndarray,
    lower: np.ndarray,
    upper: np.ndarray,
    boundary_margin: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Split endpoints into internal and natural exterior-boundary endpoints."""
    exterior = np.any(
        (endpoints <= lower + boundary_margin)
        | (endpoints >= upper - boundary_margin),
        axis=1,
    )
    return endpoints[~exterior], endpoints[exterior]


def sample_line(start: np.ndarray, end: np.ndarray) -> tuple[np.ndarray, float]:
    """Return rounded voxel coordinates sampled at roughly one-voxel spacing."""
    distance = float(np.linalg.norm(end - start))
    count = max(2, int(np.ceil(distance)) + 1)
    points = np.rint(np.linspace(start, end, count)).astype(int)
    points = np.unique(points, axis=0)
    return points, distance


def gap_metrics(
    segmentation: np.ndarray,
    start: np.ndarray,
    end: np.ndarray,
    endpoint_trim: int,
) -> dict[str, float]:
    """Measure empty material along the candidate endpoint-to-endpoint gap."""
    line, endpoint_distance = sample_line(start, end)
    trim = min(endpoint_trim, max(0, (len(line) - 1) // 3))
    interior = line[trim : len(line) - trim] if trim else line
    values = np.asarray(
        segmentation[interior[:, 0], interior[:, 1], interior[:, 2]]
    ) > 0
    empty = ~values
    empty_fraction = float(empty.mean()) if len(empty) else 0.0

    longest = current = 0
    for is_empty in empty:
        current = current + 1 if is_empty else 0
        longest = max(longest, current)
    spacing = endpoint_distance / max(len(line) - 1, 1)
    return {
        "endpoint_distance_voxels": endpoint_distance,
        "estimated_empty_gap_voxels": float(longest * spacing),
        "empty_fraction": empty_fraction,
    }


def candidate_pairs(endpoints: np.ndarray, maximum_distance: float) -> list[tuple[int, int, float]]:
    """Return candidate endpoint pairs ordered from nearest to farthest."""
    if len(endpoints) < 2:
        return []
    tree = cKDTree(endpoints)
    pairs = []
    for first, second in tree.query_pairs(maximum_distance):
        distance = float(np.linalg.norm(endpoints[first] - endpoints[second]))
        pairs.append((first, second, distance))
    return sorted(pairs, key=lambda item: item[2])


def outward_direction(skeleton: np.ndarray, endpoint: np.ndarray) -> np.ndarray:
    """Estimate the direction in which a broken strut would leave an endpoint."""
    shape = np.asarray(skeleton.shape)
    neighbors: list[np.ndarray] = []
    for offset in np.ndindex(3, 3, 3):
        delta = np.asarray(offset, dtype=int) - 1
        if np.all(delta == 0):
            continue
        position = endpoint + delta
        if np.all(position >= 0) and np.all(position < shape):
            if skeleton[tuple(position)] > 0:
                neighbors.append(position)
    if len(neighbors) != 1:
        return np.zeros(3, dtype=float)
    direction = endpoint.astype(float) - neighbors[0]
    return direction / np.linalg.norm(direction)


def endpoints_face_gap(
    skeleton: np.ndarray,
    first: np.ndarray,
    second: np.ndarray,
    minimum_cosine: float,
) -> bool:
    """Check that both endpoint tangents point toward the proposed gap."""
    separation = second.astype(float) - first
    unit = separation / np.linalg.norm(separation)
    first_outward = outward_direction(skeleton, first)
    second_outward = outward_direction(skeleton, second)
    return bool(
        np.dot(first_outward, unit) >= minimum_cosine
        and np.dot(second_outward, -unit) >= minimum_cosine
    )


def analyze(
    segmentation: np.ndarray,
    skeleton: np.ndarray,
    *,
    boundary_margin: int = 12,
    maximum_gap: float = 30.0,
    minimum_empty_fraction: float = 0.70,
    minimum_facing_cosine: float = 0.50,
    endpoint_trim: int = 2,
    chunk_depth: int = 32,
) -> dict[str, Any]:
    """Analyze matching segmentation and skeleton volumes."""
    if segmentation.shape != skeleton.shape:
        raise ValueError(
            "segmentation and skeleton shapes differ: "
            f"{segmentation.shape} versus {skeleton.shape}"
        )
    if (
        boundary_margin < 0
        or maximum_gap <= 0
        or not 0 <= minimum_empty_fraction <= 1
        or not -1 <= minimum_facing_cosine <= 1
    ):
        raise ValueError("invalid detection parameters")

    lower, upper = foreground_bounds(skeleton, chunk_depth)
    all_endpoints = find_endpoints(skeleton, chunk_depth)
    internal, exterior = internal_endpoints(
        all_endpoints, lower, upper, boundary_margin
    )

    used: set[int] = set()
    anomalies: list[dict[str, Any]] = []
    for first, second, _ in candidate_pairs(internal, maximum_gap):
        if first in used or second in used:
            continue
        if not endpoints_face_gap(
            skeleton, internal[first], internal[second], minimum_facing_cosine
        ):
            continue
        metrics = gap_metrics(
            segmentation, internal[first], internal[second], endpoint_trim
        )
        if metrics["empty_fraction"] < minimum_empty_fraction:
            continue
        used.update((first, second))
        midpoint = (internal[first].astype(float) + internal[second]) / 2
        anomalies.append(
            {
                "id": len(anomalies) + 1,
                "type": "confirmed_break",
                "endpoints_zyx": [internal[first].tolist(), internal[second].tolist()],
                "midpoint_zyx": midpoint.tolist(),
                "slice": int(round(midpoint[0])),
                **{key: round(value, 3) for key, value in metrics.items()},
            }
        )

    for index, endpoint in enumerate(internal):
        if index in used:
            continue
        anomalies.append(
            {
                "id": len(anomalies) + 1,
                "type": "unpaired_internal_endpoint",
                "endpoint_zyx": endpoint.tolist(),
                "slice": int(endpoint[0]),
                "estimated_empty_gap_voxels": None,
                "note": "Possible broken or missing strut; no nearby endpoint pair was confirmed.",
            }
        )

    slice_counts: dict[int, int] = {}
    for anomaly in anomalies:
        slice_number = int(anomaly["slice"])
        slice_counts[slice_number] = slice_counts.get(slice_number, 0) + 1
    total = len(anomalies)
    per_slice = [
        {
            "slice": slice_number,
            "count": count,
            "percentage_of_anomalies": round(100 * count / total, 3) if total else 0.0,
        }
        for slice_number, count in sorted(slice_counts.items())
    ]

    confirmed = sum(a["type"] == "confirmed_break" for a in anomalies)
    unpaired = total - confirmed
    return {
        "summary": {
            "total_skeleton_endpoints": int(len(all_endpoints)),
            "ignored_exterior_endpoints": int(len(exterior)),
            "internal_endpoints": int(len(internal)),
            "confirmed_breaks": int(confirmed),
            "unpaired_internal_endpoints": int(unpaired),
            "total_anomalies": int(total),
        },
        "parameters": {
            "boundary_margin_voxels": boundary_margin,
            "maximum_gap_voxels": maximum_gap,
            "minimum_empty_fraction": minimum_empty_fraction,
            "minimum_facing_cosine": minimum_facing_cosine,
            "endpoint_trim_voxels": endpoint_trim,
            "foreground_bounds_zyx": [lower.tolist(), upper.tolist()],
        },
        "anomalies": anomalies,
        "anomalies_by_slice": per_slice,
        "limitations": (
            "Unpaired internal endpoints are candidates, not confirmed missing struts. "
            "A fully absent strut with no skeleton trace requires a CAD or defect-free "
            "reference lattice for reliable detection."
        ),
    }


def short_summary(result: dict[str, Any]) -> str:
    """Create a compact human-readable summary."""
    summary = result["summary"]
    total = summary["total_anomalies"]
    confirmed_percentage = (
        100 * summary["confirmed_breaks"] / total if total else 0.0
    )
    unpaired_percentage = (
        100 * summary["unpaired_internal_endpoints"] / total if total else 0.0
    )
    busiest_slice = max(
        result["anomalies_by_slice"], key=lambda item: item["count"], default=None
    )
    slice_text = (
        f" Slice {busiest_slice['slice']} has the largest share at "
        f"{busiest_slice['percentage_of_anomalies']:.1f}% "
        f"({busiest_slice['count']} anomalies)."
        if busiest_slice
        else " No slices contain anomaly candidates."
    )
    paired_gaps = [
        anomaly["estimated_empty_gap_voxels"]
        for anomaly in result["anomalies"]
        if anomaly["type"] == "confirmed_break"
    ]
    gap_text = (
        f" Estimated confirmed gap: {min(paired_gaps):.1f}–{max(paired_gaps):.1f} voxels."
        if paired_gaps
        else " No paired gap passed the empty-space confirmation test."
    )
    return (
        f"Detected {total} total anomaly candidates: "
        f"{summary['confirmed_breaks']} confirmed endpoint-pair breaks "
        f"({confirmed_percentage:.1f}%) and "
        f"{summary['unpaired_internal_endpoints']} unpaired internal endpoints "
        f"({unpaired_percentage:.1f}%). "
        f"Ignored {summary['ignored_exterior_endpoints']} natural exterior endpoints."
        + gap_text
        + slice_text
    )


def compact_report(result: dict[str, Any], top_slices: int = 10) -> dict[str, Any]:
    """Return the requested findings without endpoint-coordinate diagnostics."""
    gaps = [
        float(anomaly["estimated_empty_gap_voxels"])
        for anomaly in result["anomalies"]
        if anomaly["type"] == "confirmed_break"
    ]
    gap_statistics = {
        "count": len(gaps),
        "minimum_voxels": round(min(gaps), 3) if gaps else None,
        "median_voxels": round(float(np.median(gaps)), 3) if gaps else None,
        "mean_voxels": round(float(np.mean(gaps)), 3) if gaps else None,
        "maximum_voxels": round(max(gaps), 3) if gaps else None,
    }
    busiest = sorted(
        result["anomalies_by_slice"],
        key=lambda item: (-item["count"], item["slice"]),
    )[:top_slices]
    return {
        "short_summary": result["short_summary"],
        "counts": result["summary"],
        "confirmed_gap_statistics": gap_statistics,
        "confirmed_gap_estimates_voxels": [round(gap, 3) for gap in gaps],
        "top_slices": busiest,
        "slice_percentages": {
            str(item["slice"]): item["percentage_of_anomalies"]
            for item in result["anomalies_by_slice"]
        },
        "limitations": result["limitations"],
    }


def markdown_report(result: dict[str, Any], top_slices: int = 10) -> str:
    """Create a brief human-readable report."""
    report = compact_report(result, top_slices)
    counts = report["counts"]
    gaps = report["confirmed_gap_statistics"]
    lines = [
        "# Lattice Anomaly Summary",
        "",
        f"- Total anomaly candidates: **{counts['total_anomalies']}**",
        f"- Confirmed endpoint-pair breaks: **{counts['confirmed_breaks']}** "
        f"({100 * counts['confirmed_breaks'] / max(counts['total_anomalies'], 1):.1f}%)",
        f"- Unpaired internal endpoints: **{counts['unpaired_internal_endpoints']}** "
        f"({100 * counts['unpaired_internal_endpoints'] / max(counts['total_anomalies'], 1):.1f}%)",
        f"- Natural exterior endpoints ignored: **{counts['ignored_exterior_endpoints']}**",
        f"- Confirmed gap length: **{gaps['minimum_voxels']}–{gaps['maximum_voxels']} voxels** "
        f"(median {gaps['median_voxels']}, mean {gaps['mean_voxels']})",
        "",
        f"## Top {len(report['top_slices'])} slices",
        "",
        "| Slice | Anomalies | Percentage |",
        "|---:|---:|---:|",
    ]
    lines.extend(
        f"| {item['slice']} | {item['count']} | {item['percentage_of_anomalies']:.1f}% |"
        for item in report["top_slices"]
    )
    lines.extend(
        [
            "",
            "Confirmed breaks require paired inward-facing endpoints and primarily empty "
            "segmentation between them. Unpaired endpoints remain possible defects or "
            "skeletonization artifacts.",
        ]
    )
    return "\n".join(lines) + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("segmentation", type=Path, help="Matching 3-D mask (.npy/.tif/.tiff)")
    parser.add_argument("skeleton", type=Path, help="Matching 3-D skeleton (.npy)")
    parser.add_argument("--output", type=Path, help="Optional JSON results path")
    parser.add_argument(
        "--detailed-output",
        type=Path,
        help="Optional full JSON diagnostics, including every endpoint coordinate",
    )
    parser.add_argument("--boundary-margin", type=int, default=12)
    parser.add_argument("--maximum-gap", type=float, default=30.0)
    parser.add_argument("--minimum-empty-fraction", type=float, default=0.70)
    parser.add_argument("--minimum-facing-cosine", type=float, default=0.50)
    parser.add_argument("--endpoint-trim", type=int, default=2)
    parser.add_argument("--chunk-depth", type=int, default=32)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    segmentation = load_volume(args.segmentation)
    skeleton = load_volume(args.skeleton, skeleton=True)
    result = analyze(
        segmentation,
        skeleton,
        boundary_margin=args.boundary_margin,
        maximum_gap=args.maximum_gap,
        minimum_empty_fraction=args.minimum_empty_fraction,
        minimum_facing_cosine=args.minimum_facing_cosine,
        endpoint_trim=args.endpoint_trim,
        chunk_depth=args.chunk_depth,
    )
    result["inputs"] = {
        "segmentation": str(args.segmentation.resolve()),
        "skeleton": str(args.skeleton.resolve()),
        "shape_zyx": list(segmentation.shape),
    }
    result["short_summary"] = short_summary(result)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        if args.output.suffix.lower() == ".md":
            args.output.write_text(markdown_report(result), encoding="utf-8")
        else:
            # Arrays and per-slice percentages stay on single lines, keeping the
            # default report compact while retaining all requested measurements.
            args.output.write_text(
                json.dumps(compact_report(result), separators=(",", ":")) + "\n",
                encoding="utf-8",
            )
        print(f"Saved compact report to {args.output.resolve()}")
    if args.detailed_output:
        args.detailed_output.parent.mkdir(parents=True, exist_ok=True)
        args.detailed_output.write_text(
            json.dumps(result, indent=2) + "\n", encoding="utf-8"
        )
        print(f"Saved optional detailed diagnostics to {args.detailed_output.resolve()}")
    print(result["short_summary"])


if __name__ == "__main__":
    main()
