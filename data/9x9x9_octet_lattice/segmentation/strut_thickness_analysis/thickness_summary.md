# Strut Thickness Summary

- TIFF: `data/9x9x9_octet_lattice/segmentation/brightness_corrected_segmented_mask.tif`
- Sampled Z slices: **76 of 761**
- Shaft-centerline measurements: **60832**
- Cubic voxel edge length: **58.1 µm**. This is the published cubic CT voxel size for this dataset ([Tran et al., 2023](https://doi.org/10.1016/j.ndteint.2023.102870)).
- Nominal designed strut diameter: **350 µm** (a design target, not the CT voxel size)
- Accepted range: **262.5–437.5 µm**

## Measured local-diameter distribution

- P10: **232.4 µm**
- P25: **232.4 µm**
- Median: **284.6 µm**
- P75: **328.7 µm**
- P90: **348.6 µm**
- Too thin: **46.19%**
- Within accepted range: **52.23%**
- Too thick: **1.58%**

These are segmentation-derived local diameters computed from the 3D Euclidean distance transform at shaft centerline voxels. Their absolute accuracy is limited by the 58.1 µm voxel resolution and the quality of the segmentation.
The distribution contains observed foreground only. Its smallest possible centerline diameter is two voxel radii (116.2 µm). Missing struts are absent observations, not zero-diameter measurements, and are reported separately in the expected-strut defect results.
