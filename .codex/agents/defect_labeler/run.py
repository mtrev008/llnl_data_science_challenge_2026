from __future__ import annotations

import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[3]
ANALYSIS_DIR = PROJECT_ROOT / "data" / "missing_struts" / "analysis"
CLUSTER_SUMMARY_JSON = ANALYSIS_DIR / "cluster_summary.json"
CLUSTER_LABELS_JSON = ANALYSIS_DIR / "cluster_labels.json"


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


def main() -> None:
    summary = json.loads(CLUSTER_SUMMARY_JSON.read_text(encoding="utf-8"))
    clusters = summary.get("clusters", [])
    if not clusters:
        raise ValueError("cluster_summary.json does not contain clusters")
    normal_score = min(float(cluster["mean_defect_score"]) for cluster in clusters)
    labels = [label_cluster(cluster, normal_score) for cluster in clusters]
    result = {
        "status": "passed",
        "labeller": "local defect_labeler subagent",
        "api_used": False,
        "source": str(CLUSTER_SUMMARY_JSON),
        "cluster_labels": labels,
    }
    CLUSTER_LABELS_JSON.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print("Defect Labeller pipeline step")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
