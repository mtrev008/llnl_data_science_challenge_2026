"""Calculate JSON-guided material-presence density for expected lattice struts.

The registered JSON supplies ideal junctions, struts, and unit-cell membership.
The raw CT and segmented mask supply measured evidence. Each expected shaft is
sampled with perpendicular cross-sectional disks, producing a dimensionless
0-1 density score plus missing, broken, low-density, uncertain, or present
classification.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Sequence

import numpy as np
import tifffile


DEFAULT_VOXEL_SIZE_UM = 58.1
DEFAULT_TARGET_UM = 350.0
DEFAULT_SEARCH_RADIUS_VOXELS = 4
DEFAULT_MASK_WEIGHT = 0.30
DEFAULT_RAW_WEIGHT = 0.30
DEFAULT_THICKNESS_WEIGHT = 0.25
DEFAULT_CONTINUITY_WEIGHT = 0.15
DEFAULT_UNCERTAINTY_MARGIN = 0.05
DEFAULT_SIGNAL_DISAGREEMENT = 0.25
DEFAULT_RAW_SUPPORT_THRESHOLD = 0.50
TIFF_SUFFIXES = {".tif", ".tiff"}

STRUT_FIELDS = (
    "strut_id",
    "junction0",
    "junction1",
    "unit_cell_edge_idx",
    "unit_cell_ids",
    "design_thickness",
    "start_x",
    "start_y",
    "start_z",
    "end_x",
    "end_y",
    "end_z",
    "shaft_sample_count",
    "mask_occupancy",
    "centerline_coverage",
    "raw_ct_score",
    "equivalent_thickness_um",
    "thickness_score",
    "longest_internal_gap_voxels",
    "continuity_score",
    "density_score",
    "otsu_threshold",
    "density_threshold",
    "classification",
)

UNIT_CELL_FIELDS = (
    "unit_cell_id",
    "index_x",
    "index_y",
    "index_z",
    "strut_count",
    "mean_density_score",
    "minimum_density_score",
    "present_count",
    "uncertain_count",
    "low_density_count",
    "broken_count",
    "missing_count",
)

LOW_DENSITY_SLICE_FIELDS = (
    "slice_index",
    "low_density_strut_count",
    "strut_ids",
)


def _positive_float(value: str) -> float:
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise argparse.ArgumentTypeError("value must be a positive finite number")
    return number


def _nonnegative_float(value: str) -> float:
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise argparse.ArgumentTypeError("value must be a nonnegative finite number")
    return number


def _nonnegative_int(value: str) -> int:
    number = int(value)
    if number < 0:
        raise argparse.ArgumentTypeError("value must be a nonnegative integer")
    return number


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Calculate per-strut and per-unit-cell density scores by comparing "
            "registered JSON geometry with raw CT and a segmented mask."
        )
    )
    parser.add_argument("raw_tiff", type=Path)
    parser.add_argument("mask_tiff", type=Path)
    parser.add_argument("registered_json", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--voxel-size-um", type=_positive_float, default=DEFAULT_VOXEL_SIZE_UM
    )
    parser.add_argument(
        "--target-um", type=_positive_float, default=DEFAULT_TARGET_UM
    )
    parser.add_argument(
        "--search-radius-voxels",
        type=_nonnegative_int,
        default=DEFAULT_SEARCH_RADIUS_VOXELS,
    )
    parser.add_argument(
        "--mask-weight", type=_nonnegative_float, default=DEFAULT_MASK_WEIGHT
    )
    parser.add_argument(
        "--raw-weight", type=_nonnegative_float, default=DEFAULT_RAW_WEIGHT
    )
    parser.add_argument(
        "--thickness-weight",
        type=_nonnegative_float,
        default=DEFAULT_THICKNESS_WEIGHT,
    )
    parser.add_argument(
        "--continuity-weight",
        type=_nonnegative_float,
        default=DEFAULT_CONTINUITY_WEIGHT,
    )
    parser.add_argument(
        "--uncertainty-margin",
        type=_nonnegative_float,
        default=DEFAULT_UNCERTAINTY_MARGIN,
    )
    parser.add_argument(
        "--signal-disagreement",
        type=_nonnegative_float,
        default=DEFAULT_SIGNAL_DISAGREEMENT,
    )
    parser.add_argument(
        "--raw-support-threshold",
        type=_nonnegative_float,
        default=DEFAULT_RAW_SUPPORT_THRESHOLD,
    )
    return parser


def _validate_tiff(path: Path, label: str) -> None:
    if path.suffix.lower() not in TIFF_SUFFIXES:
        raise ValueError(f"{label} must end in .tif or .tiff: {path}")
    if not path.is_file():
        raise FileNotFoundError(f"{label} not found: {path}")


def _validate_weights(weights: Sequence[float]) -> None:
    if not math.isclose(sum(weights), 1.0, rel_tol=0.0, abs_tol=1e-9):
        raise ValueError(f"density weights must sum to 1.0; got {sum(weights):.12g}")


def _load_design(
    path: Path,
) -> tuple[dict[int, np.ndarray], list[dict[str, Any]], list[dict[str, Any]]]:
    if path.suffix.lower() != ".json":
        raise ValueError(f"registered design must end in .json: {path}")
    if not path.is_file():
        raise FileNotFoundError(f"registered design not found: {path}")
    with path.open(encoding="utf-8") as stream:
        design = json.load(stream)
    if not isinstance(design, dict):
        raise ValueError("registered JSON must contain an object")
    junction_data = design.get("junctions")
    struts = design.get("struts")
    unit_cells = design.get("unit_cells")
    if not all(isinstance(value, list) for value in (junction_data, struts, unit_cells)):
        raise ValueError(
            "registered JSON must contain junctions, struts, and unit_cells lists"
        )
    if not junction_data or not struts or not unit_cells:
        raise ValueError("registered JSON geometry lists must not be empty")

    junctions: dict[int, np.ndarray] = {}
    for junction in junction_data:
        try:
            identifier = int(junction["id"])
            position = np.asarray(junction["position"], dtype=float)
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError("every junction needs a numeric id and position") from error
        if identifier in junctions:
            raise ValueError(f"duplicate junction id: {identifier}")
        if position.shape != (3,) or not np.isfinite(position).all():
            raise ValueError(f"junction {identifier} needs a finite XYZ position")
        junctions[identifier] = position

    seen_struts: set[int] = set()
    validated_struts = []
    for strut in struts:
        try:
            identifier = int(strut["id"])
            junction0 = int(strut["junction0"])
            junction1 = int(strut["junction1"])
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError(
                "every strut needs numeric id, junction0, and junction1"
            ) from error
        if identifier in seen_struts:
            raise ValueError(f"duplicate strut id: {identifier}")
        if junction0 not in junctions or junction1 not in junctions:
            raise ValueError(f"strut {identifier} references an unknown junction")
        seen_struts.add(identifier)
        validated_struts.append(dict(strut))

    seen_cells: set[int] = set()
    validated_cells = []
    for cell in unit_cells:
        try:
            identifier = int(cell["id"])
            indices = np.asarray(cell["indices"], dtype=int)
            cell_struts = [int(value) for value in cell["struts"]]
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError(
                "every unit cell needs numeric id, indices, and struts"
            ) from error
        if identifier in seen_cells:
            raise ValueError(f"duplicate unit-cell id: {identifier}")
        if indices.shape != (3,):
            raise ValueError(f"unit cell {identifier} needs three indices")
        unknown = set(cell_struts) - seen_struts
        if unknown:
            raise ValueError(
                f"unit cell {identifier} references unknown struts: {sorted(unknown)[:5]}"
            )
        seen_cells.add(identifier)
        validated_cells.append(dict(cell))
    return junctions, validated_struts, validated_cells


def _centerline_xyz(start: np.ndarray, stop: np.ndarray) -> np.ndarray:
    count = max(2, int(math.ceil(np.linalg.norm(stop - start))) + 1)
    xyz = np.linspace(start, stop, count)
    rounded = np.rint(xyz).astype(int)
    keep = np.ones(len(rounded), dtype=bool)
    keep[1:] = np.any(rounded[1:] != rounded[:-1], axis=1)
    return xyz[keep]


def _shaft_line(
    start_xyz: np.ndarray, stop_xyz: np.ndarray, endpoint_exclusion: int
) -> np.ndarray:
    line = _centerline_xyz(start_xyz, stop_xyz)
    if len(line) > 2 * endpoint_exclusion + 2:
        line = line[endpoint_exclusion:-endpoint_exclusion]
    return line


def _perpendicular_disk_xyz(
    start_xyz: np.ndarray, stop_xyz: np.ndarray, radius: int
) -> np.ndarray:
    direction = stop_xyz - start_xyz
    norm = np.linalg.norm(direction)
    if norm == 0:
        raise ValueError("strut endpoints must differ")
    direction = direction / norm
    reference = np.array([1.0, 0.0, 0.0])
    if abs(float(np.dot(direction, reference))) > 0.9:
        reference = np.array([0.0, 1.0, 0.0])
    first = np.cross(direction, reference)
    first /= np.linalg.norm(first)
    second = np.cross(direction, first)

    axis = np.arange(-radius, radius + 1, dtype=float)
    aa, bb = np.meshgrid(axis, axis, indexing="ij")
    keep = aa * aa + bb * bb <= radius * radius
    return (
        aa[keep, None] * first[None, :]
        + bb[keep, None] * second[None, :]
    )


def _slice_normalization(raw: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    lows = np.empty(raw.shape[0], dtype=np.float64)
    scales = np.empty(raw.shape[0], dtype=np.float64)
    for index in range(raw.shape[0]):
        image = np.asarray(raw[index])
        low = float(np.median(image))
        high = float(np.percentile(image, 99.5))
        lows[index] = low
        scales[index] = max(high - low, 1.0)
    return lows, scales


def _longest_internal_false_run(values: np.ndarray) -> int:
    supported = np.flatnonzero(values)
    if supported.size < 2:
        return 0
    selected = values[supported[0] : supported[-1] + 1]
    longest = current = 0
    for value in selected:
        if value:
            current = 0
        else:
            current += 1
            longest = max(longest, current)
    return longest


def _otsu_threshold(values: np.ndarray, bins: int = 256) -> float:
    values = np.asarray(values, dtype=float)
    values = values[np.isfinite(values)]
    if values.size == 0:
        raise ValueError("cannot threshold an empty score array")
    minimum = float(values.min())
    maximum = float(values.max())
    if math.isclose(minimum, maximum):
        return minimum
    counts, edges = np.histogram(values, bins=bins, range=(minimum, maximum))
    centers = (edges[:-1] + edges[1:]) / 2.0
    probabilities = counts.astype(float) / counts.sum()
    cumulative_weight = np.cumsum(probabilities)
    cumulative_mean = np.cumsum(probabilities * centers)
    total_mean = cumulative_mean[-1]
    denominator = cumulative_weight * (1.0 - cumulative_weight)
    variance = np.zeros_like(denominator)
    valid = denominator > 0
    variance[valid] = (
        (total_mean * cumulative_weight[valid] - cumulative_mean[valid]) ** 2
        / denominator[valid]
    )
    return float(centers[int(np.argmax(variance))])


def _cell_membership(
    unit_cells: Sequence[dict[str, Any]],
) -> dict[int, list[int]]:
    membership: dict[int, list[int]] = defaultdict(list)
    for cell in unit_cells:
        cell_id = int(cell["id"])
        for strut_id in cell["struts"]:
            membership[int(strut_id)].append(cell_id)
    return membership


def _analyze_strut(
    raw: np.ndarray,
    mask: np.ndarray,
    shape: np.ndarray,
    lows: np.ndarray,
    scales: np.ndarray,
    start_xyz: np.ndarray,
    stop_xyz: np.ndarray,
    radius: int,
    target_um: float,
    raw_support_threshold: float,
) -> dict[str, float | int | np.ndarray]:
    line_xyz = _shaft_line(start_xyz, stop_xyz, radius)
    disk = _perpendicular_disk_xyz(start_xyz, stop_xyz, radius)
    coordinates_xyz = line_xyz[:, None, :] + disk[None, :, :]
    coordinates_zyx = np.rint(coordinates_xyz[..., ::-1]).astype(int)
    valid = np.all(
        (coordinates_zyx >= 0) & (coordinates_zyx < shape[None, None, :]),
        axis=2,
    )

    local_occupancy = np.zeros(len(line_xyz), dtype=float)
    local_raw = np.zeros(len(line_xyz), dtype=float)
    for point_index, neighborhood in enumerate(coordinates_zyx):
        selected = neighborhood[valid[point_index]]
        if selected.size == 0:
            continue
        z, y, x = selected.T
        mask_values = np.asarray(mask[z, y, x]) > 0
        local_occupancy[point_index] = float(mask_values.mean())
        raw_values = np.asarray(raw[z, y, x], dtype=float)
        normalized = np.clip(
            (raw_values - lows[z]) / scales[z],
            0.0,
            1.0,
        )
        local_raw[point_index] = float(normalized.mean())

    mask_supported = local_occupancy > 0
    raw_supported = local_raw >= raw_support_threshold
    supported = mask_supported | raw_supported
    coverage = float(supported.mean()) if supported.size else 0.0
    gap = _longest_internal_false_run(supported)
    continuity = coverage * (1.0 - gap / max(len(supported), 1))
    mask_score = float(local_occupancy.mean()) if local_occupancy.size else 0.0
    raw_score = float(local_raw.mean()) if local_raw.size else 0.0

    equivalent_local = target_um * np.sqrt(np.clip(local_occupancy, 0.0, 1.0))
    supported_thickness = equivalent_local[mask_supported]
    equivalent_thickness = (
        float(np.median(supported_thickness)) if supported_thickness.size else 0.0
    )
    thickness_score = float(np.clip(equivalent_thickness / target_um, 0.0, 1.0))
    return {
        "sample_count": int(len(line_xyz)),
        "mask_score": mask_score,
        "coverage": coverage,
        "raw_score": raw_score,
        "equivalent_thickness": equivalent_thickness,
        "thickness_score": thickness_score,
        "gap": gap,
        "continuity": float(np.clip(continuity, 0.0, 1.0)),
        "supported": supported,
    }


def analyze_density(
    raw: np.ndarray,
    mask: np.ndarray,
    junctions: dict[int, np.ndarray],
    struts: Sequence[dict[str, Any]],
    unit_cells: Sequence[dict[str, Any]],
    target_um: float,
    search_radius_voxels: int,
    weights: Sequence[float],
    uncertainty_margin: float,
    signal_disagreement: float,
    raw_support_threshold: float,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], float]:
    if raw.shape != mask.shape:
        raise ValueError(f"raw and mask shapes differ: {raw.shape} != {mask.shape}")
    if raw.ndim != 3:
        raise ValueError(f"expected 3D volumes, got shape {raw.shape}")
    _validate_weights(weights)
    lows, scales = _slice_normalization(raw)
    shape = np.asarray(raw.shape, dtype=int)
    membership = _cell_membership(unit_cells)
    rows: list[dict[str, Any]] = []

    for strut in struts:
        strut_id = int(strut["id"])
        junction0 = int(strut["junction0"])
        junction1 = int(strut["junction1"])
        start = junctions[junction0]
        stop = junctions[junction1]
        metrics = _analyze_strut(
            raw=raw,
            mask=mask,
            shape=shape,
            lows=lows,
            scales=scales,
            start_xyz=start,
            stop_xyz=stop,
            radius=search_radius_voxels,
            target_um=target_um,
            raw_support_threshold=raw_support_threshold,
        )
        density_score = float(
            weights[0] * metrics["mask_score"]
            + weights[1] * metrics["raw_score"]
            + weights[2] * metrics["thickness_score"]
            + weights[3] * metrics["continuity"]
        )
        rows.append(
            {
                "strut_id": strut_id,
                "junction0": junction0,
                "junction1": junction1,
                "unit_cell_edge_idx": strut.get("unit_cell_edge_idx", ""),
                "unit_cell_ids": ";".join(
                    str(value) for value in membership.get(strut_id, [])
                ),
                "design_thickness": strut.get("thickness", ""),
                "start_x": float(start[0]),
                "start_y": float(start[1]),
                "start_z": float(start[2]),
                "end_x": float(stop[0]),
                "end_y": float(stop[1]),
                "end_z": float(stop[2]),
                "shaft_sample_count": metrics["sample_count"],
                "mask_occupancy": metrics["mask_score"],
                "centerline_coverage": metrics["coverage"],
                "raw_ct_score": metrics["raw_score"],
                "equivalent_thickness_um": metrics["equivalent_thickness"],
                "thickness_score": metrics["thickness_score"],
                "longest_internal_gap_voxels": metrics["gap"],
                "continuity_score": metrics["continuity"],
                "density_score": float(np.clip(density_score, 0.0, 1.0)),
                "otsu_threshold": 0.0,
                "density_threshold": 0.0,
                "classification": "",
                "_any_support": bool(np.any(metrics["supported"])),
            }
        )

    threshold = _otsu_threshold(
        np.asarray([row["density_score"] for row in rows], dtype=float)
    )
    low_density_threshold = max(0.0, threshold - uncertainty_margin)
    gap_limit = 2 * search_radius_voxels
    for row in rows:
        score = float(row["density_score"])
        if not row.pop("_any_support"):
            classification = "missing"
        elif int(row["longest_internal_gap_voxels"]) > gap_limit:
            classification = "broken"
        elif score < low_density_threshold:
            classification = "low_density"
        elif (
            abs(score - threshold) <= uncertainty_margin
            or abs(float(row["mask_occupancy"]) - float(row["raw_ct_score"]))
            > signal_disagreement
        ):
            classification = "uncertain"
        else:
            classification = "present"
        row["otsu_threshold"] = threshold
        row["density_threshold"] = low_density_threshold
        row["classification"] = classification

    by_strut = {int(row["strut_id"]): row for row in rows}
    cell_rows = []
    for cell in unit_cells:
        selected = [
            by_strut[int(identifier)]
            for identifier in cell["struts"]
            if int(identifier) in by_strut
        ]
        scores = np.asarray([row["density_score"] for row in selected], dtype=float)
        counts = Counter(row["classification"] for row in selected)
        indices = [int(value) for value in cell["indices"]]
        cell_rows.append(
            {
                "unit_cell_id": int(cell["id"]),
                "index_x": indices[0],
                "index_y": indices[1],
                "index_z": indices[2],
                "strut_count": len(selected),
                "mean_density_score": float(scores.mean()) if scores.size else 0.0,
                "minimum_density_score": float(scores.min()) if scores.size else 0.0,
                "present_count": counts["present"],
                "uncertain_count": counts["uncertain"],
                "low_density_count": counts["low_density"],
                "broken_count": counts["broken"],
                "missing_count": counts["missing"],
            }
        )
    return rows, cell_rows, threshold


def _low_density_by_slice(
    rows: Sequence[dict[str, Any]], slice_count: int
) -> list[dict[str, Any]]:
    struts_by_slice: dict[int, set[int]] = defaultdict(set)
    for row in rows:
        if row["classification"] != "low_density":
            continue
        start = np.array(
            [row["start_x"], row["start_y"], row["start_z"]], dtype=float
        )
        stop = np.array([row["end_x"], row["end_y"], row["end_z"]], dtype=float)
        line = _centerline_xyz(start, stop)
        z_indices = np.unique(np.rint(line[:, 2]).astype(int))
        for slice_index in z_indices:
            if 0 <= slice_index < slice_count:
                struts_by_slice[int(slice_index)].add(int(row["strut_id"]))
    return [
        {
            "slice_index": slice_index,
            "low_density_strut_count": len(struts_by_slice.get(slice_index, set())),
            "strut_ids": ";".join(
                str(value) for value in sorted(struts_by_slice.get(slice_index, set()))
            ),
        }
        for slice_index in range(slice_count)
    ]


def _write_csv(path: Path, fields: Sequence[str], rows: Sequence[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    key: f"{value:.8g}" if isinstance(value, float) else value
                    for key, value in row.items()
                    if key in fields
                }
            )


def _write_summary(
    path: Path,
    raw_path: Path,
    mask_path: Path,
    json_path: Path,
    rows: Sequence[dict[str, Any]],
    cell_rows: Sequence[dict[str, Any]],
    slice_rows: Sequence[dict[str, Any]],
    threshold: float,
    weights: Sequence[float],
    search_radius: int,
) -> None:
    counts = Counter(row["classification"] for row in rows)
    scores = np.asarray([row["density_score"] for row in rows], dtype=float)
    suspicious = sorted(rows, key=lambda row: float(row["density_score"]))[:30]
    suspicious_cells = sorted(
        cell_rows, key=lambda row: float(row["mean_density_score"])
    )[:20]
    low_density_threshold = (
        float(rows[0]["density_threshold"]) if rows else threshold
    )
    nonempty_slices = [
        row for row in slice_rows if int(row["low_density_strut_count"]) > 0
    ]
    lines = [
        "# JSON-Guided Strut Density Summary",
        "",
        f"- Raw CT: `{raw_path}`",
        f"- Segmented mask: `{mask_path}`",
        f"- Registered design: `{json_path}`",
        f"- Expected struts analyzed: **{len(rows)}**",
        f"- Unit cells analyzed: **{len(cell_rows)}**",
        f"- Otsu density threshold: **{threshold:.4f}**",
        (
            f"- Conservative low-density threshold: "
            f"**{low_density_threshold:.4f}**"
        ),
        f"- Mean density score: **{scores.mean():.4f}**",
        f"- Median density score: **{np.median(scores):.4f}**",
        "",
        "## Classification counts",
        "",
        "| Classification | Count | Percent |",
        "|---|---:|---:|",
    ]
    for classification in ("present", "uncertain", "low_density", "broken", "missing"):
        count = counts[classification]
        lines.append(
            f"| {classification} | {count} | {100.0 * count / len(rows):.2f}% |"
        )
    lines.extend(
        [
            "",
            "## Density formula",
            "",
            "```text",
            (
                f"score = {weights[0]:.2f}×mask + {weights[1]:.2f}×raw CT "
                f"+ {weights[2]:.2f}×thickness + {weights[3]:.2f}×continuity"
            ),
            "```",
            "",
            f"- Cross-sectional search radius: **{search_radius} voxels**",
            "- The score is dimensionless and is not physical density in g/cm³.",
            "",
            "## 30 lowest-density struts",
            "",
            "| Strut | Score | Class | Mask | Raw CT | Thickness (µm) | Gap |",
            "|---:|---:|---|---:|---:|---:|---:|",
        ]
    )
    for row in suspicious:
        lines.append(
            f"| {row['strut_id']} | {row['density_score']:.4f} | "
            f"{row['classification']} | {row['mask_occupancy']:.4f} | "
            f"{row['raw_ct_score']:.4f} | {row['equivalent_thickness_um']:.1f} | "
            f"{row['longest_internal_gap_voxels']} |"
        )
    lines.extend(
        [
            "",
            "## 20 lowest-density unit cells",
            "",
            "| Unit cell | Indices | Mean score | Minimum score | Missing | Broken | Low density |",
            "|---:|---|---:|---:|---:|---:|---:|",
        ]
    )
    for row in suspicious_cells:
        indices = f"({row['index_x']}, {row['index_y']}, {row['index_z']})"
        lines.append(
            f"| {row['unit_cell_id']} | {indices} | "
            f"{row['mean_density_score']:.4f} | {row['minimum_density_score']:.4f} | "
            f"{row['missing_count']} | {row['broken_count']} | "
            f"{row['low_density_count']} |"
        )
    lines.extend(
        [
            "",
            "## Low-density struts by Z slice",
            "",
            (
                "A strut is counted once on every Z slice intersected by its "
                "ideal JSON centerline. Slices with zero low-density struts remain "
                "available in `low_density_struts_by_slice.csv`."
            ),
            "",
            "| Z slice | Low-density struts |",
            "|---:|---:|",
        ]
    )
    for row in nonempty_slices:
        lines.append(
            f"| {row['slice_index']} | {row['low_density_strut_count']} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            (
                "The registered JSON defines where ideal struts should exist but "
                "does not contain observed defects. Raw CT, mask occupancy, "
                "equivalent thickness, and continuity supply the measured evidence."
            ),
            (
                "Classification prevalence is inferred from the current score "
                "distribution and continuity; it is not forced to match literature."
            ),
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_steps(
    path: Path,
    raw_path: Path,
    mask_path: Path,
    json_path: Path,
    voxel_size_um: float,
    target_um: float,
    search_radius: int,
    weights: Sequence[float],
    uncertainty_margin: float,
    disagreement: float,
    raw_support_threshold: float,
    density_threshold: float,
    low_density_threshold: float,
) -> None:
    lines = [
        "# Exact JSON-Guided Strut Density Calculation Steps",
        "",
        "## Inputs used",
        "",
        f"- Raw CT: `{raw_path}`",
        f"- Segmented mask: `{mask_path}`",
        f"- Registered ideal-design JSON: `{json_path}`",
        f"- Cubic voxel size: **{voxel_size_um:g} µm**",
        f"- Nominal target diameter: **{target_um:g} µm**",
        "",
        "## Process",
        "",
        "1. Validate that raw CT and mask TIFFs are 3D and have identical shapes.",
        (
            "2. Validate JSON junction IDs and XYZ positions, strut endpoint "
            "references, and unit-cell membership."
        ),
        (
            "3. Normalize each raw CT Z slice: subtract its median, divide by "
            "(P99.5 − median), and clip to 0–1."
        ),
        (
            "4. Interpolate each ideal JSON strut between its two junctions, "
            "convert XYZ sampling coordinates to TIFF ZYX indices, and exclude "
            f"{search_radius} samples at each endpoint to reduce node bias."
        ),
        (
            f"5. Construct a perpendicular radius-{search_radius}-voxel sampling "
            "disk at every remaining shaft point."
        ),
        (
            "6. Measure mask occupancy and normalized raw CT signal across those "
            "cross-sections."
        ),
        (
            "7. Mark local support when mask material is present or normalized "
            f"raw signal is at least {raw_support_threshold:.2f}; calculate "
            "coverage and the longest internal unsupported run."
        ),
        (
            "8. Estimate equivalent local diameter as target diameter × "
            "sqrt(cross-sectional mask occupancy), then take the median of "
            "supported shaft samples."
        ),
        (
            "9. Convert occupancy, raw CT, equivalent thickness, and continuity "
            "to bounded 0–1 component scores."
        ),
        "10. Calculate the combined material-presence score:",
        "",
        "```text",
        (
            f"score = {weights[0]:.2f}×mask occupancy "
            f"+ {weights[1]:.2f}×raw CT "
            f"+ {weights[2]:.2f}×thickness "
            f"+ {weights[3]:.2f}×continuity"
        ),
        "```",
        "",
        (
            f"11. Apply Otsu separation to all strut scores. This run's threshold "
            f"is **{density_threshold:.6f}**."
        ),
        (
            f"    Use the conservative low-density cutoff Otsu minus the "
            f"uncertainty margin: **{low_density_threshold:.6f}**."
        ),
        "12. Classify in order:",
        "    - Missing: no raw-or-mask support anywhere on the shaft.",
        (
            f"    - Broken: internal unsupported run longer than "
            f"{2 * search_radius} rasterized centerline samples."
        ),
        "    - Low density: score below the conservative low-density cutoff.",
        (
            f"    - Uncertain: score within {uncertainty_margin:.3f} of the "
            f"threshold or mask/raw disagreement greater than {disagreement:.3f}."
        ),
        "    - Present: none of the above.",
        (
            "13. Aggregate each JSON unit cell from the scores and classes of its "
            "listed struts."
        ),
        (
            "14. Count each low-density strut once on every Z slice intersected "
            "by its ideal JSON centerline."
        ),
        (
            "15. Write per-strut, per-unit-cell, and per-slice CSV files plus "
            "the Markdown summary."
        ),
        "",
        "## Output definitions",
        "",
        "- `strut_density.csv`: one traceable row per ideal JSON strut.",
        "- `unit_cell_density.csv`: aggregate density and defect counts by unit cell.",
        (
            "- `low_density_struts_by_slice.csv`: all Z slices, low-density "
            "counts, and intersecting strut IDs."
        ),
        "- `density_summary.md`: totals and lowest-density candidates.",
        "- `strut_density_calculation_steps.md`: this parameter-specific document.",
        "",
        "## Limitations",
        "",
        (
            "- Density score is a relative 0–1 material-presence score, not "
            "calibrated mass density."
        ),
        "- Results depend on JSON-to-TIFF registration and segmentation quality.",
        (
            "- Equivalent thickness comes from cross-sectional occupied area; "
            "the separate thickness agent provides independent global EDT-based "
            "thickness validation."
        ),
        "- Diagonal rasterized gap counts do not convert exactly to axial microns.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def run(args: argparse.Namespace) -> None:
    _validate_tiff(args.raw_tiff, "raw TIFF")
    _validate_tiff(args.mask_tiff, "mask TIFF")
    weights = (
        args.mask_weight,
        args.raw_weight,
        args.thickness_weight,
        args.continuity_weight,
    )
    _validate_weights(weights)
    raw = tifffile.memmap(args.raw_tiff)
    mask = tifffile.memmap(args.mask_tiff)
    junctions, struts, unit_cells = _load_design(args.registered_json)
    rows, cell_rows, threshold = analyze_density(
        raw=raw,
        mask=mask,
        junctions=junctions,
        struts=struts,
        unit_cells=unit_cells,
        target_um=args.target_um,
        search_radius_voxels=args.search_radius_voxels,
        weights=weights,
        uncertainty_margin=args.uncertainty_margin,
        signal_disagreement=args.signal_disagreement,
        raw_support_threshold=args.raw_support_threshold,
    )
    slice_rows = _low_density_by_slice(rows, raw.shape[0])
    args.output_dir.mkdir(parents=True, exist_ok=True)
    strut_path = args.output_dir / "strut_density.csv"
    cell_path = args.output_dir / "unit_cell_density.csv"
    slice_path = args.output_dir / "low_density_struts_by_slice.csv"
    summary_path = args.output_dir / "density_summary.md"
    steps_path = args.output_dir / "strut_density_calculation_steps.md"
    _write_csv(strut_path, STRUT_FIELDS, rows)
    _write_csv(cell_path, UNIT_CELL_FIELDS, cell_rows)
    _write_csv(slice_path, LOW_DENSITY_SLICE_FIELDS, slice_rows)
    _write_summary(
        summary_path,
        args.raw_tiff,
        args.mask_tiff,
        args.registered_json,
        rows,
        cell_rows,
        slice_rows,
        threshold,
        weights,
        args.search_radius_voxels,
    )
    _write_steps(
        steps_path,
        args.raw_tiff,
        args.mask_tiff,
        args.registered_json,
        args.voxel_size_um,
        args.target_um,
        args.search_radius_voxels,
        weights,
        args.uncertainty_margin,
        args.signal_disagreement,
        args.raw_support_threshold,
        threshold,
        float(rows[0]["density_threshold"]) if rows else threshold,
    )
    print(f"Analyzed {len(rows)} expected struts and {len(cell_rows)} unit cells.")
    print(f"Otsu density threshold: {threshold:.6f}")
    print(f"Saved {strut_path}")
    print(f"Saved {cell_path}")
    print(f"Saved {slice_path}")
    print(f"Saved {summary_path}")
    print(f"Saved {steps_path}")


def main() -> None:
    run(build_parser().parse_args())


if __name__ == "__main__":
    main()
