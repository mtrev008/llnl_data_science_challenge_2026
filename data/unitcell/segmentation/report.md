# Unitcell Segmentation Report

## Summary

- Date: 2026-07-21
- Input volume: `C:\Users\andre\llnl_data_science_challenge_2026\data\unitcell\unitcell.npy`
- Reference mask for scoring: `C:\Users\andre\llnl_data_science_challenge_2026\data\unitcell\unitcell_mask.npy`
- Qualitative render inspected: `C:\Users\andre\llnl_data_science_challenge_2026\data\unitcell\ground_truth_segmentation_image.png`
- Input shape: `(256, 256, 256)`
- Input dtype: `float32`
- Input range: `-0.003128750` to `0.015257692`
- Selected raw threshold: `0.010000`
- Selected min-max normalized threshold: `0.714045`
- Selection criterion: maximize Dice score against `unitcell_mask.npy`, with smaller foreground-count error and fewer connected components as tie-breakers
- Final method: global thresholding with `mask = volume >= threshold`

## Input Inspection

- Percentile p0.001: `-0.001519176`
- Percentile p0.01: `-0.001079610`
- Percentile p0.05: `-0.000573885`
- Percentile p0.50: `0.000000000`
- Percentile p0.95: `0.002116629`
- Percentile p0.99: `0.012658402`
- The reference render image has shape `(1838, 1765, 4)`, so it does not correspond to a single 256x256 voxel slice. It was used only as a qualitative 3D appearance check.

## Iterations

- Closed-loop sweep thresholds: `0.005`, `0.009`, `0.010`
- Iteration history CSV: `C:\Users\andre\llnl_data_science_challenge_2026\data\unitcell\segmentation\iteration_history.csv`
- Threshold `0.005` over-segmented relative to the reference mask.
- Threshold `0.009` improved overlap while remaining slightly too inclusive.
- Threshold `0.010` matched the reference mask exactly and was selected immediately.

## Final Mask Statistics

- Mask output shape: `(256, 256, 256)`
- Mask dtype in `.npy`: `bool`
- Mask encoding in `.tif`: `uint8` with values `0` and `255`
- Total voxels: `16777216`
- Foreground voxels: `622182`
- Background voxels: `16155034`
- Foreground percentage: `3.708494%`
- Background percentage: `96.291506%`
- Connected components (26-connectivity): `1`
- Largest component fraction: `1.00000000`
- Foreground voxels touching the volume boundary: `0`
- Dice to reference mask: `1.00000000`

## Slice Outputs

- Central slice visualization: `C:\Users\andre\llnl_data_science_challenge_2026\data\unitcell\segmentation\mask_slice_128.png`
- Informative lattice slice visualization: `C:\Users\andre\llnl_data_science_challenge_2026\data\unitcell\segmentation\mask_slice_210.png`
- Slice 380 diagnostic: `C:\Users\andre\llnl_data_science_challenge_2026\data\unitcell\segmentation\mask_slice_380.png`
- The volume has only `256` slices along axis 0, so zero-based slice `380` does not exist. A diagnostic placeholder image was saved instead, and slice `128` was saved as the central slice.

## Outputs

- Script: `C:\Users\andre\llnl_data_science_challenge_2026\data\unitcell\segmentation\segment_lattice.py`
- Final mask `.npy`: `C:\Users\andre\llnl_data_science_challenge_2026\data\unitcell\segmentation\segmented_mask.npy`
- Final mask `.tif`: `C:\Users\andre\llnl_data_science_challenge_2026\data\unitcell\segmentation\segmented_mask.tif`
- Iteration history: `C:\Users\andre\llnl_data_science_challenge_2026\data\unitcell\segmentation\iteration_history.csv`
- Report: `C:\Users\andre\llnl_data_science_challenge_2026\data\unitcell\segmentation\report.md`

## Library Versions

- numpy: `2.4.6`
- scipy: `1.17.1`
- scikit-image: `0.26.0`
- tifffile: `2026.3.3`
- matplotlib: `3.11.1`
