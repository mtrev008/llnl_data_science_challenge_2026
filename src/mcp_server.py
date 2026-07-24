from fastmcp import FastMCP
from pathlib import Path
from data_validation_agent import (
    profile_json,
    profile_tiff,
)
import json
import matplotlib
from typing import Any  
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np 
import pandas as pd


# Initialize the MCP server
mcp = FastMCP("LLNL CT Analysis Tools")
SUPPORTED_INPUTS = {".npy", ".csv", ".json"}
SUPPORTED_OUTPUTS = {".png", ".svg", ".pdf"}


def _load_numeric_values(
    filepath: str,
    column: str | None,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Load finite numeric values from a supported input file."""
    source = Path(filepath).expanduser().resolve()

    if not source.is_file():
        raise ValueError(f"Input file does not exist: {source}")

    extension = source.suffix.lower()

    if extension not in SUPPORTED_INPUTS:
        raise ValueError(
            f"Unsupported input type '{extension}'. "
            f"Use one of: {', '.join(sorted(SUPPORTED_INPUTS))}"
        )

    if extension == ".npy":
        array = np.load(source, allow_pickle=False)

        if not np.issubdtype(array.dtype, np.number):
            raise ValueError("NPY input must contain numeric values")

        values = array.reshape(-1)
        input_description = {
            "type": "npy",
            "shape": list(array.shape),
        }

    elif extension == ".csv":
        if not column:
            raise ValueError("column is required for CSV input")

        dataframe = pd.read_csv(source)

        if column not in dataframe.columns:
            raise ValueError(
                f"Column '{column}' was not found. "
                f"Available columns: {list(dataframe.columns)}"
            )

        values = pd.to_numeric(
            dataframe[column],
            errors="coerce",
        ).to_numpy()

        input_description = {
            "type": "csv",
            "rows": int(len(dataframe)),
            "column": column,
        }

    else:  # .json
        if not column:
            raise ValueError("column is required for JSON input")

        with source.open("r", encoding="utf-8") as file:
            data = json.load(file)

        if isinstance(data, list):
            dataframe = pd.json_normalize(data)
        elif isinstance(data, dict):
            dataframe = pd.json_normalize(data)
        else:
            raise ValueError("JSON must contain an object or list")

        if column not in dataframe.columns:
            raise ValueError(
                f"Column '{column}' was not found. "
                f"Available columns: {list(dataframe.columns)}"
            )

        values = pd.to_numeric(
            dataframe[column],
            errors="coerce",
        ).to_numpy()

        input_description = {
            "type": "json",
            "rows": int(len(dataframe)),
            "column": column,
        }

    values = np.asarray(values, dtype=float)
    finite_values = values[np.isfinite(values)]

    if finite_values.size == 0:
        raise ValueError("No finite numeric values were found")

    input_description["value_count"] = int(finite_values.size)
    input_description["discarded_value_count"] = int(
        values.size - finite_values.size
    )

    return finite_values, input_description

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

@mcp.tool()
def create_histogram(
    input_filepath: str,
    output_filepath: str,
    column: str | None = None,
    bins: int = 30,
    title: str | None = None,
    x_label: str | None = None,
    threshold: float | None = None,
    show_mean: bool = True,
    show_median: bool = True,
    overwrite: bool = False,
) -> dict[str, Any]:
    """
    Create a histogram from numeric NPY, CSV, or JSON data.

    Args:
        input_filepath:
            Path to the source file. Supported types: .npy, .csv, .json.

        output_filepath:
            Image output path. Supported types: .png, .svg, .pdf.

        column:
            Numeric CSV or JSON field to plot. Required for CSV and JSON;
            ignored for NPY arrays.

        bins:
            Number of histogram bins, from 1 through 1000.

        title:
            Optional plot title.

        x_label:
            Optional horizontal-axis label.

        threshold:
            Optional vertical threshold line. The result includes the
            count and percentage of values greater than or equal to it.

        show_mean:
            Whether to display the mean as a vertical line.

        show_median:
            Whether to display the median as a vertical line.

        overwrite:
            Allow an existing output image to be replaced.

    Returns:
        A dictionary with output location, statistics, warnings, and
        threshold analysis.
    """
    figure = None

    try:
        if not isinstance(bins, int) or isinstance(bins, bool):
            raise ValueError("bins must be an integer")

        if not 1 <= bins <= 1000:
            raise ValueError("bins must be between 1 and 1000")

        output_path = Path(output_filepath).expanduser().resolve()

        if output_path.suffix.lower() not in SUPPORTED_OUTPUTS:
            raise ValueError(
                "Output type must be .png, .svg, or .pdf"
            )

        if output_path.exists() and not overwrite:
            raise ValueError(
                f"Output already exists: {output_path}. "
                "Set overwrite=True to replace it."
            )

        output_path.parent.mkdir(parents=True, exist_ok=True)

        values, input_info = _load_numeric_values(
            input_filepath,
            column,
        )

        mean_value = float(np.mean(values))
        median_value = float(np.median(values))

        if title is None:
            title = f"Distribution of {column or 'values'}"

        if x_label is None:
            x_label = column or "Value"

        figure, axis = plt.subplots(figsize=(9, 6))

        axis.hist(
            values,
            bins=bins,
            color="#4C78A8",
            edgecolor="white",
            alpha=0.9,
        )

        if show_mean:
            axis.axvline(
                mean_value,
                color="#E45756",
                linestyle="--",
                linewidth=2,
                label=f"Mean: {mean_value:.4g}",
            )

        if show_median:
            axis.axvline(
                median_value,
                color="#54A24B",
                linestyle=":",
                linewidth=2,
                label=f"Median: {median_value:.4g}",
            )

        threshold_analysis = None

        if threshold is not None:
            threshold_count = int(
                np.count_nonzero(values >= threshold)
            )

            threshold_analysis = {
                "threshold": float(threshold),
                "comparison": ">=",
                "count": threshold_count,
                "percentage": float(
                    threshold_count / values.size * 100
                ),
            }

            axis.axvline(
                threshold,
                color="#F58518",
                linestyle="-.",
                linewidth=2,
                label=f"Threshold: {threshold:.4g}",
            )

        axis.set_title(title)
        axis.set_xlabel(x_label)
        axis.set_ylabel("Frequency")
        axis.grid(axis="y", alpha=0.25)

        if show_mean or show_median or threshold is not None:
            axis.legend()

        figure.tight_layout()
        figure.savefig(output_path, dpi=200, bbox_inches="tight")

        warnings = []

        if input_info["discarded_value_count"] > 0:
            warnings.append(
                f"Discarded {input_info['discarded_value_count']} "
                "non-finite or non-numeric values."
            )

        return {
            "status": "success",
            "visualization_type": "histogram",
            "input_filepath": str(
                Path(input_filepath).expanduser().resolve()
            ),
            "output_filepath": str(output_path),
            "input_info": input_info,
            "statistics": {
                "count": int(values.size),
                "minimum": float(np.min(values)),
                "maximum": float(np.max(values)),
                "mean": mean_value,
                "median": median_value,
                "standard_deviation": float(
                    np.std(values, ddof=1)
                ) if values.size > 1 else 0.0,
                "q1": float(np.percentile(values, 25)),
                "q3": float(np.percentile(values, 75)),
            },
            "threshold_analysis": threshold_analysis,
            "warnings": warnings,
        }

    except Exception as error:
        return {
            "status": "error",
            "visualization_type": "histogram",
            "error_type": type(error).__name__,
            "error": str(error),
        }

    finally:
        if figure is not None:
            plt.close(figure)

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
