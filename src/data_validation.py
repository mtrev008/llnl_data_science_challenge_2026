from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import tifffile


JUNCTION_COLLECTION_NAMES = (
    "junctions",
    "nodes",
    "vertices",
)

STRUT_COLLECTION_NAMES = (
    "struts",
    "edges",
)

UNIT_CELL_COLLECTION_NAMES = (
    "unit_cells",
    "cells",
)


def find_collection(
    data: dict[str, Any],
    possible_names: tuple[str, ...],
) -> tuple[str | None, list[Any]]:
    """
    Find a list-like JSON collection using several possible names.
    """

    for name in possible_names:
        value = data.get(name)

        if isinstance(value, list):
            return name, value

    return None, []


def extract_position(record: dict[str, Any]) -> list[float] | None:
    """
    Extract a three-dimensional coordinate from a junction record.

    Supported examples:
        {"position": [x, y, z]}
        {"coordinates": [x, y, z]}
        {"x": x, "y": y, "z": z}
    """

    for key in ("position", "coordinates", "coordinate", "point"):
        value = record.get(key)

        if isinstance(value, (list, tuple)) and len(value) == 3:
            try:
                return [float(item) for item in value]
            except (TypeError, ValueError):
                return None

    if all(key in record for key in ("x", "y", "z")):
        try:
            return [
                float(record["x"]),
                float(record["y"]),
                float(record["z"]),
            ]
        except (TypeError, ValueError):
            return None

    return None


def extract_endpoint_ids(
    strut: dict[str, Any],
) -> tuple[Any, Any] | None:
    """
    Extract the two endpoint junction IDs from a strut record.
    """

    endpoint_pairs = (
        ("junction0", "junction1"),
        ("start_node", "end_node"),
        ("node0", "node1"),
        ("source", "target"),
    )

    for first_key, second_key in endpoint_pairs:
        if first_key in strut and second_key in strut:
            return strut[first_key], strut[second_key]

    return None


def inspect_tiff(tiff_path: Path) -> dict[str, Any]:
    """
    Inspect a TIFF without loading the complete CT volume into memory.
    """

    errors: list[str] = []
    warnings: list[str] = []

    if not tiff_path.exists():
        return {
            "errors": [f"TIFF does not exist: {tiff_path}"],
            "warnings": [],
        }

    try:
        with tifffile.TiffFile(tiff_path) as tif:
            if not tif.series:
                return {
                    "errors": ["TIFF contains no image series."],
                    "warnings": [],
                }

            series = tif.series[0]
            first_page = tif.pages[0]

            page_shapes = {
                tuple(page.shape)
                for page in tif.pages
            }

            page_dtypes = {
                str(page.dtype)
                for page in tif.pages
            }

            if len(page_shapes) != 1:
                errors.append(
                    "TIFF pages do not all have the same shape."
                )

            if len(page_dtypes) != 1:
                errors.append(
                    "TIFF pages do not all have the same data type."
                )

            if len(series.shape) != 3:
                warnings.append(
                    f"Expected a 3D series but found shape {series.shape}."
                )

            if series.axes not in {"ZYX", "QYX"}:
                warnings.append(
                    f"Unexpected or ambiguous TIFF axes: {series.axes}"
                )

            if first_page.samplesperpixel != 1:
                warnings.append(
                    "TIFF has more than one sample per pixel. "
                    "It may be RGB rather than scalar CT data."
                )

            # Inspect only three pages to avoid loading the entire volume.
            page_count = len(tif.pages)
            sample_indices = sorted({
                0,
                page_count // 2,
                page_count - 1,
            })

            sampled_slices = []

            for index in sample_indices:
                image = tif.pages[index].asarray()

                sampled_slices.append({
                    "slice_index": index,
                    "minimum": float(np.min(image)),
                    "maximum": float(np.max(image)),
                    "mean": float(np.mean(image)),
                    "standard_deviation": float(np.std(image)),
                    "is_constant": bool(np.all(image == image.flat[0])),
                })

            blank_samples = [
                item["slice_index"]
                for item in sampled_slices
                if item["is_constant"]
            ]

            if blank_samples:
                warnings.append(
                    "One or more sampled slices were constant: "
                    f"{blank_samples}"
                )

            useful_tags = {}

            for tag_name in (
                "ImageWidth",
                "ImageLength",
                "BitsPerSample",
                "Compression",
                "PhotometricInterpretation",
                "XResolution",
                "YResolution",
                "ResolutionUnit",
                "Software",
                "ImageDescription",
            ):
                if tag_name in first_page.tags:
                    value = first_page.tags[tag_name].value
                    useful_tags[tag_name] = str(value)

            return {
                "path": str(tiff_path.resolve()),
                "file_size_bytes": tiff_path.stat().st_size,
                "shape": list(series.shape),
                "axes": series.axes,
                "dtype": str(series.dtype),
                "page_count": page_count,
                "series_count": len(tif.series),
                "is_bigtiff": bool(tif.is_bigtiff),
                "is_imagej": bool(tif.is_imagej),
                "is_ome": bool(tif.is_ome),
                "bits_per_sample": str(first_page.bitspersample),
                "samples_per_pixel": int(first_page.samplesperpixel),
                "compression": first_page.compression.name,
                "photometric": first_page.photometric.name,
                "all_pages_same_shape": len(page_shapes) == 1,
                "all_pages_same_dtype": len(page_dtypes) == 1,
                "sampled_slices": sampled_slices,
                "tags": useful_tags,
                "errors": errors,
                "warnings": warnings,
            }

    except tifffile.TiffFileError as error:
        return {
            "errors": [f"Invalid or unreadable TIFF: {error}"],
            "warnings": [],
        }


def inspect_json(json_path: Path) -> dict[str, Any]:
    """
    Inspect and validate the registered lattice JSON graph.
    """

    errors: list[str] = []
    warnings: list[str] = []

    if not json_path.exists():
        return {
            "errors": [f"JSON does not exist: {json_path}"],
            "warnings": [],
        }

    try:
        with json_path.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except json.JSONDecodeError as error:
        return {
            "errors": [f"Invalid JSON syntax: {error}"],
            "warnings": [],
        }

    if not isinstance(data, dict):
        return {
            "errors": ["Expected the top-level JSON value to be an object."],
            "warnings": [],
        }

    junction_key, junctions = find_collection(
        data,
        JUNCTION_COLLECTION_NAMES,
    )

    strut_key, struts = find_collection(
        data,
        STRUT_COLLECTION_NAMES,
    )

    unit_cell_key, unit_cells = find_collection(
        data,
        UNIT_CELL_COLLECTION_NAMES,
    )

    if not junctions:
        errors.append(
            "No junction, node, or vertex collection was found."
        )

    if not struts:
        errors.append(
            "No strut or edge collection was found."
        )

    junction_ids: set[Any] = set()
    duplicate_junction_ids: list[Any] = []
    positions: list[list[float]] = []

    for index, junction in enumerate(junctions):
        if not isinstance(junction, dict):
            errors.append(
                f"Junction record {index} is not a JSON object."
            )
            continue

        junction_id = junction.get("id")

        if junction_id is None:
            errors.append(
                f"Junction record {index} does not contain an id."
            )
        elif junction_id in junction_ids:
            duplicate_junction_ids.append(junction_id)
        else:
            junction_ids.add(junction_id)

        position = extract_position(junction)

        if position is None:
            warnings.append(
                f"Junction {junction_id} has no recognized XYZ position."
            )
        elif not np.all(np.isfinite(position)):
            errors.append(
                f"Junction {junction_id} contains non-finite coordinates."
            )
        else:
            positions.append(position)

    if duplicate_junction_ids:
        errors.append(
            "Duplicate junction IDs found: "
            f"{duplicate_junction_ids[:10]}"
        )

    strut_ids: set[Any] = set()
    duplicate_strut_ids: list[Any] = []
    invalid_references: list[Any] = []
    self_connections: list[Any] = []
    invalid_thicknesses: list[Any] = []
    duplicate_edges: list[Any] = []
    seen_edges: set[tuple[str, str]] = set()

    for index, strut in enumerate(struts):
        if not isinstance(strut, dict):
            errors.append(
                f"Strut record {index} is not a JSON object."
            )
            continue

        strut_id = strut.get("id")

        if strut_id is None:
            errors.append(
                f"Strut record {index} does not contain an id."
            )
        elif strut_id in strut_ids:
            duplicate_strut_ids.append(strut_id)
        else:
            strut_ids.add(strut_id)

        endpoints = extract_endpoint_ids(strut)

        if endpoints is None:
            errors.append(
                f"Strut {strut_id} has no recognized endpoint fields."
            )
            continue

        endpoint0, endpoint1 = endpoints

        if endpoint0 not in junction_ids or endpoint1 not in junction_ids:
            invalid_references.append(strut_id)

        if endpoint0 == endpoint1:
            self_connections.append(strut_id)

        normalized_edge = tuple(sorted(
            (str(endpoint0), str(endpoint1))
        ))

        if normalized_edge in seen_edges:
            duplicate_edges.append(strut_id)
        else:
            seen_edges.add(normalized_edge)

        if "thickness" in strut:
            try:
                thickness = float(strut["thickness"])

                if not np.isfinite(thickness) or thickness <= 0:
                    invalid_thicknesses.append(strut_id)
            except (TypeError, ValueError):
                invalid_thicknesses.append(strut_id)

    if duplicate_strut_ids:
        errors.append(
            "Duplicate strut IDs found: "
            f"{duplicate_strut_ids[:10]}"
        )

    if invalid_references:
        errors.append(
            f"{len(invalid_references)} struts reference missing junctions."
        )

    if self_connections:
        errors.append(
            f"{len(self_connections)} struts connect a junction to itself."
        )

    if invalid_thicknesses:
        errors.append(
            f"{len(invalid_thicknesses)} struts have invalid thickness."
        )

    if duplicate_edges:
        warnings.append(
            f"{len(duplicate_edges)} duplicate endpoint pairs were found. "
            "Verify whether these are intentional shared records."
        )

    coordinate_summary: dict[str, Any] | None = None

    if positions:
        position_array = np.asarray(positions, dtype=float)

        coordinate_summary = {
            "count": len(position_array),
            "minimum_xyz": position_array.min(axis=0).tolist(),
            "maximum_xyz": position_array.max(axis=0).tolist(),
            "mean_xyz": position_array.mean(axis=0).tolist(),
        }

    return {
        "path": str(json_path.resolve()),
        "top_level_keys": list(data.keys()),
        "junction_collection": junction_key,
        "strut_collection": strut_key,
        "unit_cell_collection": unit_cell_key,
        "junction_count": len(junctions),
        "strut_count": len(struts),
        "unit_cell_count": len(unit_cells),
        "duplicate_junction_id_count": len(duplicate_junction_ids),
        "duplicate_strut_id_count": len(duplicate_strut_ids),
        "invalid_reference_count": len(invalid_references),
        "self_connection_count": len(self_connections),
        "invalid_thickness_count": len(invalid_thicknesses),
        "duplicate_endpoint_pair_count": len(duplicate_edges),
        "coordinate_summary": coordinate_summary,
        "errors": errors,
        "warnings": warnings,
    }


def cross_validate(
    tiff_result: dict[str, Any],
    json_result: dict[str, Any],
) -> dict[str, Any]:
    """
    Perform TIFF-to-JSON compatibility checks.

    This function tests coordinate hypotheses but does not silently
    assume the coordinate unit or axis convention.
    """

    errors: list[str] = []
    warnings: list[str] = []

    shape = tiff_result.get("shape")
    coordinate_summary = json_result.get("coordinate_summary")

    result: dict[str, Any] = {
        "errors": errors,
        "warnings": warnings,
    }

    if not shape or len(shape) != 3:
        errors.append(
            "Cannot compare coordinates because TIFF shape is not 3D."
        )
        return result

    if coordinate_summary is None:
        warnings.append(
            "JSON coordinates were unavailable, so spatial compatibility "
            "could not be checked."
        )
        return result

    shape_zyx = np.asarray(shape, dtype=float)
    minimum_xyz = np.asarray(
        coordinate_summary["minimum_xyz"],
        dtype=float,
    )
    maximum_xyz = np.asarray(
        coordinate_summary["maximum_xyz"],
        dtype=float,
    )

    # Hypothesis 1:
    # JSON coordinates are XYZ voxel indices.
    minimum_zyx_from_xyz = minimum_xyz[::-1]
    maximum_zyx_from_xyz = maximum_xyz[::-1]

    xyz_voxel_hypothesis = bool(
        np.all(minimum_zyx_from_xyz >= 0)
        and np.all(maximum_zyx_from_xyz < shape_zyx)
    )

    # Hypothesis 2:
    # JSON coordinates are already ordered ZYX.
    zyx_voxel_hypothesis = bool(
        np.all(minimum_xyz >= 0)
        and np.all(maximum_xyz < shape_zyx)
    )

    result["tiff_shape_zyx"] = shape
    result["json_minimum_coordinates"] = minimum_xyz.tolist()
    result["json_maximum_coordinates"] = maximum_xyz.tolist()
    result["plausible_xyz_voxel_coordinates"] = xyz_voxel_hypothesis
    result["plausible_zyx_voxel_coordinates"] = zyx_voxel_hypothesis

    if not xyz_voxel_hypothesis and not zyx_voxel_hypothesis:
        warnings.append(
            "JSON coordinates do not fit directly inside the TIFF under "
            "either XYZ-voxel or ZYX-voxel assumptions. They may use "
            "physical units, an origin offset, or a different registration."
        )

    if xyz_voxel_hypothesis and zyx_voxel_hypothesis:
        warnings.append(
            "Both XYZ and ZYX voxel interpretations appear numerically "
            "possible. Axis order remains ambiguous."
        )

    return result


def determine_decision(
    sections: list[dict[str, Any]],
) -> str:
    """
    Return PASS, PASS_WITH_WARNINGS, or FAIL.
    """

    all_errors = [
        error
        for section in sections
        for error in section.get("errors", [])
    ]

    all_warnings = [
        warning
        for section in sections
        for warning in section.get("warnings", [])
    ]

    if all_errors:
        return "FAIL"

    if all_warnings:
        return "PASS_WITH_WARNINGS"

    return "PASS"


def write_markdown_report(
    report: dict[str, Any],
    output_path: Path,
) -> None:
    """
    Create a human-readable validation report.
    """

    tiff_data = report["tiff"]
    json_data = report["json"]
    cross_data = report["cross_file"]

    lines = [
        "# Dataset Validation Report",
        "",
        f"**Decision:** {report['decision']}",
        "",
        "## TIFF",
        "",
        f"- Shape: `{tiff_data.get('shape')}`",
        f"- Axes: `{tiff_data.get('axes')}`",
        f"- Data type: `{tiff_data.get('dtype')}`",
        f"- Pages: `{tiff_data.get('page_count')}`",
        "",
        "## JSON graph",
        "",
        f"- Junctions: `{json_data.get('junction_count')}`",
        f"- Struts: `{json_data.get('strut_count')}`",
        f"- Unit cells: `{json_data.get('unit_cell_count')}`",
        f"- Invalid references: "
        f"`{json_data.get('invalid_reference_count')}`",
        "",
        "## Cross-file checks",
        "",
        f"- Plausible XYZ voxel coordinates: "
        f"`{cross_data.get('plausible_xyz_voxel_coordinates')}`",
        f"- Plausible ZYX voxel coordinates: "
        f"`{cross_data.get('plausible_zyx_voxel_coordinates')}`",
        "",
        "## Errors",
        "",
    ]

    errors = report["all_errors"]

    if errors:
        lines.extend(f"- {error}" for error in errors)
    else:
        lines.append("- None")

    lines.extend([
        "",
        "## Warnings",
        "",
    ])

    warnings = report["all_warnings"]

    if warnings:
        lines.extend(f"- {warning}" for warning in warnings)
    else:
        lines.append("- None")

    output_path.write_text(
        "\n".join(lines),
        encoding="utf-8",
    )


def validate_dataset(
    tiff_path: Path,
    json_path: Path,
    output_directory: Path,
) -> dict[str, Any]:
    """
    Run the complete validation pipeline.
    """

    tiff_result = inspect_tiff(tiff_path)
    json_result = inspect_json(json_path)
    cross_result = cross_validate(tiff_result, json_result)

    sections = [
        tiff_result,
        json_result,
        cross_result,
    ]

    all_errors = [
        error
        for section in sections
        for error in section.get("errors", [])
    ]

    all_warnings = [
        warning
        for section in sections
        for warning in section.get("warnings", [])
    ]

    report = {
        "decision": determine_decision(sections),
        "tiff": tiff_result,
        "json": json_result,
        "cross_file": cross_result,
        "all_errors": all_errors,
        "all_warnings": all_warnings,
    }

    output_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    json_output = output_directory / "validation_report.json"
    markdown_output = output_directory / "validation_report.md"

    with json_output.open("w", encoding="utf-8") as file:
        json.dump(
            report,
            file,
            indent=2,
        )

    write_markdown_report(
        report,
        markdown_output,
    )

    return report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate an LLNL lattice TIFF and registered JSON."
    )

    parser.add_argument(
        "tiff_path",
        type=Path,
    )

    parser.add_argument(
        "json_path",
        type=Path,
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("outputs/validation"),
    )

    args = parser.parse_args()

    report = validate_dataset(
        args.tiff_path,
        args.json_path,
        args.output_dir,
    )

    print(f"Validation decision: {report['decision']}")
    print(f"Errors: {len(report['all_errors'])}")
    print(f"Warnings: {len(report['all_warnings'])}")
    print(f"Reports saved in: {args.output_dir}")


if __name__ == "__main__":
    main()