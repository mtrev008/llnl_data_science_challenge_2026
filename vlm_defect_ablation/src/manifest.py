from pathlib import Path
import json

def save_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True); path.write_text(json.dumps(value, indent=2, default=str), encoding="utf-8")

def create_manifest(condition: str, center: int, files: list[Path], permitted: dict, attempt: int) -> dict:
    return {"condition": condition, "center_slice": center, "attempt": attempt, "files": [{"name": p.name, "path": str(p)} for p in files], "permitted_context": permitted}
