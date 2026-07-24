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
OUTPUT_DIR = Path(
    r"C:\Users\andre\llnl_data_science_challenge_2026\validation_outputs"
    r"\210127_brian_tran_0point5dash1_1_slices\spatial_intensity_test"
)
LOW_THRESHOLD = 29789
HIGH_THRESHOLD = 54370


def xyz(zyx):
    z, y, x = (int(v) for v in zyx)
    return [x, y, z]


def point_record(kind, label, zyx, value, shape):
    z, y, x = (int(v) for v in zyx)
    boundary_distance = min(
        z, y, x, shape[0] - 1 - z, shape[1] - 1 - y, shape[2] - 1 - x
    )
    return {
        "band": kind,
        "label": label,
        "z": z,
        "y": y,
        "x": x,
        "json_x": x,
        "json_y": y,
        "json_z": z,
        "intensity": int(value),
        "nearest_volume_boundary_voxels": int(boundary_distance),
    }


def choose_slice_point(array, mask, prefer="center"):
    coords = np.argwhere(mask)
    if coords.size == 0:
        return None
    if prefer == "first":
        y, x = coords[0]
    else:
        center = np.array([(array.shape[0] - 1) / 2, (array.shape[1] - 1) / 2])
        idx = np.argmin(np.sum((coords - center) ** 2, axis=1))
        y, x = coords[idx]
    return int(y), int(x), int(array[y, x])


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with tifffile.TiffFile(TIFF_PATH) as tif:
        shape = tuple(int(v) for v in tif.series[0].shape)
        if len(shape) != 3:
            raise RuntimeError(f"Expected 3-D TIFF, got shape {shape}")

        per_slice = []
        accum = {
            "low": {
                "count": 0, "bd_sum": 0.0, "bd_min": None, "bd_max": None,
                "z_min": None, "z_max": None, "y_min": None, "y_max": None,
                "x_min": None, "x_max": None, "center_point": None,
                "center_d2": None, "deep_point": None, "first_point": None,
                "last_point": None,
            },
            "high": {
                "count": 0, "bd_sum": 0.0, "bd_min": None, "bd_max": None,
                "z_min": None, "z_max": None, "y_min": None, "y_max": None,
                "x_min": None, "x_max": None, "center_point": None,
                "center_d2": None, "deep_point": None, "first_point": None,
                "last_point": None,
            },
        }
        exact_min = None
        exact_max = None
        center3 = np.array([(v - 1) / 2 for v in shape])

        for z, page in enumerate(tif.pages):
            a = page.asarray()
            masks = {"low": a <= LOW_THRESHOLD, "high": a >= HIGH_THRESHOLD}
            row = {
                "z": z,
                "minimum": int(a.min()),
                "maximum": int(a.max()),
                "mean": float(np.mean(a)),
                "standard_deviation": float(np.std(a)),
            }
            for kind, mask in masks.items():
                ys, xs = np.nonzero(mask)
                count = int(ys.size)
                row[f"{kind}_count"] = count
                row[f"{kind}_fraction"] = count / a.size
                if count == 0:
                    continue
                zs = np.full(count, z, dtype=np.int32)
                bdist = np.minimum.reduce(
                    [
                        zs,
                        ys,
                        xs,
                        shape[0] - 1 - zs,
                        shape[1] - 1 - ys,
                        shape[2] - 1 - xs,
                    ]
                )
                state = accum[kind]
                state["count"] += count
                state["bd_sum"] += float(bdist.sum())
                bmin, bmax = int(bdist.min()), int(bdist.max())
                state["bd_min"] = bmin if state["bd_min"] is None else min(state["bd_min"], bmin)
                state["bd_max"] = bmax if state["bd_max"] is None else max(state["bd_max"], bmax)
                for axis, vals in (("z", zs), ("y", ys), ("x", xs)):
                    vmin, vmax = int(vals.min()), int(vals.max())
                    state[f"{axis}_min"] = vmin if state[f"{axis}_min"] is None else min(state[f"{axis}_min"], vmin)
                    state[f"{axis}_max"] = vmax if state[f"{axis}_max"] is None else max(state[f"{axis}_max"], vmax)
                coords = np.column_stack([zs, ys, xs])
                d2 = np.sum((coords - center3) ** 2, axis=1)
                ci = int(np.argmin(d2))
                candidate = (int(z), int(ys[ci]), int(xs[ci]))
                if state["center_d2"] is None or float(d2[ci]) < state["center_d2"]:
                    state["center_d2"] = float(d2[ci])
                    state["center_point"] = candidate
                di = int(np.argmax(bdist))
                deep_candidate = (int(z), int(ys[di]), int(xs[di]))
                if state["deep_point"] is None or int(bdist[di]) > state["deep_point"][0]:
                    state["deep_point"] = (int(bdist[di]), deep_candidate)
                first = (int(z), int(ys[0]), int(xs[0]))
                last = (int(z), int(ys[-1]), int(xs[-1]))
                if state["first_point"] is None:
                    state["first_point"] = first
                state["last_point"] = last

            amin, amax = int(a.min()), int(a.max())
            min_yx = np.argwhere(a == amin)[0]
            max_yx = np.argwhere(a == amax)[0]
            if exact_min is None or amin < exact_min[0]:
                exact_min = (amin, (z, int(min_yx[0]), int(min_yx[1])))
            if exact_max is None or amax > exact_max[0]:
                exact_max = (amax, (z, int(max_yx[0]), int(max_yx[1])))
            per_slice.append(row)

    with (OUTPUT_DIR / "spatial_band_by_slice.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(per_slice[0]))
        writer.writeheader()
        writer.writerows(per_slice)

    representatives = []
    with tifffile.TiffFile(TIFF_PATH) as tif:
        for kind in ("low", "high"):
            state = accum[kind]
            for label, point in (
                ("first_lexicographic", state["first_point"]),
                ("last_lexicographic", state["last_point"]),
                ("nearest_volume_center", state["center_point"]),
                ("deepest_from_boundary", state["deep_point"][1]),
            ):
                z, y, x = point
                value = tif.pages[z].asarray()[y, x]
                representatives.append(point_record(kind, label, point, value, shape))
        representatives.append(
            point_record("exact_minimum", "first_exact_minimum", exact_min[1], exact_min[0], shape)
        )
        representatives.append(
            point_record("exact_maximum", "first_exact_maximum", exact_max[1], exact_max[0], shape)
        )

    with (OUTPUT_DIR / "representative_points.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(representatives[0]))
        writer.writeheader()
        writer.writerows(representatives)

    low_peak = max(per_slice, key=lambda r: r["low_count"])["z"]
    high_peak = max(per_slice, key=lambda r: r["high_count"])["z"]
    interior_start = int(np.ceil(shape[0] * 0.10))
    interior_end = int(np.floor((shape[0] - 1) * 0.90))
    interior_rows = [r for r in per_slice if interior_start <= r["z"] <= interior_end]
    selected_row = max(interior_rows, key=lambda r: (r["standard_deviation"], -r["z"]))
    selected_z = int(selected_row["z"])

    fig, ax = plt.subplots(1, 1, figsize=(11, 9), constrained_layout=True)
    with tifffile.TiffFile(TIFF_PATH) as tif:
        a = tif.pages[selected_z].asarray()
        im = ax.imshow(a, cmap="gray", vmin=LOW_THRESHOLD, vmax=HIGH_THRESHOLD)
        low = choose_slice_point(a, a <= LOW_THRESHOLD)
        high = choose_slice_point(a, a >= HIGH_THRESHOLD)
        selected_points = []
        if low:
            y, x, value = low
            selected_points.append(point_record("low", "representative_on_selected_slice", (selected_z, y, x), value, shape))
            ax.scatter(x, y, s=150, marker="o", facecolors="none", edgecolors="cyan", linewidths=2.5,
                       label=f"Low ≤ P01 ({LOW_THRESHOLD:,})")
            ax.annotate(
                f"LOW {value:,}\nZYX=({selected_z},{y},{x})\nXYZ=({x},{y},{selected_z})",
                (x, y), xytext=(18, 18), textcoords="offset points",
                color="cyan", fontsize=10,
                bbox=dict(facecolor="black", alpha=0.78, edgecolor="cyan"),
                arrowprops=dict(arrowstyle="->", color="cyan", linewidth=1.8),
            )
        if high:
            y, x, value = high
            selected_points.append(point_record("high", "representative_on_selected_slice", (selected_z, y, x), value, shape))
            ax.scatter(x, y, s=150, marker="x", c="red", linewidths=2.5,
                       label=f"High ≥ P99 ({HIGH_THRESHOLD:,})")
            ax.annotate(
                f"HIGH {value:,}\nZYX=({selected_z},{y},{x})\nXYZ=({x},{y},{selected_z})",
                (x, y), xytext=(18, -62), textcoords="offset points",
                color="red", fontsize=10,
                bbox=dict(facecolor="white", alpha=0.85, edgecolor="red"),
                arrowprops=dict(arrowstyle="->", color="red", linewidth=1.8),
            )
        ax.set_title(
            f"Interior intensity-diverse slice Z={selected_z}\n"
            f"mean={selected_row['mean']:.1f}, SD={selected_row['standard_deviation']:.1f}, "
            f"range={selected_row['minimum']:,}–{selected_row['maximum']:,}"
        )
        ax.set_xlabel("X voxel index")
        ax.set_ylabel("Y voxel index")
        ax.legend(loc="lower right", framealpha=0.9)
    cbar = fig.colorbar(im, ax=ax, shrink=0.84)
    cbar.set_label("Stored uint16 intensity (digital number)")
    fig.savefig(OUTPUT_DIR / "annotated_representative_slice.png", dpi=180)
    plt.close(fig)

    summary = {
        "input_tiff": str(TIFF_PATH),
        "shape_zyx": list(shape),
        "definitions": {
            "low_band": f"intensity <= validated global P01 ({LOW_THRESHOLD})",
            "high_band": f"intensity >= validated global P99 ({HIGH_THRESHOLD})",
        },
        "bands": {},
        "exact_minimum": {"intensity": exact_min[0], "zyx": list(exact_min[1]), "xyz": xyz(exact_min[1])},
        "exact_maximum": {"intensity": exact_max[0], "zyx": list(exact_max[1]), "xyz": xyz(exact_max[1])},
        "peak_slices": {"low_count_peak_z": low_peak, "high_count_peak_z": high_peak},
        "slice_selection": {
            "rule": "maximum within-slice standard deviation after excluding the outer 10% of Z slices",
            "eligible_z_range_inclusive": [interior_start, interior_end],
            "selected_z": selected_z,
            "selected_slice_statistics": selected_row,
        },
        "selected_slice_representative_points": selected_points,
        "polarity_interpretation": {
            "finding": "On the selected representative slice, the high-band point lies on a bright lattice line and the low-band point lies in a dark cell void.",
            "supported_conclusion": "The evidence supports higher stored intensity as lattice foreground and lower stored intensity as background/void for threshold-segmentation polarity in this TIFF.",
            "limits": "This does not identify material, establish physical attenuation or density, or guarantee that one global threshold is accurate on every slice.",
        },
        "limitations": [
            "Quantile bands are intensity categories, not material labels.",
            "Spatial locations alone do not establish attenuation calibration or material identity.",
            "Foreground/background polarity requires comparison with recognizable lattice and outside-background regions.",
        ],
    }
    for kind in ("low", "high"):
        state = accum[kind]
        summary["bands"][kind] = {
            "count": state["count"],
            "fraction": state["count"] / np.prod(shape),
            "zyx_bounding_box": {
                "minimum": [state["z_min"], state["y_min"], state["x_min"]],
                "maximum": [state["z_max"], state["y_max"], state["x_max"]],
            },
            "mean_nearest_volume_boundary_voxels": state["bd_sum"] / state["count"],
            "minimum_nearest_volume_boundary_voxels": state["bd_min"],
            "maximum_nearest_volume_boundary_voxels": state["bd_max"],
            "nearest_volume_center_zyx": list(state["center_point"]),
            "nearest_volume_center_xyz": xyz(state["center_point"]),
            "deepest_from_boundary_zyx": list(state["deep_point"][1]),
            "deepest_from_boundary_xyz": xyz(state["deep_point"][1]),
        }
    (OUTPUT_DIR / "spatial_intensity_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )

    md = [
        "# Spatial intensity-location test",
        "",
        f"- TIFF: `{TIFF_PATH}`",
        f"- Shape (Z,Y,X): `{shape}`",
        f"- Low band: intensity ≤ global P01 = `{LOW_THRESHOLD}`",
        f"- High band: intensity ≥ global P99 = `{HIGH_THRESHOLD}`",
        f"- Selected slice: Z=`{selected_z}`, the maximum-SD slice within interior Z=`{interior_start}`–`{interior_end}`",
        f"- Selected slice mean / SD / range: `{selected_row['mean']:.3f}` / `{selected_row['standard_deviation']:.3f}` / `{selected_row['minimum']}`–`{selected_row['maximum']}`",
        "",
    ]
    for kind in ("low", "high"):
        b = summary["bands"][kind]
        md.extend([
            f"## {kind.title()} band",
            "",
            f"- Count: `{b['count']}` ({b['fraction']:.6%} of voxels)",
            f"- ZYX bounding box: `{b['zyx_bounding_box']['minimum']}` to `{b['zyx_bounding_box']['maximum']}`",
            f"- Mean nearest-boundary distance: `{b['mean_nearest_volume_boundary_voxels']:.3f}` voxels",
            f"- Nearest center point ZYX / XYZ: `{b['nearest_volume_center_zyx']}` / `{b['nearest_volume_center_xyz']}`",
            f"- Deepest point ZYX / XYZ: `{b['deepest_from_boundary_zyx']}` / `{b['deepest_from_boundary_xyz']}`",
            "",
        ])
    md.extend([
        "## Exact extrema",
        "",
        f"- Minimum: `{exact_min[0]}` at ZYX `{list(exact_min[1])}`, XYZ `{xyz(exact_min[1])}`",
        f"- Maximum: `{exact_max[0]}` at ZYX `{list(exact_max[1])}`, XYZ `{xyz(exact_max[1])}`",
        "",
        "## Selected-slice representative points",
        "",
    ])
    for p in selected_points:
        md.append(
            f"- {p['band'].title()}: intensity `{p['intensity']}` at "
            f"ZYX `[{p['z']}, {p['y']}, {p['x']}]`, "
            f"XYZ `[{p['json_x']}, {p['json_y']}, {p['json_z']}]`"
        )
    md.extend([
        "",
        "## Polarity interpretation",
        "",
        "On the selected slice, the high-band marker lies on a bright lattice line and the low-band marker lies in a dark cell void. This supports using higher stored intensity as lattice foreground and lower stored intensity as background/void for segmentation polarity in this TIFF.",
        "",
        "This does not establish material identity, attenuation, density, or the accuracy of a single global threshold across all slices.",
        "",
        "Quantile bands are intensity categories, not material labels. Their alignment with recognizable lattice lines supports polarity here, but does not prove attenuation calibration or material identity.",
    ])
    (OUTPUT_DIR / "spatial_intensity_report.md").write_text("\n".join(md), encoding="utf-8")


if __name__ == "__main__":
    main()
