# Exact Strut Thickness Analysis Steps

This document describes the current behavior of
`src/strut_thickness_analysis.py`. It distinguishes the observed-material
thickness calculation from the optional registered-JSON defect comparison.

## Current 9×9×9 invocation

```text
python src/strut_thickness_analysis.py \
  data/9x9x9_octet_lattice/segmentation/brightness_corrected_segmented_mask.tif \
  --input-kind mask \
  --output-dir data/9x9x9_octet_lattice/segmentation/strut_thickness_analysis
```

The current thickness run does not require the registered JSON. The JSON is
used only when missing/broken strut classification is requested.

## Default parameters

| Parameter | Default | Purpose |
|---|---:|---|
| Voxel edge length | 58.1 µm | Converts 3D voxel distances to physical distance |
| Nominal target diameter | 350 µm | Sets the reference thickness and junction-exclusion radius |
| Accuracy tolerance | ±25% | Defines the 262.5–437.5 µm reference interval |
| Sample fraction | 10% | Selects evenly spaced Z slices |
| JSON search radius | 4 voxels | Searches for CT foreground around expected centerlines |

For the current volume, which contains 761 Z slices, the 10% setting selects
76 evenly spaced slices.

## Thickness calculation

### 1. Validate and load the TIFF

1. Confirm that the input filename ends in `.tif` or `.tiff`.
2. Confirm that the file exists.
3. Memory-map the TIFF with `tifffile.memmap` instead of loading the complete
   volume into memory.
4. Require a three-dimensional array. The array is interpreted in ZYX order:
   `(Z slices, Y rows, X columns)`.

### 2. Determine foreground material

- For a mask input, every voxel greater than zero is material.
- For raw CT, every voxel greater than or equal to the supplied threshold is
  material.
- In automatic mode, the script inspects up to nine planes. Boolean data or
  integer data containing only 0, 1, or 255 is treated as a mask.
- Raw CT cannot be processed without an explicit finite threshold.

### 3. Choose the sampled Z slices

The number of sampled slices is:

```text
round(total Z slices × sample fraction)
```

The indices are distributed evenly from the first through the final Z slice
using `numpy.linspace`. Duplicate integer indices are removed.

### 4. Build a 3D halo around each sampled slice

The nominal radius in voxels is:

```text
ceil((target diameter / 2) / voxel size)
```

With the defaults:

```text
ceil((350 / 2) / 58.1) = 4 voxels
```

The Z halo on each side of the sampled slice is:

```text
max(3, 2 × nominal radius + 2)
```

The current halo is therefore 10 slices on each side, except where the volume
boundary truncates it. Calculating within this slab preserves three-dimensional
neighborhood information instead of treating the sampled plane as an isolated
2D image.

### 5. Generate or load the skeleton

- If no skeleton TIFF is supplied, `skimage.morphology.skeletonize` generates a
  3D one-voxel-wide skeleton of the foreground slab.
- If a skeleton TIFF is supplied, its shape must exactly match the input TIFF.
- A supplied skeleton is rejected if it contains foreground outside the
  segmented mask.

### 6. Keep shaft centerlines and exclude junctions

1. Convolve the skeleton with a 3×3×3 neighborhood containing 26 possible
   neighbors.
2. A branch point is a skeleton voxel with more than two skeleton neighbors.
3. Dilate branch points by the nominal radius, currently four voxels.
4. On the sampled center plane, retain only skeleton voxels that:
   - have exactly two skeleton neighbors; and
   - are outside the dilated branch-point region.

This removes thick lattice junctions so they are not reported as ordinary
strut-shaft thicknesses.

### 7. Calculate the local 3D radius

The script runs SciPy's Euclidean distance transform on the 3D foreground mask:

```python
radius_um = distance_transform_edt(
    mask,
    sampling=(voxel_size_um, voxel_size_um, voxel_size_um),
)
```

At each foreground voxel, this returns the Euclidean distance to the nearest
background voxel. Because the `sampling` values are in microns, the returned
distance is already in microns.

### 8. Convert radius to local diameter

For every retained shaft-centerline voxel on the sampled plane:

```text
local diameter = 2 × distance-transform radius
```

The voxel grid causes repeated discrete values. Examples for 58.1 µm voxels:

| Centerline radius | Diameter |
|---:|---:|
| 1 voxel | 116.2 µm |
| √2 voxels | 164.3 µm |
| √3 voxels | 201.3 µm |
| 2 voxels | 232.4 µm |

The minimum observed-material diameter is therefore 116.2 µm. Missing material
does not produce a zero-diameter observation because it has no foreground
centerline voxel to measure.

### 9. Combine the sampled measurements

Measurements remain associated with their sampled Z indices for the outlier
reports. All nonempty sampled-slice arrays are also concatenated into one
distribution for the plots and overall statistics. The run stops with an error
if no valid shaft measurements are found.

## Thickness statistics and plots

### Reference categories

The reference interval is:

```text
lower = target × (1 − tolerance / 100)
upper = target × (1 + tolerance / 100)
```

With a 350 µm target and ±25% tolerance:

- Too thin: below 262.5 µm
- Within the reference interval: 262.5–437.5 µm, inclusive
- Too thick: above 437.5 µm

These are measurement-location percentages, not percentages of complete
physical struts.

### Generated plots

- `thickness_percentile_curve.png`: sorted diameter versus measurement
  percentile, with the target and reference interval.
- `thickness_box_plot.png`: observed local-diameter box plot using 1.5×IQR
  whiskers.
- `thickness_cdf.png`: empirical cumulative fraction versus local diameter.

### Generated thickness reports

- `thickness_summary.md`: P10, P25, median, P75, P90, and reference-category
  percentages.
- `high_thickness_outliers.md`: values above `Q3 + 1.5 × IQR`, grouped by
  sampled Z slice.
- `low_thickness_outliers.md`: values strictly below the fifth percentile,
  grouped by sampled Z slice. Values equal to the cutoff are excluded because
  voxel quantization creates large groups of identical measurements.

## Optional registered-JSON defect comparison

This is separate from the thickness calculation and runs only when
`--registered-json` is supplied.

### 1. Validate the registered design

1. Require a `.json` file containing nonempty `junctions` and `struts` lists.
2. Require every junction to have a unique numeric ID and a finite XYZ
   position.
3. Require every strut to have a unique ID and two valid junction references.
4. Assume the JSON is already spatially registered to the TIFF.

### 2. Rasterize each expected strut

1. Read the XYZ coordinates of the strut's two junctions.
2. Interpolate points from one endpoint to the other.
3. Reverse XYZ to ZYX for TIFF indexing.
4. Round coordinates to integer voxels.
5. Remove consecutive duplicate voxel coordinates.

This creates an expected 3D centerline; it does not render a visual image.

### 3. Search for foreground support

1. Construct a spherical set of voxel offsets using the configured search
   radius, currently four voxels.
2. At every expected-centerline point, inspect the in-bounds spherical
   neighborhood.
3. Mark the point as supported if any voxel in that neighborhood is foreground.
4. Calculate:
   - coverage fraction = supported points / total centerline points;
   - longest internal unsupported run, counting only gaps bracketed by supported
     material on both sides.

### 4. Classify the expected strut

- Missing: no expected-centerline point has foreground support.
- Broken: foreground exists, but the longest internal unsupported run is
  greater than twice the search radius. With a four-voxel radius, the cutoff is
  greater than eight rasterized centerline samples.
- Present: neither missing nor broken.

The broken-run value is a count of rasterized centerline samples. For diagonal
struts it is not necessarily equal to the count multiplied by 58.1 µm because
adjacent samples can be diagonally separated.

### 5. Write defect outputs

- `strut_defects.csv`: one row per expected JSON strut, including endpoints,
  sample count, coverage fraction, longest internal gap, and classification.
- `defect_summary.md`: totals and percentages for present, missing, and broken
  expected struts.

## Important interpretation limits

- Thickness is measured only where segmented material and a valid shaft
  centerline exist.
- Zero is not a measurable thickness in this method; missing struts are handled
  by the registered-JSON comparison.
- The absolute thickness accuracy is limited by the 58.1 µm voxel resolution,
  segmentation quality, and skeleton placement.
- Junction exclusion depends on the nominal target diameter.
- Defect classification depends on JSON-to-TIFF registration and the search
  radius.
- The default thickness results cover 76 sampled Z slices, not every one of the
  761 slices.
