import json
from pathlib import Path

import numpy as np


HERE = Path(__file__).resolve().parent
INPUT = HERE / "octet_truss_8x8x8.json"
OUTPUT = HERE / "octet_truss_8x8x8_segmented.npz"
RESOLUTION = 256


def main() -> None:
    with INPUT.open() as stream:
        geometry = json.load(stream)

    junctions = {item["id"]: np.asarray(item["position"], dtype=np.float64)
                 for item in geometry["junctions"]}
    positions = np.stack(list(junctions.values()))
    lower = positions.min(axis=0)
    upper = positions.max(axis=0)
    spacing = (upper - lower) / RESOLUTION
    mask = np.zeros((RESOLUTION, RESOLUTION, RESOLUTION), dtype=np.uint8)

    for strut in geometry["struts"]:
        start = junctions[strut["junction0"]]
        end = junctions[strut["junction1"]]
        radius = float(strut["thickness"])

        lo = np.maximum(0, np.floor((np.minimum(start, end) - radius - lower) / spacing).astype(int))
        hi = np.minimum(RESOLUTION - 1,
                        np.floor((np.maximum(start, end) + radius - lower) / spacing).astype(int))
        axes = [lower[d] + (np.arange(lo[d], hi[d] + 1) + 0.5) * spacing[d]
                for d in range(3)]
        x, y, z = np.meshgrid(*axes, indexing="ij")
        points = np.stack((x, y, z), axis=-1)

        direction = end - start
        length_squared = float(direction @ direction)
        projection = np.clip(((points - start) @ direction) / length_squared, 0.0, 1.0)
        closest = start + projection[..., None] * direction
        inside = np.sum((points - closest) ** 2, axis=-1) <= radius ** 2
        block = mask[lo[0]:hi[0] + 1, lo[1]:hi[1] + 1, lo[2]:hi[2] + 1]
        block[inside] = 1

    np.savez_compressed(OUTPUT, mask=mask)
    print(f"Saved {OUTPUT}")
    print(f"shape={mask.shape} dtype={mask.dtype} foreground={np.count_nonzero(mask)}")


if __name__ == "__main__":
    main()
