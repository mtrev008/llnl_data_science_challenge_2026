import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import tifffile


TIFF_PATH = Path(
    r"C:\Users\andre\llnl_data_science_challenge_2026\data\missing_struts\tif_stacks"
    r"\210127_Brian_Tran_strut_lattices_0point5dash1 1 Slices.tif"
)
OUT = Path(
    r"C:\Users\andre\llnl_data_science_challenge_2026\validation_outputs"
    r"\210127_brian_tran_0point5dash1_1_slices\spatial_intensity_test"
)
Z = 345


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    with tifffile.TiffFile(TIFF_PATH) as tif:
        a = tif.pages[Z].asarray()

    levels = [
        ("minimum", 0, "cyan", "o", (0.12, 0.18)),
        ("P01", 1, "deepskyblue", "s", (0.12, 0.72)),
        ("P25", 25, "lime", "^", (0.34, 0.27)),
        ("median", 50, "gold", "D", (0.50, 0.72)),
        ("P75", 75, "orange", "v", (0.67, 0.28)),
        ("P99", 99, "red", "X", (0.82, 0.70)),
        ("maximum", 100, "magenta", "*", (0.88, 0.18)),
    ]
    values = np.percentile(a, [item[1] for item in levels], method="nearest").astype(int)
    points = []
    h, w = a.shape
    for (label, percentile, color, marker, anchor_fraction), value in zip(levels, values):
        coords = np.argwhere(a == value)
        anchor = np.array([anchor_fraction[0] * (h - 1), anchor_fraction[1] * (w - 1)])
        idx = int(np.argmin(np.sum((coords - anchor) ** 2, axis=1)))
        y, x = (int(v) for v in coords[idx])
        points.append({
            "label": label,
            "percentile": percentile,
            "intensity": int(value),
            "z": Z,
            "y": y,
            "x": x,
            "json_x": x,
            "json_y": y,
            "json_z": Z,
            "color": color,
            "marker": marker,
        })

    stats = {
        "z": Z,
        "shape_yx": [h, w],
        "count": int(a.size),
        "minimum": int(a.min()),
        "maximum": int(a.max()),
        "mean": float(np.mean(a)),
        "median": float(np.median(a)),
        "standard_deviation": float(np.std(a)),
        "p01": int(np.percentile(a, 1, method="nearest")),
        "p25": int(np.percentile(a, 25, method="nearest")),
        "p75": int(np.percentile(a, 75, method="nearest")),
        "p99": int(np.percentile(a, 99, method="nearest")),
    }

    fig, ax = plt.subplots(figsize=(13, 10), constrained_layout=True)
    im = ax.imshow(a, cmap="gray", vmin=stats["p01"], vmax=stats["p99"])
    text_offsets = [
        (15, 12), (15, -58), (15, 12), (15, -58), (15, 12), (-185, -58), (-210, 12)
    ]
    for p, offset in zip(points, text_offsets):
        face = "none" if p["marker"] in ("o", "s", "^", "v", "D") else p["color"]
        ax.scatter(
            p["x"], p["y"], s=170, marker=p["marker"], facecolors=face,
            edgecolors=p["color"], c=None if face == "none" else p["color"],
            linewidths=2.3, label=f"{p['label']} = {p['intensity']:,}"
        )
        ax.annotate(
            f"{p['label']} {p['intensity']:,}\n"
            f"ZYX=({Z},{p['y']},{p['x']})\n"
            f"XYZ=({p['x']},{p['y']},{Z})",
            (p["x"], p["y"]), xytext=offset, textcoords="offset points",
            fontsize=8.5, color=p["color"],
            bbox=dict(facecolor="black", alpha=0.78, edgecolor=p["color"]),
            arrowprops=dict(arrowstyle="->", color=p["color"], linewidth=1.4),
        )
    ax.set_title(
        f"Z slice 345: deterministic intensity quantile locations\n"
        f"mean={stats['mean']:.1f}, median={stats['median']:.0f}, "
        f"SD={stats['standard_deviation']:.1f}, range={stats['minimum']:,}–{stats['maximum']:,}"
    )
    ax.set_xlabel("X voxel index")
    ax.set_ylabel("Y voxel index")
    ax.legend(loc="upper right", fontsize=8, framealpha=0.92, ncol=2)
    cbar = fig.colorbar(im, ax=ax, shrink=0.82)
    cbar.set_label("Stored uint16 intensity (digital number); display clipped to slice P01–P99")
    png = OUT / "annotated_slice_z345.png"
    fig.savefig(png, dpi=190)
    plt.close(fig)

    csv_path = OUT / "slice_z345_representative_points.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "label", "percentile", "intensity", "z", "y", "x",
            "json_x", "json_y", "json_z"
        ])
        writer.writeheader()
        for p in points:
            writer.writerow({k: p[k] for k in writer.fieldnames})

    result = {
        "input_tiff": str(TIFF_PATH),
        "slice_statistics": stats,
        "selection_method": (
            "Nearest-rank slice percentiles at 0, 1, 25, 50, 75, 99, and 100 percent. "
            "For each exact percentile intensity, select the matching voxel nearest a fixed, "
            "predeclared spatial anchor to distribute annotations deterministically."
        ),
        "points": [{k: v for k, v in p.items() if k not in ("color", "marker")} for p in points],
        "display": "Grayscale display limits are slice P01 to P99; stored point values are unchanged.",
        "limitations": [
            "Intensity quantiles are not material classes.",
            "Appearance supports image-structure interpretation but not material identity or physical calibration.",
        ],
        "artifacts": {
            "annotated_png": str(png),
            "points_csv": str(csv_path),
        },
    }
    (OUT / "slice_z345_summary.json").write_text(json.dumps(result, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
