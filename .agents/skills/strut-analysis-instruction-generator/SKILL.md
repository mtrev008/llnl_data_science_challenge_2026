---
name: strut-analysis-instruction-generator
description: Generate schema-valid, measurement-oriented multimodal instructions for registered CT lattice z-stacks when reviewing strut corridors, masks, skeletons, and raw CT.
---

# Strut Analysis Instruction Generator

Use this skill for a registered-lattice z-stack panel that needs an Agent 1 instruction JSON. It is an interpretation contract, not a classifier.

1. Confirm raw CT, segmentation, optional skeleton, expected corridors, junctions, IDs, voxel spacing, and material metadata are available.
2. Emit only the required schema: measurable configuration recommendations, per-strut observations, uncertainty conditions, and requested overlays.
3. Require corridor occupancy, components, endpoint connection, persistent gaps, distance-transform thickness, deviation, curvature, raw-CT corroboration, and quality flags.
4. Require normal reference thresholds to be robust median/MAD estimates from same-orientation and similar-length candidates.
5. Require two overlapping observations for a defect unless the stack covers the whole physical strut. Mark poor alignment, clipping, or conflicting raw/mask evidence uncertain.

Do not assign final labels or substitute geometry IDs. Preserve every source `strut_id`, endpoint, and inclusive z-range.
