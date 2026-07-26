from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPORT_PATH = PROJECT_ROOT / "reports/report.md"


def run_step(step: str, script: Path) -> dict:
    env = os.environ.copy()
    env.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")
    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=PROJECT_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        return {
            "step": step,
            "subagent": str(script.parent.relative_to(PROJECT_ROOT)),
            "status": "failed",
            "outputs": [],
            "metrics": {},
            "issues": [result.stderr.strip() or result.stdout.strip() or "step failed"],
        }
    for line in reversed(result.stdout.splitlines()):
        line = line.strip()
        if line.startswith("{") and line.endswith("}"):
            return json.loads(line)
    return {
        "step": step,
        "subagent": str(script.parent.relative_to(PROJECT_ROOT)),
        "status": "failed",
        "outputs": [],
        "metrics": {},
        "issues": ["step completed but did not emit a JSON summary card"],
    }


def main() -> None:
    sys.path.insert(0, str(PROJECT_ROOT))
    from src.workflow_tools import write_final_report

    steps = [
        ("Data Analyzer", PROJECT_ROOT / ".codex/agents/data_analyzer/run.py"),
        ("Segmentation", PROJECT_ROOT / ".codex/agents/segmentation/run.py"),
        ("Skeletonization", PROJECT_ROOT / ".codex/agents/skeletonization/run.py"),
        ("Detecting Defects", PROJECT_ROOT / ".codex/agents/defect_detection/run.py"),
        ("Visualization", PROJECT_ROOT / ".codex/agents/visualization/run.py"),
    ]
    cards = []
    for step, script in steps:
        card = run_step(step, script)
        cards.append(card)
        if card["status"] != "passed":
            break
    write_final_report(cards, REPORT_PATH)
    print(f"Final report: {REPORT_PATH}")


if __name__ == "__main__":
    main()
