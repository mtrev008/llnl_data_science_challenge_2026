#!/usr/bin/env python
"""Validate and summarize topology of a lattice graph; outputs are graph indicators only."""
from __future__ import annotations
import argparse, csv, json, math
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import networkx as nx

AXIS = {"x": 0, "y": 1, "z": 2}

def boundary_edge_connectivity(graph, lower, upper):
    """Return the terminal-set minimum edge cut / edge-disjoint path count."""
    lower, upper = set(lower) & set(graph), set(upper) & set(graph)
    if not lower or not upper: return None
    directed = nx.DiGraph()
    directed.add_nodes_from(graph)
    for first, second in graph.edges():
        directed.add_edge(first, second, capacity=1)
        directed.add_edge(second, first, capacity=1)
    source, sink, infinite = object(), object(), graph.number_of_edges()+1
    directed.add_node(source); directed.add_node(sink)
    for node in lower: directed.add_edge(source, node, capacity=infinite)
    for node in upper: directed.add_edge(node, sink, capacity=infinite)
    return int(nx.maximum_flow_value(directed, source, sink, capacity="capacity"))

def write_edge_screening_metrics(path, graph, positions, lower, upper):
    """Write intact-graph betweenness and boundary distances for every edge."""
    import numpy as np
    from scipy.spatial import cKDTree
    betweenness = nx.edge_betweenness_centrality(graph, normalized=True)
    lower_hops = nx.multi_source_dijkstra_path_length(graph, lower, weight=None)
    upper_hops = nx.multi_source_dijkstra_path_length(graph, upper, weight=None)
    lower_tree = cKDTree(np.asarray([positions[node] for node in lower]))
    upper_tree = cKDTree(np.asarray([positions[node] for node in upper]))
    rows = []
    for first, second, data in graph.edges(data=True):
        midpoint = (np.asarray(positions[first])+np.asarray(positions[second]))/2
        rows.append({"strut_id": data["strut_id"], "junction0": first, "junction1": second,
                     "edge_betweenness_normalized": betweenness[(first,second)],
                     "lower_boundary_hops": min(lower_hops[first],lower_hops[second]),
                     "upper_boundary_hops": min(upper_hops[first],upper_hops[second]),
                     "lower_boundary_euclidean_graph_units": float(lower_tree.query(midpoint)[0]),
                     "upper_boundary_euclidean_graph_units": float(upper_tree.query(midpoint)[0])})
    rows.sort(key=lambda row: row["strut_id"])
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    values = [row["edge_betweenness_normalized"] for row in rows]
    return {"path": path.name, "edge_count": len(rows), "edge_betweenness_normalized_min": min(values),
            "edge_betweenness_normalized_max": max(values),
            "edge_betweenness_normalized_mean": sum(values)/len(values)}

def write_defect_clusters(path, accepted, graph_data):
    """Cluster mapped candidates by shared node, cell, or neighboring cell."""
    edge_cells = {}
    cell_indices = {}
    for cell in graph_data.get("unit_cells", []):
        cell_id = cell.get("id"); indices = tuple(cell.get("indices", []))
        if len(indices) == 3: cell_indices[cell_id] = indices
        for edge_id in cell.get("struts", []): edge_cells.setdefault(edge_id, set()).add(cell_id)
    cluster_graph = nx.Graph(); cluster_graph.add_nodes_from(item["candidate_id"] for item in accepted)
    relations = {item["candidate_id"]: {"shared_node":0,"shared_cell":0,"neighbor_cell":0} for item in accepted}
    for index, first in enumerate(accepted):
        for second in accepted[index+1:]:
            shared_node = bool(set(first["endpoints"]) & set(second["endpoints"]))
            cells_a, cells_b = edge_cells.get(first["edge_id"],set()), edge_cells.get(second["edge_id"],set())
            shared_cell = bool(cells_a & cells_b)
            neighbor_cell = any(max(abs(cell_indices[a][i]-cell_indices[b][i]) for i in range(3)) <= 1
                                for a in cells_a for b in cells_b if a in cell_indices and b in cell_indices)
            if shared_node or shared_cell or neighbor_cell:
                cluster_graph.add_edge(first["candidate_id"],second["candidate_id"])
                for item, key in ((shared_node,"shared_node"),(shared_cell,"shared_cell"),(neighbor_cell,"neighbor_cell")):
                    if item:
                        relations[first["candidate_id"]][key]+=1; relations[second["candidate_id"]][key]+=1
    component_lookup = {}
    for cluster_id, component in enumerate(sorted(nx.connected_components(cluster_graph), key=lambda x:min(x))):
        for candidate_id in component: component_lookup[candidate_id]=(cluster_id,len(component))
    rows = []
    for item in sorted(accepted,key=lambda x:x["candidate_id"]):
        cluster_id, size = component_lookup[item["candidate_id"]]
        rows.append({"candidate_id":item["candidate_id"],"classification":item["classification"],
                     "matched_edge_id":item["edge_id"],"cluster_id":cluster_id,"cluster_size":size,
                     **relations[item["candidate_id"]]})
    with path.open("w",newline="",encoding="utf-8") as handle:
        writer=csv.DictWriter(handle,fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    return {"path":path.name,"cluster_count":nx.number_connected_components(cluster_graph),
            "largest_cluster_size":max((len(c) for c in nx.connected_components(cluster_graph)),default=0),
            "criteria":["shared_consolidated_node","shared_unit_cell","neighboring_unit_cell_chebyshev_distance_le_1"]}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--graph", required=True, type=Path); parser.add_argument("--axis", choices=AXIS, required=True)
    parser.add_argument("--terminal-fraction", type=float, default=.05); parser.add_argument("--defect-candidates", type=Path)
    parser.add_argument("--candidate-edge-mapping", type=Path)
    parser.add_argument("--advanced-metrics", action="store_true")
    parser.add_argument("--merge-coincident-nodes", action="store_true"); parser.add_argument("--merge-tolerance", type=float, default=.0)
    parser.add_argument("--output-dir", required=True, type=Path); args = parser.parse_args()
    if not 0 < args.terminal_fraction <= .5: raise ValueError("--terminal-fraction must be in (0, 0.5]")
    if args.merge_tolerance < 0: raise ValueError("--merge-tolerance must be nonnegative")
    graph_data = json.loads(args.graph.read_text(encoding="utf-8")); node_records = graph_data.get("junctions", []); struts = graph_data.get("struts", [])
    positions, duplicate_ids, invalid_nodes = {}, [], []
    for item in node_records:
        node_id, position = item.get("id"), item.get("position")
        if node_id in positions: duplicate_ids.append(node_id); continue
        if not isinstance(position, list) or len(position) != 3 or not all(isinstance(v, (int,float)) and math.isfinite(v) for v in position): invalid_nodes.append(node_id); continue
        positions[node_id] = position
    coordinate_groups = {}
    for node_id, position in positions.items():
        key = tuple(round(value / args.merge_tolerance) if args.merge_tolerance else value for value in position)
        coordinate_groups.setdefault(key, []).append(node_id)
    raw_to_topology = {node_id: (members[0] if args.merge_coincident_nodes else node_id) for members in coordinate_groups.values() for node_id in members}
    graph, invalid_edges, self_loops, duplicate_edges = nx.Graph(), [], [], []
    graph.add_nodes_from(set(raw_to_topology.values()))
    for edge in struts:
        edge_id, first, second = edge.get("id"), edge.get("junction0"), edge.get("junction1")
        if first not in positions or second not in positions: invalid_edges.append({"strut_id": edge_id, "reason": "missing_endpoint"}); continue
        first, second = raw_to_topology[first], raw_to_topology[second]
        if first == second: self_loops.append(edge_id); continue
        if graph.has_edge(first, second): duplicate_edges.append(edge_id); continue
        graph.add_edge(first, second, strut_id=edge_id)
    components = sorted(nx.connected_components(graph), key=len, reverse=True)
    axis = AXIS[args.axis]; coords = [position[axis] for position in positions.values()]
    low, high = min(coords), max(coords); width = (high-low)*args.terminal_fraction
    lower = sorted({raw_to_topology[node] for node, position in positions.items() if position[axis] <= low+width})
    upper = sorted({raw_to_topology[node] for node, position in positions.items() if position[axis] >= high-width})
    reachable = bool(set(lower) and set(upper) and any(nx.has_path(graph, start, end) for start in lower for end in upper))
    bridges = list(nx.bridges(graph)); articulations = list(nx.articulation_points(graph)); degree_counts = Counter(dict(graph.degree()).values())
    args.output_dir.mkdir(parents=True, exist_ok=True)
    boundary_redundancy = None
    edge_screening = None
    if args.advanced_metrics:
        connectivity = boundary_edge_connectivity(graph, lower, upper)
        boundary_redundancy = {"boundary_set_edge_connectivity": connectivity,
                               "edge_disjoint_path_count": connectivity,
                               "equality_basis":"Menger's theorem for the unweighted graph"}
        edge_screening = write_edge_screening_metrics(args.output_dir/"edge_screening_metrics.csv",graph,positions,lower,upper)
    with (args.output_dir / "bridge_edges.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["junction0", "junction1", "strut_id"]); writer.writeheader()
        for first, second in bridges: writer.writerow({"junction0": first, "junction1": second, "strut_id": graph.edges[first,second].get("strut_id")})
    defects = None
    if args.defect_candidates:
        with args.defect_candidates.open(newline="", encoding="utf-8-sig") as handle: candidates = list(csv.DictReader(handle))
        defects = {"path": str(args.defect_candidates), "candidate_count": len(candidates), "classification_counts": dict(Counter(row.get("classification", "unknown") for row in candidates)), "mapping_status": "not established by this analyzer; no candidate edge removals were performed"}
    defect_mapping, defect_states, defect_clustering = None, None, None
    if args.candidate_edge_mapping:
        with args.candidate_edge_mapping.open(newline="", encoding="utf-8-sig") as handle:
            mapping_rows = list(csv.DictReader(handle))
        required_mapping_fields = {"candidate_id", "classification", "matched_edge_id", "mapping_status"}
        if not mapping_rows or not required_mapping_fields.issubset(mapping_rows[0]):
            raise ValueError("candidate-edge mapping CSV is empty or missing required fields")
        edge_by_id = {data["strut_id"]: (first, second) for first, second, data in graph.edges(data=True)}
        accepted, rejected = [], []
        for row in mapping_rows:
            try: edge_id = int(row["matched_edge_id"])
            except (TypeError, ValueError): edge_id = None
            if row["mapping_status"] != "geometry_validated_unique" or edge_id not in edge_by_id:
                rejected.append({"candidate_id": row.get("candidate_id"), "matched_edge_id": row.get("matched_edge_id"), "mapping_status": row.get("mapping_status")})
                continue
            accepted.append({"candidate_id": int(row["candidate_id"]), "classification": row["classification"], "edge_id": edge_id, "endpoints": edge_by_id[edge_id]})
        if len({item["candidate_id"] for item in accepted}) != len(accepted):
            raise ValueError("candidate-edge mapping contains duplicate accepted candidate IDs")
        if len({item["edge_id"] for item in accepted}) != len(accepted):
            raise ValueError("candidate-edge mapping contains duplicate accepted edge assignments")

        def state_metrics(removed, advanced=False):
            state = graph.copy(); state.remove_edges_from([edge_by_id[edge_id] for edge_id in removed])
            state_components = sorted(nx.connected_components(state), key=len, reverse=True)
            state_reachable = bool(set(lower) and set(upper) and any(nx.has_path(state, start, end) for start in lower for end in upper))
            result = {"removed_edge_count": len(removed), "component_count": len(state_components), "largest_component_nodes": len(state_components[0]) if state_components else 0, "lower_to_upper_path_exists": state_reachable, "bridge_edge_count": sum(1 for _ in nx.bridges(state)), "articulation_node_count": sum(1 for _ in nx.articulation_points(state))}
            if advanced:
                connectivity = boundary_edge_connectivity(state, lower, upper)
                result.update({"boundary_set_edge_connectivity":connectivity,"edge_disjoint_path_count":connectivity})
            return result

        individual_rows = []
        for item in accepted:
            metrics = state_metrics([item["edge_id"]])
            individual_rows.append({"candidate_id": item["candidate_id"], "classification": item["classification"], "matched_edge_id": item["edge_id"], **metrics, "component_count_change": metrics["component_count"]-len(components), "bridge_edge_count_change": metrics["bridge_edge_count"]-len(bridges), "articulation_node_count_change": metrics["articulation_node_count"]-len(articulations)})
        with (args.output_dir / "defect_topology_changes.csv").open("w", newline="", encoding="utf-8") as handle:
            fields = list(individual_rows[0]) if individual_rows else ["candidate_id"]
            writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader(); writer.writerows(individual_rows)
        missing_ids = [item["edge_id"] for item in accepted if item["classification"] == "missing"]
        all_ids = [item["edge_id"] for item in accepted]
        defect_mapping = {"path": str(args.candidate_edge_mapping), "accepted_count": len(accepted), "rejected_count": len(rejected), "rejected_rows": rejected, "acceptance_status": "complete" if not rejected else "partial", "accepted_mapping_status": "geometry_validated_unique"}
        defect_states = {"intact": state_metrics([],args.advanced_metrics), "all_validated_missing_removed": state_metrics(missing_ids,args.advanced_metrics), "all_validated_candidates_removed": state_metrics(all_ids,args.advanced_metrics), "individual_changes_csv": "defect_topology_changes.csv"}
        defect_clustering = write_defect_clusters(args.output_dir/"defect_clusters.csv",accepted,graph_data)
    coincident_group_count = sum(1 for members in coordinate_groups.values() if len(members) > 1)
    status = "complete" if not (duplicate_ids or invalid_nodes or invalid_edges or self_loops or duplicate_edges or (coincident_group_count and not args.merge_coincident_nodes)) else "provisional"
    output = {"schema_version": "1.0.0", "created_at": datetime.now(timezone.utc).isoformat(), "status": status,
              "source_graph": str(args.graph), "graph_validation": {"input_junction_count": len(node_records), "valid_raw_junction_count": len(positions), "topology_junction_count": graph.number_of_nodes(), "input_strut_count": len(struts), "valid_strut_count": graph.number_of_edges(), "duplicate_node_ids": duplicate_ids, "invalid_node_ids": invalid_nodes, "invalid_edges": invalid_edges, "self_loop_strut_ids": self_loops, "duplicate_edge_strut_ids": duplicate_edges, "coincident_coordinate_group_count": coincident_group_count, "coincident_node_merge": {"enabled": args.merge_coincident_nodes, "tolerance": args.merge_tolerance}},
              "components": {"count": len(components), "largest_component_nodes": len(components[0]) if components else 0, "component_sizes": [len(component) for component in components]},
              "degree_distribution": {str(degree): count for degree, count in sorted(degree_counts.items())},
              "boundary_terminals": {"axis": args.axis, "terminal_fraction": args.terminal_fraction, "lower_node_count": len(lower), "upper_node_count": len(upper), "lower_to_upper_path_exists": reachable},
              "vulnerability_indicators": {"bridge_edge_count": len(bridges), "articulation_node_count": len(articulations), "bridge_edges_csv": "bridge_edges.csv"},
              "boundary_redundancy": boundary_redundancy,
              "edge_screening_metrics": edge_screening,
              "defect_candidates": defects,
              "candidate_edge_mapping": defect_mapping,
              "defect_topology_states": defect_states,
              "defect_clustering": defect_clustering,
              "limitations": ["Metrics are graph properties, not physical force, stress, stiffness, capacity, or safety margin.", "Boundary terminal selection is a declared screening choice.", "Defect-specific removal analysis is blocked until candidate-to-graph-edge identity is validated."]}
    if defect_mapping and defect_mapping["acceptance_status"] == "complete":
        output["limitations"][-1] = "Defect-specific removals use geometry-validated spatial-marker mappings; they remain topology indicators rather than mechanical results."
    summary_path = args.output_dir / "topology_summary.json"; summary_path.write_text(json.dumps(output, indent=2)+"\n", encoding="utf-8")
    report = ["# Lattice topology analysis", "", f"- Status: `{status}`", f"- Components: {len(components)}", f"- Valid struts: {graph.number_of_edges():,}", f"- Lower-to-upper path on {args.axis}: `{reachable}`", f"- Bridge edges: {len(bridges):,}", f"- Articulation nodes: {len(articulations):,}", "", "## Limitations", ""] + [f"- {item}" for item in output["limitations"]]
    (args.output_dir / "topology_report.md").write_text("\n".join(report)+"\n", encoding="utf-8")
    print(json.dumps({"summary": str(summary_path), "status": status, "components": len(components), "bridges": len(bridges)}))
if __name__ == "__main__": main()
