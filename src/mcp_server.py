"""Single MCP server for LLNL Data Science Challenge analysis tools."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import tempfile
from typing import Any, Callable

os.environ.setdefault(
    "MPLCONFIGDIR",
    str(Path(tempfile.gettempdir()) / "llnl-mcp-matplotlib"),
)

from fastmcp import FastMCP
import numpy as np
import pandas as pd
import tifffile

from data_validation_updated import profile_json, profile_tiff
from skeletonization import skeletonize_mask
from threshold_optimizer import segment_brightness_corrected


PROJECT_ROOT = Path(__file__).resolve().parents[1]
VISUALIZATION_SCRIPT = (
    PROJECT_ROOT
    / ".agents"
    / "skills"
    / "visualization-expert"
    / "scripts"
    / "generate_visualization.py"
)


def _load_visualization_module():
    """Load the tested visualization renderer relative to this repository."""
    if not VISUALIZATION_SCRIPT.is_file():
        raise RuntimeError(
            f"Visualization renderer does not exist: {VISUALIZATION_SCRIPT}"
        )
    specification = importlib.util.spec_from_file_location(
        "llnl_visualization_renderer",
        VISUALIZATION_SCRIPT,
    )
    if specification is None or specification.loader is None:
        raise RuntimeError(
            f"Unable to load visualization renderer: {VISUALIZATION_SCRIPT}"
        )
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


visualization = _load_visualization_module()
mcp = FastMCP("LLNL Data Science Challenge Tools")


def _visualization_error(
    visualization_type: str,
    error: Exception,
) -> dict[str, Any]:
    return {
        "status": "error",
        "visualization_type": visualization_type,
        "input_paths": [],
        "output_path": None,
        "error_type": type(error).__name__,
        "error": str(error),
        "warnings": [],
    }


def _run_visualization(
    visualization_type: str,
    operation: Callable[[argparse.Namespace], dict[str, Any]],
    arguments: argparse.Namespace,
) -> dict[str, Any]:
    """Run a renderer operation and preserve optional context and manifests."""
    try:
        item = operation(arguments)
        visualization.attach_validation(
            item,
            getattr(arguments, "validation_report", None),
        )
        visualization.update_manifest(
            getattr(arguments, "manifest", None),
            item,
        )
        return item
    except Exception as error:
        return _visualization_error(visualization_type, error)


@mcp.tool()
def segment_ct_global_threshold(
    input_filepath: str,
    output_filepath: str,
    threshold: float,
) -> dict[str, Any]:
    """
    Segment a 3D CT volume using one fixed threshold for every voxel.

    This is a baseline method for intensity-uniform or synthetic volumes. For
    the LLNL 9x9x9 CT dataset, prefer segment_ct_brightness_corrected.

    Args:
        input_filepath: Input 3D .npy, .tif, or .tiff CT volume.
        output_filepath: Output .npy, .tif, or .tiff binary mask.
        threshold: Voxels greater than or equal to this value are foreground.

    Returns:
        Structured method, shape, encoding, voxel counts, and output metadata.
    """
    input_path = Path(input_filepath).expanduser().resolve()
    output_path = Path(output_filepath).expanduser().resolve()

    if input_path.suffix.lower() == ".npy":
        volume = np.load(input_path, mmap_mode="r", allow_pickle=False)
    elif input_path.suffix.lower() in {".tif", ".tiff"}:
        volume = tifffile.memmap(input_path)
    else:
        raise ValueError("input_filepath must end in .npy, .tif, or .tiff")

    if volume.ndim != 3:
        raise ValueError(f"expected a 3D CT volume, got shape {volume.shape}")
    if not np.isfinite(threshold):
        raise ValueError("threshold must be finite")
    if input_path == output_path:
        raise ValueError("output_filepath must not overwrite the input volume")

    mask = np.asarray(volume >= threshold, dtype=np.uint8)
    foreground_voxels = int(np.count_nonzero(mask))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.suffix.lower() == ".npy":
        np.save(output_path, mask, allow_pickle=False)
        encoding = "0/1"
    elif output_path.suffix.lower() in {".tif", ".tiff"}:
        # TIFF viewers generally display uint8 data on a 0-255 scale. Store
        # foreground as 255 so the binary structure is visibly white rather
        # than an almost-black intensity of 1.
        tifffile.imwrite(output_path, mask * np.uint8(255), photometric="minisblack")
        encoding = "0/255"
    else:
        raise ValueError("output_filepath must end in .npy, .tif, or .tiff")

    return {
        "method": "global_threshold",
        "input": str(input_path),
        "output": str(output_path),
        "shape_zyx": list(mask.shape),
        "input_dtype": str(volume.dtype),
        "threshold": float(threshold),
        "mask_encoding": encoding,
        "foreground_voxels": foreground_voxels,
        "background_voxels": int(mask.size - foreground_voxels),
    }


@mcp.tool()
def segment_ct_brightness_corrected(
    input_filepath: str,
    output_filepath: str,
    reference_slice: int = 380,
    reference_threshold: float = 40049.0,
    smoothing_sigma: float = 8.0,
) -> dict[str, Any]:
    """
    Segment a 3D CT volume with a smoothed per-slice brightness correction.

    This is the recommended production method for the LLNL 9x9x9 CT dataset.
    It anchors the threshold on a calibrated reference slice and adjusts other
    slices using their smoothed median-intensity profile.
    """
    return segment_brightness_corrected(
        Path(input_filepath),
        Path(output_filepath),
        reference_slice=reference_slice,
        reference_threshold=reference_threshold,
        smoothing_sigma=smoothing_sigma,
    )


@mcp.tool()
def skeletonize(input_filepath: str, output_filepath: str) -> str:
    """
    Creates a skeleton from a 3D segmentation mask.

    Args:
        input_filepath: Path to the .npy, .tif, or .tiff file containing the 3D mask.
        output_filepath: Path to save the extracted skeleton (.npy, .tif, or .tiff).

    Returns:
        A status message indicating success and the save location, or an error message.
    """
    result = skeletonize_mask(input_filepath, output_filepath)

    return (
        f"Skeletonized {input_filepath}; saved {output_filepath} with shape "
        f"{result.shape} and {np.count_nonzero(result)} skeleton voxels."
    )


@mcp.tool()
def inspect_lattice_dataset(
    tiff_filepath: str,
    json_filepath: str,
    output_directory: str,
) -> dict[str, Any]:
    """Validate and statistically profile a lattice CT TIFF and JSON graph."""
    tiff_path = Path(tiff_filepath)
    json_path = Path(json_filepath)
    output_path = Path(output_directory)
    plot_directory = output_path / "plots"
    csv_directory = output_path / "csv"
    tiff_result = profile_tiff(tiff_path, plot_directory, csv_directory)
    json_result, _ = profile_json(json_path, plot_directory)
    return {"tiff": tiff_result, "json": json_result}


@mcp.tool()
def inspect_visualization_input(input_filepath: str) -> dict[str, Any]:
    """
    Inspect a visualization input without modifying it.

    Returns source type, shape or columns, size, and supported visualization
    operations. This tool does not require a validation report.
    """
    try:
        source = visualization.source_path(input_filepath)
        suffix = source.suffix.lower()
        result: dict[str, Any] = {
            "status": "success",
            "input_filepath": str(source),
            "file_size_bytes": source.stat().st_size,
            "warnings": [],
        }
        if suffix in visualization.TIFF_SUFFIXES:
            result.update({
                "input_type": "tiff",
                **visualization.inspect_tiff(source),
                "supported_visualizations": [
                    "histogram",
                    "slice",
                    "orthogonal",
                    "slice_trend",
                    "overlay",
                    "compare_mask",
                ],
            })
        elif suffix == ".npy":
            array = np.load(source, allow_pickle=False, mmap_mode="r")
            result.update({
                "input_type": "npy",
                "shape": list(array.shape),
                "dtype": array.dtype.name,
                "supported_visualizations": [
                    "histogram",
                    "bar",
                    "slice",
                    "orthogonal",
                    "slice_trend",
                    "overlay",
                    "compare_mask",
                ],
            })
        elif suffix == ".csv":
            frame = pd.read_csv(source)
            result.update({
                "input_type": "csv",
                "rows": int(len(frame)),
                "columns": [str(value) for value in frame.columns],
                "supported_visualizations": [
                    "histogram",
                    "bar",
                    "slice_trend",
                ],
            })
        elif suffix == ".json":
            data = json.loads(source.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                keys = [str(value) for value in data.keys()]
            elif isinstance(data, list):
                keys = sorted({
                    str(key)
                    for record in data
                    if isinstance(record, dict)
                    for key in record
                })
            else:
                keys = []
            result.update({
                "input_type": "json",
                "top_level_type": type(data).__name__,
                "available_keys": keys,
                "supported_visualizations": [
                    "histogram",
                    "bar",
                    "graph",
                ],
            })
        elif suffix in visualization.IMAGE_SUFFIXES:
            array = visualization.load_array(source)
            result.update({
                "input_type": "image",
                "shape": list(array.shape),
                "dtype": array.dtype.name,
                "supported_visualizations": [
                    "slice",
                    "overlay",
                    "compare_mask",
                ],
            })
        else:
            raise ValueError(f"Unsupported visualization input type: {suffix}")
        return result
    except Exception as error:
        return {
            "status": "error",
            "input_filepath": str(Path(input_filepath).expanduser().resolve()),
            "error_type": type(error).__name__,
            "error": str(error),
            "warnings": [],
        }


@mcp.tool()
def create_histogram(
    input_filepath: str,
    output_filepath: str,
    column: str | None = None,
    bins: int | str = "auto",
    title: str | None = None,
    x_label: str | None = None,
    threshold: float | None = None,
    show_mean: bool = True,
    show_median: bool = True,
    log_count: bool = False,
    manifest_filepath: str | None = None,
    validation_report_filepath: str | None = None,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Create a histogram from TIFF, NPY, CSV, or JSON numeric data."""
    return _run_visualization(
        "histogram",
        visualization.histogram,
        argparse.Namespace(
            command="histogram",
            input=input_filepath,
            output=output_filepath,
            column=column,
            bins=str(bins),
            title=title,
            x_label=x_label,
            threshold=threshold,
            show_mean=show_mean,
            show_median=show_median,
            log_count=log_count,
            manifest=manifest_filepath,
            validation_report=validation_report_filepath,
            overwrite=overwrite,
        ),
    )


@mcp.tool()
def create_bar_chart(
    input_filepath: str,
    output_filepath: str,
    column: str | None = None,
    title: str | None = None,
    x_label: str | None = None,
    max_categories: int = 50,
    manifest_filepath: str | None = None,
    validation_report_filepath: str | None = None,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Create a bar chart from categorical NPY, CSV, or JSON values."""
    return _run_visualization(
        "bar",
        visualization.bar,
        argparse.Namespace(
            command="bar",
            input=input_filepath,
            output=output_filepath,
            column=column,
            title=title,
            x_label=x_label,
            max_categories=max_categories,
            manifest=manifest_filepath,
            validation_report=validation_report_filepath,
            overwrite=overwrite,
        ),
    )


@mcp.tool()
def visualize_slice(
    input_filepath: str,
    output_filepath: str,
    slice_index: int | None = None,
    axis: int = 0,
    low_percentile: float = 1.0,
    high_percentile: float = 99.0,
    title: str | None = None,
    manifest_filepath: str | None = None,
    validation_report_filepath: str | None = None,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Render one slice from a TIFF, NPY volume, or supported image."""
    return _run_visualization(
        "slice",
        visualization.slice_plot,
        argparse.Namespace(
            command="slice",
            input=input_filepath,
            output=output_filepath,
            axis=axis,
            index=slice_index,
            low_percentile=low_percentile,
            high_percentile=high_percentile,
            title=title,
            manifest=manifest_filepath,
            validation_report=validation_report_filepath,
            overwrite=overwrite,
        ),
    )


@mcp.tool()
def create_orthogonal_views(
    input_filepath: str,
    output_filepath: str,
    low_percentile: float = 1.0,
    high_percentile: float = 99.0,
    title: str | None = None,
    manifest_filepath: str | None = None,
    validation_report_filepath: str | None = None,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Render center slices along all three axes of a TIFF or NPY volume."""
    return _run_visualization(
        "orthogonal",
        visualization.orthogonal,
        argparse.Namespace(
            command="orthogonal",
            input=input_filepath,
            output=output_filepath,
            low_percentile=low_percentile,
            high_percentile=high_percentile,
            title=title,
            manifest=manifest_filepath,
            validation_report=validation_report_filepath,
            overwrite=overwrite,
        ),
    )


@mcp.tool()
def plot_slice_trend(
    input_filepath: str,
    output_filepath: str,
    metric: str = "mean",
    axis: int = 0,
    column: str | None = None,
    title: str | None = None,
    manifest_filepath: str | None = None,
    validation_report_filepath: str | None = None,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Plot a mean or standard-deviation trend from TIFF, NPY, or CSV data."""
    return _run_visualization(
        "slice-trend",
        visualization.slice_trend,
        argparse.Namespace(
            command="slice-trend",
            input=input_filepath,
            output=output_filepath,
            metric=metric,
            axis=axis,
            column=column,
            title=title,
            manifest=manifest_filepath,
            validation_report=validation_report_filepath,
            overwrite=overwrite,
        ),
    )


@mcp.tool()
def overlay_segmentation(
    image_filepath: str,
    mask_filepath: str,
    output_filepath: str,
    slice_index: int | None = None,
    axis: int = 0,
    mask_threshold: float = 0.5,
    alpha: float = 0.45,
    low_percentile: float = 1.0,
    high_percentile: float = 99.0,
    title: str | None = None,
    manifest_filepath: str | None = None,
    validation_report_filepath: str | None = None,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Overlay a binary mask on a scientific image or volume slice."""
    return _run_visualization(
        "overlay",
        visualization.overlay,
        argparse.Namespace(
            command="overlay",
            image=image_filepath,
            mask=mask_filepath,
            output=output_filepath,
            index=slice_index,
            axis=axis,
            mask_threshold=mask_threshold,
            alpha=alpha,
            low_percentile=low_percentile,
            high_percentile=high_percentile,
            title=title,
            manifest=manifest_filepath,
            validation_report=validation_report_filepath,
            overwrite=overwrite,
        ),
    )


@mcp.tool()
def compare_masks(
    prediction_filepath: str,
    reference_filepath: str,
    output_filepath: str,
    slice_index: int | None = None,
    axis: int = 0,
    threshold: float = 0.5,
    title: str | None = None,
    manifest_filepath: str | None = None,
    validation_report_filepath: str | None = None,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Compare predicted and reference masks and create an error-class map."""
    return _run_visualization(
        "compare-mask",
        visualization.compare_mask,
        argparse.Namespace(
            command="compare-mask",
            prediction=prediction_filepath,
            truth=reference_filepath,
            output=output_filepath,
            index=slice_index,
            axis=axis,
            threshold=threshold,
            title=title,
            manifest=manifest_filepath,
            validation_report=validation_report_filepath,
            overwrite=overwrite,
        ),
    )


@mcp.tool()
def render_graph(
    input_filepath: str,
    output_filepath: str,
    x_dimension: int = 0,
    y_dimension: int = 1,
    title: str | None = None,
    manifest_filepath: str | None = None,
    validation_report_filepath: str | None = None,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Render a 2D projection of a recognized node-edge JSON graph."""
    return _run_visualization(
        "graph",
        visualization.graph,
        argparse.Namespace(
            command="graph",
            input=input_filepath,
            output=output_filepath,
            x_dimension=x_dimension,
            y_dimension=y_dimension,
            title=title,
            manifest=manifest_filepath,
            validation_report=validation_report_filepath,
            overwrite=overwrite,
        ),
    )


if __name__ == "__main__":
    mcp.run()
