"""Render a CT segmentation mask as a high-resolution digital-twin PNG."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import sys
import tempfile
from typing import Any

os.environ.setdefault(
    "MPLCONFIGDIR",
    str(Path(tempfile.gettempdir()) / "llnl-visualization-matplotlib"),
)

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
import numpy as np
from scipy import ndimage
import tifffile


MODEL_CMAP = LinearSegmentedColormap.from_list(
    "ct_surface_blue",
    ["#07182f", "#123b67", "#2f77a9", "#76b6d5", "#d8f0f7"],
)


def resolve_input(value: str) -> Path:
    path = Path(value).expanduser().resolve()
    if not path.is_file():
        raise ValueError(f"Input mask does not exist: {path}")
    if path.suffix.lower() not in {".tif", ".tiff"}:
        raise ValueError("Input mask must be a TIFF")
    return path


def resolve_output(value: str, overwrite: bool) -> Path:
    path = Path(value).expanduser().resolve()
    if path.suffix.lower() != ".png":
        raise ValueError("Output must use .png")
    if path.exists() and not overwrite:
        raise ValueError(f"Output already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def validate_spacing(values: tuple[float, float, float]) -> tuple[float, float, float]:
    spacing = tuple(float(value) for value in values)
    if len(spacing) != 3 or not all(math.isfinite(value) and value > 0 for value in spacing):
        raise ValueError("voxel_size_xyz must contain three positive finite values")
    return spacing


def pool_xy(binary: np.ndarray, factor: int) -> np.ndarray:
    y_size, x_size = binary.shape
    y_pad = (-y_size) % factor
    x_pad = (-x_size) % factor
    padded = np.pad(binary, ((0, y_pad), (0, x_pad)), mode="constant")
    return padded.reshape(
        padded.shape[0] // factor,
        factor,
        padded.shape[1] // factor,
        factor,
    ).max(axis=(1, 3))


def inspect_and_reduce(
    path: Path,
    threshold: float,
    factor: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, dict[str, Any]]:
    if factor < 1:
        raise ValueError("display reduction factor must be positive")
    with tifffile.TiffFile(path) as tiff:
        shape = tuple(int(value) for value in tiff.series[0].shape)
        if len(shape) != 3:
            raise ValueError(f"Expected a 3D mask, got shape {shape}")
        z_size, y_size, x_size = shape
        reduced_shape = (
            math.ceil(z_size / factor),
            math.ceil(y_size / factor),
            math.ceil(x_size / factor),
        )
        reduced = np.zeros(reduced_shape, dtype=bool)
        xy = np.zeros((y_size, x_size), dtype=bool)
        xz = np.zeros((z_size, x_size), dtype=bool)
        yz = np.zeros((z_size, y_size), dtype=bool)
        foreground = 0
        z_bucket: list[np.ndarray] = []
        reduced_z = 0
        for z_index, page in enumerate(tiff.pages):
            binary = np.asarray(page.asarray() > threshold, dtype=bool)
            foreground += int(np.count_nonzero(binary))
            xy |= binary
            xz[z_index] = np.any(binary, axis=0)
            yz[z_index] = np.any(binary, axis=1)
            z_bucket.append(pool_xy(binary, factor))
            if len(z_bucket) == factor or z_index == z_size - 1:
                reduced[reduced_z] = np.logical_or.reduce(z_bucket)
                z_bucket.clear()
                reduced_z += 1
    total = int(np.prod(shape, dtype=np.int64))
    return reduced, xy, xz, yz, {
        "source_shape_zyx": list(shape),
        "source_foreground_voxels": foreground,
        "source_background_voxels": total - foreground,
        "source_foreground_fraction": foreground / total,
        "display_reduction_factor": factor,
        "display_reduction_method": "3d_max_pool",
        "reduced_shape_zyx": list(reduced.shape),
        "scientific_sampling": False,
        "display_reduced": factor > 1,
        "orthogonal_projection_coverage": 1.0,
    }


def perspective_depth_image(
    reduced: np.ndarray,
    canvas_size: int,
) -> tuple[np.ndarray, dict[str, Any], dict[str, Any]]:
    surface = reduced & ~ndimage.binary_erosion(
        reduced,
        structure=ndimage.generate_binary_structure(3, 1),
        border_value=0,
    )
    coordinates = np.argwhere(surface).astype(np.float32)
    if not len(coordinates):
        raise ValueError("Reduced mask contains no surface voxels")
    max_points = 4_000_000
    point_stride = max(1, int(math.ceil(len(coordinates) / max_points)))
    coordinates = coordinates[::point_stride]

    xyz = coordinates[:, [2, 1, 0]]
    xyz -= (np.asarray(reduced.shape[::-1], dtype=np.float32) - 1.0) / 2.0
    azimuth = np.deg2rad(-43.0)
    elevation = np.deg2rad(24.0)
    rotate_z = np.array([
        [np.cos(azimuth), -np.sin(azimuth), 0.0],
        [np.sin(azimuth), np.cos(azimuth), 0.0],
        [0.0, 0.0, 1.0],
    ], dtype=np.float32)
    rotate_x = np.array([
        [1.0, 0.0, 0.0],
        [0.0, np.cos(elevation), -np.sin(elevation)],
        [0.0, np.sin(elevation), np.cos(elevation)],
    ], dtype=np.float32)
    rotated = xyz @ rotate_z.T @ rotate_x.T
    horizontal = rotated[:, 0]
    vertical = rotated[:, 2]
    depth = rotated[:, 1]

    margin = 30
    width = canvas_size - 2 * margin
    h_range = float(np.ptp(horizontal)) or 1.0
    v_range = float(np.ptp(vertical)) or 1.0
    scale = min(width / h_range, width / v_range)
    px = np.clip(
        np.rint((horizontal - horizontal.min()) * scale + margin).astype(np.int32),
        0,
        canvas_size - 1,
    )
    py = np.clip(
        np.rint((vertical - vertical.min()) * scale + margin).astype(np.int32),
        0,
        canvas_size - 1,
    )
    flat = (canvas_size - 1 - py) * canvas_size + px
    buffer = np.full(canvas_size * canvas_size, -np.inf, dtype=np.float32)
    np.maximum.at(buffer, flat, depth)
    image = buffer.reshape((canvas_size, canvas_size))
    occupied = np.isfinite(image)
    image[~occupied] = np.nan
    finite = image[occupied]
    normalized = (image - finite.min()) / max(float(finite.max() - finite.min()), 1e-6)
    normalized = ndimage.grey_dilation(
        np.nan_to_num(normalized, nan=-1.0),
        size=(3, 3),
    )
    normalized[normalized < 0] = np.nan
    return normalized, {
        "surface_voxels_reduced": int(np.count_nonzero(surface)),
        "perspective_points_rendered": int(len(coordinates)),
        "perspective_point_stride": point_stride,
        "perspective_canvas": [canvas_size, canvas_size],
        "view_azimuth_degrees": -43.0,
        "view_elevation_degrees": 24.0,
    }, {
        "reduced_shape_zyx": np.asarray(reduced.shape, dtype=np.float32),
        "rotate_z": rotate_z,
        "rotate_x": rotate_x,
        "horizontal_min": float(horizontal.min()),
        "vertical_min": float(vertical.min()),
        "scale": float(scale),
        "margin": margin,
        "canvas_size": canvas_size,
    }


def load_anomalies(
    value: str | None,
    source_shape_zyx: tuple[int, int, int],
) -> tuple[Path | None, list[dict[str, Any]], dict[str, Any]]:
    if value is None:
        return None, [], {
            "anomaly_count": 0,
            "anomaly_counts_by_classification": {},
            "out_of_bounds_anomaly_count": 0,
        }
    path = Path(value).expanduser().resolve()
    if not path.is_file():
        raise ValueError(f"Anomaly CSV does not exist: {path}")
    required = {"z", "y", "x", "classification"}
    records: list[dict[str, Any]] = []
    out_of_bounds = 0
    counts: dict[str, int] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None or not required.issubset(reader.fieldnames):
            raise ValueError(
                "Anomaly CSV must contain z, y, x, and classification columns"
            )
        for row_index, row in enumerate(reader):
            try:
                zyx = np.array(
                    [float(row["z"]), float(row["y"]), float(row["x"])],
                    dtype=np.float64,
                )
            except (TypeError, ValueError) as error:
                raise ValueError(
                    f"Anomaly row {row_index + 2} has invalid coordinates"
                ) from error
            if not np.isfinite(zyx).all():
                raise ValueError(
                    f"Anomaly row {row_index + 2} has nonfinite coordinates"
                )
            in_bounds = bool(
                np.all(zyx >= 0)
                and np.all(zyx < np.asarray(source_shape_zyx, dtype=float))
            )
            if not in_bounds:
                out_of_bounds += 1
                continue
            classification = str(row["classification"]).strip() or "unknown"
            counts[classification] = counts.get(classification, 0) + 1
            records.append({
                "zyx": zyx,
                "classification": classification,
                "source_id": row.get("strut_id", str(row_index)),
            })
    return path, records, {
        "anomaly_count": len(records),
        "anomaly_counts_by_classification": counts,
        "out_of_bounds_anomaly_count": out_of_bounds,
    }


def project_anomalies_to_perspective(
    anomalies: list[dict[str, Any]],
    reduction_factor: int,
    transform: dict[str, Any],
) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    projected: dict[str, list[tuple[float, float]]] = {}
    for anomaly in anomalies:
        reduced_zyx = anomaly["zyx"] / reduction_factor
        xyz = reduced_zyx[[2, 1, 0]].astype(np.float32)
        xyz -= (transform["reduced_shape_zyx"][::-1] - 1.0) / 2.0
        rotated = xyz @ transform["rotate_z"].T @ transform["rotate_x"].T
        px = (
            (rotated[0] - transform["horizontal_min"]) * transform["scale"]
            + transform["margin"]
        )
        py_up = (
            (rotated[2] - transform["vertical_min"]) * transform["scale"]
            + transform["margin"]
        )
        py = transform["canvas_size"] - 1 - py_up
        projected.setdefault(anomaly["classification"], []).append((px, py))
    return {
        classification: (
            np.asarray(points, dtype=float)[:, 0],
            np.asarray(points, dtype=float)[:, 1],
        )
        for classification, points in projected.items()
    }


ANOMALY_STYLES = {
    "missing": {
        "color": "#F58518",
        "marker": "o",
        "label": "missing strut candidate",
    },
    "potentially_broken": {
        "color": "#E45756",
        "marker": "^",
        "label": "potentially broken strut",
    },
}


def plot_anomaly_markers(
    axis: plt.Axes,
    x_values: np.ndarray,
    y_values: np.ndarray,
    classification: str,
    size: float,
    label: bool,
) -> None:
    style = ANOMALY_STYLES.get(
        classification,
        {"color": "#B279A2", "marker": "D", "label": classification},
    )
    axis.scatter(
        x_values,
        y_values,
        s=size,
        c=style["color"],
        marker=style["marker"],
        edgecolors="black",
        linewidths=0.8,
        alpha=0.95,
        label=style["label"] if label else None,
        zorder=10,
    )


def add_projection(
    axis: plt.Axes,
    projection: np.ndarray,
    title: str,
    horizontal_label: str,
    vertical_label: str,
    extent: tuple[float, float, float, float],
    anomalies: list[dict[str, Any]],
    horizontal_index: int,
    vertical_index: int,
    spacing: tuple[float, float, float],
) -> None:
    axis.imshow(
        projection,
        cmap="Blues",
        origin="lower",
        interpolation="nearest",
        extent=extent,
        aspect="equal",
    )
    axis.set_title(title, fontsize=12, fontweight="bold")
    axis.set_xlabel(horizontal_label)
    axis.set_ylabel(vertical_label)
    axis.grid(False)
    for classification in sorted({item["classification"] for item in anomalies}):
        selected = [item for item in anomalies if item["classification"] == classification]
        xyz = np.stack([item["zyx"][[2, 1, 0]] for item in selected])
        plot_anomaly_markers(
            axis,
            xyz[:, horizontal_index] * spacing[horizontal_index],
            xyz[:, vertical_index] * spacing[vertical_index],
            classification,
            size=46,
            label=False,
        )


def render_digital_twin(
    mask_filepath: str,
    output_filepath: str,
    voxel_size_xyz: tuple[float, float, float],
    units: str = "mm",
    threshold: float = 127.5,
    display_reduction_factor: int = 2,
    anomaly_csv: str | None = None,
    overwrite: bool = False,
) -> dict[str, Any]:
    source = resolve_input(mask_filepath)
    output = resolve_output(output_filepath, overwrite)
    spacing = validate_spacing(voxel_size_xyz)
    reduced, xy, xz, yz, statistics = inspect_and_reduce(
        source,
        threshold,
        display_reduction_factor,
    )
    perspective, perspective_stats, perspective_transform = perspective_depth_image(
        reduced,
        1500,
    )
    statistics.update(perspective_stats)
    z_size, y_size, x_size = statistics["source_shape_zyx"]
    anomaly_path, anomalies, anomaly_stats = load_anomalies(
        anomaly_csv,
        (z_size, y_size, x_size),
    )
    statistics.update(anomaly_stats)
    x_extent = x_size * spacing[0]
    y_extent = y_size * spacing[1]
    z_extent = z_size * spacing[2]

    fig = plt.figure(figsize=(16, 11), facecolor="#f6f8fb")
    grid = fig.add_gridspec(2, 3, width_ratios=(2.2, 1, 1), hspace=0.28, wspace=0.23)
    main = fig.add_subplot(grid[:, 0])
    main.imshow(perspective, cmap=MODEL_CMAP, origin="upper", interpolation="bilinear")
    main.set_title(
        "CT-Segmentation-Derived As-Built Surface Visual",
        fontsize=17,
        fontweight="bold",
        pad=14,
    )
    main.text(
        0.02,
        0.02,
        "Depth-shaded perspective • 2× max-pooled display geometry",
        transform=main.transAxes,
        color="white",
        fontsize=10,
        bbox={"facecolor": "#07182f", "alpha": 0.82, "pad": 6, "edgecolor": "none"},
    )
    main.axis("off")
    perspective_anomalies = project_anomalies_to_perspective(
        anomalies,
        display_reduction_factor,
        perspective_transform,
    )
    for classification, (marker_x, marker_y) in perspective_anomalies.items():
        plot_anomaly_markers(
            main,
            marker_x,
            marker_y,
            classification,
            size=90,
            label=True,
        )
    if anomalies:
        main.legend(
            loc="upper left",
            frameon=True,
            framealpha=0.9,
            fontsize=10,
        )

    add_projection(
        fig.add_subplot(grid[0, 1]),
        xy,
        "Full-resolution XY material projection",
        f"x ({units})",
        f"y ({units})",
        (0, x_extent, 0, y_extent),
        anomalies,
        0,
        1,
        spacing,
    )
    add_projection(
        fig.add_subplot(grid[0, 2]),
        xz,
        "Full-resolution XZ material projection",
        f"x ({units})",
        f"z ({units})",
        (0, x_extent, 0, z_extent),
        anomalies,
        0,
        2,
        spacing,
    )
    add_projection(
        fig.add_subplot(grid[1, 1]),
        yz,
        "Full-resolution YZ material projection",
        f"y ({units})",
        f"z ({units})",
        (0, y_extent, 0, z_extent),
        anomalies,
        1,
        2,
        spacing,
    )
    notes = fig.add_subplot(grid[1, 2])
    notes.axis("off")
    notes.text(
        0,
        1,
        "\n".join([
            "Traceability",
            "",
            f"Source: {source.name}",
            f"Shape ZYX: {z_size} × {y_size} × {x_size}",
            f"Voxel spacing XYZ: {spacing}",
            f"Displayed units: {units}",
            f"Mask threshold: {threshold}",
            f"Foreground: {statistics['source_foreground_fraction']:.3%}",
            f"Anomalies plotted: {statistics['anomaly_count']}",
            f"Out of bounds: {statistics['out_of_bounds_anomaly_count']}",
            "",
            "The perspective panel uses display-only",
            "2× max pooling. Orthogonal projections",
            "cover every source voxel.",
            "",
            "This is an as-built surface visual,",
            "not validated CAD or mechanics evidence.",
        ]),
        va="top",
        fontsize=11,
        linespacing=1.35,
        color="#172033",
    )
    fig.suptitle(
        "Missing-strut lattice digital-twin visualization",
        fontsize=20,
        fontweight="bold",
        y=0.985,
    )
    fig.savefig(output, dpi=200, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    if not output.is_file() or output.stat().st_size == 0:
        raise RuntimeError(f"PNG output was not written: {output}")
    return {
        "status": "success",
        "visualization_type": "ct_as_built_digital_twin_png",
        "input_paths": [
            str(source),
            *([str(anomaly_path)] if anomaly_path else []),
        ],
        "output_path": str(output),
        "parameters": {
            "source_axis_order": "ZYX",
            "output_coordinate_order": "XYZ",
            "voxel_size_xyz": list(spacing),
            "units": units,
            "mask_threshold": threshold,
            "display_reduction_factor": display_reduction_factor,
            "anomaly_coordinate_order": "ZYX",
        },
        "statistics": statistics,
        "warnings": [
            "Voxel calibration is supplied but not independently verified.",
            "The 3D perspective is display-reduced; orthogonal projections use full source coverage.",
            "Anomaly markers use CSV spatial coordinates; source IDs are not interpreted as registered-graph strut IDs.",
        ],
        "provenance": {
            "script": "render_ct_digital_twin.py",
            "scientific_sampling": False,
            "perspective_display_reduced": display_reduction_factor > 1,
            "orthogonal_projection_coverage": 1.0,
            "created_utc": datetime.now(timezone.utc).isoformat(),
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mask", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--voxel-size-x", type=float, required=True)
    parser.add_argument("--voxel-size-y", type=float, required=True)
    parser.add_argument("--voxel-size-z", type=float, required=True)
    parser.add_argument("--units", default="mm")
    parser.add_argument("--threshold", type=float, default=127.5)
    parser.add_argument("--display-reduction-factor", type=int, default=2)
    parser.add_argument("--anomalies")
    parser.add_argument("--overwrite", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        result = render_digital_twin(
            mask_filepath=args.mask,
            output_filepath=args.output,
            voxel_size_xyz=(
                args.voxel_size_x,
                args.voxel_size_y,
                args.voxel_size_z,
            ),
            units=args.units,
            threshold=args.threshold,
            display_reduction_factor=args.display_reduction_factor,
            anomaly_csv=args.anomalies,
            overwrite=args.overwrite,
        )
    except Exception as error:
        result = {
            "status": "error",
            "visualization_type": "ct_as_built_digital_twin_png",
            "input_paths": [],
            "output_path": None,
            "error_type": type(error).__name__,
            "error": str(error),
            "warnings": [],
        }
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "success" else 1


if __name__ == "__main__":
    sys.exit(main())
