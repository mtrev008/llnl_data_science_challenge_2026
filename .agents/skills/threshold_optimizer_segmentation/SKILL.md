---
name: threshold-optimizer-segmentation
description: Creates brightness-corrected 3-D CT lattice segmentations by running the bundled threshold_optimizer.py script with per-slice threshold adjustment.
---

# Threshold Optimizer Segmentation Protocol

Use this skill when a single global threshold is not reliable because CT slice brightness drifts, or when the user asks for optimized threshold segmentation.

## Bundled Script

- `scripts/threshold_optimizer.py` loads `.npy`, `.tif`, or `.tiff` volumes, computes a smoothed slice-median brightness profile, preserves a reference threshold on a reference slice, and writes a binary segmentation.

## Inputs

- Original CT volume path.
- Output segmentation path, usually inside a `segmentation/` folder beside the source volume.
- Optional `--reference-slice`, `--reference-threshold`, `--smoothing-sigma`, and `--opening-iterations`.

## Workflow

1. Run `scripts/threshold_optimizer.py` on the original CT volume and output mask path.
2. Use defaults only when the user does not provide optimizer settings:
   - `--reference-slice 380`
   - `--reference-threshold 40049.0`
   - `--smoothing-sigma 8.0`
   - `--opening-iterations 0`
3. Review the printed threshold range and foreground fraction summary for obvious failures such as blank or nearly full masks.
4. Report the output segmentation path, threshold range, median foreground fraction, and mask encoding.

## Constraints

- Create a new segmentation from the original CT volume; do not copy or reuse an existing segmentation.
- Use `--opening-iterations 1` when validation shows small artifacts are hurting topology without materially reducing foreground overlap.
- This skill only performs optimized segmentation. Use the skeletonization expert afterward if a skeleton is needed.
