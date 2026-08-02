---
name: as-built-geometric-analysis
description: Measure, validate, and report CT-derived as-built lattice geometry from graph, strut-measurement, segmentation-mask, and nominal-reference artifacts. Use for strut length, orientation, diameter or thickness statistics, circular-equivalent section properties, slenderness screening, local or global relative density, nominal-to-as-built geometry comparison, and geometry evidence preparation before topology or structural-mechanics analysis.
---

# As-Built Geometric Analysis

Create a traceable geometry report. Keep direct measurements separate from derived engineering indicators and do not convert geometry evidence into stress, stiffness, capacity, or defect-criticality claims.

## Required workflow

1. Identify the graph, segmentation mask, nominal model, strut-measurement table, or combination. Record source paths, coordinate convention, and voxel calibration.
2. Confirm coordinates, units, and graph integrity. Stop member-level interpretation if node IDs, member endpoints, or positions are invalid or coordinate axes are ambiguous.
3. Run `scripts/analyze_lattice_geometry.py`. Provide `--voxel-size-mm` only when sourced. Summarize `--measurements` separately unless a validated graph-edge ID mapping exists. Provide `--mask` only for a calibrated segmentation mask.
4. Read [metric-definitions.md](references/metric-definitions.md) before interpreting diameter, section, slenderness, or relative-density outputs.
5. Save results under `<dataset>/pipeline_outputs/as_built_geometric_analysis/` or the dataset's established analysis folder. Preserve sources and assumptions in the JSON summary.
6. Explicitly report invalid or unavailable quantities. Never infer material properties, load direction, joint restraint, defect-to-edge identity, or nominal correspondence from proximity alone.

## Analysis gates

- Do not use a graph `thickness` field as physical diameter when its unit or definition is unknown.
- Do not join a measurement table to graph members solely because integer IDs match.
- Treat mask relative density as segmentation-derived and report its provenance and calibration status.
- Use orientation relative to loading only when the axis mapping is supplied.
- Treat circular section properties and slenderness as screening indicators until section shape and end restraint are justified.
- Do not call a member thin, missing, critical, or failed without an approved defect definition and downstream evidence.

## Outputs

- `as_built_geometry_summary.json`: sources, validation, units, distributions, and limitations.
- `strut_geometry.csv`: valid graph members with length and absolute direction cosines.
- `as_built_geometry_report.md`: concise handoff for topology and mechanics agents.

## Example

```powershell
& "C:\Users\andre\miniconda3\envs\dssi_env\python.exe" `
  .agents\applications_agent\as-built-geometric-analysis\scripts\analyze_lattice_geometry.py `
  --graph "data\missing_struts\registered_jsons\210127_Brian_Tran_strut_lattices_0point5dash1 1 Slices.json" `
  --voxel-size-mm 0.05809 `
  --measurements "data\missing_struts\analysis\strut_thickness_analysis\strut_defects.csv" `
  --output-dir "data\missing_struts\pipeline_outputs\as_built_geometric_analysis"
```
