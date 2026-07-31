from dataclasses import dataclass
import random
import numpy as np

@dataclass(frozen=True)
class SliceStack:
    center_slice: int
    indices: tuple[int, ...]
    arrays: np.ndarray
    original_dimensions: tuple[int, int]

def valid_centers(depth: int, size: int = 7, stride: int = 1) -> list[int]:
    half = size // 2
    return list(range(half, depth - half, stride))

def select_centers(depth: int, stacks: dict, override: list[int] | None = None) -> list[int]:
    valid = valid_centers(depth, int(stacks.get("size", 7)), int(stacks.get("stride", 1)))
    requested = override if override is not None else stacks.get("center_slices") or []
    if requested: return [int(x) for x in requested if int(x) in set(valid)]
    if stacks.get("center_range"):
        a, b = stacks["center_range"]; return [z for z in valid if int(a) <= z <= int(b)]
    if stacks.get("random_count"):
        return sorted(random.Random(int(stacks.get("random_seed", 42))).sample(valid, min(int(stacks["random_count"]), len(valid))))
    return valid

def build_stack(volume: np.ndarray, center: int, size: int = 7) -> SliceStack:
    half = size // 2; indices = tuple(range(center - half, center + half + 1))
    if size != 7 or min(indices) < 0 or max(indices) >= volume.shape[0]: raise ValueError("invalid seven-slice center")
    arrays = np.asarray(volume[list(indices)]).copy()
    return SliceStack(center, indices, arrays, tuple(arrays.shape[1:]))
