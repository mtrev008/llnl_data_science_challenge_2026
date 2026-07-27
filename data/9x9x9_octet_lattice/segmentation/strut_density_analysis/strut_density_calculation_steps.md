# Exact JSON-Guided Strut Density Calculation Steps

## Inputs used

- Raw CT: `data/missing_struts/tif_stacks/210127_Brian_Tran_strut_lattices_0point5dash1 1 Slices.tif`
- Segmented mask: `data/9x9x9_octet_lattice/segmentation/brightness_corrected_segmented_mask.tif`
- Registered ideal-design JSON: `data/missing_struts/registered_jsons/210127_Brian_Tran_strut_lattices_0point5dash1 1 Slices.json`
- Cubic voxel size: **58.1 µm**
- Nominal target diameter: **350 µm**

## Process

1. Validate that raw CT and mask TIFFs are 3D and have identical shapes.
2. Validate JSON junction IDs and XYZ positions, strut endpoint references, and unit-cell membership.
3. Normalize each raw CT Z slice: subtract its median, divide by (P99.5 − median), and clip to 0–1.
4. Interpolate each ideal JSON strut between its two junctions, convert XYZ sampling coordinates to TIFF ZYX indices, and exclude 4 samples at each endpoint to reduce node bias.
5. Construct a perpendicular radius-4-voxel sampling disk at every remaining shaft point.
6. Measure mask occupancy and normalized raw CT signal across those cross-sections.
7. Mark local support when mask material is present or normalized raw signal is at least 0.50; calculate coverage and the longest internal unsupported run.
8. Estimate equivalent local diameter as target diameter × sqrt(cross-sectional mask occupancy), then take the median of supported shaft samples.
9. Convert occupancy, raw CT, equivalent thickness, and continuity to bounded 0–1 component scores.
10. Calculate the combined material-presence score:

```text
score = 0.30×mask occupancy + 0.30×raw CT + 0.25×thickness + 0.15×continuity
```

11. Apply Otsu separation to all strut scores. This run's threshold is **0.409112**.
    Use the conservative low-density cutoff Otsu minus the uncertainty margin: **0.359112**.
12. Classify in order:
    - Missing: no raw-or-mask support anywhere on the shaft.
    - Broken: internal unsupported run longer than 8 rasterized centerline samples.
    - Low density: score below the conservative low-density cutoff.
    - Uncertain: score within 0.050 of the threshold or mask/raw disagreement greater than 0.250.
    - Present: none of the above.
13. Aggregate each JSON unit cell from the scores and classes of its listed struts.
14. Count each low-density strut once on every Z slice intersected by its ideal JSON centerline.
15. Write per-strut, per-unit-cell, and per-slice CSV files plus the Markdown summary.

## Output definitions

- `strut_density.csv`: one traceable row per ideal JSON strut.
- `unit_cell_density.csv`: aggregate density and defect counts by unit cell.
- `low_density_struts_by_slice.csv`: all Z slices, low-density counts, and intersecting strut IDs.
- `density_summary.md`: totals and lowest-density candidates.
- `strut_density_calculation_steps.md`: this parameter-specific document.

## Limitations

- Density score is a relative 0–1 material-presence score, not calibrated mass density.
- Results depend on JSON-to-TIFF registration and segmentation quality.
- Equivalent thickness comes from cross-sectional occupied area; the separate thickness agent provides independent global EDT-based thickness validation.
- Diagonal rasterized gap counts do not convert exactly to axial microns.
