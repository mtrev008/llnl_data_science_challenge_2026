import csv
import json
from pathlib import Path

import numpy as np


JSON_PATH = Path(
    r"C:\Users\andre\llnl_data_science_challenge_2026\data\missing_struts\registered_jsons"
    r"\210127_Brian_Tran_strut_lattices_0point5dash1 1 Slices.json"
)
OUT_DIR = Path(
    r"C:\Users\andre\llnl_data_science_challenge_2026\validation_outputs"
    r"\210127_brian_tran_0point5dash1_1_slices\spatial_intensity_test"
)
TIFF_SHAPE_ZYX = (761, 815, 837)


def stats(values):
    a = np.asarray(values, dtype=float)
    return {
        "minimum": float(np.min(a)),
        "p25": float(np.percentile(a, 25)),
        "median": float(np.median(a)),
        "mean": float(np.mean(a)),
        "p75": float(np.percentile(a, 75)),
        "maximum": float(np.max(a)),
        "standard_deviation": float(np.std(a)),
        "unique_count": int(np.unique(a).size),
    }


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    data = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    junctions = {int(j["id"]): np.asarray(j["position"], dtype=float) for j in data["junctions"]}
    struts = {int(s["id"]): (int(s["junction0"]), int(s["junction1"])) for s in data["struts"]}
    rows = []
    for cell in data["unit_cells"]:
        junction_ids = set()
        for strut_id in cell["struts"]:
            j0, j1 = struts[int(strut_id)]
            junction_ids.update((j0, j1))
        points = np.vstack([junctions[jid] for jid in sorted(junction_ids)])
        pmin = points.min(axis=0)
        pmax = points.max(axis=0)
        span = pmax - pmin
        # Conditional raster-covering definition: integer index box floor(min)..ceil(max), inclusive.
        cover_min = np.floor(pmin).astype(int)
        cover_max = np.ceil(pmax).astype(int)
        cover_count = cover_max - cover_min + 1
        idx = [int(v) for v in cell["indices"]]
        rows.append({
            "cell_id": int(cell["id"]),
            "cell_i": idx[0], "cell_j": idx[1], "cell_k": idx[2],
            "strut_reference_count": len(cell["struts"]),
            "unique_endpoint_junction_count": len(junction_ids),
            "x_min": pmin[0], "x_max": pmax[0], "x_span": span[0],
            "y_min": pmin[1], "y_max": pmax[1], "y_span": span[1],
            "z_min": pmin[2], "z_max": pmax[2], "z_span": span[2],
            "cover_x_count": int(cover_count[0]),
            "cover_y_count": int(cover_count[1]),
            "cover_z_count": int(cover_count[2]),
            "cover_box_voxel_count": int(np.prod(cover_count, dtype=np.int64)),
            "coordinate_box_volume": float(np.prod(span)),
        })

    csv_path = OUT_DIR / "unit_cell_registered_coordinate_spans.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    summary = {
        "input_json": str(JSON_PATH),
        "tiff_shape_zyx": list(TIFF_SHAPE_ZYX),
        "json_definition": {
            "unit_cell_count": len(data["unit_cells"]),
            "index_ranges_ijk": {
                "i": [min(r["cell_i"] for r in rows), max(r["cell_i"] for r in rows)],
                "j": [min(r["cell_j"] for r in rows), max(r["cell_j"] for r in rows)],
                "k": [min(r["cell_k"] for r in rows), max(r["cell_k"] for r in rows)],
            },
            "fields": ["id", "indices", "struts"],
            "meaning_used": "A JSON unit-cell record and the unique junction endpoints of its referenced struts.",
        },
        "registered_coordinate_span_statistics": {
            axis: stats([r[f"{axis}_span"] for r in rows]) for axis in "xyz"
        },
        "conditional_integer_cover_counts": {
            axis: stats([r[f"cover_{axis}_count"] for r in rows]) for axis in "xyz"
        },
        "conditional_cover_box_voxel_count": stats([r["cover_box_voxel_count"] for r in rows]),
        "coordinate_box_volume": stats([r["coordinate_box_volume"] for r in rows]),
        "whole_lattice_coordinate_bounds_xyz": {
            "minimum": [
                min(r["x_min"] for r in rows),
                min(r["y_min"] for r in rows),
                min(r["z_min"] for r in rows),
            ],
            "maximum": [
                max(r["x_max"] for r in rows),
                max(r["y_max"] for r in rows),
                max(r["z_max"] for r in rows),
            ],
        },
        "naive_full_tiff_dimension_divided_by_9_xyz": [
            TIFF_SHAPE_ZYX[2] / 9,
            TIFF_SHAPE_ZYX[1] / 9,
            TIFF_SHAPE_ZYX[0] / 9,
        ],
        "interpretation_limits": [
            "The JSON has no voxel spacing, coordinate units, origin, axis declaration, transform matrix, or explicit per-cell voxel mask.",
            "The README asserts that this JSON is aligned with the same-named TIFF, but does not document the transform or declare that one JSON coordinate unit equals one voxel index.",
            "Integer cover counts are conditional on treating registered XYZ coordinates as TIFF X,Y,Z voxel indices.",
            "Cover-box counts include void/background and may overlap neighboring cells; they are not material voxel counts.",
            "Actual foreground voxels per cell require a segmentation mask plus an explicit boundary/ownership convention.",
        ],
    }
    json_path = OUT_DIR / "unit_cell_voxel_span_summary.json"
    json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    s = summary
    lines = [
        "# Unit-cell voxel-span assessment",
        "",
        f"- JSON unit cells: {s['json_definition']['unit_cell_count']} (indices 0–8 on i, j, and k)",
        f"- TIFF shape ZYX: {TIFF_SHAPE_ZYX}",
        "- Unit-cell geometry: bounding box of unique junction endpoints from each cell's referenced struts",
        "",
        "## Registered-coordinate spans",
        "",
    ]
    for axis in "xyz":
        a = s["registered_coordinate_span_statistics"][axis]
        lines.append(
            f"- {axis.upper()}: min {a['minimum']:.6f}, median {a['median']:.6f}, "
            f"max {a['maximum']:.6f}; mean {a['mean']:.6f}"
        )
    lines.extend([
        "",
        "## Conditional integer covering boxes",
        "",
        "These figures apply only if registered JSON XYZ units are interpreted as TIFF XYZ voxel indices.",
    ])
    for axis in "xyz":
        a = s["conditional_integer_cover_counts"][axis]
        lines.append(
            f"- {axis.upper()} covering count: min {a['minimum']:.0f}, "
            f"median {a['median']:.0f}, max {a['maximum']:.0f}"
        )
    v = s["conditional_cover_box_voxel_count"]
    lines.extend([
        f"- Bounding-box count: min {v['minimum']:.0f}, median {v['median']:.0f}, max {v['maximum']:.0f}",
        "",
        "These are box voxels, including void, and are not actual lattice-material voxel counts.",
        "",
        "## Identifiability",
        "",
        "The exact number of material/foreground voxels belonging to a unit cell is not determined by the TIFF and JSON alone. A segmentation mask and an explicit convention for assigning shared struts and boundary voxels to cells are required.",
    ])
    (OUT_DIR / "unit_cell_voxel_span_report.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
