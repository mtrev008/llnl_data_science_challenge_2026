import os

import matplotlib.pyplot as plt
import numpy as np
from fastmcp import FastMCP

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
    try:
        data = np.load(input_filepath)
        segmentation = data >= threshold

        os.makedirs(os.path.dirname(os.path.abspath(output_filepath)), exist_ok=True)
        np.save(output_filepath, segmentation)

        foreground_voxels = int(np.count_nonzero(segmentation))
        total_voxels = int(segmentation.size)
        foreground_fraction = foreground_voxels / total_voxels

        return (
            f"Saved segmentation to {output_filepath}. "
            f"Threshold: {threshold}. "
            f"Foreground voxels: {foreground_voxels}/{total_voxels} "
            f"({foreground_fraction:.4%})."
        )
    except Exception as exc:
        return f"Error segmenting CT dataset: {exc}"

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
    try:
        data = np.load(input_filepath)

        if data.ndim != 3:
            return f"Error visualizing slice: expected a 3D array, got shape {data.shape}."
        if axis not in (0, 1, 2):
            return f"Error visualizing slice: axis must be 0, 1, or 2, got {axis}."
        if not 0 <= slice_index < data.shape[axis]:
            return (
                f"Error visualizing slice: slice_index must be in "
                f"[0, {data.shape[axis] - 1}] for axis {axis}, got {slice_index}."
            )

        image = np.take(data, slice_index, axis=axis)
        os.makedirs(os.path.dirname(os.path.abspath(output_filepath)), exist_ok=True)

        plt.figure(figsize=(6, 6))
        plt.imshow(image, cmap="gray")
        plt.axis("off")
        plt.tight_layout(pad=0)
        plt.savefig(output_filepath, bbox_inches="tight", pad_inches=0)
        plt.close()

        return f"Saved slice {slice_index} along axis {axis} to {output_filepath}."
    except Exception as exc:
        return f"Error visualizing slice: {exc}"

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
    try:
        os.makedirs(os.path.dirname(os.path.abspath(output_filepath)), exist_ok=True)
        skeleton = skeletonize_mask(input_filepath, output_filepath)
        if skeleton is None:
            return f"Error skeletonizing mask: failed to load {input_filepath}."
        return (
            f"Saved skeleton to {output_filepath}. "
            f"Skeleton voxels: {int(np.count_nonzero(skeleton))}."
        )
    except Exception as exc:
        return f"Error skeletonizing mask: {exc}"

if __name__ == "__main__":
    # Run the FastMCP server, exposing the tools over standard I/O (default)
    mcp.run()
