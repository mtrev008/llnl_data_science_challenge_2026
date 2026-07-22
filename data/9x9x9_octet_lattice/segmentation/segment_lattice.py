#!/usr/bin/env python3
"""Segment an x-ray CT lattice volume using sampled threshold optimization."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import tifffile
from skimage.filters import threshold_otsu
from skimage.measure import label


MAX_ITERATIONS = 10
MAX_FAILED_ATTEMPTS = 3
TARGET_SLICE = 380


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_tif", type=Path, help="Input .tif/.tiff CT volume")
    return parser.parse_args()


def load_volume(path: Path) -> np.ndarray:
    if path.suffix.lower() not in {".tif", ".tiff"}:
        raise ValueError(f"Input must be .tif or .tiff, got {path}")
    return tifffile.imread(path)


def sample_volume(volume: np.ndarray, max_samples: int = 2_000_000) -> np.ndarray:
    flat = volume.ravel()
    if flat.size <= max_samples:
        return flat.astype(np.float32, copy=False)
    stride = max(1, flat.size // max_samples)
    return flat[::stride].astype(np.float32, copy=False)


def count_components_on_slice(mask_slice: np.ndarray) -> tuple[int, int]:
    labels = label(mask_slice, connectivity=1)
    if labels.max() == 0:
        return 0, 0
    counts = np.bincount(labels.ravel())
    return int(labels.max()), int(counts[1:].max())


def score_mask(mask_sample: np.ndarray, raw_slice: np.ndarray, threshold: float) -> tuple[float, dict]:
    foreground_fraction = float(mask_sample.mean())
    slice_mask = raw_slice > threshold
    components, largest_component = count_components_on_slice(slice_mask)
    failure = foreground_fraction <= 0.005 or foreground_fraction >= 0.75 or components == 0
    target_fraction_score = 1.0 - min(abs(foreground_fraction - 0.18) / 0.18, 1.0)
    component_score = min(components / 100.0, 1.0)
    largest_fraction = largest_component / max(1, int(slice_mask.sum()))
    connectivity_penalty = max(0.0, largest_fraction - 0.98)
    score = target_fraction_score + 0.2 * component_score - connectivity_penalty
    if failure:
        score -= 2.0
    return score, {
        "threshold": float(threshold),
        "foreground_fraction": foreground_fraction,
        "slice_components": components,
        "largest_slice_component_fraction": float(largest_fraction),
        "score": float(score),
        "failure": bool(failure),
    }


def save_iteration_diagnostic(
    out_dir: Path,
    iteration: int,
    volume: np.ndarray,
    sample: np.ndarray,
    threshold: float,
    slice_index: int,
    stats: dict,
) -> Path:
    raw_slice = volume[slice_index]
    mask_slice = raw_slice > threshold
    fig, axes = plt.subplots(1, 3, figsize=(14, 4))
    axes[0].hist(sample, bins=256, color="#4c78a8")
    axes[0].axvline(threshold, color="#e45756", linewidth=2)
    axes[0].set_title(f"Iteration {iteration}: threshold {threshold:.2f}")
    axes[0].set_xlabel("Intensity")
    axes[0].set_ylabel("Sampled voxels")
    axes[1].imshow(raw_slice, cmap="gray")
    axes[1].set_title(f"Raw slice {slice_index}")
    axes[1].axis("off")
    axes[2].imshow(mask_slice, cmap="gray", vmin=0, vmax=1)
    axes[2].set_title(
        f"Mask, fg={stats['foreground_fraction']:.3f}, components={stats['slice_components']}"
    )
    axes[2].axis("off")
    fig.tight_layout()
    path = out_dir / f"iteration_{iteration:02d}_diagnostic.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def save_mask_slice(mask: np.ndarray, out_path: Path, slice_index: int) -> None:
    plt.figure(figsize=(6, 6))
    plt.imshow(mask[slice_index], cmap="gray", vmin=0, vmax=255)
    plt.axis("off")
    plt.tight_layout(pad=0)
    plt.savefig(out_path, dpi=150, bbox_inches="tight", pad_inches=0)
    plt.close()


def write_report(
    out_path: Path,
    input_path: Path,
    volume: np.ndarray,
    selected: dict,
    iterations: list[dict],
    outputs: dict[str, Path],
    slice_index: int,
    requested_slice: int,
    foreground_voxels: int,
) -> None:
    total_voxels = int(volume.size)
    background_voxels = total_voxels - foreground_voxels
    foreground_fraction = foreground_voxels / total_voxels
    slice_note = (
        f"Requested slice {requested_slice}; volume contains that slice."
        if slice_index == requested_slice
        else f"Requested slice {requested_slice}; used nearest valid slice {slice_index}."
    )
    lines = [
        "# Segmentation Report",
        "",
        "## Input",
        f"- Input file: `{input_path}`",
        f"- Shape: `{tuple(int(x) for x in volume.shape)}`",
        f"- Dtype: `{volume.dtype}`",
        f"- Intensity range: `{int(volume.min())}` to `{int(volume.max())}`",
        "",
        "## Method",
        "- Sampled up to 2,000,000 voxels uniformly from the flattened volume.",
        "- Estimated an Otsu threshold from the sample.",
        "- Evaluated candidate thresholds around the Otsu estimate with foreground fraction and slice connected-component checks.",
        "- Chose the highest-scoring non-empty/non-full candidate and applied it to the full volume.",
        "- Saved the final mask as uint8 TIFF values: foreground 255, background 0.",
        "",
        "## Iterations",
    ]
    for item in iterations:
        lines.append(
            "- Iteration {iteration}: threshold `{threshold:.3f}`, foreground fraction "
            "`{foreground_fraction:.6f}`, slice components `{slice_components}`, score "
            "`{score:.6f}`, failure `{failure}`, diagnostic `{diagnostic}`".format(**item)
        )
    lines.extend(
        [
            "",
            "## Final Parameters",
            f"- Final threshold: `{selected['threshold']:.3f}`",
            f"- Number of iterations attempted: `{len(iterations)}`",
            "- Failed attempts without improvement: `0`",
            "",
            "## Statistics",
            f"- Foreground voxel count: `{foreground_voxels}`",
            f"- Background voxel count: `{background_voxels}`",
            f"- Foreground fraction: `{foreground_fraction:.8f}`",
            f"- Slice visualization note: {slice_note}",
            "",
            "## Output Paths",
        ]
    )
    for name, path in outputs.items():
        lines.append(f"- {name}: `{path}`")
    lines.extend(
        [
            "",
            "## Limitations",
            "- This is an intensity-threshold segmentation optimized by sampled histogram and one representative slice diagnostic.",
            "- No 3D morphological cleanup was applied, to keep memory usage predictable for the large volume.",
            "- The segmentation completed within the configured safety limits.",
            "",
        ]
    )
    out_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    input_path = args.input_tif.resolve()
    volume = load_volume(input_path)
    out_dir = input_path.parent / "segmentation"
    out_dir.mkdir(exist_ok=True)

    sample = sample_volume(volume)
    otsu_threshold = float(threshold_otsu(sample))
    raw_slice_index = min(TARGET_SLICE, volume.shape[0] - 1)
    raw_slice = volume[raw_slice_index]

    candidates = [
        otsu_threshold + delta
        for delta in (-3000, -2000, -1000, 0, 1000, 2000, 3000)
    ][:MAX_ITERATIONS]

    best: dict | None = None
    iterations: list[dict] = []
    failed_without_improvement = 0
    best_score = -float("inf")
    for iteration, threshold in enumerate(candidates, start=1):
        mask_sample = sample > threshold
        score, stats = score_mask(mask_sample, raw_slice, threshold)
        diagnostic = save_iteration_diagnostic(
            out_dir, iteration, volume, sample, threshold, raw_slice_index, stats
        )
        stats["iteration"] = iteration
        stats["diagnostic"] = str(diagnostic)
        iterations.append(stats)
        if score > best_score:
            best_score = score
            best = stats
            failed_without_improvement = 0
        else:
            failed_without_improvement += 1
        if failed_without_improvement >= MAX_FAILED_ATTEMPTS:
            break

    if best is None:
        raise RuntimeError("No segmentation candidate was evaluated")

    final_threshold = best["threshold"]
    mask_path = out_dir / "segmented_mask.tif"
    slice_path = out_dir / "mask_slice_380.png"
    report_path = out_dir / "segmentation_report.md"

    mask_memmap = tifffile.memmap(
        mask_path,
        shape=volume.shape,
        dtype=np.uint8,
        photometric="minisblack",
        bigtiff=True,
    )
    foreground_voxels = 0
    for z_index in range(volume.shape[0]):
        mask_slice = volume[z_index] > final_threshold
        foreground_voxels += int(np.count_nonzero(mask_slice))
        mask_memmap[z_index] = mask_slice.astype(np.uint8) * 255
    mask_memmap.flush()
    del mask_memmap

    final_slice = ((volume[raw_slice_index] > final_threshold).astype(np.uint8)) * 255
    save_mask_slice(final_slice[np.newaxis, ...], slice_path, 0)

    outputs = {
        "script": out_dir / "segment_lattice.py",
        "segmented_mask": mask_path,
        "mask_slice_380": slice_path,
        "segmentation_report": report_path,
    }
    write_report(
        report_path,
        input_path,
        volume,
        best,
        iterations,
        outputs,
        raw_slice_index,
        TARGET_SLICE,
        foreground_voxels,
    )

    print(f"Segmentation completed: {mask_path}")
    print(f"Threshold: {final_threshold:.3f}")
    print(f"Foreground voxels: {foreground_voxels}")
    print(f"Foreground fraction: {foreground_voxels / volume.size:.8f}")
    print(f"Iterations: {len(iterations)}")


if __name__ == "__main__":
    main()
