from pathlib import Path
import numpy as np
from PIL import Image
from .tiff_loader import load_volume

def load_masks(path: str | Path, indices: tuple[int, ...]) -> np.ndarray:
    p = Path(path)
    if p.is_dir():
        candidates = []
        for i in indices:
            match = sorted(p.glob(f"*{i:06d}*"))
            if not match: raise FileNotFoundError(f"no mask image for slice {i} in {p}")
            candidates.append(match[0])
        return np.asarray([np.asarray(Image.open(x)) > 0 for x in candidates])
    volume = load_volume(p); return np.asarray(volume[list(indices)] > 0)

def auto_segment(arrays: np.ndarray) -> tuple[np.ndarray, dict]:
    threshold = float(np.percentile(arrays, 70)); mask = arrays > threshold
    return mask, {"method": "percentile", "threshold": threshold, "foreground_fraction": float(mask.mean())}
