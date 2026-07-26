---
name: skeletonization
description: Skeletonize a 3D segmentation mask for the LLNL CT workflow.
---

# Skeletonization Subagent

Create a centerline skeleton from `data/missing_struts/analysis/segmented_mask.tif`,
validate that it is 3D, shape-compatible, and nonblank, then write the skeleton
TIFF and summary metrics under `data/missing_struts/analysis/`.

Run `python .codex/agents/skeletonization/run.py`.
