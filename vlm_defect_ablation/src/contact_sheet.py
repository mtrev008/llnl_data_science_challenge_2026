from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
from .stack_builder import SliceStack

def _u8(a: np.ndarray) -> np.ndarray:
    values = a.astype(float, copy=False)
    lo, hi = np.percentile(values, (1, 99)); return np.clip((values - lo) * 255 / max(hi - lo, 1), 0, 255).astype("uint8")

def create_contact_sheet(stack: SliceStack, output: Path, max_dimension: int = 2048) -> dict:
    h, w = stack.original_dimensions; scale = min(1.0, max_dimension / max(w * 7, h + 28)); size = (max(1, int(w * scale)), max(1, int(h * scale)))
    sheet = Image.new("RGB", (size[0] * 7, size[1] + 28), "white"); draw = ImageDraw.Draw(sheet)
    for i, (z, array) in enumerate(zip(stack.indices, stack.arrays)):
        im = Image.fromarray(_u8(array)).resize(size, Image.Resampling.LANCZOS).convert("RGB"); sheet.paste(im, (i * size[0], 28))
        draw.text((i * size[0] + 2, 2), f"z={z}" + (" CENTER" if z == stack.center_slice else ""), fill="red" if z == stack.center_slice else "black")
    output.parent.mkdir(parents=True, exist_ok=True); sheet.save(output)
    return {"path": str(output), "original_dimensions": [h, w], "resized_dimensions": list(size), "scale": scale}
