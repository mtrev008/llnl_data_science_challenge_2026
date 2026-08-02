#!/usr/bin/env python
"""Validate lattice coordinates and define provisional geometric terminal sets."""
from __future__ import annotations

import argparse
import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

AXIS_INDEX = {"x": 0, "y": 1, "z": 2}


def parse_fraction_list(values: Iterable[float]) -> list[float]:
    """Validate, deduplicate, and sort terminal fractions."""
    fractions = sorted(set(float(value) for value in values))
    if not fractions or any(not 0.0 < value <= 0.5 for value in fractions):
        raise ValueError("terminal fractions must be in (0, 0.5]")
    return fractions


def load_graph(path: Path) -> tuple[dict[int, tuple[float, float, float]], list[dict], dict]:
    """Load the registered graph and return validated XYZ junction positions."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    junction_records = payload.get("junctions")
    strut_records = payload.get("struts")
    if not isinstance(junction_records, list) or not isinstance(strut_records, list):
        raise ValueError("graph JSON must contain list-valued 'junctions' and 'struts'")

    positions: dict[int, tuple[float, float, float]] = {}
    duplicate_node_ids: list[int] = []
    invalid_nodes: list[dict] = []
    for record_index, record in enumerate(junction_records):
        node_id = record.get("id")
        position = record.get("position")
        if not isinstance(node_id, int):
            invalid_nodes.append({"record_index": record_index, "node_id": node_id, "reason": "invalid_id"})
            continue
        if node_id in positions:
            duplicate_node_ids.append(node_id)
            continue
        if (
            not isinstance(position, list)
            or len(position) != 3
            or not all(isinstance(value, (int, float)) and math.isfinite(value) for value in position)
        ):
            invalid_nodes.append({"record_index": record_index, "node_id": node_id, "reason": "invalid_position"})
            continue
        positions[node_id] = tuple(float(value) for value in position)

    duplicate_edge_ids: list[int] = []
    invalid_edges: list[dict] = []
    self_loop_edge_ids: list[int] = []
    seen_edge_ids: set[int] = set()
    valid_edges: list[dict] = []
    for record_index, edge in enumerate(strut_records):
        edge_id = edge.get("id")
        first, second = edge.get("junction0"), edge.get("junction1")
        if not isinstance(edge_id, int):
            invalid_edges.append({"record_index": record_index, "edge_id": edge_id, "reason": "invalid_id"})
            continue
        if edge_id in seen_edge_ids:
            duplicate_edge_ids.append(edge_id)
            continue
        seen_edge_ids.add(edge_id)
        if first not in positions or second not in positions:
            invalid_edges.append({"record_index": record_index, "edge_id": edge_id, "reason": "missing_endpoint"})
            continue
        if first == second:
            self_loop_edge_ids.append(edge_id)
            continue
        valid_edges.append(edge)

    diagnostics = {
        "input_junction_count": len(junction_records),
        "valid_junction_count": len(positions),
        "input_strut_count": len(strut_records),
        "valid_strut_count": len(valid_edges),
        "duplicate_node_ids": duplicate_node_ids,
        "duplicate_edge_ids": duplicate_edge_ids,
        "invalid_nodes": invalid_nodes,
        "invalid_edges": invalid_edges,
        "self_loop_edge_ids": self_loop_edge_ids,
    }
    return positions, valid_edges, diagnostics


def coordinate_groups(
    positions: dict[int, tuple[float, float, float]],
) -> dict[tuple[float, float, float], list[int]]:
    """Group junction records that have exactly coincident XYZ coordinates."""
    groups: dict[tuple[float, float, float], list[int]] = {}
    for node_id, position in positions.items():
        groups.setdefault(position, []).append(node_id)
    return groups


def coordinate_extents(
    positions: dict[int, tuple[float, float, float]],
) -> dict[str, dict[str, float]]:
    """Return minimum, maximum, and span for each graph coordinate component."""
    if not positions:
        raise ValueError("graph contains no valid junction coordinates")
    return {
        axis: {
            "minimum": min(point[index] for point in positions.values()),
            "maximum": max(point[index] for point in positions.values()),
            "span": max(point[index] for point in positions.values())
            - min(point[index] for point in positions.values()),
        }
        for axis, index in AXIS_INDEX.items()
    }


def check_ct_bounds(
    positions: dict[int, tuple[float, float, float]],
    ct_shape_zyx: tuple[int, int, int] | None,
) -> dict:
    """Check graph XYZ positions against a CT array whose storage order is ZYX."""
    if ct_shape_zyx is None:
        return {
            "available": False,
            "status": "not_evaluated",
            "reason": "no CT shape was supplied",
        }
    if any(size <= 0 for size in ct_shape_zyx):
        raise ValueError("CT shape values must be positive")

    shape_xyz = (ct_shape_zyx[2], ct_shape_zyx[1], ct_shape_zyx[0])
    inside_ids = [
        node_id
        for node_id, point in positions.items()
        if all(0.0 <= point[index] < shape_xyz[index] for index in range(3))
    ]
    fraction = len(inside_ids) / len(positions) if positions else 0.0
    return {
        "available": True,
        "status": "numerically_plausible" if fraction == 1.0 else "bounds_mismatch",
        "ct_array_order": "zyx",
        "ct_shape_zyx": list(ct_shape_zyx),
        "ct_shape_xyz": list(shape_xyz),
        "inside_node_count": len(inside_ids),
        "outside_node_count": len(positions) - len(inside_ids),
        "inside_fraction": fraction,
        "interpretation": (
            "A bounds check supports numerical compatibility only; it does not prove "
            "axis handedness, physical orientation, or registration accuracy."
        ),
    }


def select_boundary_nodes(
    positions: dict[int, tuple[float, float, float]],
    axis: str,
    fraction: float,
) -> dict:
    """Select lower and upper terminal records by a fraction of graph extent."""
    if axis not in AXIS_INDEX:
        raise ValueError(f"unsupported axis: {axis}")
    if not 0.0 < fraction <= 0.5:
        raise ValueError("terminal fraction must be in (0, 0.5]")
    index = AXIS_INDEX[axis]
    values = [point[index] for point in positions.values()]
    low, high = min(values), max(values)
    width = (high - low) * fraction
    lower_limit, upper_limit = low + width, high - width
    lower = sorted(node_id for node_id, point in positions.items() if point[index] <= lower_limit)
    upper = sorted(node_id for node_id, point in positions.items() if point[index] >= upper_limit)
    overlap = sorted(set(lower).intersection(upper))
    return {
        "axis": axis,
        "terminal_fraction": fraction,
        "axis_minimum": low,
        "axis_maximum": high,
        "terminal_width": width,
        "lower_limit": lower_limit,
        "upper_limit": upper_limit,
        "lower_node_ids": lower,
        "upper_node_ids": upper,
        "lower_node_count": len(lower),
        "upper_node_count": len(upper),
        "overlap_node_ids": overlap,
    }


def unique_location_count(
    node_ids: list[int],
    positions: dict[int, tuple[float, float, float]],
) -> int:
    """Count unique spatial junctions represented by a raw node-ID set."""
    return len({positions[node_id] for node_id in node_ids})


def physical_extents(
    extents: dict[str, dict[str, float]],
    voxel_size_xyz_um: tuple[float, float, float] | None,
) -> dict:
    """Convert graph-coordinate extents to physical dimensions when calibrated."""
    if voxel_size_xyz_um is None:
        return {
            "available": False,
            "status": "not_evaluated",
            "reason": "no XYZ voxel size was supplied",
        }
    if any(not math.isfinite(size) or size <= 0 for size in voxel_size_xyz_um):
        raise ValueError("voxel sizes must be finite and positive")
    return {
        "available": True,
        "voxel_size_xyz_um": list(voxel_size_xyz_um),
        "span_um": {
            axis: extents[axis]["span"] * voxel_size_xyz_um[index]
            for axis, index in AXIS_INDEX.items()
        },
        "span_mm": {
            axis: extents[axis]["span"] * voxel_size_xyz_um[index] / 1000.0
            for axis, index in AXIS_INDEX.items()
        },
        "calibration_status": "provided_not_independently_verified",
    }


def write_boundary_nodes(
    path: Path,
    selected: dict,
    positions: dict[int, tuple[float, float, float]],
) -> None:
    """Write one row per lower/upper raw junction record."""
    lower, upper = set(selected["lower_node_ids"]), set(selected["upper_node_ids"])
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["boundary", "junction_id", "x", "y", "z"])
        writer.writeheader()
        for boundary, node_ids in (("lower", lower), ("upper", upper)):
            for node_id in sorted(node_ids):
                x, y, z = positions[node_id]
                writer.writerow({"boundary": boundary, "junction_id": node_id, "x": x, "y": y, "z": z})


def write_sensitivity(
    path: Path,
    sensitivity: list[dict],
) -> None:
    """Write compact boundary-fraction sensitivity results."""
    fields = [
        "axis",
        "terminal_fraction",
        "terminal_width",
        "lower_limit",
        "upper_limit",
        "lower_raw_node_count",
        "upper_raw_node_count",
        "lower_unique_location_count",
        "upper_unique_location_count",
        "overlap_node_count",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(sensitivity)


def build_report(summary: dict) -> str:
    """Render a concise human-readable report."""
    selected = summary["selected_boundary"]
    bounds = summary["ct_bounds_check"]
    physical = summary["physical_calibration"]
    lines = [
        "# Coordinate and boundary definition",
        "",
        f"- Status: `{summary['status']}`",
        f"- Source graph: `{summary['source_graph']}`",
        "- Canonical graph position order: `[x, y, z]` (provisional interpretation)",
        f"- Valid junction records: {summary['graph_validation']['valid_junction_count']:,}",
        f"- Unique exact coordinate locations: {summary['coordinate_groups']['unique_location_count']:,}",
        f"- Selected screening axis: `{selected['axis']}`",
        f"- Selected terminal fraction: {selected['terminal_fraction']:.6g}",
        f"- Lower terminal records: {selected['lower_node_count']:,}",
        f"- Upper terminal records: {selected['upper_node_count']:,}",
        f"- Lower unique terminal locations: {selected['lower_unique_location_count']:,}",
        f"- Upper unique terminal locations: {selected['upper_unique_location_count']:,}",
        f"- CT bounds check: `{bounds['status']}`",
    ]
    if physical["available"]:
        spans = physical["span_mm"]
        lines.append(
            f"- Calibrated graph span: x={spans['x']:.6f} mm, "
            f"y={spans['y']:.6f} mm, z={spans['z']:.6f} mm"
        )
    lines.extend(
        [
            "",
            "## Interpretation gate",
            "",
            "- The graph JSON supports a reproducible coordinate convention and geometric terminal sets.",
            "- The CT bounds check establishes numerical plausibility, not a validated registration transform.",
            "- The selected terminals are graph-extrema screening regions, not confirmed platens, grips, or supports.",
            "- The physical application load axis and coordinate handedness remain unknown.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--graph", required=True, type=Path)
    parser.add_argument("--axis", choices=AXIS_INDEX, default="z")
    parser.add_argument("--terminal-fractions", nargs="+", type=float, default=[0.01, 0.025, 0.05, 0.075, 0.1])
    parser.add_argument("--selected-terminal-fraction", type=float, default=0.05)
    parser.add_argument("--ct-shape-zyx", nargs=3, type=int, metavar=("Z", "Y", "X"))
    parser.add_argument("--voxel-size-xyz-um", nargs=3, type=float, metavar=("SX", "SY", "SZ"))
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()

    fractions = parse_fraction_list([*args.terminal_fractions, args.selected_terminal_fraction])
    positions, edges, graph_diagnostics = load_graph(args.graph)
    if graph_diagnostics["duplicate_node_ids"] or graph_diagnostics["invalid_nodes"]:
        raise ValueError("invalid or duplicate graph junction records prevent coordinate definition")
    if graph_diagnostics["duplicate_edge_ids"] or graph_diagnostics["invalid_edges"]:
        raise ValueError("invalid or duplicate graph strut records prevent graph validation")

    groups = coordinate_groups(positions)
    extents = coordinate_extents(positions)
    bounds = check_ct_bounds(positions, tuple(args.ct_shape_zyx) if args.ct_shape_zyx else None)
    physical = physical_extents(
        extents,
        tuple(args.voxel_size_xyz_um) if args.voxel_size_xyz_um else None,
    )

    detailed_sensitivity = [
        select_boundary_nodes(positions, args.axis, fraction) for fraction in fractions
    ]
    sensitivity_rows = [
        {
            "axis": item["axis"],
            "terminal_fraction": item["terminal_fraction"],
            "terminal_width": item["terminal_width"],
            "lower_limit": item["lower_limit"],
            "upper_limit": item["upper_limit"],
            "lower_raw_node_count": item["lower_node_count"],
            "upper_raw_node_count": item["upper_node_count"],
            "lower_unique_location_count": unique_location_count(item["lower_node_ids"], positions),
            "upper_unique_location_count": unique_location_count(item["upper_node_ids"], positions),
            "overlap_node_count": len(item["overlap_node_ids"]),
        }
        for item in detailed_sensitivity
    ]
    selected = next(
        item
        for item in detailed_sensitivity
        if math.isclose(item["terminal_fraction"], args.selected_terminal_fraction)
    )
    selected["lower_unique_location_count"] = unique_location_count(selected["lower_node_ids"], positions)
    selected["upper_unique_location_count"] = unique_location_count(selected["upper_node_ids"], positions)

    status = "provisional_pass"
    if bounds["available"] and bounds["status"] == "bounds_mismatch":
        status = "failed_bounds_check"
    summary = {
        "schema_version": "1.0.0",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "source_graph": str(args.graph),
        "coordinate_definition": {
            "graph_position_order": "xyz",
            "graph_position_order_status": "inferred_from_schema_and_numerical_bounds",
            "ct_array_order": "zyx" if args.ct_shape_zyx else None,
            "ct_array_order_status": "provided_to_script" if args.ct_shape_zyx else "not_evaluated",
            "graph_to_ct_index_mapping": "graph [x,y,z] corresponds to CT index [z,y,x]",
            "mapping_status": "provisional",
            "handedness": "unknown",
            "origin_definition": "unknown",
            "application_load_axis": "unknown",
        },
        "graph_validation": graph_diagnostics,
        "coordinate_groups": {
            "unique_location_count": len(groups),
            "coincident_group_count": sum(len(node_ids) > 1 for node_ids in groups.values()),
            "maximum_records_per_location": max(map(len, groups.values())),
            "consolidation_performed": False,
        },
        "coordinate_extents_graph_units": extents,
        "ct_bounds_check": bounds,
        "physical_calibration": physical,
        "boundary_definition_status": "provisional_geometric_screening",
        "selected_boundary": selected,
        "boundary_sensitivity": sensitivity_rows,
        "limitations": [
            "No authoritative graph-to-CT registration transform was supplied.",
            "A numerical CT bounds check does not prove coordinate handedness or physical orientation.",
            "The selected graph-axis extrema are not confirmed physical attachment or loading regions.",
            "No physical application load axis is assigned.",
            "Coincident graph records are counted by unique location but are not consolidated by this script.",
        ],
    }

    args.output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = args.output_dir / "coordinate_boundary_definition.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    write_boundary_nodes(args.output_dir / "boundary_nodes.csv", selected, positions)
    write_sensitivity(args.output_dir / "boundary_sensitivity.csv", sensitivity_rows)
    (args.output_dir / "coordinate_boundary_report.md").write_text(
        build_report(summary), encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "status": status,
                "summary": str(summary_path),
                "valid_junctions": len(positions),
                "valid_struts": len(edges),
                "lower_terminal_records": selected["lower_node_count"],
                "upper_terminal_records": selected["upper_node_count"],
                "lower_unique_terminal_locations": selected["lower_unique_location_count"],
                "upper_unique_terminal_locations": selected["upper_unique_location_count"],
            }
        )
    )


if __name__ == "__main__":
    main()
