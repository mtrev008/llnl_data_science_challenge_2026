from fastmcp import FastMCP
from pathlib import Path
from data_validation_agent import (
    profile_json,
    profile_tiff,
)


# Initialize the MCP server
mcp = FastMCP("LLNL CT Analysis Tools")

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
    pass # Implementation goes here

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

@mcp.tool()
def inspect_lattice_dataset(
    tiff_filepath: str,
    json_filepath: str,
    output_directory: str,
) -> dict:
    """
    Validate and statistically profile a lattice CT TIFF and JSON graph.
    """

    tiff_path = Path(tiff_filepath)
    json_path = Path(json_filepath)
    output_path = Path(output_directory)

    plot_directory = output_path / "plots"
    csv_directory = output_path / "csv"

    tiff_result = profile_tiff(
        tiff_path,
        plot_directory,
        csv_directory,
    )

    json_result, _ = profile_json(
        json_path,
        plot_directory,
    )

    return {
        "tiff": tiff_result,
        "json": json_result,
    }



"""
@mcp.tool()
def validate_lattice_dataset(
    tiff_filepath: str,
    json_filepath: str,
    output_directory: str,
) -> dict:
    
    Validate an X-ray CT TIFF and registered lattice JSON.

    Checks TIFF integrity, JSON graph integrity, endpoint references,
    coordinate availability, and basic TIFF-to-JSON spatial compatibility.

    Parameters
    ----------
    tiff_filepath:
        Path to the CT .tif or .tiff file.

    json_filepath:
        Path to the registered lattice graph .json file.

    output_directory:
        Directory where validation_report.json and
        validation_report.md will be saved.

    Returns
    -------
    dict
        Validation decision, error count, warning count, and report paths.
    

    report = validate_dataset(
        Path(tiff_filepath),
        Path(json_filepath),
        Path(output_directory),
    )

    return {
        "decision": report["decision"],
        "error_count": len(report["all_errors"]),
        "warning_count": len(report["all_warnings"]),
        "json_report": str(
            Path(output_directory) / "validation_report.json"
        ),
        "markdown_report": str(
            Path(output_directory) / "validation_report.md"
        ),
    }
"""
if __name__ == "__main__":
    # Run the FastMCP server, exposing the tools over standard I/O (default)
    mcp.run()
