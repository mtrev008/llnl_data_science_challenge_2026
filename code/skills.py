import json
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from fastmcp import FastMCP


mcp = FastMCP("Visualization Agent")


def load_reports(validation_report: str) -> dict:
    """
    Reads a report from the data agent, or any other agents regarding their statistics to create visualizations
    """
    report_path = Path(validation_report).expanduser().resolve()

    if not report_path.exists():
        raise ValueError("Validation Report does not exist")

    if report_path.suffix.lower() != ".json":
        raise ValueError("Must be in .json format")

    with report_path.open("r", encoding="utf-8") as file:
        report = json.load(file)

    return report


def find_filepath(report: dict[str, Any], source_name: str) -> Path:
    files = report["files"]

    if source_name not in files:
        raise ValueError("Source name was not found")

    source_information = files[source_name]

    if "filepath" not in source_information:
        raise ValueError("Source does not contain a filepath")

    source_path = Path(
        source_information["filepath"]
    ).expanduser().resolve()

    if not source_path.exists():
        raise ValueError("Source file does not exist")

    return source_path


def load_numeric_values(
    source_filepath: Path,
    column: str | None
) -> np.ndarray:
    extension = source_filepath.suffix.lower()

    if extension == ".npy":
        array = np.load(source_filepath, allow_pickle=False)
        values = array.reshape(-1)

    elif extension == ".csv":
        dataframe = pd.read_csv(source_filepath)

        if column is None:
            raise ValueError("A column is required")

        if column not in dataframe.columns:
            raise ValueError("Column was not found")

        values = pd.to_numeric(
            dataframe[column],
            errors="coerce"
        ).to_numpy()

    elif extension == ".json":
        with source_filepath.open("r", encoding="utf-8") as file:
            json_data = json.load(file)

        if isinstance(json_data, list):
            dataframe = pd.json_normalize(json_data)

        elif isinstance(json_data, dict):
            try:
                dataframe = pd.DataFrame(json_data)
            except ValueError:
                dataframe = pd.json_normalize(json_data)

        else:
            raise ValueError(
                "The JSON file must contain a list or dictionary"
            )

        if column is None:
            raise ValueError("A column is required")

        if column not in dataframe.columns:
            raise ValueError(f"Column {column} was not found")

        values = pd.to_numeric(
            dataframe[column],
            errors="coerce"
        ).to_numpy()

    else:
        raise ValueError("Unsupported source type")

    values = np.asarray(values, dtype=float)
    values = values[np.isfinite(values)]

    if values.size == 0:
        raise ValueError(
            "The selected data has no valid numeric values"
        )

    return values


@mcp.tool()
def create_histogram(
    validation_report_filepath: str,
    source_name: str,
    output_filepath: str,
    column: str | None = None,
    bins: int = 30,
    title: str | None = None,
    x_axis_label: str | None = None,
    threshold: float | None = None,
    show_mean: bool = True,
    show_median: bool = True
) -> dict[str, Any]:
    try:
        if bins < 1 or bins > 1000:
            raise ValueError(
                "The number of bins must be between 1 and 1000"
            )

        report = load_reports(validation_report_filepath)
        source_filepath = find_filepath(report, source_name)
        values = load_numeric_values(source_filepath, column)

        output_path = Path(
            output_filepath
        ).expanduser().resolve()

        output_path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        mean_value = float(np.mean(values))
        median_value = float(np.median(values))

        standard_deviation = (
            float(np.std(values, ddof=1))
            if values.size > 1
            else 0.0
        )

        q1 = float(np.percentile(values, 25))
        q3 = float(np.percentile(values, 75))

        figure, axis = plt.subplots(figsize=(9, 6))

        axis.hist(
            values,
            bins=bins,
            edgecolor="pink",
            alpha=0.8
        )

        if show_mean:
            axis.axvline(
                mean_value,
                linestyle="--",
                linewidth=2,
                label=f"Mean: {mean_value:.4g}"
            )

        if show_median:
            axis.axvline(
                median_value,
                linestyle="--",
                linewidth=2,
                label=f"Median: {median_value:.4g}"
            )

        values_above_threshold = None
        percentage_above_threshold = None

        if threshold is not None:
            axis.axvline(
                threshold,
                linestyle="-.",
                linewidth=2,
                label=f"Threshold: {threshold:.4g}"
            )

            values_above_threshold = int(
                np.count_nonzero(values >= threshold)
            )

            percentage_above_threshold = float(
                values_above_threshold / values.size * 100
            )

        if title is None:
            if column is not None:
                title = f"Distribution of {column}"
            else:
                title = f"Intensity Distribution: {source_name}"

        if x_axis_label is None:
            x_axis_label = column or "Voxel Intensity"

        axis.set_title(title)
        axis.set_xlabel(x_axis_label)
        axis.set_ylabel("Frequency")
        axis.grid(axis="y", alpha=0.25)

        if show_mean or show_median or threshold is not None:
            axis.legend()

        figure.tight_layout()

        figure.savefig(
            output_path,
            dpi=200,
            bbox_inches="tight"
        )

        plt.close(figure)

        return {
            "status": "success",
            "visualization_type": "histogram",
            "source_name": source_name,
            "source_filepath": str(source_filepath),
            "output_filepath": str(output_path),
            "column": column,
            "parameters": {
                "bins": bins,
                "threshold": threshold,
                "show_mean": show_mean,
                "show_median": show_median
            },
            "statistics": {
                "count": int(values.size),
                "minimum": float(np.min(values)),
                "maximum": float(np.max(values)),
                "mean": mean_value,
                "median": median_value,
                "standard_deviation": standard_deviation,
                "q1": q1,
                "q3": q3
            },
            "threshold_analysis": {
                "values_at_or_above_threshold":
                    values_above_threshold,
                "percentage_at_or_above_threshold":
                    percentage_above_threshold
            } if threshold is not None else None,
            "warnings": []
        }

    except Exception as error:
        return {
            "status": "error",
            "visualization_type": "histogram",
            "error": str(error)
        }        





