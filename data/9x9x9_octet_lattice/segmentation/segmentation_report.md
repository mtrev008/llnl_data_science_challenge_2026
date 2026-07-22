# Segmentation Report

## Inputs
- Input dataset: `/home/mtrev008/Desktop/LLNL_DSC/llnl_data_science_challenge_2026/data/9x9x9_octet_lattice/9x9x9_octet_lattice.tif`
- Output directory: `/home/mtrev008/Desktop/LLNL_DSC/llnl_data_science_challenge_2026/data/9x9x9_octet_lattice/segmentation`
- Read mode: `2d_fallback`
- Limitation: The TIFF did not expose a readable multi-page stack. Segmentation was performed deterministically on the single readable page.
- TIFF series count: `1`
- TIFF page count: `1`
- TIFF reported shape: `(815, 837)`
- TIFF axes: `YX`
- Working array shape: `(1, 815, 837)`

## Intensity Statistics
- Min: `5304.000`
- Max: `61876.000`
- Mean: `49093.406`
- Std: `10063.883`
- Quantiles: `{'0.000': 5304.0, '0.001': 16724.0, '0.010': 24235.5390625, '0.050': 29706.69921875, '0.250': 40754.5, '0.500': 53404.0, '0.750': 56302.0, '0.950': 58441.0, '0.990': 59375.0, '0.999': 60217.0, '1.000': 61876.0}`
- Threshold estimates: `{'triangle': 48285.461, 'yen': 49832.352, 'otsu': 43865.773, 'li': 42746.98, 'isodata': 43644.789}`

## Final Selection
- Selected candidate: `triangle_bright_r1`
- Threshold method: `triangle`
- Threshold value: `48285.461`
- Polarity: `bright`
- Closing radius: `1`
- Minimum object size: `128`
- Maximum hole size: `128`
- Foreground voxel count: `499234`
- Background voxel count: `182921`
- Foreground fraction: `0.731848`
- Score: `1.891641`

## Optimization Iterations

| Iteration | Candidate | Threshold | Polarity | Close | Min object | Max hole | Foreground fraction | Components | Score | Note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | triangle_bright_r1 | triangle=48285.461 | bright | 1 | 128 | 128 | 0.731848 | 1 | 1.891641 | improved best |
| 2 | triangle_dark_r1 | triangle=48285.461 | dark | 1 | 128 | 128 | 0.268273 | 1 | 1.427542 | no improvement |
| 3 | yen_bright_r1 | yen=49832.352 | bright | 1 | 128 | 128 | 0.728521 | 1 | 1.868919 | no improvement |
| 4 | yen_dark_r1 | yen=49832.352 | dark | 1 | 128 | 128 | 0.273152 | 6 | 1.206791 | no improvement |

## Outputs
- Script: `/home/mtrev008/Desktop/LLNL_DSC/llnl_data_science_challenge_2026/data/9x9x9_octet_lattice/segmentation/segment_lattice.py`
- Final mask: `/home/mtrev008/Desktop/LLNL_DSC/llnl_data_science_challenge_2026/data/9x9x9_octet_lattice/segmentation/9x9x9_octet_lattice_mask.tif`
- Slice visualization: `/home/mtrev008/Desktop/LLNL_DSC/llnl_data_science_challenge_2026/data/9x9x9_octet_lattice/segmentation/mask_slice_380.png`
- Histogram: `/home/mtrev008/Desktop/LLNL_DSC/llnl_data_science_challenge_2026/data/9x9x9_octet_lattice/segmentation/intensity_histogram.png`
- Optimization overview: `/home/mtrev008/Desktop/LLNL_DSC/llnl_data_science_challenge_2026/data/9x9x9_octet_lattice/segmentation/optimization_overview.png`
- Report: `/home/mtrev008/Desktop/LLNL_DSC/llnl_data_science_challenge_2026/data/9x9x9_octet_lattice/segmentation/segmentation_report.md`

## Notes
- The requested `mask_slice_380.png` could not represent slice 380 because the readable TIFF data exposed only one page. The output image shows page 0 with the required filename.
