from pathlib import Path
import numpy as np
import tifffile

def load_volume(path: str | Path) -> np.ndarray:
    p = Path(path)
    if not p.is_file(): raise FileNotFoundError(p)
    try: volume = tifffile.memmap(p)
    except Exception: volume = tifffile.imread(p)
    if volume.ndim != 3: raise ValueError(f"expected a 3-D multipage TIFF, got {volume.shape}")
    return volume

def inspect_tiff(path: str | Path) -> dict:
    volume = load_volume(path)
    return {"path": str(path), "shape": list(volume.shape), "dtype": str(volume.dtype), "slice_count": int(volume.shape[0])}
