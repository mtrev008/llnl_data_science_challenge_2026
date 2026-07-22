from fastmcp import FastMCP
from pathlib import Path
import numpy as np

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
    input_path = Path(input_filepath).resolve()
    output_path = Path(output_filepath).resolve()


    if not input_path.is_file():
        raise FileNotFoundError(f"Input CT volume does not exist: {input_path}")


    if input_path.suffix.lower() != ".npy":
        raise ValueError(f"Input must be a .npy file: {input_path}")


    if output_path.suffix.lower() != ".npy":
        raise ValueError(f"Output must be a .npy file: {output_path}")


    volume = np.load(input_path, allow_pickle=False)


    if volume.ndim != 3:
        raise ValueError(
            f"Expected a 3D CT volume, but received shape {volume.shape}"
        )


    if not np.issubdtype(volume.dtype, np.number):
        raise TypeError(
            f"Expected numeric CT data, but received dtype {volume.dtype}"
        )


    mask = volume >= threshold


    output_path.parent.mkdir(parents=True, exist_ok=True)
    np.save(output_path, mask, allow_pickle=False)


    foreground_voxels = int(np.count_nonzero(mask))
    foreground_fraction = foreground_voxels / mask.size


    return (
        f"Saved segmentation to {output_path}. "
        f"Threshold={threshold}, shape={mask.shape}, "
        f"foreground_voxels={foreground_voxels}, "
        f"foreground_fraction={foreground_fraction:.6f}"
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
    pass # Implementation goes here

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
    pass # Implementation goes here, calling skeletonize_mask internally

if __name__ == "__main__":
    # Run the FastMCP server, exposing the tools over standard I/O (default)
    mcp.run()
