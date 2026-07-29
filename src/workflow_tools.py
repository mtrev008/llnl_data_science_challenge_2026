from __future__ import annotations

import json
import os
import struct
import subprocess
import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT = PROJECT_ROOT / "reports" / "report.md"

PIPELINE_STEPS = [
    {
        "step": "Data Analyzer",
        "subagent": ".codex/agents/data_analyzer",
        "script": PROJECT_ROOT / ".codex/agents/data_analyzer/run.py",
        "expected_phrase": "Data Analyzer pipeline step",
        "artifacts": [
            "data/missing_struts/analysis/ct_volume_stats.json",
            "data/missing_struts/analysis/ct_volume_stats.md",
        ],
    },
    {
        "step": "Segmentation",
        "subagent": ".codex/agents/segmentation",
        "script": PROJECT_ROOT / ".codex/agents/segmentation/run.py",
        "expected_phrase": "Segmentation pipeline step",
        "artifacts": [
            "data/missing_struts/analysis/segmentation_workflow.py",
            "data/missing_struts/analysis/segmented_mask.tif",
            "data/missing_struts/analysis/segmentation_slice_380.png",
            "data/missing_struts/analysis/segmentation_report.md",
            "data/missing_struts/analysis/evaluation_summary.md",
        ],
    },
    {
        "step": "Skeletonization",
        "subagent": ".codex/agents/skeletonization",
        "script": PROJECT_ROOT / ".codex/agents/skeletonization/run.py",
        "expected_phrase": "Skeletonization pipeline step",
        "artifacts": [
            "data/missing_struts/analysis/skeleton.tif",
        ],
    },
    {
        "step": "Detecting Defects",
        "subagent": ".codex/agents/defect_detection",
        "script": PROJECT_ROOT / ".codex/agents/defect_detection/run.py",
        "expected_phrase": "Detecting Defects pipeline step",
        "artifacts": [
            "data/missing_struts/analysis/defect_method_comparison.json",
            "data/missing_struts/analysis/defect_method_comparison.md",
            "data/missing_struts/analysis/defect_method_comparison/clustering_baseline_result.json",
            "data/missing_struts/analysis/defect_method_comparison/simple_json_assisted_result.json",
            "data/missing_struts/analysis/defect_method_comparison/simple_mask_only_result.json",
            "data/missing_struts/analysis/cluster_summary.json",
            "data/missing_struts/analysis/cluster_labels.json",
            "data/missing_struts/analysis/per_strut_defects.json",
            "data/missing_struts/analysis/anomaly_summary.json",
            "data/missing_struts/analysis/anomaly_summary.md",
            "data/missing_struts/analysis/defect_visual_review/visual_review_index.json",
            "data/missing_struts/analysis/defect_visual_review/hf_model_review_results.json",
        ],
    },
    {
        "step": "Visualization",
        "subagent": ".codex/agents/visualization",
        "script": PROJECT_ROOT / ".codex/agents/visualization/run.py",
        "expected_phrase": "Visualization pipeline step",
        "artifacts": [
            "data/missing_struts/analysis/defect_struts_overview.png",
            "data/missing_struts/analysis/defect_struts_visualization.md",
        ],
    },
]


def collect_artifacts(paths: list[str]) -> list[dict[str, Any]]:
    artifacts = []
    for path in paths:
        artifact_path = PROJECT_ROOT / path
        exists = artifact_path.exists()
        artifacts.append(
            {
                "path": path,
                "exists": exists,
                "size_bytes": artifact_path.stat().st_size if exists else 0,
            }
        )
    return artifacts


def read_json_result(path: str) -> Any:
    return json.loads((PROJECT_ROOT / path).read_text(encoding="utf-8"))


def read_markdown_result(path: str) -> str:
    text = (PROJECT_ROOT / path).read_text(encoding="utf-8")
    if text.startswith("version https://git-lfs.github.com/spec/v1"):
        return "Git LFS pointer present; full Markdown content is not checked out locally."
    return text.strip()


def summarize_png(path: str) -> dict[str, Any]:
    with (PROJECT_ROOT / path).open("rb") as file:
        header = file.read(24)
    if not header.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError(f"{path} is not a PNG file")
    width, height = struct.unpack(">II", header[16:24])
    return {
        "path": path,
        "width": width,
        "height": height,
        "format": "PNG",
    }


def collect_step_results(step_name: str) -> list[dict[str, Any]]:
    if step_name == "Data Analyzer":
        return [
            {
                "title": "CT volume statistics",
                "source": "data/missing_struts/analysis/ct_volume_stats.json",
                "content": read_json_result("data/missing_struts/analysis/ct_volume_stats.json"),
            },
            {
                "title": "CT volume statistics report",
                "source": "data/missing_struts/analysis/ct_volume_stats.md",
                "content": read_markdown_result("data/missing_struts/analysis/ct_volume_stats.md"),
            },
        ]
    if step_name == "Segmentation":
        return [
            {
                "title": "Segmentation report",
                "source": "data/missing_struts/analysis/segmentation_report.md",
                "content": read_markdown_result("data/missing_struts/analysis/segmentation_report.md"),
            },
            {
                "title": "Segmentation evaluation",
                "source": "data/missing_struts/analysis/evaluation_summary.md",
                "content": read_markdown_result("data/missing_struts/analysis/evaluation_summary.md"),
            },
            {
                "title": "Segmented mask volume statistics",
                "source": "data/missing_struts/analysis/segmented_mask.tif",
                "content": {
                    "path": "data/missing_struts/analysis/segmented_mask.tif",
                    "foreground_voxels": 23410270,
                    "background_voxels": 495709685,
                    "foreground_fraction": 23410270 / (23410270 + 495709685),
                    "source": "segmentation_report.md",
                },
            },
        ]
    if step_name == "Skeletonization":
        return [
            {
                "title": "Skeleton output",
                "source": "data/missing_struts/analysis/skeleton.tif",
                "content": {
                    "path": "data/missing_struts/analysis/skeleton.tif",
                    "format": "BigTIFF",
                    "result": "3D centerline skeleton artifact generated from segmented_mask.tif",
                },
            },
        ]
    if step_name == "Detecting Defects":
        comparison = read_json_result("data/missing_struts/analysis/defect_method_comparison.json")
        baseline = read_json_result(
            "data/missing_struts/analysis/defect_method_comparison/clustering_baseline_result.json"
        )
        json_assisted = read_json_result(
            "data/missing_struts/analysis/defect_method_comparison/simple_json_assisted_result.json"
        )
        mask_only = read_json_result(
            "data/missing_struts/analysis/defect_method_comparison/simple_mask_only_result.json"
        )
        baseline_examples = [
            {
                "strut_id": item["strut_id"],
                "presence_status": item.get("presence_status"),
                "classification": item.get("classification"),
                "weak_subtype": item.get("weak_subtype"),
                "reason": item["reason"],
                "profile_mean": item.get("profile_mean"),
                "profile_min": item.get("profile_min"),
                "longest_low_profile_gap": item.get("longest_low_profile_gap"),
            }
            for item in baseline["strut_records"]
            if item.get("classification") != "present"
        ][:10]
        return [
            {
                "title": "Method comparison summary",
                "source": "data/missing_struts/analysis/defect_method_comparison.json",
                "content": comparison,
            },
            {
                "title": "Clustering baseline result",
                "source": "data/missing_struts/analysis/defect_method_comparison/clustering_baseline_result.json",
                "content": {
                    "method_name": baseline["method_name"],
                    "status": baseline["status"],
                    "summary_metrics": baseline["summary_metrics"],
                },
            },
            {
                "title": "Simple JSON-assisted result",
                "source": "data/missing_struts/analysis/defect_method_comparison/simple_json_assisted_result.json",
                "content": {
                    "method_name": json_assisted["method_name"],
                    "status": json_assisted["status"],
                    "summary_metrics": json_assisted["summary_metrics"],
                },
            },
            {
                "title": "Simple mask-only result",
                "source": "data/missing_struts/analysis/defect_method_comparison/simple_mask_only_result.json",
                "content": {
                    "method_name": mask_only["method_name"],
                    "status": mask_only["status"],
                    "summary_metrics": mask_only["summary_metrics"],
                },
            },
            {
                "title": "Baseline example strut classifications",
                "source": "data/missing_struts/analysis/per_strut_defects.json",
                "content": {
                    "total_records": len(baseline["strut_records"]),
                    "first_10_non_present": baseline_examples,
                },
            },
            {
                "title": "Comparison Markdown summary",
                "source": "data/missing_struts/analysis/defect_method_comparison.md",
                "content": read_markdown_result("data/missing_struts/analysis/defect_method_comparison.md"),
            },
        ]
    if step_name == "Visualization":
        return [
            {
                "title": "Defect strut overview",
                "source": "data/missing_struts/analysis/defect_struts_overview.png",
                "content": summarize_png("data/missing_struts/analysis/defect_struts_overview.png"),
            },
            {
                "title": "Visualization summary",
                "source": "data/missing_struts/analysis/defect_struts_visualization.md",
                "content": read_markdown_result("data/missing_struts/analysis/defect_struts_visualization.md"),
            },
        ]
    return []


def run_pipeline_step(step: dict[str, Any]) -> dict[str, Any]:
    env = os.environ.copy()
    env.setdefault("MPLCONFIGDIR", "/tmp/matplotlib-cache")
    result = subprocess.run(
        [sys.executable, "-B", str(step["script"])],
        cwd=PROJECT_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    stdout = result.stdout.strip()
    stderr = result.stderr.strip()
    issues = []
    if result.returncode != 0:
        issues.append(stderr or stdout or "subagent exited with a nonzero status")
    if step["expected_phrase"] not in stdout:
        issues.append(f"missing expected output: {step['expected_phrase']}")
    artifacts = collect_artifacts(step.get("artifacts", []))
    missing_artifacts = [artifact["path"] for artifact in artifacts if not artifact["exists"]]
    if missing_artifacts:
        issues.append("missing expected result artifact(s): " + ", ".join(missing_artifacts))
    result_content = []
    if not missing_artifacts:
        try:
            result_content = collect_step_results(step["step"])
        except Exception as exc:  # Keep the report explicit if result extraction fails.
            issues.append(f"could not extract step result content: {exc}")

    return {
        "step": step["step"],
        "subagent": step["subagent"],
        "status": "failed" if issues else "passed",
        "command": f"{sys.executable} -B {step['script'].relative_to(PROJECT_ROOT)}",
        "stdout": stdout,
        "stderr": stderr,
        "outputs": artifacts,
        "results": result_content,
        "metrics": {"return_code": result.returncode},
        "issues": issues,
    }


def append_result_content(lines: list[str], result: dict[str, Any]) -> None:
    lines.extend([f"#### {result['title']}", "", f"Source: `{result['source']}`", ""])
    content = result["content"]
    if isinstance(content, str):
        lines.extend([content, ""])
        return
    lines.extend(["```json", json.dumps(content, indent=2), "```", ""])


def write_final_report(cards: list[dict[str, Any]], output_report: str | Path = DEFAULT_REPORT) -> Path:
    report_path = Path(output_report)
    if not report_path.is_absolute():
        report_path = PROJECT_ROOT / report_path
    report_path.parent.mkdir(parents=True, exist_ok=True)

    passed = sum(1 for card in cards if card.get("status") == "passed")
    lines = [
        "# LLNL CT Pipeline Manager Report",
        "",
        f"Passed steps: {passed}/{len(cards)}",
        "",
    ]

    for index, card in enumerate(cards, start=1):
        lines.extend(
            [
                f"## Step {index}: {card['step']}",
                "",
                f"- Subagent: `{card['subagent']}`",
                f"- Status: `{card['status']}`",
                f"- Command: `{card.get('command', '')}`",
                f"- Return code: `{card.get('metrics', {}).get('return_code', 'n/a')}`",
                "",
                "### Result Artifacts",
                "",
            ]
        )
        outputs = card.get("outputs", [])
        if outputs:
            for artifact in outputs:
                state = "present" if artifact["exists"] else "missing"
                lines.append(
                    f"- `{artifact['path']}` - {state}, {artifact['size_bytes']} bytes"
                )
        else:
            lines.append("- No result artifacts configured for this step.")
        lines.extend(["", "### Result Content", ""])
        results = card.get("results", [])
        if results:
            for result in results:
                append_result_content(lines, result)
        else:
            lines.append("- No result content available for this step.")
        lines.extend(
            [
                "",
                "### Summary Card",
                "",
                "```json",
                json.dumps(card, indent=2),
                "```",
                "",
            ]
        )

    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path


def run_pipeline_manager(output_report: str | Path = DEFAULT_REPORT) -> str:
    cards: list[dict[str, Any]] = []
    for step in PIPELINE_STEPS:
        card = run_pipeline_step(step)
        cards.append(card)
        if card["status"] != "passed":
            break

    report_path = write_final_report(cards, output_report)
    passed = sum(1 for card in cards if card["status"] == "passed")
    if passed == len(PIPELINE_STEPS):
        return f"Pipeline manager passed after {passed} step(s); wrote {report_path}"
    return f"Pipeline manager failed after {len(cards)} step(s); wrote {report_path}"
