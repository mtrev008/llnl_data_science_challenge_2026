#!/usr/bin/env python
"""Write a provenance-preserving geometric summary for a lattice graph."""
from __future__ import annotations
import argparse, csv, json, math
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, median

def percentile(values, q):
    if not values: return None
    values = sorted(values); position = (len(values) - 1) * q; lo, hi = math.floor(position), math.ceil(position)
    return values[lo] if lo == hi else values[lo] + (values[hi] - values[lo]) * (position - lo)

def summary(values):
    return {"count": len(values), "min": min(values) if values else None, "p10": percentile(values, .1), "median": median(values) if values else None, "mean": mean(values) if values else None, "p90": percentile(values, .9), "max": max(values) if values else None}

def measurement_summary(path):
    with path.open(newline="", encoding="utf-8-sig") as handle: rows = list(csv.DictReader(handle))
    metrics = {}
    for field in ["thickness_min_um", "thickness_mean_um", "thickness_median_um", "path_length_um", "straight_length_um", "tortuosity", "gap_um"]:
        vals = []
        for row in rows:
            try:
                value = float(row.get(field, ""))
                if math.isfinite(value): vals.append(value)
            except (TypeError, ValueError): pass
        if vals: metrics[field] = summary(vals)
    return {"path": str(path), "row_count": len(rows), "metric_distributions": metrics, "identity_mapping_status": "not established; values are not attached to graph struts"}

def mask_density(path, voxel_size_mm):
    import numpy as np, tifffile
    foreground_count = 0; z_min = y_min = x_min = None; z_max = y_max = x_max = None
    with tifffile.TiffFile(path) as tif:
        for z, page in enumerate(tif.pages):
            foreground = page.asarray() > 0
            count = int(np.count_nonzero(foreground))
            if not count: continue
            foreground_count += count
            occupied_y = np.flatnonzero(np.any(foreground, axis=1))
            occupied_x = np.flatnonzero(np.any(foreground, axis=0))
            z_min = z if z_min is None else min(z_min, z); z_max = z if z_max is None else max(z_max, z)
            local_y_min, local_y_max = int(occupied_y[0]), int(occupied_y[-1])
            local_x_min, local_x_max = int(occupied_x[0]), int(occupied_x[-1])
            y_min = local_y_min if y_min is None else min(y_min, local_y_min)
            y_max = local_y_max if y_max is None else max(y_max, local_y_max)
            x_min = local_x_min if x_min is None else min(x_min, local_x_min)
            x_max = local_x_max if x_max is None else max(x_max, local_x_max)
    if not foreground_count: return {"path": str(path), "status": "empty_mask"}
    dimensions = (z_max-z_min+1, y_max-y_min+1, x_max-x_min+1); voxel_volume = voxel_size_mm ** 3
    solid_volume = foreground_count * voxel_volume; envelope_volume = int(np.prod(dimensions)) * voxel_volume
    return {"path": str(path), "status": "computed", "foreground_voxels": foreground_count, "bounding_box_min_zyx": [z_min, y_min, x_min], "bounding_box_max_zyx": [z_max, y_max, x_max], "bounding_box_dimensions_voxels_zyx": list(dimensions), "solid_volume_mm3": solid_volume, "envelope_volume_mm3": envelope_volume, "relative_density_bounding_box": solid_volume / envelope_volume, "limitation": "Segmentation-derived global estimate; threshold, mask provenance, and envelope definition control the value."}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--graph", required=True, type=Path); parser.add_argument("--voxel-size-mm", required=True, type=float)
    parser.add_argument("--measurements", type=Path); parser.add_argument("--mask", type=Path); parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--load-axis", nargs=3, type=float, metavar=("X", "Y", "Z")); args = parser.parse_args()
    if args.voxel_size_mm <= 0: raise ValueError("--voxel-size-mm must be positive")
    graph = json.loads(args.graph.read_text(encoding="utf-8")); nodes = {item["id"]: item["position"] for item in graph.get("junctions", [])}
    norm = math.sqrt(sum(x*x for x in args.load_axis)) if args.load_axis else None
    if args.load_axis and norm == 0: raise ValueError("--load-axis must be nonzero")
    axis = [x/norm for x in args.load_axis] if args.load_axis else None; rows, invalid, lengths, directions = [], [], [], [[], [], []]
    for member in graph.get("struts", []):
        member_id, start, end = member.get("id"), member.get("junction0"), member.get("junction1")
        if start not in nodes or end not in nodes: invalid.append({"strut_id": member_id, "reason": "missing_endpoint"}); continue
        vector = [float(nodes[end][i])-float(nodes[start][i]) for i in range(3)]; length_voxels = math.sqrt(sum(v*v for v in vector))
        if not math.isfinite(length_voxels) or length_voxels <= 0: invalid.append({"strut_id": member_id, "reason": "nonpositive_or_nonfinite_length"}); continue
        cosine = [abs(v/length_voxels) for v in vector]
        row = {"strut_id": member_id, "junction0": start, "junction1": end, "length_voxels": length_voxels, "length_mm": length_voxels*args.voxel_size_mm, "abs_direction_cosine_x": cosine[0], "abs_direction_cosine_y": cosine[1], "abs_direction_cosine_z": cosine[2]}
        if axis: row["abs_direction_cosine_load_axis"] = abs(sum(vector[i]/length_voxels*axis[i] for i in range(3)))
        rows.append(row); lengths.append(row["length_mm"])
        for i in range(3): directions[i].append(cosine[i])
    args.output_dir.mkdir(parents=True, exist_ok=True); csv_path = args.output_dir / "strut_geometry.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]) if rows else ["strut_id"]); writer.writeheader(); writer.writerows(rows)
    report = {"schema_version": "1.0.0", "created_at": datetime.now(timezone.utc).isoformat(), "status": "complete" if not invalid else "provisional", "sources": {"graph": str(args.graph), "voxel_size_mm": args.voxel_size_mm, "measurement_table": str(args.measurements) if args.measurements else None, "mask": str(args.mask) if args.mask else None}, "graph_validation": {"junction_count": len(nodes), "input_strut_count": len(graph.get("struts", [])), "valid_strut_count": len(rows), "invalid_struts": invalid}, "strut_geometry": {"length_mm": summary(lengths), "abs_direction_cosine_x": summary(directions[0]), "abs_direction_cosine_y": summary(directions[1]), "abs_direction_cosine_z": summary(directions[2])}, "load_axis": {"value": args.load_axis, "status": "user_supplied" if axis else "not_supplied"}, "limitations": ["Graph geometry provides centerline lengths and orientations, not physical stress or stiffness.", "Graph thickness fields were not interpreted as physical diameters by this analyzer.", "Circular section properties, slenderness, and nominal comparison require validated member-diameter and mapping evidence."]}
    if args.measurements: report["measurement_table_summary"] = measurement_summary(args.measurements)
    if args.mask: report["mask_relative_density"] = mask_density(args.mask, args.voxel_size_mm)
    json_path = args.output_dir / "as_built_geometry_summary.json"; json_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    length = report["strut_geometry"]["length_mm"]
    markdown = ["# As-built geometric analysis", "", f"- Status: `{report['status']}`", f"- Valid graph struts: {len(rows):,} / {len(graph.get('struts', [])):,}", f"- Length median: {length['median']:.6f} mm", f"- Length range: {length['min']:.6f} to {length['max']:.6f} mm", "", "## Limitations", ""] + [f"- {item}" for item in report["limitations"]]
    (args.output_dir / "as_built_geometry_report.md").write_text("\n".join(markdown)+"\n", encoding="utf-8")
    print(json.dumps({"summary": str(json_path), "strut_csv": str(csv_path), "status": report["status"]}))
if __name__ == "__main__": main()
