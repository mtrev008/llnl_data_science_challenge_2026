"""Measure lattice-strut thickness and optionally identify strut defects.

The analysis samples evenly spaced Z slices, measures local 3D diameter at
strut centerlines, and writes a percentile curve, box plot, and Markdown summary.
When an aligned design JSON is supplied, it separately compares every expected
strut with the volume to identify missing and broken struts. It is intended for
segmented lattice data, but a raw CT TIFF can also be supplied when a
segmentation threshold is provided.

Example:
    python src/strut_thickness_analysis.py segmented_mask.tif \
        --output-dir thickness_results
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Any, Sequence

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import tifffile
from scipy.ndimage import binary_dilation, convolve, distance_transform_edt
from skimage.morphology import skeletonize


DEFAULT_TARGET_UM = 350.0
DEFAULT_TOLERANCE_PERCENT = 25.0
DEFAULT_SAMPLE_FRACTION = 0.10
# Tran et al., NDT & E International 138 (2023), 102870, Section 2.2:
# the reconstructed X-ray CT data use cubic 58.1 µm voxels.
DEFAULT_VOXEL_SIZE_UM = 58.1
VOXEL_SIZE_SOURCE_URL = "https://doi.org/10.1016/j.ndteint.2023.102870"
# ceil((350 µm / 2) / 58.1 µm) = 4 voxels: the nominal strut radius.
DEFAULT_SEARCH_RADIUS_VOXELS = 4
TIFF_SUFFIXES = {".tif", ".tiff"}

DEFECT_CSV_FIELDS = (
    "strut_id",
    "junction0",
    "junction1",
    "sample_count",
    "coverage_fraction",
    "longest_gap_voxels",
    "classification",
)


def _positive_float(value: str) -> float:
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise argparse.ArgumentTypeError("value must be a positive finite number")
    return number


def _fraction(value: str) -> float:
    number = float(value)
    if not math.isfinite(number) or not 0 < number <= 1:
        raise argparse.ArgumentTypeError("value must be greater than 0 and at most 1")
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
            "Measure 3D strut thickness on evenly sampled TIFF slices and "
            "optionally compare the mask with an aligned strut design."
        )
    )
    parser.add_argument("input_tiff", type=Path, help="Raw CT or binary mask TIFF")
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Directory for the PNG plots and per-slice CSV",
    )
    parser.add_argument(
        "--input-kind",
        choices=("auto", "mask", "raw"),
        default="auto",
        help="Interpret the input as a mask or raw CT (default: auto)",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        help="Foreground threshold required for raw CT input (voxels >= threshold)",
    )
    parser.add_argument(
        "--skeleton-tiff",
        type=Path,
        help="Optional precomputed skeleton TIFF with the same shape as the input",
    )
    parser.add_argument(
        "--voxel-size-um",
        type=_positive_float,
        default=DEFAULT_VOXEL_SIZE_UM,
        help=f"Cubic voxel edge length in microns (default: {DEFAULT_VOXEL_SIZE_UM})",
    )
    parser.add_argument(
        "--target-um",
        type=_positive_float,
        default=DEFAULT_TARGET_UM,
        help=f"Nominal strut diameter in microns (default: {DEFAULT_TARGET_UM})",
    )
    parser.add_argument(
        "--tolerance-percent",
        type=_nonnegative_float,
        default=DEFAULT_TOLERANCE_PERCENT,
        help=(
            "Symmetric accuracy tolerance around the target "
            f"(default: {DEFAULT_TOLERANCE_PERCENT} percent)"
        ),
    )
    parser.add_argument(
        "--sample-fraction",
        type=_fraction,
        default=DEFAULT_SAMPLE_FRACTION,
        help=f"Fraction of Z slices to sample (default: {DEFAULT_SAMPLE_FRACTION})",
    )
    parser.add_argument(
        "--registered-json",
        type=Path,
        help=(
            "Optional aligned design JSON containing expected junctions and struts; "
            "enables missing/broken strut classification"
        ),
    )
    parser.add_argument(
        "--search-radius-voxels",
        type=_nonnegative_int,
        default=DEFAULT_SEARCH_RADIUS_VOXELS,
        help=(
            "Registration-search radius around each expected centerline point "
            f"(default: {DEFAULT_SEARCH_RADIUS_VOXELS})"
        ),
    )
    return parser


def _validate_tiff_path(path: Path, label: str) -> None:
    if path.suffix.lower() not in TIFF_SUFFIXES:
        raise ValueError(f"{label} must end in .tif or .tiff: {path}")
    if not path.is_file():
        raise FileNotFoundError(f"{label} not found: {path}")


def _looks_binary(volume: np.ndarray) -> bool:
    """Inspect a few planes to distinguish common 0/1/255 masks from raw CT."""
    if np.issubdtype(volume.dtype, np.bool_):
        return True
    if not np.issubdtype(volume.dtype, np.integer):
        return False

    indices = np.unique(
        np.linspace(0, volume.shape[0] - 1, min(9, volume.shape[0]), dtype=int)
    )
    allowed = np.array([0, 1, 255], dtype=volume.dtype)
    return all(np.isin(np.asarray(volume[index]), allowed).all() for index in indices)


def _sample_indices(slice_count: int, sample_fraction: float) -> np.ndarray:
    sample_count = max(1, int(round(slice_count * sample_fraction)))
    return np.unique(
        np.linspace(0, slice_count - 1, sample_count, dtype=int)
    )


def _classify(
    measurements_um: np.ndarray, lower_um: float, upper_um: float
) -> tuple[float, float, float]:
    count = measurements_um.size
    too_thin = 100.0 * np.count_nonzero(measurements_um < lower_um) / count
    accurate = (
        100.0
        * np.count_nonzero(
            (measurements_um >= lower_um) & (measurements_um <= upper_um)
        )
        / count
    )
    too_thick = 100.0 * np.count_nonzero(measurements_um > upper_um) / count
    return float(too_thin), float(accurate), float(too_thick)


def _measure_slice(
    volume: np.ndarray,
    slice_index: int,
    halo_voxels: int,
    input_is_mask: bool,
    threshold: float | None,
    voxel_size_um: float,
    target_um: float,
    skeleton_volume: np.ndarray | None,
) -> np.ndarray:
    """Measure shaft diameters centered on one Z slice using a 3D halo."""
    start = max(0, slice_index - halo_voxels)
    stop = min(volume.shape[0], slice_index + halo_voxels + 1)
    center = slice_index - start

    chunk = np.asarray(volume[start:stop])
    if input_is_mask:
        mask = chunk > 0
    else:
        if threshold is None:
            raise ValueError("a finite --threshold is required for raw CT input")
        mask = chunk >= threshold

    if skeleton_volume is None:
        skeleton = skeletonize(mask)
    else:
        skeleton = np.asarray(skeleton_volume[start:stop]) > 0
        if np.any(skeleton & ~mask):
            raise ValueError(
                "the supplied skeleton contains foreground outside the segmented mask"
            )

    if not np.any(skeleton[center]):
        return np.empty(0, dtype=float)

    neighbor_kernel = np.ones((3, 3, 3), dtype=np.uint8)
    neighbor_kernel[1, 1, 1] = 0
    neighbor_count = convolve(
        skeleton.astype(np.uint8), neighbor_kernel, mode="constant", cval=0
    )

    # Junctions have more than two skeleton neighbors. Exclude a nominal-radius
    # neighborhood around them so thick lattice nodes are not counted as shafts.
    branch_points = skeleton & (neighbor_count > 2)
    exclusion_radius = max(
        1, int(math.ceil((target_um / 2.0) / voxel_size_um))
    )
    near_junction = binary_dilation(branch_points, iterations=exclusion_radius)
    valid_centerline = (
        skeleton[center]
        & (neighbor_count[center] == 2)
        & ~near_junction[center]
    )
    if not np.any(valid_centerline):
        return np.empty(0, dtype=float)

    radius_um = distance_transform_edt(
        mask, sampling=(voxel_size_um, voxel_size_um, voxel_size_um)
    )
    return 2.0 * radius_um[center][valid_centerline]


def measure_sampled_slices(
    volume: np.ndarray,
    sample_indices: Sequence[int],
    input_is_mask: bool,
    threshold: float | None,
    voxel_size_um: float,
    target_um: float,
    skeleton_volume: np.ndarray | None = None,
) -> tuple[list[tuple[int, np.ndarray]], int]:
    """Return thickness measurements for each requested Z slice."""
    nominal_radius_voxels = int(
        math.ceil((target_um / 2.0) / voxel_size_um)
    )
    halo_voxels = max(3, 2 * nominal_radius_voxels + 2)

    results = []
    for slice_index in sample_indices:
        measurements = _measure_slice(
            volume=volume,
            slice_index=int(slice_index),
            halo_voxels=halo_voxels,
            input_is_mask=input_is_mask,
            threshold=threshold,
            voxel_size_um=voxel_size_um,
            target_um=target_um,
            skeleton_volume=skeleton_volume,
        )
        results.append((int(slice_index), measurements))
    return results, halo_voxels


def _write_csv(
    path: Path,
    fieldnames: Sequence[str],
    rows: Sequence[dict[str, int | float | str]],
) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            formatted = {
                key: f"{value:.6g}" if isinstance(value, float) else value
                for key, value in row.items()
            }
            writer.writerow(formatted)


def _plot_percentile_curve(
    path: Path,
    measurements_um: np.ndarray,
    target_um: float,
    lower_um: float,
    upper_um: float,
) -> None:
    ordered = np.sort(measurements_um)
    percentiles = np.linspace(0.0, 100.0, ordered.size)

    figure, axis = plt.subplots(figsize=(9, 5.5))
    axis.plot(percentiles, ordered, color="#2457A6", linewidth=1.8)
    axis.axhspan(
        lower_um,
        upper_um,
        color="#3A923A",
        alpha=0.14,
        label=f"Accurate: {lower_um:g}–{upper_um:g} µm",
    )
    axis.axhline(
        target_um,
        color="#C23B22",
        linestyle="--",
        linewidth=1.5,
        label=f"Target: {target_um:g} µm",
    )
    axis.set(
        title="Sampled Strut Thickness Distribution",
        xlabel="Measurement percentile",
        ylabel="Local strut diameter (µm)",
        xlim=(0, 100),
    )
    axis.grid(alpha=0.25)
    axis.legend()
    figure.tight_layout()
    figure.savefig(path, dpi=180)
    plt.close(figure)


def _plot_box(
    path: Path,
    measurements_um: np.ndarray,
) -> None:
    figure, axis = plt.subplots(figsize=(6.5, 6.5))
    axis.boxplot(
        measurements_um,
        tick_labels=["Observed shaft locations"],
        whis=1.5,
        showmeans=True,
        showfliers=True,
        patch_artist=True,
        boxprops={"facecolor": "#7CA9D8", "edgecolor": "#2457A6"},
        medianprops={"color": "#132A4F", "linewidth": 2},
        meanprops={
            "marker": "D",
            "markerfacecolor": "#F2A541",
            "markeredgecolor": "#8A5700",
        },
        flierprops={
            "marker": ".",
            "markersize": 2.5,
            "markerfacecolor": "#666666",
            "markeredgecolor": "#666666",
            "alpha": 0.35,
        },
    )
    axis.set(
        title="Observed Local Strut Thickness Distribution",
        ylabel="Local strut diameter (µm)",
    )
    axis.grid(axis="y", alpha=0.25)
    figure.tight_layout()
    figure.savefig(path, dpi=180)
    plt.close(figure)


def _plot_cdf(
    path: Path,
    measurements_um: np.ndarray,
) -> None:
    ordered = np.sort(measurements_um)
    cumulative = np.arange(1, ordered.size + 1) / ordered.size
    figure, axis = plt.subplots(figsize=(9, 5.5))
    axis.plot(ordered, cumulative, color="#2457A6", linewidth=1.8)
    axis.set(
        title="Observed Local Strut Thickness: Empirical CDF",
        xlabel="Local strut diameter (µm)",
        ylabel="Cumulative fraction",
        ylim=(0, 1),
    )
    axis.grid(alpha=0.25)
    figure.tight_layout()
    figure.savefig(path, dpi=180)
    plt.close(figure)


def _load_registered_design(
    path: Path,
) -> tuple[dict[int, np.ndarray], list[dict[str, Any]]]:
    if path.suffix.lower() != ".json":
        raise ValueError(f"registered design must end in .json: {path}")
    if not path.is_file():
        raise FileNotFoundError(f"registered design not found: {path}")

    with path.open(encoding="utf-8") as stream:
        design = json.load(stream)
    if not isinstance(design, dict):
        raise ValueError("registered design JSON must contain an object")

    junction_data = design.get("junctions")
    strut_data = design.get("struts")
    if not isinstance(junction_data, list) or not isinstance(strut_data, list):
        raise ValueError(
            "registered design JSON must contain junctions and struts lists"
        )
    if not junction_data or not strut_data:
        raise ValueError("registered design must contain at least one strut")

    junctions: dict[int, np.ndarray] = {}
    for junction in junction_data:
        if not isinstance(junction, dict):
            raise ValueError("every junction must be an object")
        try:
            junction_id = int(junction["id"])
            position = np.asarray(junction["position"], dtype=float)
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError("each junction needs a numeric id and position") from error
        if position.shape != (3,) or not np.isfinite(position).all():
            raise ValueError(
                f"junction {junction_id} must have a finite XYZ position"
            )
        if junction_id in junctions:
            raise ValueError(f"duplicate junction id: {junction_id}")
        junctions[junction_id] = position

    struts: list[dict[str, Any]] = []
    seen_strut_ids: set[int] = set()
    for strut in strut_data:
        if not isinstance(strut, dict):
            raise ValueError("every strut must be an object")
        try:
            strut_id = int(strut["id"])
            junction0 = int(strut["junction0"])
            junction1 = int(strut["junction1"])
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError(
                "each strut needs numeric id, junction0, and junction1 values"
            ) from error
        if strut_id in seen_strut_ids:
            raise ValueError(f"duplicate strut id: {strut_id}")
        if junction0 not in junctions or junction1 not in junctions:
            raise ValueError(
                f"strut {strut_id} references an unknown junction"
            )
        seen_strut_ids.add(strut_id)
        struts.append(
            {
                "id": strut_id,
                "junction0": junction0,
                "junction1": junction1,
            }
        )
    return junctions, struts


def _sphere_offsets(radius_voxels: int) -> np.ndarray:
    axis = np.arange(-radius_voxels, radius_voxels + 1, dtype=int)
    zz, yy, xx = np.meshgrid(axis, axis, axis, indexing="ij")
    offsets = np.column_stack((zz.ravel(), yy.ravel(), xx.ravel()))
    return offsets[np.sum(offsets * offsets, axis=1) <= radius_voxels**2]


def _centerline_voxels(start_xyz: np.ndarray, stop_xyz: np.ndarray) -> np.ndarray:
    sample_count = max(2, int(math.ceil(np.linalg.norm(stop_xyz - start_xyz))) + 1)
    xyz = np.linspace(start_xyz, stop_xyz, sample_count)
    zyx = np.rint(xyz[:, ::-1]).astype(int)
    keep = np.ones(len(zyx), dtype=bool)
    keep[1:] = np.any(zyx[1:] != zyx[:-1], axis=1)
    return zyx[keep]


def _longest_false_run(values: np.ndarray) -> int:
    """Return the longest internal false run bracketed by true values."""
    supported_indices = np.flatnonzero(values)
    if supported_indices.size < 2:
        return 0
    values = values[supported_indices[0] : supported_indices[-1] + 1]
    longest = 0
    current = 0
    for value in values:
        if value:
            current = 0
        else:
            current += 1
            longest = max(longest, current)
    return longest


def classify_expected_struts(
    volume: np.ndarray,
    junctions: dict[int, np.ndarray],
    struts: Sequence[dict[str, Any]],
    input_is_mask: bool,
    threshold: float | None,
    search_radius_voxels: int,
) -> list[dict[str, int | float | str]]:
    """Compare aligned expected centerlines with foreground in a ZYX volume."""
    if not input_is_mask and threshold is None:
        raise ValueError("a finite threshold is required to classify raw CT data")

    offsets = _sphere_offsets(search_radius_voxels)
    shape = np.asarray(volume.shape, dtype=int)
    rows: list[dict[str, int | float | str]] = []

    for strut in struts:
        junction0 = int(strut["junction0"])
        junction1 = int(strut["junction1"])
        line = _centerline_voxels(junctions[junction0], junctions[junction1])
        neighborhoods = line[:, None, :] + offsets[None, :, :]
        in_bounds = np.all(
            (neighborhoods >= 0) & (neighborhoods < shape[None, None, :]),
            axis=2,
        )
        supported = np.zeros(len(line), dtype=bool)
        for point_index, neighborhood in enumerate(neighborhoods):
            coordinates = neighborhood[in_bounds[point_index]]
            if coordinates.size == 0:
                continue
            values = np.asarray(
                volume[
                    coordinates[:, 0],
                    coordinates[:, 1],
                    coordinates[:, 2],
                ]
            )
            foreground = values > 0 if input_is_mask else values >= threshold
            supported[point_index] = bool(np.any(foreground))

        coverage = float(np.mean(supported))
        longest_gap = _longest_false_run(supported)
        # A missing strut has no foreground support anywhere on its registered
        # expected centerline. A broken strut has material on both sides of an
        # internal unsupported run longer than the registration-search diameter.
        if not np.any(supported):
            classification = "missing"
        elif longest_gap > 2 * search_radius_voxels:
            classification = "broken"
        else:
            classification = "present"

        rows.append(
            {
                "strut_id": int(strut["id"]),
                "junction0": junction0,
                "junction1": junction1,
                "sample_count": int(len(line)),
                "coverage_fraction": coverage,
                "longest_gap_voxels": longest_gap,
                "classification": classification,
            }
        )
    return rows


def _write_defect_summary(
    path: Path,
    input_tiff: Path,
    registered_json: Path,
    rows: Sequence[dict[str, int | float | str]],
    search_radius_voxels: int,
    voxel_size_um: float,
) -> dict[str, int]:
    counts = {
        classification: sum(
            row["classification"] == classification for row in rows
        )
        for classification in ("present", "missing", "broken")
    }
    total = len(rows)
    lines = [
        "# Expected-Strut Defect Summary",
        "",
        f"- TIFF: `{input_tiff}`",
        f"- Registered design: `{registered_json}`",
        f"- Expected struts: **{total}**",
        (
            f"- Present struts: **{counts['present']}** "
            f"({100.0 * counts['present'] / total:.2f}%)"
        ),
        (
            f"- Missing struts: **{counts['missing']}** "
            f"({100.0 * counts['missing'] / total:.2f}%)"
        ),
        (
            f"- Broken struts: **{counts['broken']}** "
            f"({100.0 * counts['broken'] / total:.2f}%)"
        ),
        "",
        "## Classification method",
        "",
        "- Missing: no foreground support anywhere along an expected JSON centerline.",
        (
            "- Broken: foreground exists on both sides of an internal unsupported "
            f"run longer than **{2 * search_radius_voxels} voxels**."
        ),
        "- Present: neither of the above conditions is met.",
        (
            "- These rules detect defects from this TIFF and do not force the "
            "counts to match literature percentages."
        ),
        "",
        "## Diagnostic parameters",
        "",
        (
            f"- Broken-run cutoff: **{2 * search_radius_voxels} voxels** "
            f"(**{2 * search_radius_voxels * voxel_size_um:g} µm**), derived from "
            "the diameter of the registration-search neighborhood."
        ),
        f"- Registration search radius: **{search_radius_voxels} voxels**",
        "",
        (
            "Thickness categories describe material around surviving centerlines. "
            "Missing and broken classifications instead compare every expected "
            "design centerline with foreground in the TIFF."
        ),
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
    return counts


def _write_thickness_summary(
    path: Path,
    input_tiff: Path,
    sampled_slice_count: int,
    total_slice_count: int,
    measurements_um: np.ndarray,
    voxel_size_um: float,
    target_um: float,
    lower_um: float,
    upper_um: float,
    percentages: tuple[float, float, float],
) -> None:
    percentiles = np.percentile(measurements_um, [10, 25, 50, 75, 90])
    source_note = (
        "This is the published cubic CT voxel size for this dataset "
        f"([Tran et al., 2023]({VOXEL_SIZE_SOURCE_URL}))."
        if math.isclose(voxel_size_um, DEFAULT_VOXEL_SIZE_UM)
        else "This value was supplied on the command line; verify it against the "
        "metadata for the input scan."
    )
    lines = [
        "# Strut Thickness Summary",
        "",
        f"- TIFF: `{input_tiff}`",
        f"- Sampled Z slices: **{sampled_slice_count} of {total_slice_count}**",
        f"- Shaft-centerline measurements: **{measurements_um.size}**",
        f"- Cubic voxel edge length: **{voxel_size_um:g} µm**. {source_note}",
        (
            f"- Nominal designed strut diameter: **{target_um:g} µm** "
            "(a design target, not the CT voxel size)"
        ),
        f"- Accepted range: **{lower_um:g}–{upper_um:g} µm**",
        "",
        "## Measured local-diameter distribution",
        "",
        f"- P10: **{percentiles[0]:.1f} µm**",
        f"- P25: **{percentiles[1]:.1f} µm**",
        f"- Median: **{percentiles[2]:.1f} µm**",
        f"- P75: **{percentiles[3]:.1f} µm**",
        f"- P90: **{percentiles[4]:.1f} µm**",
        f"- Too thin: **{percentages[0]:.2f}%**",
        f"- Within accepted range: **{percentages[1]:.2f}%**",
        f"- Too thick: **{percentages[2]:.2f}%**",
        "",
        (
            "These are segmentation-derived local diameters computed from the "
            "3D Euclidean distance transform at shaft centerline voxels. Their "
            "absolute accuracy is limited by the 58.1 µm voxel resolution and "
            "the quality of the segmentation."
        ),
        (
            "The distribution contains observed foreground only. Its smallest "
            f"possible centerline diameter is two voxel radii "
            f"({2.0 * voxel_size_um:g} µm). Missing struts are absent observations, "
            "not zero-diameter measurements, and are reported separately in the "
            "expected-strut defect results."
        ),
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def _format_outlier_values(values: np.ndarray) -> str:
    if values.size == 0:
        return "—"
    rounded = np.round(values, 1)
    unique, counts = np.unique(rounded, return_counts=True)
    return ", ".join(
        f"{value:.1f} µm × {count}"
        for value, count in zip(unique, counts, strict=True)
    )


def _write_high_thickness_outliers(
    path: Path,
    input_tiff: Path,
    measurements_by_slice: Sequence[tuple[int, np.ndarray]],
    total_slice_count: int,
) -> None:
    nonempty = [values for _, values in measurements_by_slice if values.size]
    measurements = np.concatenate(nonempty)
    q1, q3 = np.percentile(measurements, [25, 75])
    iqr = q3 - q1
    upper_fence = q3 + 1.5 * iqr

    slice_rows = []
    for slice_index, values in measurements_by_slice:
        high = values[values > upper_fence]
        if high.size:
            slice_rows.append((slice_index, values.size, high))

    high_total = sum(high.size for _, _, high in slice_rows)
    sampled_count = len(measurements_by_slice)
    lines = [
        "# High Strut Thickness Outlier Report",
        "",
        f"- TIFF: `{input_tiff}`",
        f"- Sampled Z slices: **{sampled_count} of {total_slice_count}**",
        f"- Total shaft-centerline measurements: **{measurements.size}**",
        "- High-outlier rule: **above Q3 + 1.5 × IQR**",
        f"- Q1: **{q1:.1f} µm**",
        f"- Q3: **{q3:.1f} µm**",
        f"- IQR: **{iqr:.1f} µm**",
        f"- Upper fence: **{upper_fence:.1f} µm**",
        (
            f"- High outliers: **{high_total} "
            f"({100.0 * high_total / measurements.size:.2f}%)**"
        ),
        "",
        (
            "> This report identifies outlier measurement locations only among "
            "the sampled slices. It does not imply that an entire strut is "
            "defective, missing, or broken."
        ),
        "",
        "## High outliers by Z slice",
        "",
        "| Z slice | Measurements | High outliers | High-outlier % |",
        "|---:|---:|---:|---:|",
    ]
    for slice_index, count, high in slice_rows:
        lines.append(
            f"| {slice_index} | {count} | {high.size} | "
            f"{100.0 * high.size / count:.2f}% |"
        )

    lines.extend(["", "## Thickness values by high-outlier slice", ""])
    for slice_index, _, high in slice_rows:
        lines.extend(
            [
                f"### Z slice {slice_index}",
                "",
                f"- High values: {_format_outlier_values(high)}",
                "",
            ]
        )
    if not slice_rows:
        lines.extend(["No high Tukey outliers were found in the sampled slices.", ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_low_thickness_outliers(
    path: Path,
    input_tiff: Path,
    measurements_by_slice: Sequence[tuple[int, np.ndarray]],
    total_slice_count: int,
    lower_percentile: float = 5.0,
) -> None:
    nonempty = [values for _, values in measurements_by_slice if values.size]
    measurements = np.concatenate(nonempty)
    cutoff = float(np.percentile(measurements, lower_percentile))

    slice_rows = []
    for slice_index, values in measurements_by_slice:
        low = values[values < cutoff]
        if low.size:
            slice_rows.append((slice_index, values.size, low))

    low_total = sum(low.size for _, _, low in slice_rows)
    lines = [
        "# Low Strut Thickness Outlier Report",
        "",
        f"- TIFF: `{input_tiff}`",
        f"- Sampled Z slices: **{len(measurements_by_slice)} of {total_slice_count}**",
        f"- Total shaft-centerline measurements: **{measurements.size}**",
        f"- Low-outlier rule: **strictly below the {lower_percentile:g}th percentile**",
        f"- Low-thickness cutoff: **{cutoff:.1f} µm**",
        (
            f"- Low outliers: **{low_total} "
            f"({100.0 * low_total / measurements.size:.2f}%)**"
        ),
        "",
        (
            "> Thickness values are quantized by the voxel grid. Values tied at "
            "the percentile cutoff are excluded so a large quantized plateau is "
            "not mislabeled as outlying."
        ),
        "",
        (
            "> This report identifies low observed thickness locations only "
            "among sampled slices. It does not classify missing or broken struts."
        ),
        "",
        "## Low outliers by Z slice",
        "",
        "| Z slice | Measurements | Low outliers | Low-outlier % |",
        "|---:|---:|---:|---:|",
    ]
    for slice_index, count, low in slice_rows:
        lines.append(
            f"| {slice_index} | {count} | {low.size} | "
            f"{100.0 * low.size / count:.2f}% |"
        )

    lines.extend(["", "## Thickness values by low-outlier slice", ""])
    for slice_index, _, low in slice_rows:
        lines.extend(
            [
                f"### Z slice {slice_index}",
                "",
                f"- Low values: {_format_outlier_values(low)}",
                "",
            ]
        )
    if not slice_rows:
        lines.extend(["No low-tail outliers were found in the sampled slices.", ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def run_analysis(args: argparse.Namespace) -> None:
    _validate_tiff_path(args.input_tiff, "input TIFF")
    if args.skeleton_tiff is not None:
        _validate_tiff_path(args.skeleton_tiff, "skeleton TIFF")
    if args.threshold is not None and not math.isfinite(args.threshold):
        raise ValueError("--threshold must be finite")

    volume = tifffile.memmap(args.input_tiff)
    if volume.ndim != 3:
        raise ValueError(f"expected a 3D TIFF, got shape {volume.shape}")

    if args.input_kind == "mask":
        input_is_mask = True
    elif args.input_kind == "raw":
        input_is_mask = False
    else:
        input_is_mask = _looks_binary(volume)

    if not input_is_mask and args.threshold is None:
        raise ValueError(
            "input appears to be raw CT data; provide --threshold or use "
            "--input-kind mask if it is already segmented"
        )

    skeleton_volume = None
    if args.skeleton_tiff is not None:
        skeleton_volume = tifffile.memmap(args.skeleton_tiff)
        if skeleton_volume.ndim != 3:
            raise ValueError(
                f"expected a 3D skeleton TIFF, got shape {skeleton_volume.shape}"
            )
        if skeleton_volume.shape != volume.shape:
            raise ValueError(
                "input and skeleton shapes differ: "
                f"{volume.shape} != {skeleton_volume.shape}"
            )

    sampled_indices = _sample_indices(volume.shape[0], args.sample_fraction)
    lower_um = args.target_um * (1.0 - args.tolerance_percent / 100.0)
    upper_um = args.target_um * (1.0 + args.tolerance_percent / 100.0)

    measurements_by_slice, halo_voxels = measure_sampled_slices(
        volume=volume,
        sample_indices=sampled_indices,
        input_is_mask=input_is_mask,
        threshold=args.threshold,
        voxel_size_um=args.voxel_size_um,
        target_um=args.target_um,
        skeleton_volume=skeleton_volume,
    )
    nonempty = [values for _, values in measurements_by_slice if values.size]
    if not nonempty:
        raise ValueError(
            "no valid strut-shaft measurements were found in the sampled slices"
        )
    all_measurements = np.concatenate(nonempty)

    percentages = _classify(all_measurements, lower_um, upper_um)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    curve_path = args.output_dir / "thickness_percentile_curve.png"
    box_path = args.output_dir / "thickness_box_plot.png"
    cdf_path = args.output_dir / "thickness_cdf.png"
    high_outliers_path = args.output_dir / "high_thickness_outliers.md"
    low_outliers_path = args.output_dir / "low_thickness_outliers.md"
    obsolete_cdf_box_path = args.output_dir / "thickness_cdf_box_plot.png"
    thickness_summary_path = args.output_dir / "thickness_summary.md"
    obsolete_csv_path = args.output_dir / "thickness_by_slice.csv"
    obsolete_bars_path = args.output_dir / "thickness_accuracy_bars.png"
    if obsolete_csv_path.exists():
        obsolete_csv_path.unlink()
    if obsolete_bars_path.exists():
        obsolete_bars_path.unlink()
    if obsolete_cdf_box_path.exists():
        obsolete_cdf_box_path.unlink()

    _plot_percentile_curve(
        curve_path, all_measurements, args.target_um, lower_um, upper_um
    )
    _plot_box(box_path, all_measurements)
    _plot_cdf(cdf_path, all_measurements)
    _write_thickness_summary(
        path=thickness_summary_path,
        input_tiff=args.input_tiff,
        sampled_slice_count=len(sampled_indices),
        total_slice_count=volume.shape[0],
        measurements_um=all_measurements,
        voxel_size_um=args.voxel_size_um,
        target_um=args.target_um,
        lower_um=lower_um,
        upper_um=upper_um,
        percentages=percentages,
    )
    _write_high_thickness_outliers(
        path=high_outliers_path,
        input_tiff=args.input_tiff,
        measurements_by_slice=measurements_by_slice,
        total_slice_count=volume.shape[0],
    )
    _write_low_thickness_outliers(
        path=low_outliers_path,
        input_tiff=args.input_tiff,
        measurements_by_slice=measurements_by_slice,
        total_slice_count=volume.shape[0],
    )

    defect_counts = None
    defect_csv_path = None
    defect_summary_path = None
    if args.registered_json is not None:
        junctions, struts = _load_registered_design(args.registered_json)
        defect_rows = classify_expected_struts(
            volume=volume,
            junctions=junctions,
            struts=struts,
            input_is_mask=input_is_mask,
            threshold=args.threshold,
            search_radius_voxels=args.search_radius_voxels,
        )
        defect_csv_path = args.output_dir / "strut_defects.csv"
        defect_summary_path = args.output_dir / "defect_summary.md"
        _write_csv(defect_csv_path, DEFECT_CSV_FIELDS, defect_rows)
        defect_counts = _write_defect_summary(
            path=defect_summary_path,
            input_tiff=args.input_tiff,
            registered_json=args.registered_json,
            rows=defect_rows,
            search_radius_voxels=args.search_radius_voxels,
            voxel_size_um=args.voxel_size_um,
        )

    print(f"Sampled {len(sampled_indices)} of {volume.shape[0]} Z slices.")
    print(
        f"Measured {all_measurements.size} shaft-centerline locations "
        f"using a {halo_voxels}-voxel 3D halo."
    )
    print(f"Too thin (< {lower_um:g} µm): {percentages[0]:.2f}%")
    print(
        f"Accurate ({lower_um:g}–{upper_um:g} µm): "
        f"{percentages[1]:.2f}%"
    )
    print(f"Too thick (> {upper_um:g} µm): {percentages[2]:.2f}%")
    print(f"Saved {curve_path}")
    print(f"Saved {box_path}")
    print(f"Saved {cdf_path}")
    print(f"Saved {thickness_summary_path}")
    print(f"Saved {high_outliers_path}")
    print(f"Saved {low_outliers_path}")
    if defect_counts is not None:
        total_struts = sum(defect_counts.values())
        print(
            f"Expected-strut comparison: {defect_counts['missing']} missing "
            f"({100.0 * defect_counts['missing'] / total_struts:.2f}%), "
            f"{defect_counts['broken']} broken "
            f"({100.0 * defect_counts['broken'] / total_struts:.2f}%)."
        )
        print(f"Saved {defect_csv_path}")
        print(f"Saved {defect_summary_path}")


def main() -> None:
    args = build_parser().parse_args()
    run_analysis(args)


if __name__ == "__main__":
    main()
