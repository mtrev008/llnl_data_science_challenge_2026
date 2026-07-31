"""Stackwise, evidence-preserving strut measurement for registered CT lattices.

This module intentionally does not reuse the clustering or existing detector outputs.
Provider responses are advisory instruction records; labels are always produced by the
versioned, deterministic measurements in this file.
"""
from __future__ import annotations

import argparse
import base64
import json
import math
import os
import traceback
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib-cache")
import matplotlib.pyplot as plt
import numpy as np
import tifffile
from huggingface_hub import InferenceClient, get_token
from PIL import Image
from scipy import ndimage as ndi

from src.fewshot_strut_classifier import (
    clamp_bounds, compute_crop_box, interpolate_points, normalize_raw_patch,
    orientation_bucket, percentile_limits, validate_input_file,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA = PROJECT_ROOT / "data" / "missing_struts"
DEFAULT_RAW = DATA / "tif_stacks" / "210127_Brian_Tran_strut_lattices_0point5dash1 1 Slices.tif"
DEFAULT_MASK = DATA / "analysis" / "segmented_mask.tif"
DEFAULT_SKELETON = DATA / "analysis" / "skeleton.tif"
DEFAULT_GEOMETRY = DATA / "registered_jsons" / "210127_Brian_Tran_strut_lattices_0point5dash1 1 Slices.json"
DEFAULT_OUTPUT = DATA / "analysis" / "stackwise_two_agent_detection"
AGENT1_MODEL = "Qwen/Qwen3-VL-30B-A3B-Instruct:novita"
# A second independently prompted VLM reviews the same evidence as Agent 1.
AGENT2_MODEL = "Qwen/Qwen3-VL-30B-A3B-Instruct:novita"
LABELS = ("missing", "broken", "thin", "bent", "normal", "uncertain")
MISSING_VLM_LABELS = ("missing", "not_missing")
# The upper boundary is a scan-truncation region with no usable strut evidence.
DEFAULT_VLM_EXCLUDED_Z_RANGES = ((1, 26), (740, 761))


@dataclass(frozen=True)
class StackwiseConfig:
    raw_tif: Path = DEFAULT_RAW
    segmentation_tif: Path = DEFAULT_MASK
    skeleton_tif: Path | None = DEFAULT_SKELETON
    geometry_json: Path = DEFAULT_GEOMETRY
    output_dir: Path = DEFAULT_OUTPUT
    stack_size: int = 7
    stride: int = 1
    agent1_model: str = AGENT1_MODEL
    agent2_model: str = AGENT2_MODEL
    representative_validation: bool = False
    max_stacks: int | None = None
    center_z: int | None = None
    max_vlm_candidates_per_window: int | None = None
    max_vlm_batches: int | None = None
    vlm_excluded_z_ranges: tuple[tuple[int, int], ...] = DEFAULT_VLM_EXCLUDED_Z_RANGES
    evidence_quadrant: str | None = None
    evidence_grid_size: int = 2
    use_providers: bool = True
    render_evidence: bool = True


@dataclass(frozen=True)
class WindowMeasurementContext:
    """Distance-transform evidence computed once for an inclusive z-window."""
    z0: int
    mask: np.ndarray
    slice_thickness_distance: dict[int, np.ndarray]
    local_component_count: int


def validate_window(stack_size: int, stride: int) -> None:
    if stack_size < 1 or stack_size % 2 == 0:
        raise ValueError("--stack-size must be a positive odd integer")
    if stride < 1:
        raise ValueError("--stride must be at least 1")


def open_volume(path: Path, label: str) -> np.ndarray:
    validate_input_file(path, label)
    try:
        volume = tifffile.memmap(path)
    except Exception:
        volume = tifffile.imread(path)
    if volume.ndim != 3:
        raise ValueError(f"{label} must be a 3-D multipage TIFF, got {volume.shape}")
    return volume


def load_geometry(path: Path) -> tuple[dict[str, Any], dict[int, dict[str, Any]]]:
    validate_input_file(path, "Geometry JSON")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data.get("junctions"), list) or not isinstance(data.get("struts"), list):
        raise ValueError("Geometry JSON must contain list fields 'junctions' and 'struts'")
    junctions = {int(item["id"]): item for item in data["junctions"]}
    for strut in data["struts"]:
        if "id" not in strut or int(strut["junction0"]) not in junctions or int(strut["junction1"]) not in junctions:
            raise ValueError("Each strut needs id, junction0, and junction1 present in junctions")
    return data, junctions


def stack_windows(depth: int, stack_size: int, stride: int) -> list[tuple[int, int]]:
    validate_window(stack_size, stride)
    if depth < 1:
        return []
    half = stack_size // 2
    return [(max(0, center - half), min(depth - 1, center + half)) for center in range(0, depth, stride)]


def struts_intersecting_z(struts: Iterable[dict[str, Any]], junctions: dict[int, dict[str, Any]], z0: int, z1: int) -> list[dict[str, Any]]:
    output = []
    for strut in struts:
        start = np.asarray(junctions[int(strut["junction0"])]["position"], dtype=float)
        end = np.asarray(junctions[int(strut["junction1"])]["position"], dtype=float)
        if min(start[2], end[2]) <= z1 and max(start[2], end[2]) >= z0:
            output.append(strut)
    return output


def _point_at_z(start: np.ndarray, end: np.ndarray, z: float) -> np.ndarray:
    delta = float(end[2] - start[2])
    return (start + end) / 2 if abs(delta) < 1e-6 else start + (end - start) * ((z - start[2]) / delta)


def _line_samples(start: np.ndarray, end: np.ndarray, z0: int, z1: int) -> np.ndarray:
    dz = float(end[2] - start[2])
    if abs(dz) < 1e-6:
        clipped_start, clipped_end = start, end
    else:
        t_at_bounds = sorted(((z0 - start[2]) / dz, (z1 - start[2]) / dz))
        t0, t1 = max(0.0, t_at_bounds[0]), min(1.0, t_at_bounds[1])
        clipped_start, clipped_end = start + (end - start) * t0, start + (end - start) * t1
    return interpolate_points(clipped_start, clipped_end, max(7, int(np.linalg.norm(clipped_end - clipped_start) / 2) + 1))


def _support_at(mask: np.ndarray, point: np.ndarray, radius: int = 2) -> bool:
    x, y, z = (int(round(float(v))) for v in point)
    z0, z1 = clamp_bounds(z - radius, z + radius + 1, mask.shape[0])
    y0, y1 = clamp_bounds(y - radius, y + radius + 1, mask.shape[1])
    x0, x1 = clamp_bounds(x - radius, x + radius + 1, mask.shape[2])
    return bool(np.any(mask[z0:z1, y0:y1, x0:x1] > 0))


def _longest_false_run(flags: Iterable[bool]) -> int:
    current = longest = 0
    for flag in flags:
        current = 0 if flag else current + 1
        longest = max(longest, current)
    return longest


def robust_baselines(records: list[dict[str, Any]]) -> dict[tuple[str, int], tuple[float, float]]:
    groups: dict[tuple[str, int], list[float]] = defaultdict(list)
    for record in records:
        if record["occupancy_ratio"] >= 0.75 and record["mean_thickness"] > 0:
            groups[(record["orientation_bucket"], int(record["length_voxels"] // 15))].append(record["mean_thickness"])
    return {key: (float(np.median(values)), max(0.15, float(np.median(np.abs(np.asarray(values) - np.median(values)))) * 1.4826)) for key, values in groups.items()}


def robust_shape_baselines(records: list[dict[str, Any]]) -> dict[tuple[str, int], tuple[float, float, float, float]]:
    """Matched-normal curvature and deviation references used for bending candidates."""
    groups: dict[tuple[str, int], list[tuple[float, float]]] = defaultdict(list)
    for record in records:
        if record["occupancy_ratio"] >= 0.75 and record["alignment_quality"] == "acceptable":
            groups[(record["orientation_bucket"], int(record["length_voxels"] // 15))].append((float(record["curvature"]), float(record["maximum_deviation"])))
    output = {}
    for key, values in groups.items():
        array = np.asarray(values, dtype=float)
        curvature_median, deviation_median = np.median(array, axis=0)
        curvature_mad, deviation_mad = np.median(np.abs(array - np.asarray([curvature_median, deviation_median])), axis=0) * 1.4826
        output[key] = (float(curvature_median), max(0.02, float(curvature_mad)), float(deviation_median), max(0.5, float(deviation_mad)))
    return output


def decision_from_measurement(record: dict[str, Any], baseline: tuple[float, float] | None, shape_baseline: tuple[float, float, float, float] | None = None) -> tuple[str, float, str]:
    occ, gap, raw = record["occupancy_ratio"], record["maximum_gap_length"], record["raw_ct_corroboration"]
    count = max(1, record["sample_count"])
    if record.get("alignment_quality") == "poor":
        return "uncertain", 0.35, "Expected corridor is outside the usable volume."
    if occ <= 0.10 and raw <= 0.25:
        return "missing", 0.88, "No segmentation or raw-CT material corroborates the expected span."
    if gap / count >= 0.25 and occ < 0.85:
        return "broken", min(0.94, 0.62 + gap / count * 0.5), "A persistent internal corridor gap remains."
    if baseline and record["mean_thickness"] < baseline[0] - max(2 * baseline[1], baseline[0] * 0.18) and occ >= 0.6:
        return "thin", 0.76, "Continuous material is robustly below matched normal thickness."
    if shape_baseline:
        curvature_median, curvature_scale, deviation_median, deviation_scale = shape_baseline
        curvature_outlier = record["curvature"] > curvature_median + max(4 * curvature_scale, 0.04)
        deviation_outlier = record["maximum_deviation"] > deviation_median + max(4 * deviation_scale, 1.0)
        if curvature_outlier or deviation_outlier:
            return "bent", 0.70, "Observed shape is a robust matched-normal curvature or deviation outlier."
    if occ >= 0.55:
        return "normal", 0.72, "Corridor material is continuous within alignment tolerance."
    return "uncertain", 0.42, "Insufficient or conflicting local evidence."


def window_measurement_context(mask: np.ndarray, z0: int, z1: int) -> WindowMeasurementContext:
    """Compute bounded per-slice thickness maps once, then reuse them per strut."""
    window_mask = mask[z0:z1 + 1] > 0
    slice_thickness_distance = {
        local_z: np.asarray(ndi.distance_transform_edt(window_mask[local_z]), dtype=np.float32)
        for local_z in range(window_mask.shape[0])
    }
    return WindowMeasurementContext(
        z0=z0,
        mask=window_mask,
        slice_thickness_distance=slice_thickness_distance,
        local_component_count=int(ndi.label(window_mask)[1]),
    )


def _nearest_foreground_point(mask: np.ndarray, z: int, y: int, x: int, radius: int = 8) -> tuple[float, np.ndarray]:
    """Find local observed material without allocating a full-volume nearest-index map."""
    z0, z1 = clamp_bounds(z - radius, z + radius + 1, mask.shape[0])
    y0, y1 = clamp_bounds(y - radius, y + radius + 1, mask.shape[1])
    x0, x1 = clamp_bounds(x - radius, x + radius + 1, mask.shape[2])
    candidates = np.argwhere(mask[z0:z1, y0:y1, x0:x1] > 0)
    expected = np.asarray([x, y, z], dtype=float)
    if not len(candidates):
        return float(radius + 1), expected
    points = candidates[:, [2, 1, 0]].astype(float)
    points += np.asarray([x0, y0, z0], dtype=float)
    distances = np.linalg.norm(points - expected, axis=1)
    nearest = points[int(np.argmin(distances))]
    return float(np.min(distances)), nearest


def measure_strut(strut: dict[str, Any], junctions: dict[int, dict[str, Any]], raw: np.ndarray, mask: np.ndarray, skeleton: np.ndarray | None, z0: int, z1: int, raw_limits: tuple[float, float], context: WindowMeasurementContext) -> dict[str, Any]:
    start = np.asarray(junctions[int(strut["junction0"])]["position"], dtype=float)
    end = np.asarray(junctions[int(strut["junction1"])]["position"], dtype=float)
    samples = _line_samples(start, end, z0, z1)
    support = [_support_at(mask, point) for point in samples]
    low, high = raw_limits
    raw_values = []
    thicknesses = []
    deviations = []
    observed_points = []
    for point in samples:
        x, y, z = (int(round(float(v))) for v in point)
        if 0 <= z < raw.shape[0] and 0 <= y < raw.shape[1] and 0 <= x < raw.shape[2]:
            raw_values.append(float(np.clip((float(raw[z, y, x]) - low) / (high - low), 0, 1)))
            local_z = z - context.z0
            if 0 <= local_z < context.mask.shape[0]:
                thicknesses.append(float(2 * context.slice_thickness_distance[local_z][y, x]))
                deviation, observed_local = _nearest_foreground_point(context.mask, local_z, y, x)
                deviations.append(deviation)
                observed_points.append(observed_local + np.asarray([0.0, 0.0, float(context.z0)]))
    direction = end - start
    length = float(np.linalg.norm(direction))
    endpoint_connection = bool(support[0] and support[-1]) if support else False
    max_gap = _longest_false_run(support)
    if len(observed_points) >= 3:
        step_vectors = np.diff(np.asarray(observed_points), axis=0)
        step_lengths = np.linalg.norm(step_vectors, axis=1)
        unit_steps = step_vectors[step_lengths > 1e-6] / step_lengths[step_lengths > 1e-6, None]
        curvature = float(np.max(np.linalg.norm(np.diff(unit_steps, axis=0), axis=1))) if len(unit_steps) >= 2 else 0.0
    else:
        curvature = 0.0
    return {
        "strut_id": int(strut["id"]), "junction0": int(strut["junction0"]), "junction1": int(strut["junction1"]),
        "start_xyz": [round(float(v), 4) for v in start], "end_xyz": [round(float(v), 4) for v in end],
        "length_voxels": round(length, 4), "orientation_bucket": orientation_bucket(direction), "sample_count": len(support),
        "occupancy_ratio": round(float(np.mean(support)) if support else 0.0, 5), "maximum_gap_length": max_gap,
        "mean_thickness": round(float(np.mean(thicknesses)) if thicknesses else 0.0, 5), "minimum_thickness": round(float(np.min(thicknesses)) if thicknesses else 0.0, 5),
        "maximum_deviation": round(float(np.max(deviations)) if deviations else 0.0, 5), "curvature": round(curvature, 5),
        "raw_ct_corroboration": round(float(np.mean(raw_values)) if raw_values else 0.0, 5), "local_components": context.local_component_count,
        "endpoint_connection": endpoint_connection, "persistent_gap": bool(max_gap >= max(2, len(support)//4)),
        "segmentation_quality": "available", "alignment_quality": "acceptable" if all(0 <= p[0] < raw.shape[2] and 0 <= p[1] < raw.shape[1] for p in samples) else "poor",
        "skeleton_available": skeleton is not None,
    }


def _render_stack_panel(path: Path, raw: np.ndarray, mask: np.ndarray, skeleton: np.ndarray | None, targets: list[dict[str, Any]], junctions: dict[int, dict[str, Any]], z0: int, z1: int, limits: tuple[float, float]) -> None:
    z = (z0 + z1) // 2
    panels = [(raw[z], "Raw CT"), (mask[z] > 0, "Segmentation"), (skeleton[z] > 0 if skeleton is not None else np.zeros_like(mask[z]), "Skeleton")]
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    for ax, (image, title) in zip(axes, panels):
        ax.imshow(normalize_raw_patch(image, *limits) if title == "Raw CT" else image, cmap="gray", origin="lower")
        for strut in targets:
            a = np.asarray(junctions[int(strut["junction0"])]["position"]); b = np.asarray(junctions[int(strut["junction1"])]["position"])
            point = _point_at_z(a, b, z)
            ax.plot([a[0], b[0]], [a[1], b[1]], color="cyan", alpha=.4, linewidth=.7)
            ax.text(point[0], point[1], str(strut["id"]), color="yellow", fontsize=5)
        ax.set_title(f"{title}; z={z}"); ax.set_axis_off()
    fig.suptitle(f"Expected corridors / junction-defined struts; stack {z0}-{z1}")
    fig.tight_layout(); fig.savefig(path, dpi=130); plt.close(fig)


def _render_clean_stack_panel(path: Path, raw: np.ndarray, mask: np.ndarray, skeleton: np.ndarray | None, z0: int, z1: int, limits: tuple[float, float]) -> None:
    """Render the raw evidence views without registered-strut annotations."""
    z = (z0 + z1) // 2
    panels = [
        (raw[z], "Raw CT"),
        (mask[z] > 0, "Segmentation"),
        (skeleton[z] > 0 if skeleton is not None else np.zeros_like(mask[z]), "Skeleton"),
    ]
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    for ax, (image, title) in zip(axes, panels):
        ax.imshow(normalize_raw_patch(image, *limits) if title == "Raw CT" else image, cmap="gray", origin="lower")
        ax.set_title(f"{title}; z={z}")
        ax.set_axis_off()
    fig.suptitle(f"Clean CT evidence; stack {z0}-{z1}")
    fig.tight_layout(); fig.savefig(path, dpi=130); plt.close(fig)


def evidence_crop_bounds(shape: tuple[int, int], quadrant: str | None) -> tuple[int, int, int, int]:
    """Return x0, x1, y0, y1 for an optional image quadrant."""
    height, width = shape
    if quadrant is None:
        return 0, width, 0, height
    if quadrant != "top_right":
        raise ValueError("evidence_quadrant must be 'top_right' or None")
    return width // 2, width, 0, height // 2


def evidence_tile_bounds(shape: tuple[int, int], row: int, column: int, grid_size: int) -> tuple[int, int, int, int]:
    """Return source-array x0, x1, y0, y1 for one row-major image tile."""
    if grid_size < 1 or row < 0 or column < 0 or row >= grid_size or column >= grid_size:
        raise ValueError("grid_size and tile row/column must describe a valid positive grid")
    height, width = shape
    y_edges = np.linspace(0, height, grid_size + 1, dtype=int)
    x_edges = np.linspace(0, width, grid_size + 1, dtype=int)
    return int(x_edges[column]), int(x_edges[column + 1]), int(y_edges[row]), int(y_edges[row + 1])


def _raw_to_display_uint8(array: np.ndarray) -> np.ndarray:
    """Encode CT source values as 8-bit without contrast normalization."""
    source = np.asarray(array)
    if source.dtype.itemsize > 1:
        return (source.astype(np.uint16) >> 8).astype(np.uint8)
    return source.astype(np.uint8, copy=False)


def _multimodal_tile(raw_tile: np.ndarray, mask_tile: np.ndarray, skeleton_tile: np.ndarray) -> Image.Image:
    """Put the three aligned evidence modalities into one VLM image."""
    raw_image = Image.fromarray(_raw_to_display_uint8(raw_tile)).convert("RGB")
    mask_image = Image.fromarray((np.asarray(mask_tile) > 0).astype(np.uint8) * 255).convert("RGB")
    skeleton_image = Image.fromarray((np.asarray(skeleton_tile) > 0).astype(np.uint8) * 255).convert("RGB")
    composite = Image.new("RGB", (raw_image.width * 3, raw_image.height))
    composite.paste(raw_image, (0, 0))
    composite.paste(mask_image, (raw_image.width, 0))
    composite.paste(skeleton_image, (raw_image.width * 2, 0))
    return composite


def _export_original_slice_images(directory: Path, batch_id: str, z: int, raw: np.ndarray, mask: np.ndarray, skeleton: np.ndarray | None, quadrant: str | None = None, grid_size: int = 1) -> list[tuple[str, Path]]:
    """Write VLM evidence; a 2x2 grid is exactly four multimodal images."""
    if quadrant is not None and grid_size != 1:
        raise ValueError("evidence_quadrant and evidence_grid_size cannot both select a crop")
    skeleton_plane = skeleton[z] if skeleton is not None else np.zeros_like(mask[z])
    outputs: list[tuple[str, Path]] = []
    tile_locations = [(None, evidence_crop_bounds(raw[z].shape, quadrant))] if quadrant is not None else [((row, column), evidence_tile_bounds(raw[z].shape, row, column, grid_size)) for row in range(grid_size) for column in range(grid_size)]
    for tile, (x0, x1, y0, y1) in tile_locations:
        tile_suffix = "" if tile is None else f"_tile_r{tile[0] + 1:02d}_c{tile[1] + 1:02d}"
        path = directory / f"{batch_id}_z{z:04d}_multimodal{tile_suffix}.png"
        _multimodal_tile(raw[z, y0:y1, x0:x1], mask[z, y0:y1, x0:x1], skeleton_plane[y0:y1, x0:x1]).save(path)
        region = "top-right quarter" if tile is None else ("full slice" if grid_size == 1 else f"tile row {tile[0] + 1}, column {tile[1] + 1} of a {grid_size}x{grid_size} grid")
        outputs.append((f"Multimodal {region} at z={z}; source-array bounds x={x0}:{x1}, y={y0}:{y1}. The three horizontal panels are Raw CT, Segmentation, then Skeleton; raw CT uses direct 16-bit-to-8-bit encoding without contrast normalization.", path))
    return outputs


def _candidate_crop_box(strut: dict[str, Any], junctions: dict[int, dict[str, Any]], raw: np.ndarray) -> tuple[int, int, int, int]:
    """Return the shared XY crop for all individual slices of one candidate."""
    start = np.asarray(junctions[int(strut["junction0"])]["position"])
    end = np.asarray(junctions[int(strut["junction1"])]["position"])
    return compute_crop_box(start, end, raw.shape[2], raw.shape[1], margin=14)


def _render_candidate_slice_panel(path: Path, raw: np.ndarray, mask: np.ndarray, skeleton: np.ndarray | None, crop_box: tuple[int, int, int, int], z: int, limits: tuple[float, float]) -> None:
    """Render one unannotated candidate crop at one z slice, with three modalities."""
    x0, x1, y0, y1 = crop_box
    fig, axes = plt.subplots(1, 3, figsize=(8.5, 3.0))
    modalities = (
        ("Raw CT", lambda z: normalize_raw_patch(raw[z, y0:y1, x0:x1], *limits)),
        ("Segmentation", lambda z: mask[z, y0:y1, x0:x1] > 0),
        ("Skeleton", lambda z: skeleton[z, y0:y1, x0:x1] > 0 if skeleton is not None else np.zeros((y1 - y0, x1 - x0), dtype=bool)),
    )
    for axis, (name, image_at) in zip(axes, modalities):
        axis.imshow(image_at(z), cmap="gray", origin="lower")
        axis.set_title(name, fontsize=10)
        axis.set_axis_off()
    fig.suptitle(f"Clean candidate corridor crop; z={z} (no geometry overlay)", fontsize=11)
    fig.tight_layout(); fig.savefig(path, dpi=130); plt.close(fig)


def _junction_pair(strut: dict[str, Any]) -> tuple[int, int]:
    """Return the ordered registered endpoint IDs used in VLM contracts."""
    return int(strut["junction0"]), int(strut["junction1"])


def _render_candidate_index_panel(path: Path, targets: list[dict[str, Any]], z0: int, z1: int) -> None:
    """Render a text-only crop map using registered junction IDs only."""
    rows = [[str(number), str(_junction_pair(target)[0]), str(_junction_pair(target)[1])] for number, target in enumerate(targets, start=1)]
    figure_height = max(2.0, 0.46 * len(rows) + 1.2)
    fig, axis = plt.subplots(figsize=(8.2, figure_height))
    axis.set_axis_off()
    table = axis.table(cellText=rows, colLabels=["Crop", "Junction 0", "Junction 1"], loc="center", cellLoc="center")
    table.auto_set_font_size(False); table.set_fontsize(10); table.scale(1, 1.3)
    fig.suptitle(f"Candidate index only; stack {z0}-{z1}. This table is not image evidence.", fontsize=11)
    fig.tight_layout(); fig.savefig(path, dpi=150); plt.close(fig)


def _completion_payload(completion: Any) -> dict[str, Any]:
    if hasattr(completion, "model_dump"):
        return completion.model_dump()
    if hasattr(completion, "choices"):
        return {
            "choices": [
                {
                    "finish_reason": getattr(choice, "finish_reason", None),
                    "message": {
                        "role": getattr(getattr(choice, "message", None), "role", "assistant"),
                        "content": getattr(getattr(choice, "message", None), "content", ""),
                    },
                }
                for choice in completion.choices
            ]
        }
    return {"message": str(completion)}


def _provider_request(model: str, payload: dict[str, Any], token: str) -> dict[str, Any]:
    client = InferenceClient(api_key=token, timeout=60)
    try:
        completion = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": [{"type": "text", "text": json.dumps(payload)}]}],
            max_tokens=512,
        )
        return _completion_payload(completion)
    except Exception as exc:
        raise RuntimeError(f"Hugging Face provider rejected {model}: {exc}") from exc


def _provider_stack_request(model: str, instruction: dict[str, Any], panels: list[tuple[str, Path]], token: str) -> dict[str, Any]:
    """Send clean context, index, and unannotated strut crops to a provider."""
    content: list[dict[str, Any]] = []
    if prompt := instruction.get("vlm_prompt"):
        content.append({"type": "text", "text": str(prompt)})
    content.append({"type": "text", "text": "Window manifest and required response schema:\n" + json.dumps(instruction)})
    for description, panel_path in panels:
        encoded = base64.b64encode(panel_path.read_bytes()).decode("ascii")
        content.extend((
            {"type": "text", "text": description},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{encoded}"}},
        ))
    messages = [{"role": "user", "content": content}]
    client = InferenceClient(api_key=token, timeout=60)
    try:
        completion = client.chat.completions.create(model=model, messages=messages, max_tokens=768)
        return _completion_payload(completion)
    except Exception as exc:
        raise RuntimeError(f"Hugging Face provider rejected {model}: {exc}") from exc


def provider_token() -> str:
    """Return an explicit token or the token saved by ``hf auth login``."""
    token = os.environ.get("HF_TOKEN") or get_token()
    if not token:
        raise RuntimeError("Hugging Face authentication is required for provider calls; no fallback model is selected.")
    return token


def preflight_models(config: StackwiseConfig) -> None:
    if not config.use_providers:
        return
    token = provider_token()
    for model in dict.fromkeys((config.agent1_model, config.agent2_model)):
        _provider_request(model, {"task": "preflight", "reply": "ok"}, token)


def agent1_contract(stack_id: str, z0: int, z1: int, targets: list[dict[str, Any]], geometry: dict[str, Any], junctions: dict[int, dict[str, Any]] | None = None, evidence_z_slices: list[int] | None = None, panel_crop_xyxy: tuple[int, int, int, int] | None = None) -> dict[str, Any]:
    evidence_z_slices = evidence_z_slices or list(range(z0, z1 + 1))
    panel_crop_xyxy = panel_crop_xyxy or (0, 0, 0, 0)
    crop_x0, _, crop_y0, _ = panel_crop_xyxy
    id_location_manifest = []
    for review_order, strut in enumerate(targets, start=1):
        junction0_id, junction1_id = _junction_pair(strut)
        item = {"review_order": review_order, "junction0_id": junction0_id, "junction1_id": junction1_id}
        if junctions is not None:
            positions = []
            start = np.asarray(junctions[int(strut["junction0"])]["position"])
            end = np.asarray(junctions[int(strut["junction1"])]["position"])
            for z in evidence_z_slices:
                if min(start[2], end[2]) <= z <= max(start[2], end[2]):
                    point = _point_at_z(start, end, z)
                    positions.append({"z": z, "expected_xy": [round(float(point[0] - crop_x0), 1), round(float(point[1] - crop_y0), 1)]})
            item["expected_locations"] = positions
        id_location_manifest.append(item)
    return {
        "schema_version": "1.2",
        "agent": "agent1_multimodal_window_analyst",
        "vlm_prompt": """You are Agent 1, a multimodal CT-lattice evidence analyst. Review the attached source-array evidence for one CT-lattice z-window. For each z, you receive one multimodal image per spatial tile; its three horizontal panels are Raw CT, Segmentation, then Skeleton. For a 2x2 grid, this is exactly four images. Inspect every row-major tile and all three panels before moving to the next z; source-array bounds are stated in each panel description. Raw CT uses direct 16-bit-to-8-bit encoding without contrast normalization, and there is no geometry overlay. Inspect the images in ascending z order; a boundary-trimmed window can contain fewer than seven supplied slices, and you must not infer evidence for omitted slices.

The JSON-derived registered-junction manifest contains EVERY registered connection visible in the supplied image region. It is not selected or ranked by deterministic defect measurements. Entries are in row-by-column order: increasing expected y (row), then increasing expected x (column); review_order is the local position in that sequence. Each entry names its endpoint nodes as junction0_id and junction1_id, and expected_xy is the nominal corridor location in the supplied panel at that z. The manifest is a lookup aid, not observed material evidence. Do not invent junction IDs or nominate a pair absent from this manifest.

Apply this visual missing-strut criterion. A registered strut should exist as a material bridge between its two registered junctions/nodes. Every interior junction should have four visually connected struts, one on each local lattice side/direction. A junction on one of the four lateral sides of the scan (left, right, top, or bottom in the slice) may legitimately have fewer visible connections; reduced degree at such a boundary junction alone is not missing evidence. At both endpoint nodes, inspect all four local lattice sides/directions: distinguish the expected connection to the opposite endpoint from the other three neighboring connections. Nominate a strut only if its expected junction-to-junction bridge is substantially absent in raw CT and lacks a continuous segmentation/skeleton bridge. Material at both endpoints with an absent interior is broken, not missing. Thin, bent, low-contrast-but-present, clipped, or misregistered evidence is not sufficient for missing; report it as uncertainty for Agent 2 instead.

Return a compact missing-strut triage handoff, not an entry for every target. For each visually nominated connection, preserve both junction0_id and junction1_id and report whether the clean raw CT, segmentation, and skeleton show material along the expected corridor. Do not call a strut missing yourself and do not invent junction IDs.

Keep all arrays within their stated limits and all strings concise. Your output is handed to Agent 2, which makes the final VLM label with reasoning; deterministic numeric measurements are retained as audit evidence.""",
        "stack_id": stack_id,
        "z_range_inclusive": [z0, z1],
        "evidence_panel_crop_xyxy_in_source": list(panel_crop_xyxy),
        "registered_junction_connection_manifest": id_location_manifest,
        "geometry_metadata": {k: geometry[k] for k in ("spacing", "material", "units") if k in geometry},
        "required_preprocessing": ["For each z slice, inspect all four row-major spatial tiles and the Raw CT, Segmentation, and Skeleton panels within each tile.", "Review manifest entries in the supplied row-by-column order; it was not defect-filtered.", "Use the registered junction IDs only to map visible endpoints and expected connections.", "Expect four visible strut connections at each interior junction; allow reduced degree only at the left, right, top, or bottom scan boundary.", "At each endpoint node inspect all four local lattice sides/directions, then assess whether the expected bridge to the paired endpoint node is absent."],
        "required_features": ["corridor occupancy", "components", "endpoint connection", "persistent gaps", "distance-transform thickness", "centerline deviation", "curvature", "raw-CT corroboration", "quality flags"],
        "threshold_rule": "Use same-orientation, similar-length normal candidates with median and MAD.",
        "persistence_rule": "Defects require two overlapping stacks unless the stack spans the complete strut.",
        "required_output_schema": {
            "window_summary": "string, maximum 120 words",
            "potential_missing_observations": "array of visually nominated entries from this manifest, each with junction0_id, junction1_id, raw_ct_support, segmentation_support, skeleton_support, and corridor_extent",
            "uncertainty_conditions": "array, maximum 5 concise strings",
            "agent2_missing_review_junction_pairs": "array of visually nominated objects, each with junction0_id and junction1_id from this manifest",
        },
    }


def agent2_adjudication_contract(stack_id: str, agent1_instruction: dict[str, Any]) -> dict[str, Any]:
    """Final VLM adjudication from Agent 1's description and the same image evidence."""
    return {
        "schema_version": "1.0",
        "agent": "agent2_multimodal_final_adjudicator",
        "vlm_prompt": """You are Agent 2, the final missing-strut adjudicator for a registered CT-lattice window. You receive the same four multimodal spatial-tile images that Agent 1 reviewed for each z, Agent 1's written description, and focused clean crop images only for Agent 1-nominated junction pairs. Each tile has Raw CT, Segmentation, and Skeleton horizontal panels. Inspect every supplied tile in row-major order and every z in ascending order, then assess Agent 1's description against the observed evidence. Tile source-array bounds are in their panel descriptions. Boundary-trimmed stacks can contain fewer than seven slices; do not infer evidence for omitted boundary slices. The index maps crop number to its ordered junction0_id and junction1_id only; it is not material evidence.\n\nFor every supplied junction pair, return exactly one final label: missing or not_missing. A missing strut must be a substantially absent material bridge between its two registered junctions/nodes in raw CT and segmentation/skeleton evidence. Every interior junction should have four visually connected struts, one on each local lattice side/direction. A junction on the left, right, top, or bottom lateral scan boundary may legitimately have fewer visible connections, so reduced degree there alone is not missing evidence. At both endpoint nodes, consider all four local lattice sides/directions and verify that the absent connection is the expected bridge between the named endpoint pair, rather than another neighboring strut. If there is any continuous material bridge, or material is absent only in the interior while endpoints remain, return not_missing: the latter is a broken-strut pattern, not missing. Also return not_missing for thin, bent, low-contrast-but-present, clipped, misregistered, or conflicting evidence. Include concise visual reasoning and confidence from 0 to 1. Preserve junction0_id and junction1_id exactly.\n\nReturn only the requested compact JSON object. Do not repeat the prompt, manifest, or Agent 1's text.""",
        "stack_id": stack_id,
        "agent1_description": agent1_instruction.get("agent1_analysis", {}),
        "agent1_instructions": {key: agent1_instruction[key] for key in ("required_features", "threshold_rule", "persistence_rule", "required_output_schema")},
        "required_output_schema": {
            "agreement_summary": "string",
            "final_assessments": [{"junction0_id": "integer", "junction1_id": "integer", "final_label": "missing|not_missing", "confidence": "number 0..1", "reasoning": "string", "agent1_agreement": "agree|disagree|partial"}],
        },
        "safety_rule": "Every final assessment must preserve a supplied junction0_id and junction1_id, use only missing or not_missing, and give visual reasoning. Do not invent observations for junction pairs absent from Agent 1's description.",
    }


def _response_junction_pair(item: Any) -> tuple[int, int] | None:
    if not isinstance(item, dict):
        return None
    try:
        return int(item["junction0_id"]), int(item["junction1_id"])
    except (KeyError, TypeError, ValueError):
        return None


def parse_agent2_assessments(response: dict[str, Any], allowed_pairs: Iterable[tuple[int, int]] | None = None) -> list[dict[str, Any]]:
    """Extract validated VLM final labels without altering deterministic records."""
    choices = response.get("choices", [])
    content = choices[0].get("message", {}).get("content", "") if choices else ""
    if not isinstance(content, str):
        return []
    if content.startswith("```"):
        content = content.split("\n", 1)[1].rsplit("```", 1)[0]
    try:
        payload = json.loads(content)
    except json.JSONDecodeError:
        # Some providers stop immediately after the final assessments array.
        # Recover only the unambiguous omitted outer object delimiter.
        if not content.rstrip().endswith("]"):
            return []
        try:
            payload = json.loads(content.rstrip() + "}")
        except json.JSONDecodeError:
            return []
    allowed = set(allowed_pairs) if allowed_pairs is not None else None
    normalized = []
    for item in payload.get("final_assessments", []):
        if item.get("final_label") not in MISSING_VLM_LABELS:
            continue
        try:
            confidence = float(item["confidence"])
        except (KeyError, TypeError, ValueError):
            continue
        pair = _response_junction_pair(item)
        if pair is None or (allowed is not None and pair not in allowed):
            continue
        normalized.append({"junction0_id": pair[0], "junction1_id": pair[1], "final_label": item["final_label"], "confidence": max(0.0, min(1.0, confidence)), "reasoning": str(item.get("reasoning", "")), "agent1_agreement": str(item.get("agent1_agreement", ""))})
    return normalized


def parse_agent1_review_pairs(response: dict[str, Any], allowed_pairs: Iterable[tuple[int, int]]) -> list[tuple[int, int]]:
    """Keep only manifest junction pairs explicitly nominated by Agent 1."""
    choices = response.get("choices", [])
    content = choices[0].get("message", {}).get("content", "") if choices else ""
    if not isinstance(content, str):
        return []
    if content.startswith("```"):
        content = content.split("\n", 1)[1].rsplit("```", 1)[0]
    try:
        payload = json.loads(content)
    except json.JSONDecodeError:
        return []
    allowed = set(allowed_pairs)
    proposed = list(payload.get("agent2_missing_review_junction_pairs", []))
    proposed.extend(item for item in payload.get("potential_missing_observations", []) if isinstance(item, dict))
    review_pairs: list[tuple[int, int]] = []
    for item in proposed:
        pair = _response_junction_pair(item)
        if pair is not None and pair in allowed and pair not in review_pairs:
            review_pairs.append(pair)
    return review_pairs


def merge_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for record in records: by_id[int(record["strut_id"])].append(record)
    merged = []
    for strut_id, items in sorted(by_id.items()):
        counts = Counter(item["classification"] for item in items)
        defect, quantity = max(((label, count) for label, count in counts.items() if label not in ("normal", "uncertain")), default=("normal", 0), key=lambda item: item[1])
        full_span = any(item.get("full_span_observation", False) for item in items)
        label = defect if quantity >= 2 or full_span else ("normal" if counts["normal"] else "uncertain")
        source = [item for item in items if item["classification"] == label] or items
        merged.append({"strut_id": strut_id, "classification": label, "confidence": round(float(np.mean([item["confidence"] for item in source])), 5), "stack_ids": [item["stack_id"] for item in items], "overlap_evidence_count": quantity, "records": items})
    return merged


def accumulate_record(aggregates: dict[int, dict[str, Any]], record: dict[str, Any]) -> None:
    """Keep compact overlap evidence in memory while full records stream to disk."""
    strut_id = int(record["strut_id"])
    aggregate = aggregates.setdefault(strut_id, {"counts": Counter(), "confidence_by_label": defaultdict(list), "stack_ids": [], "full_span": False, "representative_record": record})
    label = str(record["classification"])
    aggregate["counts"][label] += 1
    aggregate["confidence_by_label"][label].append(float(record["confidence"]))
    aggregate["stack_ids"].append(record["stack_id"])
    aggregate["full_span"] = bool(aggregate["full_span"] or record["full_span_observation"])
    if float(record["confidence"]) > float(aggregate["representative_record"]["confidence"]):
        aggregate["representative_record"] = record


def finalize_aggregates(aggregates: dict[int, dict[str, Any]]) -> list[dict[str, Any]]:
    merged = []
    for strut_id, aggregate in sorted(aggregates.items()):
        counts: Counter[str] = aggregate["counts"]
        defect, quantity = max(((label, count) for label, count in counts.items() if label not in ("normal", "uncertain")), default=("normal", 0), key=lambda item: item[1])
        label = defect if quantity >= 2 or aggregate["full_span"] else ("normal" if counts["normal"] else "uncertain")
        confidence_values = aggregate["confidence_by_label"].get(label) or aggregate["confidence_by_label"].get("normal") or [0.0]
        merged.append({"strut_id": strut_id, "classification": label, "confidence": round(float(np.mean(confidence_values)), 5), "stack_ids": aggregate["stack_ids"], "overlap_evidence_count": quantity, "record_count": int(sum(counts.values())), "representative_record": aggregate["representative_record"]})
    return merged


def candidate_score(record: dict[str, Any]) -> float:
    """Rank deterministic anomaly candidates without clustering."""
    label = str(record["classification"])
    severity = {"missing": 1.0, "broken": 0.9, "thin": 0.75, "bent": 0.7, "uncertain": 0.45}.get(label, 0.0)
    gap_ratio = float(record["maximum_gap_length"]) / max(1, int(record["sample_count"]))
    return round(severity + 0.25 * gap_ratio + 0.15 * (1.0 - float(record["occupancy_ratio"])), 5)


def candidate_summary(record: dict[str, Any]) -> dict[str, Any]:
    """Persist the rule trigger and numeric evidence for a VLM candidate."""
    return {
        "strut_id": int(record["strut_id"]),
        "candidate_label": record["classification"],
        "candidate_score": candidate_score(record),
        "reason": record["reason"],
        "stack_id": record["stack_id"],
        "evidence": {key: record[key] for key in ("occupancy_ratio", "maximum_gap_length", "endpoint_connection", "mean_thickness", "maximum_deviation", "curvature", "raw_ct_corroboration", "alignment_quality")},
    }


def candidate_selection_key(record: dict[str, Any]) -> tuple[float, int, float, int, int]:
    """Choose one review window per strut deterministically after overlap collection."""
    return (
        candidate_score(record),
        int(bool(record.get("full_span_observation"))),
        float(record["raw_ct_corroboration"]),
        int(record["alignment_quality"] == "acceptable"),
        -int(record["stack_range"][0]),
    )


def row_column_key(record: dict[str, Any], struts_by_id: dict[int, dict[str, Any]], junctions: dict[int, dict[str, Any]]) -> tuple[float, float, int, int]:
    """Order a slice-intersecting registered connection by nominal row then column."""
    strut = struts_by_id[int(record["strut_id"])]
    junction0_id, junction1_id = _junction_pair(strut)
    start = np.asarray(junctions[junction0_id]["position"], dtype=float)
    end = np.asarray(junctions[junction1_id]["position"], dtype=float)
    z = min(max(float(record["target_slice"]), min(start[2], end[2])), max(start[2], end[2]))
    point = _point_at_z(start, end, z)
    return round(float(point[1]), 4), round(float(point[0]), 4), junction0_id, junction1_id


def record_in_evidence_crop(record: dict[str, Any], struts_by_id: dict[int, dict[str, Any]], junctions: dict[int, dict[str, Any]], crop_xyxy: tuple[int, int, int, int]) -> bool:
    strut = struts_by_id[int(record["strut_id"])]
    start = np.asarray(junctions[int(strut["junction0"])]["position"], dtype=float)
    end = np.asarray(junctions[int(strut["junction1"])]["position"], dtype=float)
    point = _point_at_z(start, end, float(record["target_slice"]))
    x0, x1, y0, y1 = crop_xyxy
    return x0 <= point[0] < x1 and y0 <= point[1] < y1


def window_intersects_z_ranges(z0: int, z1: int, ranges: Iterable[tuple[int, int]]) -> bool:
    """Whether an inclusive stack window contains an excluded z slice."""
    return any(z0 <= end and start <= z1 for start, end in ranges)


def vlm_included_z_slices(z0: int, z1: int, ranges: Iterable[tuple[int, int]]) -> list[int]:
    """Keep usable slices when a stack window straddles an excluded boundary region."""
    excluded = tuple(ranges)
    return [z for z in range(z0, z1 + 1) if not any(start <= z <= end for start, end in excluded)]


def run_stackwise_detector(config: StackwiseConfig) -> dict[str, Any]:
    """Measure every registered strut and visually review every strut intersecting each window."""
    validate_window(config.stack_size, config.stride)
    if config.evidence_grid_size not in (1, 2, 3):
        raise ValueError("evidence_grid_size must be 1 (full slice), 2 (four quarters), or 3 (nine tiles)")
    if config.evidence_quadrant is not None and config.evidence_grid_size != 1:
        raise ValueError("evidence_quadrant and evidence_grid_size cannot both select a crop")
    if config.max_vlm_candidates_per_window is not None and config.max_vlm_candidates_per_window < 1:
        raise ValueError("max_vlm_candidates_per_window must be at least 1 when provided")
    if config.max_vlm_batches is not None and config.max_vlm_batches < 1:
        raise ValueError("max_vlm_batches must be at least 1 when provided")
    if any(start < 0 or end < start for start, end in config.vlm_excluded_z_ranges):
        raise ValueError("vlm_excluded_z_ranges must contain non-negative inclusive start:end pairs")
    raw, mask = open_volume(config.raw_tif, "Raw TIFF"), open_volume(config.segmentation_tif, "Segmentation TIFF")
    skeleton = open_volume(config.skeleton_tif, "Skeleton TIFF") if config.skeleton_tif else None
    if raw.shape != mask.shape or (skeleton is not None and skeleton.shape != raw.shape): raise ValueError("Raw, segmentation, and skeleton TIFF dimensions must match (z, y, x)")
    evidence_crop_xyxy = evidence_crop_bounds((raw.shape[1], raw.shape[2]), config.evidence_quadrant)
    geometry, junctions = load_geometry(config.geometry_json)
    token = provider_token() if config.use_providers else None
    preflight_models(config)
    for name in ("agent1_triage", "agent2_adjudications", "stacks", "overlays", "clean_stacks", "whole_slices", "candidate_crops", "candidate_indexes"): (config.output_dir / name).mkdir(parents=True, exist_ok=True)
    limits = percentile_limits(raw); windows = stack_windows(raw.shape[0], config.stack_size, config.stride)
    if config.representative_validation and windows: windows = [windows[i] for i in sorted(set([0, len(windows)//2, len(windows)-1]))]
    if config.center_z is not None:
        windows = [window for window in windows if (window[0] + window[1]) // 2 == config.center_z]
        if not windows:
            raise ValueError(f"No stack window is centered at z={config.center_z}")
    if config.max_stacks is not None: windows = windows[:config.max_stacks]
    aggregates: dict[int, dict[str, Any]] = {}; failures = config.output_dir / "failures.jsonl"
    failures.unlink(missing_ok=True)
    candidates: dict[int, dict[str, Any]] = {}
    vlm_jobs: dict[int, dict[str, Any]] = {}
    agent2_assessments_by_id: dict[int, dict[str, Any]] = {}
    coverage = {"window_count": len(windows), "measured_record_count": 0, "candidate_observation_count": 0, "vlm_trimmed_window_count": 0, "vlm_fully_excluded_window_count": 0, "agent1_triage_window_count": 0, "vlm_batch_count": 0, "agent2_assessment_count": 0}
    per_stack_handle = (config.output_dir / "per_stack_records.jsonl").open("w", encoding="utf-8")
    for z0, z1 in windows:
        stack_id = f"stack_{z0:04d}_{z1:04d}"; targets = struts_intersecting_z(geometry["struts"], junctions, z0, z1)
        try:
            context = window_measurement_context(mask, z0, z1)
            measured = [measure_strut(s, junctions, raw, mask, skeleton, z0, z1, limits, context) for s in targets]
            baselines = robust_baselines(measured)
            shape_baselines = robust_shape_baselines(measured)
            for record in measured:
                group_key = (record["orientation_bucket"], int(record["length_voxels"] // 15))
                baseline = baselines.get(group_key)
                label, confidence, reason = decision_from_measurement(record, baseline, shape_baselines.get(group_key))
                record.update({"scan_id": config.raw_tif.stem, "stack_id": stack_id, "stack_range": [z0, z1], "target_slice": (z0 + z1)//2, "classification": label, "confidence": confidence, "reason": reason, "full_span_observation": min(record["start_xyz"][2], record["end_xyz"][2]) >= z0 and max(record["start_xyz"][2], record["end_xyz"][2]) <= z1})
            candidate_records = sorted((record for record in measured if record["classification"] != "normal"), key=candidate_score, reverse=True)
            coverage["measured_record_count"] += len(measured)
            coverage["candidate_observation_count"] += len(candidate_records)
            evidence_z_slices = vlm_included_z_slices(z0, z1, config.vlm_excluded_z_ranges)
            if len(evidence_z_slices) < config.stack_size:
                coverage["vlm_trimmed_window_count"] += 1
            if not evidence_z_slices:
                coverage["vlm_fully_excluded_window_count"] += 1
            for record in candidate_records:
                summary = candidate_summary(record)
                prior = candidates.get(summary["strut_id"])
                if prior is None or summary["candidate_score"] > prior["candidate_score"]:
                    candidates[summary["strut_id"]] = summary
            # The VLM queue includes every registered strut that intersects this
            # window. Deterministic classes remain audit data only and do not gate
            # visual review.
            if evidence_z_slices:
                for record in measured:
                    job = vlm_jobs.setdefault(int(record["strut_id"]), {"record": record, "supporting_stack_ids": [], "evidence_z_slices": evidence_z_slices})
                    job["supporting_stack_ids"].append(stack_id)
                    if candidate_selection_key(record) > candidate_selection_key(job["record"]):
                        job["record"] = record
                        job["evidence_z_slices"] = evidence_z_slices
            for record in measured:
                record["agent2_final_assessment"] = agent2_assessments_by_id.get(int(record["strut_id"]))
            (config.output_dir / "stacks" / f"{stack_id}.json").write_text(json.dumps(measured, indent=2), encoding="utf-8")
            for record in measured:
                per_stack_handle.write(json.dumps(record) + "\n")
                accumulate_record(aggregates, record)
            per_stack_handle.flush()
        except Exception as exc:
            with failures.open("a", encoding="utf-8") as handle: handle.write(json.dumps({"stack_id": stack_id, "error": str(exc), "traceback": traceback.format_exc()}) + "\n")
    per_stack_handle.close()
    struts_by_id = {int(strut["id"]): strut for strut in geometry["struts"]}
    visible_vlm_target_ids = {
        strut_id for strut_id, job in vlm_jobs.items()
        if record_in_evidence_crop(job["record"], struts_by_id, junctions, evidence_crop_xyxy)
    }
    jobs_by_stack: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for strut_id, job in vlm_jobs.items():
        selected = job["record"]
        jobs_by_stack[str(selected["stack_id"])].append(job)
    for source_stack_id, jobs in sorted(jobs_by_stack.items()):
        # Every registered strut intersecting the window is retained; use a stable
        # ID order only to paginate full visual review.
        jobs = [job for job in jobs if record_in_evidence_crop(job["record"], struts_by_id, junctions, evidence_crop_xyxy)]
        jobs.sort(key=lambda job: row_column_key(job["record"], struts_by_id, junctions))
        batch_width = config.max_vlm_candidates_per_window or len(jobs)
        for batch_index, batch_start in enumerate(range(0, len(jobs), batch_width)):
            if config.max_vlm_batches is not None and coverage["vlm_batch_count"] >= config.max_vlm_batches:
                break
            batch_jobs = jobs[batch_start:batch_start + batch_width]
            selected_records = [job["record"] for job in batch_jobs]
            z0, z1 = selected_records[0]["stack_range"]
            evidence_z_slices = batch_jobs[0]["evidence_z_slices"]
            batch_id = f"{source_stack_id}_batch_{batch_index:03d}"
            batch_targets = [struts_by_id[int(record["strut_id"])] for record in selected_records]
            agent1_panels: list[tuple[str, Path]] = []
            if config.render_evidence:
                for z in evidence_z_slices:
                    agent1_panels.extend(_export_original_slice_images(config.output_dir / "whole_slices", batch_id, z, raw, mask, skeleton, config.evidence_quadrant, config.evidence_grid_size))
            instruction = agent1_contract(batch_id, z0, z1, batch_targets, geometry, junctions, evidence_z_slices, evidence_crop_xyxy)
            instruction["source_stack_id"] = source_stack_id
            instruction["batch_index"] = batch_index
            instruction["vlm_evidence_z_slices"] = evidence_z_slices
            instruction["evidence_quadrant"] = config.evidence_quadrant or "full_slice"
            instruction["evidence_grid_size"] = config.evidence_grid_size
            instruction["row_column_ordering"] = "Entries are ordered by increasing expected y (row), then increasing expected x (column), using the nominal registered location at the target slice."
            instruction["agent1_evidence_panels"] = [{"description": description, "path": str(path)} for description, path in agent1_panels]
            if config.use_providers:
                if not agent1_panels:
                    raise ValueError("Provider calls require rendered clean whole-slice evidence panels")
                instruction["agent1_analysis"] = _provider_stack_request(config.agent1_model, instruction, agent1_panels, token)
            else:
                instruction["agent1_analysis"] = {"status": "providers_disabled"}
            coverage["agent1_triage_window_count"] += 1
            coverage["vlm_batch_count"] += 1
            pair_to_strut_id = {_junction_pair(target): int(target["id"]) for target in batch_targets}
            review_pairs = parse_agent1_review_pairs(instruction["agent1_analysis"], pair_to_strut_id)
            review_targets = [struts_by_id[pair_to_strut_id[pair]] for pair in review_pairs]
            agent2_panels = list(agent1_panels)
            if config.render_evidence and review_targets:
                index_panel = config.output_dir / "candidate_indexes" / f"{batch_id}.png"
                _render_candidate_index_panel(index_panel, review_targets, z0, z1)
                agent2_panels.append(("Text-only candidate index; maps crop number to its registered junction pair and is not material evidence.", index_panel))
                if config.evidence_quadrant is None:
                    for candidate_number, target in enumerate(review_targets, start=1):
                        crop_box = _candidate_crop_box(target, junctions, raw)
                        for z in evidence_z_slices:
                            crop_panel = config.output_dir / "candidate_crops" / f"{batch_id}_candidate_{candidate_number:02d}_z{z:04d}.png"
                            _render_candidate_slice_panel(crop_panel, raw, mask, skeleton, crop_box, z, limits)
                            agent2_panels.append((f"Agent 1-nominated connection {candidate_number}, clean crop at z={z}; use the index to obtain its registered junction pair.", crop_panel))
            instruction["agent1_nominated_review_junction_pairs"] = [{"junction0_id": pair[0], "junction1_id": pair[1]} for pair in review_pairs]
            instruction["agent2_evidence_panels"] = [{"description": description, "path": str(path)} for description, path in agent2_panels]
            (config.output_dir / "agent1_triage" / f"{batch_id}.json").write_text(json.dumps(instruction, indent=2), encoding="utf-8")
            agent2_request = agent2_adjudication_contract(batch_id, instruction)
            agent2_request["review_junction_pairs"] = [{"junction0_id": pair[0], "junction1_id": pair[1]} for pair in review_pairs]
            agent2_request["evidence_panels"] = instruction["agent2_evidence_panels"]
            agent2_adjudication = _provider_stack_request(config.agent2_model, agent2_request, agent2_panels, token) if config.use_providers and review_pairs else {"status": "no_agent1_nominations" if config.use_providers else "providers_disabled"}
            agent2_assessments = parse_agent2_assessments(agent2_adjudication, review_pairs)
            for assessment in agent2_assessments:
                pair = assessment["junction0_id"], assessment["junction1_id"]
                agent2_assessments_by_id[pair_to_strut_id[pair]] = assessment
            coverage["agent2_assessment_count"] += len(agent2_assessments)
            (config.output_dir / "agent2_adjudications" / f"{batch_id}.json").write_text(json.dumps({"stack_id": source_stack_id, "batch_id": batch_id, "status": "adjudicated", "agent2_adjudication_request": agent2_request, "provider_response": agent2_adjudication, "final_assessments": agent2_assessments}, indent=2), encoding="utf-8")
    merged = finalize_aggregates(aggregates)
    for record in merged:
        record["agent2_final_assessment"] = agent2_assessments_by_id.get(int(record["strut_id"]))
    coverage.update({"unique_measured_struts": len(merged), "unique_candidate_struts": len(candidates), "unique_vlm_target_struts": len(vlm_jobs), "unique_vlm_evidence_region_target_struts": len(visible_vlm_target_ids), "unadjudicated_vlm_target_struts": len(visible_vlm_target_ids - set(agent2_assessments_by_id))})
    (config.output_dir / "candidate_struts.json").write_text(json.dumps(sorted(candidates.values(), key=lambda item: (-item["candidate_score"], item["strut_id"])), indent=2), encoding="utf-8")
    (config.output_dir / "coverage_report.json").write_text(json.dumps(coverage, indent=2), encoding="utf-8")
    result = {"status": "passed" if not failures.exists() else "completed_with_failures", "metadata": {"workflow": "registered_geometry_all_struts_then_vlm", "clustering": "not used", "agent1_model": config.agent1_model, "agent2_model": config.agent2_model, "agent1_role": "all-registered-struts visual missing triage", "agent2_role": "missing-only final adjudicator", "vlm_labels": list(MISSING_VLM_LABELS), "stack_size": config.stack_size, "stride": config.stride, "labels": list(LABELS)}, "coverage": coverage, "per_strut_records": merged}
    (config.output_dir / "merged_per_strut_results.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Two-agent stackwise registered-strut detector")
    parser.add_argument("--raw-tif", type=Path, default=DEFAULT_RAW); parser.add_argument("--segmentation-tif", type=Path, default=DEFAULT_MASK)
    parser.add_argument("--skeleton-tif", type=Path, default=DEFAULT_SKELETON); parser.add_argument("--geometry-json", type=Path, default=DEFAULT_GEOMETRY)
    parser.add_argument("--no-skeleton", action="store_true", help="Do not load skeleton evidence.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT); parser.add_argument("--stack-size", type=int, default=7); parser.add_argument("--stride", type=int, default=1)
    parser.add_argument("--agent1-model", default=AGENT1_MODEL); parser.add_argument("--agent2-model", default=AGENT2_MODEL); parser.add_argument("--representative-validation", action="store_true"); parser.add_argument("--max-stacks", type=int); parser.add_argument("--center-z", type=int, help="Run only the window centered on this z slice."); parser.add_argument("--max-vlm-candidates-per-window", type=int, help="Optional explicit pagination size; by default Agent 1 sees every connection in the evidence region."); parser.add_argument("--max-vlm-batches", type=int, help="Cap VLM batches for a bounded test run."); parser.add_argument("--vlm-exclude-z", action="append", default=[], metavar="START:END", help="Inclusive z range excluded from VLM rendering and calls; repeatable. Default excludes 1:26 and 740:761."); parser.add_argument("--evidence-quadrant", choices=("top_right",), help="Send only the selected source-image quadrant to both VLMs."); parser.add_argument("--evidence-grid", type=int, choices=(1, 2, 3), default=2, help="Split each VLM source slice into a 1x1 full slice, 2x2 four-quarter grid (default), or 3x3 nine-tile grid."); parser.add_argument("--no-providers", action="store_true"); parser.add_argument("--no-render-evidence", action="store_true", help="Skip PNG rendering for a numeric-only deterministic baseline.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    try:
        excluded_ranges = tuple(tuple(int(value) for value in item.split(":", 1)) for item in args.vlm_exclude_z) or DEFAULT_VLM_EXCLUDED_Z_RANGES
    except ValueError as exc:
        raise ValueError("--vlm-exclude-z must use START:END, for example 740:761") from exc
    result = run_stackwise_detector(StackwiseConfig(raw_tif=args.raw_tif, segmentation_tif=args.segmentation_tif, skeleton_tif=None if args.no_skeleton else args.skeleton_tif, geometry_json=args.geometry_json, output_dir=args.output_dir, stack_size=args.stack_size, stride=args.stride, agent1_model=args.agent1_model, agent2_model=args.agent2_model, representative_validation=args.representative_validation, max_stacks=args.max_stacks, center_z=args.center_z, max_vlm_candidates_per_window=args.max_vlm_candidates_per_window, max_vlm_batches=args.max_vlm_batches, vlm_excluded_z_ranges=excluded_ranges, evidence_quadrant=args.evidence_quadrant, evidence_grid_size=1 if args.evidence_quadrant else args.evidence_grid, use_providers=not args.no_providers, render_evidence=not args.no_render_evidence))
    print(json.dumps({"status": result["status"], "output": str(args.output_dir / "merged_per_strut_results.json")}))


if __name__ == "__main__": main()
