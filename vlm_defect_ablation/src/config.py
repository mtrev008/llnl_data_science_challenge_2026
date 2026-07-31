from __future__ import annotations
from pathlib import Path
from typing import Any
import yaml

CONDITIONS = ("images_only", "images_segmentation", "images_geometry", "images_segmentation_geometry", "images_paper", "full_context")

def load_config(path: str | Path) -> dict[str, Any]:
    config = yaml.safe_load(Path(path).read_text()) or {}
    for key in ("data", "volume", "stacks", "geometry", "segmentation", "paper", "experiment", "vlm", "execution"):
        config.setdefault(key, {})
    config["data"]["output_dir"] = str(config["data"].get("output_dir", "outputs"))
    config["stacks"].setdefault("size", 7); config["stacks"].setdefault("stride", 1)
    config["stacks"].setdefault("random_seed", 42); config["experiment"].setdefault("conditions", list(CONDITIONS))
    config["geometry"].setdefault("registered_to_tiff", False); config["vlm"].setdefault("provider", "mock")
    config["segmentation"].setdefault("on_the_fly", False)
    config["vlm"].setdefault("model", "mock-vlm"); config["execution"].setdefault("timeout_seconds", 120)
    validate_config(config)
    return config

def validate_config(c: dict[str, Any]) -> None:
    if c["stacks"]["size"] != 7: raise ValueError("this experiment requires seven-slice stacks")
    if int(c["stacks"]["stride"]) < 1: raise ValueError("stride must be positive")
    unknown = set(c["experiment"]["conditions"]) - set(CONDITIONS)
    if unknown: raise ValueError(f"unknown conditions: {sorted(unknown)}")
    if not c["data"].get("tiff_path"): raise ValueError("data.tiff_path is required")
