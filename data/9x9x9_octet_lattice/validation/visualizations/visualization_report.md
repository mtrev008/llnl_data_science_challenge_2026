# Validation Visualization Report

## Request

Create scientific visualizations from the validated 9x9x9 octet-lattice CT
volume and registered graph.

## Inputs

- CT volume: `data/9x9x9_octet_lattice/9x9x9_octet_lattice.tif`
- Registered graph: `data/missing_struts/registered_jsons/210127_Brian_Tran_strut_lattices_0point5dash1 1 Slices.json`
- Validation report: `data/9x9x9_octet_lattice/validation/validation_report.json`

The upstream deterministic validation decision was `PASS` with no reported
errors or warnings.

## Generated artifacts

- `histograms/tiff_intensity_distribution.png`
- `statistical_plots/tiff_slice_mean.png`
- `statistical_plots/tiff_slice_standard_deviation.png`
- `ct_slices/tiff_z_slice_000.png`
- `ct_slices/tiff_z_slice_380.png`
- `ct_slices/tiff_z_slice_760.png`
- `ct_slices/tiff_orthogonal_center_views.png`
- `graph_views/registered_graph_xy_projection.png`
- `visualization_manifest.json`

## Observations

- The complete streamed TIFF histogram contains 519,119,955 voxels. Its mean
  intensity is approximately 34,296 and its median is 32,409. The higher mean
  and extended high-intensity tail indicate a right-skewed distribution.
- Mean slice intensity is relatively stable through most of the interior and
  rises strongly near both ends of the Z stack. The end slices also have larger
  intensity variation.
- Slice standard deviation shows regular interior peaks. These periodic peaks
  are consistent with changes in the amount and orientation of lattice material
  intersected by successive slices; the plot alone does not establish a defect.
- Slice 380 and the orthogonal center views visibly preserve the repeating
  lattice structure. Bright junctions and struts are clearly separated from
  the darker background under the recorded display window.
- The registered graph XY projection has a regular repeated node-edge pattern.
  The validation report recorded 10,206 junctions, 18,468 struts, no duplicate
  critical IDs, and no invalid endpoint references.

## Limitations

- CT values are scanner or reconstruction intensity, not calibrated physical
  density.
- No voxel spacing or physical units were supplied, so no physical scale bar is
  shown.
- The graph view is a 2D XY projection of 3D coordinates.
- The validation report's coordinate-bounds check supports numerical
  plausibility only; it does not prove spatial registration or CT-material
  overlap.

## Provenance

All TIFF distribution and slice-trend calculations processed all 761 pages.
The integer histogram counted every voxel without sampling. See
`visualization_manifest.json` for paths, parameters, statistics, rendering
metadata, and upstream validation context for every artifact.
