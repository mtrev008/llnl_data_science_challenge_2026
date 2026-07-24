from __future__ import annotations

import argparse
import csv
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import tifffile


# Numeric identifiers are validated, but they are excluded from averages and plots.
IDENTIFIER_KEYS = {
    "id",
    "junction0",
    "junction1",
    "source",
    "target",
    "node0",
    "node1",
    "start_node",
    "end_node",
}

JUNCTION_NAMES = ("junctions", "nodes", "vertices")
STRUT_NAMES = ("struts", "edges")
UNIT_CELL_NAMES = ("unit_cells", "cells")


def is_number(value: Any) -> bool:
    """Return True for finite numeric values, excluding booleans."""
    return (
        isinstance(value, (int, float, np.integer, np.floating))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def should_skip_key(key: str) -> bool:
    """Skip identifiers when calculating scientific statistics."""
    normalized = key.lower().strip()
    return (
        normalized in IDENTIFIER_KEYS
        or normalized.endswith("_id")
        or normalized.endswith("_ids")
    )


def safe_filename(text: str) -> str:
    """Convert a collection or field name into a safe filename."""
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", text).strip("._") or "field"


def find_collection(
    data: dict[str, Any],
    possible_names: tuple[str, ...],
) -> tuple[str | None, list[Any]]:
    """Find the first list collection matching one of the supplied names."""
    for name in possible_names:
        value = data.get(name)
        if isinstance(value, list):
            return name, value
    return None, []


def flatten_numeric_record(
    record: dict[str, Any],
    prefix: str = "",
) -> dict[str, float]:
    """
    Convert one JSON record into meaningful numeric parameters.

    Examples
    --------
    position: [x, y, z] -> position.x, position.y, position.z
    indices: [i, j, k] -> indices.i, indices.j, indices.k
    struts: [12, 13, 14] -> struts.__length__
    """
    output: dict[str, float] = {}

    for key, value in record.items():
        if should_skip_key(key):
            continue

        path = f"{prefix}.{key}" if prefix else key

        if is_number(value):
            output[path] = float(value)
            continue

        if isinstance(value, dict):
            output.update(flatten_numeric_record(value, path))
            continue

        if isinstance(value, (list, tuple)):
            # Split short 3D numeric arrays into named components.
            if len(value) == 3 and all(is_number(item) for item in value):
                lowered = key.lower()
                if any(
                    word in lowered
                    for word in ("position", "coordinate", "point", "location")
                ):
                    labels = ("x", "y", "z")
                else:
                    labels = ("i", "j", "k")

                for label, item in zip(labels, value):
                    output[f"{path}.{label}"] = float(item)
            else:
                # Long arrays commonly contain IDs. Their length is meaningful;
                # their arithmetic mean generally is not.
                output[f"{path}.__length__"] = float(len(value))

    return output


def descriptive_statistics(
    values: list[float],
    record_count: int,
) -> dict[str, Any]:
    """Calculate descriptive statistics for one numeric parameter."""
    array = np.asarray(values, dtype=np.float64)
    counts = Counter(array.tolist())
    most_common = counts.most_common()

    mode: float | None = None
    mode_count = 0

    if most_common:
        mode_count = most_common[0][1]
        tied_modes = sum(
            1 for _, count in most_common if count == mode_count
        )

        # Do not report a misleading mode when every value is unique or tied.
        if mode_count > 1 and tied_modes == 1:
            mode = float(most_common[0][0])

    return {
        "count": int(array.size),
        "missing_count": int(record_count - array.size),
        "minimum": float(np.min(array)),
        "maximum": float(np.max(array)),
        "mean": float(np.mean(array)),
        "median": float(np.median(array)),
        "mode": mode,
        "mode_count": int(mode_count),
        "standard_deviation": float(np.std(array)),
        "p05": float(np.percentile(array, 5)),
        "p25": float(np.percentile(array, 25)),
        "p75": float(np.percentile(array, 75)),
        "p95": float(np.percentile(array, 95)),
        "unique_count": int(np.unique(array).size),
    }


def save_distribution_plot(
    values: list[float],
    title: str,
    output_path: Path,
) -> None:
    """Save a bar chart for discrete values or a histogram otherwise."""
    array = np.asarray(values, dtype=np.float64)
    unique_count = np.unique(array).size

    plt.figure(figsize=(9, 5))

    if unique_count <= 20:
        unique, counts = np.unique(array, return_counts=True)
        plt.bar(unique, counts)
    else:
        bin_count = min(50, max(10, int(np.sqrt(array.size))))
        plt.hist(array, bins=bin_count)

    plt.xlabel("Value")
    plt.ylabel("Frequency")
    plt.title(title)
    plt.tight_layout()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=150)
    plt.close()


def write_json_statistics_csv(
    rows: list[dict[str, Any]],
    output_path: Path,
) -> None:
    """Write flattened JSON statistics to CSV."""
    if not rows:
        return

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def profile_json(
    json_path: Path,
    plot_directory: Path,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Validate and statistically profile a lattice JSON file."""
    with json_path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise ValueError("The top-level JSON value must be an object.")

    result: dict[str, Any] = {
        "path": str(json_path.resolve()),
        "top_level_keys": list(data.keys()),
        "collections": {},
        "graph_validation": {},
    }

    csv_rows: list[dict[str, Any]] = []

    # Profile every top-level list that contains dictionary records.
    for collection_name, collection in data.items():
        if not isinstance(collection, list):
            continue

        records = [item for item in collection if isinstance(item, dict)]
        if not records:
            continue

        values_by_field: dict[str, list[float]] = defaultdict(list)

        for record in records:
            flattened = flatten_numeric_record(record)
            for field, value in flattened.items():
                values_by_field[field].append(value)

        parameter_statistics: dict[str, Any] = {}

        for field, values in sorted(values_by_field.items()):
            stats = descriptive_statistics(values, len(records))
            parameter_statistics[field] = stats

            csv_rows.append(
                {
                    "collection": collection_name,
                    "field": field,
                    **stats,
                }
            )

            save_distribution_plot(
                values=values,
                title=f"{collection_name}: {field}",
                output_path=(
                    plot_directory
                    / f"{safe_filename(collection_name)}__{safe_filename(field)}.png"
                ),
            )

        result["collections"][collection_name] = {
            "record_count": len(records),
            "numeric_parameter_count": len(parameter_statistics),
            "parameters": parameter_statistics,
        }

    # Perform graph-specific validation.
    junction_key, junctions = find_collection(data, JUNCTION_NAMES)
    strut_key, struts = find_collection(data, STRUT_NAMES)
    unit_cell_key, unit_cells = find_collection(data, UNIT_CELL_NAMES)

    junction_id_list = [
        record.get("id")
        for record in junctions
        if isinstance(record, dict) and "id" in record
    ]
    strut_id_list = [
        record.get("id")
        for record in struts
        if isinstance(record, dict) and "id" in record
    ]

    junction_ids = set(junction_id_list)
    node_degree: Counter[Any] = Counter()
    invalid_references = 0
    self_connections = 0
    duplicate_edges = 0
    seen_edges: set[tuple[str, str]] = set()

    for strut in struts:
        if not isinstance(strut, dict):
            continue

        endpoint0 = strut.get("junction0")
        endpoint1 = strut.get("junction1")

        if endpoint0 not in junction_ids or endpoint1 not in junction_ids:
            invalid_references += 1
            continue

        if endpoint0 == endpoint1:
            self_connections += 1

        edge = tuple(sorted((str(endpoint0), str(endpoint1))))
        if edge in seen_edges:
            duplicate_edges += 1
        else:
            seen_edges.add(edge)

        node_degree[endpoint0] += 1
        node_degree[endpoint1] += 1

    degree_values = [float(value) for value in node_degree.values()]
    degree_statistics = None

    if degree_values:
        degree_statistics = descriptive_statistics(
            values=degree_values,
            record_count=len(junction_ids),
        )

        save_distribution_plot(
            values=degree_values,
            title="Junction degree distribution",
            output_path=plot_directory / "junction_degree_distribution.png",
        )

    result["graph_validation"] = {
        "junction_collection": junction_key,
        "strut_collection": strut_key,
        "unit_cell_collection": unit_cell_key,
        "junction_count": len(junctions),
        "strut_count": len(struts),
        "unit_cell_count": len(unit_cells),
        "duplicate_junction_id_count": (
            len(junction_id_list) - len(set(junction_id_list))
        ),
        "duplicate_strut_id_count": (
            len(strut_id_list) - len(set(strut_id_list))
        ),
        "invalid_reference_count": invalid_references,
        "self_connection_count": self_connections,
        "duplicate_endpoint_pair_count": duplicate_edges,
        "node_degree_statistics": degree_statistics,
    }

    return result, csv_rows


def histogram_percentile(
    histogram: np.ndarray,
    percentile: float,
) -> int:
    """Read a percentile from an integer intensity histogram."""
    cumulative = np.cumsum(histogram)
    target = percentile / 100.0 * cumulative[-1]
    return int(np.searchsorted(cumulative, target, side="left"))


def profile_tiff(
    tiff_path: Path,
    plot_directory: Path,
    csv_directory: Path,
) -> dict[str, Any]:
    """
    Profile a uint8 or uint16 TIFF one page at a time.

    The full CT volume is never loaded into memory. An exact integer
    histogram is accumulated while each slice is read. This is extra information
    """
    with tifffile.TiffFile(tiff_path) as tif:
        if not tif.series:
            raise ValueError("The TIFF contains no image series.")

        series = tif.series[0]
        pages = tif.pages
        first_page = pages[0]
        dtype = np.dtype(series.dtype)

        if dtype.kind != "u" or dtype.itemsize > 2:
            raise ValueError(
                "This example calculates exact streaming statistics for "
                "uint8 and uint16 TIFF data."
            )

        histogram = np.zeros(np.iinfo(dtype).max + 1, dtype=np.int64)
        slice_rows: list[dict[str, Any]] = []
        page_shapes: set[tuple[int, ...]] = set()
        page_dtypes: set[str] = set()

        for slice_index, page in enumerate(pages):
            image = page.asarray()
            page_shapes.add(tuple(image.shape))
            page_dtypes.add(str(image.dtype))

            histogram += np.bincount(
                image.ravel(),
                minlength=histogram.size,
            )

            slice_rows.append(
                {
                    "slice_index": slice_index,
                    "minimum": int(np.min(image)),
                    "maximum": int(np.max(image)),
                    "mean": float(np.mean(image)),
                    "standard_deviation": float(np.std(image)),
                    "zero_fraction": float(np.mean(image == 0)),
                    "is_constant": bool(np.all(image == image.flat[0])),
                }
            )

        total_voxels = int(histogram.sum())
        intensity_values = np.arange(histogram.size, dtype=np.float64)
        occupied_bins = np.flatnonzero(histogram)

        mean = float(
            np.dot(intensity_values, histogram) / total_voxels
        )
        variance = float(
            np.dot((intensity_values - mean) ** 2, histogram)
            / total_voxels
        )

        intensity_statistics = {
            "count": total_voxels,
            "minimum": int(occupied_bins[0]),
            "maximum": int(occupied_bins[-1]),
            "mean": mean,
            "median": histogram_percentile(histogram, 50),
            "mode": int(np.argmax(histogram)),
            "standard_deviation": math.sqrt(variance),
            "p01": histogram_percentile(histogram, 1),
            "p05": histogram_percentile(histogram, 5),
            "p25": histogram_percentile(histogram, 25),
            "p75": histogram_percentile(histogram, 75),
            "p95": histogram_percentile(histogram, 95),
            "p99": histogram_percentile(histogram, 99),
            "zero_fraction": float(histogram[0] / total_voxels),
        }

        # Global intensity plot.
        plot_directory.mkdir(parents=True, exist_ok=True)
        present = histogram > 0

        plt.figure(figsize=(10, 5))
        plt.plot(np.flatnonzero(present), histogram[present])
        plt.xlabel("Intensity")
        plt.ylabel("Voxel count")
        plt.title("TIFF intensity distribution")
        plt.tight_layout()
        plt.savefig(
            plot_directory / "tiff_intensity_distribution.png",
            dpi=150,
        )
        plt.close()

        # Per-slice trend plots.
        slice_indices = [row["slice_index"] for row in slice_rows]
        slice_means = [row["mean"] for row in slice_rows]
        slice_standard_deviations = [
            row["standard_deviation"] for row in slice_rows
        ]

        plt.figure(figsize=(10, 5))
        plt.plot(slice_indices, slice_means)
        plt.xlabel("Z slice")
        plt.ylabel("Mean intensity")
        plt.title("Mean intensity by slice")
        plt.tight_layout()
        plt.savefig(plot_directory / "tiff_slice_mean.png", dpi=150)
        plt.close()

        plt.figure(figsize=(10, 5))
        plt.plot(slice_indices, slice_standard_deviations)
        plt.xlabel("Z slice")
        plt.ylabel("Intensity standard deviation")
        plt.title("Intensity variation by slice")
        plt.tight_layout()
        plt.savefig(
            plot_directory / "tiff_slice_standard_deviation.png",
            dpi=150,
        )
        plt.close()

        csv_directory.mkdir(parents=True, exist_ok=True)
        with (csv_directory / "tiff_slice_statistics.csv").open(
            "w",
            newline="",
            encoding="utf-8",
        ) as file:
            writer = csv.DictWriter(
                file,
                fieldnames=list(slice_rows[0].keys()),
            )
            writer.writeheader()
            writer.writerows(slice_rows)

        return {
            "path": str(tiff_path.resolve()),
            "shape": list(series.shape),
            "axes": series.axes,
            "dtype": str(series.dtype),
            "page_count": len(pages),
            "series_count": len(tif.series),
            "bits_per_sample": str(first_page.bitspersample),
            "compression": first_page.compression.name,
            "all_pages_same_shape": len(page_shapes) == 1,
            "all_pages_same_dtype": len(page_dtypes) == 1,
            "blank_or_constant_slice_count": int(
                sum(row["is_constant"] for row in slice_rows)
            ),
            "intensity_statistics": intensity_statistics,
        }


def extract_junction_positions(
    json_path: Path,
) -> np.ndarray | None:
    """Extract recognized XYZ junction coordinates for a bounds check."""
    with json_path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    _, junctions = find_collection(data, JUNCTION_NAMES)
    positions: list[list[float]] = []

    for junction in junctions:
        if not isinstance(junction, dict):
            continue

        coordinate = None

        for key in ("position", "coordinates", "coordinate", "point"):
            candidate = junction.get(key)
            if (
                isinstance(candidate, (list, tuple))
                and len(candidate) == 3
                and all(is_number(item) for item in candidate)
            ):
                coordinate = candidate
                break

        if coordinate is None and all(
            key in junction for key in ("x", "y", "z")
        ):
            candidate = [junction["x"], junction["y"], junction["z"]]
            if all(is_number(item) for item in candidate):
                coordinate = candidate

        if coordinate is not None:
            positions.append([float(item) for item in coordinate])

    if not positions:
        return None

    return np.asarray(positions, dtype=np.float64)


def cross_validate_tiff_json(
    tiff_result: dict[str, Any],
    json_path: Path,
) -> dict[str, Any]:
    """Test whether JSON coordinates numerically fit the TIFF bounds."""
    positions_xyz = extract_junction_positions(json_path)

    if positions_xyz is None:
        return {
            "coordinate_check_available": False,
            "warning": "No recognizable junction XYZ coordinates were found.",
        }

    shape_zyx = np.asarray(tiff_result["shape"], dtype=np.float64)
    minimum_xyz = positions_xyz.min(axis=0)
    maximum_xyz = positions_xyz.max(axis=0)

    xyz_to_zyx_fits = bool(
        np.all(minimum_xyz[::-1] >= 0)
        and np.all(maximum_xyz[::-1] < shape_zyx)
    )

    already_zyx_fits = bool(
        np.all(minimum_xyz >= 0)
        and np.all(maximum_xyz < shape_zyx)
    )

    return {
        "coordinate_check_available": True,
        "json_minimum_xyz": minimum_xyz.tolist(),
        "json_maximum_xyz": maximum_xyz.tolist(),
        "plausible_xyz_voxel_coordinates": xyz_to_zyx_fits,
        "plausible_zyx_voxel_coordinates": already_zyx_fits,
        "note": (
            "This is only a numerical bounds check. It does not prove that "
            "the graph is correctly registered to the CT material."
        ),
    }


def profile_stl(stl_path: Path) -> dict[str, Any]:
    """Profile an optional STL using Trimesh."""
    try:
        import trimesh
    except ImportError as error:
        raise RuntimeError(
            "STL profiling requires Trimesh: pip install trimesh"
        ) from error

    loaded = trimesh.load(stl_path, force="scene")

    if isinstance(loaded, trimesh.Scene):
        if not loaded.geometry:
            raise ValueError("The STL contains no geometry.")
        mesh = trimesh.util.concatenate(tuple(loaded.geometry.values()))
    else:
        mesh = loaded

    return {
        "path": str(stl_path.resolve()),
        "vertex_count": int(len(mesh.vertices)),
        "triangle_count": int(len(mesh.faces)),
        "watertight": bool(mesh.is_watertight),
        "surface_area": float(mesh.area),
        "volume": float(abs(mesh.volume)) if mesh.is_watertight else None,
        "bounds_xyz": np.asarray(mesh.bounds).tolist(),
        "dimensions_xyz": np.asarray(mesh.extents).tolist(),
        "connected_component_count": int(
            len(mesh.split(only_watertight=False))
        ),
        "degenerate_face_count": int(
            np.count_nonzero(mesh.area_faces == 0)
        ),
    }


def determine_decision(
    report: dict[str, Any],
) -> tuple[str, list[str], list[str]]:
    """Convert deterministic checks into PASS, PASS_WITH_WARNINGS, or FAIL."""
    errors: list[str] = []
    warnings: list[str] = []

    tiff = report["tiff"]
    graph = report["json"]["graph_validation"]
    cross_file = report["cross_file"]

    if not tiff["all_pages_same_shape"]:
        errors.append("TIFF pages do not all have the same shape.")

    if not tiff["all_pages_same_dtype"]:
        errors.append("TIFF pages do not all have the same data type.")

    if graph["junction_collection"] is None:
        errors.append("No recognized junction collection was found.")

    if graph["strut_collection"] is None:
        errors.append("No recognized strut collection was found.")

    if graph["invalid_reference_count"] > 0:
        errors.append("One or more struts reference nonexistent junctions.")

    if graph["duplicate_junction_id_count"] > 0:
        errors.append("Duplicate junction IDs were found.")

    if graph["duplicate_strut_id_count"] > 0:
        errors.append("Duplicate strut IDs were found.")

    if tiff["blank_or_constant_slice_count"] > 0:
        warnings.append("One or more TIFF slices are constant.")

    if not cross_file.get("coordinate_check_available", False):
        warnings.append("TIFF-to-JSON coordinate comparison was unavailable.")
    elif not cross_file["plausible_xyz_voxel_coordinates"]:
        warnings.append(
            "JSON XYZ coordinates do not fit directly inside the TIFF volume."
        )

    stl_result = report.get("stl")
    if stl_result and not stl_result["watertight"]:
        warnings.append(
            "The STL is not watertight, so its enclosed volume is unreliable."
        )

    if errors:
        return "FAIL", errors, warnings

    if warnings:
        return "PASS_WITH_WARNINGS", errors, warnings

    return "PASS", errors, warnings


def write_markdown_report(
    report: dict[str, Any],
    output_path: Path,
) -> None:
    """Write a compact human-readable report."""
    graph = report["json"]["graph_validation"]
    intensity = report["tiff"]["intensity_statistics"]
    cross_file = report["cross_file"]

    lines = [
        "# Data Validation and Profiling Report",
        "",
        f"**Decision:** {report['decision']}",
        "",
        "## TIFF",
        "",
        f"- Shape: `{report['tiff']['shape']}`",
        f"- Axes: `{report['tiff']['axes']}`",
        f"- Data type: `{report['tiff']['dtype']}`",
        f"- Pages: `{report['tiff']['page_count']}`",
        f"- Intensity minimum: `{intensity['minimum']}`",
        f"- Intensity maximum: `{intensity['maximum']}`",
        f"- Intensity mean: `{intensity['mean']:.3f}`",
        f"- Intensity median: `{intensity['median']}`",
        f"- Intensity mode: `{intensity['mode']}`",
        f"- Intensity standard deviation: "
        f"`{intensity['standard_deviation']:.3f}`",
        "",
        "## JSON graph",
        "",
        f"- Junctions: `{graph['junction_count']}`",
        f"- Struts: `{graph['strut_count']}`",
        f"- Unit cells: `{graph['unit_cell_count']}`",
        f"- Invalid references: `{graph['invalid_reference_count']}`",
        f"- Duplicate junction IDs: "
        f"`{graph['duplicate_junction_id_count']}`",
        f"- Duplicate strut IDs: `{graph['duplicate_strut_id_count']}`",
        "",
        "## Cross-file checks",
        "",
        f"- Plausible XYZ voxel coordinates: "
        f"`{cross_file.get('plausible_xyz_voxel_coordinates')}`",
        f"- Plausible ZYX voxel coordinates: "
        f"`{cross_file.get('plausible_zyx_voxel_coordinates')}`",
        "",
        "## Errors",
        "",
    ]

    lines.extend(
        [f"- {item}" for item in report["errors"]]
        if report["errors"]
        else ["- None"]
    )

    lines.extend(["", "## Warnings", ""])

    lines.extend(
        [f"- {item}" for item in report["warnings"]]
        if report["warnings"]
        else ["- None"]
    )

    output_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Validate and statistically profile lattice TIFF, JSON, "
            "and optional STL files."
        )
    )

    parser.add_argument("--tiff", required=True, help="Path to the CT TIFF.")
    parser.add_argument(
        "--json",
        required=True,
        help="Path to the registered lattice JSON.",
    )
    parser.add_argument("--stl", help="Optional path to an STL mesh.")
    parser.add_argument(
        "--output-dir",
        default="outputs/validation",
        help="Directory for reports, CSV files, and plots.",
    )

    args = parser.parse_args()

    tiff_path = Path(args.tiff)
    json_path = Path(args.json)
    stl_path = Path(args.stl) if args.stl else None
    output_directory = Path(args.output_dir)

    if not tiff_path.is_file():
        raise FileNotFoundError(f"TIFF not found: {tiff_path}")

    if not json_path.is_file():
        raise FileNotFoundError(f"JSON not found: {json_path}")

    if stl_path is not None and not stl_path.is_file():
        raise FileNotFoundError(f"STL not found: {stl_path}")

    plot_directory = output_directory / "plots"
    csv_directory = output_directory / "csv"
    output_directory.mkdir(parents=True, exist_ok=True)

    tiff_result = profile_tiff(
        tiff_path=tiff_path,
        plot_directory=plot_directory,
        csv_directory=csv_directory,
    )

    json_result, json_csv_rows = profile_json(
        json_path=json_path,
        plot_directory=plot_directory,
    )

    write_json_statistics_csv(
        rows=json_csv_rows,
        output_path=csv_directory / "json_parameter_statistics.csv",
    )

    report: dict[str, Any] = {
        "inputs": {
            "tiff": str(tiff_path.resolve()),
            "json": str(json_path.resolve()),
            "stl": str(stl_path.resolve()) if stl_path else None,
        },
        "tiff": tiff_result,
        "json": json_result,
        "cross_file": cross_validate_tiff_json(
            tiff_result=tiff_result,
            json_path=json_path,
        ),
    }

    if stl_path is not None:
        report["stl"] = profile_stl(stl_path)

    decision, errors, warnings = determine_decision(report)
    report["decision"] = decision
    report["errors"] = errors
    report["warnings"] = warnings

    with (output_directory / "validation_report.json").open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(report, file, indent=2)

    write_markdown_report(
        report=report,
        output_path=output_directory / "validation_report.md",
    )

    print(f"Decision: {decision}")
    print(f"JSON report: {output_directory / 'validation_report.json'}")
    print(f"Markdown report: {output_directory / 'validation_report.md'}")
    print(f"Plots: {plot_directory}")
    print(f"CSV files: {csv_directory}")


if __name__ == "__main__":
    main()