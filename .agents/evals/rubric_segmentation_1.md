# Lattice Segmentation Evaluator

This code compares a result segmentation with a clean ground-truth image. It
measures foreground overlap, connectivity, junction topology, and small artifacts,
then returns a score from 0 to 5.

## Scoring

- **5:** Effectively identical structure, connectivity, and junctions.
- **4:** Correct topology with only minor local differences.
- **3:** Mostly correct lattice with noticeable gaps, noise, or thickness errors.
- **2:** Significant missing or extra regions and degraded connectivity.
- **1:** Severe structural failure with limited correspondence.
- **0:** Blank, unusable, or unrelated result.

## Code

The loading functions convert both images to binary masks and remove surrounding
plot borders. The metric functions measure components, endpoints, junctions, false
positives, false negatives, and isolated noise. `evaluate` combines those values
into the rubric score and required JSON response.

```python
#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from skimage.morphology import skeletonize


def load_mask(path):
    pixels = np.asarray(Image.open(path).convert("L"))
    dark = pixels < 128
    return dark if dark.mean() < 0.5 else ~dark


def crop_mask(mask):
    rows, columns = np.where(mask)
    if len(rows) == 0:
        return mask
    return mask[rows.min() : rows.max() + 1, columns.min() : columns.max() + 1]


def normalize_masks(truth, result):
    truth = crop_mask(truth)
    result = crop_mask(result)
    resized = Image.fromarray(result.astype(np.uint8) * 255).resize(
        (truth.shape[1], truth.shape[0]), Image.Resampling.NEAREST
    )
    return truth, np.asarray(resized) > 0


def component_count(mask):
    return ndi.label(mask, np.ones((3, 3)))[1]


def topology(mask):
    skeleton = skeletonize(mask)
    neighbors = ndi.convolve(skeleton.astype(np.uint8), np.ones((3, 3))) - skeleton
    endpoints = np.count_nonzero(skeleton & (neighbors == 1))
    junctions = ndi.label(skeleton & (neighbors >= 3))[1]
    return int(endpoints), int(junctions)


def small_artifacts(mask):
    labels, count = ndi.label(mask)
    sizes = np.bincount(labels.ravel())[1:]
    limit = max(3, round(mask.size * 0.00005))
    return int(np.count_nonzero(sizes <= limit)), count


def difference(reference, observed):
    return abs(observed - reference) / max(reference, 1)


def evaluate(ground_truth_path, result_path):
    truth = load_mask(ground_truth_path)
    result = load_mask(result_path)

    if result.mean() < 0.0001 or result.mean() > 0.9999:
        return {
            "reasoning": (
                "The result is blank or unusable, so connectivity and junctions "
                "are not preserved and the segmentation has no meaningful match."
            ),
            "score": 0,
        }

    truth, result = normalize_masks(truth, result)
    truth_pixels = np.count_nonzero(truth)
    true_positive = np.count_nonzero(truth & result)
    false_positive = np.count_nonzero(~truth & result)
    false_negative = np.count_nonzero(truth & ~result)

    iou = true_positive / max(
        true_positive + false_positive + false_negative, 1
    )
    over = false_positive / max(truth_pixels, 1)
    under = false_negative / max(truth_pixels, 1)

    truth_components = component_count(truth)
    result_components = component_count(result)
    truth_endpoints, truth_junctions = topology(truth)
    result_endpoints, result_junctions = topology(result)
    truth_artifacts, _ = small_artifacts(truth)
    result_artifacts, result_component_total = small_artifacts(result)
    extra_artifacts = max(0, result_artifacts - truth_artifacts)

    connectivity_error = difference(truth_components, result_components)
    endpoint_error = difference(truth_endpoints, result_endpoints)
    junction_error = difference(truth_junctions, result_junctions)
    artifact_error = extra_artifacts / max(result_component_total, 1)

    quality = (
        0.35 * iou
        + 0.20 * max(0, 1 - connectivity_error)
        + 0.20 * max(0, 1 - junction_error)
        + 0.10 * max(0, 1 - endpoint_error)
        + 0.075 * max(0, 1 - over)
        + 0.075 * max(0, 1 - under)
        - 0.15 * artifact_error
    )

    if iou >= 0.995 and max(connectivity_error, junction_error, endpoint_error) <= 0.02:
        score = 5
    elif quality >= 0.88 and max(connectivity_error, junction_error) <= 0.15:
        score = 4
    elif quality >= 0.68 and max(connectivity_error, junction_error) <= 0.45:
        score = 3
    elif quality >= 0.42:
        score = 2
    elif iou >= 0.05:
        score = 1
    else:
        score = 0

    reasoning = (
        f"Foreground overlap is {iou:.1%}, with {over:.1%} over-segmentation and "
        f"{under:.1%} under-segmentation. The result has {result_components} "
        f"connected components versus {truth_components} in the ground truth, "
        f"{result_junctions} junctions versus {truth_junctions}, and "
        f"{extra_artifacts} extra small artifacts. These connectivity, topology, and noise differences "
        f"justify a score of {score}."
    )
    return {"reasoning": reasoning, "score": score}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("ground_truth", type=Path)
    parser.add_argument("result", type=Path)
    args = parser.parse_args()
    print(json.dumps(evaluate(args.ground_truth, args.result)))


if __name__ == "__main__":
    main()
```
