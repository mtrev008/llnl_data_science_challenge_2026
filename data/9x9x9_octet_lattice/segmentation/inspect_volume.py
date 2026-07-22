from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import tifffile


def main() -> None:
    input_path = Path(__file__).resolve().parent.parent / "9x9x9_octet_lattice.tif"
    output_dir = Path(__file__).resolve().parent
    volume = tifffile.imread(input_path)
    volume_f = volume.astype(np.float32, copy=False)
    p1, p99 = np.percentile(volume_f, [1, 99.5])

    fig, axes = plt.subplots(2, 3, figsize=(15, 9), constrained_layout=True)
    slice_indices = [0, volume.shape[0] // 4, 380, volume.shape[0] // 2, (3 * volume.shape[0]) // 4, volume.shape[0] - 1]
    for ax, idx in zip(axes.flat, slice_indices):
        ax.imshow(volume[idx], cmap="gray", vmin=p1, vmax=p99)
        ax.set_title(f"slice {idx}")
        ax.axis("off")
    fig.savefig(output_dir / "raw_representative_slices.png", dpi=160)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 5), constrained_layout=True)
    ax.hist(volume_f.ravel()[::32], bins=256, color="black")
    ax.set_title("Intensity histogram (1/32 sample)")
    ax.set_xlabel("intensity")
    ax.set_ylabel("count")
    fig.savefig(output_dir / "raw_histogram.png", dpi=160)
    plt.close(fig)


if __name__ == "__main__":
    main()
