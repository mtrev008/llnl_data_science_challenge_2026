# Visualization Output Schema

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
  iteration_comparisons/
  thumbnails/
```

A Markdown report should cover request, inputs, validation status, artifacts,
important observations, warnings, skipped items, and output paths.
