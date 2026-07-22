#!/usr/bin/env python3

from __future__ import annotations

import argparse
import inspect
import math
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
os.environ.setdefault("MPLCONFIGDIR", str(SCRIPT_DIR / ".mplconfig"))

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import tifffile
from scipy import ndimage as ndi
from skimage import filters, morphology, segmentation


DEFAULT_INPUT = SCRIPT_DIR.parent / "9x9x9_octet_lattice.tif"
MAX_OPTIMIZATION_ITERATIONS = 10
MAX_FAILED_ATTEMPTS = 3


@dataclass(frozen=True)
class CandidateConfig:
    name: str
    threshold_method: str
    polarity: str
    closing_radius: int
    min_object_size: int
    max_hole_size: int


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Segment a lattice TIFF dataset.")
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help="Path to the input TIFF dataset.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=SCRIPT_DIR,
        help="Directory for segmentation outputs.",
    )
    return parser.parse_args()


def inspect_and_load_dataset(input_path: Path) -> tuple[np.ndarray, dict[str, Any]]:
    metadata: dict[str, Any] = {
        "input_path": str(input_path),
        "read_mode": "unknown",
        "series_count": None,
        "page_count": None,
        "series_shape": None,
        "series_axes": None,
        "fallback_note": None,
    }

    with tifffile.TiffFile(input_path) as tif:
        metadata["series_count"] = len(tif.series)
        metadata["page_count"] = len(tif.pages)
        if tif.series:
            metadata["series_shape"] = tuple(int(v) for v in tif.series[0].shape)
            metadata["series_axes"] = tif.series[0].axes

    array = tifffile.imread(input_path)
    metadata["raw_shape"] = tuple(int(v) for v in array.shape)
    metadata["raw_dtype"] = str(array.dtype)

    if array.ndim == 2:
        metadata["read_mode"] = "2d_fallback"
        metadata["fallback_note"] = (
            "The TIFF did not expose a readable multi-page stack. "
            "Segmentation was performed deterministically on the single readable page."
        )
        volume = array[np.newaxis, ...]
    elif array.ndim == 3:
        metadata["read_mode"] = "3d_stack"
        volume = array
    else:
        raise ValueError(f"Unsupported TIFF dimensionality: {array.ndim}")

    metadata["working_shape"] = tuple(int(v) for v in volume.shape)
    return volume.astype(np.float32), metadata


def compute_thresholds(volume: np.ndarray) -> dict[str, float]:
    return {
        "triangle": float(filters.threshold_triangle(volume)),
        "yen": float(filters.threshold_yen(volume)),
        "otsu": float(filters.threshold_otsu(volume)),
        "li": float(filters.threshold_li(volume)),
        "isodata": float(filters.threshold_isodata(volume)),
    }


def build_candidates() -> list[CandidateConfig]:
    return [
        CandidateConfig("triangle_bright_r1", "triangle", "bright", 1, 128, 128),
        CandidateConfig("triangle_dark_r1", "triangle", "dark", 1, 128, 128),
        CandidateConfig("yen_bright_r1", "yen", "bright", 1, 128, 128),
        CandidateConfig("yen_dark_r1", "yen", "dark", 1, 128, 128),
        CandidateConfig("otsu_bright_r1", "otsu", "bright", 1, 128, 128),
        CandidateConfig("otsu_dark_r1", "otsu", "dark", 1, 128, 128),
        CandidateConfig("triangle_bright_r2", "triangle", "bright", 2, 256, 256),
        CandidateConfig("yen_bright_r2", "yen", "bright", 2, 256, 256),
        CandidateConfig("li_bright_r1", "li", "bright", 1, 128, 128),
        CandidateConfig("isodata_bright_r1", "isodata", "bright", 1, 128, 128),
    ]


def footprint_for(mask_ndim: int, radius: int) -> np.ndarray:
    if radius <= 0:
        return np.ones((1,) * mask_ndim, dtype=bool)
    if mask_ndim == 2:
        return morphology.disk(radius)
    if mask_ndim == 3:
        return morphology.ball(radius)
    raise ValueError(f"Unsupported mask dimensionality for morphology: {mask_ndim}")


def postprocess_mask(mask: np.ndarray, config: CandidateConfig) -> np.ndarray:
    cleaned = morphology.closing(mask, footprint=footprint_for(mask.ndim, config.closing_radius))
    small_object_kwargs = {"max_size": config.min_object_size}
    if "max_size" not in inspect.signature(morphology.remove_small_objects).parameters:
        small_object_kwargs = {"min_size": config.min_object_size}
    cleaned = morphology.remove_small_objects(cleaned, **small_object_kwargs)
    cleaned = morphology.remove_small_holes(cleaned, max_size=config.max_hole_size)
    return cleaned


def summarize_components(mask: np.ndarray) -> tuple[int, float]:
    labels, component_count = ndi.label(mask)
    if component_count == 0:
        return 0, 0.0
    component_sizes = np.bincount(labels.ravel())[1:]
    largest_fraction = float(component_sizes.max() / mask.size)
    return int(component_count), largest_fraction


def evaluate_candidate(
    volume: np.ndarray,
    config: CandidateConfig,
    thresholds: dict[str, float],
) -> tuple[np.ndarray, dict[str, Any]]:
    threshold_value = thresholds[config.threshold_method]
    if config.polarity == "bright":
        raw_mask = volume >= threshold_value
    elif config.polarity == "dark":
        raw_mask = volume <= threshold_value
    else:
        raise ValueError(f"Unsupported polarity: {config.polarity}")

    mask = postprocess_mask(raw_mask, config)

    gradient = filters.sobel(normalize_for_display(volume))
    boundaries = segmentation.find_boundaries(mask, mode="inner")
    boundary_gradient_mean = float(gradient[boundaries].mean()) if boundaries.any() else 0.0

    foreground_fraction = float(mask.mean())
    foreground_count = int(mask.sum())
    background_count = int(mask.size - foreground_count)

    if foreground_count == 0 or background_count == 0:
        intensity_contrast = 0.0
        foreground_mean = float("nan")
        background_mean = float("nan")
    else:
        foreground_mean = float(volume[mask].mean())
        background_mean = float(volume[~mask].mean())
        intensity_contrast = abs(foreground_mean - background_mean) / (float(volume.std()) + 1e-8)

    component_count, largest_component_fraction = summarize_components(mask)

    extreme_fraction_penalty = 0.0
    if foreground_fraction < 0.02:
        extreme_fraction_penalty += 1.0
    if foreground_fraction > 0.98:
        extreme_fraction_penalty += 1.0

    score = (
        2.5 * boundary_gradient_mean
        + 0.5 * intensity_contrast
        + 1.0 * largest_component_fraction
        - 0.15 * math.log1p(component_count)
        - 0.5 * extreme_fraction_penalty
    )

    metrics = {
        "name": config.name,
        "threshold_method": config.threshold_method,
        "threshold_value": threshold_value,
        "polarity": config.polarity,
        "closing_radius": config.closing_radius,
        "min_object_size": config.min_object_size,
        "max_hole_size": config.max_hole_size,
        "foreground_voxels": foreground_count,
        "background_voxels": background_count,
        "foreground_fraction": foreground_fraction,
        "foreground_mean_intensity": foreground_mean,
        "background_mean_intensity": background_mean,
        "intensity_contrast": intensity_contrast,
        "boundary_gradient_mean": boundary_gradient_mean,
        "component_count": component_count,
        "largest_component_fraction": largest_component_fraction,
        "score": float(score),
    }
    return mask, metrics


def normalize_for_display(array: np.ndarray) -> np.ndarray:
    low = float(np.quantile(array, 0.01))
    high = float(np.quantile(array, 0.99))
    if high <= low:
        return np.zeros_like(array, dtype=np.float32)
    clipped = np.clip(array, low, high)
    return ((clipped - low) / (high - low)).astype(np.float32)


def representative_slice_index(volume: np.ndarray) -> int:
    return min(380, int(volume.shape[0] - 1))


def save_histogram(
    volume: np.ndarray,
    thresholds: dict[str, float],
    output_path: Path,
) -> None:
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.hist(volume.ravel(), bins=256, color="#365c8d", alpha=0.85)
    for name, value in thresholds.items():
        ax.axvline(value, linewidth=1.5, label=f"{name}: {value:.1f}")
    ax.set_title("Intensity Histogram")
    ax.set_xlabel("Intensity")
    ax.set_ylabel("Voxel Count")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def save_overview(
    volume: np.ndarray,
    candidate_results: list[dict[str, Any]],
    output_path: Path,
) -> None:
    display_volume = normalize_for_display(volume)
    slice_index = representative_slice_index(volume)
    rows = len(candidate_results) + 1
    fig, axes = plt.subplots(rows, 3, figsize=(13, 4 * rows))

    if rows == 1:
        axes = np.asarray([axes])

    axes[0, 0].imshow(display_volume[slice_index], cmap="gray")
    axes[0, 0].set_title(f"Readable slice {slice_index}")
    axes[0, 1].hist(volume.ravel(), bins=256, color="#365c8d", alpha=0.9)
    axes[0, 1].set_title("Intensity Histogram")
    axes[0, 2].axis("off")
    axes[0, 2].text(
        0.0,
        0.95,
        "Optimization summary",
        va="top",
        fontsize=12,
        fontweight="bold",
    )

    for row_index, result in enumerate(candidate_results, start=1):
        mask = result["mask"]
        metrics = result["metrics"]
        overlay = np.dstack([display_volume[slice_index]] * 3)
        overlay[..., 0] = np.maximum(overlay[..., 0], mask[slice_index].astype(np.float32))

        axes[row_index, 0].imshow(display_volume[slice_index], cmap="gray")
        axes[row_index, 0].set_title(metrics["name"])
        axes[row_index, 1].imshow(mask[slice_index], cmap="gray")
        axes[row_index, 1].set_title(f"Mask frac={metrics['foreground_fraction']:.3f}")
        axes[row_index, 2].imshow(overlay)
        axes[row_index, 2].set_title(f"Score={metrics['score']:.3f}")
        axes[row_index, 2].text(
            0.02,
            0.02,
            (
                f"method={metrics['threshold_method']}  polarity={metrics['polarity']}\n"
                f"thr={metrics['threshold_value']:.1f}  comps={metrics['component_count']}\n"
                f"close={metrics['closing_radius']}  min_obj={metrics['min_object_size']}"
            ),
            transform=axes[row_index, 2].transAxes,
            fontsize=8,
            va="bottom",
            ha="left",
            color="white",
            bbox={"facecolor": "black", "alpha": 0.55, "pad": 3},
        )

    for ax_row in axes:
        for ax in ax_row:
            ax.set_xticks([])
            ax.set_yticks([])

    fig.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def save_mask_slice_png(
    volume: np.ndarray,
    mask: np.ndarray,
    metadata: dict[str, Any],
    output_path: Path,
) -> None:
    display_volume = normalize_for_display(volume)
    slice_index = representative_slice_index(volume)
    title = f"Mask visualization for slice {slice_index}"
    if metadata["read_mode"] == "2d_fallback":
        title = "Requested slice 380 unavailable; showing readable page 0"

    fig, axes = plt.subplots(1, 3, figsize=(12, 4.5))
    overlay = np.dstack([display_volume[slice_index]] * 3)
    overlay[..., 1] = np.maximum(overlay[..., 1], mask[slice_index].astype(np.float32))

    axes[0].imshow(display_volume[slice_index], cmap="gray")
    axes[0].set_title("Raw")
    axes[1].imshow(mask[slice_index], cmap="gray")
    axes[1].set_title("Mask")
    axes[2].imshow(overlay)
    axes[2].set_title("Overlay")
    fig.suptitle(title)

    for ax in axes:
        ax.set_xticks([])
        ax.set_yticks([])

    fig.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)


def mask_output_name(input_path: Path) -> str:
    if input_path.stem == "9x9x9_octet_lattice":
        return "9x9x9_octet_lattice_mask.tif"
    return f"{input_path.stem}_mask.tif"


def save_mask(mask: np.ndarray, metadata: dict[str, Any], output_path: Path) -> None:
    save_array = (mask.astype(np.uint8) * 255)
    if metadata["read_mode"] == "2d_fallback":
        save_array = save_array[0]
    tifffile.imwrite(output_path, save_array, photometric="minisblack")


def volume_statistics(volume: np.ndarray) -> dict[str, Any]:
    quantiles = [0.0, 0.001, 0.01, 0.05, 0.25, 0.5, 0.75, 0.95, 0.99, 0.999, 1.0]
    return {
        "shape": tuple(int(v) for v in volume.shape),
        "dtype": str(volume.dtype),
        "min": float(volume.min()),
        "max": float(volume.max()),
        "mean": float(volume.mean()),
        "std": float(volume.std()),
        "quantiles": {f"{q:.3f}": float(np.quantile(volume, q)) for q in quantiles},
    }


def write_report(
    input_path: Path,
    output_dir: Path,
    metadata: dict[str, Any],
    stats: dict[str, Any],
    thresholds: dict[str, float],
    candidate_results: list[dict[str, Any]],
    best_result: dict[str, Any],
) -> None:
    mask_path = output_dir / mask_output_name(input_path)
    report_path = output_dir / "segmentation_report.md"
    slice_png_path = output_dir / "mask_slice_380.png"
    histogram_path = output_dir / "intensity_histogram.png"
    overview_path = output_dir / "optimization_overview.png"

    best_metrics = best_result["metrics"]

    lines: list[str] = []
    lines.append("# Segmentation Report")
    lines.append("")
    lines.append("## Inputs")
    lines.append(f"- Input dataset: `{input_path}`")
    lines.append(f"- Output directory: `{output_dir}`")
    lines.append(f"- Read mode: `{metadata['read_mode']}`")
    if metadata["fallback_note"]:
        lines.append(f"- Limitation: {metadata['fallback_note']}")
    lines.append(f"- TIFF series count: `{metadata['series_count']}`")
    lines.append(f"- TIFF page count: `{metadata['page_count']}`")
    lines.append(f"- TIFF reported shape: `{metadata['series_shape']}`")
    lines.append(f"- TIFF axes: `{metadata['series_axes']}`")
    lines.append(f"- Working array shape: `{metadata['working_shape']}`")
    lines.append("")
    lines.append("## Intensity Statistics")
    lines.append(f"- Min: `{stats['min']:.3f}`")
    lines.append(f"- Max: `{stats['max']:.3f}`")
    lines.append(f"- Mean: `{stats['mean']:.3f}`")
    lines.append(f"- Std: `{stats['std']:.3f}`")
    lines.append(f"- Quantiles: `{stats['quantiles']}`")
    lines.append(f"- Threshold estimates: `{ {k: round(v, 3) for k, v in thresholds.items()} }`")
    lines.append("")
    lines.append("## Final Selection")
    lines.append(f"- Selected candidate: `{best_metrics['name']}`")
    lines.append(f"- Threshold method: `{best_metrics['threshold_method']}`")
    lines.append(f"- Threshold value: `{best_metrics['threshold_value']:.3f}`")
    lines.append(f"- Polarity: `{best_metrics['polarity']}`")
    lines.append(f"- Closing radius: `{best_metrics['closing_radius']}`")
    lines.append(f"- Minimum object size: `{best_metrics['min_object_size']}`")
    lines.append(f"- Maximum hole size: `{best_metrics['max_hole_size']}`")
    lines.append(f"- Foreground voxel count: `{best_metrics['foreground_voxels']}`")
    lines.append(f"- Background voxel count: `{best_metrics['background_voxels']}`")
    lines.append(f"- Foreground fraction: `{best_metrics['foreground_fraction']:.6f}`")
    lines.append(f"- Score: `{best_metrics['score']:.6f}`")
    lines.append("")
    lines.append("## Optimization Iterations")
    lines.append("")
    lines.append("| Iteration | Candidate | Threshold | Polarity | Close | Min object | Max hole | Foreground fraction | Components | Score | Note |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")

    best_score_so_far = -float("inf")
    for iteration_index, result in enumerate(candidate_results, start=1):
        metrics = result["metrics"]
        if metrics["score"] > best_score_so_far:
            note = "improved best"
            best_score_so_far = metrics["score"]
        else:
            note = "no improvement"
        lines.append(
            "| "
            + " | ".join(
                [
                    str(iteration_index),
                    metrics["name"],
                    f"{metrics['threshold_method']}={metrics['threshold_value']:.3f}",
                    metrics["polarity"],
                    str(metrics["closing_radius"]),
                    str(metrics["min_object_size"]),
                    str(metrics["max_hole_size"]),
                    f"{metrics['foreground_fraction']:.6f}",
                    str(metrics["component_count"]),
                    f"{metrics['score']:.6f}",
                    note,
                ]
            )
            + " |"
        )

    lines.append("")
    lines.append("## Outputs")
    lines.append(f"- Script: `{output_dir / 'segment_lattice.py'}`")
    lines.append(f"- Final mask: `{mask_path}`")
    lines.append(f"- Slice visualization: `{slice_png_path}`")
    lines.append(f"- Histogram: `{histogram_path}`")
    lines.append(f"- Optimization overview: `{overview_path}`")
    lines.append(f"- Report: `{report_path}`")
    lines.append("")
    lines.append("## Notes")
    if metadata["read_mode"] == "2d_fallback":
        lines.append(
            "- The requested `mask_slice_380.png` could not represent slice 380 because the readable TIFF data exposed only one page. "
            "The output image shows page 0 with the required filename."
        )
    else:
        lines.append("- `mask_slice_380.png` uses slice 380, or the last slice if the stack is shorter than 381 slices.")

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    input_path = args.input.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / ".mplconfig").mkdir(parents=True, exist_ok=True)

    volume, metadata = inspect_and_load_dataset(input_path)
    thresholds = compute_thresholds(volume)
    stats = volume_statistics(volume)

    save_histogram(volume, thresholds, output_dir / "intensity_histogram.png")

    candidate_results: list[dict[str, Any]] = []
    best_result: dict[str, Any] | None = None
    failed_attempts = 0

    for iteration_count, config in enumerate(build_candidates(), start=1):
        if iteration_count > MAX_OPTIMIZATION_ITERATIONS:
            break

        mask, metrics = evaluate_candidate(volume, config, thresholds)
        candidate_result = {"config": config, "mask": mask, "metrics": metrics}
        candidate_results.append(candidate_result)

        if best_result is None or metrics["score"] > best_result["metrics"]["score"]:
            best_result = candidate_result
            failed_attempts = 0
        else:
            failed_attempts += 1

        if failed_attempts >= MAX_FAILED_ATTEMPTS:
            break

    if best_result is None:
        raise RuntimeError("No candidate masks were evaluated.")

    save_overview(volume, candidate_results, output_dir / "optimization_overview.png")
    save_mask(best_result["mask"], metadata, output_dir / mask_output_name(input_path))
    save_mask_slice_png(volume, best_result["mask"], metadata, output_dir / "mask_slice_380.png")
    write_report(input_path, output_dir, metadata, stats, thresholds, candidate_results, best_result)


if __name__ == "__main__":
    main()
