import argparse
from pathlib import Path

import numpy as np
import tifffile
from skimage.morphology import skeletonize


def skeletonize_mask(input_filepath: str, output_filepath: str) -> np.ndarray:
    """
    Create and save a skeleton from a 3D segmentation mask.
    
    Args:
        input_filepath: Path to a .npy, .tif, or .tiff 3D mask.
        output_filepath: Path at which to save the skeleton as .npy or TIFF.

    Returns:
        The boolean 3D skeleton array.
    """
    input_path = Path(input_filepath)
    output_path = Path(output_filepath)

    if input_path.suffix.lower() not in {".npy", ".tif", ".tiff"}:
        raise ValueError("input_filepath must end in .npy, .tif, or .tiff")
    if output_path.suffix.lower() not in {".npy", ".tif", ".tiff"}:
        raise ValueError("output_filepath must end in .npy, .tif, or .tiff")
    if not input_path.is_file():
        raise FileNotFoundError(f"segmentation mask not found: {input_path}")
    if input_path.resolve() == output_path.resolve():
        raise ValueError("output_filepath must not overwrite the input mask")

    if input_path.suffix.lower() == ".npy":
        mask = np.load(input_path, mmap_mode="r", allow_pickle=False)
    else:
        mask = tifffile.memmap(input_path)

    if mask.ndim != 3:
        raise ValueError(f"expected a 3D segmentation mask, got shape {mask.shape}")

    result = skeletonize(np.asarray(mask) > 0)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.suffix.lower() == ".npy":
        np.save(output_path, result, allow_pickle=False)
    else:
        tifffile.imwrite(
            output_path,
            result.astype(np.uint8) * 255,
            bigtiff=True,
            photometric="minisblack",
        )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create a 3D skeleton from a binary NPY or TIFF mask."
    )
    parser.add_argument("input", type=Path, help="Input 3D segmentation mask")
    parser.add_argument("output", type=Path, help="Output 3D skeleton")
    args = parser.parse_args()

    result = skeletonize_mask(str(args.input), str(args.output))
    print(
        f"Skeletonized {args.input.resolve()}; saved {args.output.resolve()} "
        f"with shape {result.shape} and {np.count_nonzero(result)} skeleton voxels."
    )


if __name__ == "__main__":
    main()
