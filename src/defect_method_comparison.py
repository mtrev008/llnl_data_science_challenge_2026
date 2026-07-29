from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np
import tifffile
from scipy.spatial import cKDTree

try:
    from sklearn.cluster import KMeans
    from sklearn.preprocessing import StandardScaler
except Exception:  # pragma: no cover
    KMeans = None
    StandardScaler = None


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data" / "missing_struts"
ANALYSIS_DIR = DATA_DIR / "analysis"
METHOD_DIR = ANALYSIS_DIR / "defect_method_comparison"
VISUAL_DIR = ANALYSIS_DIR / "defect_visual_review"

TIF_STACK = DATA_DIR / "tif_stacks" / "210127_Brian_Tran_strut_lattices_0point5dash1 1 Slices.tif"
SEGMENTED_MASK = ANALYSIS_DIR / "segmented_mask.tif"
SKELETON_TIF = ANALYSIS_DIR / "skeleton.tif"
REFERENCE_JSON = DATA_DIR / "registered_jsons" / "210127_Brian_Tran_strut_lattices_0point5dash1 1 Slices.json"

PROFILE_SEGMENTS = 21
PATCH_RADIUS = 3
REGISTRATION_TOLERANCE_RADIUS = 2
REGISTRATION_TOLERANCE_PERCENTILE = 85.0

BASELINE_CLUSTER_SUMMARY = ANALYSIS_DIR / "cluster_summary.json"
BASELINE_CLUSTER_LABELS = ANALYSIS_DIR / "cluster_labels.json"
BASELINE_PER_STRUT = ANALYSIS_DIR / "per_strut_defects.json"
BASELINE_SUMMARY_JSON = ANALYSIS_DIR / "anomaly_summary.json"
BASELINE_SUMMARY_MD = ANALYSIS_DIR / "anomaly_summary.md"
BASELINE_OBSERVED_JSON = ANALYSIS_DIR / "observed_lattice.json"
BASELINE_VISUAL_INDEX = VISUAL_DIR / "visual_review_index.json"
BASELINE_HF_REVIEW = VISUAL_DIR / "hf_model_review_results.json"

COMPARISON_JSON = ANALYSIS_DIR / "defect_method_comparison.json"
COMPARISON_MD = ANALYSIS_DIR / "defect_method_comparison.md"

_NEIGHBOR_OFFSETS = [
    (dz, dy, dx)
    for dz in (-1, 0, 1)
    for dy in (-1, 0, 1)
    for dx in (-1, 0, 1)
    if (dz, dy, dx) != (0, 0, 0)
]


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
    z_indices = np.linspace(0, volume.shape[0] - 1, num=min(25, volume.shape[0]), dtype=int)
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


def patch_mean_at_point(volume: np.ndarray, point: list[float], patch_radius: int) -> float:
    x, y, z = [int(round(v)) for v in point]
    z0 = max(0, z - patch_radius)
    z1 = min(volume.shape[0], z + patch_radius + 1)
    y0 = max(0, y - patch_radius)
    y1 = min(volume.shape[1], y + patch_radius + 1)
    x0 = max(0, x - patch_radius)
    x1 = min(volume.shape[2], x + patch_radius + 1)
    patch = np.asarray(volume[z0:z1, y0:y1, x0:x1], dtype=np.float32)
    if patch.size == 0:
        return float("nan")
    return float(np.mean(patch))


def normalized_patch_mean(volume: np.ndarray, point: list[float], low: float, high: float) -> float:
    candidate_means = []
    for dz in range(-REGISTRATION_TOLERANCE_RADIUS, REGISTRATION_TOLERANCE_RADIUS + 1):
        for dy in range(-REGISTRATION_TOLERANCE_RADIUS, REGISTRATION_TOLERANCE_RADIUS + 1):
            for dx in range(-REGISTRATION_TOLERANCE_RADIUS, REGISTRATION_TOLERANCE_RADIUS + 1):
                offset_point = [point[0] + dx, point[1] + dy, point[2] + dz]
                candidate_mean = patch_mean_at_point(volume, offset_point, PATCH_RADIUS)
                if not math.isnan(candidate_mean):
                    candidate_means.append(candidate_mean)
    if not candidate_means:
        return 0.0
    selected_mean = float(np.percentile(np.asarray(candidate_means, dtype=np.float32), REGISTRATION_TOLERANCE_PERCENTILE))
    value = (selected_mean - low) / (high - low)
    return max(0.0, min(1.0, value))


def profile_for_raw_ct(volume: np.ndarray, start: list[float], end: list[float], low: float, high: float) -> list[float]:
    return [
        normalized_patch_mean(volume, interpolate(start, end, i / (PROFILE_SEGMENTS - 1)), low, high)
        for i in range(PROFILE_SEGMENTS)
    ]


def local_mask_support(mask: np.ndarray, point: list[float], radius: int = 1) -> float:
    x, y, z = [int(round(v)) for v in point]
    z0 = max(0, z - radius)
    z1 = min(mask.shape[0], z + radius + 1)
    y0 = max(0, y - radius)
    y1 = min(mask.shape[1], y + radius + 1)
    x0 = max(0, x - radius)
    x1 = min(mask.shape[2], x + radius + 1)
    patch = np.asarray(mask[z0:z1, y0:y1, x0:x1] > 0, dtype=np.float32)
    if patch.size == 0:
        return 0.0
    return float(np.max(patch))


def profile_for_mask(mask: np.ndarray, start: list[float], end: list[float]) -> list[float]:
    return [
        local_mask_support(mask, interpolate(start, end, i / (PROFILE_SEGMENTS - 1)), radius=1)
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
            "reason": "scikit-learn unavailable; used defect-score quantiles and sampled silhouette",
        }

    scaled = StandardScaler().fit_transform(features)
    best_labels = None
    best_score = -1.0
    best_k = 2
    scores: dict[str, float] = {}
    max_k = min(5, len(features) - 1)
    for k in range(2, max_k + 1):
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


def cluster_summary(per_strut: list[dict[str, Any]], cluster_metrics: dict[str, Any]) -> dict[str, Any]:
    by_cluster: dict[int, list[dict[str, Any]]] = {}
    for record in per_strut:
        by_cluster.setdefault(int(record["cluster_id"]), []).append(record)
    clusters = []
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


def label_cluster(cluster: dict[str, Any], normal_score: float) -> dict[str, Any]:
    defect_score = float(cluster["mean_defect_score"])
    profile_mean = float(cluster["mean_profile_mean"])
    profile_min = float(cluster["mean_profile_min"])
    longest_gap = float(cluster["mean_longest_low_gap"])
    continuity = float(cluster["mean_continuity_score"])
    relative_score = defect_score - normal_score
    if abs(relative_score) <= 1e-9 and continuity >= 0.90:
        label = "present"
        confidence = 0.90
        reason = "cluster has the lowest defect score and the most continuous raw CT support profile"
    elif relative_score >= 0.12 and profile_mean < 0.35:
        label = "weak"
        confidence = 0.80
        reason = "cluster has materially reduced raw CT support relative to the present baseline"
    elif relative_score >= 0.20 and profile_mean < 0.45:
        label = "weak"
        confidence = 0.78
        reason = "cluster is well separated from the lowest-defect cluster and has reduced material support"
    elif relative_score >= 0.30:
        label = "weak"
        confidence = 0.70
        reason = "cluster is anomalous by defect score, but support profile is not specific enough for missing or disconnected"
    elif relative_score <= 0.08 and profile_mean >= 0.45 and continuity >= 0.85:
        label = "present"
        confidence = 0.88
        reason = "cluster has the strongest support profile and high continuity"
    else:
        label = "weak"
        confidence = 0.55
        reason = "cluster evidence is weaker than the present baseline but needs per-strut subtype review"
    return {
        "cluster_id": int(cluster["cluster_id"]),
        "label": label,
        "confidence": confidence,
        "reason": reason,
        "evidence": {
            "strut_count": int(cluster["strut_count"]),
            "mean_defect_score": defect_score,
            "mean_profile_mean": profile_mean,
            "mean_profile_min": profile_min,
            "mean_longest_low_gap": longest_gap,
            "mean_continuity_score": continuity,
            "relative_defect_score": relative_score,
            "representative_strut_ids": cluster.get("representative_strut_ids", []),
        },
    }


def weak_subtype(record: dict[str, Any]) -> tuple[str | None, str | None]:
    if record["classification"] != "weak":
        return None, None
    if record["profile_mean"] <= 0.20 and record["longest_low_profile_gap"] >= 8:
        return "missing", "very low mean support with a long contiguous low-support gap"
    if record["profile_endpoint_mean"] > record["profile_middle_mean"] + 0.20 and record["longest_low_profile_gap"] >= 2:
        return "broken", "endpoints retain support while the strut middle has a low-support gap"
    if record["profile_mean"] < 0.35 or record["profile_middle_mean"] < 0.25:
        return "thin", "weak strut has reduced average or middle support but no decisive full gap"
    return "uncertain_weak", "weak cluster assignment lacks a specific missing, broken, or thin profile signature"


def load_reference() -> dict[str, Any]:
    return json.loads(REFERENCE_JSON.read_text(encoding="utf-8"))


def junction_lookup(reference: dict[str, Any]) -> dict[int, dict[str, Any]]:
    return {int(junction["id"]): junction for junction in reference["junctions"]}


def strut_lookup(reference: dict[str, Any]) -> list[dict[str, Any]]:
    return [{**strut, "id": int(strut["id"]), "junction0": int(strut["junction0"]), "junction1": int(strut["junction1"])} for strut in reference["struts"]]


def compute_mask_bbox(mask: np.ndarray) -> dict[str, list[int]]:
    z_any = np.any(mask, axis=(1, 2))
    y_any = np.any(mask, axis=(0, 2))
    x_any = np.any(mask, axis=(0, 1))
    z_idx = np.flatnonzero(z_any)
    y_idx = np.flatnonzero(y_any)
    x_idx = np.flatnonzero(x_any)
    return {
        "z": [int(z_idx[0]), int(z_idx[-1])],
        "y": [int(y_idx[0]), int(y_idx[-1])],
        "x": [int(x_idx[0]), int(x_idx[-1])],
    }


def compute_reference_bbox(reference: dict[str, Any], margin: float) -> dict[str, list[int]]:
    positions = np.asarray([junction["position"] for junction in reference["junctions"]], dtype=np.float32)
    x = positions[:, 0]
    y = positions[:, 1]
    z = positions[:, 2]
    return {
        "x": [int(math.floor(float(np.min(x) - margin))), int(math.ceil(float(np.max(x) + margin)))],
        "y": [int(math.floor(float(np.min(y) - margin))), int(math.ceil(float(np.max(y) + margin)))],
        "z": [int(math.floor(float(np.min(z) - margin))), int(math.ceil(float(np.max(z) + margin)))],
    }


def estimate_boundary_margin(reference: dict[str, Any]) -> float:
    junctions = junction_lookup(reference)
    lengths = []
    for strut in reference["struts"][: min(len(reference["struts"]), 2048)]:
        a = np.asarray(junctions[int(strut["junction0"])]["position"], dtype=np.float32)
        b = np.asarray(junctions[int(strut["junction1"])]["position"], dtype=np.float32)
        lengths.append(float(np.linalg.norm(b - a)))
    if not lengths:
        return 8.0
    return max(6.0, float(np.median(lengths)) * 0.45)


def classify_boundary(position_xyz: list[float], bbox: dict[str, list[int]], margin: float) -> dict[str, Any]:
    x, y, z = [float(v) for v in position_xyz]
    distances = {
        "x_min": x - bbox["x"][0],
        "x_max": bbox["x"][1] - x,
        "y_min": y - bbox["y"][0],
        "y_max": bbox["y"][1] - y,
        "z_min": z - bbox["z"][0],
        "z_max": bbox["z"][1] - z,
    }
    face, face_distance = min(distances.items(), key=lambda item: item[1])
    is_boundary = face_distance <= margin
    return {
        "is_boundary": bool(is_boundary),
        "boundary_label": "boundary" if is_boundary else "interior",
        "nearest_face": face,
        "face_distance_voxels": float(face_distance),
    }


def build_reference_incidence(reference: dict[str, Any]) -> dict[int, list[int]]:
    incidence: dict[int, list[int]] = defaultdict(list)
    for strut in strut_lookup(reference):
        incidence[strut["junction0"]].append(strut["id"])
        incidence[strut["junction1"]].append(strut["id"])
    return incidence


def build_junction_records_from_reference(
    reference: dict[str, Any],
    bbox: dict[str, list[int]],
    margin: float,
    strut_records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    by_strut_id = {int(record["strut_id"]): record for record in strut_records if "strut_id" in record}
    incidence = build_reference_incidence(reference)
    records = []
    for junction in reference["junctions"]:
        junction_id = int(junction["id"])
        boundary_info = classify_boundary(junction["position"], bbox, margin)
        incident = [by_strut_id[strut_id] for strut_id in incidence.get(junction_id, []) if strut_id in by_strut_id]
        observed_degree = sum(1 for record in incident if record.get("presence_status") in {"present", "weak"} or record.get("classification") == "present")
        expected_degree = 2 if boundary_info["is_boundary"] else 4
        missing_neighbor_count = max(0, expected_degree - observed_degree)
        flagged = missing_neighbor_count > 0
        records.append(
            {
                "junction_id": junction_id,
                "position_xyz": [float(v) for v in junction["position"]],
                "reference_mode": "registered_json",
                "boundary_label": boundary_info["boundary_label"],
                "nearest_face": boundary_info["nearest_face"],
                "face_distance_voxels": boundary_info["face_distance_voxels"],
                "expected_degree": expected_degree,
                "observed_degree": int(observed_degree),
                "missing_neighbor_count": int(missing_neighbor_count),
                "incident_strut_ids": [int(record["strut_id"]) for record in incident],
                "flagged": bool(flagged),
                "reason": (
                    f"{boundary_info['boundary_label']} junction evaluated against expected degree {expected_degree}; "
                    f"observed support degree {observed_degree}"
                ),
            }
        )
    return records


def summarize_method_counts(strut_records: list[dict[str, Any]], junction_records: list[dict[str, Any]]) -> dict[str, Any]:
    missing_struts = [record for record in strut_records if record.get("presence_status") == "missing" or record.get("weak_subtype") == "missing"]
    weak_struts = [
        record
        for record in strut_records
        if record.get("presence_status") == "weak"
        or (record.get("classification") == "weak" and record.get("weak_subtype") != "missing")
    ]
    flagged_junctions = [record for record in junction_records if record.get("flagged")]
    return {
        "total_junctions": len(junction_records),
        "flagged_junctions": len(flagged_junctions),
        "total_struts": len(strut_records),
        "flagged_missing_struts": len(missing_struts),
        "flagged_weak_struts": len(weak_struts),
    }


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def method_paths(method_name: str) -> dict[str, Path]:
    slug = method_name.replace(" ", "_")
    return {
        "json": METHOD_DIR / f"{slug}_result.json",
        "md": METHOD_DIR / f"{slug}_summary.md",
    }


def write_method_artifacts(result: dict[str, Any]) -> None:
    paths = method_paths(result["method_name"])
    write_json(paths["json"], result)
    metrics = result["summary_metrics"]
    lines = [
        f"# {result['method_name']}",
        "",
        f"- Status: **{result['status']}**",
        f"- Reference mode: **{result['reference_mode']}**",
        f"- Input mask: `{result['input_mask']}`",
        f"- Total junctions: **{metrics.get('total_junctions', 0)}**",
        f"- Flagged junctions: **{metrics.get('flagged_junctions', 0)}**",
        f"- Total struts: **{metrics.get('total_struts', 0)}**",
        f"- Missing struts: **{metrics.get('flagged_missing_struts', 0)}**",
        f"- Weak struts: **{metrics.get('flagged_weak_struts', 0)}**",
        "",
        "## Caveats",
        "",
    ]
    caveats = result.get("summary_metrics", {}).get("caveats", [])
    if caveats:
        lines.extend([f"- {item}" for item in caveats])
    else:
        lines.append("- None recorded.")
    write_text(paths["md"], "\n".join(lines) + "\n")
    result["artifact_paths"].update({"result_json": str(paths["json"]), "summary_md": str(paths["md"])})


def run_clustering_baseline(reference: dict[str, Any], bbox: dict[str, list[int]], margin: float) -> dict[str, Any]:
    if (
        BASELINE_CLUSTER_SUMMARY.exists()
        and BASELINE_CLUSTER_LABELS.exists()
        and BASELINE_PER_STRUT.exists()
        and BASELINE_SUMMARY_JSON.exists()
    ):
        per_strut = json.loads(BASELINE_PER_STRUT.read_text(encoding="utf-8"))
        if per_strut:
            junction_records = build_junction_records_from_reference(reference, bbox, margin, per_strut)
            baseline_summary = json.loads(BASELINE_SUMMARY_JSON.read_text(encoding="utf-8"))
            result = {
                "method_name": "clustering_baseline",
                "input_mask": str(SEGMENTED_MASK),
                "reference_mode": "registered_json",
                "junction_records": junction_records,
                "strut_records": per_strut,
                "summary_metrics": {
                    **summarize_method_counts(per_strut, junction_records),
                    "selected_cluster_count": baseline_summary.get("selected_cluster_count"),
                    "silhouette_score": baseline_summary.get("silhouette_score"),
                    "classification_counts": baseline_summary.get("classification_counts", {}),
                    "weak_subtype_counts": baseline_summary.get("weak_subtype_counts", {}),
                    "caveats": [
                        "Baseline artifacts were reused from the existing raw-CT clustering run in analysis/.",
                        "Visual-review PNG/SVG outputs are not required by the comparison reporting contract.",
                    ],
                },
                "artifact_paths": {
                    "legacy_summary_json": str(BASELINE_SUMMARY_JSON),
                    "legacy_summary_md": str(BASELINE_SUMMARY_MD),
                    "legacy_cluster_summary_json": str(BASELINE_CLUSTER_SUMMARY),
                    "legacy_cluster_labels_json": str(BASELINE_CLUSTER_LABELS),
                    "legacy_per_strut_json": str(BASELINE_PER_STRUT),
                },
                "status": "passed",
            }
            write_json(
                BASELINE_VISUAL_INDEX,
                {
                    "visual_panel_count": 0,
                    "max_visual_panels": 0,
                    "panel_type": "omitted",
                    "note": "Comparison workflow no longer depends on visual SVG/PNG review artifacts.",
                    "panels": [],
                },
            )
            write_json(
                BASELINE_HF_REVIEW,
                {
                    "status": "skipped",
                    "reason": "No external LLM/API review was used; cluster labels came from the local defect_labeler logic.",
                    "reviews": [],
                },
            )
            write_method_artifacts(result)
            return result

    volume = open_tif_volume(TIF_STACK)
    if len(volume.shape) != 3:
        raise ValueError(f"expected 3D TIF stack, got shape {volume.shape}")
    low, high = percentile_limits(volume)
    junctions = junction_lookup(reference)
    per_strut = []
    for strut in strut_lookup(reference):
        start = [float(v) for v in junctions[strut["junction0"]]["position"]]
        end = [float(v) for v in junctions[strut["junction1"]]["position"]]
        profile = profile_for_raw_ct(volume, start, end, low, high)
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
                "registration_tolerance_radius_voxels": REGISTRATION_TOLERANCE_RADIUS,
                "registration_tolerance_percentile": REGISTRATION_TOLERANCE_PERCENTILE,
                "intensity_percentile_low": low,
                "intensity_percentile_high": high,
                **embedding,
            }
        )
    features = np.asarray([record["embedding_features"] for record in per_strut], dtype=np.float32)
    labels, cluster_metrics = select_clusters(features)
    for record, label in zip(per_strut, labels):
        record["cluster_id"] = int(label)
    baseline_cluster_summary = cluster_summary(per_strut, cluster_metrics)
    write_json(BASELINE_CLUSTER_SUMMARY, baseline_cluster_summary)
    normal_score = min(float(cluster["mean_defect_score"]) for cluster in baseline_cluster_summary["clusters"])
    cluster_labels = [label_cluster(cluster, normal_score) for cluster in baseline_cluster_summary["clusters"]]
    cluster_label_result = {
        "status": "passed",
        "labeller": "local defect_labeler subagent",
        "api_used": False,
        "source": str(BASELINE_CLUSTER_SUMMARY),
        "cluster_labels": cluster_labels,
    }
    write_json(BASELINE_CLUSTER_LABELS, cluster_label_result)
    labels_by_cluster = {int(item["cluster_id"]): item for item in cluster_labels}
    for record in per_strut:
        label_record = labels_by_cluster[int(record["cluster_id"])]
        record["classification"] = str(label_record["label"])
        subtype, subtype_reason = weak_subtype(record)
        record["weak_subtype"] = subtype
        record["weak_subtype_reason"] = subtype_reason
        record["coverage_ratio"] = float(record["profile_mean"])
        record["sample_hits"] = int(round(record["profile_mean"] * PROFILE_SEGMENTS))
        record["endpoint_hits"] = int(record["profile_endpoint_mean"] > 0.25) * 2
        record["reason"] = str(label_record["reason"])
        record["cluster_label_confidence"] = float(label_record["confidence"])
        record["presence_status"] = "missing" if subtype == "missing" else ("weak" if record["classification"] == "weak" else "present")
        record["confidence"] = float(label_record["confidence"])
    counts = Counter(item["classification"] for item in per_strut)
    weak_subtype_counts = Counter(
        item["weak_subtype"]
        for item in per_strut
        if item["classification"] == "weak" and item["weak_subtype"] is not None
    )
    confirmed = int(counts.get("weak", 0))
    defect_rate = confirmed / len(per_strut) * 100.0
    nominal_comparison = f"detected {defect_rate:.2f}% vs nominal 0.5-1.0%"
    summary = {
        "reference_json": str(REFERENCE_JSON),
        "tif_stack": str(TIF_STACK),
        "per_strut_json": str(BASELINE_PER_STRUT),
        "summary": str(BASELINE_SUMMARY_MD),
        "method": "unsupervised raw-CT strut embedding clustering with local labeller subagent",
        "defect_definition": baseline_cluster_summary["defect_definition"],
        "expected_struts": len(reference["struts"]),
        "observed_struts": None,
        "selected_cluster_count": cluster_metrics["selected_cluster_count"],
        "silhouette_score": cluster_metrics.get("silhouette_score"),
        "cluster_metrics": cluster_metrics,
        "cluster_summary_json": str(BASELINE_CLUSTER_SUMMARY),
        "cluster_labels_json": str(BASELINE_CLUSTER_LABELS),
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
        "registration_tolerance_radius_voxels": REGISTRATION_TOLERANCE_RADIUS,
        "registration_tolerance_percentile": REGISTRATION_TOLERANCE_PERCENTILE,
        "profile_segments": PROFILE_SEGMENTS,
        "visual_review_dir": str(VISUAL_DIR),
        "visual_review_index": str(BASELINE_VISUAL_INDEX),
        "visual_review_panels": 0,
        "hf_model_review_results": str(BASELINE_HF_REVIEW),
        "hf_model_review_count": 0,
        "hf_model": None,
    }
    write_json(BASELINE_PER_STRUT, per_strut)
    write_json(BASELINE_SUMMARY_JSON, summary)
    write_json(
        BASELINE_OBSERVED_JSON,
        {
            "method": summary["method"],
            "note": "Observed lattice skeleton graph is not used by this raw-CT unsupervised detector.",
            "struts": [],
        },
    )
    write_json(
        BASELINE_VISUAL_INDEX,
        {
            "visual_panel_count": 0,
            "max_visual_panels": 0,
            "panel_type": "omitted",
            "note": "Comparison workflow no longer depends on visual SVG/PNG review artifacts.",
            "panels": [],
        },
    )
    write_json(
        BASELINE_HF_REVIEW,
        {
            "status": "skipped",
            "reason": "No external LLM/API review was used; cluster labels came from the local defect_labeler logic.",
            "reviews": [],
        },
    )
    write_text(
        BASELINE_SUMMARY_MD,
        "\n".join(
            [
                "# Defect Detection Summary",
                "",
                f"- Method: **{summary['method']}**",
                f"- Expected struts: **{summary['expected_struts']}**",
                f"- Selected clusters: **{summary['selected_cluster_count']}**",
                f"- Silhouette score: **{summary['silhouette_score']}**",
                f"- Present struts: **{counts.get('present', 0)}**",
                f"- Weak struts: **{counts.get('weak', 0)}**",
                f"- Weak/missing subtype: **{weak_subtype_counts.get('missing', 0)}**",
                f"- Weak/broken subtype: **{weak_subtype_counts.get('broken', 0)}**",
                f"- Weak/thin subtype: **{weak_subtype_counts.get('thin', 0)}**",
                f"- Weak/uncertain subtype: **{weak_subtype_counts.get('uncertain_weak', 0)}**",
                f"- Confirmed defects: **{summary['confirmed_anomalies']}**",
                f"- Confirmed defect percentage: **{summary['confirmed_anomaly_percentage']:.2f}%**",
                f"- Nominal defect-rate comparison: **{summary['nominal_rate_comparison']}**",
                "",
                "## Notes",
                "",
                "- This baseline remains the existing raw-CT clustering detector, wrapped for comparison.",
                "- Visual-review PNG/SVG outputs are no longer part of the reporting contract.",
            ]
        )
        + "\n",
    )
    junction_records = build_junction_records_from_reference(reference, bbox, margin, per_strut)
    result = {
        "method_name": "clustering_baseline",
        "input_mask": str(SEGMENTED_MASK),
        "reference_mode": "registered_json",
        "junction_records": junction_records,
        "strut_records": per_strut,
        "summary_metrics": {
            **summarize_method_counts(per_strut, junction_records),
            "selected_cluster_count": cluster_metrics["selected_cluster_count"],
            "silhouette_score": cluster_metrics.get("silhouette_score"),
            "classification_counts": dict(sorted(counts.items())),
            "weak_subtype_counts": dict(sorted(weak_subtype_counts.items())),
            "caveats": [
                "Baseline clusters raw-CT support profiles rather than using binary-topology reasoning.",
                "Weak classifications are comparison-ready, but not all weak struts are decisive missing-strut findings.",
            ],
        },
        "artifact_paths": {
            "legacy_summary_json": str(BASELINE_SUMMARY_JSON),
            "legacy_summary_md": str(BASELINE_SUMMARY_MD),
            "legacy_cluster_summary_json": str(BASELINE_CLUSTER_SUMMARY),
            "legacy_cluster_labels_json": str(BASELINE_CLUSTER_LABELS),
            "legacy_per_strut_json": str(BASELINE_PER_STRUT),
        },
        "status": "passed",
    }
    write_method_artifacts(result)
    return result


def classify_support_status(embedding: dict[str, Any]) -> tuple[str, float, str]:
    mean_support = float(embedding["profile_mean"])
    middle_support = float(embedding["profile_middle_mean"])
    longest_gap = int(embedding["longest_low_profile_gap"])
    if mean_support <= 0.08 or (mean_support <= 0.15 and longest_gap >= 8):
        return "missing", 0.88, "binary support stays near zero or contains a long missing segment"
    if mean_support < 0.35 or middle_support < 0.25 or longest_gap >= 4:
        return "weak", 0.68, "binary support is partial or interrupted along the nominal strut path"
    return "present", 0.86, "binary support is continuous across the nominal strut path"


def run_simple_json_assisted(reference: dict[str, Any], mask: np.ndarray, bbox: dict[str, list[int]], margin: float) -> dict[str, Any]:
    junctions = junction_lookup(reference)
    strut_records = []
    for strut in strut_lookup(reference):
        start = [float(v) for v in junctions[strut["junction0"]]["position"]]
        end = [float(v) for v in junctions[strut["junction1"]]["position"]]
        embedding = embedding_from_profile(profile_for_mask(mask, start, end))
        presence_status, confidence, reason = classify_support_status(embedding)
        strut_records.append(
            {
                "strut_id": int(strut["id"]),
                "junction0": int(strut["junction0"]),
                "junction1": int(strut["junction1"]),
                "start_xyz": start,
                "end_xyz": end,
                "presence_status": presence_status,
                "confidence": confidence,
                "reason": reason,
                "sample_count": PROFILE_SEGMENTS,
                **embedding,
            }
        )
    junction_records = build_junction_records_from_reference(reference, bbox, margin, strut_records)
    for record in junction_records:
        if record["flagged"]:
            record["confidence"] = 0.82 if record["missing_neighbor_count"] >= 2 else 0.66
            record["reason"] = (
                f"{record['boundary_label']} junction expected degree {record['expected_degree']} "
                f"but only {record['observed_degree']} nominal struts had binary support"
            )
        else:
            record["confidence"] = 0.84
    result = {
        "method_name": "simple_json_assisted",
        "input_mask": str(SEGMENTED_MASK),
        "reference_mode": "registered_json",
        "junction_records": junction_records,
        "strut_records": strut_records,
        "summary_metrics": {
            **summarize_method_counts(strut_records, junction_records),
            "boundary_margin_voxels": margin,
            "bbox_faces": bbox,
            "caveats": [
                "This mode assumes the registered nominal graph is spatially aligned to the segmented mask.",
                "Observed degree is computed from binary support on expected nominal struts, not from free-form inferred graph structure.",
            ],
        },
        "artifact_paths": {},
        "status": "passed",
    }
    write_method_artifacts(result)
    return result


def skeleton_voxel_graph(skeleton: np.ndarray) -> tuple[np.ndarray, dict[tuple[int, int, int], int], np.ndarray]:
    coords = np.argwhere(skeleton)
    coord_to_index = {tuple(int(v) for v in coord): idx for idx, coord in enumerate(coords)}
    degrees = np.zeros(len(coords), dtype=np.int16)
    for idx, coord in enumerate(coords):
        z, y, x = [int(v) for v in coord]
        count = 0
        for dz, dy, dx in _NEIGHBOR_OFFSETS:
            if (z + dz, y + dy, x + dx) in coord_to_index:
                count += 1
        degrees[idx] = count
    return coords, coord_to_index, degrees


def connected_node_components(coords: np.ndarray, coord_to_index: dict[tuple[int, int, int], int], node_indices: set[int]) -> tuple[list[list[int]], dict[int, int]]:
    node_components: list[list[int]] = []
    node_to_component: dict[int, int] = {}
    remaining = set(node_indices)
    while remaining:
        start = remaining.pop()
        stack = [start]
        component = [start]
        node_to_component[start] = len(node_components)
        while stack:
            current = stack.pop()
            z, y, x = [int(v) for v in coords[current]]
            for dz, dy, dx in _NEIGHBOR_OFFSETS:
                neighbor = coord_to_index.get((z + dz, y + dy, x + dx))
                if neighbor is None or neighbor not in remaining:
                    continue
                remaining.remove(neighbor)
                node_to_component[neighbor] = len(node_components)
                stack.append(neighbor)
                component.append(neighbor)
        node_components.append(component)
    return node_components, node_to_component


def follow_branch(
    start_idx: int,
    node_component_id: int,
    coords: np.ndarray,
    coord_to_index: dict[tuple[int, int, int], int],
    degrees: np.ndarray,
    node_to_component: dict[int, int],
    visited_edges: set[tuple[int, int]],
) -> tuple[list[int], set[int]]:
    path = [start_idx]
    touched_nodes = {node_component_id}
    prev = None
    current = start_idx
    while True:
        z, y, x = [int(v) for v in coords[current]]
        neighbors = []
        for dz, dy, dx in _NEIGHBOR_OFFSETS:
            neighbor = coord_to_index.get((z + dz, y + dy, x + dx))
            if neighbor is None or neighbor == prev:
                continue
            neighbors.append(neighbor)
        next_nodes = []
        for neighbor in neighbors:
            edge = tuple(sorted((current, neighbor)))
            if edge in visited_edges:
                continue
            if neighbor in node_to_component:
                touched_nodes.add(node_to_component[neighbor])
                visited_edges.add(edge)
            else:
                next_nodes.append(neighbor)
        if not next_nodes:
            break
        next_idx = next_nodes[0]
        visited_edges.add(tuple(sorted((current, next_idx))))
        path.append(next_idx)
        prev, current = current, next_idx
        if degrees[current] != 2:
            if current in node_to_component:
                touched_nodes.add(node_to_component[current])
            break
    return path, touched_nodes


def run_simple_mask_only(reference: dict[str, Any], mask: np.ndarray, bbox: dict[str, list[int]], margin: float) -> dict[str, Any]:
    skeleton = open_tif_volume(SKELETON_TIF)
    coords, coord_to_index, degrees = skeleton_voxel_graph(np.asarray(skeleton) > 0)
    node_indices = {idx for idx, degree in enumerate(degrees) if degree != 2}
    node_components, node_to_component = connected_node_components(coords, coord_to_index, node_indices)
    reference_positions = np.asarray([junction["position"] for junction in reference["junctions"]], dtype=np.float32)
    reference_ids = np.asarray([int(junction["id"]) for junction in reference["junctions"]], dtype=np.int32)
    tree = cKDTree(reference_positions[:, [2, 1, 0]])
    junction_records = []
    component_neighbors: dict[int, set[int]] = defaultdict(set)
    visited_edges: set[tuple[int, int]] = set()
    strut_records = []
    for component_id, component in enumerate(node_components):
        component_coords = coords[np.asarray(component, dtype=np.int32)]
        centroid_zyx = component_coords.mean(axis=0)
        position_xyz = [float(centroid_zyx[2]), float(centroid_zyx[1]), float(centroid_zyx[0])]
        boundary_info = classify_boundary(position_xyz, bbox, margin)
        distance, ref_index = tree.query([centroid_zyx[0], centroid_zyx[1], centroid_zyx[2]], k=1)
        matched_reference_junction_id = int(reference_ids[int(ref_index)]) if float(distance) <= max(8.0, margin * 1.5) else None
        junction_records.append(
            {
                "junction_id": int(component_id),
                "matched_reference_junction_id": matched_reference_junction_id,
                "position_xyz": position_xyz,
                "reference_mode": "mask_only_inferred",
                "boundary_label": boundary_info["boundary_label"],
                "nearest_face": boundary_info["nearest_face"],
                "face_distance_voxels": boundary_info["face_distance_voxels"],
                "expected_degree": 2 if boundary_info["is_boundary"] else 4,
                "observed_degree": 0,
                "missing_neighbor_count": 0,
                "incident_branch_ids": [],
                "flagged": False,
                "reason": "junction candidate inferred from skeleton voxels with non-two-neighbor topology",
            }
        )
    branch_id = 0
    for component_id, component in enumerate(node_components):
        seen_neighbors = set()
        for node_idx in component:
            z, y, x = [int(v) for v in coords[node_idx]]
            for dz, dy, dx in _NEIGHBOR_OFFSETS:
                neighbor = coord_to_index.get((z + dz, y + dy, x + dx))
                if neighbor is None or neighbor in node_to_component:
                    continue
                edge = tuple(sorted((node_idx, neighbor)))
                if edge in visited_edges or neighbor in seen_neighbors:
                    continue
                path, touched_nodes = follow_branch(
                    neighbor,
                    component_id,
                    coords,
                    coord_to_index,
                    degrees,
                    node_to_component,
                    visited_edges,
                )
                seen_neighbors.add(neighbor)
                touched = sorted(touched_nodes)
                for touched_node in touched:
                    component_neighbors[touched_node].add(branch_id)
                branch_coords = coords[np.asarray(path, dtype=np.int32)]
                status = "present"
                confidence = 0.78
                reason = "observed skeleton branch connects inferred junction neighborhoods"
                if len(touched) == 1:
                    status = "weak"
                    confidence = 0.60
                    reason = "branch terminates without a second inferred junction; likely boundary stub or truncated connection"
                strut_records.append(
                    {
                        "branch_id": int(branch_id),
                        "presence_status": status,
                        "confidence": confidence,
                        "reason": reason,
                        "junction_ids": touched,
                        "start_xyz": [
                            float(branch_coords[0][2]),
                            float(branch_coords[0][1]),
                            float(branch_coords[0][0]),
                        ],
                        "end_xyz": [
                            float(branch_coords[-1][2]),
                            float(branch_coords[-1][1]),
                            float(branch_coords[-1][0]),
                        ],
                        "voxel_length": int(len(path)),
                    }
                )
                branch_id += 1
    for record in junction_records:
        incident_ids = sorted(component_neighbors.get(int(record["junction_id"]), set()))
        observed_degree = len(incident_ids)
        expected_degree = int(record["expected_degree"])
        missing_neighbor_count = max(0, expected_degree - observed_degree)
        record["observed_degree"] = int(observed_degree)
        record["missing_neighbor_count"] = int(missing_neighbor_count)
        record["incident_branch_ids"] = incident_ids
        record["flagged"] = bool(missing_neighbor_count > 0)
        record["confidence"] = 0.80 if missing_neighbor_count >= 2 else (0.65 if missing_neighbor_count == 1 else 0.82)
        if record["flagged"]:
            record["reason"] = (
                f"{record['boundary_label']} inferred junction expected degree {expected_degree} "
                f"but only {observed_degree} skeleton branches were observed"
            )
    result = {
        "method_name": "simple_mask_only",
        "input_mask": str(SEGMENTED_MASK),
        "reference_mode": "mask_only",
        "junction_records": junction_records,
        "strut_records": strut_records,
        "summary_metrics": {
            **summarize_method_counts(strut_records, junction_records),
            "boundary_margin_voxels": margin,
            "bbox_faces": bbox,
            "caveats": [
                "Mask-only mode infers junctions from skeleton topology and then compares degree against the 4/2 rule.",
                "Recovered branch records represent observed branches only; missing branches are inferred from under-connected junction neighborhoods.",
            ],
        },
        "artifact_paths": {},
        "status": "passed",
    }
    write_method_artifacts(result)
    return result


def flagged_strut_id_set(result: dict[str, Any]) -> set[int]:
    ids = set()
    for record in result.get("strut_records", []):
        if record.get("presence_status") in {"missing", "weak"} and "strut_id" in record:
            ids.add(int(record["strut_id"]))
    return ids


def flagged_reference_junction_id_set(result: dict[str, Any]) -> set[int]:
    ids = set()
    for record in result.get("junction_records", []):
        if not record.get("flagged"):
            continue
        if record.get("reference_mode") == "registered_json" and "junction_id" in record:
            ids.add(int(record["junction_id"]))
        elif record.get("matched_reference_junction_id") is not None:
            ids.add(int(record["matched_reference_junction_id"]))
    return ids


def build_comparison_summary(results: list[dict[str, Any]]) -> dict[str, Any]:
    methods = [result["method_name"] for result in results]
    per_method = []
    for result in results:
        metrics = result["summary_metrics"]
        per_method.append(
            {
                "method_name": result["method_name"],
                "status": result["status"],
                "reference_mode": result["reference_mode"],
                "flagged_missing_struts": metrics.get("flagged_missing_struts", 0),
                "flagged_weak_struts": metrics.get("flagged_weak_struts", 0),
                "flagged_junctions": metrics.get("flagged_junctions", 0),
                "caveats": metrics.get("caveats", []),
            }
        )
    pairwise = []
    for idx, left in enumerate(results):
        for right in results[idx + 1 :]:
            pairwise.append(
                {
                    "methods": [left["method_name"], right["method_name"]],
                    "flagged_strut_overlap_count": len(flagged_strut_id_set(left) & flagged_strut_id_set(right)),
                    "flagged_junction_overlap_count": len(
                        flagged_reference_junction_id_set(left) & flagged_reference_junction_id_set(right)
                    ),
                    "flagged_strut_disagreement_count": len(flagged_strut_id_set(left) ^ flagged_strut_id_set(right)),
                    "flagged_junction_disagreement_count": len(
                        flagged_reference_junction_id_set(left) ^ flagged_reference_junction_id_set(right)
                    ),
                }
            )
    return {
        "methods_run": methods,
        "input_mask": str(SEGMENTED_MASK),
        "reference_json": str(REFERENCE_JSON),
        "skeleton_tif": str(SKELETON_TIF),
        "per_method": per_method,
        "pairwise_overlap_and_disagreement": pairwise,
        "recommended_next_step_interpretation": (
            "Treat clustering as the raw-CT baseline, use JSON-assisted binary support to confirm nominal-strut gaps, "
            "and treat mask-only junction under-connectivity as topology-first corroboration where registration is uncertain."
        ),
    }


def write_comparison_summary(summary: dict[str, Any]) -> None:
    write_json(COMPARISON_JSON, summary)
    lines = [
        "# Defect Method Comparison",
        "",
        f"- Input mask: `{summary['input_mask']}`",
        f"- Reference JSON: `{summary['reference_json']}`",
        f"- Methods run: **{', '.join(summary['methods_run'])}**",
        "",
        "## Per-method counts",
        "",
    ]
    for item in summary["per_method"]:
        lines.extend(
            [
                f"### {item['method_name']}",
                "",
                f"- Status: **{item['status']}**",
                f"- Reference mode: **{item['reference_mode']}**",
                f"- Missing struts: **{item['flagged_missing_struts']}**",
                f"- Weak struts: **{item['flagged_weak_struts']}**",
                f"- Flagged junctions: **{item['flagged_junctions']}**",
                "",
            ]
        )
    lines.extend(
        [
            "## Overlap and disagreement",
            "",
        ]
    )
    for item in summary["pairwise_overlap_and_disagreement"]:
        lines.append(
            f"- {item['methods'][0]} vs {item['methods'][1]}: "
            f"strut overlap {item['flagged_strut_overlap_count']}, "
            f"junction overlap {item['flagged_junction_overlap_count']}, "
            f"strut disagreement {item['flagged_strut_disagreement_count']}, "
            f"junction disagreement {item['flagged_junction_disagreement_count']}"
        )
    lines.extend(
        [
            "",
            "## Recommendation",
            "",
            summary["recommended_next_step_interpretation"],
        ]
    )
    write_text(COMPARISON_MD, "\n".join(lines) + "\n")


def run_defect_method_comparison() -> dict[str, Any]:
    ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
    METHOD_DIR.mkdir(parents=True, exist_ok=True)
    VISUAL_DIR.mkdir(parents=True, exist_ok=True)
    reference = load_reference()
    margin = estimate_boundary_margin(reference)
    bbox = compute_reference_bbox(reference, margin)
    mask = open_tif_volume(SEGMENTED_MASK)
    ordered_methods = [
        ("clustering_baseline", lambda: run_clustering_baseline(reference, bbox, margin)),
        ("simple_json_assisted", lambda: run_simple_json_assisted(reference, mask, bbox, margin)),
        ("simple_mask_only", lambda: run_simple_mask_only(reference, mask, bbox, margin)),
    ]
    results = []
    for method_name, runner in ordered_methods:
        try:
            results.append(runner())
        except Exception as exc:  # pragma: no cover
            failed = {
                "method_name": method_name,
                "input_mask": str(SEGMENTED_MASK),
                "reference_mode": "unknown",
                "junction_records": [],
                "strut_records": [],
                "summary_metrics": {
                    "total_junctions": 0,
                    "flagged_junctions": 0,
                    "total_struts": 0,
                    "flagged_missing_struts": 0,
                    "flagged_weak_struts": 0,
                    "caveats": [f"method failed: {exc}"],
                },
                "artifact_paths": {},
                "status": f"failed: {exc}",
            }
            write_method_artifacts(failed)
            results.append(failed)
    summary = build_comparison_summary(results)
    write_comparison_summary(summary)
    return summary
