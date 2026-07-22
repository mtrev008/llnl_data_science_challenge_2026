---
name: threshold-optimizer
description: Compare CT segmentation results by calling the segment_ct_dataset MCP tool with multiple threshold values and saving every mask separately. Use when testing, comparing, or optimizing segmentation thresholds for a volumetric .npy dataset.
---

# Threshold Optimizer

Use the `segment_ct_dataset()` MCP tool to segment one CT dataset at multiple thresholds.

## Procedure

1. Obtain the input `.npy` filepath from the user and confirm that it exists.
2. Use the user's threshold values. If none are provided, use `0.0001`, `0.001`, `0.0015`, `0.002`, `0.003`, `0.005`, `0,006`, and `0.007`.
3. For each threshold, create a unique output filename in this format:

   ```text
   <input_stem>_threshold_<threshold>.npy
   ```

   Replace the decimal point with `p`. For example, threshold `0.003` must produce `unitcell_threshold_0p3.npy`.
4. Call `segment_ct_dataset()` once for every threshold, passing the same input file and a different output file each time.
5. Confirm that each expected output file exists after its MCP call.
6. Report the threshold, output filepath, and success or failure status for every result so the files can be compared.

## Default MCP calls

Given an input file named `/data/unitcell.npy`, make these separate calls:

```text
segment_ct_dataset(
    input_filepath="/data/unitcell.npy",
    output_filepath="/data/unitcell_threshold_0p7.npy",
    threshold=0.0001
)
segment_ct_dataset(
    input_filepath="/data/unitcell.npy",
    output_filepath="/data/unitcell_threshold_0p7.npy",
    threshold=0.001
)
segment_ct_dataset(
    input_filepath="/data/unitcell.npy",
    output_filepath="/data/unitcell_threshold_0p7.npy",
    threshold=0.0015
)
segment_ct_dataset(
    input_filepath="/data/unitcell.npy",
    output_filepath="/data/unitcell_threshold_0p7.npy",
    threshold=0.002
)
segment_ct_dataset(
    input_filepath="/data/unitcell.npy",
    output_filepath="/data/unitcell_threshold_0p3.npy",
    threshold=0.003
)

segment_ct_dataset(
    input_filepath="/data/unitcell.npy",
    output_filepath="/data/unitcell_threshold_0p5.npy",
    threshold=0.005
)
segment_ct_dataset(
    input_filepath="/data/unitcell.npy",
    output_filepath="/data/unitcell_threshold_0p7.npy",
    threshold=0.006
)

segment_ct_dataset(
    input_filepath="/data/unitcell.npy",
    output_filepath="/data/unitcell_threshold_0p7.npy",
    threshold=0.007
)
```

## Rules

- Call the MCP tool separately for every threshold; do not implement segmentation locally.
- Never use the same output filepath for two thresholds.
- Never overwrite the input dataset.
- Ask before overwriting an existing output file.
- Continue with the remaining thresholds if one call fails, then clearly report the failure.
- Do not claim that a segmentation succeeded unless its output file exists.
