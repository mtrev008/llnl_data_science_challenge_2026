from __future__ import annotations

import argparse
import json
import math
import os
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib-cache")

import matplotlib.pyplot as plt
import numpy as np
import tifffile
from scipy import ndimage as ndi


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data" / "missing_struts"
ANALYSIS_DIR = DATA_DIR / "analysis"
OUTPUT_DIR = ANALYSIS_DIR / "fewshot_strut_classifier"

RAW_TIF = DATA_DIR / "tif_stacks" / "210127_Brian_Tran_strut_lattices_0point5dash1 1 Slices.tif"
SEGMENTATION_TIF = ANALYSIS_DIR / "segmented_mask.tif"
SKELETON_TIF = ANALYSIS_DIR / "skeleton.tif"
REGISTERED_FALLBACK_JSON = (
    DATA_DIR / "registered_jsons" / "210127_Brian_Tran_strut_lattices_0point5dash1 1 Slices.json"
)
REGISTERED_OUTPUT_JSON = ANALYSIS_DIR / "registration" / "registered_lattice.json"
OUTPUT_JSON = ANALYSIS_DIR / "per_strut_fewshot_defects.json"

CLASS_DEFINITIONS = {
    "missing": "The entire strut is absent between the two junctions.",
    "broken": "Part of the strut is absent, but not the full span.",
    "thin": "The strut is continuous but its diameter is below the dataset median diameter baseline.",
    "present": "None of the above.",
}


@dataclass(frozen=True)
class FewShotConfig:
    raw_tif: Path = RAW_TIF
    segmentation_tif: Path = SEGMENTATION_TIF
    skeleton_tif: Path = SKELETON_TIF
    registered_json: Path = REGISTERED_OUTPUT_JSON
    fallback_registered_json: Path = REGISTERED_FALLBACK_JSON
    output_dir: Path = OUTPUT_DIR
    output_json: Path = OUTPUT_JSON
    default_half_window: int = 4
    slice_padding: int = 3
    example_half_window: int = 3
    full_slice_center: int = 380
    full_slice_half_window: int = 3
    crop_margin: int = 18
    patch_radius: int = 2
    diameter_patch_radius: int = 7
    min_samples: int = 7
    max_samples: int = 9
    thin_ratio_threshold: float = 0.78
    broken_gap_fraction: float = 0.22
    max_rendered_targets: int = 128
    max_examples_per_class: int = 1


def parse_cli_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description="Classify registered lattice struts into present/missing/broken/thin using few-shot-style evidence bundles.",
    )
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    parser.add_argument("--output-json", type=Path, default=OUTPUT_JSON)
    parser.add_argument("--max-rendered-targets", type=int, default=128)
    parser.add_argument("--prepare-examples-only", action="store_true")
    return parser.parse_args(argv)


def _is_lfs_pointer(path: Path) -> bool:
    try:
        with path.open("rb") as handle:
            return handle.read(64).startswith(b"version https://git-lfs.github.com/spec/v1")
    except OSError:
        return False


def validate_input_file(path: Path, label: str) -> None:
    if not path.exists():
        raise FileNotFoundError(f"{label} does not exist: {path}")
    if path.is_dir():
        raise IsADirectoryError(f"{label} must be a file, not a directory: {path}")
    if _is_lfs_pointer(path):
        raise ValueError(f"{label} is a Git LFS pointer instead of real data: {path}")


def open_tif_volume(path: Path) -> np.ndarray:
    try:
        return tifffile.memmap(path)
    except Exception:
        return tifffile.imread(path)


def load_registered_lattice(config: FewShotConfig) -> tuple[dict[str, Any], Path]:
    path = config.registered_json if config.registered_json.exists() else config.fallback_registered_json
    validate_input_file(path, "Registered lattice JSON")
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    for key in ("junctions", "struts"):
        if key not in data or not isinstance(data[key], list):
            raise ValueError(f"Registered lattice JSON must contain a list field {key!r}")
    return data, path


def percentile_limits(volume: np.ndarray) -> tuple[float, float]:
    z_indices = np.linspace(0, volume.shape[0] - 1, num=min(25, volume.shape[0]), dtype=int)
    planes = []
    for z_index in z_indices:
        plane = np.asarray(volume[int(z_index)], dtype=np.float32)
        step_y = max(1, plane.shape[0] // 256)
        step_x = max(1, plane.shape[1] // 256)
        planes.append(plane[::step_y, ::step_x].ravel())
    values = np.concatenate(planes)
    low, high = np.percentile(values, [1.0, 99.7])
    if high <= low:
        high = low + 1.0
    return float(low), float(high)


def interpolate_points(start_xyz: np.ndarray, end_xyz: np.ndarray, count: int) -> np.ndarray:
    fractions = np.linspace(0.0, 1.0, num=count, dtype=np.float32)
    return start_xyz[None, :] + (end_xyz - start_xyz)[None, :] * fractions[:, None]


def clamp_bounds(lower: int, upper: int, limit: int) -> tuple[int, int]:
    lower = max(0, lower)
    upper = min(limit, upper)
    if upper <= lower:
        upper = min(limit, lower + 1)
    return lower, upper


def normalize_raw_patch(patch: np.ndarray, low: float, high: float) -> np.ndarray:
    patch = np.asarray(patch, dtype=np.float32)
    patch = np.clip((patch - low) / (high - low), 0.0, 1.0)
    return patch


def patch_mean(volume: np.ndarray, point_xyz: np.ndarray, radius: int) -> float:
    x, y, z = [int(round(float(value))) for value in point_xyz]
    z0, z1 = clamp_bounds(z - radius, z + radius + 1, volume.shape[0])
    y0, y1 = clamp_bounds(y - radius, y + radius + 1, volume.shape[1])
    x0, x1 = clamp_bounds(x - radius, x + radius + 1, volume.shape[2])
    patch = np.asarray(volume[z0:z1, y0:y1, x0:x1], dtype=np.float32)
    if patch.size == 0:
        return 0.0
    return float(np.mean(patch))


def patch_support(volume: np.ndarray, point_xyz: np.ndarray, radius: int) -> float:
    x, y, z = [int(round(float(value))) for value in point_xyz]
    z0, z1 = clamp_bounds(z - radius, z + radius + 1, volume.shape[0])
    y0, y1 = clamp_bounds(y - radius, y + radius + 1, volume.shape[1])
    x0, x1 = clamp_bounds(x - radius, x + radius + 1, volume.shape[2])
    patch = np.asarray(volume[z0:z1, y0:y1, x0:x1] > 0, dtype=np.float32)
    if patch.size == 0:
        return 0.0
    return float(np.max(patch))


def local_axial_diameter(mask_plane: np.ndarray, point_xy: tuple[float, float], radius: int) -> float:
    x, y = [int(round(value)) for value in point_xy]
    y0, y1 = clamp_bounds(y - radius, y + radius + 1, mask_plane.shape[0])
    x0, x1 = clamp_bounds(x - radius, x + radius + 1, mask_plane.shape[1])
    patch = np.asarray(mask_plane[y0:y1, x0:x1] > 0, dtype=bool)
    if patch.size == 0 or not np.any(patch):
        return 0.0
    local_y = y - y0
    local_x = x - x0
    if not (0 <= local_y < patch.shape[0] and 0 <= local_x < patch.shape[1]):
        return 0.0
    if not patch[local_y, local_x]:
        distance = ndi.distance_transform_edt(~patch)
        nearest = np.argwhere(distance == np.min(distance))
        if nearest.size == 0:
            return 0.0
        local_y, local_x = [int(value) for value in nearest[0]]
    labels, _ = ndi.label(patch)
    label = int(labels[local_y, local_x])
    if label == 0:
        return 0.0
    area = int(np.sum(labels == label))
    if area <= 0:
        return 0.0
    return float(2.0 * math.sqrt(area / math.pi))


def longest_false_run(flags: Iterable[bool]) -> int:
    longest = 0
    current = 0
    for flag in flags:
        if flag:
            current = 0
            continue
        current += 1
        longest = max(longest, current)
    return longest


def orientation_bucket(direction_xyz: np.ndarray | list[float]) -> str:
    direction_array = np.asarray(direction_xyz, dtype=np.float32)
    magnitude = float(np.linalg.norm(direction_array))
    if magnitude == 0.0:
        return "degenerate"
    unit = np.abs(direction_array / magnitude)
    active_axes = tuple(axis for axis, value in zip("xyz", unit) if value >= 0.45)
    if len(active_axes) == 3:
        return "xyz-diagonal"
    if len(active_axes) == 2:
        return f"{''.join(active_axes)}-diagonal"
    dominant = "xyz"[int(np.argmax(unit))]
    return f"{dominant}-dominant"


def json_relative(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def compute_slice_range(
    start_xyz: np.ndarray,
    end_xyz: np.ndarray,
    depth: int,
    default_half_window: int,
    slice_padding: int,
) -> tuple[int, int]:
    z_values = sorted([int(round(float(start_xyz[2]))), int(round(float(end_xyz[2])))])
    midpoint = int(round((z_values[0] + z_values[1]) / 2))
    half_window = max(default_half_window, int(math.ceil(abs(z_values[1] - z_values[0]) / 2.0)) + slice_padding)
    z0 = max(0, midpoint - half_window)
    z1 = min(depth - 1, midpoint + half_window)
    return z0, z1


def compute_continuous_example_slices(
    start_xyz: np.ndarray,
    end_xyz: np.ndarray,
    depth: int,
    half_window: int,
) -> list[int]:
    midpoint = int(round((float(start_xyz[2]) + float(end_xyz[2])) / 2.0))
    z0 = max(0, midpoint - half_window)
    z1 = min(depth - 1, midpoint + half_window)
    return list(range(z0, z1 + 1))


def relative_slice_name(slice_index: int, center_index: int) -> str:
    offset = int(slice_index) - int(center_index)
    if offset == 0:
        return "slice_000.png"
    sign = "+" if offset > 0 else "-"
    return f"slice_{sign}{abs(offset):03d}.png"


def compute_crop_box(
    start_xyz: np.ndarray,
    end_xyz: np.ndarray,
    width: int,
    height: int,
    margin: int,
) -> tuple[int, int, int, int]:
    x_values = [int(round(float(start_xyz[0]))), int(round(float(end_xyz[0])))]
    y_values = [int(round(float(start_xyz[1]))), int(round(float(end_xyz[1])))]
    x0, x1 = clamp_bounds(min(x_values) - margin, max(x_values) + margin + 1, width)
    y0, y1 = clamp_bounds(min(y_values) - margin, max(y_values) + margin + 1, height)
    return x0, x1, y0, y1


def render_slice_panel(
    destination: Path,
    slice_index: int,
    raw_plane: np.ndarray,
    segmentation_plane: np.ndarray,
    skeleton_plane: np.ndarray,
    low: float,
    high: float,
    start_xyz: np.ndarray,
    end_xyz: np.ndarray,
    crop_box: tuple[int, int, int, int],
    title_prefix: str,
) -> None:
    x0, x1, y0, y1 = crop_box
    raw_crop = normalize_raw_patch(raw_plane[y0:y1, x0:x1], low, high)
    seg_crop = np.asarray(segmentation_plane[y0:y1, x0:x1] > 0, dtype=np.float32)
    skel_crop = np.asarray(skeleton_plane[y0:y1, x0:x1] > 0, dtype=np.float32)

    figure, axes = plt.subplots(2, 2, figsize=(8, 8))
    panels = [
        (axes[0, 0], raw_crop, "Raw CT"),
        (axes[0, 1], seg_crop, "Segmentation"),
        (axes[1, 0], skel_crop, "Skeleton"),
        (axes[1, 1], raw_crop, "Overlay"),
    ]
    x_coords = [float(start_xyz[0] - x0), float(end_xyz[0] - x0)]
    y_coords = [float(start_xyz[1] - y0), float(end_xyz[1] - y0)]
    z0, z1 = float(start_xyz[2]), float(end_xyz[2])
    if abs(z1 - z0) <= 1e-6:
        fraction = 0.5
    else:
        fraction = min(1.0, max(0.0, (float(slice_index) - z0) / (z1 - z0)))
    target_xy = start_xyz[:2] + (end_xyz[:2] - start_xyz[:2]) * fraction
    highlight_x = float(target_xy[0] - x0)
    highlight_y = float(target_xy[1] - y0)

    for axis, image, title in panels:
        axis.imshow(image, cmap="gray", origin="lower")
        axis.plot(x_coords, y_coords, color="cyan", linewidth=1.4)
        axis.scatter([highlight_x], [highlight_y], c="yellow", s=18, edgecolors="black", linewidths=0.4)
        axis.set_title(title)
        axis.set_xticks([])
        axis.set_yticks([])
    figure.suptitle(f"{title_prefix} slice z={slice_index}")
    figure.tight_layout()
    figure.savefig(destination, dpi=140)
    plt.close(figure)


def render_raw_tif_crop(
    destination: Path,
    raw_plane: np.ndarray,
    low: float,
    high: float,
    crop_box: tuple[int, int, int, int],
) -> None:
    x0, x1, y0, y1 = crop_box
    raw_crop = normalize_raw_patch(raw_plane[y0:y1, x0:x1], low, high)
    plt.imsave(destination, raw_crop, cmap="gray", vmin=0.0, vmax=1.0, origin="lower")


def render_raw_tif_full_slice(
    destination: Path,
    raw_plane: np.ndarray,
    low: float,
    high: float,
) -> None:
    raw_image = normalize_raw_patch(raw_plane, low, high)
    plt.imsave(destination, raw_image, cmap="gray", vmin=0.0, vmax=1.0, origin="lower")


def strut_intersections_for_slice(registered_lattice: dict[str, Any], slice_index: int) -> list[dict[str, Any]]:
    junction_by_id = {int(junction["id"]): junction for junction in registered_lattice["junctions"]}
    intersections: list[dict[str, Any]] = []
    for strut in registered_lattice["struts"]:
        start = np.asarray(junction_by_id[int(strut["junction0"])]["position"], dtype=np.float32)
        end = np.asarray(junction_by_id[int(strut["junction1"])]["position"], dtype=np.float32)
        z0 = float(start[2])
        z1 = float(end[2])
        if min(z0, z1) > slice_index or max(z0, z1) < slice_index:
            continue
        fraction = 0.5 if abs(z1 - z0) <= 1e-6 else (float(slice_index) - z0) / (z1 - z0)
        point = start + (end - start) * float(fraction)
        intersections.append(
            {
                "strut_id": int(strut["id"]),
                "junction_ids": [int(strut["junction0"]), int(strut["junction1"])],
                "x": round(float(point[0]), 3),
                "y": round(float(point[1]), 3),
                "z": int(slice_index),
            }
        )
    return intersections


def lattice_row_centers(registered_lattice: dict[str, Any], gap_threshold: float = 5.0) -> list[float]:
    y_values = sorted(float(junction["position"][1]) for junction in registered_lattice["junctions"])
    if not y_values:
        return []
    rows: list[list[float]] = [[y_values[0]]]
    for y_value in y_values[1:]:
        if y_value - rows[-1][-1] > gap_threshold:
            rows.append([y_value])
        else:
            rows[-1].append(y_value)
    return [float(np.mean(row)) for row in reversed(rows)]


def build_row_label_slots(
    registered_lattice: dict[str, Any],
    slice_index: int,
    png_path: Path,
    row_centers: list[float],
) -> dict[str, Any]:
    row_items: list[list[dict[str, Any]]] = [[] for _ in row_centers]
    for item in strut_intersections_for_slice(registered_lattice, slice_index):
        if not row_centers:
            continue
        row_index = int(np.argmin([abs(float(item["y"]) - center) for center in row_centers]))
        row_items[row_index].append(item)

    numbered_rows = []
    for row_index, row in enumerate(row_items, start=1):
        ordered = sorted(row, key=lambda item: float(item["x"]))
        numbered_rows.append(
            {
                "row": row_index,
                "row_order": "top_to_bottom",
                "strut_order": "left_to_right",
                "row_center_y": round(float(row_centers[row_index - 1]), 3),
                "strut_count": len(ordered),
                "y_min": round(float(min(item["y"] for item in ordered)), 3) if ordered else None,
                "y_max": round(float(max(item["y"] for item in ordered)), 3) if ordered else None,
                "struts": [
                    {
                        "position_in_row": strut_index,
                        "strut_id": item["strut_id"],
                        "junction_ids": item["junction_ids"],
                        "x": item["x"],
                        "y": item["y"],
                        "label": None,
                        "notes": "",
                    }
                    for strut_index, item in enumerate(ordered, start=1)
                ],
            }
        )

    return {
        "slice_index": int(slice_index),
        "png": json_relative(png_path),
        "row_count": len(numbered_rows),
        "row_source": "registered_junction_y_centers",
        "rows": numbered_rows,
    }


def write_full_slice_review_sequence(
    raw_volume: np.ndarray,
    intensity_limits: tuple[float, float],
    registered_lattice: dict[str, Any],
    output_dir: Path,
    config: FewShotConfig,
) -> dict[str, Any]:
    sequence_dir = output_dir / "full_slice_review" / "sequence_001"
    sequence_dir.mkdir(parents=True, exist_ok=True)
    center_index = min(raw_volume.shape[0] - 1, max(0, int(config.full_slice_center)))
    z0 = max(0, center_index - int(config.full_slice_half_window))
    z1 = min(raw_volume.shape[0] - 1, center_index + int(config.full_slice_half_window))
    slice_indices = list(range(z0, z1 + 1))
    slice_paths: list[Path] = []
    for slice_index in slice_indices:
        path = sequence_dir / relative_slice_name(slice_index, center_index)
        render_raw_tif_full_slice(
            destination=path,
            raw_plane=np.asarray(raw_volume[slice_index]),
            low=intensity_limits[0],
            high=intensity_limits[1],
        )
        slice_paths.append(path)
    row_centers = lattice_row_centers(registered_lattice)
    contact_sheet = sequence_dir / "contact_sheet.png"
    render_contact_sheet(slice_paths, contact_sheet)
    metadata = {
        "sequence_id": "sequence_001",
        "image_type": "raw_tif_full_slice",
        "source_tif": json_relative(RAW_TIF),
        "slice_indices": [int(value) for value in slice_indices],
        "slice_pngs": [json_relative(path) for path in slice_paths],
        "contact_sheet_png": json_relative(contact_sheet),
        "human_verified": False,
        "row_labels": [
            build_row_label_slots(
                registered_lattice=registered_lattice,
                slice_index=int(slice_index),
                png_path=path,
                row_centers=row_centers,
            )
            for slice_index, path in zip(slice_indices, slice_paths)
        ],
        "review_instruction": "Fill each struts[].label with present, missing, broken, or thin. Rows are geometry-derived, ordered top-to-bottom; struts are ordered left-to-right within each row.",
        "class_definitions": CLASS_DEFINITIONS,
        "crop_box_xyxy": None,
    }
    metadata_path = sequence_dir / "metadata.json"
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    manifest = {
        "metadata": {
            "status": "pending_human_review",
            "review_type": "single_full_tif_slice_sequence",
            "source_tif": json_relative(RAW_TIF),
            "image_type": "raw_tif_full_slice",
            "review_required": "Fill row_labels in sequence_001/metadata.json with row-by-row labels for every strut you identify in each full slice.",
        },
        "sequences": [
            {
                "sequence_id": "sequence_001",
                "metadata_json": json_relative(metadata_path),
                "slice_indices": metadata["slice_indices"],
                "slice_pngs": metadata["slice_pngs"],
                "contact_sheet_png": metadata["contact_sheet_png"],
                "human_verified": False,
            }
        ],
    }
    manifest_path = output_dir / "slice_review_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    deprecated_example_manifest = {
        "metadata": {
            "status": "deprecated",
            "replacement": json_relative(manifest_path),
            "reason": "Human review now uses one uncropped raw TIFF slice sequence, not per-strut few-shot example candidates.",
        },
        "examples": [],
    }
    (output_dir / "example_manifest.json").write_text(json.dumps(deprecated_example_manifest, indent=2), encoding="utf-8")
    review_lines = [
        "# Full-Slice Review Queue",
        "",
        "This is one uncropped sequence taken directly from the raw TIFF stack.",
        "Label visible struts row by row in `full_slice_review/sequence_001/metadata.json`.",
        "",
        "## sequence_001",
        "",
        f"- Image type: `{metadata['image_type']}`",
        f"- Source TIFF: `{metadata['source_tif']}`",
        f"- Slice indices: `{metadata['slice_indices']}`",
        f"- Contact sheet: `{metadata['contact_sheet_png']}`",
        f"- Metadata: `{json_relative(metadata_path)}`",
        "- Row labels: `TODO`",
        "",
    ]
    (output_dir / "review_queue.md").write_text("\n".join(review_lines), encoding="utf-8")
    return manifest


def render_contact_sheet(slice_paths: list[Path], destination: Path) -> None:
    if not slice_paths:
        return
    images = [plt.imread(path) for path in slice_paths]
    columns = min(4, len(images))
    rows = int(math.ceil(len(images) / columns))
    figure, axes = plt.subplots(rows, columns, figsize=(columns * 3, rows * 3))
    if not isinstance(axes, np.ndarray):
        axes = np.asarray([axes])
    flat_axes = axes.ravel()
    for axis in flat_axes:
        axis.axis("off")
    for axis, image, path in zip(flat_axes, images, slice_paths):
        axis.imshow(image)
        axis.set_title(path.stem.rsplit("_", 1)[-1], fontsize=8)
        axis.axis("off")
    figure.tight_layout()
    figure.savefig(destination, dpi=140)
    plt.close(figure)


def build_prompt_contract(output_dir: Path) -> dict[str, Any]:
    payload = {
        "task": "Classify a single expected strut from a standardized PNG evidence bundle.",
        "class_definitions": CLASS_DEFINITIONS,
        "required_output_schema": {
            "label": "present|missing|broken|thin",
            "confidence": "float in [0, 1]",
            "rationale": "short string",
        },
        "backend_policy": {
            "primary": "multimodal few-shot classifier when available",
            "fallback": "local heuristic classifier over raw CT, segmentation, and skeleton evidence",
        },
    }
    path = output_dir / "prompt_contract.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def measure_strut_record(
    strut: dict[str, Any],
    junction_by_id: dict[int, dict[str, Any]],
    raw_volume: np.ndarray,
    segmentation_volume: np.ndarray,
    skeleton_volume: np.ndarray,
    intensity_limits: tuple[float, float],
    config: FewShotConfig,
) -> dict[str, Any]:
    start_xyz = np.asarray(junction_by_id[int(strut["junction0"])]["position"], dtype=np.float32)
    end_xyz = np.asarray(junction_by_id[int(strut["junction1"])]["position"], dtype=np.float32)
    direction = end_xyz - start_xyz
    length = float(np.linalg.norm(direction))
    sample_count = max(config.min_samples, min(config.max_samples, int(math.ceil(length / 18.0))))
    sample_points = interpolate_points(start_xyz, end_xyz, sample_count)
    low, high = intensity_limits

    raw_profile = [patch_mean(raw_volume, point, config.patch_radius) for point in sample_points]
    raw_profile_norm = [float(np.clip((value - low) / (high - low), 0.0, 1.0)) for value in raw_profile]
    segmentation_profile = [patch_support(segmentation_volume, point, config.patch_radius) for point in sample_points]
    skeleton_profile = [patch_support(skeleton_volume, point, 1) for point in sample_points]
    if len(sample_points) <= 3:
        diameter_sample_points = sample_points
    else:
        diameter_indices = np.linspace(1, len(sample_points) - 2, num=min(3, len(sample_points) - 2), dtype=int)
        diameter_sample_points = sample_points[diameter_indices]
    diameters = []
    for point in diameter_sample_points:
        z = min(segmentation_volume.shape[0] - 1, max(0, int(round(float(point[2])))))
        plane = np.asarray(segmentation_volume[z] > 0, dtype=bool)
        diameters.append(local_axial_diameter(plane, (float(point[0]), float(point[1])), config.diameter_patch_radius))
    present_diameters = [value for value in diameters if value > 0.0]
    support_flags = [value >= 0.5 for value in segmentation_profile]

    return {
        "strut_id": int(strut["id"]),
        "junction0": int(strut["junction0"]),
        "junction1": int(strut["junction1"]),
        "start_xyz": [round(float(value), 4) for value in start_xyz.tolist()],
        "end_xyz": [round(float(value), 4) for value in end_xyz.tolist()],
        "direction_xyz": [round(float(value), 5) for value in direction.tolist()],
        "length_voxels": round(length, 5),
        "orientation_bucket": orientation_bucket(direction),
        "sample_count": sample_count,
        "raw_profile": [round(float(value), 5) for value in raw_profile_norm],
        "segmentation_profile": [round(float(value), 5) for value in segmentation_profile],
        "skeleton_profile": [round(float(value), 5) for value in skeleton_profile],
        "diameter_profile": [round(float(value), 5) for value in diameters],
        "coverage_fraction": round(float(np.mean(segmentation_profile)), 5),
        "skeleton_fraction": round(float(np.mean(skeleton_profile)), 5),
        "raw_mean": round(float(np.mean(raw_profile_norm)), 5),
        "raw_min": round(float(np.min(raw_profile_norm)), 5),
        "median_nonzero_diameter": round(float(np.median(present_diameters)), 5) if present_diameters else 0.0,
        "longest_absent_run": int(longest_false_run(support_flags)),
        "absent_fraction": round(float(np.mean([not flag for flag in support_flags])), 5),
    }


def classify_record(record: dict[str, Any], diameter_baseline: float, config: FewShotConfig) -> dict[str, Any]:
    sample_count = max(1, int(record["sample_count"]))
    coverage = float(record["coverage_fraction"])
    longest_gap_fraction = float(record["longest_absent_run"]) / sample_count
    raw_mean = float(record["raw_mean"])
    skeleton_fraction = float(record["skeleton_fraction"])
    diameter = float(record["median_nonzero_diameter"])
    thin_ratio = diameter / diameter_baseline if diameter_baseline > 0 else 1.0

    if coverage <= 0.12 and raw_mean <= 0.28:
        label = "missing"
        confidence = min(0.99, 0.70 + (0.12 - coverage) * 1.2 + (0.28 - raw_mean) * 0.7)
        rationale = "Segmentation support is absent across nearly the full strut span and raw CT remains dark."
    elif longest_gap_fraction >= config.broken_gap_fraction and coverage < 0.82:
        label = "broken"
        confidence = min(0.97, 0.56 + longest_gap_fraction * 0.8 + (0.82 - coverage) * 0.35)
        rationale = "The strut has a contiguous missing segment but retains some material support outside that gap."
    elif coverage >= 0.7 and skeleton_fraction >= 0.15 and 0.0 < thin_ratio < config.thin_ratio_threshold:
        label = "thin"
        confidence = min(0.95, 0.55 + (config.thin_ratio_threshold - thin_ratio) * 1.4)
        rationale = "The strut is continuous, but its segmentation-derived axial diameter is below the dataset median baseline."
    else:
        label = "present"
        confidence = min(0.95, 0.52 + coverage * 0.25 + max(0.0, thin_ratio - config.thin_ratio_threshold) * 0.15)
        rationale = "The strut keeps material continuity without a full-span gap or sub-baseline thinness."

    classified = dict(record)
    classified.update(
        {
            "predicted_label": label,
            "confidence": round(float(max(0.0, min(1.0, confidence))), 5),
            "rationale": rationale,
            "diameter_baseline": round(float(diameter_baseline), 5),
            "diameter_ratio_to_baseline": round(float(thin_ratio), 5),
        }
    )
    return classified


def choose_example_records(
    records: list[dict[str, Any]],
    max_examples_per_class: int,
) -> dict[str, list[dict[str, Any]]]:
    selected: dict[str, list[dict[str, Any]]] = {}
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        grouped[str(record["predicted_label"])].append(record)
    for label in CLASS_DEFINITIONS:
        candidates = sorted(
            grouped.get(label, []),
            key=lambda item: (-float(item["confidence"]), item["orientation_bucket"], int(item["strut_id"])),
        )
        picked: list[dict[str, Any]] = []
        seen_orientations: set[str] = set()
        for candidate in candidates:
            orientation = str(candidate["orientation_bucket"])
            if orientation not in seen_orientations or len(seen_orientations) >= max_examples_per_class:
                picked.append(candidate)
                seen_orientations.add(orientation)
            if len(picked) >= max_examples_per_class:
                break
        if not picked and candidates:
            picked = [candidates[0]]
        selected[label] = picked
    return selected


def build_prompt_payload(example_records: list[dict[str, Any]], target_record: dict[str, Any]) -> dict[str, Any]:
    return {
        "class_definitions": CLASS_DEFINITIONS,
        "approved_examples": [
            {
                "example_id": record["example_id"],
                "label": record["label"],
                "proposed_label": record.get("proposed_label", record["label"]),
                "rationale": record["rationale"],
                "orientation_bucket": record["orientation_bucket"],
                "slice_indices": record["slice_indices"],
                "slice_pngs": record["slice_pngs"],
            }
            for record in example_records
        ],
        "target": {
            "strut_id": target_record["strut_id"],
            "orientation_bucket": target_record["orientation_bucket"],
            "slice_range": target_record["evidence_bundle"]["slice_range"],
            "evidence_bundle": target_record["evidence_bundle"],
        },
        "required_output_schema": {
            "label": "present|missing|broken|thin",
            "confidence": "float",
            "rationale": "short string",
        },
    }


def render_evidence_bundle(
    record: dict[str, Any],
    raw_volume: np.ndarray,
    segmentation_volume: np.ndarray,
    skeleton_volume: np.ndarray,
    intensity_limits: tuple[float, float],
    bundle_dir: Path,
    config: FewShotConfig,
    title_prefix: str,
) -> dict[str, Any]:
    bundle_dir.mkdir(parents=True, exist_ok=True)
    start_xyz = np.asarray(record["start_xyz"], dtype=np.float32)
    end_xyz = np.asarray(record["end_xyz"], dtype=np.float32)
    z0, z1 = compute_slice_range(
        start_xyz,
        end_xyz,
        depth=raw_volume.shape[0],
        default_half_window=config.default_half_window,
        slice_padding=config.slice_padding,
    )
    crop_box = compute_crop_box(
        start_xyz,
        end_xyz,
        width=raw_volume.shape[2],
        height=raw_volume.shape[1],
        margin=config.crop_margin,
    )
    slice_paths: list[Path] = []
    for slice_index in range(z0, z1 + 1):
        path = bundle_dir / f"slice_{slice_index:04d}.png"
        render_slice_panel(
            destination=path,
            slice_index=slice_index,
            raw_plane=np.asarray(raw_volume[slice_index]),
            segmentation_plane=np.asarray(segmentation_volume[slice_index]),
            skeleton_plane=np.asarray(skeleton_volume[slice_index]),
            low=intensity_limits[0],
            high=intensity_limits[1],
            start_xyz=start_xyz,
            end_xyz=end_xyz,
            crop_box=crop_box,
            title_prefix=title_prefix,
        )
        slice_paths.append(path)
    contact_sheet = bundle_dir / "contact_sheet.png"
    render_contact_sheet(slice_paths, contact_sheet)
    metadata = {
        "strut_id": int(record["strut_id"]),
        "orientation_bucket": record["orientation_bucket"],
        "slice_range": [int(z0), int(z1)],
        "crop_box_xyxy": [int(crop_box[0]), int(crop_box[2]), int(crop_box[1]), int(crop_box[3])],
        "slice_pngs": [json_relative(path) for path in slice_paths],
        "contact_sheet_png": json_relative(contact_sheet),
    }
    (bundle_dir / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return metadata


def render_example_review_bundle(
    record: dict[str, Any],
    example_id: str,
    raw_volume: np.ndarray,
    segmentation_volume: np.ndarray,
    skeleton_volume: np.ndarray,
    intensity_limits: tuple[float, float],
    bundle_dir: Path,
    config: FewShotConfig,
) -> dict[str, Any]:
    bundle_dir.mkdir(parents=True, exist_ok=True)
    start_xyz = np.asarray(record["start_xyz"], dtype=np.float32)
    end_xyz = np.asarray(record["end_xyz"], dtype=np.float32)
    slice_indices = compute_continuous_example_slices(
        start_xyz,
        end_xyz,
        depth=raw_volume.shape[0],
        half_window=config.example_half_window,
    )
    center_index = slice_indices[len(slice_indices) // 2]
    crop_box = compute_crop_box(
        start_xyz,
        end_xyz,
        width=raw_volume.shape[2],
        height=raw_volume.shape[1],
        margin=config.crop_margin,
    )
    slice_paths: list[Path] = []
    for slice_index in slice_indices:
        path = bundle_dir / relative_slice_name(slice_index, center_index)
        render_raw_tif_crop(
            destination=path,
            raw_plane=np.asarray(raw_volume[slice_index]),
            low=intensity_limits[0],
            high=intensity_limits[1],
            crop_box=crop_box,
        )
        slice_paths.append(path)
    contact_sheet = bundle_dir / "contact_sheet.png"
    render_contact_sheet(slice_paths, contact_sheet)
    metadata = {
        "example_id": example_id,
        "label": None,
        "proposed_label": record["predicted_label"],
        "definition": CLASS_DEFINITIONS[str(record["predicted_label"])],
        "slice_indices": [int(value) for value in slice_indices],
        "image_type": "raw_tif_crop",
        "source_tif": json_relative(RAW_TIF),
        "junction_ids": [int(record["junction0"]), int(record["junction1"])],
        "strut_id": int(record["strut_id"]),
        "orientation_bucket": record["orientation_bucket"],
        "evidence": [record["rationale"]],
        "slice_pngs": [json_relative(path) for path in slice_paths],
        "contact_sheet_png": json_relative(contact_sheet),
        "human_verified": False,
        "human_label": None,
        "human_evidence": [],
        "strut_labels_in_slice": [
            {
                "slice_index": int(slice_index),
                "png": json_relative(path),
                "labels": [],
            }
            for slice_index, path in zip(slice_indices, slice_paths)
        ],
        "review_instruction": "Label every visible strut in each cropped raw-TIFF slice. Include the target strut and any other struts visible in the crop.",
        "crop_box_xyxy": [int(crop_box[0]), int(crop_box[2]), int(crop_box[1]), int(crop_box[3])],
    }
    (bundle_dir / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return metadata


def write_example_manifest(
    example_sets: dict[str, list[dict[str, Any]]],
    output_dir: Path,
    registered_json_path: Path,
    diameter_baseline: float,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    examples: list[dict[str, Any]] = []
    for label in ("missing", "broken", "thin", "present"):
        for index, record in enumerate(example_sets.get(label, []), start=1):
            item = {
                "example_id": record["example_id"],
                "label": None,
                "proposed_label": label,
                "definition": CLASS_DEFINITIONS[label],
                "rationale": record["rationale"],
                "strut_id": int(record["strut_id"]),
                "junction0": int(record["junction0"]),
                "junction1": int(record["junction1"]),
                "orientation_bucket": record["orientation_bucket"],
                "start_xyz": record["start_xyz"],
                "end_xyz": record["end_xyz"],
                "slice_indices": record["evidence_bundle"]["slice_indices"],
                "image_type": record["evidence_bundle"]["image_type"],
                "source_tif": record["evidence_bundle"]["source_tif"],
                "slice_pngs": record["evidence_bundle"]["slice_pngs"],
                "contact_sheet_png": record["evidence_bundle"]["contact_sheet_png"],
                "metadata_json": json_relative(output_dir / "review_examples" / record["example_id"] / "metadata.json"),
                "human_verified": False,
                "human_label": None,
                "strut_labels_in_slice": record["evidence_bundle"]["strut_labels_in_slice"],
            }
            examples.append(item)
    manifest = {
        "metadata": {
            "registered_json": json_relative(registered_json_path),
            "diameter_baseline": round(float(diameter_baseline), 5),
            "class_definitions": CLASS_DEFINITIONS,
            "status": "pending_human_review",
            "image_type": "raw_tif_crop",
            "orientation_policy": "Candidate examples are selected from multiple orientation buckets where available.",
            "review_required": "Each cropped raw-TIFF slice must be checked by a human. Label every visible strut in every slice before using the example in a few-shot prompt.",
        },
        "examples": examples,
    }
    path = output_dir / "example_manifest.json"
    path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    review_lines = [
        "# Few-Shot Example Review Queue",
        "",
        "Each candidate below is a continuous slice sequence. Verify every PNG, assign the target strut label, and label any other visible struts in the crop before using it in a few-shot prompt.",
        "The PNGs are cropped raw slices from the source TIFF, not segmentation/skeleton panels.",
        "",
    ]
    for example in examples:
        review_lines.extend(
            [
                f"## {example['example_id']}",
                "",
                f"- Proposed label: `{example['proposed_label']}`",
                f"- Human label: `TODO`",
                f"- Strut ID: `{example['strut_id']}`",
                f"- Junction IDs: `{example['junction0']}`, `{example['junction1']}`",
                f"- Slice indices: `{example['slice_indices']}`",
                f"- Image type: `{example['image_type']}`",
                f"- Contact sheet: `{example['contact_sheet_png']}`",
                f"- Metadata: `{example['metadata_json']}`",
                "- Per-slice visible strut labels: `TODO`",
                "- Human evidence notes: `TODO`",
                "",
            ]
        )
    (output_dir / "review_queue.md").write_text("\n".join(review_lines), encoding="utf-8")
    return manifest, examples


def render_examples(
    example_sets: dict[str, list[dict[str, Any]]],
    raw_volume: np.ndarray,
    segmentation_volume: np.ndarray,
    skeleton_volume: np.ndarray,
    intensity_limits: tuple[float, float],
    output_dir: Path,
    config: FewShotConfig,
) -> list[dict[str, Any]]:
    enriched_examples: list[dict[str, Any]] = []
    example_number = 1
    for label, records in example_sets.items():
        for record in records:
            example_id = f"example_{example_number:03d}"
            bundle_dir = output_dir / "review_examples" / example_id
            metadata = render_example_review_bundle(
                record=record,
                example_id=example_id,
                raw_volume=raw_volume,
                segmentation_volume=segmentation_volume,
                skeleton_volume=skeleton_volume,
                intensity_limits=intensity_limits,
                bundle_dir=bundle_dir,
                config=config,
            )
            enriched = dict(record)
            enriched["example_id"] = example_id
            enriched["evidence_bundle"] = metadata
            enriched_examples.append(enriched)
            example_number += 1
    return enriched_examples


def index_examples_by_label(examples: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for example in examples:
        grouped[str(example["label"])].append(example)
    return grouped


def select_prompt_examples(
    examples_by_label: dict[str, list[dict[str, Any]]],
    target_label: str,
) -> list[dict[str, Any]]:
    ordered_labels = [target_label] + [label for label in ("missing", "broken", "thin", "present") if label != target_label]
    selected: list[dict[str, Any]] = []
    for label in ordered_labels:
        candidates = examples_by_label.get(label, [])
        selected.extend(candidates[:1])
    return selected[:4]


def run_fewshot_strut_classifier(config: FewShotConfig, prepare_examples_only: bool = False) -> dict[str, Any]:
    config.output_dir.mkdir(parents=True, exist_ok=True)
    for path, label in (
        (config.raw_tif, "Raw TIFF stack"),
        (config.segmentation_tif, "Segmentation TIFF"),
        (config.skeleton_tif, "Skeleton TIFF"),
    ):
        validate_input_file(path, label)

    registered_lattice, registered_json_path = load_registered_lattice(config)
    raw_volume = open_tif_volume(config.raw_tif)
    segmentation_volume = open_tif_volume(config.segmentation_tif)
    skeleton_volume = open_tif_volume(config.skeleton_tif)
    intensity_limits = percentile_limits(raw_volume)
    prompt_contract = build_prompt_contract(config.output_dir)
    slice_review_manifest = write_full_slice_review_sequence(
        raw_volume=raw_volume,
        intensity_limits=intensity_limits,
        registered_lattice=registered_lattice,
        output_dir=config.output_dir,
        config=config,
    )

    if prepare_examples_only:
        result = {
            "status": "passed",
            "mode": "prepare_examples_only",
            "registered_json": json_relative(registered_json_path),
            "prompt_contract": prompt_contract,
            "slice_review_manifest": slice_review_manifest,
        }
        (config.output_dir / "run_metadata.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        return result

    junction_by_id = {int(junction["id"]): junction for junction in registered_lattice["junctions"]}
    measured_records = []
    total_struts = len(registered_lattice["struts"])
    for index, strut in enumerate(registered_lattice["struts"], start=1):
        measured_records.append(
            measure_strut_record(
                strut=strut,
                junction_by_id=junction_by_id,
                raw_volume=raw_volume,
                segmentation_volume=segmentation_volume,
                skeleton_volume=skeleton_volume,
                intensity_limits=intensity_limits,
                config=config,
            )
        )
        if index % 2000 == 0 or index == total_struts:
            print(f"[fewshot] measured {index}/{total_struts} struts", flush=True)

    diameter_samples = [float(record["median_nonzero_diameter"]) for record in measured_records if record["median_nonzero_diameter"] > 0]
    diameter_baseline = float(np.median(np.asarray(diameter_samples, dtype=np.float32))) if diameter_samples else 0.0
    classified_records = [classify_record(record, diameter_baseline, config) for record in measured_records]

    labeled_examples_by_label: dict[str, list[dict[str, Any]]] = defaultdict(list)
    candidate_examples_by_label: dict[str, list[dict[str, Any]]] = defaultdict(list)
    records_to_render = sorted(
        [record for record in classified_records if record["predicted_label"] != "present"],
        key=lambda item: (-float(item["confidence"]), int(item["strut_id"])),
    )[: max(0, config.max_rendered_targets)]
    render_ids = {int(record["strut_id"]) for record in records_to_render}

    label_counts = Counter(str(record["predicted_label"]) for record in classified_records)
    output_records: list[dict[str, Any]] = []
    for record in classified_records:
        prompt_examples = select_prompt_examples(labeled_examples_by_label, str(record["predicted_label"]))
        candidate_prompt_examples = select_prompt_examples(candidate_examples_by_label, str(record["predicted_label"]))
        evidence_bundle: dict[str, Any]
        if int(record["strut_id"]) in render_ids:
            bundle_dir = config.output_dir / "targets" / f"strut_{int(record['strut_id']):05d}"
            rendered_metadata = render_evidence_bundle(
                record=record,
                raw_volume=raw_volume,
                segmentation_volume=segmentation_volume,
                skeleton_volume=skeleton_volume,
                intensity_limits=intensity_limits,
                bundle_dir=bundle_dir,
                config=config,
                title_prefix=f"Target strut {int(record['strut_id'])}",
            )
            prompt_payload = build_prompt_payload(
                candidate_prompt_examples,
                {
                    "strut_id": record["strut_id"],
                    "orientation_bucket": record["orientation_bucket"],
                    "evidence_bundle": rendered_metadata,
                },
            )
            prompt_path = bundle_dir / "prompt_payload.json"
            prompt_path.write_text(json.dumps(prompt_payload, indent=2), encoding="utf-8")
            evidence_bundle = {
                **rendered_metadata,
                "metadata_json": json_relative(bundle_dir / "metadata.json"),
                "prompt_payload_json": json_relative(prompt_path),
                "render_status": "rendered",
            }
        else:
            evidence_bundle = {
                "bundle_dir": json_relative(config.output_dir / "targets" / f"strut_{int(record['strut_id']):05d}"),
                "render_status": "not_rendered_by_policy",
                "slice_range": list(
                    compute_slice_range(
                        np.asarray(record["start_xyz"], dtype=np.float32),
                        np.asarray(record["end_xyz"], dtype=np.float32),
                        depth=raw_volume.shape[0],
                        default_half_window=config.default_half_window,
                        slice_padding=config.slice_padding,
                    )
                ),
            }

        output_records.append(
            {
                "strut_id": int(record["strut_id"]),
                "junction0": int(record["junction0"]),
                "junction1": int(record["junction1"]),
                "start_xyz": record["start_xyz"],
                "end_xyz": record["end_xyz"],
                "orientation_bucket": record["orientation_bucket"],
                "length_voxels": record["length_voxels"],
                "predicted_label": record["predicted_label"],
                "confidence": record["confidence"],
                "rationale": record["rationale"],
                "diameter_baseline": record["diameter_baseline"],
                "diameter_ratio_to_baseline": record["diameter_ratio_to_baseline"],
                "coverage_fraction": record["coverage_fraction"],
                "skeleton_fraction": record["skeleton_fraction"],
                "raw_mean": record["raw_mean"],
                "raw_min": record["raw_min"],
                "longest_absent_run": record["longest_absent_run"],
                "evidence_bundle": evidence_bundle,
                "example_ids_used": [example["example_id"] for example in prompt_examples],
                "candidate_example_ids_available": [example["example_id"] for example in candidate_prompt_examples],
                "backend": {
                    "provider": "local",
                    "model": "heuristic_fewshot_v1",
                    "mode": "heuristic-fallback",
                },
            }
        )

    result = {
        "status": "passed",
        "metadata": {
            "registered_json": json_relative(registered_json_path),
            "raw_tif": json_relative(config.raw_tif),
            "segmentation_tif": json_relative(config.segmentation_tif),
            "skeleton_tif": json_relative(config.skeleton_tif),
            "output_dir": json_relative(config.output_dir),
            "prompt_contract_json": json_relative(config.output_dir / "prompt_contract.json"),
            "slice_review_manifest_json": json_relative(config.output_dir / "slice_review_manifest.json"),
            "slice_review_manifest_status": "pending_human_review",
            "class_definitions": CLASS_DEFINITIONS,
            "diameter_baseline": round(float(diameter_baseline), 5),
            "rendered_target_bundle_limit": int(config.max_rendered_targets),
            "rendered_target_bundles": len(render_ids),
            "label_counts": {label: int(label_counts.get(label, 0)) for label in ("present", "missing", "broken", "thin")},
            "runtime_inputs_exclude": [
                "data/missing_struts/analysis/cluster_summary.json",
                "data/missing_struts/analysis/cluster_labels.json",
                "data/missing_struts/analysis/per_strut_defects.json",
            ],
        },
        "strut_records": output_records,
    }
    config.output_json.write_text(json.dumps(result, indent=2), encoding="utf-8")
    (config.output_dir / "run_metadata.json").write_text(json.dumps(result["metadata"], indent=2), encoding="utf-8")
    return result


def cli_main(argv: list[str] | None = None) -> int:
    args = parse_cli_args(argv)
    config = FewShotConfig(
        output_dir=args.output_dir,
        output_json=args.output_json,
        max_rendered_targets=max(0, int(args.max_rendered_targets)),
    )
    result = run_fewshot_strut_classifier(config=config, prepare_examples_only=bool(args.prepare_examples_only))
    print(json.dumps({"status": result["status"], "output_json": json_relative(config.output_json)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(cli_main())
