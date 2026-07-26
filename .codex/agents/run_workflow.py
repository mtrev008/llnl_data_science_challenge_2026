import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    sys.path.insert(0, str(PROJECT_ROOT))
    from src.workflow_tools import run_pipeline_manager

    print(run_pipeline_manager("reports/report.md"))


if __name__ == "__main__":
    main()
