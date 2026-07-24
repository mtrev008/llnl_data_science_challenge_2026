# Unit-cell voxel-span assessment

- JSON unit cells: 729 (indices 0–8 on i, j, and k)
- TIFF shape ZYX: (761, 815, 837)
- Unit-cell geometry: bounding box of unique junction endpoints from each cell's referenced struts

## Registered-coordinate spans

- X: min 79.442674, median 79.442674, max 79.442674; mean 79.442674
- Y: min 79.596705, median 79.596705, max 79.596705; mean 79.596705
- Z: min 79.261223, median 79.261223, max 79.261223; mean 79.261223

## Conditional integer covering boxes

These figures apply only if registered JSON XYZ units are interpreted as TIFF XYZ voxel indices.
- X covering count: min 81, median 81, max 82
- Y covering count: min 81, median 82, max 82
- Z covering count: min 81, median 81, max 82
- Bounding-box count: min 531441, median 538002, max 551368

These are box voxels, including void, and are not actual lattice-material voxel counts.

## Identifiability

The exact number of material/foreground voxels belonging to a unit cell is not determined by the TIFF and JSON alone. A segmentation mask and an explicit convention for assigning shared struts and boundary voxels to cells are required.