from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib-cache")

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D


PROJECT_ROOT = Path(__file__).resolve().parents[3]
ANALYSIS_DIR = PROJECT_ROOT / "data" / "missing_struts" / "analysis"
PER_STRUT_DEFECTS = ANALYSIS_DIR / "per_strut_defects.json"
OUTPUT_MARKDOWN = ANALYSIS_DIR / "defect_struts_visualization.md"
VIEW_ELEVATION = 24
VIEW_AZIMUTH = 38


@dataclass(frozen=True)
class DefectStyle:
    subtype: str
    color: str
    alpha: float
    linewidth: float


STYLES = {
    "missing": DefectStyle("missing", "red", 0.92, 2.0),
    "broken": DefectStyle("broken", "orange", 0.88, 1.8),
    "thin": DefectStyle("thin", "blue", 0.42, 1.0),
}

OVERVIEW_OUTPUT = ANALYSIS_DIR / "defect_struts_overview.png"
DBSCAN_CLUSTER_OUTPUT = ANALYSIS_DIR / "dbscan_clusters_3d.png"


def load_records() -> dict[str, list[np.ndarray]]:
    records = json.loads(PER_STRUT_DEFECTS.read_text(encoding="utf-8"))
    grouped: dict[str, list[np.ndarray]] = {subtype: [] for subtype in STYLES}
    for record in records:
        subtype = record.get("weak_subtype")
        if record.get("classification") != "weak" or subtype not in STYLES:
            continue

        start_xyz = np.asarray(record.get("start_xyz"), dtype=float)
        end_xyz = np.asarray(record.get("end_xyz"), dtype=float)
        if start_xyz.shape != (3,) or end_xyz.shape != (3,):
            continue
        if not np.isfinite(start_xyz).all() or not np.isfinite(end_xyz).all():
            continue

        grouped[subtype].append(np.vstack([start_xyz, end_xyz]))
    return grouped


def compute_axis_limits(grouped: dict[str, list[np.ndarray]]) -> tuple[tuple[float, float], ...]:
    segments = [segment for segments in grouped.values() for segment in segments]
    if not segments:
        raise ValueError("No defect strut segments were found for visualization.")

    points = np.concatenate(segments, axis=0)
    mins = points.min(axis=0)
    maxs = points.max(axis=0)
    center = (mins + maxs) / 2.0
    max_range = float(np.max(maxs - mins))
    half_range = max(max_range / 2.0, 1.0)
    return tuple((float(c - half_range), float(c + half_range)) for c in center)


def configure_axes(ax: plt.Axes, axis_limits: tuple[tuple[float, float], ...]) -> None:
    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    ax.set_zlabel("Z")
    ax.set_xlim(*axis_limits[0])
    ax.set_ylim(*axis_limits[1])
    ax.set_zlim(*axis_limits[2])
    ax.view_init(elev=VIEW_ELEVATION, azim=VIEW_AZIMUTH)
    ax.grid(True, alpha=0.25)
    ax.set_box_aspect(tuple(limits[1] - limits[0] for limits in axis_limits))


def plot_segments(
    segments_by_subtype: dict[str, list[np.ndarray]],
    output_path: Path,
    title: str,
    axis_limits: tuple[tuple[float, float], ...],
) -> None:
    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection="3d")

    handles: list[Line2D] = []
    for subtype, segments in segments_by_subtype.items():
        style = STYLES[subtype]
        for segment in segments:
            ax.plot(
                segment[:, 0],
                segment[:, 1],
                segment[:, 2],
                color=style.color,
                alpha=style.alpha,
                linewidth=style.linewidth,
            )
        handles.append(Line2D([0], [0], color=style.color, linewidth=2.0, alpha=style.alpha, label=subtype))

    configure_axes(ax, axis_limits)
    ax.set_title(title)
    if handles:
        ax.legend(handles=handles, loc="upper right", frameon=True)

    fig.tight_layout()
    fig.savefig(output_path, dpi=220)
    plt.close(fig)


def plot_dbscan_clusters(records: list[dict], output_path: Path) -> None:
    """Render all registered struts, colored by their DBSCAN cluster ID."""
    grouped: dict[int, list[np.ndarray]] = {}
    for record in records:
        start = np.asarray(record.get("start_xyz"), dtype=float)
        end = np.asarray(record.get("end_xyz"), dtype=float)
        if start.shape != (3,) or end.shape != (3,) or not np.isfinite(np.r_[start, end]).all():
            continue
        grouped.setdefault(int(record["cluster_id"]), []).append(np.vstack([start, end]))
    if not grouped:
        raise ValueError("No DBSCAN cluster labels were found to render.")

    axis_limits = compute_axis_limits({str(key): value for key, value in grouped.items()})
    colors = plt.get_cmap("tab10")
    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection="3d")
    handles: list[Line2D] = []
    for index, (cluster_id, segments) in enumerate(sorted(grouped.items(), key=lambda item: len(item[1]), reverse=True)):
        color = "#6b7280" if cluster_id == -1 else colors(index % 10)
        for segment in segments:
            alpha = 0.18 if len(segments) > 100 else 0.95
            linewidth = 0.45 if len(segments) > 100 else 1.6
            ax.plot(segment[:, 0], segment[:, 1], segment[:, 2], color=color, alpha=alpha, linewidth=linewidth)
        handles.append(Line2D([0], [0], color=color, linewidth=2, label=f"cluster {cluster_id} ({len(segments):,} struts)"))
    configure_axes(ax, axis_limits)
    ax.set_title("Full-Stack DBSCAN Clustering (Euclidean Distance)")
    ax.legend(handles=handles, loc="upper right", frameon=True)
    fig.tight_layout()
    fig.savefig(output_path, dpi=220)
    plt.close(fig)


def write_summary(grouped: dict[str, list[np.ndarray]]) -> None:
    lines = [
        "# Defect Strut Visualization",
        "",
        f"- Data source: `{PER_STRUT_DEFECTS.relative_to(PROJECT_ROOT)}`",
        f"- View angle: elevation `{VIEW_ELEVATION}`, azimuth `{VIEW_AZIMUTH}`",
        "- Legend:",
        f"  - `missing`: `{STYLES['missing'].color}`",
        f"  - `broken`: `{STYLES['broken'].color}`",
        f"  - `thin`: `{STYLES['thin'].color}`",
        "",
        "## Subtype Counts",
        "",
    ]

    for subtype in ("missing", "broken", "thin"):
        lines.append(f"- `{subtype}`: {len(grouped[subtype])}")

    lines.extend(
        [
            "",
            "## Output Files",
            "",
            f"- Overview: `{OVERVIEW_OUTPUT.relative_to(PROJECT_ROOT)}`",
            f"- Summary: `{OUTPUT_MARKDOWN.relative_to(PROJECT_ROOT)}`",
            "",
            "Only `classification == \"weak\"` records with `weak_subtype` in `missing`, `broken`, or `thin` were rendered.",
        ]
    )
    OUTPUT_MARKDOWN.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    records = json.loads(PER_STRUT_DEFECTS.read_text(encoding="utf-8"))
    plot_dbscan_clusters(records, DBSCAN_CLUSTER_OUTPUT)
    grouped = load_records()
    if any(grouped.values()):
        axis_limits = compute_axis_limits(grouped)
        plot_segments(grouped, OVERVIEW_OUTPUT, "Weak Defect Struts Overview", axis_limits)
        write_summary(grouped)
    print("Visualization pipeline step")
    print(f"Rendered full-stack DBSCAN cluster overview under {ANALYSIS_DIR.relative_to(PROJECT_ROOT)}.")


if __name__ == "__main__":
    main()
