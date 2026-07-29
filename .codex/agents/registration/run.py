from __future__ import annotations

import json
import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]


def main() -> None:
    sys.path.insert(0, str(PROJECT_ROOT))
    os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib-cache")

    from src.registration_workflow import RegistrationConfig, run_registration_workflow

    result = run_registration_workflow(RegistrationConfig())
    print("Registration pipeline step")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
