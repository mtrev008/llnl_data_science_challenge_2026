from fastmcp import FastMCP
from pathlib import Path

import numpy as np
import tifffile
from matplotlib import image as mpl_image
from skimage.morphology import skeletonize as skeletonize_volume

try:
    from src.skeletonization import skeletonize_mask
except ModuleNotFoundError:  # Supports running this file directly from src/.
    from skeletonization import skeletonize_mask

# Initialize the MCP server
mcp = FastMCP("CT Segmentation")

@mcp.tool()
def segment_ct_dataset(input_filepath: str, output_filepath: str, threshold: float) -> str:
    """
    Segments a 3D CT dataset based on a given density threshold value.
    
    Args:
        input_filepath: Path to the input .npy file containing the 3D CT scan data.
        output_filepath: Path indicating where the segmented .npy file should be saved.
        threshold: The density value to use as a threshold. Voxels >= threshold will be set to 1, others to 0.
    
    Returns:
        A status message indicating success and the save location, or an error message.
    """
    input_path = Path(input_filepath)
    output_path = Path(output_filepath)

    if input_path.suffix.lower() == ".npy":
        volume = np.load(input_path, mmap_mode="r", allow_pickle=False)
    elif input_path.suffix.lower() in {".tif", ".tiff"}:
        volume = tifffile.memmap(input_path)
    else:
        raise ValueError("input_filepath must end in .npy, .tif, or .tiff")

    if volume.ndim != 3:
        raise ValueError(f"expected a 3D CT volume, got shape {volume.shape}")
    if not np.isfinite(threshold):
        raise ValueError("threshold must be finite")

    mask = np.asarray(volume >= threshold, dtype=np.uint8)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.suffix.lower() == ".npy":
        np.save(output_path, mask, allow_pickle=False)
    elif output_path.suffix.lower() in {".tif", ".tiff"}:
        # TIFF viewers generally display uint8 data on a 0-255 scale. Store
        # foreground as 255 so the binary structure is visibly white rather
        # than an almost-black intensity of 1.
        tifffile.imwrite(output_path, mask * np.uint8(255), photometric="minisblack")
    else:
        raise ValueError("output_filepath must end in .npy, .tif, or .tiff")

    return (
        f"Segmented {input_path} at threshold {threshold:.10g}; "
        f"saved {output_path} with shape {mask.shape}."
    )

@mcp.tool()
def visualize_slice(input_filepath: str, output_filepath: str, slice_index: int, axis: int = 0) -> str:
    """
    Loads a 3D CT dataset from a .npy file and saves a visualization of a specific slice to an image file.
    
    Args:
        input_filepath: Path to the input .npy file containing the 3D CT data.
        output_filepath: Path indicating where the output image should be saved (e.g., .png).
        slice_index: The index of the slice to visualize.
        axis: The axis along which to take the slice (0, 1, or 2). Default is 0.
        
    Returns:
        A status message indicating success and the save location, or an error message.
    """
    input_path = Path(input_filepath)
    output_path = Path(output_filepath)

    if input_path.suffix.lower() == ".npy":
        volume = np.load(input_path, mmap_mode="r", allow_pickle=False)
    elif input_path.suffix.lower() in {".tif", ".tiff"}:
        volume = tifffile.memmap(input_path)
    else:
        raise ValueError("input_filepath must end in .npy, .tif, or .tiff")

    if volume.ndim != 3:
        raise ValueError(f"expected a 3D CT volume, got shape {volume.shape}")
    if axis not in (0, 1, 2):
        raise ValueError("axis must be 0, 1, or 2")
    if not 0 <= slice_index < volume.shape[axis]:
        raise IndexError(
            f"slice_index must be between 0 and {volume.shape[axis] - 1} "
            f"for axis {axis}"
        )

    image_slice = np.asarray(np.take(volume, slice_index, axis=axis))
    finite = image_slice[np.isfinite(image_slice)]
    if finite.size == 0:
        raise ValueError("the requested slice contains no finite values")

    lower = float(finite.min())
    upper = float(finite.max())
    if lower == upper:
        display_slice = np.zeros(image_slice.shape, dtype=np.uint8)
    else:
        display_slice = np.clip((image_slice - lower) / (upper - lower), 0, 1)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    mpl_image.imsave(output_path, display_slice, cmap="gray", vmin=0, vmax=1)
    return (
        f"Saved axis {axis} slice {slice_index} from {input_path} "
        f"to {output_path} with shape {image_slice.shape}."
    )

@mcp.tool()
def skeletonize(input_filepath: str, output_filepath: str) -> str:
    """
    Creates a skeleton from a 3D segmentation mask.
    
    Args:
        input_filepath: Path to the .npy file containing the 3D mask.
        output_filepath: Path to save the extracted skeleton (.npy).
        
    Returns:
        A status message indicating success and the save location, or an error message.
    """
    input_path = Path(input_filepath)
    output_path = Path(output_filepath)
    if input_path.suffix.lower() not in {".npy", ".tif", ".tiff"}:
        raise ValueError("input_filepath must end in .npy, .tif, or .tiff")
    if output_path.suffix.lower() != ".npy":
        raise ValueError("output_filepath must end in .npy")
    if not input_path.is_file():
        raise FileNotFoundError(f"segmentation mask not found: {input_path}")

    if input_path.suffix.lower() == ".npy":
        mask = np.load(input_path, mmap_mode="r", allow_pickle=False)
    else:
        mask = tifffile.memmap(input_path)
    if mask.ndim != 3:
        raise ValueError(f"expected a 3D segmentation mask, got shape {mask.shape}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    if input_path.suffix.lower() == ".npy":
        result = skeletonize_mask(str(input_path), str(output_path))
    else:
        result = skeletonize_volume(np.asarray(mask) > 0)
        np.save(output_path, result, allow_pickle=False)
    if result is None:
        raise RuntimeError("skeletonization did not produce an output")

    return (
        f"Skeletonized {input_path}; saved {output_path} with shape "
        f"{result.shape} and {np.count_nonzero(result)} skeleton voxels."
    )

if __name__ == "__main__":
    # Run the FastMCP server, exposing the tools over standard I/O (default)
    mcp.run()
