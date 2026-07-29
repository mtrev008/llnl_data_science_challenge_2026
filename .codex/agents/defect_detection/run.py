from __future__ import annotations

import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.defect_method_comparison import run_defect_method_comparison


def main() -> None:
    summary = run_defect_method_comparison()
    print("Detecting Defects pipeline step")
    print(json.dumps({"status": "passed", **summary}))


if __name__ == "__main__":
    main()
