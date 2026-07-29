from fastmcp import FastMCP
import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib-cache")

import numpy as np
import tifffile
from matplotlib import image as mpl_image

try:
    from src.registration_workflow import (
        DEFAULT_CELL_ARRANGEMENT,
        DEFAULT_CT_SPACING,
        DEFAULT_JSON_PATH,
        DEFAULT_JSON_SPACING,
        DEFAULT_OUTPUT_DIR,
        DEFAULT_TIFF_PATH,
        RegistrationConfig,
        run_registration_workflow,
    )
    from src.workflow_tools import run_pipeline_manager as run_pipeline_manager_impl
    from src.skeletonization import skeletonize_mask
except ModuleNotFoundError:  # Supports running this file directly from src/.
    from registration_workflow import (
        DEFAULT_CELL_ARRANGEMENT,
        DEFAULT_CT_SPACING,
        DEFAULT_JSON_PATH,
        DEFAULT_JSON_SPACING,
        DEFAULT_OUTPUT_DIR,
        DEFAULT_TIFF_PATH,
        RegistrationConfig,
        run_registration_workflow,
    )
    from workflow_tools import run_pipeline_manager as run_pipeline_manager_impl
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
        input_filepath: Path to the .npy, .tif, or .tiff file containing the 3D mask.
        output_filepath: Path to save the extracted skeleton (.npy, .tif, or .tiff).
        
    Returns:
        A status message indicating success and the save location, or an error message.
    """
    result = skeletonize_mask(input_filepath, output_filepath)

    return (
        f"Skeletonized {input_filepath}; saved {output_filepath} with shape "
        f"{result.shape} and {np.count_nonzero(result)} skeleton voxels."
    )

@mcp.tool()
def run_pipeline_manager(output_report: str = "reports/report.md") -> str:
    """
    Runs the ordered LLNL CT pipeline manager and writes one final report.

    Args:
        output_report: Path to the consolidated Markdown report.

    Returns:
        A status message with the pipeline result and report path.
    """
    return run_pipeline_manager_impl(output_report)


@mcp.tool()
def register_lattice_to_ct(
    json_filepath: str = str(DEFAULT_JSON_PATH),
    tif_filepath: str = str(DEFAULT_TIFF_PATH),
    output_directory: str = str(DEFAULT_OUTPUT_DIR),
    ct_spacing_x: float = DEFAULT_CT_SPACING[0],
    ct_spacing_y: float = DEFAULT_CT_SPACING[1],
    ct_spacing_z: float = DEFAULT_CT_SPACING[2],
    json_spacing: float = DEFAULT_JSON_SPACING,
    cells_x: int = DEFAULT_CELL_ARRANGEMENT[0],
    cells_y: int = DEFAULT_CELL_ARRANGEMENT[1],
    cells_z: int = DEFAULT_CELL_ARRANGEMENT[2],
    downsample: int = 1,
) -> str:
    """
    Runs the 7-stage rigid lattice-registration workflow for a CT TIFF stack.

    Args:
        json_filepath: Path to the nominal lattice JSON graph.
        tif_filepath: Path to the 3D CT TIFF stack.
        output_directory: Directory where registration artifacts will be written.
        ct_spacing_x: CT voxel spacing along x in physical units.
        ct_spacing_y: CT voxel spacing along y in physical units.
        ct_spacing_z: CT voxel spacing along z in physical units.
        json_spacing: Multiplier converting nominal JSON positions into CT physical units.
        cells_x: Unit cells present in the scan along x.
        cells_y: Unit cells present in the scan along y.
        cells_z: Unit cells present in the scan along z.
        downsample: Integer CT downsampling factor used before segmentation and junction search.

    Returns:
        A status string summarizing the registration result and output paths.
    """
    config = RegistrationConfig(
        json_path=Path(json_filepath),
        tif_path=Path(tif_filepath),
        output_dir=Path(output_directory),
        ct_spacing=(float(ct_spacing_x), float(ct_spacing_y), float(ct_spacing_z)),
        json_spacing=float(json_spacing),
        cells=(int(cells_x), int(cells_y), int(cells_z)),
        downsample=int(downsample),
    )
    result = run_registration_workflow(config)
    metrics = result["metrics"]
    return (
        f"Registration passed for {json_filepath} against {tif_filepath}; "
        f"matched {metrics['matched_junctions']} junctions with RMSE {metrics['rmse']:.6g}. "
        f"Saved outputs under {output_directory}, including "
        f"{result['artifacts']['registered_lattice']}."
    )

if __name__ == "__main__":
    # Run the FastMCP server, exposing the tools over standard I/O (default)
    mcp.run()
