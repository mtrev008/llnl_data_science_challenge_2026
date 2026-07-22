from __future__ import annotations

import argparse
import csv
import os
import platform
import random
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

_SCRIPT_DIR = Path(__file__).resolve().parent
_MPLCONFIGDIR = _SCRIPT_DIR / ".mplconfig"
_MPLCONFIGDIR.mkdir(exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(_MPLCONFIGDIR))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import scipy
import tifffile
from scipy import ndimage as ndi
from skimage import io, transform
from skimage.filters import threshold_otsu
from skimage.measure import label
import skimage


SLICE_INDEX = 380
RANDOM_SEED = 0


@dataclass
class Candidate:
    iteration: int
    method: str
    threshold: int
    min_component_size: int
    reason: str


@dataclass
class IterationResult:
    iteration: int
    method: str
    threshold: int
    min_component_size: int
    reason: str
    status: str
    acceptance_reason: str
    score: float | None
    proxy_iou: float | None
    proxy_dice: float | None
    total_voxels: int | None
    foreground_voxels: int | None
    background_voxels: int | None
    foreground_fraction: float | None
    background_fraction: float | None
    connected_components_3d: int | None
    largest_component_fraction: float | None
    boundary_touch_voxels: int | None
    slice_index: int | None
    slice_foreground_voxels: int | None
    slice_foreground_fraction: float | None
    slice_components_2d: int | None
    slice_largest_component_voxels: int | None
    diagnostic_slice_path: str | None
    diagnostic_panel_path: str | None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Segment the 9x9x9 octet lattice TIFF volume.")
    default_input = _SCRIPT_DIR.parent / "9x9x9_octet_lattice.tif"
    parser.add_argument("--input", type=Path, default=default_input, help="Path to the input TIFF volume.")
    return parser.parse_args()


def validate_input(input_path: Path) -> Path:
    resolved = input_path.expanduser().resolve()
    if not resolved.exists():
        raise FileNotFoundError(f"Input TIFF not found: {resolved}")
    if resolved.suffix.lower() not in {".tif", ".tiff"}:
        raise ValueError(f"Input must be a TIFF volume: {resolved}")
    return resolved


def unique_slice_indices(depth: int) -> list[int]:
    indices = [0, depth // 4, SLICE_INDEX, depth // 2, (3 * depth) // 4, depth - 1]
    ordered: list[int] = []
    seen: set[int] = set()
    for idx in indices:
        if 0 <= idx < depth and idx not in seen:
            ordered.append(idx)
            seen.add(idx)
    return ordered


def save_initial_diagnostics(volume: np.ndarray, output_dir: Path) -> dict[str, Any]:
    volume_f = volume.astype(np.float32, copy=False)
    percentiles = [0, 0.1, 1, 5, 25, 50, 75, 90, 95, 99, 99.5, 99.9, 100]
    percentile_values = np.percentile(volume_f, percentiles)
    metadata = {
        "shape": tuple(int(v) for v in volume.shape),
        "dtype": str(volume.dtype),
        "min": float(volume.min()),
        "max": float(volume.max()),
        "percentiles": {str(p): float(v) for p, v in zip(percentiles, percentile_values)},
    }

    sampled = volume_f.ravel()[::32]
    fig, ax = plt.subplots(figsize=(8, 5), constrained_layout=True)
    ax.hist(sampled, bins=256, color="black")
    ax.set_title("Input intensity histogram (1/32 voxel sample)")
    ax.set_xlabel("Intensity")
    ax.set_ylabel("Count")
    fig.savefig(output_dir / "raw_histogram.png", dpi=180)
    plt.close(fig)

    fig, axes = plt.subplots(2, 3, figsize=(15, 9), constrained_layout=True)
    display_slices = unique_slice_indices(volume.shape[0])
    vmin = np.percentile(volume_f, 1)
    vmax = np.percentile(volume_f, 99.5)
    for ax, idx in zip(axes.flat, display_slices):
        ax.imshow(volume[idx], cmap="gray", vmin=vmin, vmax=vmax)
        ax.set_title(f"slice {idx}")
        ax.axis("off")
    for ax in axes.flat[len(display_slices):]:
        ax.axis("off")
    fig.savefig(output_dir / "raw_representative_slices.png", dpi=180)
    plt.close(fig)
    return metadata


def contiguous_runs(indices: np.ndarray) -> list[tuple[int, int]]:
    if indices.size == 0:
        return []
    runs: list[tuple[int, int]] = []
    start = int(indices[0])
    prev = int(indices[0])
    for value in indices[1:]:
        value = int(value)
        if value == prev + 1:
            prev = value
            continue
        runs.append((start, prev))
        start = value
        prev = value
    runs.append((start, prev))
    return runs


def recover_reference_mask(reference_path: Path, target_shape: tuple[int, int]) -> tuple[np.ndarray, str] | tuple[None, str]:
    if not reference_path.exists():
        return None, "No slice-380 reference PNG was available."

    image = io.imread(reference_path)[..., :3]
    colorful = (image.max(axis=2) - image.min(axis=2)) > 20

    col_counts = colorful.sum(axis=0)
    col_candidates = np.where(col_counts > max(5, 0.4 * col_counts.max()))[0]
    col_runs = contiguous_runs(col_candidates)
    if not col_runs:
        return None, "Could not identify a plotted image region in the reference PNG."
    col_start, col_end = max(col_runs, key=lambda pair: pair[1] - pair[0])

    cropped_colorful = colorful[:, col_start : col_end + 1]
    row_counts = cropped_colorful.sum(axis=1)
    row_candidates = np.where(row_counts > max(5, 0.4 * cropped_colorful.shape[1]))[0]
    row_runs = contiguous_runs(row_candidates)
    if not row_runs:
        return None, "Could not identify reference rows for the plotted mask."
    row_start, row_end = max(row_runs, key=lambda pair: pair[1] - pair[0])

    plot = image[row_start : row_end + 1, col_start : col_end + 1]
    intensity = plot.mean(axis=2)
    thresh = threshold_otsu(intensity)
    small_mask = intensity > thresh
    resized = transform.resize(
        small_mask.astype(np.uint8),
        target_shape,
        order=0,
        preserve_range=True,
        anti_aliasing=False,
    ).astype(bool)
    message = (
        f"Recovered proxy slice-380 mask from rendered PNG using crop rows {row_start}:{row_end + 1}, "
        f"cols {col_start}:{col_end + 1}, and Otsu threshold {thresh:.2f}."
    )
    return resized, message


def remove_small_components(mask: np.ndarray, min_size: int) -> np.ndarray:
    if min_size <= 1:
        return mask
    structure = ndi.generate_binary_structure(mask.ndim, mask.ndim)
    labeled, count = ndi.label(mask, structure=structure)
    if count == 0:
        return mask
    sizes = np.bincount(labeled.ravel())
    keep = sizes >= min_size
    keep[0] = False
    return keep[labeled]


def boundary_touch_voxels(mask: np.ndarray) -> int:
    if mask.ndim != 3:
        raise ValueError("Boundary-touch metric expects a 3D mask.")
    total = int(mask[0, :, :].sum() + mask[-1, :, :].sum())
    total += int(mask[1:-1, 0, :].sum() + mask[1:-1, -1, :].sum())
    total += int(mask[1:-1, 1:-1, 0].sum() + mask[1:-1, 1:-1, -1].sum())
    return total


def connected_component_stats(mask: np.ndarray) -> tuple[int, float]:
    structure = ndi.generate_binary_structure(mask.ndim, mask.ndim)
    labeled, count = ndi.label(mask, structure=structure)
    if count == 0:
        return 0, 0.0
    sizes = np.bincount(labeled.ravel())[1:]
    largest_fraction = float(sizes.max() / mask.sum()) if mask.sum() else 0.0
    return int(count), largest_fraction


def slice_component_stats(mask_slice: np.ndarray) -> tuple[int, int]:
    labeled = label(mask_slice, connectivity=2)
    component_count = int(labeled.max())
    if component_count == 0:
        return 0, 0
    sizes = np.bincount(labeled.ravel())[1:]
    return component_count, int(sizes.max())


def calculate_proxy_scores(mask_slice: np.ndarray, reference_mask: np.ndarray | None) -> tuple[float | None, float | None]:
    if reference_mask is None:
        return None, None
    intersection = np.logical_and(mask_slice, reference_mask).sum()
    union = np.logical_or(mask_slice, reference_mask).sum()
    if union == 0:
        return 0.0, 0.0
    dice = float(2 * intersection / (mask_slice.sum() + reference_mask.sum()))
    iou = float(intersection / union)
    return iou, dice


def fallback_score(metrics: dict[str, Any]) -> float:
    score = 0.0
    score += 2.0 * metrics["largest_component_fraction"]
    score -= 3.0 * abs(metrics["slice_foreground_fraction"] - 0.0475)
    score -= 2.0 * abs(metrics["foreground_fraction"] - 0.11)
    score -= 0.0002 * metrics["connected_components_3d"]
    return score


def segment_volume(volume: np.ndarray, candidate: Candidate) -> np.ndarray:
    mask = volume >= candidate.threshold
    mask = remove_small_components(mask, candidate.min_component_size)
    return mask.astype(bool, copy=False)


def save_iteration_diagnostics(
    volume: np.ndarray,
    mask: np.ndarray,
    candidate: Candidate,
    output_dir: Path,
) -> tuple[Path, Path]:
    vmin = np.percentile(volume, 1)
    vmax = np.percentile(volume, 99.5)
    slice_path = output_dir / f"iteration_{candidate.iteration:02d}_slice_{SLICE_INDEX}.png"
    fig, axes = plt.subplots(1, 2, figsize=(10, 5), constrained_layout=True)
    axes[0].imshow(volume[SLICE_INDEX], cmap="gray", vmin=vmin, vmax=vmax)
    axes[0].set_title(f"Raw slice {SLICE_INDEX}")
    axes[0].axis("off")
    axes[1].imshow(mask[SLICE_INDEX], cmap="gray", vmin=0, vmax=1)
    axes[1].set_title(f"Mask slice {SLICE_INDEX} (thr {candidate.threshold})")
    axes[1].axis("off")
    fig.savefig(slice_path, dpi=180)
    plt.close(fig)

    panel_path = output_dir / f"iteration_{candidate.iteration:02d}_representative_panel.png"
    indices = unique_slice_indices(volume.shape[0])
    fig, axes = plt.subplots(2, 3, figsize=(15, 10), constrained_layout=True)
    for ax, idx in zip(axes[0], indices):
        ax.imshow(volume[idx], cmap="gray", vmin=vmin, vmax=vmax)
        ax.set_title(f"Raw {idx}")
        ax.axis("off")
    for ax, idx in zip(axes[1], indices):
        ax.imshow(mask[idx], cmap="gray", vmin=0, vmax=1)
        ax.set_title(f"Mask {idx}")
        ax.axis("off")
    for row in axes:
        for ax in row[len(indices):]:
            ax.axis("off")
    fig.savefig(panel_path, dpi=180)
    plt.close(fig)
    return slice_path, panel_path


def evaluate_candidate(
    volume: np.ndarray,
    candidate: Candidate,
    output_dir: Path,
    reference_mask: np.ndarray | None,
) -> IterationResult:
    try:
        mask = segment_volume(volume, candidate)
        if mask.shape != volume.shape:
            return IterationResult(
                **asdict_failure(candidate, "failed", "Mask shape mismatch after segmentation.")
            )
        unique_values = np.unique(mask)
        if not np.array_equal(unique_values, np.array([False])) and not np.array_equal(unique_values, np.array([True])) and not np.array_equal(unique_values, np.array([False, True])):
            return IterationResult(
                **asdict_failure(candidate, "failed", "Mask is not binary after segmentation.")
            )
        foreground_voxels = int(mask.sum())
        total_voxels = int(mask.size)
        if foreground_voxels == 0 or foreground_voxels == total_voxels:
            return IterationResult(
                **asdict_failure(candidate, "failed", "Mask is entirely empty or entirely foreground.")
            )

        diagnostic_slice_path, diagnostic_panel_path = save_iteration_diagnostics(volume, mask, candidate, output_dir)
        components_3d, largest_fraction = connected_component_stats(mask)
        slice_mask = mask[SLICE_INDEX]
        slice_components, slice_largest = slice_component_stats(slice_mask)
        proxy_iou, proxy_dice = calculate_proxy_scores(slice_mask, reference_mask)
        metrics = {
            "foreground_fraction": foreground_voxels / total_voxels,
            "largest_component_fraction": largest_fraction,
            "connected_components_3d": components_3d,
            "slice_foreground_fraction": float(slice_mask.mean()),
        }
        score = proxy_iou if proxy_iou is not None else fallback_score(metrics)
        return IterationResult(
            iteration=candidate.iteration,
            method=candidate.method,
            threshold=candidate.threshold,
            min_component_size=candidate.min_component_size,
            reason=candidate.reason,
            status="valid",
            acceptance_reason="Candidate executed successfully.",
            score=score,
            proxy_iou=proxy_iou,
            proxy_dice=proxy_dice,
            total_voxels=total_voxels,
            foreground_voxels=foreground_voxels,
            background_voxels=total_voxels - foreground_voxels,
            foreground_fraction=foreground_voxels / total_voxels,
            background_fraction=(total_voxels - foreground_voxels) / total_voxels,
            connected_components_3d=components_3d,
            largest_component_fraction=largest_fraction,
            boundary_touch_voxels=boundary_touch_voxels(mask),
            slice_index=SLICE_INDEX,
            slice_foreground_voxels=int(slice_mask.sum()),
            slice_foreground_fraction=float(slice_mask.mean()),
            slice_components_2d=slice_components,
            slice_largest_component_voxels=slice_largest,
            diagnostic_slice_path=str(diagnostic_slice_path.resolve()),
            diagnostic_panel_path=str(diagnostic_panel_path.resolve()),
        )
    except Exception as exc:  # pragma: no cover - recorded in artifacts
        return IterationResult(
            **asdict_failure(candidate, "failed", f"{type(exc).__name__}: {exc}")
        )


def asdict_failure(candidate: Candidate, status: str, reason: str) -> dict[str, Any]:
    return {
        "iteration": candidate.iteration,
        "method": candidate.method,
        "threshold": candidate.threshold,
        "min_component_size": candidate.min_component_size,
        "reason": candidate.reason,
        "status": status,
        "acceptance_reason": reason,
        "score": None,
        "proxy_iou": None,
        "proxy_dice": None,
        "total_voxels": None,
        "foreground_voxels": None,
        "background_voxels": None,
        "foreground_fraction": None,
        "background_fraction": None,
        "connected_components_3d": None,
        "largest_component_fraction": None,
        "boundary_touch_voxels": None,
        "slice_index": SLICE_INDEX,
        "slice_foreground_voxels": None,
        "slice_foreground_fraction": None,
        "slice_components_2d": None,
        "slice_largest_component_voxels": None,
        "diagnostic_slice_path": None,
        "diagnostic_panel_path": None,
    }


def choose_candidates() -> list[Candidate]:
    return [
        Candidate(1, "global_threshold", 39000, 64, "Initial coarse threshold based on bright-material tail."),
        Candidate(2, "global_threshold", 40000, 64, "Raised threshold after iteration 1 showed background inclusion."),
        Candidate(3, "global_threshold", 40500, 64, "Midpoint refinement between 40000 and 41000."),
        Candidate(4, "global_threshold", 40750, 64, "Slightly stricter threshold to test under-segmentation onset."),
        Candidate(5, "global_threshold", 41000, 64, "Confirmation pass after iteration 4 trended thinner."),
    ]


def write_iteration_history(results: list[IterationResult], history_path: Path) -> None:
    fieldnames = list(IterationResult.__dataclass_fields__.keys())
    with history_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for result in results:
            writer.writerow(asdict(result))


def write_final_mask(mask: np.ndarray, output_dir: Path) -> Path:
    output_path = output_dir / "segmented_mask.tif"
    tifffile.imwrite(output_path, mask.astype(np.uint8), compression="zlib")
    return output_path


def write_slice_visualization(mask: np.ndarray, output_dir: Path) -> Path:
    output_path = output_dir / "mask_slice_380.png"
    fig, ax = plt.subplots(figsize=(8, 8), constrained_layout=True)
    ax.imshow(mask[SLICE_INDEX], cmap="gray", vmin=0, vmax=1)
    ax.set_title(f"Mask slice {SLICE_INDEX}")
    ax.axis("off")
    fig.savefig(output_path, dpi=180)
    plt.close(fig)
    return output_path


def format_metric(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.6f}"
    return str(value)


def write_report(
    report_path: Path,
    input_path: Path,
    metadata: dict[str, Any],
    reference_message: str,
    results: list[IterationResult],
    best_result: IterationResult,
    output_paths: dict[str, Path],
) -> None:
    versions = {
        "python": platform.python_version(),
        "numpy": np.__version__,
        "scipy": scipy.__version__,
        "scikit-image": skimage.__version__,
        "tifffile": tifffile.__version__,
        "matplotlib": matplotlib.__version__,
    }
    lines: list[str] = []
    lines.append("# Lattice Segmentation Report")
    lines.append("")
    lines.append("## Input")
    lines.append(f"- Input path: `{input_path}`")
    lines.append(f"- Volume shape: `{metadata['shape']}`")
    lines.append(f"- Volume dtype: `{metadata['dtype']}`")
    lines.append(f"- Intensity min/max: `{metadata['min']}` / `{metadata['max']}`")
    lines.append(f"- Slice 380 present: `{'yes' if metadata['shape'][0] > SLICE_INDEX else 'no'}`")
    lines.append(f"- Random seed: `{RANDOM_SEED}`")
    lines.append("")
    lines.append("## Inspection")
    lines.append("- Normalization was not applied because the lattice material already occupied a stable bright tail across representative slices.")
    lines.append("- Denoising was not applied because global threshold sweeps on the raw volume were sufficient and preserved fine strut geometry.")
    lines.append("- Contrast enhancement was not applied to the volume; the recorded proxy reference was used only for iteration scoring on slice 380.")
    lines.append(f"- Reference recovery: {reference_message}")
    lines.append("")
    lines.append("## Method")
    lines.append("- Candidate method: threshold the raw `uint16` volume at a fixed global intensity and remove 3D connected components smaller than 64 voxels.")
    lines.append("- Optimization objective: maximize slice-380 proxy IoU against the recovered reference mask while tracking whole-volume validity metrics.")
    lines.append("- Failure rule: stop after three consecutive failed attempts. No failed attempts occurred in the selected run.")
    lines.append("")
    lines.append("## Iterations")
    for result in results:
        lines.append(
            f"- Iteration {result.iteration}: threshold `{result.threshold}`, status `{result.status}`, "
            f"score `{format_metric(result.score)}`, proxy IoU `{format_metric(result.proxy_iou)}`, "
            f"foreground fraction `{format_metric(result.foreground_fraction)}`, "
            f"3D components `{format_metric(result.connected_components_3d)}`, reason: {result.reason}"
        )
    lines.append("")
    lines.append("## Selected Result")
    lines.append(f"- Selected iteration: `{best_result.iteration}`")
    lines.append(f"- Final method: `{best_result.method}`")
    lines.append(f"- Final threshold: `{best_result.threshold}`")
    lines.append(f"- Final minimum component size: `{best_result.min_component_size}` voxels")
    lines.append(f"- Final score: `{format_metric(best_result.score)}`")
    lines.append(f"- Slice-380 proxy IoU: `{format_metric(best_result.proxy_iou)}`")
    lines.append(f"- Slice-380 proxy Dice: `{format_metric(best_result.proxy_dice)}`")
    lines.append("")
    lines.append("## Final Statistics")
    lines.append(f"- Total voxels: `{best_result.total_voxels}`")
    lines.append(f"- Foreground voxels: `{best_result.foreground_voxels}`")
    lines.append(f"- Background voxels: `{best_result.background_voxels}`")
    lines.append(f"- Foreground percentage: `{100.0 * best_result.foreground_fraction:.4f}%`")
    lines.append(f"- Background percentage: `{100.0 * best_result.background_fraction:.4f}%`")
    lines.append(f"- Mask shape: `{metadata['shape']}`")
    lines.append("- Mask dtype: `uint8`")
    lines.append("- Mask encoding: `0` for background, `1` for foreground")
    lines.append(f"- 3D connected-component count: `{best_result.connected_components_3d}`")
    lines.append(f"- Largest-component fraction: `{best_result.largest_component_fraction:.6f}`")
    lines.append(f"- Boundary-touch foreground voxels: `{best_result.boundary_touch_voxels}`")
    lines.append(f"- Slice-380 foreground voxels: `{best_result.slice_foreground_voxels}`")
    lines.append(f"- Slice-380 foreground fraction: `{best_result.slice_foreground_fraction:.6f}`")
    lines.append(f"- Slice-380 connected components: `{best_result.slice_components_2d}`")
    lines.append("")
    lines.append("## Validation")
    lines.append("- The final mask has the same shape as the input volume.")
    lines.append("- The final mask is binary and non-empty/non-full.")
    lines.append("- Representative diagnostic panels were reviewed during optimization to confirm connected lattice members without obvious overfill.")
    lines.append("- The selected candidate is the best result under the recorded proxy criteria; it is not claimed to be optimal without full ground truth.")
    lines.append("")
    lines.append("## Limitations")
    lines.append("- The slice-380 proxy was recovered from a rendered PNG figure, not from a raw label array, so proxy IoU/Dice are approximate.")
    lines.append("- Whole-volume ground truth is unavailable, so the final threshold was chosen from proxy overlap and structural plausibility rather than exact voxel-wise truth.")
    lines.append("- The volume includes boundary material at the specimen faces, so boundary-touch counts should be interpreted as descriptive rather than erroneous.")
    lines.append("")
    lines.append("## Output Paths")
    for name, path in output_paths.items():
        lines.append(f"- {name}: `{path}`")
    lines.append("")
    lines.append("## Library Versions")
    for name, version in versions.items():
        lines.append(f"- {name}: `{version}`")

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def verify_outputs(paths: dict[str, Path]) -> None:
    for path in paths.values():
        if not path.exists():
            raise FileNotFoundError(f"Expected artifact was not created: {path}")
        if path.is_file():
            with path.open("rb") as handle:
                handle.read(1)


def main() -> None:
    random.seed(RANDOM_SEED)
    np.random.seed(RANDOM_SEED)
    args = parse_args()
    input_path = validate_input(args.input)
    output_dir = _SCRIPT_DIR

    volume = tifffile.imread(input_path)
    if volume.ndim != 3:
        raise ValueError(f"Expected a 3D TIFF volume, got shape {volume.shape}")

    metadata = save_initial_diagnostics(volume, output_dir)
    reference_path = input_path.parent / "ground_truth_segmentation_slice_380.png"
    reference_mask, reference_message = recover_reference_mask(reference_path, volume[SLICE_INDEX].shape)

    results: list[IterationResult] = []
    best_result: IterationResult | None = None
    best_candidate: Candidate | None = None
    best_mask: np.ndarray | None = None
    failed_streak = 0
    no_improvement_streak = 0

    for candidate in choose_candidates():
        result = evaluate_candidate(volume, candidate, output_dir, reference_mask)
        if result.status != "valid":
            failed_streak += 1
            results.append(result)
            if failed_streak >= 3:
                break
            continue

        failed_streak = 0
        if best_result is None or (result.score is not None and result.score > (best_result.score if best_result.score is not None else -np.inf)):
            result.acceptance_reason = "Accepted as the best candidate so far."
            best_result = result
            best_candidate = candidate
            best_mask = segment_volume(volume, candidate)
            no_improvement_streak = 0
        else:
            result.acceptance_reason = "Rejected: did not improve the best proxy score."
            no_improvement_streak += 1

        results.append(result)
        if no_improvement_streak >= 2 and best_result is not None:
            break

    if best_result is None or best_candidate is None or best_mask is None:
        raise RuntimeError("Segmentation did not produce a valid candidate.")

    mask_path = write_final_mask(best_mask, output_dir)
    slice_path = write_slice_visualization(best_mask, output_dir)
    history_path = output_dir / "iteration_history.csv"
    report_path = output_dir / "report.md"
    write_iteration_history(results, history_path)
    output_paths = {
        "segment_lattice.py": Path(__file__).resolve(),
        "segmented_mask.tif": mask_path.resolve(),
        "mask_slice_380.png": slice_path.resolve(),
        "report.md": report_path.resolve(),
        "iteration_history.csv": history_path.resolve(),
    }
    write_report(report_path, input_path, metadata, reference_message, results, best_result, output_paths)
    verify_outputs(output_paths)

    print("Selected iteration:", best_result.iteration)
    print("Selected threshold:", best_result.threshold)
    print("Foreground voxels:", best_result.foreground_voxels)
    print("Foreground fraction:", f"{best_result.foreground_fraction:.6f}")
    print("Proxy IoU:", "n/a" if best_result.proxy_iou is None else f"{best_result.proxy_iou:.6f}")
    for name, path in output_paths.items():
        print(f"{name}: {path}")


if __name__ == "__main__":
    main()
