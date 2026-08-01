---
name: lattice-strut-defect-detector
description: Identifies candidates for missing or broken struts in 2D grayscale CT slices of additive manufactured lattices. This skill should be used when processing individual slices to flag structural discontinuities for expert review.
---

# Lattice Strut Defect Detector

## Scope
This skill is limited to the detection of two specific defect types in 2D CT slices:
1. **Missing-strut candidates**: Entirely absent material where a strut is expected.
2. **Broken-strut candidates**: Partial material presence with a localized gap or interruption.

This skill explicitly excludes the detection of thin struts, bent struts, porosity, surface roughness, junction defects, or any other geometric irregularity.

## Direct visual observations
- The images show a repeating grid of high-intensity (bright) lines intersecting at nodes, forming a diamond-like lattice pattern.
- The background is low-intensity (dark).
- Struts appear as linear features with relatively consistent brightness and width.
- Nodes appear as brighter, slightly larger circular or polygonal intersections.
- The lattice is oriented diagonally relative to the image axes.
- Some slices show gaps in the bright lines (discontinuities) where the dark background is visible within the expected path of a strut.

## Inferred structural assumptions
- **Inference**: The lattice is intended to be a regular, periodic structure.
- **Inference**: The presence of a majority of intact struts allows for the mathematical prediction of where the remaining struts should be located.
- **Inference**: A "broken" strut is a single structural element that is partially present in the slice, whereas a "missing" strut is completely absent from the slice.

## Lattice model
The lattice is organized as a repeating grid of intersecting diagonal lines.
- **Orientation**: Struts follow two primary diagonal axes.
- **Junctions**: Nodes occur at the intersection of these diagonal axes.
- **Expectation Logic**: A script can infer expected strut locations by:
    1. Detecting the coordinates of all high-intensity nodes.
    2. Calculating the average distance and angle between adjacent nodes.
    3. Projecting linear paths between all adjacent nodes based on the dominant periodicity of the image.
    4. Defining "expected strut zones" as the areas along these projected paths.

## Detection pipeline
1. **Binarization**: Convert the grayscale slice to a binary mask using an adaptive threshold to separate material (bright) from background (dark).
2. **Node Detection**: Identify local intensity maxima or centroids of connected components that correspond to the lattice intersections.
3. **Grid Mapping**: Determine the dominant periodicity and orientation of the lattice to create a map of expected strut paths between nodes.
4. **Strut Sampling**: For every expected strut path, sample the binary mask for the presence of material.
5. **Continuity Analysis**: Analyze the distribution of material along each expected path to determine if it is fully present, partially present, or absent.
6. **Candidate Labeling**: Apply logic to categorize the result as a missing, broken, or uncertain candidate.

## Measurements
- **Material Fill Ratio**: The ratio of pixels containing material to the total number of pixels along an expected strut path. Informs both missing and broken candidates.
- **Gap Length**: The maximum contiguous length of background pixels found within an expected strut path that is otherwise partially filled. Informs broken candidates.
- **Node Connectivity**: A boolean indicating if an expected strut path is connected to both its bounding nodes. Informs broken candidates.

## Missing-strut candidate logic
A location is flagged as a `possible_missing` candidate if:
- An expected strut path is defined between two nodes.
- The **Material Fill Ratio** along that path is below a threshold indicating near-total absence of material.
- No significant material is detected between the two bounding nodes.

## Broken-strut candidate logic
A location is flagged as a `possible_broken` candidate if:
- An expected strut path is defined between two nodes.
- The **Material Fill Ratio** is above the "missing" threshold but below a "fully intact" threshold.
- There is a detected **Gap Length** that exceeds the typical noise/roughness width of a healthy strut.
- The strut fails the **Node Connectivity** check (material is present but does not form a continuous bridge between nodes).

## Distinguishing missing from broken
- **Missing**: No material detected along the expected path.
- **Broken**: Material is detected, but it is interrupted by a gap.
- **Uncertain**: If material is detected but the fill ratio is so low that it is impossible to distinguish between a severely broken strut and a nearly missing one, the label `uncertain` must be used.

## Adaptive threshold estimation
- **Binarization Threshold**: Estimated using Otsu's method or by calculating the mean intensity of the image and applying a offset based on the standard deviation of the background.
- **Intact Fill Ratio**: Estimated by calculating the average Material Fill Ratio of the top 10% of the most "complete" struts in the current slice.
- **Gap Length Threshold**: Estimated as a multiple of the average strut width (calculated from the population of intact struts in the slice).
- **Missing Fill Ratio**: Estimated as a small fraction (e.g., 10%) of the average intact fill ratio.

## Paper-derived methods
- **Centerline/Path Analysis**: Adapted from the concept of "computed centerline" (page 8). Instead of 3D skeletonization, the 2D adaptation uses the grid mapping of nodes to define expected 2D linear paths.
- **Outlier Detection**: Adapted from the use of histograms to find defective struts as outliers (page 11). The detector uses the population of struts in a single slice to establish "normal" fill ratios and flags deviations as candidates.
- **Rejected Methods**:
    - **Contour View (CV)**: Rejected (page 4, 8). Requires projecting data along a longitudinal axis across multiple slices; not possible with a single 2D slice.
    - **Roughness Map (RM)**: Rejected (page 1, 8). Focuses on surface roughness, which is explicitly excluded from this scope.
    - **3D Spatial Graph Alignment**: Rejected (page 12). Requires a CAD reference or 3D volume; this detector must operate in isolation on one slice.

## Output contract
For each slice, the detector returns a summary and a list of candidates.

**Per-slice Summary:**
- `slice_index`: Integer.
- `total_expected_struts`: Integer.
- `candidate_count`: Integer.

**Candidate Record:**
- `location`: Coordinates of the midpoint of the expected strut path.
- `label`: One of `possible_missing`, `possible_broken`, `uncertain`.
- `confidence`: A value from 0.0 to 1.0 based on the deviation from the population mean.
- `metrics`:
    - `fill_ratio`: The calculated Material Fill Ratio.
    - `max_gap_length`: The length of the largest gap found.
    - `connectivity`: Boolean (connected/disconnected).

## Diagnostics to save
- **Binarized Mask**: The image after adaptive thresholding.
- **Expectation Overlay**: A visualization showing the projected grid of expected strut paths overlaid on the original image.
- **Candidate Map**: The original image with candidates highlighted in different colors based on their label.

## Limitations
- **2D Ambiguity**: A strut appearing "missing" in one slice may simply be angled out of the plane of the slice; it cannot be confirmed as missing without 3D data.
- **Node Occlusion**: If nodes are missing or poorly defined, the grid mapping may fail, leading to missed candidates.
- **Noise**: High-intensity noise in the background may be misidentified as partial material, leading to `possible_broken` or `uncertain` labels for actually missing struts.
