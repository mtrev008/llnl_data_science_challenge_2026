"""Export a CT segmentation mask as a traceable as-built STL surface."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import sys
import tempfile
from typing import Any

os.environ.setdefault(
    "MPLCONFIGDIR",
    str(Path(tempfile.gettempdir()) / "llnl-visualization-matplotlib"),
)

import numpy as np
import tifffile


TIFF_SUFFIXES = {".tif", ".tiff"}
MAX_COMPONENT_INVENTORY_BYTES = 256 * 1024 * 1024
MAX_PREVIEW_FACES = 50_000
PREVIEW_COLOR = "#4C78A8"


def source_path(value: str) -> Path:
    path = Path(value).expanduser().resolve()
    if not path.is_file():
        raise ValueError(f"Input file does not exist: {path}")
    if path.suffix.lower() not in TIFF_SUFFIXES:
        raise ValueError("Segmentation mask must use .tif or .tiff")
    return path


def writable_output(
    value: str,
    suffixes: set[str],
    overwrite: bool,
    label: str,
) -> Path:
    path = Path(value).expanduser().resolve()
    if path.suffix.lower() not in suffixes:
        expected = ", ".join(sorted(suffixes))
        raise ValueError(f"{label} must use one of: {expected}")
    if path.exists() and not overwrite:
        raise ValueError(f"Output already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def validate_voxel_size(values: tuple[float, float, float]) -> tuple[float, float, float]:
    spacing = tuple(float(value) for value in values)
    if len(spacing) != 3 or not all(math.isfinite(value) and value > 0 for value in spacing):
        raise ValueError("voxel_size_xyz must contain three finite positive values")
    return spacing


def inspect_mask(path: Path, requested_threshold: float | None) -> dict[str, Any]:
    with tifffile.TiffFile(path) as tiff:
        if not tiff.pages:
            raise ValueError("Segmentation TIFF contains no pages")
        series = tiff.series[0]
        shape = tuple(int(value) for value in series.shape)
        dtype = np.dtype(series.dtype)
        if len(shape) != 3:
            raise ValueError(f"Expected a 3D mask, got shape {shape}")
        page_shapes = {tuple(int(value) for value in page.shape) for page in tiff.pages}
        page_dtypes = {np.dtype(page.dtype).str for page in tiff.pages}
        if len(page_shapes) != 1 or len(page_dtypes) != 1:
            raise ValueError("TIFF pages do not have consistent shapes and dtypes")

    unique_values: set[float] = set()
    foreground_voxels = 0
    total_voxels = int(np.prod(shape, dtype=np.int64))
    threshold = requested_threshold
    if threshold is not None and not math.isfinite(float(threshold)):
        raise ValueError("mask_threshold must be finite")

    with tifffile.TiffFile(path) as tiff:
        for page in tiff.pages:
            values = np.asarray(page.asarray())
            if not np.issubdtype(values.dtype, np.number) and values.dtype != np.bool_:
                raise ValueError("Segmentation mask must be numeric or boolean")
            current = np.unique(values)
            if len(unique_values) <= 3:
                unique_values.update(float(value) for value in current[:4])
            if threshold is not None:
                foreground_voxels += int(np.count_nonzero(values > threshold))

    sorted_unique = sorted(unique_values)
    if threshold is None:
        if len(sorted_unique) != 2:
            raise ValueError(
                "A non-binary mask requires an explicit mask_threshold"
            )
        threshold = float((sorted_unique[0] + sorted_unique[1]) / 2.0)
        with tifffile.TiffFile(path) as tiff:
            foreground_voxels = sum(
                int(np.count_nonzero(page.asarray() > threshold))
                for page in tiff.pages
            )
    if foreground_voxels == 0:
        raise ValueError("Mask contains no foreground voxels")
    if foreground_voxels == total_voxels:
        raise ValueError("Mask is entirely foreground and has no bounded surface")

    memory_mappable = True
    try:
        tifffile.memmap(path)
    except (ValueError, OSError):
        memory_mappable = False
    return {
        "shape_zyx": list(shape),
        "dtype": dtype.name,
        "page_count": int(shape[0]),
        "unique_values": sorted_unique if len(sorted_unique) <= 3 else sorted_unique[:3],
        "mask_threshold": float(threshold),
        "foreground_voxels": foreground_voxels,
        "background_voxels": total_voxels - foreground_voxels,
        "foreground_fraction": foreground_voxels / total_voxels,
        "memory_mappable": memory_mappable,
        "estimated_binary_bytes": total_voxels,
    }


def load_mask_volume(path: Path) -> np.ndarray:
    try:
        return tifffile.memmap(path)
    except (ValueError, OSError):
        return tifffile.imread(path)


def component_inventory(
    volume: np.ndarray,
    threshold: float,
) -> dict[str, Any]:
    from scipy import ndimage

    estimated_binary_bytes = int(np.prod(volume.shape, dtype=np.int64))
    if estimated_binary_bytes > MAX_COMPONENT_INVENTORY_BYTES:
        return {
            "source_component_count": None,
            "component_sizes_voxels": None,
            "inventory_skipped": True,
            "inventory_reason": (
                "Binary mask exceeds the configured eager component-inventory limit"
            ),
        }
    binary = np.asarray(volume > threshold, dtype=bool)
    labels, count = ndimage.label(binary, structure=ndimage.generate_binary_structure(3, 1))
    sizes = np.bincount(labels.reshape(-1))[1:]
    return {
        "source_component_count": int(count),
        "component_sizes_voxels": sorted(
            (int(value) for value in sizes),
            reverse=True,
        ),
        "inventory_skipped": False,
        "inventory_reason": None,
    }


def filter_components(
    binary: np.ndarray,
    minimum_component_voxels: int,
) -> tuple[np.ndarray, dict[str, Any]]:
    from scipy import ndimage

    if minimum_component_voxels < 0:
        raise ValueError("minimum_component_voxels cannot be negative")
    if minimum_component_voxels == 0:
        return binary, {
            "removed_component_count": 0,
            "removed_voxel_count": 0,
            "component_filter_applied": False,
        }
    if binary.nbytes > MAX_COMPONENT_INVENTORY_BYTES:
        raise ValueError(
            "Component filtering exceeds the safe eager-labeling limit; "
            "use zero filtering for this volume"
        )
    labels, count = ndimage.label(binary, structure=ndimage.generate_binary_structure(3, 1))
    sizes = np.bincount(labels.reshape(-1))
    remove = sizes < minimum_component_voxels
    remove[0] = False
    removed_ids = np.flatnonzero(remove)
    removed_voxels = int(sizes[removed_ids].sum())
    filtered = binary.copy()
    filtered[remove[labels]] = False
    return filtered, {
        "removed_component_count": int(len(removed_ids)),
        "removed_voxel_count": removed_voxels,
        "component_filter_applied": True,
        "component_count_before_filter": int(count),
    }


def _padded_slab(
    volume: np.ndarray,
    read_start: int,
    read_end: int,
    threshold: float,
) -> tuple[np.ndarray, np.ndarray]:
    slab = np.asarray(volume[read_start:read_end] > threshold, dtype=np.uint8)
    before = 1 if read_start == 0 else 0
    after = 1 if read_end == volume.shape[0] else 0
    padded = np.pad(
        slab,
        ((before, after), (1, 1), (1, 1)),
        mode="constant",
        constant_values=0,
    )
    offset_zyx = np.array([read_start - before, -1.0, -1.0], dtype=np.float64)
    return padded, offset_zyx


def extract_surface_chunked(
    volume: np.ndarray,
    threshold: float,
    slab_depth: int,
    slab_overlap: int,
    marching_cubes_step_size: int = 1,
) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    from skimage import measure

    if slab_depth < 2:
        raise ValueError("slab_depth must be at least 2")
    if slab_overlap < 1 or slab_overlap >= slab_depth:
        raise ValueError("slab_overlap must be at least 1 and less than slab_depth")
    if marching_cubes_step_size < 1:
        raise ValueError("marching_cubes_step_size must be at least 1")

    all_vertices: list[np.ndarray] = []
    all_faces: list[np.ndarray] = []
    vertex_offset = 0
    slab_count = 0
    z_size = volume.shape[0]

    for core_start in range(0, z_size, slab_depth):
        core_end = min(z_size, core_start + slab_depth)
        read_start = max(0, core_start - slab_overlap)
        read_end = min(z_size, core_end + slab_overlap)
        slab, coordinate_offset = _padded_slab(
            volume,
            read_start,
            read_end,
            threshold,
        )
        if not np.any(slab) or np.all(slab):
            continue
        vertices, faces, _, _ = measure.marching_cubes(
            slab,
            level=0.5,
            step_size=marching_cubes_step_size,
            allow_degenerate=False,
        )
        vertices = vertices.astype(np.float64, copy=False) + coordinate_offset
        centroids_z = vertices[faces, 0].mean(axis=1)
        if core_end == z_size:
            keep = (centroids_z >= core_start) & (centroids_z <= core_end)
        else:
            keep = (centroids_z >= core_start) & (centroids_z < core_end)
        faces = faces[keep]
        if not len(faces):
            continue
        used, inverse = np.unique(faces.reshape(-1), return_inverse=True)
        compact_vertices = vertices[used]
        compact_faces = inverse.reshape((-1, 3)).astype(np.int64)
        all_vertices.append(compact_vertices)
        all_faces.append(compact_faces + vertex_offset)
        vertex_offset += len(compact_vertices)
        slab_count += 1

    if not all_faces:
        raise ValueError("Marching cubes produced no surface faces")
    return (
        np.concatenate(all_vertices, axis=0),
        np.concatenate(all_faces, axis=0),
        {
            "slab_depth": int(slab_depth),
            "slab_overlap": int(slab_overlap),
            "processed_slab_count": int(slab_count),
            "marching_cubes_step_size": int(marching_cubes_step_size),
        },
    )


def reorder_and_scale_vertices(
    vertices_zyx: np.ndarray,
    voxel_size_xyz: tuple[float, float, float],
) -> np.ndarray:
    spacing = np.asarray(validate_voxel_size(voxel_size_xyz), dtype=np.float64)
    return vertices_zyx[:, [2, 1, 0]] * spacing


def clean_mesh(vertices_xyz: np.ndarray, faces: np.ndarray) -> tuple[Any, dict[str, Any]]:
    import trimesh

    mesh = trimesh.Trimesh(vertices=vertices_xyz, faces=faces, process=False)
    before = {"vertex_count": int(len(mesh.vertices)), "triangle_count": int(len(mesh.faces))}
    mesh.remove_infinite_values()
    mesh.update_faces(mesh.unique_faces())
    mesh.update_faces(mesh.nondegenerate_faces())
    mesh.remove_unreferenced_vertices()
    mesh.merge_vertices()
    mesh.remove_unreferenced_vertices()
    return mesh, {
        "before_cleanup": before,
        "after_cleanup": {
            "vertex_count": int(len(mesh.vertices)),
            "triangle_count": int(len(mesh.faces)),
        },
    }


def simplify_mesh(
    mesh: Any,
    target_face_count: int | None,
) -> tuple[Any, dict[str, Any]]:
    before = int(len(mesh.faces))
    if target_face_count is None:
        return mesh, {
            "mesh_decimated": False,
            "triangle_count_before_decimation": before,
            "triangle_count_after_decimation": before,
        }
    if target_face_count <= 0:
        raise ValueError("target_face_count must be positive")
    if target_face_count >= before:
        return mesh, {
            "mesh_decimated": False,
            "triangle_count_before_decimation": before,
            "triangle_count_after_decimation": before,
        }
    try:
        simplified = mesh.simplify_quadric_decimation(face_count=target_face_count)
    except Exception as error:
        raise RuntimeError(f"Mesh decimation failed: {error}") from error
    return simplified, {
        "mesh_decimated": True,
        "triangle_count_before_decimation": before,
        "triangle_count_after_decimation": int(len(simplified.faces)),
    }


def mesh_metrics(mesh: Any) -> dict[str, Any]:
    components = mesh.split(only_watertight=False)
    return {
        "vertex_count": int(len(mesh.vertices)),
        "triangle_count": int(len(mesh.faces)),
        "connected_component_count": int(len(components)),
        "watertight": bool(mesh.is_watertight),
        "euler_number": int(mesh.euler_number),
        "surface_area": float(mesh.area),
        "bounds_xyz": np.asarray(mesh.bounds, dtype=float).tolist(),
        "finite_vertices": bool(np.isfinite(mesh.vertices).all()),
        "valid_face_indices": bool(
            len(mesh.faces) > 0
            and np.min(mesh.faces) >= 0
            and np.max(mesh.faces) < len(mesh.vertices)
        ),
        "degenerate_face_count": int(
            len(mesh.faces) - int(np.count_nonzero(mesh.nondegenerate_faces()))
        ),
    }


def render_mesh_preview(mesh: Any, output: Path) -> dict[str, Any]:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection

    if not len(mesh.faces):
        raise ValueError("Cannot render a preview of an empty mesh")
    stride = max(1, int(math.ceil(len(mesh.faces) / MAX_PREVIEW_FACES)))
    faces = mesh.faces[::stride]
    triangles = np.asarray(mesh.vertices[faces], dtype=float)
    fig = plt.figure(figsize=(9, 8))
    axis = fig.add_subplot(111, projection="3d")
    collection = Poly3DCollection(
        triangles,
        facecolor=PREVIEW_COLOR,
        edgecolor="none",
        alpha=0.9,
    )
    axis.add_collection3d(collection)
    bounds = np.asarray(mesh.bounds, dtype=float)
    axis.set_xlim(bounds[:, 0])
    axis.set_ylim(bounds[:, 1])
    axis.set_zlim(bounds[:, 2])
    axis.set_box_aspect(np.maximum(bounds[1] - bounds[0], np.finfo(float).eps))
    axis.set_xlabel("x")
    axis.set_ylabel("y")
    axis.set_zlabel("z")
    axis.set_title("CT-segmentation-derived as-built surface")
    axis.view_init(elev=24, azim=-58)
    fig.tight_layout()
    fig.savefig(output, dpi=180, bbox_inches="tight")
    plt.close(fig)
    if not output.is_file() or output.stat().st_size == 0:
        raise RuntimeError(f"Preview was not written: {output}")
    return {
        "preview_face_stride": stride,
        "preview_faces_rendered": int(len(faces)),
        "preview_path": str(output),
    }


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    if path.stat().st_size == 0:
        raise RuntimeError(f"JSON output was not written: {path}")


def export_ct_surface(
    mask_filepath: str,
    output_filepath: str,
    voxel_size_xyz: tuple[float, float, float],
    preview_filepath: str,
    units: str = "mm",
    mask_threshold: float | None = None,
    slab_depth: int = 48,
    slab_overlap: int = 1,
    marching_cubes_step_size: int = 1,
    minimum_component_voxels: int = 0,
    target_face_count: int | None = None,
    metrics_filepath: str | None = None,
    overwrite: bool = False,
) -> dict[str, Any]:
    import trimesh

    source = source_path(mask_filepath)
    output = writable_output(output_filepath, {".stl"}, overwrite, "STL output")
    preview = writable_output(preview_filepath, {".png"}, overwrite, "Preview output")
    metrics_path = (
        writable_output(metrics_filepath, {".json"}, overwrite, "Metrics output")
        if metrics_filepath
        else None
    )
    spacing = validate_voxel_size(voxel_size_xyz)
    if not units or not units.strip():
        raise ValueError("units must be a nonempty label")

    inspection = inspect_mask(source, mask_threshold)
    volume = load_mask_volume(source)
    inventory = component_inventory(volume, inspection["mask_threshold"])
    if minimum_component_voxels:
        estimated_binary_bytes = int(np.prod(volume.shape, dtype=np.int64))
        if estimated_binary_bytes > MAX_COMPONENT_INVENTORY_BYTES:
            raise ValueError(
                "Component filtering exceeds the safe eager-labeling limit; "
                "use zero filtering for this volume"
            )
        binary = np.asarray(volume > inspection["mask_threshold"], dtype=bool)
        extraction_volume, filtering = filter_components(
            binary,
            minimum_component_voxels,
        )
        extraction_threshold = 0.5
    else:
        extraction_volume = volume
        extraction_threshold = inspection["mask_threshold"]
        filtering = {
            "removed_component_count": 0,
            "removed_voxel_count": 0,
            "component_filter_applied": False,
        }
    vertices_zyx, faces, extraction = extract_surface_chunked(
        extraction_volume,
        extraction_threshold,
        slab_depth,
        slab_overlap,
        marching_cubes_step_size,
    )
    vertices_xyz = reorder_and_scale_vertices(vertices_zyx, spacing)
    mesh, cleanup = clean_mesh(vertices_xyz, faces)
    mesh, decimation = simplify_mesh(mesh, target_face_count)
    expected_bounds = np.asarray(mesh.bounds, dtype=float)
    mesh.export(output, file_type="stl")
    if not output.is_file() or output.stat().st_size == 0:
        raise RuntimeError(f"STL output was not written: {output}")

    # STL stores triangle vertices independently. Processing on reload merges
    # coincident vertices so connectivity, Euler number, and component metrics
    # describe the mesh rather than the STL serialization.
    reloaded = trimesh.load(output, force="mesh", process=True)
    if not isinstance(reloaded, trimesh.Trimesh):
        raise RuntimeError("Reloaded STL is not a triangle mesh")
    statistics = {
        "source_shape_zyx": inspection["shape_zyx"],
        "source_dtype": inspection["dtype"],
        "foreground_voxels": inspection["foreground_voxels"],
        "background_voxels": inspection["background_voxels"],
        "foreground_fraction": inspection["foreground_fraction"],
        **inventory,
        **filtering,
        **extraction,
        **cleanup,
        **decimation,
        **mesh_metrics(reloaded),
    }
    reloaded_bounds = np.asarray(statistics["bounds_xyz"], dtype=float)
    tolerance = max(spacing) * 1e-4
    if not np.allclose(reloaded_bounds, expected_bounds, atol=tolerance, rtol=0):
        raise RuntimeError("Reloaded STL bounds do not match exported mesh bounds")
    statistics["bounds_validation_tolerance"] = tolerance

    preview_info = render_mesh_preview(reloaded, preview)
    warnings = [
        "STL does not encode coordinate units.",
        "Voxel calibration status must be interpreted from supplied metadata.",
    ]
    if inventory["inventory_skipped"]:
        warnings.append(str(inventory["inventory_reason"]))
    if not statistics["watertight"]:
        warnings.append("Exported as-built surface is not watertight.")
    parameters = {
        "source_axis_order": "ZYX",
        "output_axis_order": "XYZ",
        "voxel_size_xyz": list(spacing),
        "units": units.strip(),
        "mask_threshold": inspection["mask_threshold"],
        "slab_depth": slab_depth,
        "slab_overlap": slab_overlap,
        "marching_cubes_step_size": marching_cubes_step_size,
        "minimum_component_voxels": minimum_component_voxels,
        "target_face_count": target_face_count,
    }
    item = {
        "status": "success",
        "visualization_type": "ct_as_built_surface",
        "input_paths": [str(source)],
        "output_path": str(output),
        "preview_path": str(preview),
        "metrics_path": str(metrics_path) if metrics_path else None,
        "parameters": parameters,
        "statistics": statistics,
        "warnings": warnings,
        "provenance": {
            "script": "export_ct_surface.py",
            "surface_method": "chunked_marching_cubes",
            "scientific_sampling": marching_cubes_step_size > 1,
            "scientific_sampling_method": (
                "marching_cubes_step_size"
                if marching_cubes_step_size > 1
                else None
            ),
            "mesh_decimated": decimation["mesh_decimated"],
            "preview": preview_info,
            "created_utc": datetime.now(timezone.utc).isoformat(),
        },
    }
    if metrics_path:
        write_json(
            metrics_path,
            {
                "schema_version": "1.0",
                "artifact_type": "ct_as_built_surface_mesh_metrics",
                **item,
            },
        )
    return item


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mask", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--preview", required=True)
    parser.add_argument("--voxel-size-x", type=float, required=True)
    parser.add_argument("--voxel-size-y", type=float, required=True)
    parser.add_argument("--voxel-size-z", type=float, required=True)
    parser.add_argument("--units", default="mm")
    parser.add_argument("--mask-threshold", type=float)
    parser.add_argument("--slab-depth", type=int, default=48)
    parser.add_argument("--slab-overlap", type=int, default=1)
    parser.add_argument("--marching-cubes-step-size", type=int, default=1)
    parser.add_argument("--minimum-component-voxels", type=int, default=0)
    parser.add_argument("--target-face-count", type=int)
    parser.add_argument("--metrics")
    parser.add_argument("--overwrite", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        item = export_ct_surface(
            mask_filepath=args.mask,
            output_filepath=args.output,
            voxel_size_xyz=(
                args.voxel_size_x,
                args.voxel_size_y,
                args.voxel_size_z,
            ),
            preview_filepath=args.preview,
            units=args.units,
            mask_threshold=args.mask_threshold,
            slab_depth=args.slab_depth,
            slab_overlap=args.slab_overlap,
            marching_cubes_step_size=args.marching_cubes_step_size,
            minimum_component_voxels=args.minimum_component_voxels,
            target_face_count=args.target_face_count,
            metrics_filepath=args.metrics,
            overwrite=args.overwrite,
        )
    except ImportError as error:
        item = {
            "status": "blocked_environment",
            "visualization_type": "ct_as_built_surface",
            "input_paths": [],
            "output_path": None,
            "interpreter": sys.executable,
            "dependency": getattr(error, "name", None),
            "error": str(error),
            "warnings": [],
        }
    except Exception as error:
        item = {
            "status": "error",
            "visualization_type": "ct_as_built_surface",
            "input_paths": [],
            "output_path": None,
            "error_type": type(error).__name__,
            "error": str(error),
            "warnings": [],
        }
    print(json.dumps(item, indent=2))
    return 0 if item["status"] == "success" else 1


if __name__ == "__main__":
    sys.exit(main())
