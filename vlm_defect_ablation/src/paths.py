from pathlib import Path

def run_dir(output_dir: Path, condition: str, center: int, attempt: int = 1) -> Path:
    return output_dir / condition / f"center_{center:06d}" / f"attempt_{attempt:02d}"

def safe_child(root: Path, value: str) -> Path:
    result = (root / value).resolve()
    if root.resolve() not in result.parents and result != root.resolve():
        raise ValueError("path traversal is forbidden")
    return result
