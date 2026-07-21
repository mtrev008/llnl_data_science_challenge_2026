---
name: threshold_optimizer
description: Runs CT segmentation at multiple threshold values and saves separate mask outputs for comparison.
---

# Threshold Optimization Protocol

You are the **CT Threshold Optimization Expert**. When this skill is active, run the segmentation MCP tool repeatedly with different threshold values, save each result separately, and prepare the outputs for side-by-side comparison.

## Step 1: Select Thresholds

- Use the user-provided threshold list if one is supplied.
- Otherwise, use these default threshold values: `0.3`, `0.5`, and `0.7`.
- Keep threshold values in the output filenames so results are unambiguous.

## Step 2: Run Segmentations

For each threshold value:

1. Call the `segement_ct_dataset()` MCP tool with the same input CT dataset and the current threshold value.
2. Save the returned segmentation mask as a separate `.npy` file.
3. Use deterministic filenames with this pattern:

   ```text
   <input_stem>_segmentation_threshold_<threshold>.npy
   ```

   Replace the decimal point with `p` in filenames. For example:

   ```text
   unitcell_segmentation_threshold_0p3.npy
   unitcell_segmentation_threshold_0p5.npy
   unitcell_segmentation_threshold_0p7.npy
   ```

## Step 3: Comparison Outputs

After all segmentations are saved:

- Verify that every output mask has the same shape as the input CT volume.
- Calculate basic comparison metrics for each threshold:
  - foreground voxel count
  - foreground volume fraction
  - mean raw intensity inside the mask
  - mean raw intensity outside the mask
- Save the comparison metrics as a markdown or JSON summary next to the generated masks.

## Technical Constraints

- Do not overwrite existing segmentation files unless the user explicitly requests replacement.
- If an output path already exists, add a unique suffix such as `_run2`.
- Keep all generated masks in the requested output directory, or next to the input CT dataset if no output directory is provided.
- If `segement_ct_dataset()` is unavailable, stop and report that the required MCP tool is missing.
- If temporary helper scripts are created, remove them once processing is finished.
