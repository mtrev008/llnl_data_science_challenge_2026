---
name: visualization-expert
description: Create deterministic scientific visualizations and traceable mesh exports for X-ray CT volumes, validation reports, lattice graphs, segmentation masks, anomaly results, and iteration comparisons. Use when Codex needs histograms, statistical plots, CT slices, segmentation overlays, error maps, lattice views, CT-segmentation-derived as-built STL surfaces, digital-twin visuals, required mesh previews, mesh metrics, visualization manifests, or reports from .tif, .tiff, .npy, .csv, .json, .stl, or image inputs.
---

# Visualization Expert

Create traceable scientific figures and mesh artifacts without modifying source
data. Use the bundled scripts instead of rewriting plotting or mesh logic.

## Environment

Use only `C:\Users\andre\miniconda3\envs\dssi_env\python.exe`. Before the first
visualization command, run one preflight importing only packages needed by the
selected operation. Do not switch interpreters or install packages without
explicit approval. Return `BLOCKED_ENVIRONMENT` with the exact error on failure.

## Workflow

1. Resolve every input and output path.
2. Read upstream validation status and warnings when available.
3. Read [references/visualization-selection.md](references/visualization-selection.md).
4. Read [references/plotting-standards.md](references/plotting-standards.md).
5. For CT-derived surface export, read
   [references/surface-mesh-standards.md](references/surface-mesh-standards.md).
6. Run [scripts/generate_visualization.py](scripts/generate_visualization.py) or
   [scripts/export_ct_surface.py](scripts/export_ct_surface.py) as routed below.
7. Verify each output exists, is nonempty, and has the expected format.
8. Follow [references/output-schema.md](references/output-schema.md).
9. Report paths, observations, warnings, and limitations.

Use the visualization tools registered by `src/mcp_server.py` when they are
available. Use `scripts/generate_visualization.py` as the deterministic CLI
fallback for figures. Use `scripts/export_ct_surface.py` as the deterministic
CLI fallback for CT-derived surfaces. All interfaces use the same traceability
contract.

## Validation handoff

- `PASS`: allow normal visualization.
- `PASS_WITH_WARNINGS`: proceed and preserve applicable warnings.
- `FAIL`: create diagnostic views only.
- No report: verify readability and disclose that the data were not validated.

## Script interface

```powershell
& "C:\Users\andre\miniconda3\envs\dssi_env\python.exe" `
  ".agents\skills\visualization-expert\scripts\generate_visualization.py" `
  <subcommand> <arguments>
```

Use `histogram`, `bar`, `slice`, `orthogonal`, `slice-trend`, `overlay`,
`compare-mask`, or `graph`. Pass `--manifest <path>` to append a result. Pass
`--overwrite` only with explicit replacement permission. Parse the single JSON
object emitted to stdout.

For a CT-segmentation-derived as-built surface, prefer the registered MCP tool
`export_ct_as_built_surface`. Use this CLI fallback:

```powershell
& "C:\Users\andre\miniconda3\envs\dssi_env\python.exe" `
  ".agents\skills\visualization-expert\scripts\export_ct_surface.py" `
  --mask "<segmented-mask.tif>" `
  --output "<surface.stl>" `
  --preview "<surface-preview.png>" `
  --voxel-size-x <x> `
  --voxel-size-y <y> `
  --voxel-size-z <z> `
  --units "<unit>"
```

Require `--preview`. Add `--metrics <path>` when mesh metrics must be stored as
a separate JSON artifact. Do not pass `--overwrite` without explicit
replacement permission. Parse the single JSON object emitted to stdout.

## Surface product selection

Distinguish these products before running a tool:

- **CT-derived as-built surface**: extract geometry from a selected 3D
  segmentation mask with `export_ct_as_built_surface` or
  `export_ct_surface.py`.
- **Registered-graph mesh**: construct idealized member and junction geometry
  only when the caller requests it and radius semantics are documented.
- **Existing STL visualization**: inspect or render a supplied STL without
  regenerating geometry.

Never substitute one product for another. Describe a segmentation-derived mesh
as a **CT-segmentation-derived as-built surface visual**, not validated CAD or a
mechanically validated digital twin.

## CT-derived surface workflow

1. Resolve the mask, STL, preview, optional metrics, manifest, and validation
   paths.
2. Confirm that the geometry source is the selected 3D segmentation mask.
3. Require finite positive XYZ voxel spacing and a unit label.
4. Preserve the input array order as `ZYX` and output mesh order as `XYZ`.
5. Keep component filtering, smoothing, hole filling, and decimation disabled
   unless explicitly requested.
6. Run `export_ct_as_built_surface` when available; otherwise run
   `scripts/export_ct_surface.py`.
7. Require the exporter to reload the STL and validate finite geometry, face
   indices, and scaled bounds.
8. Require a nonempty static preview rendered from the reloaded STL.
9. Preserve cleanup, filtering, decimation, calibration, and sampling
   provenance.
10. Return the STL, preview, optional metrics, and manifest paths with all
    warnings.

Treat non-watertightness as a reported property for a defect-bearing as-built
surface, not an automatic failure. Treat unreadable output, invalid geometry,
or incompatible reloaded bounds as errors.

## Existing anomaly outputs

- Use existing anomaly CSV files directly when they provide relevant context.
- Do not rewrite, merge, or consolidate anomaly CSV files unless explicitly
  requested.
- Do not interpret topology-analysis or measurement IDs as registered-graph
  strut IDs without a validated mapping.
- Do not remove mesh or graph geometry based on unresolved anomaly-to-edge
  mappings.
- Record anomaly paths as provenance, not as generated mesh outputs.

## Large TIFF operations

- Use `histogram` directly on TIFF input to accumulate integer counts one page
  at a time.
- Use `slice-trend --axis 0` to calculate page-wise TIFF trends without loading
  the full volume.
- Prefer traceable per-slice statistics from any upstream agent when they
  already contain the complete requested statistic.
- Refuse eager loading above the script's configured memory limit when a TIFF
  cannot be memory-mapped.
- Preserve whether scientific values, histogram-bin selection, or display
  windows were sampled.
- Distinguish display-only downsampling from scientific-data sampling.

## Scientific constraints

- Never modify scientific inputs.
- Describe uncalibrated CT values as intensity, not physical density.
- Never invent units, spacing, origins, calibration, or transforms.
- Never claim registration from coordinate bounds alone.
- Keep slices, crops, windows, axes, and colors fixed in direct comparisons.
- Do not choose the scientifically best result from appearance alone.
- Treat identifier-like fields as identifiers, not measurements.
- Add scale bars only when calibration is supplied.
- Record deterministic sampling.
- Never use a downsampled display image to calculate scientific statistics.
- Never infer mesh spacing, physical origin, or coordinate transform.
- Never use downsampled display data as a surface-extraction source.
- Never fill openings that may represent missing or broken material by default.
- Never claim that an STL contains unit metadata; record units in sidecars and
  reports.

## Outputs

Default beneath a `visualizations` directory adjacent to the primary dataset:

```text
visualizations/
  visualization_manifest.json
  visualization_report.md
  histograms/
  statistical_plots/
  ct_slices/
  segmentation_overlays/
  graph_views/
  surface_meshes/
  iteration_comparisons/
  thumbnails/
```

Refuse overwrite by default. Finish when every requested artifact is verified or
has a structured error. Stop iterative requests at the caller's limit, 10
iterations, or 3 consecutive failures, whichever occurs first.
