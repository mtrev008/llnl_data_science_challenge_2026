#!/usr/bin/env python3
"""Measure struts from existing segmented and skeletonized 3D TIFF stacks."""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import tifffile
from scipy.ndimage import distance_transform_edt, maximum_filter
from scipy.spatial import ConvexHull, cKDTree


VOXEL_SIZE_UM = 58.09
MIN_BRANCH_LENGTH = 12.0
EDT_SLAB_DEPTH = 48
EDT_HALO = 16
RELATIVE_THIN_RATIO = 0.60
MIN_SUSTAINED_THIN_SAMPLES = 2
MIN_MISSING_JUNCTION_SUPPORT = 2
JUNCTION_PREDICTION_POSITION_TOLERANCE = 0.25
PREDICTION_POSITION_TOLERANCE = 0.35
PREDICTION_MERGE_TOLERANCE = 0.60
TEMPLATE_ANGLE_TOLERANCE_DEGREES = 15.0
TEMPLATE_MIN_LENGTH_RATIO = 0.75
TEMPLATE_MAX_LENGTH_RATIO = 1.30
ENDPOINT_ANGLE_TOLERANCE_DEGREES = 40.0
POTENTIALLY_BROKEN_MISSING_FRACTION = 0.20
MISSING_STRUT_MISSING_FRACTION = 0.45
LOCAL_MATERIAL_SUPPORT_FRACTION = 0.02
MAX_TRACK_GAP_SLICES = 2
CONSISTENT_STRUCTURE_SAMPLES = 3
JUNCTION_MAX_BOUNDARY_EXTENSION_SCALE = 0.30
EDGE_EXCLUSION_VOXELS = 2.0
STRUT_ENDPOINT_TRIM_FRACTION = 0.05
NEIGHBORS = [
    (z, y, x)
    for z in (-1, 0, 1)
    for y in (-1, 0, 1)
    for x in (-1, 0, 1)
    if (z, y, x) != (0, 0, 0)
]

CSV_FIELDS = [
    "strut_id",
    "classification",
    "evidence",
    "anomaly_score",
    "effective_count",
    "source_paths",
    "z_min",
    "z_max",
    "weakest_slice",
    "path_length_voxels",
    "path_length_um",
    "straight_length_voxels",
    "straight_length_um",
    "tortuosity",
    "gap_voxels",
    "gap_um",
    "thickness_min_um",
    "thickness_mean_um",
    "thickness_median_um",
    "thickness_p10_um",
    "thickness_p90_um",
    "thickness_low_percentile_um",
    "own_median_thickness_um",
    "minimum_relative_thickness",
    "sustained_thin_samples",
    "adaptive_threshold_um",
    "consecutive_thin_slices",
    "consecutive_disconnected_slices",
    "gap_midpoint_slice",
    "evidence_slices",
    "raw_support",
    "segmentation_fade",
    "recentered_fraction",
]


def percentile_argument(value: str) -> float:
    value = float(value)
    if not 0 <= value <= 50:
        raise argparse.ArgumentTypeError("percentile must be between 0 and 50")
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Measure every strut in an existing 3D mask and skeleton."
    )
    parser.add_argument("segmented_tiff", type=Path)
    parser.add_argument("--skeleton-tiff", type=Path)
    parser.add_argument("--raw-tiff", type=Path)
    parser.add_argument(
        "--expected-json",
        "--registered-json",
        type=Path,
        help="Perfect-design JSON used only for expected junction/strut counts",
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--voxel-size-um", type=float, default=VOXEL_SIZE_UM)
    parser.add_argument(
        "--voxel-spacing-um",
        type=float,
        nargs=3,
        metavar=("Z", "Y", "X"),
        help="Anisotropic Z/Y/X spacing; overrides --voxel-size-um",
    )
    parser.add_argument(
        "--strut-thickness-percentile",
        type=percentile_argument,
        default=10.0,
        help="Within-strut percentile used to represent low thickness (default: 10)",
    )
    parser.add_argument(
        "--max-track-gap-slices",
        type=int,
        default=MAX_TRACK_GAP_SLICES,
        help="Maximum consecutive missing observations bridged by a 3D track",
    )
    parser.add_argument(
        "--prediction-position-tolerance",
        type=float,
        default=PREDICTION_POSITION_TOLERANCE,
        help="Tracking/topology position gate as a fraction of observed edge length",
    )
    parser.add_argument(
        "--potentially-broken-missing-fraction",
        type=float,
        default=POTENTIALLY_BROKEN_MISSING_FRACTION,
    )
    parser.add_argument(
        "--missing-strut-missing-fraction",
        type=float,
        default=MISSING_STRUT_MISSING_FRACTION,
    )
    parser.add_argument(
        "--include-thickness-potentially-broken",
        action="store_true",
        # Thickness-only warnings are intentionally paused by default. Keep this
        # switch so the preserved detector can be re-enabled without code edits.
        help="Re-enable thickness-derived potentially-broken classifications",
    )
    parser.add_argument(
        "--include-topology-potentially-broken",
        action="store_true",
        # Topology-only warnings are intentionally paused by default. The
        # implementation remains available for a later review pass.
        help="Re-enable topology-derived potentially-broken classifications",
    )
    return parser


def neighbors(point, skeleton_points):
    z, y, x = point
    return [
        (z + dz, y + dy, x + dx)
        for dz, dy, dx in NEIGHBORS
        if (z + dz, y + dy, x + dx) in skeleton_points
    ]


def extract_paths(skeleton):
    """Return paths between clustered junctions and terminal endpoints."""
    skeleton_points = {
        tuple(int(value) for value in point)
        for point in np.argwhere(skeleton > 0)
    }
    if not skeleton_points:
        raise ValueError("the skeleton is empty")

    degree = {
        point: len(neighbors(point, skeleton_points))
        for point in skeleton_points
    }
    node_voxels = {point for point, count in degree.items() if count != 2}
    node_ids = {}
    node_types = {}
    next_node = 0

    # Merge touching branch voxels into a single physical junction.
    unassigned = {point for point in node_voxels if degree[point] > 2}
    while unassigned:
        seed = min(unassigned)
        unassigned.remove(seed)
        stack = [seed]
        component = [seed]
        while stack:
            current = stack.pop()
            for adjacent in sorted(neighbors(current, skeleton_points)):
                if adjacent in unassigned:
                    unassigned.remove(adjacent)
                    stack.append(adjacent)
                    component.append(adjacent)
        for point in component:
            node_ids[point] = next_node
        node_types[next_node] = "junction"
        next_node += 1

    for point in sorted(point for point in node_voxels if degree[point] <= 1):
        node_ids[point] = next_node
        node_types[next_node] = "terminal"
        next_node += 1

    visited_edges = set()
    paths = []

    def edge(first, second):
        return tuple(sorted((first, second)))

    for start, start_node in sorted(node_ids.items()):
        for adjacent in sorted(neighbors(start, skeleton_points)):
            if node_ids.get(adjacent) == start_node:
                continue
            first_edge = edge(start, adjacent)
            if first_edge in visited_edges:
                continue
            visited_edges.add(first_edge)
            points = [start]
            previous, current = start, adjacent
            while current not in node_ids:
                points.append(current)
                forward = [
                    point
                    for point in neighbors(current, skeleton_points)
                    if point != previous
                ]
                if not forward:
                    break
                following = forward[0]
                visited_edges.add(edge(current, following))
                previous, current = current, following
            if current not in node_ids or node_ids[current] == start_node:
                continue
            points.append(current)
            paths.append(
                {
                    "id": len(paths),
                    "start_node": start_node,
                    "end_node": node_ids[current],
                    "start_type": node_types[start_node],
                    "end_type": node_types[node_ids[current]],
                    "points": np.asarray(points, dtype=np.int32),
                }
            )
    paths.sort(key=lambda path: tuple(path["points"][0]) + tuple(path["points"][-1]))
    for path_id, path in enumerate(paths):
        path["id"] = path_id
    return paths


def thickness_at_skeleton(mask, skeleton, spacing_um):
    """Calculate ridge-recentered 3D diameters in seam-safe slabs."""
    diameters = {}
    recentered = {}
    expanded_slabs = 0
    largest_radius_voxels = 0.0
    minimum_spacing = min(spacing_um)
    for center_start in range(0, mask.shape[0], EDT_SLAB_DEPTH):
        center_stop = min(mask.shape[0], center_start + EDT_SLAB_DEPTH)
        halo = EDT_HALO
        while True:
            start = max(0, center_start - halo)
            stop = min(mask.shape[0], center_stop + halo)
            distances = distance_transform_edt(
                np.asarray(mask[start:stop]) > 0,
                sampling=spacing_um,
            )
            core_points = np.argwhere(skeleton[center_start:center_stop] > 0)
            if not len(core_points):
                break
            core_values = distances[
                core_points[:, 0] + center_start - start,
                core_points[:, 1],
                core_points[:, 2],
            ]
            largest = float(core_values.max() / minimum_spacing)
            if largest < halo - 1 or halo >= 64:
                largest_radius_voxels = max(largest_radius_voxels, largest)
                break
            halo *= 2
            expanded_slabs += 1
        local_ridge = maximum_filter(distances, size=3, mode="nearest")
        for local_z, y, x in core_points:
            z = center_start + int(local_z)
            center_radius = float(distances[z - start, y, x])
            ridge_radius = float(local_ridge[z - start, y, x])
            key = (z, int(y), int(x))
            diameters[key] = 2.0 * ridge_radius
            recentered[key] = ridge_radius > center_radius + 1e-9
    diagnostics = {
        "expanded_slabs": expanded_slabs,
        "largest_radius_voxels": largest_radius_voxels,
    }
    return diameters, recentered, diagnostics


def measure_path(path, diameters, recentered, percentile, spacing_um):
    points = path["points"]
    thickness = np.asarray(
        [diameters[tuple(int(value) for value in point)] for point in points]
    )
    shifts = np.asarray(
        [recentered[tuple(int(value) for value in point)] for point in points]
    )
    voxel_steps = np.diff(points, axis=0)
    path_length_voxels = float(np.linalg.norm(voxel_steps, axis=1).sum())
    path_length_um = float(
        np.linalg.norm(voxel_steps * np.asarray(spacing_um), axis=1).sum()
    )
    straight_length_voxels = float(np.linalg.norm(points[-1] - points[0]))
    straight_length_um = float(
        np.linalg.norm((points[-1] - points[0]) * np.asarray(spacing_um))
    )
    shaft_start = min(3, max(0, len(points) // 4))
    shaft_stop = max(shaft_start + 1, len(points) - shaft_start)
    shaft_points = points[shaft_start:shaft_stop]
    shaft_thickness = thickness[shaft_start:shaft_stop]
    weakest_index = int(np.argmin(thickness))
    per_slice = {
        int(z): float(np.median(shaft_thickness[shaft_points[:, 0] == z]))
        for z in np.unique(shaft_points[:, 0])
    }
    return {
        **path,
        "thickness": thickness,
        "shaft_points": shaft_points,
        "shaft_thickness": shaft_thickness,
        "slice_thickness": per_slice,
        "path_length_voxels": path_length_voxels,
        "path_length_um": path_length_um,
        "straight_length_voxels": straight_length_voxels,
        "straight_length_um": straight_length_um,
        "tortuosity": path_length_um / straight_length_um
        if straight_length_um
        else 1.0,
        "weakest_slice": int(points[weakest_index, 0]),
        "low_thickness": float(np.percentile(shaft_thickness, percentile)),
        "recentered_fraction": float(np.mean(shifts)),
    }


def adaptive_threshold(values):
    """Median - 3 robust standard deviations, with a quantization fallback."""
    values = np.asarray(values)
    center = float(np.median(values))
    scale = 1.4826 * float(np.median(np.abs(values - center)))
    method = "MAD"
    if scale == 0:
        q1, q3 = np.percentile(values, [25, 75])
        scale = float((q3 - q1) / 1.349)
        method = "IQR"
    if scale == 0:
        spacing = np.diff(np.unique(values))
        scale = float(spacing[0]) if len(spacing) else 0.0
        method = "quantization spacing"
    return center - 3.0 * scale, center, scale, method


def longest_consecutive(values):
    values = sorted(set(int(value) for value in values))
    best = []
    current = []
    for value in values:
        if not current or value == current[-1] + 1:
            current.append(value)
        else:
            if len(current) > len(best):
                best = current
            current = [value]
    return current if len(current) > len(best) else best


def gap_event_classification(gap_slices):
    """Classify one continuous 3D absence without counting its slices."""
    return "missing" if len(gap_slices) >= 4 else "potentially_broken"


def raw_normalization(raw):
    lows = np.empty(raw.shape[0], dtype=float)
    scales = np.empty(raw.shape[0], dtype=float)
    for z in range(raw.shape[0]):
        image = np.asarray(raw[z])
        lows[z] = np.median(image)
        scales[z] = max(float(np.percentile(image, 99.5) - lows[z]), 1.0)
    return lows, scales


def normalized_patch_max(raw, z, y, x, lows, scales, radius=2):
    y0, y1 = max(0, y - radius), min(raw.shape[1], y + radius + 1)
    x0, x1 = max(0, x - radius), min(raw.shape[2], x + radius + 1)
    value = float(np.max(raw[z, y0:y1, x0:x1]))
    return float(np.clip((value - lows[z]) / scales[z], 0, 1))


def raw_material_cutoff(raw, skeleton, lows, scales):
    points = np.argwhere(skeleton > 0)
    step = max(1, len(points) // 10000)
    values = [
        normalized_patch_max(
            raw, int(z), int(y), int(x), lows, scales, radius=1
        )
        for z, y, x in points[::step]
    ]
    return float(np.percentile(values, 10))


def persistent_thin_evidence(path, threshold):
    thin_slices = [
        z for z, value in path["slice_thickness"].items() if value < threshold
    ]
    run = longest_consecutive(thin_slices)
    return run if path["low_thickness"] < threshold and len(run) >= 3 else []


def sustained_relative_thin_evidence(
    path,
    ratio=RELATIVE_THIN_RATIO,
    minimum_samples=MIN_SUSTAINED_THIN_SAMPLES,
):
    """Return the longest path-ordered run thin relative to this strut."""
    thickness = np.asarray(path["shaft_thickness"], dtype=float)
    points = np.asarray(path["shaft_points"], dtype=int)
    own_median = float(np.median(thickness))
    thin = thickness < ratio * own_median
    padded = np.pad(thin.astype(np.int8), 1)
    edges = np.diff(padded)
    starts = np.flatnonzero(edges == 1)
    stops = np.flatnonzero(edges == -1)
    if not len(starts):
        return [], np.empty((0, 3), dtype=np.int32), 0
    lengths = stops - starts
    best = int(np.argmax(lengths))
    if int(lengths[best]) < minimum_samples:
        return [], np.empty((0, 3), dtype=np.int32), int(lengths[best])
    selected = points[starts[best] : stops[best]]
    return sorted(set(int(z) for z in selected[:, 0])), selected, int(lengths[best])


def thin_segmentation_fade(path, thin_slices, mask, raw, lows, scales, raw_cutoff):
    if raw is None or not thin_slices:
        return False, 0.0
    supports = []
    faded = 0
    for z in thin_slices:
        points = path["points"][path["points"][:, 0] == z]
        if not len(points):
            continue
        _, y, x = points[len(points) // 2]
        y, x = int(y), int(x)
        radius = 4
        y0, y1 = max(0, y - radius), min(mask.shape[1], y + radius + 1)
        x0, x1 = max(0, x - radius), min(mask.shape[2], x + radius + 1)
        raw_patch = np.asarray(raw[z, y0:y1, x0:x1], dtype=float)
        raw_fraction = float(
            np.mean(np.clip((raw_patch - lows[z]) / scales[z], 0, 1) >= raw_cutoff)
        )
        mask_fraction = float(np.mean(mask[z, y0:y1, x0:x1] > 0))
        supports.append(raw_fraction)
        faded += raw_fraction > mask_fraction + 0.15
    return faded >= 2, float(np.mean(supports)) if supports else 0.0


def validate_gap(match, mask, skeleton, raw, lows, scales, raw_cutoff):
    first = match["first"]["terminal"].astype(float)
    second = match["second"]["terminal"].astype(float)
    if abs(int(round(first[0])) - int(round(second[0]))) < 2:
        return [], [], 0.0, False
    sample_count = max(2, int(np.ceil(np.linalg.norm(second - first))) + 1)
    line = np.rint(np.linspace(first, second, sample_count)).astype(int)
    by_slice = {}
    for z in np.unique(line[:, 0]):
        points = line[line[:, 0] == z]
        by_slice[int(z)] = points[len(points) // 2]
    unsupported = []
    raw_supports = []
    faded = False
    for z in sorted(by_slice):
        _, y, x = by_slice[z]
        y0, y1 = max(0, y - 2), min(mask.shape[1], y + 3)
        x0, x1 = max(0, x - 2), min(mask.shape[2], x + 3)
        mask_present = bool(np.any(mask[z, y0:y1, x0:x1] > 0))
        skeleton_present = bool(np.any(skeleton[z, y0:y1, x0:x1] > 0))
        raw_support = (
            normalized_patch_max(raw, z, int(y), int(x), lows, scales)
            if raw is not None
            else 0.0
        )
        raw_supports.append(raw_support)
        raw_present = raw is not None and raw_support >= raw_cutoff
        # A missing/off-center skeleton sample is not a physical break when
        # segmentation still follows the moving 3D trajectory.
        if not mask_present and not skeleton_present and not raw_present:
            unsupported.append(z)
        elif not mask_present and raw_present:
            faded = True
    run = longest_consecutive(unsupported)
    gap_points = np.asarray(
        [by_slice[z] for z in run], dtype=np.int32
    ) if run else np.empty((0, 3), dtype=np.int32)
    return (
        run,
        gap_points,
        float(np.mean(raw_supports)) if raw_supports else 0.0,
        faded,
    )


def terminal_data(path):
    points = path["points"]
    if path["start_type"] == "terminal" and path["end_type"] == "junction":
        terminal = points[0]
        remote = points[-1]
        inward = points[min(4, len(points) - 1)]
    elif path["end_type"] == "terminal" and path["start_type"] == "junction":
        terminal = points[-1]
        remote = points[0]
        inward = points[max(0, len(points) - 5)]
    else:
        return None
    outward = terminal.astype(float) - inward.astype(float)
    outward /= np.linalg.norm(outward)
    return {"path": path, "terminal": terminal, "remote": remote, "outward": outward}


def match_fragments(fragments, volume_shape, median_diameter):
    """Greedily match nearby, aligned, similarly thick terminal fragments."""
    margin = 2.0 * median_diameter
    endpoints = []
    for path in fragments:
        item = terminal_data(path)
        if item is None:
            continue
        point = item["terminal"]
        if np.any(point < margin) or np.any(point > np.asarray(volume_shape) - margin):
            continue
        endpoints.append(item)

    candidates = []
    max_gap = 4.0 * median_diameter
    minimum_cosine = math.cos(math.radians(35.0))
    for first_index, first in enumerate(endpoints):
        for second in endpoints[first_index + 1 :]:
            delta = second["terminal"].astype(float) - first["terminal"]
            gap = float(np.linalg.norm(delta))
            if not 0 < gap <= max_gap:
                continue
            direction = delta / gap
            alignment = min(
                float(np.dot(first["outward"], direction)),
                float(np.dot(second["outward"], -direction)),
            )
            if alignment < minimum_cosine:
                continue
            first_thickness = first["path"]["thickness_median_um"]
            second_thickness = second["path"]["thickness_median_um"]
            similarity = min(first_thickness, second_thickness) / max(
                first_thickness, second_thickness
            )
            if similarity < 0.5:
                continue
            confidence = (
                0.5 * (1.0 - gap / max_gap)
                + 0.3 * alignment
                + 0.2 * similarity
            )
            candidates.append((confidence, gap, first, second))

    matches = []
    used = set()
    for confidence, gap, first, second in sorted(candidates, reverse=True, key=lambda x: x[0]):
        first_id = first["path"]["id"]
        second_id = second["path"]["id"]
        if first_id in used or second_id in used:
            continue
        used.update((first_id, second_id))
        matches.append(
            {
                "first": first,
                "second": second,
                "gap": gap,
                "confidence": confidence,
            }
        )
    return matches, used


def path_statistics(path):
    thickness = path["shaft_thickness"]
    return {
        "thickness_min_um": float(np.min(thickness)),
        "thickness_mean_um": float(np.mean(thickness)),
        "thickness_median_um": float(np.median(thickness)),
        "thickness_p10_um": float(np.percentile(thickness, 10)),
        "thickness_p90_um": float(np.percentile(thickness, 90)),
        "thickness_low_percentile_um": path["low_thickness"],
    }


def anomaly_score(low_thickness, center, scale):
    if scale == 0:
        return 0.0
    return float(np.clip((center - low_thickness) / (3.0 * scale), 0, 1))


def make_row(
    strut_id,
    classification,
    evidence,
    score,
    effective_count,
    source_paths,
    points,
    thickness,
    percentile,
    threshold,
    spacing_um,
    gap=0.0,
    gap_um=0.0,
    thin_slices=None,
    disconnected_slices=None,
    raw_support=0.0,
    segmentation_fade=False,
    gap_points=None,
    statistics_thickness=None,
    sustained_thin_samples=0,
):
    thin_slices = thin_slices or []
    disconnected_slices = disconnected_slices or []
    path_length = sum(path["path_length_voxels"] for path in source_paths) + gap
    path_length_um = sum(path["path_length_um"] for path in source_paths) + gap_um
    straight_length = float(np.linalg.norm(points[-1] - points[0]))
    straight_length_um = float(
        np.linalg.norm((points[-1] - points[0]) * np.asarray(spacing_um))
    )
    weakest_index = int(np.argmin(thickness))
    statistics_thickness = (
        thickness if statistics_thickness is None else statistics_thickness
    )
    row = {
        "strut_id": strut_id,
        "classification": classification,
        "evidence": evidence,
        "anomaly_score": score,
        "effective_count": effective_count,
        "source_paths": ";".join(str(path["id"]) for path in source_paths),
        "z_min": int(np.min(points[:, 0])),
        "z_max": int(np.max(points[:, 0])),
        "weakest_slice": int(points[weakest_index, 0]),
        "path_length_voxels": path_length,
        "path_length_um": path_length_um,
        "straight_length_voxels": straight_length,
        "straight_length_um": straight_length_um,
        "tortuosity": path_length_um / straight_length_um
        if straight_length_um
        else 1.0,
        "gap_voxels": gap,
        "gap_um": gap_um,
        "thickness_min_um": float(np.min(statistics_thickness)),
        "thickness_mean_um": float(np.mean(statistics_thickness)),
        "thickness_median_um": float(np.median(statistics_thickness)),
        "thickness_p10_um": float(np.percentile(statistics_thickness, 10)),
        "thickness_p90_um": float(np.percentile(statistics_thickness, 90)),
        "thickness_low_percentile_um": float(
            np.percentile(statistics_thickness, percentile)
        ),
        "own_median_thickness_um": float(np.median(statistics_thickness)),
        "minimum_relative_thickness": float(
            np.min(statistics_thickness) / np.median(statistics_thickness)
        )
        if np.median(statistics_thickness)
        else 1.0,
        "sustained_thin_samples": int(sustained_thin_samples),
        "adaptive_threshold_um": threshold,
        "consecutive_thin_slices": len(thin_slices),
        "consecutive_disconnected_slices": len(disconnected_slices),
        "gap_midpoint_slice": (
            int(disconnected_slices[len(disconnected_slices) // 2])
            if disconnected_slices
            else ""
        ),
        "evidence_slices": ";".join(
            str(value) for value in sorted(set(thin_slices + disconnected_slices))
        ),
        "raw_support": raw_support,
        "segmentation_fade": bool(segmentation_fade),
        "recentered_fraction": float(
            np.mean([path["recentered_fraction"] for path in source_paths])
        ),
        "_points": points,
        "_thin_slices": thin_slices,
        "_disconnected_slices": disconnected_slices,
        "_gap_points": gap_points
        if gap_points is not None
        else np.empty((0, 3), dtype=np.int32),
        "_endpoints": np.asarray([points[0], points[-1]], dtype=np.int32),
    }
    return row


def classify_paths(
    paths,
    mask,
    skeleton,
    raw,
    lows,
    scales,
    raw_cutoff,
    percentile,
    threshold,
    center,
    scale,
    spacing_um,
    include_thickness_potentially_broken=False,
):
    paths = [path for path in paths if path["path_length_voxels"] >= MIN_BRANCH_LENGTH]
    complete = [
        path
        for path in paths
        if path["start_type"] == path["end_type"] == "junction"
    ]
    fragments = [path for path in paths if path not in complete]
    median_diameter = float(
        np.median([path["thickness_median_um"] for path in complete])
        / min(spacing_um)
    )
    matches, _ = match_fragments(fragments, mask.shape, median_diameter)

    rows = []
    for path in complete:
        thin_slices, _, thin_sample_count = sustained_relative_thin_evidence(path)
        faded, raw_support = thin_segmentation_fade(
            path, thin_slices, mask, raw, lows, scales, raw_cutoff
        )
        thin = bool(thin_slices) and not faded
        report_thin = include_thickness_potentially_broken and thin
        rows.append(
            make_row(
                len(rows),
                "potentially_broken" if report_thin else "normal",
                "thin" if report_thin else "none",
                anomaly_score(path["low_thickness"], center, scale),
                1,
                [path],
                path["points"],
                path["thickness"],
                percentile,
                threshold,
                spacing_um,
                thin_slices=thin_slices if report_thin else [],
                raw_support=raw_support,
                segmentation_fade=faded,
                statistics_thickness=path["shaft_thickness"],
                sustained_thin_samples=thin_sample_count,
            )
        )

    matched_ids = set()
    for match in matches:
        disconnected_slices, gap_points, raw_support, faded = validate_gap(
            match, mask, skeleton, raw, lows, scales, raw_cutoff
        )
        if not disconnected_slices:
            continue
        first = match["first"]
        second = match["second"]
        first_points = first["path"]["points"]
        first_thickness = first["path"]["thickness"]
        if not np.array_equal(first_points[-1], first["terminal"]):
            first_points = first_points[::-1]
            first_thickness = first_thickness[::-1]
        second_points = second["path"]["points"]
        second_thickness = second["path"]["thickness"]
        if not np.array_equal(second_points[0], second["terminal"]):
            second_points = second_points[::-1]
            second_thickness = second_thickness[::-1]
        points = np.vstack((first_points, second_points))
        thickness = np.concatenate((first_thickness, second_thickness))
        shaft_thickness = np.concatenate(
            (first["path"]["shaft_thickness"], second["path"]["shaft_thickness"])
        )
        low = float(np.percentile(shaft_thickness, percentile))
        thin_slices = []
        thin_score = anomaly_score(low, center, scale)
        score = 1.0 - (1.0 - thin_score) * (1.0 - match["confidence"])
        gap_delta = (
            second["terminal"].astype(float) - first["terminal"].astype(float)
        )
        gap_um = float(np.linalg.norm(gap_delta * np.asarray(spacing_um)))
        matched_ids.update((first["path"]["id"], second["path"]["id"]))
        rows.append(
            make_row(
                len(rows),
                "broken",
                "fragment_gap",
                score,
                1,
                [first["path"], second["path"]],
                points,
                thickness,
                percentile,
                threshold,
                spacing_um,
                match["gap"],
                gap_um,
                thin_slices=thin_slices,
                disconnected_slices=disconnected_slices,
                raw_support=raw_support,
                segmentation_fade=faded,
                gap_points=gap_points,
                statistics_thickness=shaft_thickness,
            )
        )

    margin = 2.0 * median_diameter
    shape = np.asarray(mask.shape)
    for path in fragments:
        if path["id"] in matched_ids:
            continue
        terminals = []
        if path["start_type"] == "terminal":
            terminals.append(path["points"][0])
        if path["end_type"] == "terminal":
            terminals.append(path["points"][-1])
        if any(np.any(point < margin) or np.any(point > shape - margin) for point in terminals):
            continue
        rows.append(
            make_row(
                len(rows),
                "incomplete_fragment",
                "unmatched_endpoint",
                anomaly_score(path["low_thickness"], center, scale),
                0,
                [path],
                path["points"],
                path["thickness"],
                percentile,
                threshold,
                spacing_um,
                statistics_thickness=path["shaft_thickness"],
            )
        )
    return rows


def _canonical_vector(vector):
    vector = np.asarray(vector, dtype=float)
    for value in vector:
        if abs(value) > 1e-9:
            return -vector if value < 0 else vector
    return vector


def _learn_connection_templates(paths):
    """Learn normal connection vectors from intact TIFF skeleton paths."""
    vectors = []
    for path in paths:
        if (
            path["start_type"] == path["end_type"] == "junction"
            and path["path_length_voxels"] >= MIN_BRANCH_LENGTH
        ):
            vector = _canonical_vector(path["points"][-1] - path["points"][0])
            if np.linalg.norm(vector) > 0:
                vectors.append(vector)
    if not vectors:
        return []
    lengths = np.asarray([np.linalg.norm(vector) for vector in vectors])
    center = float(np.median(lengths))
    vectors = [
        vector
        for vector in vectors
        if 0.60 * center <= np.linalg.norm(vector) <= 1.40 * center
    ]
    clusters = []
    cosine_limit = math.cos(math.radians(TEMPLATE_ANGLE_TOLERANCE_DEGREES))
    for vector in sorted(vectors, key=lambda value: tuple(value)):
        length = np.linalg.norm(vector)
        assigned = False
        for cluster in clusters:
            template = np.median(cluster, axis=0)
            template_length = np.linalg.norm(template)
            cosine = float(np.dot(vector, template) / (length * template_length))
            if (
                cosine >= cosine_limit
                and TEMPLATE_MIN_LENGTH_RATIO
                <= length / template_length
                <= TEMPLATE_MAX_LENGTH_RATIO
            ):
                cluster.append(vector)
                assigned = True
                break
        if not assigned:
            clusters.append([vector])
    minimum_support = max(5, int(0.001 * len(vectors)))
    return [
        np.median(cluster, axis=0)
        for cluster in clusters
        if len(cluster) >= minimum_support
    ]


def _material_support_at(point, mask, skeleton, raw, lows, scales, raw_cutoff, radius):
    z, y, x = np.rint(point).astype(int)
    z0, z1 = max(0, z - radius), min(mask.shape[0], z + radius + 1)
    y0, y1 = max(0, y - radius), min(mask.shape[1], y + radius + 1)
    x0, x1 = max(0, x - radius), min(mask.shape[2], x + radius + 1)
    mask_patch = np.asarray(mask[z0:z1, y0:y1, x0:x1]) > 0
    skeleton_patch = np.asarray(skeleton[z0:z1, y0:y1, x0:x1]) > 0
    mask_fraction = float(np.mean(mask_patch))
    skeleton_present = bool(np.any(skeleton_patch))
    raw_fraction = 0.0
    if raw is not None:
        raw_patch = np.asarray(raw[z0:z1, y0:y1, x0:x1], dtype=float)
        normalized = np.empty_like(raw_patch)
        for local_z, global_z in enumerate(range(z0, z1)):
            normalized[local_z] = np.clip(
                (raw_patch[local_z] - lows[global_z]) / scales[global_z], 0, 1
            )
        raw_fraction = float(np.mean(normalized >= raw_cutoff))
    return mask_fraction, skeleton_present, raw_fraction


def _longest_false_fraction(supported):
    supported = np.asarray(supported, dtype=bool)
    edges = np.diff(np.pad((~supported).astype(np.int8), 1))
    starts = np.flatnonzero(edges == 1)
    stops = np.flatnonzero(edges == -1)
    longest = int(np.max(stops - starts)) if len(starts) else 0
    return longest / max(len(supported), 1)


def classify_topology_strut(
    material_coverage,
    potentially_broken_fraction=POTENTIALLY_BROKEN_MISSING_FRACTION,
    missing_fraction=MISSING_STRUT_MISSING_FRACTION,
):
    """Classify a predicted strut from its total fraction of absent material."""
    absent_fraction = 1.0 - float(material_coverage)
    epsilon = 1e-12
    if absent_fraction + epsilon >= missing_fraction:
        return "missing"
    if absent_fraction + epsilon >= potentially_broken_fraction:
        return "potentially_broken"
    return "likely_present"


def build_scan_interior_model(paths):
    """Build a conservative interior hull from observed TIFF junctions."""
    node_samples = defaultdict(list)
    for path in paths:
        if path["path_length_voxels"] < MIN_BRANCH_LENGTH:
            continue
        if path["start_type"] == "junction":
            node_samples[path["start_node"]].append(path["points"][0])
        if path["end_type"] == "junction":
            node_samples[path["end_node"]].append(path["points"][-1])
    points = np.asarray(
        [np.mean(samples, axis=0) for samples in node_samples.values()],
        dtype=float,
    )
    templates = _learn_connection_templates(paths)
    if len(points) < 4 or not templates:
        return None
    hull = ConvexHull(points)
    equations = np.asarray(hull.equations, dtype=float)
    normals = equations[:, :-1]
    offsets = equations[:, -1]
    normal_lengths = np.linalg.norm(normals, axis=1)
    edge_length = float(np.median([np.linalg.norm(value) for value in templates]))
    return {
        "normals": normals,
        "offsets": offsets,
        "normal_lengths": normal_lengths,
        "margin": edge_length,
    }


def points_in_scan_interior(
    points,
    model,
    margin_scale=1.0,
    margin_voxels=None,
):
    """Return True where points lie one strut length inside the observed hull."""
    points = np.atleast_2d(np.asarray(points, dtype=float))
    if model is None:
        return np.ones(len(points), dtype=bool)
    signed = (
        points @ model["normals"].T + model["offsets"]
    ) / model["normal_lengths"]
    distances = -np.max(signed, axis=1)
    required_margin = (
        float(margin_voxels)
        if margin_voxels is not None
        else margin_scale * model["margin"]
    )
    return distances >= required_margin


def exclude_boundary_defects(rows, interior_model):
    """Remove defect labels whose evidence touches the cropped lattice boundary."""
    for row in rows:
        if row["classification"] not in {"potentially_broken", "broken"}:
            continue
        evidence_points = (
            row["_gap_points"]
            if len(row["_gap_points"])
            else row["_points"][
                np.isin(row["_points"][:, 0], row["_thin_slices"])
            ]
        )
        if not len(evidence_points) or not np.all(
            points_in_scan_interior(
                evidence_points,
                interior_model,
                margin_voxels=EDGE_EXCLUSION_VOXELS,
            )
        ):
            row["classification"] = "normal"
            row["evidence"] = "boundary_transition"
            row["evidence_slices"] = ""
            row["_thin_slices"] = []
            row["_disconnected_slices"] = []
            row["_gap_points"] = np.empty((0, 3), dtype=np.int32)


def persistent_slice_group(values, max_gap_slices=MAX_TRACK_GAP_SLICES):
    """Return the strongest Z run while bridging only short observation gaps."""
    slices = sorted(set(int(value) for value in values))
    if not slices:
        return []
    groups = [[slices[0]]]
    for z in slices[1:]:
        if z - groups[-1][-1] <= max_gap_slices + 1:
            groups[-1].append(z)
        else:
            groups.append([z])
    return max(
        groups,
        key=lambda group: (len(group), group[-1] - group[0], -group[0]),
    )


def expanded_absence_indices(
    supported,
    consistent_samples=CONSISTENT_STRUCTURE_SAMPLES,
):
    """Expand the strongest absent run until structure is consistently present."""
    supported = np.asarray(supported, dtype=bool)
    if not len(supported) or np.all(supported):
        return np.empty(0, dtype=int)
    absent = ~supported
    edges = np.diff(np.pad(absent.astype(np.int8), 1))
    starts = np.flatnonzero(edges == 1)
    stops = np.flatnonzero(edges == -1)
    core_index = int(np.argmax(stops - starts))
    start, stop = int(starts[core_index]), int(stops[core_index])

    consecutive = 0
    expanded_start = start
    for index in range(start - 1, -1, -1):
        consecutive = consecutive + 1 if supported[index] else 0
        expanded_start = index
        if consecutive >= consistent_samples:
            expanded_start = index + consistent_samples
            break

    consecutive = 0
    expanded_stop = stop
    for index in range(stop, len(supported)):
        consecutive = consecutive + 1 if supported[index] else 0
        expanded_stop = index + 1
        if consecutive >= consistent_samples:
            expanded_stop = index - consistent_samples + 1
            break
    return np.arange(expanded_start, expanded_stop, dtype=int)


def _slice_material_present(
    point,
    z,
    mask,
    skeleton,
    raw,
    lows,
    scales,
    raw_cutoff,
    radius,
):
    """Require meaningful per-slice material; isolated skeleton voxels are weak."""
    _, y, x = np.rint(point).astype(int)
    y0, y1 = max(0, y - radius), min(mask.shape[1], y + radius + 1)
    x0, x1 = max(0, x - radius), min(mask.shape[2], x + radius + 1)
    mask_fraction = float(np.mean(mask[z, y0:y1, x0:x1] > 0))
    raw_fraction = 0.0
    if raw is not None:
        normalized = np.clip(
            (np.asarray(raw[z, y0:y1, x0:x1], dtype=float) - lows[z])
            / scales[z],
            0,
            1,
        )
        raw_fraction = float(np.mean(normalized >= raw_cutoff))
    return (
        mask_fraction >= 0.05
        or raw_fraction >= 0.05
    )


def expand_junction_boundary(
    junction,
    mask,
    skeleton,
    raw,
    lows,
    scales,
    raw_cutoff,
    valid_range,
    edge_length,
    radius,
):
    """Grow a persistent junction range until three strong material slices."""
    points = np.asarray(junction["proposal_points"], dtype=float)
    z_values = points[:, 0]
    if len(np.unique(np.rint(z_values))) >= 2:
        y_slope, y_intercept = np.polyfit(z_values, points[:, 1], 1)
        x_slope, x_intercept = np.polyfit(z_values, points[:, 2], 1)
    else:
        y_slope = x_slope = 0.0
        y_intercept, x_intercept = junction["point"][1:]

    def predicted(z):
        return np.asarray(
            [z, y_slope * z + y_intercept, x_slope * z + x_intercept],
            dtype=float,
        )

    seed_start, seed_stop = junction["z_min"], junction["z_max"]
    maximum_extension = max(
        1, int(math.ceil(JUNCTION_MAX_BOUNDARY_EXTENSION_SCALE * edge_length))
    )

    def grow(start, direction):
        boundary = start
        strong_run = 0
        for offset in range(1, maximum_extension + 1):
            z = start + direction * offset
            if not valid_range[0] <= z <= valid_range[1]:
                break
            strong = _slice_material_present(
                predicted(z),
                z,
                mask,
                skeleton,
                raw,
                lows,
                scales,
                raw_cutoff,
                radius,
            )
            strong_run = strong_run + 1 if strong else 0
            boundary = z
            if strong_run >= CONSISTENT_STRUCTURE_SAMPLES:
                boundary = z - direction * (CONSISTENT_STRUCTURE_SAMPLES - 1)
                boundary -= direction
                break
        return boundary

    z_min = grow(seed_start, -1)
    z_max = grow(seed_stop, 1)
    evidence_slices = list(range(z_min, z_max + 1))
    junction["z_min"] = z_min
    junction["z_max"] = z_max
    junction["observed_slice_count"] = len(evidence_slices)
    junction["bridged_gap_count"] = 0
    junction["evidence_slices"] = evidence_slices
    junction["z"] = evidence_slices[len(evidence_slices) // 2]
    junction["proposal_points"] = np.asarray(
        [predicted(z) for z in evidence_slices], dtype=float
    )


def infer_tiff_topology_defects(
    paths,
    mask,
    skeleton,
    raw,
    lows,
    scales,
    raw_cutoff,
    valid_range,
    interior_model,
    prediction_position_tolerance=PREDICTION_POSITION_TOLERANCE,
    potentially_broken_fraction=POTENTIALLY_BROKEN_MISSING_FRACTION,
    missing_fraction=MISSING_STRUT_MISSING_FRACTION,
    expected_structure=None,
):
    """Infer missing TIFF nodes/connections without using design coordinates."""
    node_samples = defaultdict(list)
    adjacency = set()
    incident_vectors = defaultdict(list)
    for path in paths:
        if path["path_length_voxels"] < MIN_BRANCH_LENGTH:
            continue
        if path["start_type"] == "junction":
            node_samples[path["start_node"]].append(path["points"][0])
        if path["end_type"] == "junction":
            node_samples[path["end_node"]].append(path["points"][-1])
        if path["start_type"] == path["end_type"] == "junction":
            first, second = path["start_node"], path["end_node"]
            adjacency.add(tuple(sorted((first, second))))
            delta = path["points"][-1].astype(float) - path["points"][0]
            incident_vectors[first].append(delta)
            incident_vectors[second].append(-delta)

    node_ids = sorted(node_samples)
    node_points = np.asarray(
        [np.mean(node_samples[node], axis=0) for node in node_ids], dtype=float
    )
    if not len(node_points):
        return [], []
    node_index = {node: index for index, node in enumerate(node_ids)}
    tree = cKDTree(node_points)
    templates = _learn_connection_templates(paths)
    if not templates:
        return [], []
    edge_length = float(np.median([np.linalg.norm(value) for value in templates]))
    # Junction inference intentionally uses the original, more conservative
    # proposal tolerance. Strut inference retains the newer recall setting.
    junction_match_tolerance = max(
        3.0, JUNCTION_PREDICTION_POSITION_TOLERANCE * edge_length
    )
    strut_match_tolerance = max(
        3.0, prediction_position_tolerance * edge_length
    )
    boundary_margin = EDGE_EXCLUSION_VOXELS
    expected_degrees = set(
        (expected_structure or {}).get("degree_histogram", {})
    )

    proposals = []
    shape = np.asarray(mask.shape, dtype=float)
    for node, point in zip(node_ids, node_points):
        for template in templates:
            for direction in (-1.0, 1.0):
                expected = point + direction * template
                if (
                    expected[0] < max(valid_range[0], boundary_margin)
                    or expected[0] > min(valid_range[1], shape[0] - boundary_margin)
                    or np.any(expected[1:] < boundary_margin)
                    or np.any(expected[1:] > shape[1:] - boundary_margin)
                    or not points_in_scan_interior(
                        expected,
                        interior_model,
                        margin_voxels=EDGE_EXCLUSION_VOXELS,
                    )[0]
                ):
                    continue
                distance, _ = tree.query(expected)
                if distance > junction_match_tolerance:
                    proposals.append(
                        {
                            "point": expected,
                            "source": node,
                            "vector": direction * template,
                        }
                    )

    proposal_clusters = []
    cluster_buckets = defaultdict(list)
    for proposal in proposals:
        bucket = tuple(
            np.floor(proposal["point"] / junction_match_tolerance).astype(int)
        )
        candidates = [
            index
            for offset in np.ndindex(3, 3, 3)
            for index in cluster_buckets[
                tuple(bucket[axis] + offset[axis] - 1 for axis in range(3))
            ]
        ]
        selected = next(
            (
                index
                for index in candidates
                if np.linalg.norm(
                    proposal["point"] - proposal_clusters[index]["center"]
                )
                <= junction_match_tolerance
            ),
            None,
        )
        if selected is None:
            selected = len(proposal_clusters)
            proposal_clusters.append(
                {"center": proposal["point"].copy(), "items": [proposal]}
            )
            cluster_buckets[bucket].append(selected)
        else:
            cluster = proposal_clusters[selected]
            cluster["items"].append(proposal)
            cluster["center"] = np.mean(
                [item["point"] for item in cluster["items"]], axis=0
            )

    missing_junctions = []
    node_radius = max(2, int(round(0.08 * edge_length)))
    for cluster in proposal_clusters:
        sources = {item["source"] for item in cluster["items"]}
        if len(sources) < MIN_MISSING_JUNCTION_SUPPORT:
            continue
        directions = [
            item["vector"] / np.linalg.norm(item["vector"])
            for item in cluster["items"]
        ]
        independent = any(
            abs(float(np.dot(first, second))) < 0.95
            for index, first in enumerate(directions)
            for second in directions[index + 1 :]
        )
        if not independent:
            continue
        direction_imbalance = float(
            np.linalg.norm(np.sum(directions, axis=0)) / len(directions)
        )
        if direction_imbalance >= 0.65:
            continue
        mask_fraction, skeleton_present, raw_fraction = _material_support_at(
            cluster["center"],
            mask,
            skeleton,
            raw,
            lows,
            scales,
            raw_cutoff,
            node_radius,
        )
        if skeleton_present or mask_fraction >= 0.05 or raw_fraction >= 0.05:
            continue
        missing_junctions.append(
            {
                "junction_id": len(missing_junctions),
                "point": cluster["center"],
                "z": int(round(cluster["center"][0])),
                "y": int(round(cluster["center"][1])),
                "x": int(round(cluster["center"][2])),
                "proposal_votes": len(sources),
                "mask_support": mask_fraction,
                "raw_support": raw_fraction,
                "cluster_id": -1,
                "cluster_size": 1,
                "structural_family": "",
                "proposal_points": np.asarray(
                    [item["point"] for item in cluster["items"]], dtype=float
                ),
            }
        )

    # Merge nearby consensus centers that describe the same absent physical node.
    if missing_junctions:
        candidate_tree = cKDTree(
            np.asarray([item["point"] for item in missing_junctions])
        )
        merged = []
        consumed = set()
        for start in range(len(missing_junctions)):
            if start in consumed:
                continue
            component = set(candidate_tree.query_ball_point(
                missing_junctions[start]["point"],
                PREDICTION_MERGE_TOLERANCE * edge_length,
            ))
            consumed.update(component)
            members = [missing_junctions[index] for index in sorted(component)]
            weights = np.asarray([item["proposal_votes"] for item in members])
            point = np.average(
                np.asarray([item["point"] for item in members]),
                axis=0,
                weights=weights,
            )
            merged.append(
                {
                    "junction_id": len(merged),
                    "point": point,
                    "z": int(round(point[0])),
                    "y": int(round(point[1])),
                    "x": int(round(point[2])),
                    "proposal_votes": int(np.sum(weights)),
                    "mask_support": float(
                        np.average(
                            [item["mask_support"] for item in members],
                            weights=weights,
                        )
                    ),
                    "raw_support": float(
                        np.average(
                            [item["raw_support"] for item in members],
                            weights=weights,
                        )
                    ),
                    "cluster_id": -1,
                    "cluster_size": 1,
                    "structural_family": "",
                    "proposal_points": np.vstack(
                        [item["proposal_points"] for item in members]
                    ),
                }
            )
        missing_junctions = merged

    # A junction absent on only one slice is not a missing junction. Preserve
    # the original candidate calculation above, then require its independent
    # proposal evidence to persist across at least two linked Z observations.
    persistent_junctions = []
    for junction in missing_junctions:
        proposal_points = np.asarray(junction["proposal_points"], dtype=float)
        proposal_slices = np.rint(proposal_points[:, 0]).astype(int)
        evidence_slices = persistent_slice_group(proposal_slices)
        if len(evidence_slices) < 2:
            continue
        selected = np.isin(proposal_slices, evidence_slices)
        junction["proposal_points"] = proposal_points[selected]
        junction["evidence_slices"] = evidence_slices
        junction["z_min"] = evidence_slices[0]
        junction["z_max"] = evidence_slices[-1]
        junction["observed_slice_count"] = len(evidence_slices)
        junction["bridged_gap_count"] = (
            evidence_slices[-1] - evidence_slices[0] + 1 - len(evidence_slices)
        )
        junction["z"] = evidence_slices[len(evidence_slices) // 2]
        junction["junction_id"] = len(persistent_junctions)
        expand_junction_boundary(
            junction,
            mask,
            skeleton,
            raw,
            lows,
            scales,
            raw_cutoff,
            valid_range,
            edge_length,
            node_radius,
        )
        persistent_junctions.append(junction)
    missing_junctions = persistent_junctions

    missing_tree = (
        cKDTree(np.asarray([item["point"] for item in missing_junctions]))
        if missing_junctions
        else None
    )
    visited = set()
    cluster_id = 0
    for start in range(len(missing_junctions)):
        if start in visited:
            continue
        component = []
        stack = [start]
        visited.add(start)
        while stack:
            current = stack.pop()
            component.append(current)
            for neighbor in missing_tree.query_ball_point(
                missing_junctions[current]["point"], 1.35 * edge_length
            ):
                separation = np.linalg.norm(
                    missing_junctions[current]["point"]
                    - missing_junctions[neighbor]["point"]
                )
                if neighbor not in visited and separation >= 0.65 * edge_length:
                    visited.add(neighbor)
                    stack.append(neighbor)
        for index in component:
            missing_junctions[index]["cluster_id"] = cluster_id
            missing_junctions[index]["cluster_size"] = len(component)
        cluster_id += 1

    missing_struts = []
    seen_pairs = set()
    for node, point in zip(node_ids, node_points):
        for template_index, template in enumerate(templates):
            for direction in (-1.0, 1.0):
                expected = point + direction * template
                distance, target_index = tree.query(expected)
                if distance > strut_match_tolerance:
                    continue
                target = node_ids[int(target_index)]
                pair = tuple(sorted((node, target)))
                if pair in seen_pairs or pair in adjacency or pair[0] == pair[1]:
                    continue
                seen_pairs.add(pair)
                direction_vector = direction * template
                minimum_endpoint_cosine = math.cos(
                    math.radians(ENDPOINT_ANGLE_TOLERANCE_DEGREES)
                )
                first_has_collinear_support = any(
                    abs(
                        float(
                            np.dot(value, direction_vector)
                            / (np.linalg.norm(value) * np.linalg.norm(direction_vector))
                        )
                    )
                    >= minimum_endpoint_cosine
                    for value in incident_vectors[node]
                )
                second_has_collinear_support = any(
                    abs(
                        float(
                            np.dot(value, direction_vector)
                            / (np.linalg.norm(value) * np.linalg.norm(direction_vector))
                        )
                    )
                    >= minimum_endpoint_cosine
                    for value in incident_vectors[target]
                )
                if not (
                    first_has_collinear_support and second_has_collinear_support
                ):
                    continue
                second = node_points[node_index[target]]
                count = max(3, int(np.ceil(np.linalg.norm(second - point))) + 1)
                full_line = np.linspace(point, second, count)
                trim = max(1, int(round(STRUT_ENDPOINT_TRIM_FRACTION * count)))
                line = full_line[
                    trim : max(trim + 1, count - trim)
                ]
                if not np.all(
                    points_in_scan_interior(
                        line,
                        interior_model,
                        margin_voxels=EDGE_EXCLUSION_VOXELS,
                    )
                ):
                    continue
                supported = []
                for sample in line:
                    mask_fraction, skeleton_present, raw_fraction = _material_support_at(
                        sample, mask, skeleton, raw, lows, scales, raw_cutoff, 2
                    )
                    supported.append(
                        skeleton_present
                        or mask_fraction >= LOCAL_MATERIAL_SUPPORT_FRACTION
                        or raw_fraction >= LOCAL_MATERIAL_SUPPORT_FRACTION
                    )
                coverage = float(np.mean(supported)) if supported else 1.0
                unsupported_fraction = _longest_false_fraction(supported)
                anomaly_indices = expanded_absence_indices(supported)
                classification = classify_topology_strut(
                    coverage,
                    potentially_broken_fraction,
                    missing_fraction,
                )
                if classification != "likely_present":
                    endpoint_degree_score = float(
                        np.mean(
                            [
                                not expected_degrees
                                or len(incident_vectors[endpoint]) + 1
                                in expected_degrees
                                for endpoint in (node, target)
                            ]
                        )
                    )
                    missing_struts.append(
                        {
                            "strut_id": len(missing_struts),
                            "endpoint0": node,
                            "endpoint1": target,
                            "start": point.copy(),
                            "end": second.copy(),
                            "midpoint": 0.5 * (point + second),
                            "material_coverage": coverage,
                            "unsupported_run_fraction": unsupported_fraction,
                            "classification": classification,
                            "structural_family": template_index,
                            "sample_points": np.asarray(line, dtype=float),
                            "sample_supported": np.asarray(supported, dtype=bool),
                            "anomaly_points": np.asarray(
                                line[anomaly_indices], dtype=float
                            ),
                            "full_line": np.asarray(full_line, dtype=float),
                            "structural_confidence": endpoint_degree_score,
                        }
                    )
    return missing_junctions, missing_struts


def _one_point_per_slice(points):
    """Collapse a sampled 3D trajectory to one mean Y/X position per Z slice."""
    points = np.asarray(points, dtype=float)
    if not len(points):
        return []
    rounded_z = np.rint(points[:, 0]).astype(int)
    return [
        np.asarray(
            [z, *np.mean(points[rounded_z == z, 1:], axis=0)],
            dtype=float,
        )
        for z in sorted(set(rounded_z))
    ]


def track_anomaly_observations(
    observations,
    position_tolerance,
    max_gap_slices=MAX_TRACK_GAP_SLICES,
):
    """Associate compatible slice observations into naturally ending 3D tracks."""
    if max_gap_slices < 0:
        raise ValueError("max_gap_slices must be non-negative")
    ordered = sorted(
        observations,
        key=lambda item: (
            int(item["slice"]),
            str(item["anomaly_type"]),
            str(item["structural_family"]),
            tuple(np.asarray(item["point"], dtype=float)),
        ),
    )
    active = []
    finished = []

    for z in sorted({int(item["slice"]) for item in ordered}):
        current = [item for item in ordered if int(item["slice"]) == z]
        still_active = []
        for track in active:
            if z - track["last_slice"] <= max_gap_slices + 1:
                still_active.append(track)
            else:
                finished.append(track)
        active = still_active

        matches = []
        for track_index, track in enumerate(active):
            elapsed = z - track["last_slice"]
            if elapsed <= 0:
                continue
            if len(track["observations"]) >= 2:
                previous = track["observations"][-2]
                last = track["observations"][-1]
                dz = max(1, int(last["slice"]) - int(previous["slice"]))
                velocity = (
                    np.asarray(last["point"], dtype=float)
                    - np.asarray(previous["point"], dtype=float)
                ) / dz
                predicted = np.asarray(last["point"], dtype=float) + velocity * elapsed
            else:
                predicted = np.asarray(track["observations"][-1]["point"], dtype=float)
            for observation_index, observation in enumerate(current):
                if (
                    observation["anomaly_type"] != track["anomaly_type"]
                    or observation["structural_family"]
                    != track["structural_family"]
                ):
                    continue
                distance = float(
                    np.linalg.norm(
                        np.asarray(observation["point"], dtype=float)[1:]
                        - predicted[1:]
                    )
                )
                gate = position_tolerance * max(1, elapsed)
                if distance <= gate:
                    matches.append(
                        (
                            distance / max(gate, 1e-9),
                            -float(observation["confidence"]),
                            track_index,
                            observation_index,
                        )
                    )

        used_tracks = set()
        used_observations = set()
        for _, _, track_index, observation_index in sorted(matches):
            if track_index in used_tracks or observation_index in used_observations:
                continue
            observation = current[observation_index]
            track = active[track_index]
            track["observations"].append(observation)
            track["last_slice"] = z
            used_tracks.add(track_index)
            used_observations.add(observation_index)

        for observation_index, observation in enumerate(current):
            if observation_index in used_observations:
                continue
            active.append(
                {
                    "anomaly_type": observation["anomaly_type"],
                    "structural_family": observation["structural_family"],
                    "last_slice": z,
                    "observations": [observation],
                }
            )

    finished.extend(active)
    tracks = []
    for track_id, track in enumerate(
        sorted(
            finished,
            key=lambda item: (
                int(item["observations"][0]["slice"]),
                item["anomaly_type"],
                str(item["structural_family"]),
                tuple(np.asarray(item["observations"][0]["point"])),
            ),
        )
    ):
        observations = track["observations"]
        slices = sorted({int(item["slice"]) for item in observations})
        z_min, z_max = slices[0], slices[-1]
        gaps = z_max - z_min + 1 - len(slices)
        mean_confidence = float(
            np.mean([float(item["confidence"]) for item in observations])
        )
        confidence = float(np.clip(mean_confidence * math.exp(-0.15 * gaps), 0, 1))
        tracks.append(
            {
                "track_id": track_id,
                "anomaly_type": track["anomaly_type"],
                "structural_family": track["structural_family"],
                "z_min": z_min,
                "z_max": z_max,
                "observed_slice_count": len(slices),
                "bridged_gap_count": gaps,
                "representative_slice": slices[len(slices) // 2],
                "confidence": confidence,
                "point": np.mean(
                    [np.asarray(item["point"], dtype=float) for item in observations],
                    axis=0,
                ),
                "source_ids": sorted(
                    {int(item["source_id"]) for item in observations}
                ),
                "observed_slices": slices,
            }
        )
    return tracks


def build_topology_tracks(
    missing_junctions,
    topology_struts,
    edge_length,
    position_tolerance_fraction=PREDICTION_POSITION_TOLERANCE,
    max_gap_slices=MAX_TRACK_GAP_SLICES,
):
    """Build track observations from TIFF-derived junction and strut evidence."""
    observations = []
    for junction in missing_junctions:
        for point in _one_point_per_slice(junction["proposal_points"]):
            observations.append(
                {
                    "slice": int(round(point[0])),
                    "point": point,
                    "anomaly_type": "missing_junction",
                    "structural_family": junction.get("structural_family", ""),
                    "confidence": 0.8
                    * (
                        1.0
                        - max(junction["mask_support"], junction["raw_support"])
                    )
                    + 0.2 * min(1.0, junction["proposal_votes"] / 3.0),
                    "source_id": junction["junction_id"],
                }
            )
    for strut in topology_struts:
        points = (
            strut["full_line"]
            if strut["classification"] == "missing"
            else strut["anomaly_points"]
        )
        anomaly_type = (
            "missing_strut"
            if strut["classification"] == "missing"
            else "potentially_broken_strut"
        )
        for point in _one_point_per_slice(points):
            observations.append(
                {
                    "slice": int(round(point[0])),
                    "point": point,
                    "anomaly_type": anomaly_type,
                    "structural_family": strut["structural_family"],
                    "confidence": 0.8 * (1.0 - strut["material_coverage"])
                    + 0.2 * strut.get("structural_confidence", 1.0),
                    "source_id": strut["strut_id"],
                }
            )
    return track_anomaly_observations(
        observations,
        position_tolerance=max(3.0, position_tolerance_fraction * edge_length),
        max_gap_slices=max_gap_slices,
    )


def reportable_topology_struts(struts, include_potentially_broken=False):
    """Keep missing struts while pausing topology warnings by default."""
    if include_potentially_broken:
        return list(struts)
    return [
        strut for strut in struts if strut["classification"] == "missing"
    ]


def build_missing_candidates(paths, rows, missing_total, volume_shape, valid_range):
    """Rank unique TIFF-derived locations and select exactly the global deficit."""
    path_by_id = {path["id"]: path for path in paths}
    candidates = []

    def add(location, evidence, priority, confidence, source=""):
        point = np.asarray(location, dtype=float)
        if not valid_range[0] <= point[0] <= valid_range[1]:
            return
        candidates.append(
            {
                "location": point,
                "evidence": evidence,
                "priority": priority,
                "confidence": float(np.clip(confidence, 0, 1)),
                "source": source,
            }
        )

    # A 4+-slice physical gap is already a direct missing-strut event.
    for row in rows:
        if row["classification"] == "missing" and len(row["_gap_points"]):
            add(
                np.mean(row["_gap_points"], axis=0),
                "consecutive_missing_gap",
                6,
                row["anomaly_score"],
                str(row["strut_id"]),
            )

    # Every incomplete fragment contributes its terminal evidence and midpoint.
    for row in rows:
        if row["classification"] != "incomplete_fragment":
            continue
        source_ids = [int(value) for value in row["source_paths"].split(";") if value]
        for source_id in source_ids:
            path = path_by_id[source_id]
            if path["start_type"] == "terminal":
                add(
                    path["points"][0],
                    "unmatched_endpoint",
                    4,
                    row["anomaly_score"],
                    str(row["strut_id"]),
                )
            if path["end_type"] == "terminal":
                add(
                    path["points"][-1],
                    "unmatched_endpoint",
                    4,
                    row["anomaly_score"],
                    str(row["strut_id"]),
                )
        add(
            np.mean(row["_points"], axis=0),
            "incomplete_fragment",
            2,
            row["anomaly_score"],
            str(row["strut_id"]),
        )

    # Junctions with fewer incident paths than the modal observed degree.
    junction_paths = defaultdict(list)
    junction_coordinates = defaultdict(list)
    for path in paths:
        if path["path_length_voxels"] < MIN_BRANCH_LENGTH:
            continue
        if path["start_type"] == "junction":
            junction_paths[path["start_node"]].append(path["id"])
            junction_coordinates[path["start_node"]].append(path["points"][0])
        if path["end_type"] == "junction":
            junction_paths[path["end_node"]].append(path["id"])
            junction_coordinates[path["end_node"]].append(path["points"][-1])
    degree_counts = Counter(len(value) for value in junction_paths.values())
    typical_degree = degree_counts.most_common(1)[0][0] if degree_counts else 0
    for node, incident in junction_paths.items():
        degree = len(incident)
        if 0 < degree < typical_degree:
            add(
                np.mean(junction_coordinates[node], axis=0),
                "abnormal_junction_degree",
                3,
                (typical_degree - degree) / typical_degree,
                str(node),
            )

    # Unusually long junction-to-junction paths can indicate a skipped junction.
    complete = [
        path
        for path in paths
        if path["start_type"] == path["end_type"] == "junction"
        and path["path_length_voxels"] >= MIN_BRANCH_LENGTH
    ]
    lengths = np.asarray([path["straight_length_um"] for path in complete])
    length_center = float(np.median(lengths))
    length_scale = 1.4826 * float(np.median(np.abs(lengths - length_center)))
    if length_scale > 0:
        for path in complete:
            z_score = (path["straight_length_um"] - length_center) / length_scale
            if z_score > 3:
                add(
                    np.mean(path["points"], axis=0),
                    "large_junction_gap",
                    1,
                    min(1.0, z_score / 6.0),
                    str(path["id"]),
                )

    # Prefer stronger evidence, then keep only one candidate per rounded voxel.
    candidates.sort(
        key=lambda item: (
            -item["priority"],
            -item["confidence"],
            item["evidence"],
            tuple(item["location"]),
        )
    )
    unique = []
    seen = set()
    for candidate in candidates:
        voxel = tuple(np.rint(candidate["location"]).astype(int))
        if voxel in seen:
            continue
        seen.add(voxel)
        candidate["voxel"] = voxel
        unique.append(candidate)
    if len(unique) < missing_total:
        raise ValueError(
            f"only {len(unique)} unique TIFF candidates were found for "
            f"{missing_total} globally missing struts"
        )

    selected = unique[:missing_total]
    for rank, candidate in enumerate(selected, start=1):
        z, y, x = candidate["voxel"]
        candidate.update(
            {
                "candidate_id": rank - 1,
                "rank": rank,
                "slice": int(np.clip(z, 0, volume_shape[0] - 1)),
                "z": z,
                "y": y,
                "x": x,
            }
        )
    return selected


def missing_candidates_by_slice(candidates, slice_count, slice_statistics):
    evidence_types = (
        "consecutive_missing_gap",
        "unmatched_endpoint",
        "incomplete_fragment",
        "abnormal_junction_degree",
        "large_junction_gap",
    )
    statistics_by_slice = {row["slice"]: row for row in slice_statistics}
    rows = []
    for z in range(slice_count):
        selected = [
            candidate
            for candidate in candidates
            if candidate.get("z_min", candidate["slice"])
            <= z
            <= candidate.get("z_max", candidate["slice"])
        ]
        counts = Counter(candidate["evidence"] for candidate in selected)
        statistics = statistics_by_slice.get(
            z, {"normal": 0, "broken": 0, "fragments": 0, "gaps": 0}
        )
        topology_potentially_broken = counts[
            "tiff_topology_potentially_broken_strut"
        ]
        rows.append(
            {
                "slice": z,
                "normal_struts": statistics["normal"],
                "potentially_broken_struts": (
                    statistics["broken"] + topology_potentially_broken
                ),
                "unmatched_fragment_endpoints": statistics["fragments"],
                "suspected_gap_locations": statistics["gaps"],
                "missing_struts": counts["tiff_topology_missing_strut"],
                **{name: counts[name] for name in evidence_types},
                "candidate_ids": ";".join(
                    str(candidate["candidate_id"]) for candidate in selected
                ),
            }
        )
    return rows


def load_expected_structure(json_path):
    """Load coordinate-free topology priors; design positions are intentionally ignored."""
    if json_path is None:
        return {
            "junction_count": None,
            "strut_count": None,
            "degree_histogram": {},
            "edge_family_count": None,
        }
    design = json.loads(json_path.read_text())
    degrees = Counter()
    for strut in design["struts"]:
        degrees[int(strut["junction0"])] += 1
        degrees[int(strut["junction1"])] += 1
    edge_families = {
        strut.get("unit_cell_edge_idx")
        for strut in design["struts"]
        if "unit_cell_edge_idx" in strut
    }
    return {
        "junction_count": len(design["junctions"]),
        "strut_count": len(design["struts"]),
        "degree_histogram": dict(Counter(degrees.values())),
        "edge_family_count": len(edge_families) if edge_families else None,
    }


def interior_slice_range(rows, slice_count):
    """Exclude the bottom/top partial-volume transitions from slice reporting."""
    actual = np.zeros(slice_count, dtype=int)
    for row in rows:
        if row["effective_count"]:
            actual[row["z_min"] : row["z_max"] + 1] += 1
    relevant = actual[actual > 0]
    cutoff = 0.70 * np.median(relevant)
    stable = np.flatnonzero(actual >= cutoff)
    return int(stable[0]), int(stable[-1])


def struts_by_slice(rows, slice_count, valid_range):
    normal = np.zeros(slice_count, dtype=int)
    broken = np.zeros(slice_count, dtype=int)
    fragments = np.zeros(slice_count, dtype=int)
    gaps = np.zeros(slice_count, dtype=int)
    for row in rows:
        start, stop = row["z_min"], row["z_max"] + 1
        if row["classification"] == "normal" and row["effective_count"]:
            normal[start:stop] += 1
        elif (
            row["classification"] in {"potentially_broken", "broken"}
            and row["effective_count"]
        ):
            event_slices = row["_disconnected_slices"] or row["_thin_slices"]
            if event_slices:
                broken[event_slices[len(event_slices) // 2]] += 1
        elif row["classification"] == "incomplete_fragment":
            endpoint_slices = {
                int(point[0])
                for point in row["_endpoints"]
                if valid_range[0] <= int(point[0]) <= valid_range[1]
            }
            for z in endpoint_slices:
                fragments[z] += 1
        fully_interior = (
            row["z_min"] >= valid_range[0] and row["z_max"] <= valid_range[1]
        )
        if (
            row["classification"] == "broken"
            and fully_interior
            and row["evidence"] == "fragment_gap"
        ):
            gap_slices = row["_disconnected_slices"]
            if gap_slices:
                gaps[gap_slices[len(gap_slices) // 2]] += 1
    first_slice, last_slice = valid_range
    return [
        {
            "slice": index,
            "normal": int(normal[index]),
            "broken": int(broken[index]),
            "fragments": int(fragments[index]),
            "gaps": int(gaps[index]),
        }
        for index in range(first_slice, last_slice + 1)
    ]


def write_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    key: f"{row[key]:.8g}"
                    if isinstance(row[key], float)
                    else row[key]
                    for key in CSV_FIELDS
                }
            )


def write_missing_candidate_csv(path, candidates):
    fields = (
        "candidate_id",
        "track_id",
        "rank",
        "evidence",
        "confidence",
        "source",
        "slice",
        "representative_slice",
        "z_min",
        "z_max",
        "observed_slice_count",
        "bridged_gap_count",
        "structural_family",
        "z",
        "y",
        "x",
    )
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for candidate in candidates:
            writer.writerow({field: candidate[field] for field in fields})


def write_missing_slice_csv(path, rows):
    fields = (
        "slice",
        "normal_struts",
        "potentially_broken_struts",
        "unmatched_fragment_endpoints",
        "suspected_gap_locations",
        "missing_struts",
        "consecutive_missing_gap",
        "unmatched_endpoint",
        "incomplete_fragment",
        "abnormal_junction_degree",
        "large_junction_gap",
        "candidate_ids",
    )
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_missing_junction_csv(path, junctions):
    fields = (
        "junction_id",
        "track_id",
        "z",
        "z_min",
        "z_max",
        "observed_slice_count",
        "bridged_gap_count",
        "y",
        "x",
        "confidence",
        "structural_family",
        "cluster_id",
        "cluster_size",
        "proposal_votes",
        "mask_support",
        "raw_support",
    )
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for junction in junctions:
            writer.writerow({field: junction[field] for field in fields})


def write_topology_strut_csv(path, struts):
    fields = (
        "strut_id",
        "track_id",
        "endpoint0",
        "endpoint1",
        "z",
        "z_min",
        "z_max",
        "observed_slice_count",
        "bridged_gap_count",
        "y",
        "x",
        "confidence",
        "structural_family",
        "material_coverage",
        "unsupported_run_fraction",
        "classification",
    )
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for strut in struts:
            z, y, x = np.rint(
                strut.get("_visualization_point", strut["midpoint"])
            ).astype(int)
            writer.writerow(
                {
                    "strut_id": strut["strut_id"],
                    "track_id": strut.get("track_id", ""),
                    "endpoint0": strut["endpoint0"],
                    "endpoint1": strut["endpoint1"],
                    "z": z,
                    "z_min": strut.get(
                        "z_min",
                        int(round(min(strut["start"][0], strut["end"][0]))),
                    ),
                    "z_max": strut.get(
                        "z_max",
                        int(round(max(strut["start"][0], strut["end"][0]))),
                    ),
                    "observed_slice_count": strut.get("observed_slice_count", 1),
                    "bridged_gap_count": strut.get("bridged_gap_count", 0),
                    "y": y,
                    "x": x,
                    "confidence": strut.get(
                        "confidence", 1.0 - strut["material_coverage"]
                    ),
                    "structural_family": strut.get("structural_family", ""),
                    "material_coverage": strut["material_coverage"],
                    "unsupported_run_fraction": strut[
                        "unsupported_run_fraction"
                    ],
                    "classification": strut["classification"],
                }
            )


def plot_box(path, values, threshold):
    figure, axis = plt.subplots(figsize=(8.5, 5.5))
    axis.boxplot(values, orientation="horizontal")
    axis.axvline(threshold, color="red", linestyle="--", label="Adaptive cutoff")
    axis.set(title="Per-strut Low-thickness Distribution", xlabel="Thickness (µm)")
    axis.legend()
    figure.tight_layout()
    figure.savefig(path, dpi=180)
    plt.close(figure)


def plot_cdf(path, values, threshold):
    ordered = np.sort(values)
    cumulative = np.arange(1, len(ordered) + 1) / len(ordered)
    figure, axis = plt.subplots(figsize=(8.5, 5.5))
    axis.plot(ordered, cumulative)
    axis.axvline(threshold, color="red", linestyle="--", label="Adaptive cutoff")
    axis.set(
        title="Per-strut Low-thickness CDF",
        xlabel="Thickness (µm)",
        ylabel="Cumulative fraction",
    )
    axis.legend()
    axis.grid(alpha=0.25)
    figure.tight_layout()
    figure.savefig(path, dpi=180)
    plt.close(figure)


def plot_validation(
    path, rows, slices, raw, mask, lows, scales, valid_range
):
    confirmed = [
        row
        for row in rows
        if row["classification"] in {"potentially_broken", "broken"}
        and row["z_min"] >= valid_range[0]
        and row["z_max"] <= valid_range[1]
    ]
    if confirmed:
        selected_slice = max(
            slices,
            key=lambda row: (
                row["broken"],
                row["gaps"],
                row["fragments"],
                -row["slice"],
            ),
        )["slice"]
        suspects = [
            row
            for row in confirmed
            if row["z_min"] <= selected_slice <= row["z_max"]
        ]
        if not suspects:
            suspects = [
                row
                for row in rows
                if row["classification"] == "incomplete_fragment"
                and row["z_min"] <= selected_slice <= row["z_max"]
            ][:5]
    else:
        suspects = sorted(
            (row for row in rows if row["effective_count"]),
            key=lambda row: -row["anomaly_score"],
        )[:1]
        selected_slice = int(
            np.clip(
                suspects[0]["weakest_slice"] if suspects else valid_range[0],
                valid_range[0],
                valid_range[1],
            )
        )

    first = max(valid_range[0], selected_slice - 5)
    last = min(valid_range[1], selected_slice + 5)
    display_slices = list(range(first, last + 1))
    figure, axes = plt.subplots(3, 4, figsize=(16, 12))
    axes = axes.ravel()
    colors = plt.cm.tab10(np.linspace(0, 1, max(1, len(suspects))))
    for axis, z in zip(axes, display_slices):
        if raw is not None:
            image = np.clip(
                (np.asarray(raw[z], dtype=float) - lows[z]) / scales[z], 0, 1
            )
        else:
            image = np.asarray(mask[z]) > 0
        axis.imshow(image, cmap="gray", vmin=0, vmax=1)
        axis.contour(np.asarray(mask[z]) > 0, levels=[0.5], colors="cyan", linewidths=0.35)
        for color, row in zip(colors, suspects):
            points = row["_points"]
            nearby = points[np.abs(points[:, 0] - z) <= 1]
            exact = points[points[:, 0] == z]
            if len(nearby):
                axis.plot(
                    nearby[:, 2],
                    nearby[:, 1],
                    color=color,
                    linewidth=1.0,
                    alpha=0.35,
                )
            if len(exact):
                axis.plot(
                    exact[:, 2],
                    exact[:, 1],
                    color=color,
                    linewidth=2.0,
                    label=f"strut {row['strut_id']}",
                )
            for endpoint in row["_endpoints"]:
                if endpoint[0] == z:
                    axis.scatter(
                        endpoint[2], endpoint[1], marker="x", s=45, color=color
                    )
            if z in row["_thin_slices"] and len(exact):
                axis.scatter(exact[:, 2], exact[:, 1], s=10, color="red")
            gap_points = row["_gap_points"]
            gap_here = gap_points[gap_points[:, 0] == z] if len(gap_points) else []
            if len(gap_here):
                axis.scatter(
                    gap_here[:, 2],
                    gap_here[:, 1],
                    s=35,
                    facecolors="none",
                    edgecolors="yellow",
                    linewidths=1.5,
                )
        axis.set_title(f"Z = {z}")
        axis.set_axis_off()
    for axis in axes[len(display_slices) :]:
        axis.set_axis_off()
    labels = [
        plt.Line2D([0], [0], color=color, lw=2, label=f"strut {row['strut_id']}")
        for color, row in zip(colors, suspects)
    ]
    if labels:
        figure.legend(handles=labels, loc="lower center", ncol=min(5, len(labels)))
    selected_confirmed = any(
        row["classification"] in {"potentially_broken", "broken"}
        for row in suspects
    )
    status = (
        "confirmed persistent candidates"
        if selected_confirmed
        else "TIFF suspicion candidates; no confirmed break on selected slice"
    )
    figure.suptitle(
        f"Broken-strut validation around Z={selected_slice}\n{status}",
        fontsize=15,
    )
    figure.tight_layout(rect=(0, 0.04, 1, 0.96))
    figure.savefig(path, dpi=180)
    plt.close(figure)
    return {
        "selected_slice": selected_slice,
        "first_slice": first,
        "last_slice": last,
        "strut_ids": [row["strut_id"] for row in suspects],
        "confirmed": selected_confirmed,
    }


def _trajectory_point_at_slice(points, z):
    points = np.asarray(points, dtype=float)
    if not len(points):
        raise ValueError("anomaly trajectory is empty")
    points = points[np.argsort(points[:, 0])]
    return np.asarray(
        [
            z,
            np.interp(z, points[:, 0], points[:, 1]),
            np.interp(z, points[:, 0], points[:, 2]),
        ]
    )


def build_visualization_defects(rows, missing_junctions, topology_struts):
    """Normalize exact per-slice evidence used by the contact sheets."""
    defects = []

    def add(defect_id, kind, source, points, z_min, z_max, primary):
        points = np.asarray(points, dtype=float)
        if not len(points):
            return
        evidence_slices = sorted(
            set(np.rint(points[:, 0]).astype(int).tolist())
        )
        defects.append(
            {
                "defect_id": defect_id,
                "kind": kind,
                "source": source,
                "points": points,
                "z_min": int(z_min),
                "z_max": int(z_max),
                "evidence_slices": evidence_slices,
                "evidence_center": float(np.median(evidence_slices)),
                "primary": bool(primary),
            }
        )

    for row in rows:
        if len(row["_gap_points"]):
            add(
                f"row:{row['strut_id']}",
                "broken fragment",
                row,
                row["_gap_points"],
                np.min(row["_gap_points"][:, 0]),
                np.max(row["_gap_points"][:, 0]),
                False,
            )
        elif row["classification"] == "potentially_broken" and row["_thin_slices"]:
            points = row["_points"][
                np.isin(row["_points"][:, 0], row["_thin_slices"])
            ]
            add(
                f"row:{row['strut_id']}",
                "sustained thin",
                row,
                points,
                min(row["_thin_slices"]),
                max(row["_thin_slices"]),
                False,
            )
    for junction in missing_junctions:
        add(
            f"junction:{junction['junction_id']}",
            "missing junction",
            junction,
            junction["proposal_points"],
            junction["z_min"],
            junction["z_max"],
            True,
        )
    for strut in topology_struts:
        kind = (
            "missing strut"
            if strut["classification"] == "missing"
            else "potentially broken strut"
        )
        # A full predicted centerline is a geometric range, not evidence that
        # every intersected slice is anomalous. Plot only locally absent
        # samples so normal material is never circled because of range overlap.
        points = strut["anomaly_points"]
        add(
            f"topology:{strut['strut_id']}",
            kind,
            strut,
            points,
            strut["z_min"],
            strut["z_max"],
            strut["classification"] == "missing",
        )
    return defects


def select_visualization_slices(defects, observed_layer_span):
    """Choose one evidence-rich slice per natural layer, then cover leftovers."""
    if not defects:
        return [], {}
    span = max(4.0, float(observed_layer_span))
    ordered = sorted(
        range(len(defects)),
        key=lambda index: (
            defects[index]["evidence_center"],
            defects[index]["defect_id"],
        ),
    )
    layer_groups = [[ordered[0]]]
    # The span is learned from the observed topology. A 60% split keeps
    # neighboring manifestations in one section without chaining distinct
    # approximately-one-layer-apart sections together.
    split_distance = 0.60 * span
    for index in ordered[1:]:
        previous = layer_groups[-1][-1]
        if (
            defects[index]["evidence_center"]
            - defects[previous]["evidence_center"]
            > split_distance
        ):
            layer_groups.append([index])
        else:
            layer_groups[-1].append(index)

    selected = set()
    primary_slices = []
    assignment = {}
    for members in layer_groups:
        uncovered = set(members)
        first_choice = True
        while uncovered:
            candidate_slices = sorted(
                {
                    z
                    for index in uncovered
                    for z in defects[index]["evidence_slices"]
                }
            )
            layer_center = float(
                np.median(
                    [defects[index]["evidence_center"] for index in members]
                )
            )
            z = max(
                candidate_slices,
                key=lambda value: (
                    sum(
                        defects[index]["primary"]
                        and value in defects[index]["evidence_slices"]
                        for index in uncovered
                    ),
                    sum(
                        value in defects[index]["evidence_slices"]
                        for index in uncovered
                    ),
                    -abs(value - layer_center),
                    -value,
                ),
            )
            selected.add(z)
            if first_choice:
                primary_slices.append(z)
                first_choice = False
            covered = {
                index
                for index in uncovered
                if z in defects[index]["evidence_slices"]
            }
            for index in covered:
                assignment[defects[index]["defect_id"]] = z
            uncovered -= covered

    return sorted(selected), assignment


def apply_visualization_representatives(
    defects,
    assignment,
    missing_candidates,
    selected_slices,
):
    """Make existing CSV representative coordinates match rendered panels."""
    topology_by_id = {}
    for defect in defects:
        z = assignment[defect["defect_id"]]
        point = _trajectory_point_at_slice(defect["points"], z)
        source = defect["source"]
        source["_visualization_point"] = point
        if defect["defect_id"].startswith("junction:"):
            source.update(
                {"z": int(z), "y": int(round(point[1])), "x": int(round(point[2]))}
            )
        elif defect["defect_id"].startswith("topology:"):
            topology_by_id[int(source["strut_id"])] = (
                z,
                point,
                defect["points"],
            )

    for candidate in missing_candidates:
        source_ids = [
            int(value) for value in candidate["source"].split(";") if value
        ]
        matches = [
            topology_by_id[source_id]
            for source_id in source_ids
            if source_id in topology_by_id
        ]
        if not matches:
            continue
        source_z, source_point, source_points = min(
            matches,
            key=lambda item: (
                not candidate["z_min"] <= item[0] <= candidate["z_max"],
                abs(item[0] - candidate["representative_slice"]),
            ),
        )
        eligible = [
            z
            for z in selected_slices
            if candidate["z_min"] <= z <= candidate["z_max"]
        ]
        z = (
            min(
                eligible,
                key=lambda value: (
                    value != source_z,
                    abs(value - candidate["representative_slice"]),
                    value,
                ),
            )
            if eligible
            else int(candidate["representative_slice"])
        )
        point = (
            source_point
            if z == source_z
            else _trajectory_point_at_slice(source_points, z)
        )
        candidate.update(
            {
                "slice": int(z),
                "representative_slice": int(z),
                "z": int(z),
                "y": int(round(point[1])),
                "x": int(round(point[2])),
            }
        )


def plot_gap_contact_sheets(
    output_dir,
    rows,
    missing_junctions,
    topology_missing_struts,
    raw,
    mask,
    lows,
    scales,
    visualization_defects=None,
    selected_slices=None,
):
    """Render TIFF-derived node, strut, fragment, and thinning defects."""
    defects_by_slice = defaultdict(list)
    for row in rows:
        if len(row["_gap_points"]):
            z, y, x = row["_gap_points"][len(row["_gap_points"]) // 2]
            defects_by_slice[int(z)].append(
                {
                    "kind": "broken fragment",
                    "y": int(y),
                    "x": int(x),
                    "strut_id": row["strut_id"],
                    "slice_range": (
                        int(np.min(row["_gap_points"][:, 0])),
                        int(np.max(row["_gap_points"][:, 0])),
                    ),
                }
            )
        if row["classification"] == "potentially_broken":
            z = row["_thin_slices"][len(row["_thin_slices"]) // 2]
            exact = row["_points"][row["_points"][:, 0] == z]
            if len(exact):
                _, y, x = exact[len(exact) // 2]
                defects_by_slice[int(z)].append(
                    {
                        "kind": "sustained thin",
                        "y": int(y),
                        "x": int(x),
                        "strut_id": row["strut_id"],
                        "slice_range": (
                            min(row["_thin_slices"]),
                            max(row["_thin_slices"]),
                        ),
                    }
                )
    for junction in missing_junctions:
        defects_by_slice[junction["z"]].append(
            {
                "kind": "missing junction",
                "y": junction["y"],
                "x": junction["x"],
                "strut_id": junction["junction_id"],
                "cluster_size": junction["cluster_size"],
                "slice_range": (
                    junction.get("z_min", junction["z"]),
                    junction.get("z_max", junction["z"]),
                ),
            }
        )
    for strut in topology_missing_struts:
        z, y, x = np.rint(strut["midpoint"]).astype(int)
        kind = (
            "missing strut"
            if strut["classification"] == "missing"
            else "potentially broken strut"
        )
        defects_by_slice[int(z)].append(
            {
                "kind": kind,
                "y": int(y),
                "x": int(x),
                "strut_id": strut["strut_id"],
                "slice_range": (
                    strut.get(
                        "z_min",
                        int(round(min(strut["start"][0], strut["end"][0]))),
                    ),
                    strut.get(
                        "z_max",
                        int(round(max(strut["start"][0], strut["end"][0]))),
                    ),
                ),
            }
        )

    if visualization_defects is not None and selected_slices is not None:
        defects_by_slice = defaultdict(list)
        for z in selected_slices:
            for defect in visualization_defects:
                if z not in defect["evidence_slices"]:
                    continue
                point = _trajectory_point_at_slice(defect["points"], z)
                source = defect["source"]
                identifier = (
                    source["junction_id"]
                    if defect["kind"] == "missing junction"
                    else source["strut_id"]
                )
                defects_by_slice[int(z)].append(
                    {
                        "kind": defect["kind"],
                        "y": int(round(point[1])),
                        "x": int(round(point[2])),
                        "strut_id": identifier,
                        "cluster_size": source.get("cluster_size", 1),
                        "slice_range": (defect["z_min"], defect["z_max"]),
                    }
                )

    if not defects_by_slice:
        return []

    items = sorted(defects_by_slice.items())
    paths = []
    styles = {
        "missing junction": ("magenta", 300),
        "missing strut": ("yellow", 260),
        "potentially broken strut": ("orange", 240),
        "broken fragment": ("red", 260),
        "sustained thin": ("orange", 220),
    }
    panels_per_sheet = 12
    for page, offset in enumerate(range(0, len(items), panels_per_sheet), start=1):
        page_items = items[offset : offset + panels_per_sheet]
        column_count = min(4, len(page_items))
        row_count = int(math.ceil(len(page_items) / column_count))
        figure, axes = plt.subplots(
            row_count,
            column_count,
            figsize=(4 * column_count, 4 * row_count),
            squeeze=False,
        )
        axes = axes.ravel()
        for axis, (z, defects) in zip(axes, page_items):
            if raw is not None:
                image = np.clip(
                    (np.asarray(raw[z], dtype=float) - lows[z]) / scales[z],
                    0,
                    1,
                )
            else:
                image = np.asarray(mask[z]) > 0
            axis.imshow(image, cmap="gray", vmin=0, vmax=1)
            axis.contour(
                np.asarray(mask[z]) > 0,
                levels=[0.5],
                colors="cyan",
                linewidths=0.5,
            )
            for defect in defects:
                color, size = styles[defect["kind"]]
                axis.scatter(
                    defect["x"],
                    defect["y"],
                    s=size,
                    marker="o",
                    facecolors="none",
                    edgecolors=color,
                    linewidths=2.5,
                )
                prefix = {
                    "missing junction": "J",
                    "missing strut": "M",
                    "potentially broken strut": "P",
                    "broken fragment": "B",
                    "sustained thin": "T",
                }[defect["kind"]]
                first_z, last_z = defect["slice_range"]
                label = f"{prefix}{defect['strut_id']} Z{first_z}–{last_z}"
                if defect.get("cluster_size", 1) > 1:
                    label += f" C{defect['cluster_size']}"
                axis.text(
                    defect["x"] + 8,
                    defect["y"] - 8,
                    label,
                    color=color,
                    fontsize=7,
                    bbox={"facecolor": "black", "alpha": 0.65, "pad": 1},
                )
            counts = Counter(defect["kind"] for defect in defects)
            summary = "; ".join(
                f"{kind} ×{count}" for kind, count in sorted(counts.items())
            )
            axis.set_title(f"Slice Z={z}\n{summary}")
            axis.set_axis_off()
        for axis in axes[len(page_items) :]:
            axis.set_axis_off()
        visible_kinds = {
            defect["kind"]
            for _, defects in page_items
            for defect in defects
        }
        legend = [
            plt.Line2D(
                [0],
                [0],
                marker="o",
                linestyle="none",
                markerfacecolor="none",
                markeredgecolor=color,
                markeredgewidth=2,
                label=kind,
            )
            for kind, (color, _) in styles.items()
            if kind in visible_kinds
        ]
        figure.legend(
            handles=legend,
            loc="lower center",
            ncol=max(1, len(legend)),
        )
        figure.suptitle(f"Detected gap slices — page {page}", fontsize=16)
        figure.tight_layout(rect=(0, 0.05, 1, 0.96))
        path = output_dir / f"gap_slices_{page:02d}.png"
        figure.savefig(path, dpi=180)
        plt.close(figure)
        paths.append(path)
    return paths


def write_summary(
    path,
    rows,
    slices,
    expected_total,
    valid_range,
    threshold,
    center,
    scale,
    scale_method,
    percentile,
    spacing_um,
    edt_diagnostics,
    raw_cutoff,
    validation,
    missing_candidates,
    candidate_slices,
    gap_sheet_paths,
    expected_junctions,
    observed_junctions,
    missing_junctions,
    topology_missing_struts,
):
    first_slice, last_slice = valid_range
    interior_rows = [
        row for row in rows if row["z_min"] >= first_slice and row["z_max"] <= last_slice
    ]
    effective = sum(row["effective_count"] for row in rows)
    broken = sum(
        row["classification"] == "potentially_broken" and row["effective_count"]
        for row in rows
    )
    fragment_broken = sum(row["classification"] == "broken" for row in rows)
    topology_missing = sum(
        strut["classification"] == "missing"
        for strut in topology_missing_struts
    )
    topology_potentially_broken = sum(
        strut["classification"] == "potentially_broken"
        for strut in topology_missing_struts
    )
    faded = sum(bool(row["segmentation_fade"]) for row in interior_rows)
    suspected_ids = [
        row["strut_id"]
        for row in interior_rows
        if row["classification"] in {"potentially_broken", "missing"}
    ]
    mean_recentered = float(
        np.mean([row["recentered_fraction"] for row in interior_rows])
    )
    missing = expected_total - effective if expected_total is not None else "not available"
    top_candidate_slices = sorted(
        (
            row
            for row in candidate_slices
            if row["potentially_broken_struts"] or row["missing_struts"]
        ),
        key=lambda row: (
            -row["potentially_broken_struts"],
            -row["missing_struts"],
            row["slice"],
        ),
    )[:30]
    top_gap_slices = sorted(
        (row for row in candidate_slices if row["suspected_gap_locations"] > 0),
        key=lambda row: (
            -row["suspected_gap_locations"],
            row["slice"],
        ),
    )[:30]
    lines = [
        "# 3D Strut Thickness and Defect Summary",
        "",
        "- JSON coordinate usage: **none**",
        "- JSON usage: **expected junction and strut counts only**",
        f"- Expected junctions: **{expected_junctions if expected_junctions is not None else 'not available'}**",
        f"- Observed TIFF junctions: **{observed_junctions}**",
        f"- TIFF-derived missing junctions: **{len(missing_junctions)}**",
        f"- Missing-junction clusters: **{len(set(item['cluster_id'] for item in missing_junctions))}**",
        f"- Full design struts: **{expected_total if expected_total is not None else 'not available'}**",
        f"- TIFF interior reporting range: **slices {first_slice}–{last_slice}**",
        f"- Effective detected struts: **{effective}**",
        f"- Expected-minus-observed strut count deficit: **{missing}**",
        f"- TIFF-topology missing struts: **{topology_missing}**",
        (
            "- TIFF-topology potentially broken struts: "
            f"**{topology_potentially_broken}**"
        ),
        f"- Broken fragment pairs: **{fragment_broken}**",
        (
            f"- Estimated missing percentage: "
            f"**{100 * missing / expected_total:.2f}%**"
            if expected_total
            else "- Estimated missing percentage: **not available**"
        ),
        f"- Thickness-derived potentially broken struts: **{broken}**",
        (
            "- Thickness-derived potentially broken percentage: "
            f"**{100 * broken / effective:.2f}%**"
        ),
        f"- Selected TIFF-topology anomaly candidates: **{len(missing_candidates)}**",
        (
            "- Per-slice selected-candidate total: "
            f"**{sum(row['missing_struts'] for row in candidate_slices)}**"
        ),
        f"- All suspected strut IDs: **{', '.join(str(value) for value in suspected_ids) or 'none'}**",
        f"- Voxel spacing (Z/Y/X): **{spacing_um[0]:g}/{spacing_um[1]:g}/{spacing_um[2]:g} µm**",
        f"- Adaptive statistic: **P{percentile:g} thickness**",
        f"- Distribution median: **{center:.2f} µm**",
        f"- Robust scale: **{scale:.2f} µm ({scale_method})**",
        f"- Adaptive cutoff: **{threshold:.2f} µm**",
        f"- Skeleton samples recentered to a thicker local EDT ridge: **{100 * mean_recentered:.2f}%**",
        f"- Slabs requiring a larger EDT halo: **{edt_diagnostics['expanded_slabs']}**",
        f"- Largest measured centerline radius: **{edt_diagnostics['largest_radius_voxels']:.2f} minimum-spacing voxels**",
        f"- Raw-CT material-support cutoff: **{raw_cutoff:.3f}**",
        f"- Segmentation-fade candidates not counted as broken: **{faded}**",
        "",
        "## Manual broken-strut validation",
        "",
        f"- Selected slice: **{validation['selected_slice']}**",
        f"- Neighboring range: **{validation['first_slice']}–{validation['last_slice']}**",
        (
            "- Suspected strut IDs: **"
            + (", ".join(str(value) for value in validation["strut_ids"]) or "none")
            + "**"
        ),
        (
            "- Status: **confirmed persistent candidates**"
            if validation["confirmed"]
            else "- Status: **no persistent candidate passed; highest-score region shown**"
        ),
        "",
        "![Raw CT, segmentation, and centerline validation](png_outputs/broken_strut_validation.png)",
        "",
        "## Gap slice visualizations",
        "",
    ]
    if gap_sheet_paths:
        for sheet_path in gap_sheet_paths:
            lines.extend(
                [
                    f"![Circled detected gap slices](png_outputs/{sheet_path.name})",
                    "",
                ]
            )
    else:
        lines.extend(["No detected gap slices.", ""])
    lines.extend(
        [
            "## TIFF-only topology evidence",
            "",
            f"- Missing junctions: **{len(missing_junctions)}**",
            f"- Missing-junction clusters: **{len(set(item['cluster_id'] for item in missing_junctions))}**",
            f"- Completely missing struts between present junctions: **{topology_missing}**",
            (
                "- Potentially broken topology struts between present junctions: "
                f"**{topology_potentially_broken}**"
            ),
            f"- Broken fragment pairs: **{fragment_broken}**",
            f"- Sustained relative-thickness candidates: **{broken}**",
            "",
            "## Top 30 slices by potentially broken, then missing struts",
            "",
            (
                "> Each selected 3D candidate is allocated to every slice in its "
                "inclusive tracked range. The complete allocation is available in "
                "`missing_strut_candidates_by_slice.csv`."
            ),
            "",
            "| Slice | Normal struts | Potentially broken | Unmatched endpoints | Gap locations | Missing struts |",
            "|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in top_candidate_slices:
        lines.append(
            f"| {row['slice']} | {row['normal_struts']} | "
            f"{row['potentially_broken_struts']} | "
            f"{row['unmatched_fragment_endpoints']} | "
            f"{row['suspected_gap_locations']} | "
            f"{row['missing_struts']} |"
        )
    lines.extend(
        [
            "",
            "## Top 30 slices by gap locations",
            "",
            (
                "> Each continuous gap event is counted once on its midpoint "
                "slice, not once on every absent slice."
            ),
            "",
            "| Slice | Gap locations | Potentially broken | Missing struts | Unmatched endpoints |",
            "|---:|---:|---:|---:|---:|",
        ]
    )
    for row in top_gap_slices:
        lines.append(
            f"| {row['slice']} | {row['suspected_gap_locations']} | "
            f"{row['potentially_broken_struts']} | "
            f"{row['missing_struts']} | "
            f"{row['unmatched_fragment_endpoints']} |"
        )
    lines.extend(
        [
            "",
            "## Classifications",
            "",
            "- `normal`: complete detected strut without strong anomaly evidence.",
            "- `potentially_broken`: at least three consecutive centerline samples below 50% of that strut's own median thickness.",
            "- `broken`: compatible observed fragments separated by weak or absent TIFF material.",
            "- `missing strut`: a TIFF-inferred connection absent between two present junctions.",
            "- `missing junction`: a TIFF-inferred node site with no junction or local material.",
            "- `incomplete_fragment`: interior fragment that could not be paired.",
            "",
        ]
    )
    path.write_text("\n".join(lines))


def write_concise_summary(
    path,
    expected_struts,
    detected_struts,
    missing_junctions,
    missing_struts,
    rows,
    topology_tracks,
    max_track_gap_slices,
    include_thickness_potentially_broken,
    include_topology_potentially_broken,
):
    """Write only the primary defect counts."""
    broken_fragments = sum(row["classification"] == "broken" for row in rows)
    potentially_broken = sum(
        row["classification"] == "potentially_broken" for row in rows
    )
    topology_missing = sum(
        strut["classification"] == "missing" for strut in missing_struts
    )
    topology_potentially_broken = sum(
        strut["classification"] == "potentially_broken"
        for strut in missing_struts
    )
    deficit = (
        max(0, expected_struts - detected_struts)
        if expected_struts is not None
        else "not available"
    )
    cluster_count = len(
        {junction["cluster_id"] for junction in missing_junctions}
    )
    ranged_tracks = [
        track for track in topology_tracks if track["z_max"] > track["z_min"]
    ]
    lines = [
        "# 3D Strut Thickness and Defect Summary",
        "",
        "- JSON coordinate usage: **none**",
        "- JSON structural usage: **coordinate-free connectivity and degree priors**",
        f"- 3D anomaly tracks: **{len(topology_tracks)}**",
        f"- Multi-slice anomaly tracks: **{len(ranged_tracks)}**",
        f"- Maximum bridged tracking gap: **{max_track_gap_slices} slices**",
        f"- Expected struts: **{expected_struts if expected_struts is not None else 'not available'}**",
        f"- Detected struts: **{detected_struts}**",
        f"- Strut count deficit: **{deficit}**",
        f"- Missing junctions: **{len(missing_junctions)}**",
        f"- Missing-junction clusters: **{cluster_count}**",
        f"- Missing struts: **{topology_missing}**",
        (
            "- Topology-derived potentially broken screening: **enabled**"
            if include_topology_potentially_broken
            else "- Topology-derived potentially broken screening: **paused**"
        ),
        f"- Topology-derived potentially broken struts: **{topology_potentially_broken}**",
        f"- Broken fragment pairs: **{broken_fragments}**",
        (
            "- Thickness-derived potentially broken screening: **enabled**"
            if include_thickness_potentially_broken
            else "- Thickness-derived potentially broken screening: **paused**"
        ),
        f"- Thickness-derived potentially broken struts: **{potentially_broken}**",
        "",
    ]
    path.write_text("\n".join(lines))


def run_analysis(args):
    skeleton_path = args.skeleton_tiff or args.segmented_tiff.with_name("skeleton.tif")
    mask = tifffile.memmap(args.segmented_tiff)
    skeleton = tifffile.memmap(skeleton_path)
    if mask.shape != skeleton.shape:
        raise ValueError("segmented mask and skeleton shapes differ")
    raw = tifffile.memmap(args.raw_tiff) if args.raw_tiff else None
    if raw is not None and raw.shape != mask.shape:
        raise ValueError("raw, segmented mask, and skeleton shapes differ")
    spacing_um = tuple(
        args.voxel_spacing_um
        if args.voxel_spacing_um
        else (args.voxel_size_um,) * 3
    )
    if any(value <= 0 for value in spacing_um):
        raise ValueError("voxel spacing must be positive")
    if args.max_track_gap_slices < 0:
        raise ValueError("max track gap slices must be non-negative")
    if args.prediction_position_tolerance <= 0:
        raise ValueError("prediction position tolerance must be positive")
    if not (
        0
        <= args.potentially_broken_missing_fraction
        < args.missing_strut_missing_fraction
        <= 1
    ):
        raise ValueError(
            "missing-fraction thresholds must satisfy "
            "0 <= potentially broken < missing <= 1"
        )

    print("Stage 1/4: extracting the observed TIFF skeleton graph...")
    graph_paths = extract_paths(skeleton)
    print("Stage 2/4: measuring 3D strut thickness...")
    diameters, recentered, edt_diagnostics = thickness_at_skeleton(
        mask, skeleton, spacing_um
    )
    measured = []
    for path in graph_paths:
        measurement = measure_path(
            path,
            diameters,
            recentered,
            args.strut_thickness_percentile,
            spacing_um,
        )
        measured.append({**measurement, **path_statistics(measurement)})
    complete = [
        path
        for path in measured
        if path["start_type"] == path["end_type"] == "junction"
        and path["path_length_voxels"] >= MIN_BRANCH_LENGTH
    ]
    threshold, center, scale, method = adaptive_threshold(
        [path["low_thickness"] for path in complete]
    )
    if raw is not None:
        lows, scales = raw_normalization(raw)
        raw_cutoff = raw_material_cutoff(raw, skeleton, lows, scales)
    else:
        lows = scales = None
        raw_cutoff = 0.0
    rows = classify_paths(
        measured,
        mask,
        skeleton,
        raw,
        lows,
        scales,
        raw_cutoff,
        args.strut_thickness_percentile,
        threshold,
        center,
        scale,
        spacing_um,
        args.include_thickness_potentially_broken,
    )
    expected_structure = load_expected_structure(args.expected_json)
    expected_junctions = expected_structure["junction_count"]
    expected_total = expected_structure["strut_count"]
    valid_range = interior_slice_range(rows, mask.shape[0])
    interior_model = build_scan_interior_model(measured)
    exclude_boundary_defects(rows, interior_model)
    for row in rows:
        if (
            row["classification"] in {"potentially_broken", "broken"}
            and (row["z_min"] < valid_range[0] or row["z_max"] > valid_range[1])
        ):
            row["effective_count"] = 1
            row["classification"] = "normal"
            row["evidence"] = "boundary_transition"
            row["evidence_slices"] = ""
            row["_thin_slices"] = []
            row["_disconnected_slices"] = []
    slices = struts_by_slice(rows, mask.shape[0], valid_range)
    effective_total = sum(row["effective_count"] for row in rows)
    print("Stage 3/4: inferring interior topology defects...")
    missing_junctions, topology_missing_struts = infer_tiff_topology_defects(
        measured,
        mask,
        skeleton,
        raw,
        lows,
        scales,
        raw_cutoff,
        valid_range,
        interior_model,
        args.prediction_position_tolerance,
        args.potentially_broken_missing_fraction,
        args.missing_strut_missing_fraction,
        expected_structure,
    )
    topology_missing_struts = reportable_topology_struts(
        topology_missing_struts,
        args.include_topology_potentially_broken,
    )
    templates = _learn_connection_templates(measured)
    observed_edge_length = (
        float(np.median([np.linalg.norm(template) for template in templates]))
        if templates
        else 1.0
    )
    topology_tracks = build_topology_tracks(
        missing_junctions,
        topology_missing_struts,
        observed_edge_length,
        args.prediction_position_tolerance,
        args.max_track_gap_slices,
    )

    for track in topology_tracks:
        targets = (
            missing_junctions
            if track["anomaly_type"] == "missing_junction"
            else topology_missing_struts
        )
        key = "junction_id" if track["anomaly_type"] == "missing_junction" else "strut_id"
        for target in targets:
            if target[key] not in track["source_ids"]:
                continue
            quality = (
                track["observed_slice_count"],
                track["confidence"],
            )
            if quality <= target.get("_track_quality", (-1, -1.0)):
                continue
            if track["anomaly_type"] == "missing_junction":
                covered_slices = set(target["evidence_slices"])
            else:
                covered_slices = set(track["observed_slices"])
            z_min = min(covered_slices)
            z_max = max(covered_slices)
            target.update(
                {
                    "track_id": track["track_id"],
                    "z_min": z_min,
                    "z_max": z_max,
                    "observed_slice_count": len(covered_slices),
                    "bridged_gap_count": z_max - z_min + 1 - len(covered_slices),
                    "confidence": track["confidence"],
                    "_track_quality": quality,
                }
            )
    for junction in missing_junctions:
        junction.setdefault("track_id", "")
        junction.setdefault("z_min", junction["z"])
        junction.setdefault("z_max", junction["z"])
        junction.setdefault("observed_slice_count", 1)
        junction.setdefault("bridged_gap_count", 0)
        junction.setdefault(
            "confidence",
            1.0 - max(junction["mask_support"], junction["raw_support"]),
        )

    missing_candidates = []
    strut_tracks = [
        track
        for track in topology_tracks
        if track["anomaly_type"] in {"missing_strut", "potentially_broken_strut"}
    ]
    for rank, track in enumerate(strut_tracks, start=1):
        z, y, x = np.rint(track["point"]).astype(int)
        evidence = (
            "tiff_topology_missing_strut"
            if track["anomaly_type"] == "missing_strut"
            else "tiff_topology_potentially_broken_strut"
        )
        missing_candidates.append(
            {
                "candidate_id": rank - 1,
                "track_id": track["track_id"],
                "rank": rank,
                "evidence": evidence,
                "confidence": track["confidence"],
                "source": ";".join(str(value) for value in track["source_ids"]),
                "slice": track["representative_slice"],
                "representative_slice": track["representative_slice"],
                "z_min": track["z_min"],
                "z_max": track["z_max"],
                "observed_slice_count": track["observed_slice_count"],
                "bridged_gap_count": track["bridged_gap_count"],
                "structural_family": track["structural_family"],
                "z": int(z),
                "y": int(y),
                "x": int(x),
            }
        )
    reported_track_ids = {
        track["track_id"] for track in strut_tracks
    } | {
        junction["track_id"]
        for junction in missing_junctions
        if junction["track_id"] != ""
    }
    reported_tracks = [
        track
        for track in topology_tracks
        if track["track_id"] in reported_track_ids
    ]
    nonzero_template_z = [
        abs(float(template[0]))
        for template in templates
        if abs(float(template[0])) >= 2.0
    ]
    observed_layer_span = (
        float(np.median(nonzero_template_z))
        if nonzero_template_z
        else 40.0
    )
    visualization_defects = build_visualization_defects(
        rows, missing_junctions, topology_missing_struts
    )
    selected_visualization_slices, _visualization_assignment = (
        select_visualization_slices(
            visualization_defects,
            observed_layer_span,
        )
    )
    candidate_slices = missing_candidates_by_slice(
        missing_candidates, mask.shape[0], slices
    )
    observed_junctions = len(
        {
            node
            for path in measured
            for node, node_type in (
                (path["start_node"], path["start_type"]),
                (path["end_node"], path["end_type"]),
            )
            if node_type == "junction"
        }
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    png_output_dir = args.output_dir / "png_outputs"
    png_output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = args.output_dir / "strut_defects.csv"
    summary_path = args.output_dir / "defect_summary.md"
    box_path = png_output_dir / "thickness_box_plot.png"
    cdf_path = png_output_dir / "thickness_cdf.png"
    validation_path = png_output_dir / "broken_strut_validation.png"
    candidate_path = args.output_dir / "missing_strut_candidates.csv"
    candidate_slice_path = (
        args.output_dir / "missing_strut_candidates_by_slice.csv"
    )
    missing_junction_path = args.output_dir / "missing_junctions.csv"
    topology_strut_path = args.output_dir / "topology_strut_defects.csv"
    write_csv(csv_path, rows)
    write_missing_candidate_csv(candidate_path, missing_candidates)
    write_missing_slice_csv(candidate_slice_path, candidate_slices)
    write_missing_junction_csv(missing_junction_path, missing_junctions)
    write_topology_strut_csv(topology_strut_path, topology_missing_struts)
    values = np.asarray(
        [
            row["thickness_low_percentile_um"]
            for row in rows
            if row["effective_count"]
        ]
    )
    print("Stage 4/4: writing tables and PNG outputs...")
    plot_box(box_path, values, threshold)
    plot_cdf(cdf_path, values, threshold)
    validation = plot_validation(
        validation_path,
        rows,
        slices,
        raw,
        mask,
        lows,
        scales,
        valid_range,
    )
    gap_sheet_paths = plot_gap_contact_sheets(
        png_output_dir,
        rows,
        missing_junctions,
        topology_missing_struts,
        raw,
        mask,
        lows,
        scales,
        visualization_defects,
        selected_visualization_slices,
    )
    write_concise_summary(
        summary_path,
        expected_total,
        effective_total,
        missing_junctions,
        topology_missing_struts,
        rows,
        reported_tracks,
        args.max_track_gap_slices,
        args.include_thickness_potentially_broken,
        args.include_topology_potentially_broken,
    )
    for old_path in (
        args.output_dir / "thickness_box_plot.png",
        args.output_dir / "thickness_cdf.png",
        args.output_dir / "broken_strut_validation.png",
    ):
        if old_path.exists():
            old_path.unlink()
    for old_path in args.output_dir.glob("gap_slices_*.png"):
        old_path.unlink()
    current_gap_names = {path.name for path in gap_sheet_paths}
    for old_path in png_output_dir.glob("gap_slices_*.png"):
        if old_path.name not in current_gap_names:
            old_path.unlink()
    print(f"Saved {csv_path}")
    print(f"Saved {summary_path}")
    print(f"Saved {box_path}")
    print(f"Saved {cdf_path}")
    print(f"Saved {validation_path}")
    print(f"Saved {candidate_path}")
    print(f"Saved {candidate_slice_path}")
    print(f"Saved {missing_junction_path}")
    print(f"Saved {topology_strut_path}")
    for path in gap_sheet_paths:
        print(f"Saved {path}")


def main():
    run_analysis(build_parser().parse_args())


if __name__ == "__main__":
    main()
