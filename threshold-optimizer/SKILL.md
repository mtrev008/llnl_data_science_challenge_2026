---
name: threshold-optimizer
description: Run repeatable threshold sweeps for volumetric CT or NDE datasets by calling the segment_ct_dataset MCP tool once per threshold, saving each segmentation to a distinct file, validating the outputs, and comparing foreground statistics. Use when Codex needs to test, compare, tune, or optimize segmentation thresholds for .npy volumes.
---

# Threshold Optimizer

Create comparable segmentation masks without overwriting the source volume or another threshold result.

## Workflow

1. Resolve the input volume to an absolute path and confirm that it exists.
2. Use thresholds supplied by the user. If none are supplied, use `0.3`, `0.5`, and `0.7`.
3. Inspect the callable schema for `segment_ct_dataset` and map its input-volume, threshold, and output-path arguments accordingly. Do not guess unsupported parameters.
4. Create one deterministic output path per threshold in the requested output directory or, by default, beside the input file.
5. Call `segment_ct_dataset` separately for every threshold. Do not combine thresholds into one call unless the tool schema explicitly supports a sweep while still producing separate files.
6. Validate every successful output and compile a comparison table.

## Output naming

Preserve the input stem and encode the threshold in each mask filename:

```text
<input-stem>_mask_threshold_<threshold-token>.npy
```

Convert the decimal point to `p` and a leading minus sign to `m`. Examples:

```text
volume.npy + 0.3  -> volume_mask_threshold_0p3.npy
volume.npy + 0.5  -> volume_mask_threshold_0p5.npy
volume.npy + 0.7  -> volume_mask_threshold_0p7.npy
```

Never reuse a path for two thresholds. Before overwriting an existing result, verify that the user requested replacement; otherwise choose a non-conflicting filename.

## MCP calls

Call the tool once per threshold using the same source volume and the threshold-specific destination. Conceptually:

```text
segment_ct_dataset(input=<volume>, threshold=0.3, output=<..._0p3.npy>)
segment_ct_dataset(input=<volume>, threshold=0.5, output=<..._0p5.npy>)
segment_ct_dataset(input=<volume>, threshold=0.7, output=<..._0p7.npy>)
```

Treat these names as conceptual only; use the actual argument names exposed by the MCP schema. If the tool returns mask data instead of writing the requested file, save each returned mask to its assigned path without changing its values.

If `segment_ct_dataset` is unavailable, stop and state that the required MCP dependency is missing. Do not silently replace the required tool with a different segmentation implementation.

## Validation and comparison

For each output:

- Confirm that the file exists and can be loaded as a NumPy array.
- Confirm that its shape matches the source volume.
- Confirm that it is binary or Boolean. Report unexpected values rather than coercing them silently.
- Count foreground voxels and compute foreground fraction.
- Record any tool error independently so one failed threshold does not erase successful results.

Return a table ordered by ascending threshold:

| Threshold | Output file | Shape | Foreground voxels | Foreground fraction | Status |
| ---: | --- | --- | ---: | ---: | --- |

Check monotonicity when the tool uses a conventional greater-than threshold: foreground count should not increase as the threshold rises. Flag violations as a possible tool, data, or threshold-semantics issue rather than modifying the masks.

## Selecting a threshold

Do not claim that one threshold is optimal from foreground fraction alone. Choose a winner only when the user supplies an objective criterion or reference, such as a ground-truth mask, expected volume fraction, Dice score, connectivity requirement, or visual acceptance. Otherwise present the sweep as a comparison and ask which criterion should determine the preferred threshold.

## Final response

List every saved mask with its threshold, summarize validation failures, show the comparison table, and state the selection criterion used. If no objective criterion was provided, explicitly say that no threshold was selected as optimal.
