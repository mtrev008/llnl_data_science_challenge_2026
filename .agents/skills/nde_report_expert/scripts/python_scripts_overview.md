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

**What it does:** Measures strut diameter in microns and reports thin, accurate,
and thick regions. It can also compare expected struts from a registered JSON
with the measured volume.

**How it works:** The script samples evenly spaced Z slices and skeletonizes a
3D neighborhood around each one. Skeleton points with exactly two neighbors are
treated as shaft centerlines; branch regions are excluded so thick junctions do
not inflate shaft measurements. A 3D Euclidean distance transform gives the
distance from each centerline point to the nearest background voxel.

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

The default voxel size is \(58.1\ \mu m/voxel\). For example, an EDT radius of
3 voxels corresponds to \(2 \times 3 \times 58.1 = 348.6\ \mu m\).

The tolerance bounds are:

\[
\text{lower} = \text{target}(1-\text{tolerance}/100)
\]

\[
\text{upper} = \text{target}(1+\text{tolerance}/100)
\]

Measurements below, within, or above these bounds are reported as too thin,
accurate, or too thick. The script produces percentile, box, and CDF plots plus
Markdown outlier summaries. In design-comparison mode, no foreground support
along an expected centerline means `missing`; an internal unsupported run
longer than twice the search radius means `broken`.

### `src/strut_density_analysis.py`

**What it does:** Assigns every expected strut a relative `0–1`
material-presence score and classifies it as present, uncertain, low-density,
broken, or missing.

**How it works:** At points along each ideal strut, the script samples a disk
perpendicular to the shaft and calculates:

- mask score: mean segmented occupancy in the sampled disks;
- raw score: mean slice-normalized CT intensity;
- thickness score: equivalent thickness divided by target thickness;
- continuity score: supported centerline coverage penalized by the longest gap.

Raw intensity is normalized per slice using:

\[
I_{norm} = \operatorname{clip}
\left(\frac{I-\operatorname{median}(slice)}
{P_{99.5}(slice)-\operatorname{median}(slice)},0,1\right)
\]

Disk occupancy is converted to an equivalent thickness using:

\[
t_{equiv} = t_{target}\sqrt{\text{occupancy}}
\]

The square root is used because cross-sectional area is proportional to
diameter squared. The final density score is a weighted sum:

\[
D = w_mM + w_rR + w_tT + w_cC
\]

The default weights are 0.30 mask, 0.30 raw CT, 0.25 thickness, and 0.15
continuity. Otsu's method finds a data-driven score threshold. No support means
`missing`; a gap longer than twice the search radius means `broken`; values
clearly below the threshold are `low_density`; borderline or conflicting mask
and raw signals are `uncertain`; the remainder are `present`.

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

### `src/anomaly_identifier.py`

**What it does:** Finds lattice defects by comparing an observed skeleton graph
with a registered reference design, then verifies candidates against the mask
and raw CT.

**How it works:** Skeleton voxels are connected into a graph; clustered branch
voxels become junctions and paths between junctions become observed struts. A
KD-tree measures each reference centerline point's distance to the observed
graph. A long run beyond the matching tolerance becomes a candidate. Candidate
points are then checked in local mask and raw-CT neighborhoods. Strong mask or
raw coverage marks a likely segmentation weakness; low coverage plus an
excessive gap confirms an anomaly.

### `src/missing_strut_identifier.py`

**What it does:** Performs a quicker endpoint-based count of missing and broken
struts.

**How it works:** It probes inward from each end of every reference strut. Only
the required CT slices are normalized, thresholded, and skeletonized. An
endpoint counts as present when its local mask coverage exceeds the minimum or
its patch contains skeleton. Neither endpoint present means `missing`; exactly
one endpoint present means `broken`. It saves the processed endpoint slices and
a Markdown count summary.

### `src/evaluation_of_segmentations.py`

**What it does:** Scores a 2D segmentation result against a ground-truth image
from 0 to 5.

**How it works:** It extracts foreground masks, removes likely plot artifacts,
crops empty margins, and resizes the result to the truth. Its main overlap
metric is intersection over union:

\[
IoU = \frac{TP}{TP+FP+FN}
\]

It also compares connected components, skeleton endpoints, junctions,
over-segmentation, under-segmentation, and small artifacts. A weighted quality
value uses 35% IoU, 20% connectivity, 20% junction agreement, 10% endpoint
agreement, 7.5% each for over/under-segmentation, and an artifact penalty.
Rule-based cutoffs convert that value and the topology errors into the final
integer score and Markdown explanation.

## Choosing between related scripts

- Use `threshold_optimizer.py` for brightness drift; use the MCP global
  threshold tool only when one threshold works across the full volume.
- Use `strut_thickness_analysis.py` for physical diameter accuracy and
  `strut_density_analysis.py` for combined material-presence evidence.
- Use `anomaly_identifier.py` for detailed graph and raw-CT verification;
  use `missing_strut_identifier.py` for a faster endpoint check.
- Use `evaluation_of_segmentations.py` for 2D image scoring, not physical
  measurements of the complete 3D volume.
