from __future__ import annotations

import argparse
import csv
import itertools
import json
import math
import os
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib-cache")

import matplotlib.pyplot as plt
import numpy as np
import tifffile
from scipy import ndimage as ndi
from scipy.optimize import linear_sum_assignment
from scipy.spatial import cKDTree
from skimage.filters import threshold_otsu
from skimage.morphology import ball, binary_closing, remove_small_objects, skeletonize


EPS = 1e-12
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_JSON_PATH = PROJECT_ROOT / "data" / "missing_struts" / "octet_truss_9x9x9.json"
DEFAULT_TIFF_PATH = (
    PROJECT_ROOT
    / "data"
    / "missing_struts"
    / "tif_stacks"
    / "210127_Brian_Tran_strut_lattices_0point5dash1 1 Slices.tif"
)
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "missing_struts" / "analysis" / "registration"
DEFAULT_CT_SPACING = (0.05809, 0.05809, 0.05809)
# The nominal 9x9x9 lattice uses design-space coordinates. This converts those
# coordinates into the same physical units as DEFAULT_CT_SPACING for the Brian
# Tran 0.5% specimen family.
DEFAULT_JSON_SPACING = 2.293904943560482
DEFAULT_CELL_ARRANGEMENT = (4, 3, 2)


@dataclass(frozen=True)
class RegistrationConfig:
    json_path: Path = DEFAULT_JSON_PATH
    tif_path: Path = DEFAULT_TIFF_PATH
    output_dir: Path = DEFAULT_OUTPUT_DIR
    ct_spacing: tuple[float, float, float] = DEFAULT_CT_SPACING
    json_spacing: float = DEFAULT_JSON_SPACING
    cells: tuple[int, int, int] | None = DEFAULT_CELL_ARRANGEMENT
    cell_start: tuple[int, int, int] | None = None
    threshold: float | None = None
    material: str = "bright"
    downsample: int = 1
    min_component: int = 1000
    closing_radius: int = 1
    junction_method: str = "hybrid"
    branch_degree: int = 4
    junction_cluster_radius: float = 4.0
    distance_peak_min: float = 1.5
    distance_peak_window: int = 7
    max_candidates: int = 5000
    gate: float | None = None
    trim_fraction: float = 0.75
    max_iterations: int = 80
    tolerance: float = 1e-5
    max_blocks: int = 0


@dataclass(frozen=True)
class TemplateBlock:
    points: np.ndarray
    global_indices: np.ndarray
    source_ids: list[list[int]]
    cell_start: tuple[int, int, int]
    cell_shape: tuple[int, int, int]


@dataclass(frozen=True)
class RegistrationResult:
    rotation: np.ndarray
    translation: np.ndarray
    template: TemplateBlock
    matched_template_idx: np.ndarray
    matched_ct_idx: np.ndarray
    residuals: np.ndarray
    score: float
    iterations: int


@dataclass(frozen=True)
class RegistrationArtifacts:
    nominal_summary: Path
    segmentation_mask: Path
    ct_junction_candidates_csv: Path
    ct_junction_candidates_npy: Path
    registration_metrics: Path
    junction_correspondences: Path
    registered_json_junctions: Path
    registration_3d_overlay: Path
    registration_mip_overlays: Path
    registration_error_histogram: Path
    registered_lattice: Path


def build_registration_artifacts(output_dir: Path) -> RegistrationArtifacts:
    return RegistrationArtifacts(
        nominal_summary=output_dir / "nominal_summary.json",
        segmentation_mask=output_dir / "segmentation_mask.tif",
        ct_junction_candidates_csv=output_dir / "ct_junction_candidates.csv",
        ct_junction_candidates_npy=output_dir / "ct_junction_candidates.npy",
        registration_metrics=output_dir / "registration_metrics.json",
        junction_correspondences=output_dir / "junction_correspondences.csv",
        registered_json_junctions=output_dir / "registered_json_junctions.npy",
        registration_3d_overlay=output_dir / "registration_3d_overlay.png",
        registration_mip_overlays=output_dir / "registration_mip_overlays.png",
        registration_error_histogram=output_dir / "registration_error_histogram.png",
        registered_lattice=output_dir / "registered_lattice.json",
    )


def parse_cli_args(argv: Sequence[str] | None = None) -> RegistrationConfig:
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description="Register the nominal missing-struts lattice JSON to a CT TIFF stack.",
    )
    parser.add_argument("--json", dest="json_path", type=Path, default=DEFAULT_JSON_PATH)
    parser.add_argument("--tif", dest="tif_path", type=Path, default=DEFAULT_TIFF_PATH)
    parser.add_argument("--output", dest="output_dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--ct-spacing",
        nargs=3,
        type=float,
        metavar=("SX", "SY", "SZ"),
        default=DEFAULT_CT_SPACING,
        help="CT voxel spacing in physical units, ordered x y z",
    )
    parser.add_argument(
        "--json-spacing",
        type=float,
        default=DEFAULT_JSON_SPACING,
        help="Multiplier that converts nominal JSON positions into CT physical units",
    )
    parser.add_argument(
        "--cells",
        nargs=3,
        type=int,
        metavar=("NX", "NY", "NZ"),
        default=DEFAULT_CELL_ARRANGEMENT,
        help="Known unit-cell arrangement present in the scan; omit to search the full JSON lattice",
    )
    parser.add_argument("--cell-start", nargs=3, type=int, metavar=("IX", "IY", "IZ"))
    parser.add_argument("--threshold", type=float)
    parser.add_argument("--material", choices=("bright", "dark"), default="bright")
    parser.add_argument("--downsample", type=int, default=1)
    parser.add_argument("--min-component", type=int, default=1000)
    parser.add_argument("--closing-radius", type=int, default=1)
    parser.add_argument("--junction-method", choices=("skeleton", "distance", "hybrid"), default="hybrid")
    parser.add_argument("--branch-degree", type=int, default=4)
    parser.add_argument("--junction-cluster-radius", type=float, default=4.0)
    parser.add_argument("--distance-peak-min", type=float, default=1.5)
    parser.add_argument("--distance-peak-window", type=int, default=7)
    parser.add_argument("--max-candidates", type=int, default=5000)
    parser.add_argument("--gate", type=float)
    parser.add_argument("--trim-fraction", type=float, default=0.75)
    parser.add_argument("--max-iterations", type=int, default=80)
    parser.add_argument("--tolerance", type=float, default=1e-5)
    parser.add_argument("--max-blocks", type=int, default=0)
    args = parser.parse_args(argv)
    return RegistrationConfig(
        json_path=args.json_path,
        tif_path=args.tif_path,
        output_dir=args.output_dir,
        ct_spacing=tuple(float(x) for x in args.ct_spacing),
        json_spacing=float(args.json_spacing),
        cells=tuple(int(x) for x in args.cells) if args.cells else None,
        cell_start=tuple(int(x) for x in args.cell_start) if args.cell_start else None,
        threshold=args.threshold,
        material=args.material,
        downsample=int(args.downsample),
        min_component=int(args.min_component),
        closing_radius=int(args.closing_radius),
        junction_method=args.junction_method,
        branch_degree=int(args.branch_degree),
        junction_cluster_radius=float(args.junction_cluster_radius),
        distance_peak_min=float(args.distance_peak_min),
        distance_peak_window=int(args.distance_peak_window),
        max_candidates=int(args.max_candidates),
        gate=args.gate,
        trim_fraction=float(args.trim_fraction),
        max_iterations=int(args.max_iterations),
        tolerance=float(args.tolerance),
        max_blocks=int(args.max_blocks),
    )


def _is_lfs_pointer(path: Path) -> bool:
    try:
        with path.open("rb") as handle:
            return handle.read(64).startswith(b"version https://git-lfs.github.com/spec/v1")
    except OSError:
        return False


def _validate_existing_path(path: Path, label: str) -> None:
    if not path.exists():
        raise FileNotFoundError(f"{label} does not exist: {path}")
    if path.is_dir():
        raise IsADirectoryError(f"{label} must be a file, not a directory: {path}")
    if _is_lfs_pointer(path):
        raise ValueError(
            f"{label} is a Git LFS pointer instead of local payload data: {path}. "
            "Fetch the real artifact before running registration."
        )


def load_json(path: Path) -> dict[str, Any]:
    _validate_existing_path(path, "Nominal lattice JSON")
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    for key in ("junctions", "struts", "unit_cells"):
        if key not in data or not isinstance(data[key], list):
            raise ValueError(f"JSON must contain list field {key!r}")
    return data


def nominal_summary(data: dict[str, Any], json_spacing: float) -> dict[str, Any]:
    positions = np.asarray([junction["position"] for junction in data["junctions"]], dtype=float) * json_spacing
    cell_idx = np.asarray([cell["indices"] for cell in data["unit_cells"]], dtype=int)
    unique_cells = [np.unique(cell_idx[:, axis]).tolist() for axis in range(3)]

    id_to_pos = {
        int(junction["id"]): np.asarray(junction["position"], dtype=float) * json_spacing
        for junction in data["junctions"]
    }
    lengths = []
    degrees: dict[int, int] = {}
    for strut in data["struts"]:
        junction0 = int(strut["junction0"])
        junction1 = int(strut["junction1"])
        if junction0 in id_to_pos and junction1 in id_to_pos:
            lengths.append(float(np.linalg.norm(id_to_pos[junction0] - id_to_pos[junction1])))
            degrees[junction0] = degrees.get(junction0, 0) + 1
            degrees[junction1] = degrees.get(junction1, 0) + 1

    degree_distribution = {}
    if degrees:
        degree_values = list(degrees.values())
        unique, counts = np.unique(degree_values, return_counts=True)
        degree_distribution = {str(int(key)): int(value) for key, value in zip(unique, counts)}

    return {
        "junction_records": len(data["junctions"]),
        "strut_records": len(data["struts"]),
        "unit_cells": len(data["unit_cells"]),
        "cell_index_values": unique_cells,
        "cell_shape": [len(values) for values in unique_cells],
        "json_bbox_min": positions.min(axis=0).tolist(),
        "json_bbox_max": positions.max(axis=0).tolist(),
        "strut_length_median": float(np.median(lengths)) if lengths else None,
        "strut_length_min": float(np.min(lengths)) if lengths else None,
        "strut_length_max": float(np.max(lengths)) if lengths else None,
        "junction_degree_distribution": degree_distribution,
    }


def build_cell_to_junctions(
    data: dict[str, Any],
) -> tuple[dict[tuple[int, int, int], set[int]], dict[int, dict[str, Any]]]:
    junction_by_id = {int(junction["id"]): junction for junction in data["junctions"]}
    strut_by_id = {int(strut["id"]): strut for strut in data["struts"]}
    mapping: dict[tuple[int, int, int], set[int]] = {}
    for cell in data["unit_cells"]:
        index = tuple(int(value) for value in cell["indices"])
        ids: set[int] = set()
        for strut_id in cell.get("struts", []):
            strut = strut_by_id.get(int(strut_id))
            if strut is not None:
                ids.add(int(strut["junction0"]))
                ids.add(int(strut["junction1"]))
        mapping[index] = ids
    return mapping, junction_by_id


def dedupe_structural_points(
    records: Iterable[tuple[np.ndarray, np.ndarray, int]],
    tolerance: float = 1e-6,
) -> tuple[np.ndarray, np.ndarray, list[list[int]]]:
    buckets: dict[tuple[int, int, int], list[tuple[np.ndarray, np.ndarray, int]]] = {}
    for position, global_idx, junction_id in records:
        key = tuple(np.rint(global_idx * 2.0).astype(int).tolist())
        buckets.setdefault(key, []).append((position, global_idx, junction_id))

    points = []
    indices = []
    source_ids = []
    for key in sorted(buckets):
        group = buckets[key]
        group_points = np.vstack([item[0] for item in group])
        group_indices = np.vstack([item[1] for item in group])
        point = np.mean(group_points, axis=0)
        points.append(point)
        indices.append(np.mean(group_indices, axis=0))
        source_ids.append([item[2] for item in group])
        if np.max(np.linalg.norm(group_points - point, axis=1)) > tolerance * max(1.0, np.linalg.norm(point)):
            pass
    return np.asarray(points), np.asarray(indices), source_ids


def make_template_block(
    cell_to_junctions: dict[tuple[int, int, int], set[int]],
    junction_by_id: dict[int, dict[str, Any]],
    start: tuple[int, int, int],
    shape: tuple[int, int, int],
    json_spacing: float,
) -> TemplateBlock:
    selected: list[tuple[np.ndarray, np.ndarray, int]] = []
    start_x, start_y, start_z = start
    cells_x, cells_y, cells_z = shape
    for ix in range(start_x, start_x + cells_x):
        for iy in range(start_y, start_y + cells_y):
            for iz in range(start_z, start_z + cells_z):
                for junction_id in cell_to_junctions.get((ix, iy, iz), set()):
                    junction = junction_by_id[junction_id]
                    local = np.asarray(junction["indices"], dtype=float)
                    global_idx = np.asarray((ix, iy, iz), dtype=float) + local
                    position = np.asarray(junction["position"], dtype=float) * json_spacing
                    selected.append((position, global_idx, junction_id))
    if not selected:
        raise ValueError(f"No junctions found for cell block start={start}, shape={shape}")
    points, indices, source_ids = dedupe_structural_points(selected)
    return TemplateBlock(points, indices, source_ids, start, shape)


def valid_blocks(
    cell_to_junctions: dict[tuple[int, int, int], set[int]],
    requested_shape: tuple[int, int, int] | None,
    fixed_start: tuple[int, int, int] | None,
    max_blocks: int,
) -> list[tuple[tuple[int, int, int], tuple[int, int, int]]]:
    cells = np.asarray(list(cell_to_junctions.keys()), dtype=int)
    mins, maxs = cells.min(axis=0), cells.max(axis=0)
    full_shape = tuple((maxs - mins + 1).tolist())
    shape = requested_shape or full_shape

    if fixed_start is not None:
        starts = [fixed_start]
    else:
        ranges = []
        for axis in range(3):
            last = int(maxs[axis] - shape[axis] + 1)
            first = int(mins[axis])
            if last < first:
                raise ValueError(f"Requested cell shape {shape} exceeds JSON cell extent {full_shape}")
            ranges.append(range(first, last + 1))
        starts = list(itertools.product(*ranges))

    blocks = [(tuple(map(int, start)), tuple(map(int, shape))) for start in starts]
    if max_blocks > 0:
        blocks = blocks[:max_blocks]
    return blocks


def load_ct(path: Path, downsample: int) -> np.ndarray:
    _validate_existing_path(path, "CT TIFF stack")
    try:
        volume = tifffile.imread(path)
    except Exception as exc:
        raise ValueError(f"Could not read CT TIFF stack at {path}: {exc}") from exc
    if volume.ndim != 3:
        raise ValueError(f"Expected a 3D TIFF stack; got shape {volume.shape}")
    if 0 in volume.shape:
        raise ValueError(f"CT TIFF stack is malformed or incomplete; got shape {volume.shape}")
    if downsample < 1:
        raise ValueError("--downsample must be >= 1")
    if downsample > 1:
        volume = volume[::downsample, ::downsample, ::downsample]
    return np.asarray(volume)


def sampled_otsu(volume: np.ndarray, max_samples: int = 2_000_000) -> float:
    flat = volume.ravel()
    if flat.size > max_samples:
        step = int(math.ceil(flat.size / max_samples))
        flat = flat[::step]
    return float(threshold_otsu(flat))


def segment_ct(
    volume: np.ndarray,
    threshold: float | None,
    material: str,
    min_component: int,
    closing_radius: int,
) -> tuple[np.ndarray, float]:
    used_threshold = sampled_otsu(volume) if threshold is None else float(threshold)
    mask = volume >= used_threshold if material == "bright" else volume <= used_threshold
    mask = remove_small_objects(mask.astype(bool), min_size=max(1, min_component), connectivity=3)
    if closing_radius > 0:
        mask = binary_closing(mask, footprint=ball(closing_radius))
    return np.asarray(mask, dtype=bool), used_threshold


def cluster_points(points_zyx: np.ndarray, weights: np.ndarray, radius: float) -> tuple[np.ndarray, np.ndarray]:
    if len(points_zyx) == 0:
        return np.empty((0, 3)), np.empty((0,))
    tree = cKDTree(points_zyx)
    visited = np.zeros(len(points_zyx), dtype=bool)
    centers = []
    strengths = []
    for seed in np.argsort(weights)[::-1]:
        if visited[seed]:
            continue
        ids = np.asarray(tree.query_ball_point(points_zyx[seed], r=radius), dtype=int)
        ids = ids[~visited[ids]]
        if len(ids) == 0:
            continue
        local_weights = np.maximum(weights[ids], EPS)
        centers.append(np.average(points_zyx[ids], axis=0, weights=local_weights))
        strengths.append(float(np.sum(local_weights)))
        visited[ids] = True
    return np.asarray(centers), np.asarray(strengths)


def skeleton_candidates(mask: np.ndarray, branch_degree: int) -> tuple[np.ndarray, np.ndarray]:
    skeleton = skeletonize(mask, method="lee")
    kernel = np.ones((3, 3, 3), dtype=np.uint8)
    neighbor_count = ndi.convolve(skeleton.astype(np.uint8), kernel, mode="constant", cval=0) - skeleton.astype(
        np.uint8
    )
    branch = skeleton & (neighbor_count >= branch_degree)
    points = np.argwhere(branch)
    strengths = neighbor_count[branch].astype(float)
    return points.astype(float), strengths


def distance_candidates(mask: np.ndarray, min_radius: float, window: int) -> tuple[np.ndarray, np.ndarray]:
    distance = ndi.distance_transform_edt(mask)
    window = max(3, int(window) | 1)
    maxima = distance == ndi.maximum_filter(distance, size=window, mode="constant")
    maxima &= distance >= min_radius
    points = np.argwhere(maxima)
    strengths = distance[maxima].astype(float)
    return points.astype(float), strengths


def detect_junctions(
    mask: np.ndarray,
    method: str,
    branch_degree: int,
    cluster_radius: float,
    peak_min: float,
    peak_window: int,
    max_candidates: int,
) -> tuple[np.ndarray, np.ndarray]:
    point_sets = []
    weight_sets = []
    if method in ("skeleton", "hybrid"):
        points, weights = skeleton_candidates(mask, branch_degree)
        point_sets.append(points)
        weight_sets.append(weights)
    if method in ("distance", "hybrid"):
        points, weights = distance_candidates(mask, peak_min, peak_window)
        point_sets.append(points)
        weight_sets.append(weights)
    if not point_sets or sum(len(points) for points in point_sets) == 0:
        raise RuntimeError("No CT junction candidates were detected. Adjust threshold or detector settings.")

    points = np.vstack(point_sets)
    weights = np.concatenate(weight_sets)
    centers, strengths = cluster_points(points, weights, cluster_radius)
    if len(centers) > max_candidates:
        keep = np.argsort(strengths)[::-1][:max_candidates]
        centers = centers[keep]
        strengths = strengths[keep]
    return centers, strengths


def zyx_to_physical_xyz(points_zyx: np.ndarray, spacing_xyz: Sequence[float], downsample: int) -> np.ndarray:
    xyz_voxels = points_zyx[:, ::-1] * float(downsample)
    return xyz_voxels * np.asarray(spacing_xyz, dtype=float)


def physical_xyz_to_voxel_xyz(points_xyz: np.ndarray, spacing_xyz: Sequence[float]) -> np.ndarray:
    return points_xyz / np.asarray(spacing_xyz, dtype=float)


def nearest_spacing(points: np.ndarray) -> float:
    tree = cKDTree(points)
    distances, _ = tree.query(points, k=2)
    values = distances[:, 1]
    values = values[np.isfinite(values) & (values > EPS)]
    return float(np.median(values))


def pca_frame(points: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    center = np.mean(points, axis=0)
    centered = points - center
    covariance = centered.T @ centered / max(1, len(points) - 1)
    eigenvalues, eigenvectors = np.linalg.eigh(covariance)
    order = np.argsort(eigenvalues)[::-1]
    eigenvalues = eigenvalues[order]
    eigenvectors = eigenvectors[:, order]
    if np.linalg.det(eigenvectors) < 0:
        eigenvectors[:, -1] *= -1
    return center, eigenvectors, eigenvalues


def proper_signed_permutations() -> list[np.ndarray]:
    matrices: list[np.ndarray] = []
    for permutation in itertools.permutations(range(3)):
        basis = np.eye(3)[:, permutation]
        for signs in itertools.product((-1.0, 1.0), repeat=3):
            matrix = basis @ np.diag(signs)
            if np.linalg.det(matrix) > 0.5:
                matrices.append(matrix)
    return matrices


def transform_points(points: np.ndarray, rotation: np.ndarray, translation: np.ndarray) -> np.ndarray:
    return points @ rotation.T + translation


def kabsch(
    source: np.ndarray,
    target: np.ndarray,
    weights: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    if len(source) < 3:
        raise ValueError("At least 3 correspondences are required")
    if weights is None:
        weights = np.ones(len(source), dtype=float)
    weights = np.asarray(weights, dtype=float)
    weights /= np.sum(weights)
    source_center = np.sum(source * weights[:, None], axis=0)
    target_center = np.sum(target * weights[:, None], axis=0)
    centered_source = source - source_center
    centered_target = target - target_center
    covariance = (centered_source * weights[:, None]).T @ centered_target
    u_matrix, _, v_transpose = np.linalg.svd(covariance)
    rotation = v_transpose.T @ u_matrix.T
    if np.linalg.det(rotation) < 0:
        v_transpose[-1, :] *= -1
        rotation = v_transpose.T @ u_matrix.T
    translation = target_center - rotation @ source_center
    return rotation, translation


def robust_nn_score(
    transformed: np.ndarray,
    ct_points: np.ndarray,
    gate: float,
    trim_fraction: float,
) -> tuple[float, float, float]:
    distances, _ = cKDTree(ct_points).query(transformed, k=1)
    inside = distances <= gate
    coverage = float(np.mean(inside))
    trim_count = max(3, int(len(distances) * trim_fraction))
    trimmed = np.partition(distances, min(trim_count - 1, len(distances) - 1))[:trim_count]
    rmse = float(np.sqrt(np.mean(trimmed**2)))
    score = rmse + gate * (1.0 - coverage)
    return score, coverage, rmse


def pca_initializations(template: np.ndarray, ct_points: np.ndarray) -> Iterable[tuple[np.ndarray, np.ndarray]]:
    source_center, source_frame, _ = pca_frame(template)
    ct_center, ct_frame, _ = pca_frame(ct_points)
    for permutation in proper_signed_permutations():
        rotation = ct_frame @ permutation @ source_frame.T
        if np.linalg.det(rotation) < 0:
            continue
        translation = ct_center - rotation @ source_center
        yield rotation, translation


def one_to_one_assignment(
    transformed_template: np.ndarray,
    ct_points: np.ndarray,
    gate: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    tree = cKDTree(ct_points)
    neighborhoods = tree.query_ball_point(transformed_template, r=gate)
    template_ids = [index for index, neighbors in enumerate(neighborhoods) if neighbors]
    if not template_ids:
        return np.empty(0, dtype=int), np.empty(0, dtype=int), np.empty(0, dtype=float)
    ct_ids = sorted({neighbor for index in template_ids for neighbor in neighborhoods[index]})
    ct_lookup = {neighbor: offset for offset, neighbor in enumerate(ct_ids)}
    cost = np.full((len(template_ids), len(ct_ids) + len(template_ids)), gate * 1.05, dtype=float)
    for row, template_idx in enumerate(template_ids):
        for ct_idx in neighborhoods[template_idx]:
            cost[row, ct_lookup[ct_idx]] = np.linalg.norm(transformed_template[template_idx] - ct_points[ct_idx])
    rows, cols = linear_sum_assignment(cost)
    matched_template = []
    matched_ct = []
    distances = []
    for row, col in zip(rows, cols):
        if col < len(ct_ids) and cost[row, col] <= gate:
            matched_template.append(template_ids[row])
            matched_ct.append(ct_ids[col])
            distances.append(cost[row, col])
    return np.asarray(matched_template, dtype=int), np.asarray(matched_ct, dtype=int), np.asarray(distances, dtype=float)


def refine_icp(
    template: np.ndarray,
    ct_points: np.ndarray,
    initial_rotation: np.ndarray,
    initial_translation: np.ndarray,
    gate: float,
    trim_fraction: float,
    max_iterations: int,
    tolerance: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, int]:
    rotation = initial_rotation.copy()
    translation = initial_translation.copy()
    previous_rmse = np.inf
    last = (np.empty(0, dtype=int), np.empty(0, dtype=int), np.empty(0, dtype=float))
    iteration = 0
    for iteration in range(1, max_iterations + 1):
        moved = transform_points(template, rotation, translation)
        template_ids, ct_ids, distances = one_to_one_assignment(moved, ct_points, gate)
        if len(template_ids) < 3:
            break
        keep_count = max(3, int(math.ceil(len(distances) * trim_fraction)))
        keep = np.argsort(distances)[:keep_count]
        fit_template_ids = template_ids[keep]
        fit_ct_ids = ct_ids[keep]
        rotation, translation = kabsch(template[fit_template_ids], ct_points[fit_ct_ids])
        rmse = float(np.sqrt(np.mean(distances[keep] ** 2)))
        last = (template_ids, ct_ids, distances)
        if abs(previous_rmse - rmse) < tolerance:
            return rotation, translation, template_ids, ct_ids, distances, iteration
        previous_rmse = rmse
    return rotation, translation, last[0], last[1], last[2], iteration


def search_registration(
    data: dict[str, Any],
    ct_points: np.ndarray,
    json_spacing: float,
    block_specs: list[tuple[tuple[int, int, int], tuple[int, int, int]]],
    gate: float | None,
    trim_fraction: float,
    max_iterations: int,
    tolerance: float,
) -> RegistrationResult:
    cell_map, junctions = build_cell_to_junctions(data)
    best: RegistrationResult | None = None

    for block_index, (start, shape) in enumerate(block_specs, start=1):
        template = make_template_block(cell_map, junctions, start, shape, json_spacing)
        nominal_nn = nearest_spacing(template.points)
        local_gate = gate if gate is not None else 0.35 * nominal_nn

        for initial_rotation, initial_translation in pca_initializations(template.points, ct_points):
            _, coverage, _ = robust_nn_score(
                transform_points(template.points, initial_rotation, initial_translation),
                ct_points,
                local_gate * 2.0,
                trim_fraction,
            )
            if coverage < 0.10:
                continue
            rotation, translation, template_ids, ct_ids, distances, iterations = refine_icp(
                template.points,
                ct_points,
                initial_rotation,
                initial_translation,
                gate=local_gate * 2.0,
                trim_fraction=trim_fraction,
                max_iterations=max_iterations,
                tolerance=tolerance,
            )
            if len(distances) < 3:
                continue
            moved = transform_points(template.points, rotation, translation)
            template_ids, ct_ids, distances = one_to_one_assignment(moved, ct_points, local_gate)
            if len(distances) < 3:
                continue
            coverage = len(distances) / len(template.points)
            rmse = float(np.sqrt(np.mean(distances**2)))
            score = rmse + local_gate * (1.0 - coverage)
            candidate = RegistrationResult(
                rotation=rotation,
                translation=translation,
                template=template,
                matched_template_idx=template_ids,
                matched_ct_idx=ct_ids,
                residuals=distances,
                score=score,
                iterations=iterations,
            )
            if best is None or candidate.score < best.score:
                best = candidate

        print(f"Searched block {block_index}/{len(block_specs)} start={start} shape={shape}", flush=True)

    if best is None:
        raise RuntimeError(
            "Registration failed: no hypothesis produced at least 3 gated correspondences. "
            "Check units, cell dimensions, segmentation, and --gate."
        )
    return best


def save_csv_points(path: Path, points: np.ndarray, strengths: np.ndarray | None = None) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        header = ["id", "x", "y", "z"] + (["strength"] if strengths is not None else [])
        writer.writerow(header)
        for index, point in enumerate(points):
            row = [index, *map(float, point)]
            if strengths is not None:
                row.append(float(strengths[index]))
            writer.writerow(row)


def save_matches(path: Path, result: RegistrationResult, ct_points: np.ndarray) -> None:
    moved = transform_points(result.template.points, result.rotation, result.translation)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "template_index",
                "ct_index",
                "grid_i",
                "grid_j",
                "grid_k",
                "json_x",
                "json_y",
                "json_z",
                "registered_x",
                "registered_y",
                "registered_z",
                "ct_x",
                "ct_y",
                "ct_z",
                "error",
            ]
        )
        for template_idx, ct_idx, distance in zip(
            result.matched_template_idx, result.matched_ct_idx, result.residuals
        ):
            writer.writerow(
                [
                    int(template_idx),
                    int(ct_idx),
                    *result.template.global_indices[template_idx].tolist(),
                    *result.template.points[template_idx].tolist(),
                    *moved[template_idx].tolist(),
                    *ct_points[ct_idx].tolist(),
                    float(distance),
                ]
            )


def plot_overlay(path: Path, result: RegistrationResult, ct_points: np.ndarray) -> None:
    moved = transform_points(result.template.points, result.rotation, result.translation)
    figure = plt.figure(figsize=(10, 8))
    axis = figure.add_subplot(111, projection="3d")
    axis.scatter(ct_points[:, 0], ct_points[:, 1], ct_points[:, 2], s=5, alpha=0.25, label="CT candidates")
    axis.scatter(moved[:, 0], moved[:, 1], moved[:, 2], s=8, alpha=0.55, label="Registered JSON")
    for template_idx, ct_idx in zip(result.matched_template_idx, result.matched_ct_idx):
        start = moved[template_idx]
        end = ct_points[ct_idx]
        axis.plot([start[0], end[0]], [start[1], end[1]], [start[2], end[2]], linewidth=0.5, alpha=0.4)
    axis.set_xlabel("x")
    axis.set_ylabel("y")
    axis.set_zlabel("z")
    axis.set_title("Registered JSON junctions and CT candidates")
    axis.legend()
    figure.tight_layout()
    figure.savefig(path, dpi=180)
    plt.close(figure)


def plot_errors(path: Path, residuals: np.ndarray) -> None:
    figure, axis = plt.subplots(figsize=(8, 5))
    axis.hist(residuals, bins=min(50, max(10, int(np.sqrt(len(residuals))))))
    axis.set_xlabel("Junction correspondence error")
    axis.set_ylabel("Count")
    axis.set_title("Registration error distribution")
    figure.tight_layout()
    figure.savefig(path, dpi=180)
    plt.close(figure)


def plot_mip_overlays(
    path: Path,
    volume: np.ndarray,
    result: RegistrationResult,
    spacing_xyz: Sequence[float],
    downsample: int,
) -> None:
    moved = transform_points(result.template.points, result.rotation, result.translation)
    spacing = np.asarray(spacing_xyz, dtype=float) * downsample
    voxels_xyz = moved / spacing
    figure, axes = plt.subplots(1, 3, figsize=(18, 6))
    axes[0].imshow(np.max(volume, axis=0), cmap="gray", origin="lower")
    axes[0].scatter(voxels_xyz[:, 0], voxels_xyz[:, 1], s=5, facecolors="none", edgecolors="r")
    axes[0].set_title("Axial MIP (x-y)")
    axes[1].imshow(np.max(volume, axis=1), cmap="gray", origin="lower")
    axes[1].scatter(voxels_xyz[:, 0], voxels_xyz[:, 2], s=5, facecolors="none", edgecolors="r")
    axes[1].set_title("Coronal MIP (x-z)")
    axes[2].imshow(np.max(volume, axis=2), cmap="gray", origin="lower")
    axes[2].scatter(voxels_xyz[:, 1], voxels_xyz[:, 2], s=5, facecolors="none", edgecolors="r")
    axes[2].set_title("Sagittal MIP (y-z)")
    for axis in axes:
        axis.set_aspect("equal")
    figure.tight_layout()
    figure.savefig(path, dpi=180)
    plt.close(figure)


def build_registered_lattice_json(
    data: dict[str, Any],
    rotation: np.ndarray,
    translation: np.ndarray,
    json_spacing: float,
    ct_spacing: Sequence[float],
) -> dict[str, Any]:
    registered = json.loads(json.dumps(data))
    physical_positions = (
        np.asarray([junction["position"] for junction in registered["junctions"]], dtype=float) * json_spacing
    )
    moved_physical = transform_points(physical_positions, rotation, translation)
    moved_voxel = physical_xyz_to_voxel_xyz(moved_physical, ct_spacing)
    for junction, moved in zip(registered["junctions"], moved_voxel):
        junction["position"] = [float(value) for value in moved]
    registered["registration_metadata"] = {
        "coordinate_space": "ct_voxel_xyz",
        "rigid_only": True,
    }
    return registered


def run_registration_workflow(config: RegistrationConfig) -> dict[str, Any]:
    output_dir = config.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    artifacts = build_registration_artifacts(output_dir)

    print("[1/7] Loading and inspecting nominal JSON...")
    data = load_json(config.json_path)
    summary = nominal_summary(data, config.json_spacing)
    artifacts.nominal_summary.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    cell_map, _ = build_cell_to_junctions(data)
    block_specs = valid_blocks(cell_map, config.cells, config.cell_start, config.max_blocks)
    print(f"Nominal lattice has {summary['unit_cells']} cell records; searching {len(block_specs)} candidate block(s).")

    print("[2/7] Loading and segmenting CT...")
    volume = load_ct(config.tif_path, config.downsample)
    mask, used_threshold = segment_ct(
        volume,
        config.threshold,
        config.material,
        config.min_component,
        config.closing_radius,
    )
    tifffile.imwrite(artifacts.segmentation_mask, mask.astype(np.uint8) * np.uint8(255), photometric="minisblack")

    print("[2/7] Detecting CT junction candidates...")
    centers_zyx, strengths = detect_junctions(
        mask,
        config.junction_method,
        config.branch_degree,
        config.junction_cluster_radius,
        config.distance_peak_min,
        config.distance_peak_window,
        config.max_candidates,
    )
    ct_points_physical = zyx_to_physical_xyz(centers_zyx, config.ct_spacing, config.downsample)
    save_csv_points(artifacts.ct_junction_candidates_csv, ct_points_physical, strengths)
    np.save(artifacts.ct_junction_candidates_npy, ct_points_physical)
    print(f"Detected {len(ct_points_physical)} CT junction candidates.")

    print("[3-6/7] Searching structural block, tilt, correspondences, and rigid transform...")
    result = search_registration(
        data=data,
        ct_points=ct_points_physical,
        json_spacing=config.json_spacing,
        block_specs=block_specs,
        gate=config.gate,
        trim_fraction=config.trim_fraction,
        max_iterations=config.max_iterations,
        tolerance=config.tolerance,
    )

    print("[7/7] Writing registration metrics and visual checks...")
    moved = transform_points(result.template.points, result.rotation, result.translation)
    nominal_nn = nearest_spacing(result.template.points)
    residuals = result.residuals
    metrics = {
        "json_path": str(config.json_path),
        "tif_path": str(config.tif_path),
        "output_dir": str(output_dir),
        "ct_spacing_xyz": list(config.ct_spacing),
        "json_spacing": float(config.json_spacing),
        "cells": list(config.cells) if config.cells else None,
        "cell_start_override": list(config.cell_start) if config.cell_start else None,
        "threshold_used": used_threshold,
        "material": config.material,
        "ct_volume_shape_zyx_after_downsampling": list(volume.shape),
        "downsample": config.downsample,
        "ct_junction_candidates": int(len(ct_points_physical)),
        "selected_cell_start": list(result.template.cell_start),
        "selected_cell_shape": list(result.template.cell_shape),
        "template_unique_junctions": int(len(result.template.points)),
        "matched_junctions": int(len(residuals)),
        "template_match_fraction": float(len(residuals) / len(result.template.points)),
        "ct_candidate_use_fraction": float(len(residuals) / len(ct_points_physical)),
        "rmse": float(np.sqrt(np.mean(residuals**2))),
        "median_error": float(np.median(residuals)),
        "mean_error": float(np.mean(residuals)),
        "max_error": float(np.max(residuals)),
        "nominal_nearest_junction_spacing": nominal_nn,
        "normalized_median_error": float(np.median(residuals) / nominal_nn),
        "normalized_rmse": float(np.sqrt(np.mean(residuals**2)) / nominal_nn),
        "score": float(result.score),
        "icp_iterations": int(result.iterations),
        "rotation": result.rotation.tolist(),
        "translation": result.translation.tolist(),
        "homogeneous_transform": np.vstack(
            [np.column_stack([result.rotation, result.translation]), np.array([0.0, 0.0, 0.0, 1.0])]
        ).tolist(),
        "selected_cell_block": {
            "start": list(result.template.cell_start),
            "shape": list(result.template.cell_shape),
        },
        "registered_lattice_coordinate_space": "ct_voxel_xyz",
    }
    artifacts.registration_metrics.write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    np.save(artifacts.registered_json_junctions, moved)
    save_matches(artifacts.junction_correspondences, result, ct_points_physical)
    plot_overlay(artifacts.registration_3d_overlay, result, ct_points_physical)
    plot_errors(artifacts.registration_error_histogram, residuals)
    plot_mip_overlays(
        artifacts.registration_mip_overlays,
        volume,
        result,
        config.ct_spacing,
        config.downsample,
    )
    registered_lattice = build_registered_lattice_json(
        data,
        result.rotation,
        result.translation,
        config.json_spacing,
        config.ct_spacing,
    )
    registered_lattice["registration_metadata"]["source_json"] = str(config.json_path)
    registered_lattice["registration_metadata"]["ct_tif"] = str(config.tif_path)
    registered_lattice["registration_metadata"]["ct_spacing_xyz"] = list(config.ct_spacing)
    registered_lattice["registration_metadata"]["json_spacing"] = float(config.json_spacing)
    artifacts.registered_lattice.write_text(json.dumps(registered_lattice, indent=2), encoding="utf-8")

    return {
        "status": "passed",
        "artifacts": {key: str(value) for key, value in asdict(artifacts).items()},
        "metrics": metrics,
    }


def cli_main(argv: Sequence[str] | None = None) -> int:
    config = parse_cli_args(argv)
    result = run_registration_workflow(config)
    print(json.dumps(result["metrics"], indent=2))
    print(f"Results written to: {config.output_dir.resolve()}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(cli_main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
