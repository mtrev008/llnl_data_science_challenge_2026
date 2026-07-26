#!/usr/bin/env python3
"""Count struts absent near both ends of a registered lattice model."""

import argparse
import json
from pathlib import Path

import numpy as np
from skimage.morphology import skeletonize
import tifffile


def segment_scan(image, threshold):
    low = np.median(image)
    scale = max(np.percentile(image, 99.5) - low, 1)
    return (np.clip((image - low) / scale, 0, 1) >= threshold)


def endpoint_present(mask, skeleton, position, radius, minimum_coverage):
    x, y = np.rint(position[:2]).astype(int)
    mask_patch = mask[y - radius : y + radius + 1, x - radius : x + radius + 1]
    skeleton_patch = skeleton[
        y - radius : y + radius + 1, x - radius : x + radius + 1
    ]
    return mask_patch.mean() >= minimum_coverage or skeleton_patch.any()


def identify_missing_struts(
    tiff_path,
    reference_path,
    segmentation_path,
    normalized_threshold=0.25,
    endpoint_radius=10,
    minimum_coverage=0.01,
    inward_fraction=0.2,
):
    volume = tifffile.memmap(tiff_path)
    reference = json.loads(Path(reference_path).read_text())
    junctions = {
        int(junction["id"]): np.asarray(junction["position"])
        for junction in reference["junctions"]
    }
    processed_scans = {}
    missing = 0
    broken = 0

    def scan_data(scan):
        if scan not in processed_scans:
            mask = segment_scan(np.asarray(volume[scan]), normalized_threshold)
            processed_scans[scan] = (mask, skeletonize(mask))
        return processed_scans[scan]

    for strut in reference["struts"]:
        first = junctions[int(strut["junction0"])]
        second = junctions[int(strut["junction1"])]
        start, end = (first, second) if first[2] <= second[2] else (second, first)
        start_probe = start + inward_fraction * (end - start)
        end_probe = end + inward_fraction * (start - end)

        start_scan = int(round(start_probe[2]))
        end_scan = int(round(end_probe[2]))
        start_mask, start_skeleton = scan_data(start_scan)
        end_mask, end_skeleton = scan_data(end_scan)

        start_present = endpoint_present(
            start_mask,
            start_skeleton,
            start_probe,
            endpoint_radius,
            minimum_coverage,
        )
        end_present = endpoint_present(
            end_mask,
            end_skeleton,
            end_probe,
            endpoint_radius,
            minimum_coverage,
        )
        missing += not start_present and not end_present
        broken += start_present != end_present

    scan_indices = sorted(processed_scans)
    segmentation_stack = np.stack(
        [processed_scans[scan][0] for scan in scan_indices]
    ).astype(np.uint8) * 255
    tifffile.imwrite(
        segmentation_path,
        segmentation_stack,
        photometric="minisblack",
        metadata={"axes": "ZYX", "source_scan_indices": scan_indices},
    )

    return {
        "tiff": str(Path(tiff_path).resolve()),
        "reference_json": str(Path(reference_path).resolve()),
        "segmentation_tiff": str(Path(segmentation_path).resolve()),
        "expected_struts": len(reference["struts"]),
        "endpoint_scans_processed": len(processed_scans),
        "missing_struts": int(missing),
        "broken_struts": int(broken),
        "missing_percentage": 100 * missing / len(reference["struts"]),
        "broken_percentage": 100 * broken / len(reference["struts"]),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("tiff", type=Path)
    parser.add_argument("reference_json", type=Path)
    parser.add_argument("segmentation_tiff", type=Path)
    parser.add_argument("summary", type=Path)
    parser.add_argument("--normalized-threshold", type=float, default=0.25)
    parser.add_argument("--endpoint-radius", type=int, default=10)
    parser.add_argument("--minimum-coverage", type=float, default=0.01)
    parser.add_argument("--inward-fraction", type=float, default=0.2)
    args = parser.parse_args()

    result = identify_missing_struts(
        args.tiff,
        args.reference_json,
        args.segmentation_tiff,
        args.normalized_threshold,
        args.endpoint_radius,
        args.minimum_coverage,
        args.inward_fraction,
    )
    args.summary.write_text(
        "# Missing Strut Summary\n\n"
        f"- TIFF: `{result['tiff']}`\n"
        f"- Registered JSON: `{result['reference_json']}`\n"
        f"- Endpoint segmentation TIFF: `{result['segmentation_tiff']}`\n"
        f"- Expected struts: **{result['expected_struts']}**\n"
        f"- Endpoint scans segmented and skeletonized: "
        f"**{result['endpoint_scans_processed']}**\n"
        f"- Missing struts: **{result['missing_struts']}**\n"
        f"- Missing percentage: **{result['missing_percentage']:.2f}%**\n"
        f"- Broken struts: **{result['broken_struts']}**\n"
        f"- Broken percentage: **{result['broken_percentage']:.2f}%**\n"
    )
    print(f"Missing struts: {result['missing_struts']}")
    print(f"Broken struts: {result['broken_struts']}")
    print(f"Segmentation: {args.segmentation_tiff}")
    print(f"Summary: {args.summary}")


if __name__ == "__main__":
    main()
