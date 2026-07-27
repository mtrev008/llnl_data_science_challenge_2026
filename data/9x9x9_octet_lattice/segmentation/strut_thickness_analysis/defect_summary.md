# Expected-Strut Defect Summary

- TIFF: `data/9x9x9_octet_lattice/segmentation/brightness_corrected_segmented_mask.tif`
- Registered design: `data/missing_struts/registered_jsons/210127_Brian_Tran_strut_lattices_0point5dash1 1 Slices.json`
- Expected struts: **18468**
- Present struts: **16645** (90.13%)
- Missing struts: **601** (3.25%)
- Broken struts: **1222** (6.62%)

## Classification method

- Missing: no foreground support anywhere along an expected JSON centerline.
- Broken: foreground exists on both sides of an internal unsupported run longer than **8 voxels**.
- Present: neither of the above conditions is met.
- These rules detect defects from this TIFF and do not force the counts to match literature percentages.

## Diagnostic parameters

- Broken-run cutoff: **8 voxels** (**464.8 µm**), derived from the diameter of the registration-search neighborhood.
- Registration search radius: **4 voxels**

Thickness categories describe material around surviving centerlines. Missing and broken classifications instead compare every expected design centerline with foreground in the TIFF.
