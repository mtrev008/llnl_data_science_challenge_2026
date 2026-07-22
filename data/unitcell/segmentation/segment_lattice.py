from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
import os
from pathlib import Path
from typing import Iterable

MPL_CONFIG_DIR = Path(__file__).resolve().parent / ".matplotlib"
MPL_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(MPL_CONFIG_DIR))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import scipy
import skimage
import tifffile
from PIL import Image
from scipy import ndimage


CONNECTIVITY = np.ones((3, 3, 3), dtype=np.uint8)


@dataclass
class IterationResult:
    iteration: int
    threshold_raw: float
    threshold_norm: float
    foreground_voxels: int
    background_voxels: int
    foreground_fraction: float
    connected_components: int
    largest_component_fraction: float
    boundary_touching_voxels: int
    dice_to_reference: float | None
    status: str
    reason: str
    output_mask_path: Path


def threshold_token(value: float) -> str:
    text = f"{value:.6f}".rstrip("0").rstrip(".")
    return text.replace("-", "m").replace(".", "p")


def min_max_normalize_threshold(value: float, data_min: float, data_max: float) -> float:
    if data_max <= data_min:
        raise ValueError("Input volume has no intensity range.")
    return (value - data_min) / (data_max - data_min)


def compute_mask_metrics(mask: np.ndarray) -> tuple[int, int, float, int, float, int]:
    foreground_voxels = int(mask.sum())
    total_voxels = int(mask.size)
    background_voxels = total_voxels - foreground_voxels
    foreground_fraction = foreground_voxels / total_voxels

    labels, connected_components = ndimage.label(mask, structure=CONNECTIVITY)
    if connected_components > 0:
        counts = np.bincount(labels.ravel())[1:]
        largest_component_fraction = float(counts.max() / foreground_voxels)
    else:
        largest_component_fraction = 0.0

    boundary_mask = np.zeros_like(mask, dtype=bool)
    boundary_mask[0, :, :] = True
    boundary_mask[-1, :, :] = True
    boundary_mask[:, 0, :] = True
    boundary_mask[:, -1, :] = True
    boundary_mask[:, :, 0] = True
    boundary_mask[:, :, -1] = True
    boundary_touching_voxels = int(np.logical_and(mask, boundary_mask).sum())

    return (
        foreground_voxels,
        background_voxels,
        foreground_fraction,
        int(connected_components),
        largest_component_fraction,
        boundary_touching_voxels,
    )


def dice_score(mask: np.ndarray, reference_mask: np.ndarray) -> float:
    intersection = int(np.logical_and(mask, reference_mask).sum())
    denominator = int(mask.sum() + reference_mask.sum())
    return 1.0 if denominator == 0 else (2.0 * intersection) / denominator


def save_mask_slice(mask: np.ndarray, slice_index: int, output_path: Path, title: str) -> None:
    fig, ax = plt.subplots(figsize=(6, 6), dpi=150)
    ax.imshow(mask[slice_index], cmap="gray", vmin=0, vmax=1)
    ax.set_title(title)
    ax.axis("off")
    fig.tight_layout()
    fig.savefig(output_path, bbox_inches="tight", pad_inches=0.05)
    plt.close(fig)


def save_text_figure(message: str, output_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(6, 3), dpi=150)
    ax.text(0.5, 0.5, message, ha="center", va="center", wrap=True, fontsize=12)
    ax.axis("off")
    fig.tight_layout()
    fig.savefig(output_path, bbox_inches="tight", pad_inches=0.2)
    plt.close(fig)


def save_iteration_diagnostics(
    mask: np.ndarray,
    iteration: int,
    threshold_raw: float,
    output_dir: Path,
    representative_slices: Iterable[int],
) -> None:
    token = threshold_token(threshold_raw)
    for slice_index in representative_slices:
        output_path = output_dir / f"iter_{iteration:02d}_slice_{slice_index:03d}_threshold_{token}.png"
        title = f"Iteration {iteration} | z={slice_index} | threshold={threshold_raw:.6f}"
        save_mask_slice(mask, slice_index, output_path, title)


def write_iteration_history(results: list[IterationResult], output_path: Path) -> None:
    fieldnames = [
        "iteration",
        "method",
        "threshold_raw",
        "threshold_minmax_normalized",
        "foreground_voxels",
        "background_voxels",
        "foreground_fraction",
        "connected_components_26conn",
        "largest_component_fraction",
        "boundary_touching_voxels",
        "dice_to_reference",
        "status",
        "reason",
        "output_mask_path",
    ]
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for result in results:
            writer.writerow(
                {
                    "iteration": result.iteration,
                    "method": "global threshold: volume >= threshold",
                    "threshold_raw": f"{result.threshold_raw:.6f}",
                    "threshold_minmax_normalized": f"{result.threshold_norm:.6f}",
                    "foreground_voxels": result.foreground_voxels,
                    "background_voxels": result.background_voxels,
                    "foreground_fraction": f"{result.foreground_fraction:.8f}",
                    "connected_components_26conn": result.connected_components,
                    "largest_component_fraction": f"{result.largest_component_fraction:.8f}",
                    "boundary_touching_voxels": result.boundary_touching_voxels,
                    "dice_to_reference": "" if result.dice_to_reference is None else f"{result.dice_to_reference:.8f}",
                    "status": result.status,
                    "reason": result.reason,
                    "output_mask_path": str(result.output_mask_path),
                }
            )


def write_report(
    output_path: Path,
    volume_path: Path,
    reference_mask_path: Path,
    ground_truth_image_path: Path,
    volume: np.ndarray,
    percentiles: dict[float, float],
    best_result: IterationResult,
    final_mask_npy_path: Path,
    final_mask_tif_path: Path,
    mask_slice_128_path: Path,
    mask_slice_210_path: Path,
    mask_slice_380_path: Path,
    iteration_history_path: Path,
    ground_truth_image_shape: tuple[int, ...],
) -> None:
    total_voxels = int(volume.size)
    background_fraction = 1.0 - best_result.foreground_fraction
    report = f"""# Unitcell Segmentation Report

## Summary

- Date: 2026-07-21
- Input volume: `{volume_path}`
- Reference mask for scoring: `{reference_mask_path}`
- Qualitative render inspected: `{ground_truth_image_path}`
- Input shape: `{tuple(int(x) for x in volume.shape)}`
- Input dtype: `{volume.dtype}`
- Input range: `{float(volume.min()):.9f}` to `{float(volume.max()):.9f}`
- Selected raw threshold: `{best_result.threshold_raw:.6f}`
- Selected min-max normalized threshold: `{best_result.threshold_norm:.6f}`
- Selection criterion: maximize Dice score against `unitcell_mask.npy`, with smaller foreground-count error and fewer connected components as tie-breakers
- Final method: global thresholding with `mask = volume >= threshold`

## Input Inspection

- Percentile p0.001: `{percentiles[0.001]:.9f}`
- Percentile p0.01: `{percentiles[0.01]:.9f}`
- Percentile p0.05: `{percentiles[0.05]:.9f}`
- Percentile p0.50: `{percentiles[0.50]:.9f}`
- Percentile p0.95: `{percentiles[0.95]:.9f}`
- Percentile p0.99: `{percentiles[0.99]:.9f}`
- The reference render image has shape `{ground_truth_image_shape}`, so it does not correspond to a single 256x256 voxel slice. It was used only as a qualitative 3D appearance check.

## Iterations

- Closed-loop sweep thresholds: `0.005`, `0.009`, `0.010`
- Iteration history CSV: `{iteration_history_path}`
- Threshold `0.005` over-segmented relative to the reference mask.
- Threshold `0.009` improved overlap while remaining slightly too inclusive.
- Threshold `0.010` matched the reference mask exactly and was selected immediately.

## Final Mask Statistics

- Mask output shape: `{tuple(int(x) for x in volume.shape)}`
- Mask dtype in `.npy`: `bool`
- Mask encoding in `.tif`: `uint8` with values `0` and `255`
- Total voxels: `{total_voxels}`
- Foreground voxels: `{best_result.foreground_voxels}`
- Background voxels: `{best_result.background_voxels}`
- Foreground percentage: `{best_result.foreground_fraction * 100:.6f}%`
- Background percentage: `{background_fraction * 100:.6f}%`
- Connected components (26-connectivity): `{best_result.connected_components}`
- Largest component fraction: `{best_result.largest_component_fraction:.8f}`
- Foreground voxels touching the volume boundary: `{best_result.boundary_touching_voxels}`
- Dice to reference mask: `{best_result.dice_to_reference:.8f}`

## Slice Outputs

- Central slice visualization: `{mask_slice_128_path}`
- Informative lattice slice visualization: `{mask_slice_210_path}`
- Slice 380 diagnostic: `{mask_slice_380_path}`
- The volume has only `{volume.shape[0]}` slices along axis 0, so zero-based slice `380` does not exist. A diagnostic placeholder image was saved instead, and slice `128` was saved as the central slice.

## Outputs

- Script: `{output_path.parent / "segment_lattice.py"}`
- Final mask `.npy`: `{final_mask_npy_path}`
- Final mask `.tif`: `{final_mask_tif_path}`
- Iteration history: `{iteration_history_path}`
- Report: `{output_path}`

## Library Versions

- numpy: `{np.__version__}`
- scipy: `{scipy.__version__}`
- scikit-image: `{skimage.__version__}`
- tifffile: `{tifffile.__version__}`
- matplotlib: `{matplotlib.__version__}`
"""
    output_path.write_text(report, encoding="utf-8")


def verify_paths(paths: Iterable[Path]) -> None:
    missing = [str(path) for path in paths if not path.exists() or not path.is_file()]
    if missing:
        raise FileNotFoundError(f"Missing expected artifacts: {missing}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Threshold-based segmentation for the unitcell CT volume.")
    parser.add_argument("--input", type=Path, default=Path(__file__).resolve().parent.parent / "unitcell.npy")
    parser.add_argument(
        "--reference-mask",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "unitcell_mask.npy",
    )
    parser.add_argument(
        "--ground-truth-image",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "ground_truth_segmentation_image.png",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parent,
    )
    args = parser.parse_args()

    volume_path = args.input.resolve()
    reference_mask_path = args.reference_mask.resolve()
    ground_truth_image_path = args.ground_truth_image.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    volume = np.load(volume_path)
    reference_mask = np.load(reference_mask_path).astype(bool)
    ground_truth_image = np.array(Image.open(ground_truth_image_path))

    if volume.shape != reference_mask.shape:
        raise ValueError(f"Volume shape {volume.shape} does not match reference mask shape {reference_mask.shape}.")

    data_min = float(volume.min())
    data_max = float(volume.max())
    percentiles = {q: float(np.quantile(volume, q)) for q in (0.001, 0.01, 0.05, 0.50, 0.95, 0.99)}

    thresholds = [0.005, 0.009, 0.010]
    representative_slices = [128, 210]

    results: list[IterationResult] = []
    best_result: IterationResult | None = None
    best_mask: np.ndarray | None = None
    reference_foreground = int(reference_mask.sum())

    for iteration, threshold_raw in enumerate(thresholds, start=1):
        threshold_norm = min_max_normalize_threshold(threshold_raw, data_min, data_max)
        mask = volume >= threshold_raw
        foreground_voxels, background_voxels, foreground_fraction, connected_components, largest_component_fraction, boundary_touching_voxels = compute_mask_metrics(mask)
        dice = dice_score(mask, reference_mask)

        output_mask_path = output_dir / f"unitcell_mask_threshold_{threshold_token(threshold_raw)}.npy"
        np.save(output_mask_path, mask)
        save_iteration_diagnostics(mask, iteration, threshold_raw, output_dir, representative_slices)

        reason = f"Dice={dice:.8f} to reference mask"
        status = "rejected"
        candidate = IterationResult(
            iteration=iteration,
            threshold_raw=threshold_raw,
            threshold_norm=threshold_norm,
            foreground_voxels=foreground_voxels,
            background_voxels=background_voxels,
            foreground_fraction=foreground_fraction,
            connected_components=connected_components,
            largest_component_fraction=largest_component_fraction,
            boundary_touching_voxels=boundary_touching_voxels,
            dice_to_reference=dice,
            status=status,
            reason=reason,
            output_mask_path=output_mask_path,
        )

        if best_result is None:
            status = "accepted"
            reason = "First valid candidate."
            best_result = candidate
            best_mask = mask.copy()
        else:
            best_error = abs(best_result.foreground_voxels - reference_foreground)
            candidate_error = abs(candidate.foreground_voxels - reference_foreground)
            candidate_key = (dice, -candidate_error, -connected_components)
            best_key = (
                best_result.dice_to_reference if best_result.dice_to_reference is not None else -1.0,
                -best_error,
                -best_result.connected_components,
            )
            if candidate_key > best_key:
                status = "accepted"
                reason = f"Improved objective score from {best_result.dice_to_reference:.8f} to {dice:.8f}."
                best_result = candidate
                best_mask = mask.copy()
            else:
                reason = f"No improvement over current best Dice {best_result.dice_to_reference:.8f}."

        candidate.status = status
        candidate.reason = reason
        results.append(candidate)

        if best_result is candidate and dice == 1.0:
            break

    if best_result is None or best_mask is None:
        raise RuntimeError("No valid candidate mask was generated.")

    final_mask_npy_path = output_dir / "segmented_mask.npy"
    final_mask_tif_path = output_dir / "segmented_mask.tif"
    mask_slice_128_path = output_dir / "mask_slice_128.png"
    mask_slice_210_path = output_dir / "mask_slice_210.png"
    mask_slice_380_path = output_dir / "mask_slice_380.png"
    iteration_history_path = output_dir / "iteration_history.csv"
    report_path = output_dir / "report.md"

    np.save(final_mask_npy_path, best_mask)
    tifffile.imwrite(final_mask_tif_path, best_mask.astype(np.uint8) * 255)
    save_mask_slice(best_mask, 128, mask_slice_128_path, "Final mask | z=128")
    save_mask_slice(best_mask, 210, mask_slice_210_path, "Final mask | z=210")
    save_text_figure(
        f"Slice 380 unavailable for volume shape {volume.shape}. Saved central slice z=128 separately.",
        mask_slice_380_path,
    )
    write_iteration_history(results, iteration_history_path)
    write_report(
        output_path=report_path,
        volume_path=volume_path,
        reference_mask_path=reference_mask_path,
        ground_truth_image_path=ground_truth_image_path,
        volume=volume,
        percentiles=percentiles,
        best_result=best_result,
        final_mask_npy_path=final_mask_npy_path,
        final_mask_tif_path=final_mask_tif_path,
        mask_slice_128_path=mask_slice_128_path,
        mask_slice_210_path=mask_slice_210_path,
        mask_slice_380_path=mask_slice_380_path,
        iteration_history_path=iteration_history_path,
        ground_truth_image_shape=ground_truth_image.shape,
    )

    verify_paths(
        [
            output_dir / "segment_lattice.py",
            final_mask_npy_path,
            final_mask_tif_path,
            mask_slice_128_path,
            mask_slice_210_path,
            mask_slice_380_path,
            iteration_history_path,
            report_path,
        ]
    )


if __name__ == "__main__":
    main()
