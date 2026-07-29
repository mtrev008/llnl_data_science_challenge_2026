# Python Scripts: Purpose and Methods

All project Python scripts are stored in `src/`. Together, they segment CT
volumes, extract lattice centerlines, measure strut quality, detect defects, and
create report visuals.

## Typical workflow

1. Segment the raw CT scan with `threshold_optimizer.py`.
2. Create centerlines with `skeletonization.py`.
3. Measure thickness and density with the two strut-analysis scripts.
4. Compare the measured lattice with its registered design to find defects.
5. Evaluate results and generate 3D report images.

## Script reference

### `src/threshold_optimizer.py`

**What it does:** Creates a binary segmentation while compensating for CT
brightness changes between Z slices.

**How it works:** It finds the median intensity \(m_z\) of every slice and
smooths those medians with a 1D Gaussian filter to obtain \(p_z\). A known-good
slice \(r\) and threshold \(T_r\) anchor the corrected threshold profile:

\[
T_z = p_z + (T_r - p_r)
\]

Each voxel in slice \(z\) is foreground when its intensity is at least \(T_z\).
The result is saved as `0/1` in NPY or `0/255` in TIFF.

### `src/skeletonization.py`

**What it does:** Reduces a 3D binary lattice mask to one-voxel-wide
centerlines.

**How it works:** All values greater than zero become foreground, then
scikit-image's topology-preserving 3D skeletonization thins the foreground
without removing its basic connectivity. The resulting skeleton is saved as
NPY or TIFF and is used to locate shaft centers, branches, and gaps.

### `src/strut_thickness_analysis.py`

**What it does:** Treats existing segmented-mask and skeleton TIFF stacks as a
single 3D volume, converts the skeleton into a graph, and measures every
retained strut.

**How it works:** Adjacent branch voxels become junction nodes and degree-two
paths become struts. Short paths are removed as noise. A slabbed 3D Euclidean
distance transform measures diameter along every path without allocating a
full-volume distance array. Z/Y/X voxel spacing is applied independently to
the distance transform and all physical lengths. Overlapping slab guards are
expanded when a radius approaches a slab halo, preventing seam truncation.

The graph retains the original skeleton coordinates, but thickness is sampled
from the strongest local EDT ridge in a 3×3×3 neighborhood. This corrects
off-center skeleton paths without changing topology. Junction and endpoint
neighborhoods are excluded from shaft statistics.

Because the distance transform is given the physical voxel spacing, its result
is already a radius in microns. The diameter formula is:

\[
\text{diameter}_{\mu m} = 2 \times \text{EDT radius}_{\mu m}
\]

For an isotropic scan, this is equivalent to:

\[
\text{diameter}_{\mu m}
= 2 \times \text{radius}_{voxels} \times \text{voxel size}_{\mu m/voxel}
\]

The default voxel size is \(58.09\ \mu m/voxel\). For example, an EDT radius of
3 voxels corresponds to \(2 \times 3 \times 58.09 = 348.54\ \mu m\).

Thickness defects are relative to each detected strut rather than to one
global diameter alone. Ordered shaft samples are compared with that strut's
own median. At least three consecutive centerline samples below 50% of the
median are required for `potentially_broken`; isolated low-radius samples are
ignored. The P10 distribution and robust global cutoff remain analysis and
plot diagnostics, but they are not included in the concise Markdown summary.

Nearby aligned, similarly thick endpoints are matched across weak or absent
mask, skeleton, and raw-CT support. A compatible pair becomes one `broken`
strut rather than two fragments. Completely missing struts are handled
separately because they have no centerline thickness to measure.

Missing topology is inferred only from the TIFF. Intact junction-to-junction
paths teach the normal connection lengths and direction families. At least
three different neighboring junctions must predict approximately the same
empty site, their normalized direction imbalance must be below 0.65, and their
predictions must include nonparallel directions. Predictions within 55% of the
normal connection length are merged as one physical missing-node candidate.
The local skeleton must be absent, while segmentation and normalized raw-CT
support must each remain below 5%. Adjacent accepted missing nodes receive a
shared cluster ID.

A missing strut requires two present TIFF junctions, a locally expected
connection direction, no observed graph edge, less than 20% material coverage,
and a continuous unsupported run covering at least 80% of the connection.
Connections touching a missing junction are not automatically counted as
missing struts.

The JSON is read only for the expected numbers of junction and strut records.
Its positions, indices, and endpoint coordinates are never used. No
JSON-to-TIFF transform or tilt estimate is calculated.

To reject CT crop artifacts, reliable observed TIFF junctions define a 3D
convex hull. Broken and missing-strut evidence must remain 1.5 normal observed
strut lengths inside that hull. Missing-junction sites use a smaller margin of
15% of the normal strut length, together with the balanced three-neighbor
requirement, so a real node hole near the visible surface can survive while
outward crop projections are rejected. Boundary candidates are discarded.

The script writes thickness, topology-strut, and missing-junction CSV files.
Its concise Markdown summary contains only the main strut and defect counts;
it does not include PNG links, slice tables, JSON-usage notes, or detailed
diagnostics. All PNGs are stored in the output directory's `png_outputs/`
subfolder. Combined defect sheets use magenta for missing junctions, yellow
for missing struts, red for broken fragment pairs, and orange for sustained
relative thinning. One representative slice is rendered per continuous event
and its complete Z range is printed in the panel label.


### `src/mcp_server.py`

**What it does:** Exposes segmentation, slice visualization, and skeletonization
as FastMCP tools.

**How it works:** `segment_ct_dataset` applies the global rule
\(mask = I \ge T\). `visualize_slice` extracts a plane along axis 0, 1, or 2 and
linearly maps its finite minimum and maximum to the display range. `skeletonize`
delegates to `src/skeletonization.py`. This script is an integration layer, not
a separate analysis algorithm.

### `src/3d_visualize.py`

**What it does:** Creates 3D PNG renderings of NPY volumes, optionally with a
skeleton overlay.

**How it works:** It downsamples the array for speed, min-max normalizes it to
`0–1`, and uses marching cubes at a chosen threshold to convert the voxel field
into a triangle surface mesh. Matplotlib renders that mesh at the requested
elevation and azimuth. The overlay version plots nonzero skeleton coordinates
as red points on a transparent surface.


## Choosing between related scripts

- Use `threshold_optimizer.py` for brightness drift; use the MCP global
  threshold tool only when one threshold works across the full volume.
- Use `strut_thickness_analysis.py` for physical diameter accuracy and
  `strut_density_analysis.py` for combined material-presence evidence.
- Use `anomaly_identifier.py` for detailed graph and raw-CT verification;
  use `missing_strut_identifier.py` for a faster endpoint check.
- Use `evaluation_of_segmentations.py` for 2D image scoring, not physical
  measurements of the complete 3D volume.
