# Segmentation Report

## Input
- Input file: `/Users/riamariamathew/Projects/llnl_data_science_challenge_2026/data/9x9x9_octet_lattice/9x9x9_octet_lattice.tif`
- Shape: `(761, 815, 837)`
- Dtype: `uint16`
- Intensity range: `0` to `65535`

## Method
- Sampled up to 2,000,000 voxels uniformly from the flattened volume.
- Estimated an Otsu threshold from the sample.
- Evaluated candidate thresholds around the Otsu estimate with foreground fraction and slice connected-component checks.
- Chose the highest-scoring non-empty/non-full candidate and applied it to the full volume.
- Saved the final mask as uint8 TIFF values: foreground 255, background 0.

## Iterations
- Iteration 1: threshold `37042.879`, foreground fraction `0.147938`, slice components `286`, score `1.021875`, failure `False`, diagnostic `/Users/riamariamathew/Projects/llnl_data_science_challenge_2026/data/9x9x9_octet_lattice/segmentation/iteration_01_diagnostic.png`
- Iteration 2: threshold `38042.879`, foreground fraction `0.133948`, slice components `283`, score `0.944155`, failure `False`, diagnostic `/Users/riamariamathew/Projects/llnl_data_science_challenge_2026/data/9x9x9_octet_lattice/segmentation/iteration_02_diagnostic.png`
- Iteration 3: threshold `39042.879`, foreground fraction `0.122458`, slice components `284`, score `0.880323`, failure `False`, diagnostic `/Users/riamariamathew/Projects/llnl_data_science_challenge_2026/data/9x9x9_octet_lattice/segmentation/iteration_03_diagnostic.png`
- Iteration 4: threshold `40042.879`, foreground fraction `0.113115`, slice components `283`, score `0.828416`, failure `False`, diagnostic `/Users/riamariamathew/Projects/llnl_data_science_challenge_2026/data/9x9x9_octet_lattice/segmentation/iteration_04_diagnostic.png`

## Final Parameters
- Final threshold: `37042.879`
- Number of iterations attempted: `4`
- Failed attempts without improvement: `0`

## Statistics
- Foreground voxel count: `76819584`
- Background voxel count: `442300371`
- Foreground fraction: `0.14798041`
- Slice visualization note: Requested slice 380; volume contains that slice.

## Output Paths
- script: `/Users/riamariamathew/Projects/llnl_data_science_challenge_2026/data/9x9x9_octet_lattice/segmentation/segment_lattice.py`
- segmented_mask: `/Users/riamariamathew/Projects/llnl_data_science_challenge_2026/data/9x9x9_octet_lattice/segmentation/segmented_mask.tif`
- mask_slice_380: `/Users/riamariamathew/Projects/llnl_data_science_challenge_2026/data/9x9x9_octet_lattice/segmentation/mask_slice_380.png`
- segmentation_report: `/Users/riamariamathew/Projects/llnl_data_science_challenge_2026/data/9x9x9_octet_lattice/segmentation/segmentation_report.md`

## Limitations
- This is an intensity-threshold segmentation optimized by sampled histogram and one representative slice diagnostic.
- No 3D morphological cleanup was applied, to keep memory usage predictable for the large volume.
- The segmentation completed within the configured safety limits.
