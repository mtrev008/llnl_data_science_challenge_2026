---
name: segmentation-expert
description: Segments 3-D CT lattice volumes into binary masks using a supplied global threshold and the segment_ct_dataset MCP tool.
---

# Segmentation Protocol

Use this skill when the user provides a CT `.npy`, `.tif`, or `.tiff` volume and a known threshold, and wants a new binary segmentation mask.

## Inputs

- Original CT volume path.
- Output segmentation path, usually inside a `segmentation/` folder beside the source volume.
- Finite numeric threshold.

## Workflow

1. Confirm the input is a 3-D `.npy`, `.tif`, or `.tiff` volume.
2. Choose an output path ending in `.npy`, `.tif`, or `.tiff`. Prefer `segmentation/<source-stem>_segmentation.<ext>` beside the original volume when the user does not specify a path.
3. Call `segment_ct_dataset` from `src/mcp_server.py` with the input path, output path, and threshold.
4. Report the threshold, output path, output shape, and mask encoding.

## Constraints

- Create a new segmentation from the original CT volume; do not copy or reuse an existing segmentation.
- The MCP tool writes `.npy` masks as `0/1` and TIFF masks as `0/255`.
- Do not skeletonize here. Use the skeletonization expert for skeleton output.
