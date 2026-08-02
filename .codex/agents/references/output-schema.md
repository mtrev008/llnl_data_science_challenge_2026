# Data-validation output schema

The data-validation stage produces a comprehensive
`validation_report.json`, a human-readable `validation_report.md`, and a
compact `dataset_handoff.json`. Downstream agents should consume
`dataset_handoff.json` rather than reconstructing spatial metadata from prose
or filenames.

## General conventions

- Distances ending in `_um` are micrometers.
- Distances ending in `_mm` are millimeters.
- Volumes ending in `_mm3` are cubic millimeters.
- Physical coordinate vectors use XYZ order.
- Array vectors use the declared `array_axis_order`.
- `null` means the value is unavailable. It must not be replaced with zero,
  identity, isotropic spacing, or another guessed value.

Metadata status values are:

- `verified`: independently checked against authoritative evidence.
- `provided`: supplied by a project source but not independently verified.
- `inferred`: deterministically derived from available metadata.
- `assumed`: selected as an explicit working assumption.
- `unknown`: unavailable or unresolved.
- `conflicting`: two or more sources disagree.

## `dataset_handoff.json`

### `schema_version`

The handoff contract version. Consumers must reject unsupported major schema
versions rather than silently reinterpret fields.

### `validation`

- `decision`: `PASS`, `PASS_WITH_WARNINGS`, or `FAIL`.
- `errors`: deterministic blocking conditions.
- `warnings`: usable-data limitations.

No downstream scientific processing is permitted after `FAIL` unless the user
explicitly requests diagnosis or repair.

### `specimen_resolution`

- `status`: confidence in the specimen match.
- `method`: explicit ID, unique filename alias, no match, or ambiguous match.
- `candidates`: every candidate specimen ID.
- `specimen`: resolved specimen summary or `null`.

The specimen summary includes lattice family and intentionally missing-strut
percentage. A nominal percentage does not identify which individual struts
were deliberately removed.

### `volume`

- `path`: resolved CT input path.
- `shape`: array dimensions in stored order.
- `array_axes`: axes reported by `tifffile`.
- `dtype`: CT sample data type.

### `graph`

- `path`: resolved registered-graph input path.
- `registration_status`: spatial-registration status.
- `coordinate_bounds_check_is_registration`: always `false`.

Numerical coordinate bounds do not prove registration or specimen identity.

### `spatial_calibration`

- `voxel_size_xyz_um`: physical XYZ voxel size.
- `voxel_size_status`: calibration evidence status.
- `voxel_size_source`: selected calibration source.
- `array_axis_order`: physical axis represented by each array dimension.
- `axis_mapping_status`: axis evidence status.
- `axis_mapping_source`: selected axis source.
- `array_spacing_um`: voxel spacing corresponding to each array dimension.
- `physical_extent_xyz_mm`: full CT extent in physical XYZ order.
- `voxel_volume_mm3`: physical volume represented by one voxel.

Physical length, area, volume, and thickness calculations are prohibited when
the required calibration fields are `null`, `unknown`, or `conflicting`.

### `nominal_geometry`

- `strut_diameter_um`: supplied design reference.
- `strut_diameter_status`: evidence status for that reference.
- `strut_diameter_is_acceptance_threshold`: always `false` until an approved
  criterion changes the schema and policy.
- `strut_voxels_across_xyz`: nominal diameter divided by XYZ voxel spacing.
- `relative_density_fraction`: supplied design reference.
- `relative_density_status`: evidence status for relative density.

Nominal geometry must not be reported as an observed CT measurement.

### `measurement_permissions`

Boolean permissions include:

- `segmentation_permitted`
- `physical_length_measurement_permitted`
- `physical_thickness_measurement_permitted`
- `relative_density_measurement_permitted`
- `cad_registration_claim_permitted`
- `intentional_vs_manufacturing_classification_permitted`
- `thin_defect_classification_permitted`

Downstream agents must honor `false` values even when they could technically
run an algorithm.

### `thickness_analysis_policy`

The initial mode is `exploratory_distribution`.

- `acceptance_threshold_um` is `null`.
- `nominal_value_is_acceptance_limit` is `false`.
- `thin_defect_classification_permitted` is `false`.
- Required outputs are the per-strut median histogram, local-diameter
  histogram, and segmentation-sensitivity results.

A result may be described as belonging to a distribution tail. It must not be
called a thin defect without an approved acceptance criterion.

### `limitations`

An ordered, de-duplicated list of warnings and scientific interpretation
limits that downstream reports must preserve.

## Existing comprehensive outputs

`validation_report.json` retains full TIFF, JSON graph, STL, cross-file,
calibration, error, and warning details. CSV files and plots remain analytical
evidence. The handoff intentionally duplicates only fields required to control
downstream behavior.
