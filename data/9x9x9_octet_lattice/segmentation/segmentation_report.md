# Lattice segmentation report

## Run summary

- Source: `/Users/nimanwander/Desktop/LLNL DSSI/llnl_data_science_challenge_2026/data/9x9x9_octet_lattice/9x9x9_octet_lattice.tif`
- Output: `/Users/nimanwander/Desktop/LLNL DSSI/llnl_data_science_challenge_2026/data/9x9x9_octet_lattice/segmentation`
- Shape / dtype: `(761, 815, 837)` / `>u2`; voxel count: `519119955`
- Finite sampled percentiles (0,.1,1,5,25,50,75,90,95,99,99.9,100): `[7138.0, 24901.795000000002, 29770.59, 30945.0, 31767.0, 32419.0, 33770.0, 42402.0, 48603.0, 54881.0, 58086.84100000013, 63089.0]`
- Selected method: bright-material global threshold, `intensity > 42608.1`; no morphology
- Iterations: 8; stopping reason: stable result with two sub-0.005 improvements
- Best heuristic score: 0.851595
- Full-resolution foreground: 48536551 (9.3498%); background: 470583404 (90.6502%)
- Runtime: 14.46 seconds; random seed: 20260721
- Versions: `{"python": "3.11.15", "numpy": "2.4.6", "scipy": "1.17.1", "scikit-image": "0.26.0", "tifffile": "2026.3.3", "matplotlib": "3.11.1"}`

## Optimization and score

Otsu on a deterministic 8× sampled volume initialized the search. Each next threshold was chosen from the observed occupancy and best score, with a halved step during refinement. Candidate metrics used a deterministic 4× 3-D downsample. The score is a heuristic, not accuracy: `0.27 contrast + 0.23 dominant-component fraction + 0.18 (1-small-component fraction) + 0.14 slice stability + 0.12 occupancy plausibility + 0.06 border term`, with penalties for degenerate occupancy and empty/full slices.

| Iteration | Threshold | Score | Foreground | Components | Largest component | Next change |
|---:|---:|---:|---:|---:|---:|---|
| 1 | 40249.62 | 0.8467 | 11.336% | 21298 | 95.231% | initial Otsu; adjust occupancy |
| 2 | 37554.18 | 0.8130 | 14.220% | 2731 | 99.348% | refine around best threshold based on score and occupancy |
| 3 | 42945.07 | 0.8510 | 9.328% | 48475 | 85.681% | refine around best threshold based on score and occupancy |
| 4 | 44292.79 | 0.8463 | 8.327% | 56699 | 77.593% | refine around best threshold based on score and occupancy |
| 5 | 42271.21 | 0.8514 | 9.803% | 42763 | 88.659% | refine around best threshold based on score and occupancy |
| 6 | 42608.14 | 0.8516 | 9.566% | 45782 | 87.365% | refine around best threshold based on score and occupancy |
| 7 | 42439.67 | 0.8515 | 9.686% | 44275 | 88.014% | refine around best threshold based on score and occupancy |
| 8 | 42692.37 | 0.8513 | 9.506% | 46478 | 86.897% | refine around best threshold based on score and occupancy |

## Visual assessment and limitations

All eight iteration panels were visually reviewed for polarity, leakage, speckle, holes, broken junctions, and thin-strut preservation. Bright polarity is correct. On slice 380, threshold 42608.135 preserves the prominent left-side diagonal struts and junctions and the expected point-like intersections toward the right while avoiding the visible background leakage of the low-threshold candidate. Center YZ/XZ views retain continuous lattice members without an apparent polarity error; the bright top/bottom boundary material remains because no unsupported crop or keep-largest-component operation was applied. The supplied `ground_truth_segmentation_slice_380.png` is a rendered figure rather than an axis-aligned mask array, so it served only as visual reference and no ground-truth accuracy metric is claimed. Global thresholding can miss very weak struts or retain bright artifacts; voxel spacing was unavailable, and the score is structural rather than task accuracy.

## Validation and reproduction

The final TIFF was reloaded after CLI generation and checked for matching shape, binary values 0/255, nonzero foreground/background, and readable required artifacts. Reproduce with:

```bash
MPLCONFIGDIR=/private/tmp/mplconfig python "/Users/nimanwander/Desktop/LLNL DSSI/llnl_data_science_challenge_2026/data/9x9x9_octet_lattice/segmentation/segment_lattice.py" "/Users/nimanwander/Desktop/LLNL DSSI/llnl_data_science_challenge_2026/data/9x9x9_octet_lattice/9x9x9_octet_lattice.tif" "/Users/nimanwander/Desktop/LLNL DSSI/llnl_data_science_challenge_2026/data/9x9x9_octet_lattice/segmentation"
```

Artifacts: [mask](segmented_mask.tif), [slice 380](slice_380.png), [history CSV](optimization_history.csv), [history plot](optimization_history.png), [histogram](intensity_histogram.png), [best diagnostics](best_diagnostics.png), and [iteration diagnostics](iterations/).
