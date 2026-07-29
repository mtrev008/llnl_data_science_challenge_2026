# Python Scripts: Purpose and Methods

The current project Python implementation consists of five scripts in `src/`.
Together they prepare a raw CT volume, extract its lattice centerlines, analyze
missing topology, expose selected operations through MCP, and create optional
3D NPY visualizations.

## Current TIFF workflow

1. Run `threshold_optimizer.py` on the raw CT TIFF to create a
   brightness-corrected binary mask.
2. Run `skeletonization.py` on that mask to create a complete 3D centerline
   skeleton.
3. Run `missing_strut_junction_analyzer.py` with the mask and skeleton. Supply
   the raw TIFF for intensity evidence and optionally supply an expected-design
   JSON for coordinate-free counts and structural priors.
4. Review the analyzer CSV files, Markdown summary, and annotated PNG sheets.

The `missing_strut_junction_agent` automates this workflow and delegates steps
1–2 to `segmentation_skeletonization_agent`.

## Script reference

### `src/threshold_optimizer.py`

**Purpose:** Segment a numeric 3D NPY or TIFF CT volume while compensating for
slice-dependent brightness drift.

**Method:** For every Z slice, the script measures the median intensity
\(m_z\), smooths the resulting profile to obtain \(p_z\), and shifts a known
reference threshold across the stack:

\[
T_z = p_z + (T_r - p_r)
\]

Voxels at or above \(T_z\) become foreground. TIFF masks use `uint8` values
`0/255`; NPY masks use `0/1`. The command-line defaults are reference slice
380, reference threshold 40049, and Gaussian smoothing sigma 8. These are
calibrated for the Brian Tran/LLNL 9x9x9 scan family and should be explicitly
overridden for differently calibrated scans.

### `src/skeletonization.py`

**Purpose:** Reduce a 3D segmentation mask to topology-preserving centerlines.

**Method:** Every nonzero mask voxel becomes foreground, then scikit-image's
3D-capable `skeletonize` operation thins the complete volume. It does not
skeletonize TIFF pages independently. Outputs may be NPY or TIFF; TIFF
skeletons use `uint8` values `0/255`.

### `src/missing_strut_junction_analyzer.py`

**Purpose:** Detect missing struts, potential strut defects, and missing
junctions from an observed mask and skeleton without using design coordinates.

**Inputs:** A segmented 3D TIFF is required. A matching skeleton TIFF and raw
CT TIFF are strongly recommended. An expected-design JSON is optional.

**Method:**

- Convert the observed skeleton into paths between clustered physical
  junctions and terminal endpoints.
- Learn intact connection directions, structural families, and global and
  local normal strut lengths from the TIFF-derived graph.
- Infer empty junction sites from multiple geometrically consistent
  neighboring predictions, then reject unsupported, imbalanced, duplicate, and
  boundary candidates.
- Project locally expected connections between observed junctions and evaluate
  continuous support from skeleton, segmentation, and normalized raw CT.
- Classify sufficiently absent connections as `missing`, shorter continuous
  gaps as `potential_defect`, and supported connections as present.
- Merge slice observations into physical 3D anomaly tracks before selecting
  representative visualization slices.

The expected JSON contributes coordinate-free design counts and structural
priors only. Its positions and endpoint coordinates are not used to register
or align the TIFF.

The focused workflow writes:

- `missing_struts.csv`
- `potential_defects.csv`
- `missing_junctions.csv`
- `defect_summary.md`
- `png_outputs/missing_anomalies_*.png`

The reported total missing-strut count combines directly detected missing
connections with 12 junction-implied missing struts for each accepted missing
junction. The summary shows the formula explicitly. Visualization colors are
yellow for missing struts, red for potential defects, and magenta for missing
junctions.

### `src/mcp_server.py`

**Purpose:** Expose segmentation, slice visualization, and skeletonization as
FastMCP tools.

**Method:**

- `segment_ct_dataset` applies one user-supplied global threshold. Use it only
  when a single threshold is appropriate for the complete volume.
- `visualize_slice` extracts a plane on axis 0, 1, or 2 and min-max scales it
  for grayscale display.
- `skeletonize` delegates to the same `skeletonize_mask` implementation in
  `src/skeletonization.py`.

For scans with brightness drift, prefer `threshold_optimizer.py` over the MCP
global-threshold segmentation tool.

### `src/3d_visualize.py`

**Purpose:** Create optional 3D PNG renderings of NPY volumes, with or without
a skeleton overlay.

**Method:** The script downsamples and min-max normalizes an NPY array, extracts
an isosurface with marching cubes, and renders it with Matplotlib. The overlay
variant plots nonzero NPY skeleton coordinates as red points.

This module currently exposes Python functions rather than a general CLI. Its
`__main__` block contains demonstration paths, so production workflows should
import and call `visualize_3d` or `visualize_3d_with_skeleton` with explicit
paths.

## Retired analysis path

The deleted `strut_thickness_analysis.py`, `anomaly_identifier.py`, and
`missing_strut_identifier.py` scripts are no longer runnable project
components. The deleted density and strut-thickness agent definitions are also
not part of the current workflow. Missing-topology analysis is now handled by
`missing_strut_junction_analyzer.py`; the overview therefore does not direct
users to the retired thickness, density, anomaly, or endpoint-only workflows.
