from __future__ import annotations

import json
import math
import os
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
import tifffile

try:
    from sklearn.cluster import KMeans
    from sklearn.preprocessing import StandardScaler
except Exception:  # pragma: no cover - fallback keeps the agent usable without sklearn.
    KMeans = None
    StandardScaler = None


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = PROJECT_ROOT / "data" / "missing_struts"
ANALYSIS_DIR = DATA_DIR / "analysis"
TIF_STACK = DATA_DIR / "tif_stacks" / "210127_Brian_Tran_strut_lattices_0point5dash1 1 Slices.tif"
REFERENCE_JSON = DATA_DIR / "registered_jsons" / "210127_Brian_Tran_strut_lattices_0point5dash1 1 Slices.json"
LABELER_SCRIPT = PROJECT_ROOT / ".codex" / "agents" / "defect_labeler" / "run.py"

PER_STRUT_JSON = ANALYSIS_DIR / "per_strut_defects.json"
SUMMARY_JSON = ANALYSIS_DIR / "anomaly_summary.json"
SUMMARY_MD = ANALYSIS_DIR / "anomaly_summary.md"
OBSERVED_JSON = ANALYSIS_DIR / "observed_lattice.json"
CLUSTER_SUMMARY_JSON = ANALYSIS_DIR / "cluster_summary.json"
CLUSTER_LABELS_JSON = ANALYSIS_DIR / "cluster_labels.json"
VISUAL_DIR = ANALYSIS_DIR / "defect_visual_review"
VISUAL_INDEX_JSON = VISUAL_DIR / "visual_review_index.json"
HF_MODEL_REVIEW_JSON = VISUAL_DIR / "hf_model_review_results.json"

PROFILE_SEGMENTS = int(os.environ.get("DEFECT_PROFILE_SEGMENTS", "21"))
PATCH_RADIUS = int(os.environ.get("DEFECT_PATCH_RADIUS", "3"))
MAX_CLUSTER_K = int(os.environ.get("DEFECT_MAX_CLUSTERS", "5"))
MIN_CLUSTER_K = int(os.environ.get("DEFECT_MIN_CLUSTERS", "2"))
MAX_VISUAL_PANELS = int(os.environ.get("DEFECT_MAX_VISUAL_PANELS", "100"))
NOMINAL_DEFECT_RATE_LOW = 0.5
NOMINAL_DEFECT_RATE_HIGH = 1.0


def interpolate(a: list[float], b: list[float], fraction: float) -> list[float]:
    return [float(x) + (float(y) - float(x)) * fraction for x, y in zip(a, b)]


def longest_true_run(values: list[bool]) -> int:
    longest = 0
    current = 0
    for value in values:
        current = current + 1 if value else 0
        longest = max(longest, current)
    return longest


def percentile_limits(volume: np.ndarray) -> tuple[float, float]:
    shape = volume.shape
    z_indices = np.linspace(0, shape[0] - 1, num=min(25, shape[0]), dtype=int)
    samples = []
    for z in z_indices:
        plane = np.asarray(volume[int(z)])
        step_y = max(1, plane.shape[0] // 256)
        step_x = max(1, plane.shape[1] // 256)
        samples.append(plane[::step_y, ::step_x].ravel())
    values = np.concatenate(samples).astype(np.float32)
    low, high = np.percentile(values, [1, 99.7])
    if high <= low:
        high = low + 1.0
    return float(low), float(high)


def open_tif_volume(path: Path) -> np.ndarray:
    try:
        return tifffile.memmap(path)
    except Exception:
        return tifffile.imread(path)


def normalized_patch_mean(volume: np.ndarray, point: list[float], low: float, high: float) -> float:
    x, y, z = [int(round(v)) for v in point]
    z0 = max(0, z - PATCH_RADIUS)
    z1 = min(volume.shape[0], z + PATCH_RADIUS + 1)
    y0 = max(0, y - PATCH_RADIUS)
    y1 = min(volume.shape[1], y + PATCH_RADIUS + 1)
    x0 = max(0, x - PATCH_RADIUS)
    x1 = min(volume.shape[2], x + PATCH_RADIUS + 1)
    if z0 >= z1 or y0 >= y1 or x0 >= x1:
        return 0.0
    patch = np.asarray(volume[z0:z1, y0:y1, x0:x1], dtype=np.float32)
    value = (float(np.mean(patch)) - low) / (high - low)
    return max(0.0, min(1.0, value))


def profile_for_strut(
    volume: np.ndarray,
    start: list[float],
    end: list[float],
    low: float,
    high: float,
) -> list[float]:
    return [
        normalized_patch_mean(volume, interpolate(start, end, i / (PROFILE_SEGMENTS - 1)), low, high)
        for i in range(PROFILE_SEGMENTS)
    ]


def embedding_from_profile(profile: list[float]) -> dict[str, Any]:
    values = np.asarray(profile, dtype=np.float32)
    threshold = max(0.10, float(np.percentile(values, 20)) * 0.75)
    low_flags = [float(v) < threshold for v in values]
    endpoint = float(np.mean(np.concatenate([values[:3], values[-3:]])))
    middle = values[3:-3] if len(values) > 6 else values
    middle_mean = float(np.mean(middle))
    middle_min = float(np.min(middle))
    mean = float(np.mean(values))
    minimum = float(np.min(values))
    std = float(np.std(values))
    low_fraction = float(np.mean(low_flags))
    longest_gap = longest_true_run(low_flags)
    continuity = 1.0 - (longest_gap / len(values))
    defect_score = (
        (1.0 - mean) * 0.35
        + (1.0 - minimum) * 0.20
        + low_fraction * 0.20
        + (1.0 - continuity) * 0.15
        + max(0.0, endpoint - middle_mean) * 0.10
    )
    return {
        "profile_values": [round(float(v), 5) for v in values],
        "profile_mean": mean,
        "profile_min": minimum,
        "profile_std": std,
        "profile_endpoint_mean": endpoint,
        "profile_middle_mean": middle_mean,
        "profile_middle_min": middle_min,
        "low_profile_threshold": threshold,
        "low_profile_segments": [i for i, flag in enumerate(low_flags) if flag],
        "longest_low_profile_gap": longest_gap,
        "continuity_score": continuity,
        "defect_score": float(defect_score),
        "embedding_features": [
            mean,
            minimum,
            std,
            endpoint,
            middle_mean,
            middle_min,
            low_fraction,
            longest_gap / len(values),
            continuity,
            float(defect_score),
            *[float(v) for v in values[:: max(1, len(values) // 7)]][:7],
        ],
    }


def select_clusters(features: np.ndarray) -> tuple[np.ndarray, dict[str, Any]]:
    if KMeans is None or StandardScaler is None:
        defect_axis = features[:, 9]
        q1, q2 = np.quantile(defect_axis, [0.85, 0.97])
        labels = np.zeros(len(defect_axis), dtype=int)
        labels[defect_axis >= q1] = 1
        labels[defect_axis >= q2] = 2
        score = approximate_silhouette(features, labels)
        return labels, {
            "algorithm": "quantile_fallback",
            "selected_cluster_count": int(len(set(labels.tolist()))),
            "silhouette_score": score,
            "cluster_stability": {
                "mean_silhouette_across_seeds": score,
                "min_silhouette_across_seeds": score,
                "max_silhouette_across_seeds": score,
            },
            "reason": "scikit-learn is unavailable; used defect-score quantiles and sampled silhouette",
        }

    scaled = StandardScaler().fit_transform(features)
    best_labels = None
    best_score = -1.0
    best_k = MIN_CLUSTER_K
    scores: dict[str, float] = {}
    max_k = min(MAX_CLUSTER_K, len(features) - 1)
    for k in range(MIN_CLUSTER_K, max_k + 1):
        model = KMeans(n_clusters=k, random_state=17, n_init=20)
        labels = model.fit_predict(scaled)
        score = approximate_silhouette(scaled, labels)
        if score is None:
            continue
        scores[str(k)] = score
        if score > best_score:
            best_score = score
            best_labels = labels
            best_k = k
    if best_labels is None:
        raise RuntimeError("could not select a clustering with at least two valid clusters")

    stability_scores = []
    for seed in [3, 11, 23, 37, 53]:
        labels = KMeans(n_clusters=best_k, random_state=seed, n_init=10).fit_predict(scaled)
        score = approximate_silhouette(scaled, labels)
        if score is not None:
            stability_scores.append(score)
    if not stability_scores:
        stability_scores = [best_score]

    return np.asarray(best_labels, dtype=int), {
        "algorithm": "kmeans",
        "selected_cluster_count": int(best_k),
        "silhouette_score": best_score,
        "silhouette_by_k": scores,
        "cluster_stability": {
            "mean_silhouette_across_seeds": float(np.mean(stability_scores)),
            "min_silhouette_across_seeds": float(np.min(stability_scores)),
            "max_silhouette_across_seeds": float(np.max(stability_scores)),
        },
    }


def approximate_silhouette(features: np.ndarray, labels: np.ndarray, max_samples: int = 3000) -> float | None:
    unique_labels = sorted(set(int(label) for label in labels))
    if len(unique_labels) < 2:
        return None
    if len(features) > max_samples:
        rng = np.random.default_rng(17)
        sample_indices = rng.choice(len(features), size=max_samples, replace=False)
        features = features[sample_indices]
        labels = labels[sample_indices]
    means = features.mean(axis=0)
    stds = features.std(axis=0)
    scaled = (features - means) / np.where(stds == 0, 1.0, stds)
    diff = scaled[:, None, :] - scaled[None, :, :]
    distances = np.sqrt(np.sum(diff * diff, axis=2))
    sample_scores = []
    for index, label in enumerate(labels):
        same = labels == label
        other = labels != label
        if int(np.sum(same)) <= 1 or not bool(np.any(other)):
            continue
        same_indices = np.where(same)[0]
        same_indices = same_indices[same_indices != index]
        a = float(np.mean(distances[index, same_indices]))
        b = min(
            float(np.mean(distances[index, labels == other_label]))
            for other_label in unique_labels
            if other_label != int(label) and bool(np.any(labels == other_label))
        )
        sample_scores.append((b - a) / max(a, b))
    if not sample_scores:
        return None
    return float(np.mean(sample_scores))


def write_profile_svg(path: Path, record: dict[str, Any]) -> None:
    width = 720
    height = 220
    values = record["profile_values"]
    points = []
    for i, value in enumerate(values):
        x = 40 + i / max(len(values) - 1, 1) * (width - 80)
        y = height - 40 - float(value) * (height - 80)
        points.append((x, y))
    polyline = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
    threshold_y = height - 40 - float(record["low_profile_threshold"]) * (height - 80)
    subtype = record.get("weak_subtype")
    label = record["classification"] if subtype is None else f"{record['classification']}:{subtype}"
    svg = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="720" height="220" viewBox="0 0 720 220">',
        '<rect width="720" height="220" fill="#ffffff" />',
        '<line x1="40" y1="180" x2="680" y2="180" stroke="#9ca3af" />',
        '<line x1="40" y1="40" x2="40" y2="180" stroke="#9ca3af" />',
        f'<line x1="40" y1="{threshold_y:.1f}" x2="680" y2="{threshold_y:.1f}" stroke="#dc2626" stroke-dasharray="5 5" />',
        f'<polyline points="{polyline}" fill="none" stroke="#111827" stroke-width="2" />',
        (
            f'<text x="40" y="24" font-family="monospace" font-size="14" fill="#111827">'
            f"strut {record['strut_id']} | cluster {record['cluster_id']} | "
            f"{label} | mean {record['profile_mean']:.2f}"
            "</text>"
        ),
        '</svg>',
    ]
    path.write_text("\n".join(svg), encoding="utf-8")


def write_visual_index(per_strut: list[dict[str, Any]]) -> None:
    VISUAL_DIR.mkdir(parents=True, exist_ok=True)
    candidates = sorted(per_strut, key=lambda item: item["defect_score"], reverse=True)[:MAX_VISUAL_PANELS]
    panels = []
    for record in candidates:
        label_slug = record["classification"]
        if record.get("weak_subtype") is not None:
            label_slug = f"{label_slug}_{record['weak_subtype']}"
        profile_path = VISUAL_DIR / f"strut_{record['strut_id']:05d}_{label_slug}_profile.svg"
        write_profile_svg(profile_path, record)
        record["profile_plot"] = str(profile_path.relative_to(PROJECT_ROOT))
        record["visual_evidence"] = record["profile_plot"]
        record["visual_evidence_png"] = None
        panels.append(
            {
                "strut_id": record["strut_id"],
                "cluster_id": record["cluster_id"],
                "classification": record["classification"],
                "weak_subtype": record["weak_subtype"],
                "weak_subtype_reason": record["weak_subtype_reason"],
                "defect_score": record["defect_score"],
                "profile_plot": record["profile_plot"],
                "visual_evidence": record["visual_evidence"],
                "visual_evidence_png": record["visual_evidence_png"],
            }
        )
    VISUAL_INDEX_JSON.write_text(
        json.dumps(
            {
                "visual_panel_count": len(panels),
                "max_visual_panels": MAX_VISUAL_PANELS,
                "panel_type": "raw CT strut support profile",
                "panels": panels,
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def cluster_summary(per_strut: list[dict[str, Any]], cluster_metrics: dict[str, Any]) -> dict[str, Any]:
    clusters = []
    by_cluster: dict[int, list[dict[str, Any]]] = {}
    for record in per_strut:
        by_cluster.setdefault(int(record["cluster_id"]), []).append(record)
    for cluster_id, records in sorted(by_cluster.items()):
        ordered = sorted(records, key=lambda item: item["defect_score"], reverse=True)
        clusters.append(
            {
                "cluster_id": cluster_id,
                "strut_count": len(records),
                "mean_defect_score": float(np.mean([r["defect_score"] for r in records])),
                "mean_profile_mean": float(np.mean([r["profile_mean"] for r in records])),
                "mean_profile_min": float(np.mean([r["profile_min"] for r in records])),
                "mean_longest_low_gap": float(np.mean([r["longest_low_profile_gap"] for r in records])),
                "mean_continuity_score": float(np.mean([r["continuity_score"] for r in records])),
                "representative_strut_ids": [r["strut_id"] for r in ordered[:8]],
                "representative_profiles": [r["profile_values"] for r in ordered[:3]],
            }
        )
    return {
        "method": "unsupervised raw-CT strut embedding clustering",
        "defect_definition": (
            "A defective strut is an expected registered-JSON strut assigned to a cluster "
            "that the local labeller subagent labels as weak. Weak struts are then subtyped "
            "as missing, broken, thin, or uncertain_weak from raw CT support-profile evidence."
        ),
        "cluster_metrics": cluster_metrics,
        "clusters": clusters,
    }


def run_labeler() -> dict[str, Any]:
    result = subprocess.run(
        [sys.executable, "-B", str(LABELER_SCRIPT)],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "defect labeler failed")
    return json.loads(CLUSTER_LABELS_JSON.read_text(encoding="utf-8"))


def weak_subtype(record: dict[str, Any]) -> tuple[str | None, str | None]:
    if record["classification"] != "weak":
        return None, None
    if record["profile_mean"] <= 0.20 and record["longest_low_profile_gap"] >= 8:
        return "missing", "very low mean support with a long contiguous low-support gap"
    if (
        record["profile_endpoint_mean"] > record["profile_middle_mean"] + 0.20
        and record["longest_low_profile_gap"] >= 2
    ):
        return "broken", "endpoints retain support while the strut middle has a low-support gap"
    if record["profile_mean"] < 0.35 or record["profile_middle_mean"] < 0.25:
        return "thin", "weak strut has reduced average or middle support but no decisive full gap"
    return "uncertain_weak", "weak cluster assignment lacks a specific missing, broken, or thin profile signature"


def write_markdown_summary(summary: dict[str, Any]) -> None:
    counts = summary["classification_counts"]
    subtype_counts = summary["weak_subtype_counts"]
    lines = [
        "# Defect Detection Summary",
        "",
        f"- Method: **{summary['method']}**",
        f"- Expected struts: **{summary['expected_struts']}**",
        f"- Selected clusters: **{summary['selected_cluster_count']}**",
        f"- Silhouette score: **{summary['silhouette_score']}**",
        f"- Present struts: **{counts.get('present', 0)}**",
        f"- Weak struts: **{counts.get('weak', 0)}**",
        f"- Weak/missing subtype: **{subtype_counts.get('missing', 0)}**",
        f"- Weak/broken subtype: **{subtype_counts.get('broken', 0)}**",
        f"- Weak/thin subtype: **{subtype_counts.get('thin', 0)}**",
        f"- Weak/uncertain subtype: **{subtype_counts.get('uncertain_weak', 0)}**",
        f"- Confirmed defects: **{summary['confirmed_anomalies']}**",
        f"- Confirmed defect percentage: **{summary['confirmed_anomaly_percentage']:.2f}%**",
        f"- Nominal defect-rate comparison: **{summary['nominal_rate_comparison']}**",
        "",
        "## Defective Strut Definition",
        "",
        summary["defect_definition"],
        "",
        "## Performance Metric",
        "",
        "- Primary metric: unsupervised cluster validity from silhouette score and seed-stability statistics.",
        "- Nominal 0.5-1% defect rate is included only as contextual comparison, not as the performance metric.",
        "",
        "## Labeller Subagent",
        "",
        f"- Cluster labels: `{summary['cluster_labels_json']}`",
        "- Labels were assigned after clustering by the local labeller subagent from saved cluster summaries.",
        "- Weak struts were further subtyped from per-strut raw CT support profiles.",
        "- No external LLM/API review was used.",
    ]
    SUMMARY_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
    VISUAL_DIR.mkdir(parents=True, exist_ok=True)

    reference = json.loads(REFERENCE_JSON.read_text(encoding="utf-8"))
    volume = open_tif_volume(TIF_STACK)
    if len(volume.shape) != 3:
        raise ValueError(f"expected 3D TIF stack, got shape {volume.shape}")
    low, high = percentile_limits(volume)

    junctions = {
        int(junction["id"]): [float(v) for v in junction["position"]]
        for junction in reference["junctions"]
    }
    per_strut = []
    for strut in reference["struts"]:
        start = junctions[int(strut["junction0"])]
        end = junctions[int(strut["junction1"])]
        profile = profile_for_strut(volume, start, end, low, high)
        embedding = embedding_from_profile(profile)
        per_strut.append(
            {
                "strut_id": int(strut["id"]),
                "junction0": int(strut["junction0"]),
                "junction1": int(strut["junction1"]),
                "start_xyz": start,
                "end_xyz": end,
                "sample_count": PROFILE_SEGMENTS,
                "patch_radius_voxels": PATCH_RADIUS,
                "intensity_percentile_low": low,
                "intensity_percentile_high": high,
                **embedding,
            }
        )

    features = np.asarray([record["embedding_features"] for record in per_strut], dtype=np.float32)
    labels, cluster_metrics = select_clusters(features)
    for record, label in zip(per_strut, labels):
        record["cluster_id"] = int(label)

    CLUSTER_SUMMARY_JSON.write_text(json.dumps(cluster_summary(per_strut, cluster_metrics), indent=2), encoding="utf-8")
    label_data = run_labeler()
    labels_by_cluster = {
        int(item["cluster_id"]): item
        for item in label_data.get("cluster_labels", [])
    }

    for record in per_strut:
        label_record = labels_by_cluster.get(int(record["cluster_id"]), {})
        classification = str(label_record.get("label", "uncertain"))
        record["classification"] = classification
        subtype, subtype_reason = weak_subtype(record)
        record["weak_subtype"] = subtype
        record["weak_subtype_reason"] = subtype_reason
        record["coverage_ratio"] = float(record["profile_mean"])
        record["sample_hits"] = int(round(record["profile_mean"] * PROFILE_SEGMENTS))
        record["endpoint_hits"] = int(record["profile_endpoint_mean"] > 0.25) * 2
        record["skeleton_connected"] = None
        record["mean_nearest_observed_distance"] = None
        record["reason"] = str(label_record.get("reason", "cluster was not labelled"))
        record["cluster_label_confidence"] = float(label_record.get("confidence", 0.0))

    write_visual_index(per_strut)

    counts = Counter(item["classification"] for item in per_strut)
    weak_subtype_counts = Counter(
        item["weak_subtype"]
        for item in per_strut
        if item["classification"] == "weak" and item["weak_subtype"] is not None
    )
    defect_labels = {"weak"}
    confirmed = sum(count for label, count in counts.items() if label in defect_labels)
    defect_rate = confirmed / len(per_strut) * 100
    nominal_comparison = (
        f"detected {defect_rate:.2f}% vs nominal {NOMINAL_DEFECT_RATE_LOW:.1f}-{NOMINAL_DEFECT_RATE_HIGH:.1f}%"
    )
    summary = {
        "reference_json": str(REFERENCE_JSON),
        "tif_stack": str(TIF_STACK),
        "per_strut_json": str(PER_STRUT_JSON),
        "summary": str(SUMMARY_MD),
        "method": "unsupervised raw-CT strut embedding clustering with local labeller subagent",
        "defect_definition": cluster_summary(per_strut, cluster_metrics)["defect_definition"],
        "expected_struts": len(reference["struts"]),
        "observed_struts": None,
        "selected_cluster_count": cluster_metrics["selected_cluster_count"],
        "silhouette_score": cluster_metrics.get("silhouette_score"),
        "cluster_metrics": cluster_metrics,
        "cluster_summary_json": str(CLUSTER_SUMMARY_JSON),
        "cluster_labels_json": str(CLUSTER_LABELS_JSON),
        "classification_counts": dict(sorted(counts.items())),
        "weak_subtype_counts": dict(sorted(weak_subtype_counts.items())),
        "confirmed_weak_subtypes": ["missing", "broken", "thin", "uncertain_weak"],
        "graph_candidates": weak_subtype_counts.get("missing", 0) + weak_subtype_counts.get("broken", 0),
        "weak_segmentation_candidates": counts.get("weak", 0),
        "confirmed_anomalies": confirmed,
        "confirmed_anomaly_percentage": defect_rate,
        "nominal_rate_comparison": nominal_comparison,
        "sample_count": PROFILE_SEGMENTS,
        "patch_radius_voxels": PATCH_RADIUS,
        "profile_segments": PROFILE_SEGMENTS,
        "visual_review_dir": str(VISUAL_DIR),
        "visual_review_index": str(VISUAL_INDEX_JSON),
        "visual_review_panels": min(MAX_VISUAL_PANELS, len(per_strut)),
        "hf_model_review_results": str(HF_MODEL_REVIEW_JSON),
        "hf_model_review_count": 0,
        "hf_model": None,
    }

    PER_STRUT_JSON.write_text(json.dumps(per_strut, indent=2), encoding="utf-8")
    SUMMARY_JSON.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    OBSERVED_JSON.write_text(
        json.dumps(
            {
                "method": summary["method"],
                "note": "Observed lattice skeleton graph is not used by this raw-CT unsupervised detector.",
                "struts": [],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    HF_MODEL_REVIEW_JSON.write_text(
        json.dumps(
            {
                "status": "skipped",
                "reason": "No external LLM/API review was used; cluster labels came from the local defect_labeler subagent.",
                "reviews": [],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    write_markdown_summary(summary)

    print("Detecting Defects pipeline step")
    print(json.dumps({"status": "passed", **summary}))


if __name__ == "__main__":
    main()
