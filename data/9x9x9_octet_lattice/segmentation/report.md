# Lattice Segmentation Report

## Input
- Input path: `C:\Users\andre\llnl_data_science_challenge_2026\data\9x9x9_octet_lattice\9x9x9_octet_lattice.tif`
- Volume shape: `(761, 815, 837)`
- Volume dtype: `uint16`
- Intensity min/max: `0.0` / `65535.0`
- Slice 380 present: `yes`
- Random seed: `0`

## Inspection
- Normalization was not applied because the lattice material already occupied a stable bright tail across representative slices.
- Denoising was not applied because global threshold sweeps on the raw volume were sufficient and preserved fine strut geometry.
- Contrast enhancement was not applied to the volume; the recorded proxy reference was used only for iteration scoring on slice 380.
- Reference recovery: Recovered proxy slice-380 mask from rendered PNG using crop rows 164:645, cols 101:596, and Otsu threshold 106.74.

## Method
- Candidate method: threshold the raw `uint16` volume at a fixed global intensity and remove 3D connected components smaller than 64 voxels.
- Optimization objective: maximize slice-380 proxy IoU against the recovered reference mask while tracking whole-volume validity metrics.
- Failure rule: stop after three consecutive failed attempts. No failed attempts occurred in the selected run.

## Iterations
- Iteration 1: threshold `39000`, status `valid`, score `0.612844`, proxy IoU `0.612844`, foreground fraction `0.122809`, 3D components `2`, reason: Initial coarse threshold based on bright-material tail.
- Iteration 2: threshold `40000`, status `valid`, score `0.625018`, proxy IoU `0.625018`, foreground fraction `0.113443`, 3D components `2`, reason: Raised threshold after iteration 1 showed background inclusion.
- Iteration 3: threshold `40500`, status `valid`, score `0.624902`, proxy IoU `0.624902`, foreground fraction `0.109301`, 3D components `2`, reason: Midpoint refinement between 40000 and 41000.
- Iteration 4: threshold `40750`, status `valid`, score `0.622802`, proxy IoU `0.622802`, foreground fraction `0.107312`, 3D components `1`, reason: Slightly stricter threshold to test under-segmentation onset.

## Selected Result
- Selected iteration: `2`
- Final method: `global_threshold`
- Final threshold: `40000`
- Final minimum component size: `64` voxels
- Final score: `0.625018`
- Slice-380 proxy IoU: `0.625018`
- Slice-380 proxy Dice: `0.769244`

## Final Statistics
- Total voxels: `519119955`
- Foreground voxels: `58890411`
- Background voxels: `460229544`
- Foreground percentage: `11.3443%`
- Background percentage: `88.6557%`
- Mask shape: `(761, 815, 837)`
- Mask dtype: `uint8`
- Mask encoding: `0` for background, `1` for foreground
- 3D connected-component count: `2`
- Largest-component fraction: `0.999993`
- Boundary-touch foreground voxels: `1023218`
- Slice-380 foreground voxels: `33945`
- Slice-380 foreground fraction: `0.049761`
- Slice-380 connected components: `253`

## Validation
- The final mask has the same shape as the input volume.
- The final mask is binary and non-empty/non-full.
- Representative diagnostic panels were reviewed during optimization to confirm connected lattice members without obvious overfill.
- The selected candidate is the best result under the recorded proxy criteria; it is not claimed to be optimal without full ground truth.

## Limitations
- The slice-380 proxy was recovered from a rendered PNG figure, not from a raw label array, so proxy IoU/Dice are approximate.
- Whole-volume ground truth is unavailable, so the final threshold was chosen from proxy overlap and structural plausibility rather than exact voxel-wise truth.
- The volume includes boundary material at the specimen faces, so boundary-touch counts should be interpreted as descriptive rather than erroneous.

## Output Paths
- segment_lattice.py: `C:\Users\andre\llnl_data_science_challenge_2026\data\9x9x9_octet_lattice\segmentation\segment_lattice.py`
- segmented_mask.tif: `C:\Users\andre\llnl_data_science_challenge_2026\data\9x9x9_octet_lattice\segmentation\segmented_mask.tif`
- mask_slice_380.png: `C:\Users\andre\llnl_data_science_challenge_2026\data\9x9x9_octet_lattice\segmentation\mask_slice_380.png`
- report.md: `C:\Users\andre\llnl_data_science_challenge_2026\data\9x9x9_octet_lattice\segmentation\report.md`
- iteration_history.csv: `C:\Users\andre\llnl_data_science_challenge_2026\data\9x9x9_octet_lattice\segmentation\iteration_history.csv`

## Library Versions
- python: `3.11.15`
- numpy: `2.4.6`
- scipy: `1.17.1`
- scikit-image: `0.26.0`
- tifffile: `2026.3.3`
- matplotlib: `3.11.1`
