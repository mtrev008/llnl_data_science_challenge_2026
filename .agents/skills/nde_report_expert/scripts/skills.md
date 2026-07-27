---
name: prepare-lattice-volume
description: Optimize a threshold, segment a selected original TIFF, and skeletonize the new segmentation.
---

# Volume Preparation

Given an original TIFF, create all outputs in a `segmentation` folder beside it.

## Files and tools

- `src/threshold_optimizer.py` is the threshold-selection code. It examines the CT
  volume’s intensity and brightness behavior to determine the threshold used
  for separating lattice material from background.
- `segment_ct_dataset` in `src/mcp_server.py` is the segmentation tool. It reads
  the original TIFF, applies the selected threshold to its voxels, and writes a
  new binary segmentation where background is `0` and material is `255`.
- `skeletonize` in `src/mcp_server.py` is the skeletonization tool. It calls
  `src/skeletonization.py` to reduce the segmented material to centerlines while
  preserving the lattice connectivity.

## Workflow

1. Run `src/threshold_optimizer.py` first. It applies its optimized per-slice
   threshold profile and writes a new `uint8` `0/255` segmentation TIFF; do not
   reuse or copy an existing segmentation.
2. Call `skeletonize` from `src/mcp_server.py` on the new segmentation and save
   the resulting skeleton.

Report the reference threshold, optimized threshold range, segmentation path,
and skeleton path.
