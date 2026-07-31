from __future__ import annotations

import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.fewshot_strut_classifier import FewShotConfig, run_fewshot_strut_classifier


def main() -> None:
    result = run_fewshot_strut_classifier(FewShotConfig())
    print("Few-Shot Strut Classifier pipeline step")
    print(
        json.dumps(
            {
                "status": result["status"],
                "output_json": "data/missing_struts/analysis/per_strut_fewshot_defects.json",
                "example_manifest": "data/missing_struts/analysis/fewshot_strut_classifier/example_manifest.json",
            }
        )
    )


if __name__ == "__main__":
    main()
