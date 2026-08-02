"""Deterministic scientific visualization CLI for the visualization-expert skill."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
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
from matplotlib.colors import ListedColormap
from matplotlib.patches import Patch
from matplotlib.ticker import AutoMinorLocator
import numpy as np
import pandas as pd
import tifffile


OUTPUT_SUFFIXES = {".png", ".svg", ".pdf"}
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg"}
TIFF_SUFFIXES = {".tif", ".tiff"}
MAX_DISPLAY_SAMPLES = 2_000_000
MAX_EAGER_BYTES = 512 * 1024 * 1024
MAX_RENDER_WIDTH = 4096
MAX_RENDER_HEIGHT = 4096
MAX_INTEGER_HISTOGRAM_BINS = 1_000_000
COLORS = {
    "primary": "#4C78A8",
    "mean": "#E45756",
    "median": "#54A24B",
    "threshold": "#F58518",
    "axis": "#2F3B45",
    "major_grid": "#9EABB8",
    "minor_grid": "#CFD6DE",
}


def source_path(value: str) -> Path:
    path = Path(value).expanduser().resolve()
    if not path.is_file():
        raise ValueError(f"Input file does not exist: {path}")
    return path


def output_path(value: str, overwrite: bool) -> Path:
    path = Path(value).expanduser().resolve()
    if path.suffix.lower() not in OUTPUT_SUFFIXES:
        raise ValueError("Output must use .png, .svg, or .pdf")
    if path.exists() and not overwrite:
        raise ValueError(f"Output already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def load_array(path: Path) -> np.ndarray:
    suffix = path.suffix.lower()
    if suffix == ".npy":
        return np.load(path, allow_pickle=False, mmap_mode="r")
    if suffix in TIFF_SUFFIXES:
        try:
            return tifffile.memmap(path)
        except ValueError:
            metadata = inspect_tiff(path)
            if metadata["estimated_uncompressed_bytes"] > MAX_EAGER_BYTES:
                raise ValueError(
                    "TIFF is not memory-mappable and exceeds the safe eager-load "
                    f"limit of {MAX_EAGER_BYTES} bytes. Use an axis-0 streaming "
                    "operation."
                )
            return tifffile.imread(path)
    if suffix in IMAGE_SUFFIXES:
        return plt.imread(path)
    raise ValueError(f"Unsupported array input: {suffix}")


def select_2d(array: np.ndarray, axis: int, index: int | None) -> tuple[np.ndarray, int | None]:
    array = np.asarray(array)
    if array.ndim == 2:
        return array, None
    if array.ndim == 3 and array.shape[-1] in (3, 4):
        return array, None
    if array.ndim != 3:
        raise ValueError(f"Expected a 2D or 3D array, got shape {array.shape}")
    if axis not in (0, 1, 2):
        raise ValueError("axis must be 0, 1, or 2")
    chosen = array.shape[axis] // 2 if index is None else index
    if not 0 <= chosen < array.shape[axis]:
        raise ValueError(f"slice index {chosen} is outside axis length {array.shape[axis]}")
    return np.take(array, chosen, axis=axis), chosen


def load_json_frame(path: Path, collection: str | None) -> pd.DataFrame:
    data = json.loads(path.read_text(encoding="utf-8"))
    if collection:
        records = data.get(collection)
        if not isinstance(records, list):
            raise ValueError(
                f"JSON collection '{collection}' was not found or is not a list"
            )
        return pd.json_normalize(records)
    return pd.json_normalize(data)


def numeric_values(
    path: Path,
    column: str | None,
    json_collection: str | None = None,
) -> tuple[np.ndarray, dict[str, Any]]:
    suffix = path.suffix.lower()
    if suffix == ".npy":
        raw = np.load(path, allow_pickle=False)
        if not np.issubdtype(raw.dtype, np.number):
            raise ValueError("NPY input must be numeric")
        values = raw.reshape(-1)
        info = {"shape": list(raw.shape), "column": None}
    elif suffix == ".csv":
        if not column:
            raise ValueError("--column is required for CSV input")
        frame = pd.read_csv(path)
        if column not in frame:
            raise ValueError(f"Column '{column}' was not found")
        values = pd.to_numeric(frame[column], errors="coerce").to_numpy()
        info = {"rows": len(frame), "column": column}
    elif suffix == ".json":
        if not column:
            raise ValueError("--column is required for JSON input")
        frame = load_json_frame(path, json_collection)
        if column not in frame:
            raise ValueError(f"Column '{column}' was not found")
        values = pd.to_numeric(frame[column], errors="coerce").to_numpy()
        info = {"rows": len(frame), "column": column, "json_collection": json_collection}
    else:
        raise ValueError("Numeric input must be .npy, .csv, or .json")
    values = np.asarray(values, dtype=float)
    finite = values[np.isfinite(values)]
    if finite.size == 0:
        raise ValueError("No finite numeric values were found")
    info["value_count"] = int(finite.size)
    info["discarded_value_count"] = int(values.size - finite.size)
    return finite, info


def extra_input_paths(values: list[str] | None) -> list[Path]:
    paths: list[Path] = []
    for value in values or []:
        path = source_path(value)
        paths.append(path)
    return paths


def apply_axes_style(
    axis: plt.Axes,
    style_preset: str,
    *,
    numeric_x: bool = True,
    numeric_y: bool = True,
) -> None:
    if style_preset != "classroom":
        axis.grid(axis="y", alpha=0.25)
        return
    axis.set_axisbelow(True)
    axis.set_facecolor("#FCFCFD")
    axis.title.set_fontsize(18)
    axis.title.set_fontweight("bold")
    axis.xaxis.label.set_fontsize(14)
    axis.xaxis.label.set_fontweight("bold")
    axis.yaxis.label.set_fontsize(14)
    axis.yaxis.label.set_fontweight("bold")
    axis.tick_params(
        axis="both",
        which="major",
        labelsize=12,
        width=1.5,
        length=6,
        color=COLORS["axis"],
    )
    axis.tick_params(
        axis="both",
        which="minor",
        width=0.9,
        length=3.5,
        color=COLORS["axis"],
    )
    for spine in axis.spines.values():
        spine.set_linewidth(1.6)
        spine.set_color(COLORS["axis"])
    if numeric_x:
        axis.xaxis.set_minor_locator(AutoMinorLocator(2))
    if numeric_y:
        axis.yaxis.set_minor_locator(AutoMinorLocator(2))
    axis.grid(which="major", color=COLORS["major_grid"], linewidth=0.9, alpha=0.75)
    axis.grid(which="minor", color=COLORS["minor_grid"], linewidth=0.6, alpha=0.8)


def stats(values: np.ndarray) -> dict[str, Any]:
    return {
        "count": int(values.size),
        "minimum": float(np.min(values)),
        "maximum": float(np.max(values)),
        "mean": float(np.mean(values)),
        "median": float(np.median(values)),
        "standard_deviation": float(np.std(values, ddof=1)) if values.size > 1 else 0.0,
        "q1": float(np.percentile(values, 25)),
        "q3": float(np.percentile(values, 75)),
    }


def inspect_tiff(path: Path) -> dict[str, Any]:
    with tifffile.TiffFile(path) as tiff:
        if not tiff.pages:
            raise ValueError("TIFF contains no pages")
        series = tiff.series[0]
        dtype = np.dtype(series.dtype)
        shape = tuple(int(value) for value in series.shape)
        page = tiff.pages[0]
        compression = getattr(page.compression, "name", str(page.compression))
        page_shapes = {tuple(int(value) for value in current.shape) for current in tiff.pages}
        page_dtypes = {np.dtype(current.dtype).str for current in tiff.pages}
        if len(page_shapes) != 1 or len(page_dtypes) != 1:
            raise ValueError("TIFF pages do not have consistent shapes and dtypes")
    memory_mappable = True
    try:
        tifffile.memmap(path)
    except (ValueError, OSError):
        memory_mappable = False
    return {
        "shape": list(shape),
        "dtype": dtype.name,
        "page_count": int(shape[0]) if len(shape) >= 3 else 1,
        "page_shape": list(next(iter(page_shapes))),
        "compression": compression,
        "memory_mappable": memory_mappable,
        "estimated_uncompressed_bytes": int(np.prod(shape, dtype=np.int64) * dtype.itemsize),
    }


def iterate_tiff_pages(path: Path):
    with tifffile.TiffFile(path) as tiff:
        for index, page in enumerate(tiff.pages):
            yield index, page.asarray()


def calculate_display_window(array: np.ndarray, low: float, high: float) -> dict[str, Any]:
    if not 0 <= low < high <= 100:
        raise ValueError("Display percentiles must satisfy 0 <= low < high <= 100")
    flattened = np.asarray(array).reshape(-1)
    step = max(1, int(np.ceil(flattened.size / MAX_DISPLAY_SAMPLES)))
    sampled = flattened[::step]
    finite = sampled[np.isfinite(sampled)]
    if finite.size == 0:
        raise ValueError("Image contains no finite values")
    vmin, vmax = np.percentile(finite, [low, high])
    if vmin == vmax:
        vmax = vmin + 1.0
    return {
        "display_min": float(vmin),
        "display_max": float(vmax),
        "sampled": step > 1,
        "sampling_method": "regular_stride" if step > 1 else None,
        "sampled_component": "display_window" if step > 1 else None,
        "source_value_count": int(flattened.size),
        "sample_value_count": int(sampled.size),
        "stride": int(step),
    }


def render_strides(shape: tuple[int, ...]) -> tuple[int, int]:
    if len(shape) < 2:
        raise ValueError("Display input must have at least two dimensions")
    row_stride = max(1, int(np.ceil(shape[0] / MAX_RENDER_HEIGHT)))
    column_stride = max(1, int(np.ceil(shape[1] / MAX_RENDER_WIDTH)))
    return row_stride, column_stride


def prepare_display_image(array: np.ndarray) -> tuple[np.ndarray, dict[str, Any]]:
    row_stride, column_stride = render_strides(array.shape)
    rendered = np.asarray(array)[::row_stride, ::column_stride, ...]
    return rendered, {
        "render_downsampled": row_stride > 1 or column_stride > 1,
        "original_dimensions": [int(array.shape[0]), int(array.shape[1])],
        "rendered_dimensions": [int(rendered.shape[0]), int(rendered.shape[1])],
        "render_sampling_method": (
            "regular_grid" if row_stride > 1 or column_stride > 1 else None
        ),
        "render_row_stride": row_stride,
        "render_column_stride": column_stride,
    }


def save_figure(fig: plt.Figure, path: Path) -> None:
    try:
        fig.tight_layout()
        fig.savefig(path, dpi=200, bbox_inches="tight")
    finally:
        plt.close(fig)
    if not path.is_file() or path.stat().st_size == 0:
        raise RuntimeError(f"Visualization was not saved correctly: {path}")


def result(kind: str, inputs: list[Path], output: Path, parameters: dict[str, Any],
           statistics: dict[str, Any] | None = None,
           warnings: list[str] | None = None,
           provenance: dict[str, Any] | None = None,
           extra_inputs: list[Path] | None = None) -> dict[str, Any]:
    provenance_data = {
        "script": "generate_visualization.py",
        "sampled": False,
        "sampling_method": None,
        "created_utc": datetime.now(timezone.utc).isoformat(),
    }
    if provenance:
        provenance_data.update(provenance)
    return {
        "status": "success",
        "visualization_type": kind,
        "input_paths": [str(path) for path in [*inputs, *(extra_inputs or [])]],
        "output_path": str(output),
        "parameters": parameters,
        "statistics": statistics or {},
        "warnings": warnings or [],
        "provenance": provenance_data,
    }


def update_manifest(path_value: str | None, item: dict[str, Any]) -> None:
    if not path_value or item.get("status") != "success":
        return
    path = Path(path_value).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        manifest = json.loads(path.read_text(encoding="utf-8"))
    else:
        manifest = {"schema_version": "1.0", "artifacts": []}
    if not isinstance(manifest.get("artifacts"), list):
        raise ValueError("Manifest must contain an artifacts list")
    signature = (item["visualization_type"], item["output_path"])
    manifest["artifacts"] = [
        old for old in manifest["artifacts"]
        if (old.get("visualization_type"), old.get("output_path")) != signature
    ]
    manifest["artifacts"].append(item)
    path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def attach_validation(item: dict[str, Any], report_value: str | None) -> None:
    if not report_value or item.get("status") != "success":
        return
    report_path = source_path(report_value)
    report = json.loads(report_path.read_text(encoding="utf-8"))
    decision = report.get("decision")
    if decision not in {"PASS", "PASS_WITH_WARNINGS", "FAIL"}:
        raise ValueError("Validation report has no recognized decision")
    item["input_paths"].append(str(report_path))
    item["upstream_validation"] = {
        "decision": decision,
        "report_path": str(report_path),
    }
    report_warnings = report.get("all_warnings", [])
    if isinstance(report_warnings, list):
        item["warnings"].extend(str(value) for value in report_warnings)
    if decision == "FAIL":
        item["warnings"].append(
            "Upstream validation failed; treat this artifact as diagnostic only."
        )


def percentile_from_counts(values: np.ndarray, counts: np.ndarray, percentile: float) -> float:
    total = int(np.sum(counts))
    if total == 0:
        raise ValueError("Histogram contains no values")
    target = percentile / 100.0 * max(total - 1, 0)
    index = int(np.searchsorted(np.cumsum(counts), target + 1, side="left"))
    return float(values[min(index, values.size - 1)])


def statistics_from_counts(values: np.ndarray, counts: np.ndarray) -> dict[str, Any]:
    occupied = counts > 0
    if not np.any(occupied):
        raise ValueError("TIFF contains no finite values")
    used_values = values[occupied].astype(np.float64)
    used_counts = counts[occupied].astype(np.float64)
    total = int(np.sum(used_counts))
    mean = float(np.dot(used_values, used_counts) / total)
    variance = float(np.dot((used_values - mean) ** 2, used_counts) / max(total - 1, 1))
    return {
        "count": total,
        "minimum": float(used_values[0]),
        "maximum": float(used_values[-1]),
        "mean": mean,
        "median": percentile_from_counts(values, counts, 50),
        "standard_deviation": float(np.sqrt(variance)) if total > 1 else 0.0,
        "q1": percentile_from_counts(values, counts, 25),
        "q3": percentile_from_counts(values, counts, 75),
        "occupied_bin_count": int(np.count_nonzero(occupied)),
    }


def sample_tiff_values(path: Path, page_count: int) -> tuple[np.ndarray, dict[str, Any]]:
    per_page = max(1, MAX_DISPLAY_SAMPLES // max(page_count, 1))
    samples: list[np.ndarray] = []
    source_count = 0
    for _, page in iterate_tiff_pages(path):
        flattened = np.asarray(page).reshape(-1)
        source_count += flattened.size
        stride = max(1, int(np.ceil(flattened.size / per_page)))
        selected = flattened[::stride]
        selected = selected[np.isfinite(selected)]
        if selected.size:
            samples.append(selected.astype(np.float64, copy=False))
    if not samples:
        raise ValueError("TIFF contains no finite values")
    combined = np.concatenate(samples)
    if combined.size > MAX_DISPLAY_SAMPLES:
        combined = combined[:MAX_DISPLAY_SAMPLES]
    return combined, {
        "sampled": combined.size < source_count,
        "sampling_method": "regular_stride_for_bin_edges",
        "sampled_component": "bin_edge_selection",
        "source_value_count": int(source_count),
        "sample_value_count": int(combined.size),
    }


def stream_tiff_histogram(
    path: Path,
    bins: int | str,
) -> tuple[np.ndarray, np.ndarray, dict[str, Any], dict[str, Any]]:
    metadata = inspect_tiff(path)
    dtype = np.dtype(metadata["dtype"])
    page_count = metadata["page_count"]
    if np.issubdtype(dtype, np.integer):
        limits = np.iinfo(dtype)
        bin_count = int(limits.max) - int(limits.min) + 1
        if bin_count > MAX_INTEGER_HISTOGRAM_BINS:
            raise ValueError(
                f"Integer dtype {dtype.name} requires {bin_count} exact bins, "
                f"above the safe limit of {MAX_INTEGER_HISTOGRAM_BINS}."
            )
        counts = np.zeros(bin_count, dtype=np.uint64)
        for _, page in iterate_tiff_pages(path):
            flattened = np.asarray(page).reshape(-1).astype(np.int64, copy=False)
            page_counts = np.bincount(
                flattened - int(limits.min),
                minlength=bin_count,
            ).astype(np.uint64, copy=False)
            counts += page_counts
        values = np.arange(int(limits.min), int(limits.max) + 1, dtype=np.int64)
        summary = statistics_from_counts(values, counts)
        occupied = counts > 0
        first, last = np.flatnonzero(occupied)[[0, -1]]
        display_values = values[first:last + 1]
        display_counts = counts[first:last + 1]
        edges = np.arange(
            float(display_values[0]) - 0.5,
            float(display_values[-1]) + 1.5,
            1.0,
        )
        provenance = {
            "sampled": False,
            "sampling_method": None,
            "statistics_source": "streamed_tiff_pages",
            "pages_processed": page_count,
            "histogram_count_coverage": 1.0,
            "tiff_metadata": metadata,
        }
        return display_counts, edges, summary, provenance

    sample, sampling = sample_tiff_values(path, page_count)
    selected_bins = "fd" if bins == "auto" else int(bins)
    edges = np.histogram_bin_edges(sample, bins=selected_bins)
    counts = np.zeros(edges.size - 1, dtype=np.uint64)
    total = 0
    total_sum = 0.0
    total_square_sum = 0.0
    finite_min = np.inf
    finite_max = -np.inf
    for _, page in iterate_tiff_pages(path):
        values = np.asarray(page, dtype=np.float64).reshape(-1)
        values = values[np.isfinite(values)]
        if not values.size:
            continue
        counts += np.histogram(values, bins=edges)[0].astype(np.uint64)
        total += int(values.size)
        total_sum += float(np.sum(values))
        total_square_sum += float(np.dot(values, values))
        finite_min = min(finite_min, float(np.min(values)))
        finite_max = max(finite_max, float(np.max(values)))
    centers = (edges[:-1] + edges[1:]) / 2
    approximate = statistics_from_counts(centers, counts)
    approximate.update({
        "count": total,
        "minimum": finite_min,
        "maximum": finite_max,
        "mean": total_sum / total,
        "standard_deviation": float(
            np.sqrt(max(total_square_sum - total_sum ** 2 / total, 0.0) / max(total - 1, 1))
        ) if total else 0.0,
        "percentiles_approximate_from_histogram_bins": True,
    })
    provenance = {
        **sampling,
        "statistics_source": "streamed_tiff_pages",
        "pages_processed": page_count,
        "histogram_count_coverage": 1.0,
        "tiff_metadata": metadata,
    }
    return counts, edges, approximate, provenance


def histogram(args: argparse.Namespace) -> dict[str, Any]:
    source = source_path(args.input)
    output = output_path(args.output, args.overwrite)
    extra_inputs = extra_input_paths(args.extra_input)
    bins: int | str = args.bins
    if args.bins != "auto":
        bins = int(args.bins)
        if not 1 <= bins <= 1000:
            raise ValueError("bins must be auto or an integer from 1 through 1000")
    is_tiff = source.suffix.lower() in TIFF_SUFFIXES
    if is_tiff:
        counts, edges, summary, histogram_provenance = stream_tiff_histogram(source, bins)
        info = {
            "shape": histogram_provenance["tiff_metadata"]["shape"],
            "dtype": histogram_provenance["tiff_metadata"]["dtype"],
            "discarded_value_count": 0,
        }
    else:
        values, info = numeric_values(source, args.column, args.json_collection)
        summary = stats(values)
        histogram_provenance = None
    fig, axis = plt.subplots(figsize=(9, 6))
    if is_tiff:
        axis.stairs(
            counts,
            edges,
            fill=True,
            color=COLORS["primary"],
            alpha=0.88,
            linewidth=1.4,
            edgecolor=COLORS["axis"],
        )
        mean_value = summary["mean"]
        median_value = summary["median"]
    else:
        axis.hist(
            values,
            bins=bins,
            color=COLORS["primary"],
            edgecolor="white",
            linewidth=0.8,
            alpha=0.9,
        )
        mean_value = float(np.mean(values))
        median_value = float(np.median(values))
    if args.show_mean:
        axis.axvline(mean_value, color=COLORS["mean"], linestyle="--",
                    label=f"Mean: {mean_value:.4g}")
    if args.show_median:
        axis.axvline(median_value, color=COLORS["median"], linestyle=":",
                    label=f"Median: {median_value:.4g}")
    if args.threshold is not None:
        axis.axvline(args.threshold, color=COLORS["threshold"], linestyle="-.",
                    label=f"Threshold: {args.threshold:.4g}")
    if args.log_count:
        axis.set_yscale("log")
    axis.set(title=args.title or f"Distribution of {args.column or source.stem}",
             xlabel=args.x_label or args.column or "Value",
             ylabel=args.y_label or (
                 "Frequency (log scale)" if args.log_count else "Frequency"
             ))
    apply_axes_style(axis, args.style_preset, numeric_x=True, numeric_y=not args.log_count)
    if args.show_mean or args.show_median or args.threshold is not None:
        axis.legend()
    save_figure(fig, output)
    summary.update(info)
    if args.threshold is not None:
        if is_tiff:
            bin_centers = (edges[:-1] + edges[1:]) / 2
            qualifying = bin_centers >= args.threshold
            count = int(np.sum(counts[qualifying]))
            total_count = int(np.sum(counts))
        else:
            count = int(np.count_nonzero(values >= args.threshold))
            total_count = int(values.size)
        summary["threshold_analysis"] = {
            "threshold": args.threshold, "count_at_or_above": count,
            "percentage_at_or_above": count / total_count * 100,
        }
    warnings = []
    if info["discarded_value_count"]:
        warnings.append(f"Discarded {info['discarded_value_count']} nonfinite values.")
    return result(
        "histogram", [source], output, vars_for(args), summary, warnings,
        histogram_provenance, extra_inputs=extra_inputs,
    )


def bar(args: argparse.Namespace) -> dict[str, Any]:
    source = source_path(args.input)
    output = output_path(args.output, args.overwrite)
    extra_inputs = extra_input_paths(args.extra_input)
    suffix = source.suffix.lower()
    if suffix == ".npy":
        values = np.load(source, allow_pickle=False).reshape(-1)
    elif suffix == ".csv":
        frame = pd.read_csv(source)
        if not args.column or args.column not in frame:
            raise ValueError("A valid --column is required for CSV input")
        values = frame[args.column].to_numpy()
    elif suffix == ".json":
        frame = load_json_frame(source, args.json_collection)
        if not args.column or args.column not in frame:
            raise ValueError("A valid --column is required for JSON input")
        values = frame[args.column].to_numpy()
    else:
        raise ValueError("Bar input must be .npy, .csv, or .json")
    counts = pd.Series(values).dropna().astype(str).value_counts().sort_index()
    if len(counts) > args.max_categories:
        raise ValueError(f"Found {len(counts)} categories; maximum is {args.max_categories}")
    fig, axis = plt.subplots(figsize=(max(7, len(counts) * 0.55), 6))
    numeric_index = pd.to_numeric(counts.index, errors="coerce")
    if np.all(np.isfinite(numeric_index.to_numpy(dtype=float))):
        order = np.argsort(numeric_index.to_numpy(dtype=float))
        x_values = numeric_index.to_numpy(dtype=float)[order]
        y_values = counts.to_numpy(dtype=float)[order]
        if len(x_values) > 1:
            widths = np.diff(np.unique(x_values))
            width = max(0.6, 0.8 * float(np.min(widths))) if widths.size else 0.8
        else:
            width = 0.8
        axis.bar(
            x_values,
            y_values,
            width=width,
            color=COLORS["primary"],
            edgecolor=COLORS["axis"],
            linewidth=0.9,
        )
        axis.set_xticks(x_values)
        numeric_x = True
    else:
        axis.bar(
            counts.index,
            counts.values,
            color=COLORS["primary"],
            edgecolor=COLORS["axis"],
            linewidth=0.9,
        )
        numeric_x = False
    axis.set(title=args.title or f"Counts of {args.column or source.stem}",
             xlabel=args.x_label or args.column or "Category",
             ylabel=args.y_label or "Count")
    axis.tick_params(axis="x", rotation=45)
    apply_axes_style(axis, args.style_preset, numeric_x=numeric_x, numeric_y=True)
    save_figure(fig, output)
    return result("bar", [source], output, vars_for(args),
                  {"category_count": len(counts), "counts": counts.to_dict()},
                  extra_inputs=extra_inputs)


def slice_plot(args: argparse.Namespace) -> dict[str, Any]:
    source = source_path(args.input)
    output = output_path(args.output, args.overwrite)
    raw = load_array(source)
    image, chosen = select_2d(raw, args.axis, args.index)
    display_window = calculate_display_window(
        image, args.low_percentile, args.high_percentile
    )
    rendered, render_info = prepare_display_image(image)
    fig, axis = plt.subplots(figsize=(8, 8))
    axis.imshow(
        rendered, cmap="gray",
        vmin=display_window["display_min"],
        vmax=display_window["display_max"],
    )
    axis.set_title(args.title or f"{source.name}: axis {args.axis}, slice {chosen}")
    axis.axis("off")
    save_figure(fig, output)
    return result(
        "slice", [source], output, vars_for(args),
        {
            "source_shape": list(raw.shape),
            "selected_index": chosen,
            **display_window,
            **render_info,
        },
        provenance={
            "sampled": display_window["sampled"],
            "sampling_method": display_window["sampling_method"],
            "sampled_component": display_window["sampled_component"],
            "source_value_count": display_window["source_value_count"],
            "sample_value_count": display_window["sample_value_count"],
            "stride": display_window["stride"],
            **render_info,
        },
    )


def orthogonal(args: argparse.Namespace) -> dict[str, Any]:
    source = source_path(args.input)
    output = output_path(args.output, args.overwrite)
    raw = load_array(source)
    if raw.ndim != 3:
        raise ValueError("Orthogonal views require a 3D array")
    indices = [raw.shape[i] // 2 for i in range(3)]
    display_window = calculate_display_window(
        raw, args.low_percentile, args.high_percentile
    )
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    names = ["axis 0", "axis 1", "axis 2"]
    render_details = []
    for axis_id, plot_axis in enumerate(axes):
        selected = np.take(raw, indices[axis_id], axis=axis_id)
        rendered, render_info = prepare_display_image(selected)
        render_details.append(render_info)
        plot_axis.imshow(
            rendered, cmap="gray",
            vmin=display_window["display_min"],
            vmax=display_window["display_max"],
        )
        plot_axis.set_title(f"{names[axis_id]} slice {indices[axis_id]}")
        plot_axis.axis("off")
    fig.suptitle(args.title or f"Orthogonal views: {source.name}")
    save_figure(fig, output)
    return result(
        "orthogonal", [source], output, vars_for(args),
        {
            "source_shape": list(raw.shape),
            "indices": indices,
            **display_window,
            "render_views": render_details,
        },
        provenance={
            "sampled": display_window["sampled"],
            "sampling_method": display_window["sampling_method"],
            "sampled_component": display_window["sampled_component"],
            "source_value_count": display_window["source_value_count"],
            "sample_value_count": display_window["sample_value_count"],
            "stride": display_window["stride"],
            "render_views": render_details,
        },
    )


def slice_trend(args: argparse.Namespace) -> dict[str, Any]:
    source = source_path(args.input)
    output = output_path(args.output, args.overwrite)
    extra_inputs = extra_input_paths(args.extra_input)
    if source.suffix.lower() == ".csv":
        frame = pd.read_csv(source)
        if not args.column or args.column not in frame:
            raise ValueError("A valid --column is required for CSV trends")
        values = pd.to_numeric(frame[args.column], errors="coerce").to_numpy()
        x = np.arange(values.size)
        trend_provenance = {
            "sampled": False,
            "sampling_method": None,
            "statistics_source": "csv_column",
        }
    elif source.suffix.lower() in TIFF_SUFFIXES and args.axis == 0:
        metadata = inspect_tiff(source)
        trend_values = []
        for _, page in iterate_tiff_pages(source):
            page_array = np.asarray(page)
            value = (
                float(np.mean(page_array))
                if args.metric == "mean"
                else float(np.std(page_array))
            )
            trend_values.append(value)
        values = np.asarray(trend_values, dtype=float)
        x = np.arange(values.size)
        trend_provenance = {
            "sampled": False,
            "sampling_method": None,
            "statistics_source": "streamed_tiff_pages",
            "pages_processed": int(values.size),
            "tiff_metadata": metadata,
        }
    else:
        raw = load_array(source)
        if raw.ndim != 3:
            raise ValueError("Volume trends require a 3D input")
        axes = tuple(i for i in range(3) if i != args.axis)
        values = np.mean(raw, axis=axes) if args.metric == "mean" else np.std(raw, axis=axes)
        x = np.arange(raw.shape[args.axis])
        trend_provenance = {
            "sampled": False,
            "sampling_method": None,
            "statistics_source": "memory_mapped_volume",
        }
    fig, axis = plt.subplots(figsize=(10, 5))
    axis.plot(x, values, color=COLORS["primary"], linewidth=2.3)
    axis.set(title=args.title or f"Per-slice {args.column or args.metric}",
             xlabel="Slice index", ylabel=args.y_label or args.column or args.metric)
    apply_axes_style(axis, args.style_preset, numeric_x=True, numeric_y=True)
    save_figure(fig, output)
    finite = np.asarray(values, dtype=float)
    finite = finite[np.isfinite(finite)]
    return result(
        "slice-trend", [source], output, vars_for(args), stats(finite),
        provenance=trend_provenance, extra_inputs=extra_inputs,
    )


def overlay(args: argparse.Namespace) -> dict[str, Any]:
    image_path, mask_path = source_path(args.image), source_path(args.mask)
    output = output_path(args.output, args.overwrite)
    raw_image, raw_mask = load_array(image_path), load_array(mask_path)
    image, image_index = select_2d(raw_image, args.axis, args.index)
    mask, mask_index = select_2d(raw_mask, args.axis, args.index)
    if image.shape[:2] != mask.shape[:2]:
        raise ValueError(f"Image and mask shapes differ: {image.shape} vs {mask.shape}")
    mask_bool = np.asarray(mask) > args.mask_threshold
    display_window = calculate_display_window(
        image, args.low_percentile, args.high_percentile
    )
    row_stride, column_stride = render_strides(image.shape)
    rendered_image = np.asarray(image)[::row_stride, ::column_stride, ...]
    rendered_mask = mask_bool[::row_stride, ::column_stride]
    render_info = {
        "render_downsampled": row_stride > 1 or column_stride > 1,
        "original_dimensions": [int(image.shape[0]), int(image.shape[1])],
        "rendered_dimensions": [
            int(rendered_image.shape[0]), int(rendered_image.shape[1])
        ],
        "render_sampling_method": (
            "regular_grid" if row_stride > 1 or column_stride > 1 else None
        ),
        "render_row_stride": row_stride,
        "render_column_stride": column_stride,
        "mask_render_interpolation": "nearest",
    }
    fig, axis = plt.subplots(figsize=(8, 8))
    axis.imshow(
        rendered_image, cmap="gray",
        vmin=display_window["display_min"],
        vmax=display_window["display_max"],
    )
    shown = np.ma.masked_where(~rendered_mask, rendered_mask)
    axis.imshow(shown, cmap=ListedColormap(["#00BFC4"]), alpha=args.alpha,
                interpolation="nearest")
    axis.set_title(args.title or f"Segmentation overlay: {image_path.name}")
    axis.axis("off")
    save_figure(fig, output)
    return result(
        "overlay", [image_path, mask_path], output, vars_for(args),
        {
            "image_shape": list(raw_image.shape),
            "mask_shape": list(raw_mask.shape),
            "selected_index": image_index,
            "foreground_pixels": int(mask_bool.sum()),
            "foreground_fraction": float(mask_bool.mean()),
            **display_window,
            **render_info,
        },
        provenance={
            "sampled": display_window["sampled"],
            "sampling_method": display_window["sampling_method"],
            "sampled_component": display_window["sampled_component"],
            **render_info,
        },
    )


def compare_mask(args: argparse.Namespace) -> dict[str, Any]:
    prediction_path, truth_path = source_path(args.prediction), source_path(args.truth)
    output = output_path(args.output, args.overwrite)
    prediction, pred_index = select_2d(load_array(prediction_path), args.axis, args.index)
    truth, truth_index = select_2d(load_array(truth_path), args.axis, args.index)
    if prediction.shape[:2] != truth.shape[:2]:
        raise ValueError(f"Prediction and truth shapes differ: {prediction.shape} vs {truth.shape}")
    pred = np.asarray(prediction) > args.threshold
    actual = np.asarray(truth) > args.threshold
    classes = np.zeros(pred.shape, dtype=np.uint8)
    classes[actual & pred] = 1
    classes[~actual & pred] = 2
    classes[actual & ~pred] = 3
    cmap = ListedColormap(["black", "#54A24B", "#E45756", "#F2CF5B"])
    rendered_classes, render_info = prepare_display_image(classes)
    fig, axis = plt.subplots(figsize=(8, 8))
    axis.imshow(
        rendered_classes, cmap=cmap, vmin=0, vmax=3, interpolation="nearest"
    )
    axis.legend(handles=[
        Patch(color="black", label="Background"),
        Patch(color="#54A24B", label="True positive"),
        Patch(color="#E45756", label="False positive"),
        Patch(color="#F2CF5B", label="False negative"),
    ], loc="upper right")
    axis.set_title(args.title or "Segmentation error map")
    axis.axis("off")
    save_figure(fig, output)
    tp, fp, fn = int(np.sum(classes == 1)), int(np.sum(classes == 2)), int(np.sum(classes == 3))
    return result(
        "compare-mask", [prediction_path, truth_path], output, vars_for(args),
        {
            "selected_index": pred_index,
            "true_positive": tp,
            "false_positive": fp,
            "false_negative": fn,
            "dice": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 1.0,
            **render_info,
        },
        provenance={
            "sampled": False,
            "sampling_method": None,
            **render_info,
            "mask_render_interpolation": "nearest",
        },
    )


def graph(args: argparse.Namespace) -> dict[str, Any]:
    source = source_path(args.input)
    output = output_path(args.output, args.overwrite)
    extra_inputs = extra_input_paths(args.extra_input)
    data = json.loads(source.read_text(encoding="utf-8"))
    junctions = next((data[key] for key in ("junctions", "nodes", "vertices")
                      if isinstance(data.get(key), list)), None)
    struts = next((data[key] for key in ("struts", "edges", "links")
                   if isinstance(data.get(key), list)), None)
    if junctions is None or struts is None:
        raise ValueError("JSON must contain junctions/nodes and struts/edges lists")
    positions: dict[Any, np.ndarray] = {}
    for i, node in enumerate(junctions):
        node_id = node.get("id", i)
        position = node.get("position", node.get("coordinates", node.get("point")))
        if not isinstance(position, list) or len(position) < 2:
            continue
        positions[node_id] = np.asarray(position, dtype=float)
    fig, axis = plt.subplots(figsize=(8, 8))
    invalid = 0
    for edge in struts:
        start = edge.get("junction0", edge.get("source", edge.get("start")))
        end = edge.get("junction1", edge.get("target", edge.get("end")))
        if start not in positions or end not in positions:
            invalid += 1
            continue
        p0, p1 = positions[start], positions[end]
        axis.plot([p0[args.x_dimension], p1[args.x_dimension]],
                  [p0[args.y_dimension], p1[args.y_dimension]],
                  color="#999999", linewidth=0.8, zorder=1)
    if positions:
        points = np.stack(list(positions.values()))
        axis.scatter(points[:, args.x_dimension], points[:, args.y_dimension],
                     color=COLORS["primary"], s=12, zorder=2)
    axis.set(title=args.title or f"Lattice graph projection: {source.name}",
             xlabel=f"coordinate {args.x_dimension}",
             ylabel=f"coordinate {args.y_dimension}")
    axis.set_aspect("equal", adjustable="datalim")
    apply_axes_style(axis, args.style_preset, numeric_x=True, numeric_y=True)
    save_figure(fig, output)
    warnings = [f"Omitted {invalid} edges with invalid endpoints."] if invalid else []
    return result("graph", [source], output, vars_for(args),
                  {"junction_count": len(junctions), "plotted_junction_count": len(positions),
                   "strut_count": len(struts), "invalid_edge_count": invalid},
                  warnings, extra_inputs=extra_inputs)


def vars_for(args: argparse.Namespace) -> dict[str, Any]:
    hidden = {"func", "manifest", "output", "input", "image", "mask",
              "prediction", "truth", "overwrite", "validation_report", "extra_input"}
    return {key: value for key, value in vars(args).items() if key not in hidden}


def common(parser: argparse.ArgumentParser, input_name: str = "input") -> None:
    parser.add_argument(f"--{input_name}", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--manifest")
    parser.add_argument("--validation-report")
    parser.add_argument("--extra-input", action="append")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--title")
    parser.add_argument("--style-preset", choices=("standard", "classroom"), default="standard")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("histogram")
    common(p)
    p.add_argument("--column")
    p.add_argument("--json-collection")
    p.add_argument("--bins", default="auto")
    p.add_argument("--x-label")
    p.add_argument("--y-label")
    p.add_argument("--threshold", type=float)
    p.add_argument("--show-mean", action="store_true")
    p.add_argument("--show-median", action="store_true")
    p.add_argument("--log-count", action="store_true")
    p.set_defaults(func=histogram)

    p = sub.add_parser("bar")
    common(p)
    p.add_argument("--column")
    p.add_argument("--json-collection")
    p.add_argument("--x-label")
    p.add_argument("--y-label")
    p.add_argument("--max-categories", type=int, default=50)
    p.set_defaults(func=bar)

    p = sub.add_parser("slice")
    common(p)
    p.add_argument("--axis", type=int, default=0)
    p.add_argument("--index", type=int)
    p.add_argument("--low-percentile", type=float, default=1.0)
    p.add_argument("--high-percentile", type=float, default=99.0)
    p.set_defaults(func=slice_plot)

    p = sub.add_parser("orthogonal")
    common(p)
    p.add_argument("--low-percentile", type=float, default=1.0)
    p.add_argument("--high-percentile", type=float, default=99.0)
    p.set_defaults(func=orthogonal)

    p = sub.add_parser("slice-trend")
    common(p)
    p.add_argument("--column")
    p.add_argument("--axis", type=int, default=0)
    p.add_argument("--metric", choices=("mean", "std"), default="mean")
    p.add_argument("--y-label")
    p.set_defaults(func=slice_trend)

    p = sub.add_parser("overlay")
    common(p, "image")
    p.add_argument("--mask", required=True)
    p.add_argument("--axis", type=int, default=0)
    p.add_argument("--index", type=int)
    p.add_argument("--mask-threshold", type=float, default=0.5)
    p.add_argument("--alpha", type=float, default=0.45)
    p.add_argument("--low-percentile", type=float, default=1.0)
    p.add_argument("--high-percentile", type=float, default=99.0)
    p.set_defaults(func=overlay)

    p = sub.add_parser("compare-mask")
    common(p, "prediction")
    p.add_argument("--truth", required=True)
    p.add_argument("--axis", type=int, default=0)
    p.add_argument("--index", type=int)
    p.add_argument("--threshold", type=float, default=0.5)
    p.set_defaults(func=compare_mask)

    p = sub.add_parser("graph")
    common(p)
    p.add_argument("--x-dimension", type=int, choices=(0, 1, 2), default=0)
    p.add_argument("--y-dimension", type=int, choices=(0, 1, 2), default=1)
    p.set_defaults(func=graph)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        item = args.func(args)
        attach_validation(item, args.validation_report)
        update_manifest(args.manifest, item)
    except Exception as error:
        item = {
            "status": "error",
            "visualization_type": args.command,
            "input_paths": [],
            "output_path": None,
            "error_type": type(error).__name__,
            "error": str(error),
            "warnings": [],
        }
    print(json.dumps(item, indent=2))
    return 0 if item["status"] == "success" else 1


if __name__ == "__main__":
    sys.exit(main())
