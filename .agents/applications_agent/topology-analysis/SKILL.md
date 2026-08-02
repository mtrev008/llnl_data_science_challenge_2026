---
name: topology-analysis
description: Validate and quantify lattice-graph topology, connectivity, boundary-to-boundary routes, node degree, bridge edges, articulation nodes, and defect-tolerance screening. Use for lattice graphs, skeleton-derived networks, missing or broken strut candidates, load-path redundancy screening, and topology evidence before beam, solid, or nonlinear structural analysis.
---

# Lattice Topology Analysis

Calculate topology metrics reproducibly. Label every result as a graph indicator, not a physical force, stress, stiffness, capacity, or safety margin.

## Workflow

1. Identify a graph with node IDs, coordinates, and member endpoints. Record its source and coordinate system.
2. Validate unique node IDs, finite coordinates, valid member endpoints, self-loops, and duplicate edges. Stop if these errors change connectivity.
3. Run `scripts/analyze_lattice_topology.py` with a graph and chosen boundary axis. The script forms lower and upper terminal sets from coordinate extent and reports through-thickness connectivity. Use `--merge-coincident-nodes` only when repeated coordinates are known to represent the same physical junction.
4. Read [metric-definitions.md](references/metric-definitions.md) before interpreting components, degree, bridges, articulation nodes, or routes.
5. If defect candidates lack a validated graph-edge mapping, summarize them only. Do not remove proxy edges or claim defect-specific topology loss.
6. Save output in `<dataset>/pipeline_outputs/topology_analysis/` and hand off the summary and valid edge mapping to the structural-mechanics skill.

## Gates

- A spatially close defect candidate is not proof of a graph-edge identity.
- Do not merge nodes by coordinate unless the graph representation duplicates physical junctions across cells; record the merge tolerance.
- Boundary terminal sets and axes must be stated; through-thickness results change with this choice.
- Bridges and articulation nodes are graph vulnerabilities, not mechanical single points of failure.
- Calculate defect-removal, combined-defect, and edge-disjoint-path tolerance only after a validated candidate-to-edge mapping is supplied.
- Do not infer load redistribution, stress concentration, or criticality from centrality or connectivity alone.

## Outputs

- `topology_summary.json`: graph validation, component, degree, boundary-route, bridge, articulation, and defect-mapping status.
- `bridge_edges.csv`: all graph bridges for spatial review.
- `topology_report.md`: compact handoff with limitations.

## Example

```powershell
& "C:\Users\andre\miniconda3\envs\dssi_env\python.exe" `
  .agents\applications_agent\topology-analysis\scripts\analyze_lattice_topology.py `
  --graph "data\missing_struts\registered_jsons\210127_Brian_Tran_strut_lattices_0point5dash1 1 Slices.json" `
  --defect-candidates "data\missing_struts\analysis\strut_thickness_analysis\topology_strut_defects.csv" `
  --axis z `
  --merge-coincident-nodes `
  --output-dir "data\missing_struts\pipeline_outputs\topology_analysis"
```
