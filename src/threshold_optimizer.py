#!/usr/bin/env python3
"""Segment a CT lattice while correcting slice-dependent brightness drift.

A single global threshold fails for this scan because the background becomes
much brighter near both ends of axis 0. This script measures the median
background level of every slice, smooths that profile, and shifts the threshold
by the same amount. The supplied reference threshold is preserved exactly on a
known-good reference slice.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np
from scipy.ndimage import gaussian_filter1d
import tifffile


def load_volume(path: Path) -> np.ndarray:
    if path.suffix.lower() == ".npy":
        volume = np.load(path, mmap_mode="r", allow_pickle=False)
    elif path.suffix.lower() in {".tif", ".tiff"}:
        volume = tifffile.memmap(path)
    else:
        raise ValueError("input must be a .npy, .tif, or .tiff volume")
    if volume.ndim != 3 or not np.issubdtype(volume.dtype, np.number):
        raise ValueError(f"expected a numeric 3-D volume, got {volume.shape}")
    return volume


def brightness_corrected_thresholds(
    volume: np.ndarray,
    reference_slice: int,
    reference_threshold: float,
    smoothing_sigma: float = 8.0,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return thresholds, raw medians, and the smoothed median profile."""
    if not 0 <= reference_slice < volume.shape[0]:
        raise ValueError(f"reference slice {reference_slice} is outside the volume")
    if smoothing_sigma < 0:
        raise ValueError("smoothing sigma must be non-negative")

    medians = np.asarray(
        [np.median(np.asarray(volume[z])) for z in range(volume.shape[0])],
        dtype=np.float64,
    )
    profile = (
        gaussian_filter1d(medians, smoothing_sigma, mode="nearest")
        if smoothing_sigma > 0
        else medians
    )
    thresholds = profile + (float(reference_threshold) - profile[reference_slice])
    return thresholds, medians, profile


def create_output(output: Path, shape: tuple[int, ...]) -> np.ndarray:
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.suffix.lower() == ".npy":
        return np.lib.format.open_memmap(output, mode="w+", dtype=np.uint8, shape=shape)
    if output.suffix.lower() in {".tif", ".tiff"}:
        return tifffile.memmap(
            output,
            shape=shape,
            dtype=np.uint8,
            bigtiff=True,
            photometric="minisblack",
        )
    raise ValueError("output must end in .npy, .tif, or .tiff")


def segment_brightness_corrected(
    input_path: Path,
    output_path: Path,
    *,
    reference_slice: int = 380,
    reference_threshold: float = 40049.0,
    smoothing_sigma: float = 8.0,
) -> dict[str, object]:
    """Create a binary mask using a brightness-corrected threshold profile."""
    input_path = input_path.expanduser().resolve()
    output_path = output_path.expanduser().resolve()
    if input_path == output_path:
        raise ValueError("output path must not overwrite the input volume")
    volume = load_volume(input_path)
    thresholds, medians, profile = brightness_corrected_thresholds(
        volume, reference_slice, reference_threshold, smoothing_sigma
    )
    output = create_output(output_path, volume.shape)
    tiff_output = output_path.suffix.lower() in {".tif", ".tiff"}
    foreground_per_slice: list[int] = []
    for z, threshold in enumerate(thresholds):
        mask = np.asarray(volume[z]) >= threshold
        # TIFF viewers conventionally expect an 8-bit binary image to use the
        # full display range. NPY masks retain the computational 0/1 encoding.
        output[z] = mask.astype(np.uint8) * (255 if tiff_output else 1)
        foreground_per_slice.append(int(mask.sum()))
    output.flush()
    del output

    profile_path = output_path.parent / "threshold_profile.csv"
    with profile_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(
            [
                "slice_z",
                "median_intensity",
                "smoothed_median",
                "threshold",
                "foreground_voxels",
            ]
        )
        for z, values in enumerate(
            zip(medians, profile, thresholds, foreground_per_slice)
        ):
            median, smoothed, threshold, foreground = values
            writer.writerow(
                [z, float(median), float(smoothed), float(threshold), foreground]
            )

    plane_size = int(np.prod(volume.shape[1:]))
    fractions = np.asarray(foreground_per_slice, dtype=float) / plane_size
    return {
        "input": str(input_path.resolve()),
        "output": str(output_path.resolve()),
        "threshold_profile": str(profile_path.resolve()),
        "shape_zyx": list(volume.shape),
        "input_dtype": str(volume.dtype),
        "method": "smoothed_slice_median_brightness_correction",
        "mask_encoding": "0/255" if tiff_output else "0/1",
        "reference_slice": reference_slice,
        "reference_threshold": reference_threshold,
        "smoothing_sigma_slices": smoothing_sigma,
        "threshold_min": float(thresholds.min()),
        "threshold_max": float(thresholds.max()),
        "foreground_fraction_min": float(fractions.min()),
        "foreground_fraction_median": float(np.median(fractions)),
        "foreground_fraction_max": float(fractions.max()),
        "foreground_voxels": int(sum(foreground_per_slice)),
        "background_voxels": int(volume.size - sum(foreground_per_slice)),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Input 3-D CT volume")
    parser.add_argument("output", type=Path, help="Output binary mask")
    parser.add_argument("--reference-slice", type=int, default=380)
    parser.add_argument("--reference-threshold", type=float, default=40049.0)
    parser.add_argument("--smoothing-sigma", type=float, default=8.0)
    args = parser.parse_args()

    result = segment_brightness_corrected(
        args.input,
        args.output,
        reference_slice=args.reference_slice,
        reference_threshold=args.reference_threshold,
        smoothing_sigma=args.smoothing_sigma,
    )
    print(
        f"Saved corrected mask: {args.output.resolve()}\n"
        f"Threshold range: {result['threshold_min']:.1f}-{result['threshold_max']:.1f}; "
        f"median foreground per slice: {result['foreground_fraction_median']:.2%}; "
        f"maximum: {result['foreground_fraction_max']:.2%}"
    )


if __name__ == "__main__":
    main()
