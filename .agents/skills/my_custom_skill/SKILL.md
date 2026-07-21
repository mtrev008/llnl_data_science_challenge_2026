---
name: threshold-optimizer
description: A skill that calls the segment_ct_dataset() MCP tool multiple times with different threshold values (e.g., 0.003, 0.007, 0.01) and saves the results in separate files for comparison.

---
# Threshold Optimizer Protocol

You are a **Threshold Comparison Optimizer**. When this skill is active, segment the same CT dataset multiple times with different threshold values and save each result as a separate mask for comparison.

## Step 1: Identify Inputs

- Use the user-provided CT dataset path as the input volume. The expected input is a `.npy` file unless the user explicitly provides another format supported by the available segmentation tool.
- Use the user-provided threshold list when one is given.
- If the user does not provide thresholds, use `0.003`, `0.007`, and `0.01`.
- Confirm that the input dataset exists before running segmentation.

## Step 2: Run Threshold Sweep

For each threshold:

1. Call the `segment_ct_dataset()` MCP tool with the same input dataset and the current threshold.
2. Save the output as a separate file whose name includes the threshold value.
3. Use deterministic, comparison-friendly names such as:
   - `<input_stem>_mask_threshold_0.003.npy`
   - `<input_stem>_mask_threshold_0.007.npy`
   - `<input_stem>_mask_threshold_0.01.npy`

If the MCP segmentation tool is unavailable, fall back to a local threshold operation only for `.npy` inputs:

```python
mask = (volume > threshold).astype(np.uint8)
```

When using the fallback, preserve the same output naming convention and clearly state that local thresholding was used instead of the MCP tool.

## Step 3: Compare Outputs

For each generated mask, calculate:

- Output path
- Threshold value
- Mask shape
- Foreground voxel count
- Foreground fraction of the total volume
- Mask dtype

Save these metrics in a comparison file next to the generated masks:

- `<input_stem>_threshold_comparison.csv`

Optionally include a short Markdown summary if the user asks for a human-readable comparison, but do not create an NDE report unless the user explicitly asks for one.

## Technical Constraints

- This skill only optimizes segmentation thresholds; it does not skeletonize data, render 3D visualizations, or compile NDE reports.
- Check that every generated mask has the same shape as the input volume.
- Avoid overwriting unrelated existing files. If an expected output file already exists, either replace it only when it is clearly the matching threshold output or choose a unique suffix.
- If temporary scripts or scratch files are created, remove them before finishing.
