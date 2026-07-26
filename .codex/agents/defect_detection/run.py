from __future__ import annotations

import base64
import json
import math
import os
import re
import struct
import zlib
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import requests


PROJECT_ROOT = Path(__file__).resolve().parents[3]
ANALYSIS_DIR = PROJECT_ROOT / "data" / "missing_struts" / "analysis"
REFERENCE_JSON = (
    PROJECT_ROOT
    / "data"
    / "missing_struts"
    / "registered_jsons"
    / "210127_Brian_Tran_strut_lattices_0point5dash1 1 Slices.json"
)
OBSERVED_JSON = ANALYSIS_DIR / "observed_lattice.json"
PER_STRUT_JSON = ANALYSIS_DIR / "per_strut_defects.json"
SUMMARY_JSON = ANALYSIS_DIR / "anomaly_summary.json"
SUMMARY_MD = ANALYSIS_DIR / "anomaly_summary.md"
VISUAL_DIR = ANALYSIS_DIR / "defect_visual_review"
VISUAL_INDEX_JSON = VISUAL_DIR / "visual_review_index.json"
HF_MODEL_REVIEW_JSON = VISUAL_DIR / "hf_model_review_results.json"

SEARCH_RADIUS = 12.0
SAMPLE_COUNT = 11
MAX_VISUAL_PANELS = 100
HF_MODEL = os.environ.get("DEFECT_HF_MODEL", "zai-org/GLM-4.5V")
HF_REVIEW_LIMIT = int(os.environ.get("DEFECT_HF_REVIEW_LIMIT", "0"))
PROFILE_SEGMENTS = 20
LOW_PROFILE_THRESHOLD = 0.20


def distance(a: list[float], b: list[float]) -> float:
    return math.sqrt(sum((float(x) - float(y)) ** 2 for x, y in zip(a, b)))


def interpolate(a: list[float], b: list[float], fraction: float) -> list[float]:
    return [float(x) + (float(y) - float(x)) * fraction for x, y in zip(a, b)]


def cell_for(point: list[float], cell_size: float) -> tuple[int, int, int]:
    return tuple(math.floor(float(value) / cell_size) for value in point)


def neighbor_cells(cell: tuple[int, int, int]) -> list[tuple[int, int, int]]:
    cx, cy, cz = cell
    return [
        (cx + dx, cy + dy, cz + dz)
        for dx in (-1, 0, 1)
        for dy in (-1, 0, 1)
        for dz in (-1, 0, 1)
    ]


def build_observed_index(observed: dict[str, Any], radius: float) -> dict[tuple[int, int, int], list[tuple[list[float], int]]]:
    index: dict[tuple[int, int, int], list[tuple[list[float], int]]] = defaultdict(list)
    for strut in observed["struts"]:
        strut_id = int(strut["id"])
        for point in strut.get("points", []):
            index[cell_for(point, radius)].append(([float(v) for v in point], strut_id))
    return index


def nearby_observed(
    point: list[float],
    index: dict[tuple[int, int, int], list[tuple[list[float], int]]],
    radius: float,
) -> tuple[bool, float | None, set[int]]:
    nearest: float | None = None
    nearby_struts: set[int] = set()
    for cell in neighbor_cells(cell_for(point, radius)):
        for observed_point, observed_strut_id in index.get(cell, []):
            d = distance(point, observed_point)
            if nearest is None or d < nearest:
                nearest = d
            if d <= radius:
                nearby_struts.add(observed_strut_id)
    return bool(nearby_struts), nearest, nearby_struts


def longest_true_run(values: list[bool]) -> int:
    longest = 0
    current = 0
    for value in values:
        if value:
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    return longest


def strut_material_profile(
    start: list[float],
    end: list[float],
    observed_index: dict[tuple[int, int, int], list[tuple[list[float], int]]],
) -> dict[str, Any]:
    segment_values = []
    nearest_distances = []
    for segment in range(PROFILE_SEGMENTS):
        fraction = (segment + 0.5) / PROFILE_SEGMENTS
        point = interpolate(start, end, fraction)
        hit, nearest, nearby_struts = nearby_observed(point, observed_index, SEARCH_RADIUS)
        if nearest is None:
            value = 0.0
        else:
            value = max(0.0, 1.0 - min(nearest, SEARCH_RADIUS) / SEARCH_RADIUS)
        if hit:
            value = max(value, min(1.0, 0.50 + 0.10 * len(nearby_struts)))
        segment_values.append(value)
        nearest_distances.append(nearest)

    low_segments = [
        index for index, value in enumerate(segment_values)
        if value < LOW_PROFILE_THRESHOLD
    ]
    low_flags = [value < LOW_PROFILE_THRESHOLD for value in segment_values]
    endpoint_mean = (
        sum(segment_values[:2] + segment_values[-2:]) / 4
        if len(segment_values) >= 4
        else sum(segment_values) / len(segment_values)
    )
    middle_values = segment_values[2:-2] if len(segment_values) > 4 else segment_values
    middle_min = min(middle_values) if middle_values else min(segment_values)
    mean_value = sum(segment_values) / len(segment_values)
    longest_low_gap = longest_true_run(low_flags)
    if mean_value <= LOW_PROFILE_THRESHOLD:
        profile_classification = "missing"
        profile_reason = "material profile is low across the expected strut"
    elif endpoint_mean >= 0.45 and longest_low_gap >= 2 and middle_min < LOW_PROFILE_THRESHOLD:
        profile_classification = "broken"
        profile_reason = "endpoints have support but one or more middle segments drop below threshold"
    elif mean_value < 0.55 or longest_low_gap:
        profile_classification = "weak"
        profile_reason = "profile has partial support or isolated low-support segments"
    else:
        profile_classification = "continuous"
        profile_reason = "profile remains supported along the expected strut"

    return {
        "profile_segments": PROFILE_SEGMENTS,
        "profile_values": [round(value, 4) for value in segment_values],
        "profile_mean": mean_value,
        "profile_min": min(segment_values),
        "profile_endpoint_mean": endpoint_mean,
        "profile_middle_min": middle_min,
        "low_profile_threshold": LOW_PROFILE_THRESHOLD,
        "low_profile_segments": low_segments,
        "longest_low_profile_gap": longest_low_gap,
        "profile_classification": profile_classification,
        "profile_reason": profile_reason,
        "profile_nearest_distances": [
            None if value is None else round(float(value), 4)
            for value in nearest_distances
        ],
    }


def classify_strut(
    reference_strut: dict[str, Any],
    reference_junctions: dict[int, list[float]],
    observed_index: dict[tuple[int, int, int], list[tuple[list[float], int]]],
) -> dict[str, Any]:
    start = reference_junctions[int(reference_strut["junction0"])]
    end = reference_junctions[int(reference_strut["junction1"])]
    samples = [
        interpolate(start, end, i / (SAMPLE_COUNT - 1))
        for i in range(SAMPLE_COUNT)
    ]

    hits = 0
    nearest_distances = []
    endpoint_strut_sets = []
    for i, point in enumerate(samples):
        hit, nearest, nearby_struts = nearby_observed(point, observed_index, SEARCH_RADIUS)
        if hit:
            hits += 1
        if nearest is not None:
            nearest_distances.append(nearest)
        if i in (0, SAMPLE_COUNT - 1):
            endpoint_strut_sets.append(nearby_struts)

    coverage = hits / SAMPLE_COUNT
    endpoint_hits = sum(1 for struts in endpoint_strut_sets if struts)
    shared_endpoint_struts = (
        endpoint_strut_sets[0].intersection(endpoint_strut_sets[1])
        if len(endpoint_strut_sets) == 2
        else set()
    )
    skeleton_connected = bool(shared_endpoint_struts)
    mean_nearest_distance = (
        sum(nearest_distances) / len(nearest_distances)
        if nearest_distances
        else None
    )
    profile = strut_material_profile(start, end, observed_index)

    if profile["profile_classification"] == "missing":
        classification = "missing"
        reason = profile["profile_reason"]
    elif profile["profile_classification"] == "broken":
        classification = "disconnected"
        reason = profile["profile_reason"]
    elif coverage >= 0.65 and skeleton_connected and profile["profile_classification"] == "continuous":
        classification = "present"
        reason = "sufficient skeleton coverage and one observed path is near both expected endpoints"
    elif coverage <= 0.10:
        classification = "missing"
        reason = "almost no observed skeleton points lie near the expected strut line"
    elif coverage >= 0.25 and not skeleton_connected:
        classification = "disconnected"
        reason = "skeleton material is nearby, but no observed path connects both expected endpoints"
    else:
        classification = "weak"
        reason = "partial skeleton coverage is present but below the acceptance threshold"

    return {
        "strut_id": int(reference_strut["id"]),
        "classification": classification,
        "coverage_ratio": coverage,
        "sample_hits": hits,
        "sample_count": SAMPLE_COUNT,
        "endpoint_hits": endpoint_hits,
        "skeleton_connected": skeleton_connected,
        "mean_nearest_observed_distance": mean_nearest_distance,
        "search_radius_voxels": SEARCH_RADIUS,
        "reason": reason,
        **profile,
        "junction0": int(reference_strut["junction0"]),
        "junction1": int(reference_strut["junction1"]),
    }


def candidate_priority(record: dict[str, Any]) -> tuple[int, float]:
    class_rank = {
        "missing": 0,
        "weak": 1,
        "disconnected": 2,
        "present": 3,
    }
    return (
        class_rank.get(record["classification"], 9),
        float(record["coverage_ratio"]),
    )


def collect_nearby_points(
    start: list[float],
    end: list[float],
    index: dict[tuple[int, int, int], list[tuple[list[float], int]]],
    radius: float,
) -> list[list[float]]:
    points_by_key: dict[tuple[int, int, int], list[float]] = {}
    for i in range(SAMPLE_COUNT):
        sample = interpolate(start, end, i / (SAMPLE_COUNT - 1))
        for cell in neighbor_cells(cell_for(sample, radius)):
            for observed_point, _observed_strut_id in index.get(cell, []):
                if distance(sample, observed_point) <= radius:
                    key = tuple(round(value) for value in observed_point)
                    points_by_key[key] = observed_point
    return list(points_by_key.values())


def scale_point(
    point: list[float],
    min_a: float,
    max_a: float,
    min_b: float,
    max_b: float,
    width: int,
    height: int,
) -> tuple[float, float]:
    span_a = max(max_a - min_a, 1.0)
    span_b = max(max_b - min_b, 1.0)
    x = 30 + (float(point[0]) - min_a) / span_a * (width - 60)
    y = height - 30 - (float(point[1]) - min_b) / span_b * (height - 60)
    return x, y


def write_visual_panel(
    record: dict[str, Any],
    start: list[float],
    end: list[float],
    observed_points: list[list[float]],
) -> dict[str, str]:
    width = 720
    height = 360
    margin = SEARCH_RADIUS * 2
    all_points = [start, end, *observed_points]
    xs = [point[0] for point in all_points]
    ys = [point[1] for point in all_points]
    zs = [point[2] for point in all_points]
    min_x, max_x = min(xs) - margin, max(xs) + margin
    min_y, max_y = min(ys) - margin, max(ys) + margin
    min_z, max_z = min(zs) - margin, max(zs) + margin

    xy_start = scale_point([start[0], start[1]], min_x, max_x, min_y, max_y, width // 2, height)
    xy_end = scale_point([end[0], end[1]], min_x, max_x, min_y, max_y, width // 2, height)
    xz_start = scale_point([start[0], start[2]], min_x, max_x, min_z, max_z, width // 2, height)
    xz_end = scale_point([end[0], end[2]], min_x, max_x, min_z, max_z, width // 2, height)

    def circle_xy(point: list[float]) -> str:
        x, y = scale_point([point[0], point[1]], min_x, max_x, min_y, max_y, width // 2, height)
        return f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3" fill="#2563eb" opacity="0.65" />'

    def circle_xz(point: list[float]) -> str:
        x, y = scale_point([point[0], point[2]], min_x, max_x, min_z, max_z, width // 2, height)
        return f'<circle cx="{x + width // 2:.1f}" cy="{y:.1f}" r="3" fill="#2563eb" opacity="0.65" />'

    color = {
        "missing": "#dc2626",
        "weak": "#d97706",
        "disconnected": "#7c3aed",
        "present": "#16a34a",
    }.get(record["classification"], "#111827")
    panel_path = VISUAL_DIR / f"strut_{record['strut_id']:05d}_{record['classification']}.svg"
    png_path = VISUAL_DIR / f"strut_{record['strut_id']:05d}_{record['classification']}.png"
    profile_path = VISUAL_DIR / f"strut_{record['strut_id']:05d}_{record['classification']}_profile.svg"
    svg = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="720" height="360" viewBox="0 0 720 360">',
        '<rect width="720" height="360" fill="#ffffff" />',
        '<line x1="360" y1="0" x2="360" y2="360" stroke="#d1d5db" />',
        '<text x="24" y="28" font-family="monospace" font-size="16" fill="#111827">XY view</text>',
        '<text x="384" y="28" font-family="monospace" font-size="16" fill="#111827">XZ view</text>',
        (
            f'<text x="24" y="344" font-family="monospace" font-size="13" fill="#111827">'
            f"strut {record['strut_id']} | {record['classification']} | "
            f"coverage {record['coverage_ratio']:.2f} | connected {record['skeleton_connected']}"
            "</text>"
        ),
        *[circle_xy(point) for point in observed_points],
        *[circle_xz(point) for point in observed_points],
        (
            f'<line x1="{xy_start[0]:.1f}" y1="{xy_start[1]:.1f}" '
            f'x2="{xy_end[0]:.1f}" y2="{xy_end[1]:.1f}" stroke="{color}" '
            'stroke-width="5" stroke-linecap="round" />'
        ),
        (
            f'<line x1="{xz_start[0] + width // 2:.1f}" y1="{xz_start[1]:.1f}" '
            f'x2="{xz_end[0] + width // 2:.1f}" y2="{xz_end[1]:.1f}" stroke="{color}" '
            'stroke-width="5" stroke-linecap="round" />'
        ),
        '</svg>',
    ]
    panel_path.write_text("\n".join(svg), encoding="utf-8")
    write_profile_plot(profile_path, record)
    write_png_panel(
        png_path,
        width,
        height,
        color,
        xy_start,
        xy_end,
        (xz_start[0] + width // 2, xz_start[1]),
        (xz_end[0] + width // 2, xz_end[1]),
        [scale_point([point[0], point[1]], min_x, max_x, min_y, max_y, width // 2, height) for point in observed_points],
        [(scale_point([point[0], point[2]], min_x, max_x, min_z, max_z, width // 2, height)[0] + width // 2,
          scale_point([point[0], point[2]], min_x, max_x, min_z, max_z, width // 2, height)[1]) for point in observed_points],
    )
    return {
        "svg": str(panel_path.relative_to(PROJECT_ROOT)),
        "png": str(png_path.relative_to(PROJECT_ROOT)),
        "profile_svg": str(profile_path.relative_to(PROJECT_ROOT)),
    }


def write_profile_plot(path: Path, record: dict[str, Any]) -> None:
    width = 720
    height = 220
    values = record["profile_values"]
    points = []
    for index, value in enumerate(values):
        x = 40 + index / max(len(values) - 1, 1) * (width - 80)
        y = height - 40 - float(value) * (height - 80)
        points.append((x, y))
    polyline = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
    threshold_y = height - 40 - LOW_PROFILE_THRESHOLD * (height - 80)
    bars = []
    bar_width = (width - 80) / len(values)
    for index, value in enumerate(values):
        x = 40 + index * bar_width
        y = height - 40 - float(value) * (height - 80)
        color = "#dc2626" if value < LOW_PROFILE_THRESHOLD else "#2563eb"
        bars.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_width - 2:.1f}" '
            f'height="{height - 40 - y:.1f}" fill="{color}" opacity="0.35" />'
        )
    svg = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="720" height="220" viewBox="0 0 720 220">',
        '<rect width="720" height="220" fill="#ffffff" />',
        '<line x1="40" y1="180" x2="680" y2="180" stroke="#9ca3af" />',
        '<line x1="40" y1="40" x2="40" y2="180" stroke="#9ca3af" />',
        f'<line x1="40" y1="{threshold_y:.1f}" x2="680" y2="{threshold_y:.1f}" stroke="#dc2626" stroke-dasharray="5 5" />',
        *bars,
        f'<polyline points="{polyline}" fill="none" stroke="#111827" stroke-width="2" />',
        (
            f'<text x="40" y="24" font-family="monospace" font-size="14" fill="#111827">'
            f"strut {record['strut_id']} profile | {record['profile_classification']} | "
            f"mean {record['profile_mean']:.2f} | longest low gap {record['longest_low_profile_gap']}"
            "</text>"
        ),
        '<text x="40" y="206" font-family="monospace" font-size="12" fill="#4b5563">node x</text>',
        '<text x="630" y="206" font-family="monospace" font-size="12" fill="#4b5563">node y</text>',
        '</svg>',
    ]
    path.write_text("\n".join(svg), encoding="utf-8")


def hex_to_rgb(color: str) -> tuple[int, int, int]:
    color = color.lstrip("#")
    return tuple(int(color[i : i + 2], 16) for i in (0, 2, 4))


def set_pixel(image: bytearray, width: int, height: int, x: int, y: int, color: tuple[int, int, int]) -> None:
    if 0 <= x < width and 0 <= y < height:
        offset = (y * width + x) * 3
        image[offset : offset + 3] = bytes(color)


def draw_circle(image: bytearray, width: int, height: int, cx: float, cy: float, radius: int, color: tuple[int, int, int]) -> None:
    x0 = int(round(cx))
    y0 = int(round(cy))
    for y in range(y0 - radius, y0 + radius + 1):
        for x in range(x0 - radius, x0 + radius + 1):
            if (x - x0) ** 2 + (y - y0) ** 2 <= radius ** 2:
                set_pixel(image, width, height, x, y, color)


def draw_line(image: bytearray, width: int, height: int, start: tuple[float, float], end: tuple[float, float], color: tuple[int, int, int], thickness: int = 5) -> None:
    x0, y0 = start
    x1, y1 = end
    steps = max(int(abs(x1 - x0)), int(abs(y1 - y0)), 1)
    for i in range(steps + 1):
        t = i / steps
        x = x0 + (x1 - x0) * t
        y = y0 + (y1 - y0) * t
        draw_circle(image, width, height, x, y, thickness // 2, color)


def write_png(path: Path, width: int, height: int, image: bytearray) -> None:
    def chunk(kind: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + kind
            + data
            + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
        )

    rows = []
    stride = width * 3
    for y in range(height):
        rows.append(b"\x00" + bytes(image[y * stride : (y + 1) * stride]))
    png = [
        b"\x89PNG\r\n\x1a\n",
        chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)),
        chunk(b"IDAT", zlib.compress(b"".join(rows), level=6)),
        chunk(b"IEND", b""),
    ]
    path.write_bytes(b"".join(png))


def write_png_panel(
    path: Path,
    width: int,
    height: int,
    line_color: str,
    xy_start: tuple[float, float],
    xy_end: tuple[float, float],
    xz_start: tuple[float, float],
    xz_end: tuple[float, float],
    xy_points: list[tuple[float, float]],
    xz_points: list[tuple[float, float]],
) -> None:
    image = bytearray([255, 255, 255] * width * height)
    gray = (209, 213, 219)
    blue = (37, 99, 235)
    line = hex_to_rgb(line_color)
    draw_line(image, width, height, (width // 2, 0), (width // 2, height), gray, thickness=1)
    for point in xy_points + xz_points:
        draw_circle(image, width, height, point[0], point[1], 3, blue)
    draw_line(image, width, height, xy_start, xy_end, line, thickness=5)
    draw_line(image, width, height, xz_start, xz_end, line, thickness=5)
    write_png(path, width, height, image)


def visual_classify(record: dict[str, Any], observed_points: list[list[float]]) -> tuple[str, float, str]:
    coverage = float(record["coverage_ratio"])
    connected = bool(record["skeleton_connected"])
    if coverage <= 0.10 and not observed_points:
        return "missing", 0.95, "visual panel shows no observed skeleton points near the expected strut"
    if coverage <= 0.10:
        return "missing", 0.85, "visual panel shows only sparse observed points near the expected strut"
    if coverage >= 0.65 and not connected:
        return "disconnected", 0.80, "visual panel shows material near the expected line but no endpoint-connecting path"
    if coverage < 0.65:
        return "weak", 0.75, "visual panel shows partial observed skeleton coverage near the expected strut"
    return "present", 0.70, "visual panel shows substantial observed skeleton coverage"


def add_visual_review(
    per_strut: list[dict[str, Any]],
    reference_struts: list[dict[str, Any]],
    reference_junctions: dict[int, list[float]],
    observed_index: dict[tuple[int, int, int], list[tuple[list[float], int]]],
) -> list[dict[str, Any]]:
    VISUAL_DIR.mkdir(parents=True, exist_ok=True)
    struts_by_id = {int(strut["id"]): strut for strut in reference_struts}
    candidates = [
        record for record in per_strut
        if record["classification"] != "present"
    ]
    candidates.sort(key=candidate_priority)
    reviewed = []
    for record in candidates[:MAX_VISUAL_PANELS]:
        strut = struts_by_id[int(record["strut_id"])]
        start = reference_junctions[int(strut["junction0"])]
        end = reference_junctions[int(strut["junction1"])]
        observed_points = collect_nearby_points(start, end, observed_index, SEARCH_RADIUS)
        panel_paths = write_visual_panel(record, start, end, observed_points)
        visual_label, confidence, reason = visual_classify(record, observed_points)
        record["visual_evidence"] = panel_paths["svg"]
        record["visual_evidence_png"] = panel_paths["png"]
        record["profile_plot"] = panel_paths["profile_svg"]
        record["visual_classification"] = visual_label
        record["visual_confidence"] = confidence
        record["visual_reason"] = reason
        record["visual_nearby_point_count"] = len(observed_points)
        reviewed.append(record)

    VISUAL_INDEX_JSON.write_text(
        json.dumps(
            {
                "visual_panel_count": len(reviewed),
                "max_visual_panels": MAX_VISUAL_PANELS,
                "panels": [
                    {
                        "strut_id": record["strut_id"],
                        "classification": record["classification"],
                        "visual_classification": record["visual_classification"],
                        "visual_confidence": record["visual_confidence"],
                        "visual_evidence": record["visual_evidence"],
                        "visual_evidence_png": record["visual_evidence_png"],
                        "profile_plot": record["profile_plot"],
                    }
                    for record in reviewed
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return reviewed


def parse_hf_json(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:].strip()
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        text = text[start : end + 1]
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        label_match = re.search(r'"label"\s*:\s*"([^"]+)"', text)
        confidence_match = re.search(r'"confidence"\s*:\s*([0-9.]+)', text)
        reason_match = re.search(r'"reason"\s*:\s*"([^"]+)', text)
        if label_match:
            label = label_match.group(1).lower()
            if label not in {"present", "weak", "missing", "disconnected", "uncertain"}:
                label = "uncertain"
            confidence = 0.0
            if confidence_match:
                try:
                    confidence = float(confidence_match.group(1))
                except ValueError:
                    confidence = 0.0
            reason = reason_match.group(1) if reason_match else "parsed from partial model JSON"
            return {
                "label": label,
                "confidence": max(0.0, min(confidence, 1.0)),
                "reason": reason,
            }
        return {
            "label": "uncertain",
            "confidence": 0.0,
            "reason": f"model returned non-JSON text: {text[:500]}",
        }
    label = str(parsed.get("label", "uncertain")).lower()
    if label not in {"present", "weak", "missing", "disconnected", "uncertain"}:
        label = "uncertain"
    try:
        confidence = float(parsed.get("confidence", 0.0))
    except (TypeError, ValueError):
        confidence = 0.0
    return {
        "label": label,
        "confidence": max(0.0, min(confidence, 1.0)),
        "reason": str(parsed.get("reason", "")),
    }


def call_huggingface_vision_model(record: dict[str, Any]) -> dict[str, Any]:
    api_key = os.environ["HUGGINGFACE_API_KEY"]
    panel_path = PROJECT_ROOT / record.get("visual_evidence_png", record["visual_evidence"])
    panel_b64 = base64.b64encode(panel_path.read_bytes()).decode("ascii")
    metrics = {
        "strut_id": record["strut_id"],
        "rule_classification": record["classification"],
        "coverage_ratio": record["coverage_ratio"],
        "sample_hits": record["sample_hits"],
        "sample_count": record["sample_count"],
        "endpoint_hits": record["endpoint_hits"],
        "skeleton_connected": record["skeleton_connected"],
        "mean_nearest_observed_distance": record["mean_nearest_observed_distance"],
        "visual_nearby_point_count": record.get("visual_nearby_point_count"),
    }
    prompt = (
        "You are reviewing a CT lattice defect visual panel. The panel has XY and XZ projections. "
        "The colored line is the expected strut. Blue points are nearby observed skeleton evidence. "
        "Do not treat the colored expected line as observed material. If there are no or very few blue "
        "points near the expected line, the strut is likely missing or weak. "
        "Classify the strut as present, weak, missing, disconnected, or uncertain. "
        "Use both the visual panel and these metrics: "
        f"{json.dumps(metrics)}. "
        "Return only JSON: {\"label\": str, \"confidence\": number, \"reason\": str}."
    )
    payload = {
        "model": HF_MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{panel_b64}"
                        },
                    },
                ],
            }
        ],
        "max_tokens": 512,
    }
    response = requests.post(
        "https://router.huggingface.co/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=90,
    )
    if response.status_code >= 400:
        raise RuntimeError(f"{response.status_code} response from Hugging Face: {response.text[:1000]}")
    data = response.json()
    text = data["choices"][0]["message"]["content"]
    parsed = parse_hf_json(text)
    return {
        "model": HF_MODEL,
        "label": parsed["label"],
        "confidence": parsed["confidence"],
        "reason": parsed["reason"],
    }


def add_huggingface_model_review(reviewed: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if HF_REVIEW_LIMIT <= 0:
        result = {
            "status": "skipped",
            "reason": "DEFECT_HF_REVIEW_LIMIT is 0",
            "model": HF_MODEL,
            "requested_limit": HF_REVIEW_LIMIT,
            "reviews": [],
        }
        HF_MODEL_REVIEW_JSON.write_text(json.dumps(result, indent=2), encoding="utf-8")
        return []
    if not os.environ.get("HUGGINGFACE_API_KEY"):
        result = {
            "status": "skipped",
            "reason": "HUGGINGFACE_API_KEY is not set",
            "model": HF_MODEL,
            "requested_limit": HF_REVIEW_LIMIT,
            "reviews": [],
        }
        HF_MODEL_REVIEW_JSON.write_text(json.dumps(result, indent=2), encoding="utf-8")
        return []

    model_reviews = []
    for record in reviewed[:HF_REVIEW_LIMIT]:
        try:
            model_result = call_huggingface_vision_model(record)
            record["hf_model_classification"] = model_result["label"]
            record["hf_model_confidence"] = model_result["confidence"]
            record["hf_model_reason"] = model_result["reason"]
            record["hf_model"] = model_result["model"]
            review = {
                "strut_id": record["strut_id"],
                "visual_evidence": record["visual_evidence"],
                "visual_evidence_png": record.get("visual_evidence_png"),
                "rule_classification": record["classification"],
                "visual_classification": record["visual_classification"],
                "hf_model_classification": model_result["label"],
                "hf_model_confidence": model_result["confidence"],
                "hf_model_reason": model_result["reason"],
                "hf_model": model_result["model"],
            }
        except Exception as exc:
            record["hf_model_classification"] = "error"
            record["hf_model_confidence"] = 0.0
            record["hf_model_reason"] = str(exc)
            record["hf_model"] = HF_MODEL
            review = {
                "strut_id": record["strut_id"],
                "visual_evidence": record["visual_evidence"],
                "visual_evidence_png": record.get("visual_evidence_png"),
                "rule_classification": record["classification"],
                "visual_classification": record["visual_classification"],
                "hf_model_classification": "error",
                "hf_model_confidence": 0.0,
                "hf_model_reason": str(exc),
                "hf_model": HF_MODEL,
            }
        model_reviews.append(review)

    HF_MODEL_REVIEW_JSON.write_text(
        json.dumps(
            {
                "status": "completed",
                "model": HF_MODEL,
                "requested_limit": HF_REVIEW_LIMIT,
                "review_count": len(model_reviews),
                "reviews": model_reviews,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return model_reviews


def write_markdown_summary(summary: dict[str, Any]) -> None:
    counts = summary["classification_counts"]
    lines = [
        "# Defect Detection Summary",
        "",
        f"- Expected struts: **{summary['expected_struts']}**",
        f"- Observed skeleton struts: **{summary['observed_struts']}**",
        f"- Present struts: **{counts.get('present', 0)}**",
        f"- Weak struts: **{counts.get('weak', 0)}**",
        f"- Missing struts: **{counts.get('missing', 0)}**",
        f"- Disconnected struts: **{counts.get('disconnected', 0)}**",
        f"- Confirmed anomalies: **{summary['confirmed_anomalies']}**",
        f"- Confirmed anomaly percentage: **{summary['confirmed_anomaly_percentage']:.2f}%**",
        f"- Profile segments per strut: **{summary['profile_segments']}**",
        f"- Profile classification counts: `{summary['profile_classification_counts']}`",
        f"- Visual review panels generated: **{summary['visual_review_panels']}**",
        f"- Visual review index: `{summary['visual_review_index']}`",
        f"- Hugging Face model reviews: **{summary['hf_model_review_count']}**",
        f"- Hugging Face model review results: `{summary['hf_model_review_results']}`",
        "",
        "## Decision Rules",
        "",
        f"- Each expected strut is sampled at {SAMPLE_COUNT} evenly spaced points.",
        f"- A sample is covered when an observed skeleton point is within {SEARCH_RADIUS:g} voxels.",
        "- `present`: coverage is at least 65% and the same observed skeleton path reaches both endpoints.",
        "- `missing`: coverage is 10% or less.",
        "- `disconnected`: coverage is at least 25%, but no observed path connects both endpoints.",
        "- `weak`: partial coverage remains below the present threshold.",
        "",
        "## Node-to-Node Material Profile",
        "",
        f"- Each expected JSON edge is divided into {PROFILE_SEGMENTS} equal segments from node x to node y.",
        f"- Each segment receives a support value from nearby observed skeleton evidence within {SEARCH_RADIUS:g} voxels.",
        f"- Segment values below {LOW_PROFILE_THRESHOLD:.2f} are low-support regions.",
        "- `missing`: the profile is low across the expected strut.",
        "- `disconnected`: endpoints have support, but a middle low-support gap appears.",
        "- `weak`: the profile has partial support or isolated low-support segments.",
        "- `continuous`: the profile is supported along the expected edge.",
        "",
        "## Visual Review Layer",
        "",
        "- Candidate anomalies are rendered as SVG panels with two projections: XY and XZ.",
        "- Red/orange/purple lines show the expected strut; blue points show nearby observed skeleton evidence.",
        "- The visual label is derived from the same panel evidence and stored per strut.",
        "- When `HUGGINGFACE_API_KEY` is set and `DEFECT_HF_REVIEW_LIMIT` is greater than 0, candidate panels are sent to the configured Hugging Face vision-language model.",
    ]
    SUMMARY_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    reference = json.loads(REFERENCE_JSON.read_text(encoding="utf-8"))
    observed = json.loads(OBSERVED_JSON.read_text(encoding="utf-8"))

    reference_junctions = {
        int(junction["id"]): [float(v) for v in junction["position"]]
        for junction in reference["junctions"]
    }
    observed_index = build_observed_index(observed, SEARCH_RADIUS)
    per_strut = [
        classify_strut(strut, reference_junctions, observed_index)
        for strut in reference["struts"]
    ]
    visual_reviewed = add_visual_review(
        per_strut,
        reference["struts"],
        reference_junctions,
        observed_index,
    )
    hf_model_reviewed = add_huggingface_model_review(visual_reviewed)
    counts = Counter(item["classification"] for item in per_strut)
    profile_counts = Counter(item["profile_classification"] for item in per_strut)
    visual_counts = Counter(
        item.get("visual_classification", "not_reviewed")
        for item in visual_reviewed
    )
    hf_model_counts = Counter(
        item.get("hf_model_classification", "not_reviewed")
        for item in hf_model_reviewed
    )
    confirmed_anomalies = sum(
        count for classification, count in counts.items() if classification != "present"
    )
    summary = {
        "reference_json": str(REFERENCE_JSON),
        "observed_json": str(OBSERVED_JSON),
        "per_strut_json": str(PER_STRUT_JSON),
        "summary": str(SUMMARY_MD),
        "method": "expected-strut skeleton coverage and endpoint-connectivity test",
        "expected_struts": len(reference["struts"]),
        "observed_struts": len(observed["struts"]),
        "classification_counts": dict(sorted(counts.items())),
        "graph_candidates": counts.get("missing", 0) + counts.get("disconnected", 0),
        "weak_segmentation_candidates": counts.get("weak", 0),
        "confirmed_anomalies": confirmed_anomalies,
        "confirmed_anomaly_percentage": confirmed_anomalies / len(reference["struts"]) * 100,
        "sample_count": SAMPLE_COUNT,
        "search_radius_voxels": SEARCH_RADIUS,
        "profile_segments": PROFILE_SEGMENTS,
        "low_profile_threshold": LOW_PROFILE_THRESHOLD,
        "profile_classification_counts": dict(sorted(profile_counts.items())),
        "visual_review_dir": str(VISUAL_DIR),
        "visual_review_index": str(VISUAL_INDEX_JSON),
        "visual_review_panels": len(visual_reviewed),
        "visual_classification_counts": dict(sorted(visual_counts.items())),
        "hf_model_review_results": str(HF_MODEL_REVIEW_JSON),
        "hf_model_review_count": len(hf_model_reviewed),
        "hf_model": HF_MODEL,
        "hf_model_classification_counts": dict(sorted(hf_model_counts.items())),
    }

    ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
    PER_STRUT_JSON.write_text(json.dumps(per_strut, indent=2), encoding="utf-8")
    SUMMARY_JSON.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    write_markdown_summary(summary)

    print("Detecting Defects pipeline step")
    print(json.dumps({"status": "passed", **summary}))


if __name__ == "__main__":
    main()
