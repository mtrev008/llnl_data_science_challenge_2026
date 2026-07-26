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
            "data/missing_struts/analysis/observed_lattice.json",
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
            "data/missing_struts/analysis/raw_slice_380.png",
            "data/missing_struts/analysis/segmentation_view_a.png",
            "data/missing_struts/analysis/segmentation_view_b.png",
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
        per_strut = read_json_result("data/missing_struts/analysis/per_strut_defects.json")
        anomaly_examples = [item for item in per_strut if item["classification"] != "present"][:10]
        compact_examples = [
            {
                "strut_id": item["strut_id"],
                "classification": item["classification"],
                "reason": item["reason"],
                "coverage_ratio": item["coverage_ratio"],
                "profile_classification": item.get("profile_classification"),
                "profile_mean": item.get("profile_mean"),
                "profile_min": item.get("profile_min"),
                "low_profile_segments": item.get("low_profile_segments"),
                "longest_low_profile_gap": item.get("longest_low_profile_gap"),
                "profile_plot": item.get("profile_plot"),
                "visual_evidence_png": item.get("visual_evidence_png"),
            }
            for item in anomaly_examples
        ]
        return [
            {
                "title": "Anomaly summary",
                "source": "data/missing_struts/analysis/anomaly_summary.json",
                "content": read_json_result("data/missing_struts/analysis/anomaly_summary.json"),
            },
            {
                "title": "Visual review index",
                "source": "data/missing_struts/analysis/defect_visual_review/visual_review_index.json",
                "content": read_json_result(
                    "data/missing_struts/analysis/defect_visual_review/visual_review_index.json"
                ),
            },
            {
                "title": "Hugging Face model review results",
                "source": "data/missing_struts/analysis/defect_visual_review/hf_model_review_results.json",
                "content": read_json_result(
                    "data/missing_struts/analysis/defect_visual_review/hf_model_review_results.json"
                ),
            },
            {
                "title": "Example per-strut classifications",
                "source": "data/missing_struts/analysis/per_strut_defects.json",
                "content": {
                    "total_records": len(per_strut),
                    "first_10_anomalies": compact_examples,
                },
            },
            {
                "title": "Anomaly Markdown summary",
                "source": "data/missing_struts/analysis/anomaly_summary.md",
                "content": read_markdown_result("data/missing_struts/analysis/anomaly_summary.md"),
            },
        ]
    if step_name == "Visualization":
        return [
            {
                "title": "Raw slice visualization",
                "source": "data/missing_struts/analysis/raw_slice_380.png",
                "content": summarize_png("data/missing_struts/analysis/raw_slice_380.png"),
            },
            {
                "title": "Segmentation view A",
                "source": "data/missing_struts/analysis/segmentation_view_a.png",
                "content": summarize_png("data/missing_struts/analysis/segmentation_view_a.png"),
            },
            {
                "title": "Segmentation view B",
                "source": "data/missing_struts/analysis/segmentation_view_b.png",
                "content": summarize_png("data/missing_struts/analysis/segmentation_view_b.png"),
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
