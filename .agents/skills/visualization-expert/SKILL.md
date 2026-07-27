---
name: visualization-expert
description: Create deterministic scientific visualizations for X-ray CT volumes, validation reports, lattice graphs, segmentation masks, anomaly results, and iteration comparisons. Use when Codex needs histograms, bar charts, statistical trends, CT slices, orthogonal views, segmentation overlays, ground-truth error maps, lattice graph views, or a visualization manifest and report from .tif, .tiff, .npy, .csv, .json, .stl, or image inputs.
---

# Visualization Expert

Create traceable scientific figures without modifying source data. Use the bundled
script for supported plots instead of rewriting plotting logic.

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
5. Run [scripts/generate_visualization.py](scripts/generate_visualization.py).
6. Verify each output exists, is nonempty, and has the expected format.
7. Follow [references/output-schema.md](references/output-schema.md).
8. Report paths, observations, warnings, and limitations.

Use the visualization tools registered by `src/mcp_server.py` when they are
available. Use `scripts/generate_visualization.py` as the deterministic CLI
fallback. Both interfaces use the same renderer and output contract.

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
  iteration_comparisons/
  thumbnails/
```

Refuse overwrite by default. Finish when every requested artifact is verified or
has a structured error. Stop iterative requests at the caller's limit, 10
iterations, or 3 consecutive failures, whichever occurs first.
