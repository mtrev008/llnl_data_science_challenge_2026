# CT-Derived Surface Mesh Contract

Use this contract for a CT-segmentation-derived as-built surface export. Treat
the selected 3D segmentation mask as the scientific geometry source. Do not
substitute raw CT intensity, a skeleton, or a registered graph unless the caller
explicitly requests a different product.

## Required inputs

- Accept one readable 3D `.tif` or `.tiff` segmentation mask.
- Require a finite, positive XYZ voxel-size triplet and a unit label.
- Accept a validation report as optional context.
- Accept an output STL path, a required preview path, and optional metrics and
  manifest paths.
- Refuse an existing output unless overwrite permission is explicit.
- Resolve and report absolute paths.

The initial specimen invocation uses:

```text
mask: data/missing_struts/analysis/segmented_mask.tif
source array order: ZYX
voxel_size_xyz: [0.05809, 0.05809, 0.05809]
unit: mm
default output directory: data/missing_struts/analysis/digital_twin
```

The supplied voxel size is not independently verified. Preserve its metadata
status in warnings and provenance.

## Mask validation

Before extraction:

1. Verify that the source is three-dimensional and numeric or boolean.
2. Verify that its values represent at least one foreground and one background
   voxel.
3. For the expected `0/255` mask, use the explicit interface value `127.5`.
4. Reject a non-binary source unless the caller supplies a threshold.
5. Record shape, dtype, unique-value summary, foreground count, background
   count, and foreground fraction.
6. Inventory connected components before applying any component filter.
7. Never modify the source file.

Reject empty and all-foreground masks because they do not define a bounded
specimen surface.

## Coordinate contract

- Interpret the input array as `ZYX`.
- Treat marching-cubes vertices as `ZYX`.
- Reorder vertices to `XYZ` before mesh export.
- Apply `voxel_size_xyz` only after reordering.
- Express output coordinates in the caller-supplied unit.
- Treat the origin as specimen-relative unless a verified origin is supplied.
- Never infer a transform or claim registration from compatible bounds.
- Warn that STL does not store a coordinate-unit declaration.

For source vertex `[z, y, x]`, calculate:

```text
output_xyz = [
  x * voxel_size_x,
  y * voxel_size_y,
  z * voxel_size_z
]
```

## Extraction contract

- Use marching cubes at the explicit mask interface.
- Support overlapping Z slabs for volumes that are unsafe to process eagerly.
- Record slab depth, overlap, slab count, and boundary-merge tolerance.
- Convert slab-local Z coordinates to global Z coordinates before assembly.
- Merge numerically coincident slab-boundary vertices and remove duplicate
  faces deterministically.
- Do not use downsampled display data as the extraction source.
- Record scientific sampling as false unless the source mask itself is sampled.

The default extraction must preserve the selected segmentation boundary.

## Transformation policy

Default all geometry-altering options to disabled:

```text
minimum_component_voxels: 0
smoothing: disabled
hole_filling: disabled
decimation: disabled
```

- Do not retain only the largest component by default.
- Report every removed component and the applied threshold when component
  filtering is enabled.
- Do not fill openings that may represent missing or broken material.
- Do not smooth the scientific mesh by default.
- Keep any optional smoothed visual mesh separate from the scientific STL.
- Record face counts before and after optional decimation.
- Do not force watertightness. Report it as a mesh property.

Allow conservative cleanup of duplicate vertices, duplicate faces, unreferenced
vertices, and degenerate faces. Record every cleanup operation and its counts.

## Export interface

Implement this callable contract in `scripts/export_ct_surface.py`:

```python
def export_ct_surface(
    mask_filepath: str,
    output_filepath: str,
    voxel_size_xyz: tuple[float, float, float],
    units: str = "mm",
    mask_threshold: float | None = None,
    slab_depth: int = 48,
    slab_overlap: int = 1,
    minimum_component_voxels: int = 0,
    target_face_count: int | None = None,
    metrics_filepath: str | None = None,
    preview_filepath: str,
    overwrite: bool = False,
) -> dict:
    ...
```

Require an explicit threshold for a non-binary mask. Permit `None` for boolean
or recognized two-value masks and calculate their midpoint deterministically.

## Required artifacts

The primary artifact is:

```text
ct_as_built_surface.stl
```

Require the preview and support the remaining traceability artifacts:

```text
ct_as_built_surface_mesh_metrics.json
ct_as_built_surface_preview.png
digital_twin_manifest.json
digital_twin_report.md
```

Do not store anomaly identities in STL. Use a separate CSV, PLY, GLB, or 3MF
artifact when semantic annotations or colors are required.

## Verification contract

After export, reload the STL and verify:

- the file exists and is nonempty;
- vertex and triangle counts are positive;
- all vertices are finite;
- all face indices are valid;
- output bounds match the scaled extracted-mesh bounds within a recorded
  numeric tolerance;
- connected-component count, watertightness, Euler number, surface area, and
  available nonmanifold or degenerate-face counts are reported;
- optional metrics files exist and are nonempty when requested.
- the required preview exists, is nonempty, and was rendered from the exported
  mesh rather than from a separate geometry representation.

Treat non-watertightness as a warning for an as-built defect-bearing surface,
not an automatic failure. Treat unreadable output, invalid indices, nonfinite
geometry, or incompatible bounds as errors.

## Structured result

Return one JSON-compatible object:

```json
{
  "status": "success",
  "visualization_type": "ct_as_built_surface",
  "input_paths": ["C:\\absolute\\segmented_mask.tif"],
  "output_path": "C:\\absolute\\ct_as_built_surface.stl",
  "parameters": {
    "source_axis_order": "ZYX",
    "output_axis_order": "XYZ",
    "voxel_size_xyz": [0.05809, 0.05809, 0.05809],
    "units": "mm",
    "mask_threshold": 127.5,
    "slab_depth": 48,
    "slab_overlap": 1,
    "minimum_component_voxels": 0,
    "target_face_count": null
  },
  "statistics": {
    "source_shape_zyx": [761, 815, 837],
    "foreground_voxels": 23410270,
    "source_component_count": null,
    "retained_component_count": null,
    "vertex_count": null,
    "triangle_count": null,
    "watertight": null,
    "bounds_xyz": null
  },
  "warnings": [
    "STL does not encode coordinate units.",
    "Voxel calibration is supplied but not independently verified."
  ],
  "provenance": {
    "script": "export_ct_surface.py",
    "surface_method": "chunked_marching_cubes",
    "scientific_sampling": false,
    "mesh_decimated": false
  }
}
```

For failure, return `status: error`, a null output path, `error_type`, `error`,
and any warnings accumulated before failure. For a missing locked dependency,
return `status: blocked_environment` with the interpreter, dependency, and
exact import error.

## Scientific description

Describe the result as a **CT-segmentation-derived as-built surface visual**.
Do not call it validated CAD, a mechanically validated digital twin, or proof of
graph-to-CT registration. Preserve segmentation sensitivity, calibration
status, unknown physical origin, and any component or topology limitations in
the metrics, manifest, preview caption, and report.
