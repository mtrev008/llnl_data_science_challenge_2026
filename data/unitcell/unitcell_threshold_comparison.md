# Threshold Comparison: `unitcell.npy`

Input: `data/unitcell/unitcell.npy`

Method: local NumPy fallback, because no `segment_ct_dataset()` MCP tool is available in this session.

The raw volume has intensity range `-0.003129` to `0.015258`. This comparison uses the updated threshold-optimizer defaults: `0.003`, `0.007`, and `0.01`.

| Threshold | Output mask | Foreground voxels | Foreground fraction |
| ---: | --- | ---: | ---: |
| 0.003 | `unitcell_mask_threshold_0.003.npy` | 780,596 | 0.046527 |
| 0.007 | `unitcell_mask_threshold_0.007.npy` | 712,688 | 0.042480 |
| 0.01 | `unitcell_mask_threshold_0.01.npy` | 622,182 | 0.037085 |

The generated masks are all shape `256 x 256 x 256` with dtype `uint8`.

The previously computed Otsu value was `0.005865`, so the `0.007` result is the closest of this sweep while still being slightly stricter.
