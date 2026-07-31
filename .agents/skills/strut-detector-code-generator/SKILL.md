---
name: strut-detector-code-generator
description: Build, validate, and conservatively repair deterministic registered-strut measurement code for stackwise CT detector workflows.
---

# Strut Detector Code Generator

Use this skill when implementing or reviewing the deterministic measurement side of the stackwise strut detector.

1. Inspect the existing TIFF loaders, geometry parsing, and artifact contract before editing. Keep clustering, JSON-assisted, and mask-only methods unchanged.
2. Validate matching 3-D TIFF dimensions, Git LFS pointers, odd windows, z-intersection filtering, and preserved source IDs.
3. Measure corridor occupancy, components, endpoint connection, gaps, thickness, deviation, curvature, raw corroboration, and quality flags. Use robust matched normal baselines.
4. Write per-stack logs and records, continue after an individual stack failure, render overlays, and merge overlap evidence by `strut_id`.
5. Verify schema-valid instructions, numeric measurements, overlays, and duplicate merging on representative boundary, interior, and suspected-defect stacks.

Never let model prose directly choose a final defect label. Use only `missing`, `broken`, `thin`, `bent`, `normal`, or conservative `uncertain`.
