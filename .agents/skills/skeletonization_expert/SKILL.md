---
name: skeletonization-expert
description: Creates 3-D centerline skeletons from binary CT segmentation masks using the skeletonize MCP tool.
---

# Skeletonization Protocol

Use this skill when the user has a binary segmentation mask and wants a skeletonized lattice centerline volume.

## Inputs

- Binary segmentation mask path (`.npy`, `.tif`, or `.tiff`).
- Output skeleton path (`.npy`, `.tif`, or `.tiff`).

## Workflow

1. Confirm the input is a 3-D segmentation mask and exists on disk.
2. Choose an output path ending in `.npy`, `.tif`, or `.tiff`. Prefer `segmentation/<mask-stem>_skeleton.<ext>` beside the mask when the user does not specify a path.
3. Call `skeletonize` from `src/mcp_server.py`.
4. Report the skeleton path, shape, and number of nonzero skeleton voxels.

## Constraints

- Treat any nonzero mask voxel as foreground.
- TIFF skeletons are saved as `0/255`; `.npy` skeletons are saved as boolean arrays.
- Do not segment raw CT volumes here. Use the segmentation expert or threshold optimizer segmentation expert first.
