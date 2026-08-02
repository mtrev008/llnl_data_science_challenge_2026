# Visualization Output Schema

## Contents

- Base artifact contract
- CT-derived surface artifact
  - Surface parameters
  - Source-mask statistics
  - Extraction and transformation
  - Reloaded-mesh verification
  - Required preview and provenance
  - Failure states
- Manifest storage
- Sampling provenance
- Display reduction
- Output tree and report

Return one JSON object per artifact with `status`, `visualization_type`,
`input_paths`, `output_path`, `parameters`, `statistics`, `warnings`, and
`provenance`.

```json
{
  "status": "success",
  "visualization_type": "histogram",
  "input_paths": ["C:\\absolute\\source.npy"],
  "output_path": "C:\\absolute\\plot.png",
  "parameters": {},
  "statistics": {},
  "warnings": [],
  "provenance": {
    "script": "generate_visualization.py",
    "sampled": false,
    "sampling_method": null
  }
}
```

For failure, use `status: error`, a null output, `error_type`, and `error`. For an
unavailable locked environment, use `blocked_environment` and include the
interpreter, missing dependency, and exact import error.

## CT-derived surface artifact

Use `visualization_type: ct_as_built_surface` for an STL extracted from a 3D
segmentation mask. Return one primary artifact that references its required
preview and optional metrics sidecar:

```json
{
  "status": "success",
  "visualization_type": "ct_as_built_surface",
  "input_paths": ["C:\\absolute\\segmented_mask.tif"],
  "output_path": "C:\\absolute\\ct_as_built_surface.stl",
  "preview_path": "C:\\absolute\\ct_as_built_surface_preview.png",
  "metrics_path": "C:\\absolute\\ct_as_built_surface_mesh_metrics.json",
  "parameters": {},
  "statistics": {},
  "warnings": [],
  "provenance": {}
}
```

Require `preview_path` for success. Permit `metrics_path: null` when a separate
metrics JSON was not requested. Verify the STL and preview are nonempty before
returning success.

### Surface parameters

Record:

```json
{
  "source_axis_order": "ZYX",
  "output_axis_order": "XYZ",
  "voxel_size_xyz": [0.05809, 0.05809, 0.05809],
  "units": "mm",
  "mask_threshold": 127.5,
  "slab_depth": 48,
  "slab_overlap": 1,
  "minimum_component_voxels": 0,
  "target_face_count": null
}
```

Require finite positive voxel sizes and a nonempty unit label. State in
warnings that STL does not encode its units. Record the calibration status in
warnings or validation context; never promote supplied or assumed calibration
to verified.

### Source-mask statistics

Record:

```json
{
  "source_shape_zyx": [761, 815, 837],
  "source_dtype": "uint8",
  "foreground_voxels": 23410270,
  "background_voxels": 495709685,
  "foreground_fraction": 0.04509607,
  "source_component_count": null,
  "component_sizes_voxels": null,
  "inventory_skipped": true,
  "inventory_reason": "Binary mask exceeds the configured eager component-inventory limit"
}
```

Use exact values from the selected mask. When component inventory is skipped,
preserve both the skipped flag and reason; do not replace an unknown count with
zero.

### Surface extraction and transformation

Record extraction and geometry-altering operations separately:

```json
{
  "processed_slab_count": 16,
  "component_filter_applied": false,
  "removed_component_count": 0,
  "removed_voxel_count": 0,
  "before_cleanup": {
    "vertex_count": 1000,
    "triangle_count": 2000
  },
  "after_cleanup": {
    "vertex_count": 990,
    "triangle_count": 1980
  },
  "mesh_decimated": false,
  "triangle_count_before_decimation": 1980,
  "triangle_count_after_decimation": 1980
}
```

Do not describe duplicate/degenerate cleanup as scientific sampling. Set
`scientific_sampling: true` only when source-mask values or extraction coverage
were sampled.

### Reloaded-mesh verification

Calculate final mesh statistics from the reloaded STL:

```json
{
  "vertex_count": 990,
  "triangle_count": 1980,
  "connected_component_count": 2,
  "watertight": false,
  "euler_number": 1,
  "surface_area": 125.5,
  "bounds_xyz": [[0.0, 0.0, 0.0], [41.0, 39.0, 37.0]],
  "finite_vertices": true,
  "valid_face_indices": true,
  "degenerate_face_count": 0,
  "bounds_validation_tolerance": 0.000005809
}
```

Treat nonfinite vertices, invalid face indices, unreadable STL output, empty
geometry, or bounds outside the recorded tolerance as errors. Treat
non-watertightness as a warning unless watertightness was explicitly required.

### Required preview

Render the preview from the reloaded STL, never from a separate geometry
representation. Record preview reduction as display-only provenance:

```json
{
  "preview": {
    "preview_face_stride": 20,
    "preview_faces_rendered": 50000,
    "preview_path": "C:\\absolute\\ct_as_built_surface_preview.png"
  }
}
```

Preview face subsampling does not set scientific sampling to true and must not
change the STL.

### Surface provenance

Record:

```json
{
  "script": "export_ct_surface.py",
  "surface_method": "chunked_marching_cubes",
  "scientific_sampling": false,
  "mesh_decimated": false,
  "preview": {},
  "created_utc": "2026-07-29T00:00:00+00:00"
}
```

Preserve upstream validation context when supplied. Reference existing anomaly
CSV paths only as inputs or report provenance; do not record them as newly
generated mesh artifacts.

### Surface failures

For an export failure, return:

```json
{
  "status": "error",
  "visualization_type": "ct_as_built_surface",
  "input_paths": ["C:\\absolute\\segmented_mask.tif"],
  "output_path": null,
  "error_type": "ValueError",
  "error": "Exact error message",
  "warnings": []
}
```

For a missing locked dependency, return:

```json
{
  "status": "blocked_environment",
  "visualization_type": "ct_as_built_surface",
  "input_paths": ["C:\\absolute\\segmented_mask.tif"],
  "output_path": null,
  "interpreter": "C:\\Users\\andre\\miniconda3\\envs\\dssi_env\\python.exe",
  "dependency": "trimesh",
  "error": "Exact import error",
  "warnings": []
}
```

Store manifests as:

```json
{"schema_version": "1.0", "artifacts": []}
```

Every artifact entry must include exact paths, type, field/slice metadata,
parameters, statistics, sampling, validation decision, warnings, producer, and
UTC timestamp. Record success only after verifying a nonempty output.

## Sampling provenance

Record scientific or display-window sampling explicitly:

```json
{
  "sampled": true,
  "sampling_method": "regular_stride",
  "sampled_component": "display_window",
  "source_value_count": 518875755,
  "sample_value_count": 1995676,
  "stride": 260
}
```

For streaming TIFF calculations, record coverage separately:

```json
{
  "statistics_source": "streamed_tiff_pages",
  "pages_processed": 761,
  "histogram_count_coverage": 1.0
}
```

`histogram_count_coverage: 1.0` means every finite value was counted even when
floating-point bin-edge selection used a sample.

## Display reduction

Record display-only reduction without setting scientific sampling:

```json
{
  "render_downsampled": true,
  "original_dimensions": [12000, 10000],
  "rendered_dimensions": [4096, 3413],
  "render_sampling_method": "regular_grid",
  "render_row_stride": 3,
  "render_column_stride": 3
}
```

Use nearest-neighbor display reduction for masks and categorical arrays. Never
calculate scientific statistics from the rendered array.

Use this output tree:

```text
visualizations/
  visualization_manifest.json
  visualization_report.md
  histograms/
  statistical_plots/
  ct_slices/
  segmentation_overlays/
  graph_views/
  surface_meshes/
  iteration_comparisons/
  thumbnails/
```

A Markdown report should cover request, inputs, validation status, artifacts,
important observations, warnings, skipped items, and output paths.
