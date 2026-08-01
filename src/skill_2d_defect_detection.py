"""Standalone single-slice raw-CT lattice-strut review-candidate detector.

It deliberately uses only a raw CT TIFF plane: no registered JSON,
segmentation, skeleton, or existing defect-workflow output is read.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import tifffile
from skimage import exposure, filters, morphology
from skimage.feature import peak_local_max

ROOT = Path(__file__).resolve().parents[1]
TIFF = ROOT / "data/missing_struts/tif_stacks/210127_Brian_Tran_strut_lattices_0point5dash1 1 Slices.tif"
OUT = ROOT / "data/missing_struts/analysis/skill_2d_defect_detection/slice_0385"


def adaptive_binarize(raw: np.ndarray) -> tuple[np.ndarray, float]:
    """Adaptive bright-material binarization, with only small-noise cleanup."""
    # Keep native uint16 scale: skimage assumes a [0, 1] range for float input.
    # A negative Sauvola offset selects the sparse bright lattice, rather than
    # the locally uniform dark CT background.
    threshold = filters.threshold_sauvola(raw, window_size=71, k=-0.10)
    mask = morphology.remove_small_objects(morphology.binary_opening(raw > threshold, morphology.disk(1)), min_size=12)
    return mask, float(np.median(threshold))


def nodes_from_raw(raw: np.ndarray) -> np.ndarray:
    response = filters.gaussian(exposure.rescale_intensity(raw.astype(np.float32), out_range=(0, 1)), sigma=3)
    return peak_local_max(response, min_distance=24, threshold_abs=float(np.percentile(response, 99)), exclude_border=28).astype(int)


def expected_paths(nodes: np.ndarray) -> tuple[list[tuple[np.ndarray, np.ndarray]], float]:
    """Build diagonal grid expectations from local node-to-node periodicity."""
    if len(nodes) < 4:
        return [], 0.0
    delta = nodes[:, None] - nodes[None, :]
    distance = np.hypot(delta[..., 0], delta[..., 1]); np.fill_diagonal(distance, np.inf)
    spacing = float(np.median(np.min(distance, axis=1)))
    result, seen = [], set()
    for i, node in enumerate(nodes):
        for j in np.where((distance[i] >= .62 * spacing) & (distance[i] <= 1.42 * spacing))[0]:
            angle = abs(float(np.degrees(np.arctan2(*(nodes[j] - node))))) % 180
            if not (22 <= angle <= 68 or 112 <= angle <= 158) or (min(i, int(j)), max(i, int(j))) in seen:
                continue
            seen.add((min(i, int(j)), max(i, int(j))))
            result.append((node, nodes[j]))
    return result, spacing


def _false_run(values: np.ndarray) -> int:
    best = run = 0
    for value in values:
        run = 0 if value else run + 1; best = max(best, run)
    return best


def measure(mask: np.ndarray, path: tuple[np.ndarray, np.ndarray]) -> dict:
    start, end = (np.asarray(v, float) for v in path)
    n = max(2, int(round(np.hypot(*(end - start)))) + 1)
    points = np.rint(np.linspace(start, end, n)).astype(int)[8:-8]
    samples = []
    for y, x in points:
        samples.append(bool(mask[max(0, y - 2):min(mask.shape[0], y + 3), max(0, x - 2):min(mask.shape[1], x + 3)].any()))
    values = np.asarray(samples, dtype=bool); end_count = min(6, max(1, len(values) // 3))
    return {"fill_ratio": float(values.mean()) if len(values) else 0., "max_gap_length": _false_run(values),
            "connectivity": bool(values[:end_count].any() and values[-end_count:].any())}


def classify(metrics: dict, intact_fill: float, gap_threshold: int) -> tuple[str | None, float]:
    fill, gap, connected = metrics["fill_ratio"], metrics["max_gap_length"], metrics["connectivity"]
    missing, uncertain = .10 * intact_fill, .26 * intact_fill
    if fill <= missing: return "possible_missing", float(np.clip(1 - fill / max(missing, 1e-6), 0, 1))
    if fill <= uncertain: return "uncertain", float(np.clip((uncertain - fill) / max(uncertain - missing, 1e-6), 0, 1))
    if fill < .82 * intact_fill and gap >= gap_threshold and not connected:
        return "possible_broken", float(np.clip(.45 + .55 * (1 - fill / max(intact_fill, 1e-6)), 0, 1))
    return None, 0.


def _save(raw: np.ndarray, mask: np.ndarray, paths: list, candidates: list, output: Path) -> None:
    display = exposure.rescale_intensity(raw, in_range=tuple(np.percentile(raw, [1, 99.5])), out_range=(0, 1))
    plt.imsave(output / "binarized_mask.png", mask, cmap="gray", vmin=0, vmax=1)
    fig, ax = plt.subplots(figsize=(10, 10), dpi=150); ax.imshow(display, cmap="gray")
    for a, b in paths: ax.plot([a[1], b[1]], [a[0], b[0]], color="#28b7ff", lw=.65, alpha=.55)
    ax.set_axis_off(); fig.tight_layout(pad=0); fig.savefig(output / "expectation_overlay.png", bbox_inches="tight", pad_inches=0); plt.close(fig)
    colors = {"possible_missing":"#ff3b30", "possible_broken":"#ffb000", "uncertain":"#b565ff"}
    fig, ax = plt.subplots(figsize=(10, 10), dpi=150); ax.imshow(display, cmap="gray")
    for item in candidates: ax.scatter(item["location"]["x"], item["location"]["y"], s=38, color=colors[item["label"]], edgecolors="white", lw=.5)
    ax.set_title("2-D raw-CT review candidates only", fontsize=9); ax.set_axis_off(); fig.tight_layout(pad=0)
    fig.savefig(output / "candidate_map.png", bbox_inches="tight", pad_inches=0); plt.close(fig)


def run(tiff: Path = TIFF, slice_index: int = 385, output: Path = OUT) -> dict:
    volume = tifffile.memmap(tiff)
    if volume.ndim != 3 or not 0 <= slice_index < volume.shape[0]: raise ValueError(f"Invalid slice {slice_index} for {volume.shape}")
    output.mkdir(parents=True, exist_ok=True); raw = np.asarray(volume[slice_index]); mask, threshold = adaptive_binarize(raw)
    nodes = nodes_from_raw(raw); paths, spacing = expected_paths(nodes); measurements = [measure(mask, path) for path in paths]
    fills = np.asarray([m["fill_ratio"] for m in measurements]); top = max(1, int(np.ceil(.1 * len(fills))))
    intact = float(np.mean(np.sort(fills)[-top:])) if len(fills) else 1.; gap = 7
    candidates = []
    for number, (path, metrics) in enumerate(zip(paths, measurements), 1):
        label, confidence = classify(metrics, intact, gap)
        if label:
            mid = (np.asarray(path[0]) + np.asarray(path[1])) / 2
            candidates.append({"candidate_id":f"slice_{slice_index:04d}_candidate_{number:04d}", "location":{"y":round(float(mid[0]),2),"x":round(float(mid[1]),2)}, "label":label, "confidence":round(confidence,4), "metrics":metrics})
    summary = {"slice_index":slice_index, "input_type":"single_raw_ct_slice", "input_path":str(tiff.relative_to(ROOT)), "total_expected_struts":len(paths), "candidate_count":len(candidates), "node_count":len(nodes), "adaptive_threshold_median":round(threshold,4), "estimated_node_spacing_px":round(spacing,3), "intact_fill_ratio_reference":round(intact,4), "gap_length_threshold_px":gap, "candidate_labels":["possible_missing","possible_broken","uncertain"], "limitation":"2-D raw-CT candidates only; no candidate is a confirmed defect."}
    (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n"); (output / "candidates.json").write_text(json.dumps(candidates, indent=2) + "\n")
    _save(raw, mask, paths, candidates, output); return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--tiff", type=Path, default=TIFF); parser.add_argument("--slice-index", type=int, default=385); parser.add_argument("--output-dir", type=Path, default=OUT)
    args = parser.parse_args(); print(json.dumps(run(args.tiff, args.slice_index, args.output_dir), indent=2))
