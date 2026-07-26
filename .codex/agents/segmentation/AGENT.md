---
name: segmentation
description: Segment the LLNL missing-struts CT volume with traceable optimization outputs.
---

# Segmentation Subagent

Create a binary `.tif` segmentation from the raw CT volume using the
threshold-optimizer skill script. Save the executable script copy, segmentation
mask, foreground/background statistics, slice-380 visualization, and Markdown
report under `data/missing_struts/analysis/`.

Validation criteria from the README: structural integrity, false
positives/negatives, topology, and noise/artifacts. Terminate after one
validated default pass in normal operation; never exceed 10 iterations or 3
failed attempts in iterative tuning.
