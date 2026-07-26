# LLNL CT Pipeline Manager Report

Passed steps: 5/5

## Step 1: Data Analyzer

- Subagent: `.codex/agents/data_analyzer`
- Status: `passed`
- Command: `/home/mtrev008/miniconda3/bin/python -B .codex/agents/data_analyzer/run.py`
- Return code: `0`

### Result Artifacts

- `data/missing_struts/analysis/ct_volume_stats.json` - present, 512 bytes
- `data/missing_struts/analysis/ct_volume_stats.md` - present, 376 bytes

### Result Content

#### CT volume statistics

Source: `data/missing_struts/analysis/ct_volume_stats.json`

```json
{
  "input": "/home/mtrev008/Desktop/LLNL_DSC/llnl_data_science_challenge_2026/data/missing_struts/tif_stacks/210127_Brian_Tran_strut_lattices_0point5dash1 1 Slices.tif",
  "shape_zyx": [
    761,
    815,
    837
  ],
  "dtype": ">u2",
  "voxel_count": 519119955,
  "finite_voxels": 43657920,
  "min": 0.0,
  "p01": 29728.0,
  "p05": 30945.0,
  "p25": 31777.0,
  "median": 32421.0,
  "p75": 33827.0,
  "p95": 48959.0,
  "p99": 55161.0,
  "max": 63256.0,
  "mean": 34470.13229977516,
  "std": 5497.42748430147
}
```

#### CT volume statistics report

Source: `data/missing_struts/analysis/ct_volume_stats.md`

# CT Volume Statistics

- Input: `/home/mtrev008/Desktop/LLNL_DSC/llnl_data_science_challenge_2026/data/missing_struts/tif_stacks/210127_Brian_Tran_strut_lattices_0point5dash1 1 Slices.tif`
- Shape (z, y, x): `(761, 815, 837)`
- Dtype: `>u2`
- Voxels: **519,119,955**
- Intensity range: **0** to **63256**
- Median intensity: **32421**
- Mean +/- std: **34470.1 +/- 5497.43**


### Summary Card

```json
{
  "step": "Data Analyzer",
  "subagent": ".codex/agents/data_analyzer",
  "status": "passed",
  "command": "/home/mtrev008/miniconda3/bin/python -B .codex/agents/data_analyzer/run.py",
  "stdout": "Data Analyzer pipeline step",
  "stderr": "",
  "outputs": [
    {
      "path": "data/missing_struts/analysis/ct_volume_stats.json",
      "exists": true,
      "size_bytes": 512
    },
    {
      "path": "data/missing_struts/analysis/ct_volume_stats.md",
      "exists": true,
      "size_bytes": 376
    }
  ],
  "results": [
    {
      "title": "CT volume statistics",
      "source": "data/missing_struts/analysis/ct_volume_stats.json",
      "content": {
        "input": "/home/mtrev008/Desktop/LLNL_DSC/llnl_data_science_challenge_2026/data/missing_struts/tif_stacks/210127_Brian_Tran_strut_lattices_0point5dash1 1 Slices.tif",
        "shape_zyx": [
          761,
          815,
          837
        ],
        "dtype": ">u2",
        "voxel_count": 519119955,
        "finite_voxels": 43657920,
        "min": 0.0,
        "p01": 29728.0,
        "p05": 30945.0,
        "p25": 31777.0,
        "median": 32421.0,
        "p75": 33827.0,
        "p95": 48959.0,
        "p99": 55161.0,
        "max": 63256.0,
        "mean": 34470.13229977516,
        "std": 5497.42748430147
      }
    },
    {
      "title": "CT volume statistics report",
      "source": "data/missing_struts/analysis/ct_volume_stats.md",
      "content": "# CT Volume Statistics\n\n- Input: `/home/mtrev008/Desktop/LLNL_DSC/llnl_data_science_challenge_2026/data/missing_struts/tif_stacks/210127_Brian_Tran_strut_lattices_0point5dash1 1 Slices.tif`\n- Shape (z, y, x): `(761, 815, 837)`\n- Dtype: `>u2`\n- Voxels: **519,119,955**\n- Intensity range: **0** to **63256**\n- Median intensity: **32421**\n- Mean +/- std: **34470.1 +/- 5497.43**"
    }
  ],
  "metrics": {
    "return_code": 0
  },
  "issues": []
}
```

## Step 2: Segmentation

- Subagent: `.codex/agents/segmentation`
- Status: `passed`
- Command: `/home/mtrev008/miniconda3/bin/python -B .codex/agents/segmentation/run.py`
- Return code: `0`

### Result Artifacts

- `data/missing_struts/analysis/segmentation_workflow.py` - present, 6261 bytes
- `data/missing_struts/analysis/segmented_mask.tif` - present, 519330900 bytes
- `data/missing_struts/analysis/segmentation_slice_380.png` - present, 14740 bytes
- `data/missing_struts/analysis/segmentation_report.md` - present, 999 bytes
- `data/missing_struts/analysis/evaluation_summary.md` - present, 332 bytes

### Result Content

#### Segmentation report

Source: `data/missing_struts/analysis/segmentation_report.md`

# Segmentation Report

- Method: smoothed slice-median brightness correction
- Iterations run: **1**
- Failed attempts: **0**
- Segmented mask: `/home/mtrev008/Desktop/LLNL_DSC/llnl_data_science_challenge_2026/data/missing_struts/analysis/segmented_mask.tif`
- Executable script copy: `/home/mtrev008/Desktop/LLNL_DSC/llnl_data_science_challenge_2026/data/missing_struts/analysis/segmentation_workflow.py`
- Slice 380 visualization: `/home/mtrev008/Desktop/LLNL_DSC/llnl_data_science_challenge_2026/data/missing_struts/analysis/segmentation_slice_380.png`
- Foreground voxels: **23,410,270**
- Background voxels: **495,709,685**
- Median foreground fraction: **3.97%**

## README Validation Criteria

- Structural integrity: inspect slice 380 and downstream skeleton connectivity.
- False positives/negatives: compare over-segmentation noise and missing struts.
- Topology: preserve nodes and junctions for skeletonization.
- Noise and artifacts: avoid artifacts absent from the clean ground truth.

#### Segmentation evaluation

Source: `data/missing_struts/analysis/evaluation_summary.md`

# Segmentation Evaluation

- Score: **4/5**
- Foreground overlap is 87.3%, with 2.5% over-segmentation and 10.6% under-segmentation. The result has 226 connected components versus 227 in the ground truth, 29 junctions versus 32, and 3 extra small artifacts. These connectivity, topology, and noise differences justify a score of 4.

#### Segmented mask volume statistics

Source: `data/missing_struts/analysis/segmented_mask.tif`

```json
{
  "path": "data/missing_struts/analysis/segmented_mask.tif",
  "foreground_voxels": 23410270,
  "background_voxels": 495709685,
  "foreground_fraction": 0.0450960703292556,
  "source": "segmentation_report.md"
}
```


### Summary Card

```json
{
  "step": "Segmentation",
  "subagent": ".codex/agents/segmentation",
  "status": "passed",
  "command": "/home/mtrev008/miniconda3/bin/python -B .codex/agents/segmentation/run.py",
  "stdout": "Segmentation pipeline step",
  "stderr": "",
  "outputs": [
    {
      "path": "data/missing_struts/analysis/segmentation_workflow.py",
      "exists": true,
      "size_bytes": 6261
    },
    {
      "path": "data/missing_struts/analysis/segmented_mask.tif",
      "exists": true,
      "size_bytes": 519330900
    },
    {
      "path": "data/missing_struts/analysis/segmentation_slice_380.png",
      "exists": true,
      "size_bytes": 14740
    },
    {
      "path": "data/missing_struts/analysis/segmentation_report.md",
      "exists": true,
      "size_bytes": 999
    },
    {
      "path": "data/missing_struts/analysis/evaluation_summary.md",
      "exists": true,
      "size_bytes": 332
    }
  ],
  "results": [
    {
      "title": "Segmentation report",
      "source": "data/missing_struts/analysis/segmentation_report.md",
      "content": "# Segmentation Report\n\n- Method: smoothed slice-median brightness correction\n- Iterations run: **1**\n- Failed attempts: **0**\n- Segmented mask: `/home/mtrev008/Desktop/LLNL_DSC/llnl_data_science_challenge_2026/data/missing_struts/analysis/segmented_mask.tif`\n- Executable script copy: `/home/mtrev008/Desktop/LLNL_DSC/llnl_data_science_challenge_2026/data/missing_struts/analysis/segmentation_workflow.py`\n- Slice 380 visualization: `/home/mtrev008/Desktop/LLNL_DSC/llnl_data_science_challenge_2026/data/missing_struts/analysis/segmentation_slice_380.png`\n- Foreground voxels: **23,410,270**\n- Background voxels: **495,709,685**\n- Median foreground fraction: **3.97%**\n\n## README Validation Criteria\n\n- Structural integrity: inspect slice 380 and downstream skeleton connectivity.\n- False positives/negatives: compare over-segmentation noise and missing struts.\n- Topology: preserve nodes and junctions for skeletonization.\n- Noise and artifacts: avoid artifacts absent from the clean ground truth."
    },
    {
      "title": "Segmentation evaluation",
      "source": "data/missing_struts/analysis/evaluation_summary.md",
      "content": "# Segmentation Evaluation\n\n- Score: **4/5**\n- Foreground overlap is 87.3%, with 2.5% over-segmentation and 10.6% under-segmentation. The result has 226 connected components versus 227 in the ground truth, 29 junctions versus 32, and 3 extra small artifacts. These connectivity, topology, and noise differences justify a score of 4."
    },
    {
      "title": "Segmented mask volume statistics",
      "source": "data/missing_struts/analysis/segmented_mask.tif",
      "content": {
        "path": "data/missing_struts/analysis/segmented_mask.tif",
        "foreground_voxels": 23410270,
        "background_voxels": 495709685,
        "foreground_fraction": 0.0450960703292556,
        "source": "segmentation_report.md"
      }
    }
  ],
  "metrics": {
    "return_code": 0
  },
  "issues": []
}
```

## Step 3: Skeletonization

- Subagent: `.codex/agents/skeletonization`
- Status: `passed`
- Command: `/home/mtrev008/miniconda3/bin/python -B .codex/agents/skeletonization/run.py`
- Return code: `0`

### Result Artifacts

- `data/missing_struts/analysis/skeleton.tif` - present, 519314884 bytes

### Result Content

#### Skeleton output

Source: `data/missing_struts/analysis/skeleton.tif`

```json
{
  "path": "data/missing_struts/analysis/skeleton.tif",
  "format": "BigTIFF",
  "result": "3D centerline skeleton artifact generated from segmented_mask.tif"
}
```


### Summary Card

```json
{
  "step": "Skeletonization",
  "subagent": ".codex/agents/skeletonization",
  "status": "passed",
  "command": "/home/mtrev008/miniconda3/bin/python -B .codex/agents/skeletonization/run.py",
  "stdout": "Skeletonization pipeline step",
  "stderr": "",
  "outputs": [
    {
      "path": "data/missing_struts/analysis/skeleton.tif",
      "exists": true,
      "size_bytes": 519314884
    }
  ],
  "results": [
    {
      "title": "Skeleton output",
      "source": "data/missing_struts/analysis/skeleton.tif",
      "content": {
        "path": "data/missing_struts/analysis/skeleton.tif",
        "format": "BigTIFF",
        "result": "3D centerline skeleton artifact generated from segmented_mask.tif"
      }
    }
  ],
  "metrics": {
    "return_code": 0
  },
  "issues": []
}
```

## Step 4: Detecting Defects

- Subagent: `.codex/agents/defect_detection`
- Status: `passed`
- Command: `/home/mtrev008/miniconda3/bin/python -B .codex/agents/defect_detection/run.py`
- Return code: `0`

### Result Artifacts

- `data/missing_struts/analysis/observed_lattice.json` - present, 48419091 bytes
- `data/missing_struts/analysis/per_strut_defects.json` - present, 26388433 bytes
- `data/missing_struts/analysis/anomaly_summary.json` - present, 1893 bytes
- `data/missing_struts/analysis/anomaly_summary.md` - present, 2291 bytes
- `data/missing_struts/analysis/defect_visual_review/visual_review_index.json` - present, 46221 bytes
- `data/missing_struts/analysis/defect_visual_review/hf_model_review_results.json` - present, 140 bytes

### Result Content

#### Anomaly summary

Source: `data/missing_struts/analysis/anomaly_summary.json`

```json
{
  "reference_json": "/home/mtrev008/Desktop/LLNL_DSC/llnl_data_science_challenge_2026/data/missing_struts/registered_jsons/210127_Brian_Tran_strut_lattices_0point5dash1 1 Slices.json",
  "observed_json": "/home/mtrev008/Desktop/LLNL_DSC/llnl_data_science_challenge_2026/data/missing_struts/analysis/observed_lattice.json",
  "per_strut_json": "/home/mtrev008/Desktop/LLNL_DSC/llnl_data_science_challenge_2026/data/missing_struts/analysis/per_strut_defects.json",
  "summary": "/home/mtrev008/Desktop/LLNL_DSC/llnl_data_science_challenge_2026/data/missing_struts/analysis/anomaly_summary.md",
  "method": "expected-strut skeleton coverage and endpoint-connectivity test",
  "expected_struts": 18468,
  "observed_struts": 19824,
  "classification_counts": {
    "disconnected": 1896,
    "missing": 314,
    "present": 16258
  },
  "graph_candidates": 2210,
  "weak_segmentation_candidates": 0,
  "confirmed_anomalies": 2210,
  "confirmed_anomaly_percentage": 11.96664500758068,
  "sample_count": 11,
  "search_radius_voxels": 12.0,
  "profile_segments": 20,
  "low_profile_threshold": 0.2,
  "profile_classification_counts": {
    "broken": 658,
    "continuous": 17193,
    "missing": 314,
    "weak": 303
  },
  "visual_review_dir": "/home/mtrev008/Desktop/LLNL_DSC/llnl_data_science_challenge_2026/data/missing_struts/analysis/defect_visual_review",
  "visual_review_index": "/home/mtrev008/Desktop/LLNL_DSC/llnl_data_science_challenge_2026/data/missing_struts/analysis/defect_visual_review/visual_review_index.json",
  "visual_review_panels": 100,
  "visual_classification_counts": {
    "missing": 100
  },
  "hf_model_review_results": "/home/mtrev008/Desktop/LLNL_DSC/llnl_data_science_challenge_2026/data/missing_struts/analysis/defect_visual_review/hf_model_review_results.json",
  "hf_model_review_count": 0,
  "hf_model": "zai-org/GLM-4.5V",
  "hf_model_classification_counts": {}
}
```

#### Visual review index

Source: `data/missing_struts/analysis/defect_visual_review/visual_review_index.json`

```json
{
  "visual_panel_count": 100,
  "max_visual_panels": 100,
  "panels": [
    {
      "strut_id": 1801,
      "classification": "missing",
      "visual_classification": "missing",
      "visual_confidence": 0.95,
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_01801_missing.svg",
      "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_01801_missing.png",
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_01801_missing_profile.svg"
    },
    {
      "strut_id": 1884,
      "classification": "missing",
      "visual_classification": "missing",
      "visual_confidence": 0.95,
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_01884_missing.svg",
      "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_01884_missing.png",
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_01884_missing_profile.svg"
    },
    {
      "strut_id": 1885,
      "classification": "missing",
      "visual_classification": "missing",
      "visual_confidence": 0.95,
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_01885_missing.svg",
      "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_01885_missing.png",
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_01885_missing_profile.svg"
    },
    {
      "strut_id": 1912,
      "classification": "missing",
      "visual_classification": "missing",
      "visual_confidence": 0.95,
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_01912_missing.svg",
      "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_01912_missing.png",
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_01912_missing_profile.svg"
    },
    {
      "strut_id": 1913,
      "classification": "missing",
      "visual_classification": "missing",
      "visual_confidence": 0.95,
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_01913_missing.svg",
      "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_01913_missing.png",
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_01913_missing_profile.svg"
    },
    {
      "strut_id": 1914,
      "classification": "missing",
      "visual_classification": "missing",
      "visual_confidence": 0.95,
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_01914_missing.svg",
      "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_01914_missing.png",
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_01914_missing_profile.svg"
    },
    {
      "strut_id": 1968,
      "classification": "missing",
      "visual_classification": "missing",
      "visual_confidence": 0.95,
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_01968_missing.svg",
      "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_01968_missing.png",
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_01968_missing_profile.svg"
    },
    {
      "strut_id": 1970,
      "classification": "missing",
      "visual_classification": "missing",
      "visual_confidence": 0.95,
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_01970_missing.svg",
      "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_01970_missing.png",
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_01970_missing_profile.svg"
    },
    {
      "strut_id": 2000,
      "classification": "missing",
      "visual_classification": "missing",
      "visual_confidence": 0.95,
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_02000_missing.svg",
      "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_02000_missing.png",
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_02000_missing_profile.svg"
    },
    {
      "strut_id": 3900,
      "classification": "missing",
      "visual_classification": "missing",
      "visual_confidence": 0.95,
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_03900_missing.svg",
      "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_03900_missing.png",
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_03900_missing_profile.svg"
    },
    {
      "strut_id": 3986,
      "classification": "missing",
      "visual_classification": "missing",
      "visual_confidence": 0.95,
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_03986_missing.svg",
      "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_03986_missing.png",
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_03986_missing_profile.svg"
    },
    {
      "strut_id": 5806,
      "classification": "missing",
      "visual_classification": "missing",
      "visual_confidence": 0.95,
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_05806_missing.svg",
      "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_05806_missing.png",
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_05806_missing_profile.svg"
    },
    {
      "strut_id": 5833,
      "classification": "missing",
      "visual_classification": "missing",
      "visual_confidence": 0.95,
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_05833_missing.svg",
      "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_05833_missing.png",
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_05833_missing_profile.svg"
    },
    {
      "strut_id": 5916,
      "classification": "missing",
      "visual_classification": "missing",
      "visual_confidence": 0.95,
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_05916_missing.svg",
      "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_05916_missing.png",
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_05916_missing_profile.svg"
    },
    {
      "strut_id": 5972,
      "classification": "missing",
      "visual_classification": "missing",
      "visual_confidence": 0.95,
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_05972_missing.svg",
      "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_05972_missing.png",
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_05972_missing_profile.svg"
    },
    {
      "strut_id": 5974,
      "classification": "missing",
      "visual_classification": "missing",
      "visual_confidence": 0.95,
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_05974_missing.svg",
      "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_05974_missing.png",
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_05974_missing_profile.svg"
    },
    {
      "strut_id": 6032,
      "classification": "missing",
      "visual_classification": "missing",
      "visual_confidence": 0.95,
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_06032_missing.svg",
      "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_06032_missing.png",
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_06032_missing_profile.svg"
    },
    {
      "strut_id": 6034,
      "classification": "missing",
      "visual_classification": "missing",
      "visual_confidence": 0.95,
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_06034_missing.svg",
      "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_06034_missing.png",
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_06034_missing_profile.svg"
    },
    {
      "strut_id": 7849,
      "classification": "missing",
      "visual_classification": "missing",
      "visual_confidence": 0.95,
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_07849_missing.svg",
      "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_07849_missing.png",
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_07849_missing_profile.svg"
    },
    {
      "strut_id": 7851,
      "classification": "missing",
      "visual_classification": "missing",
      "visual_confidence": 0.95,
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_07851_missing.svg",
      "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_07851_missing.png",
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_07851_missing_profile.svg"
    },
    {
      "strut_id": 7877,
      "classification": "missing",
      "visual_classification": "missing",
      "visual_confidence": 0.95,
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_07877_missing.svg",
      "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_07877_missing.png",
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_07877_missing_profile.svg"
    },
    {
      "strut_id": 7878,
      "classification": "missing",
      "visual_classification": "missing",
      "visual_confidence": 0.95,
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_07878_missing.svg",
      "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_07878_missing.png",
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_07878_missing_profile.svg"
    },
    {
      "strut_id": 7904,
      "classification": "missing",
      "visual_classification": "missing",
      "visual_confidence": 0.95,
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_07904_missing.svg",
      "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_07904_missing.png",
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_07904_missing_profile.svg"
    },
    {
      "strut_id": 8016,
      "classification": "missing",
      "visual_classification": "missing",
      "visual_confidence": 0.95,
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_08016_missing.svg",
      "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_08016_missing.png",
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_08016_missing_profile.svg"
    },
    {
      "strut_id": 8048,
      "classification": "missing",
      "visual_classification": "missing",
      "visual_confidence": 0.95,
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_08048_missing.svg",
      "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_08048_missing.png",
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_08048_missing_profile.svg"
    },
    {
      "strut_id": 8050,
      "classification": "missing",
      "visual_classification": "missing",
      "visual_confidence": 0.95,
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_08050_missing.svg",
      "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_08050_missing.png",
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_08050_missing_profile.svg"
    },
    {
      "strut_id": 8051,
      "classification": "missing",
      "visual_classification": "missing",
      "visual_confidence": 0.95,
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_08051_missing.svg",
      "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_08051_missing.png",
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_08051_missing_profile.svg"
    },
    {
      "strut_id": 9836,
      "classification": "missing",
      "visual_classification": "missing",
      "visual_confidence": 0.95,
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_09836_missing.svg",
      "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_09836_missing.png",
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_09836_missing_profile.svg"
    },
    {
      "strut_id": 9864,
      "classification": "missing",
      "visual_classification": "missing",
      "visual_confidence": 0.95,
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_09864_missing.svg",
      "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_09864_missing.png",
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_09864_missing_profile.svg"
    },
    {
      "strut_id": 10034,
      "classification": "missing",
      "visual_classification": "missing",
      "visual_confidence": 0.95,
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_10034_missing.svg",
      "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_10034_missing.png",
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_10034_missing_profile.svg"
    },
    {
      "strut_id": 11854,
      "classification": "missing",
      "visual_classification": "missing",
      "visual_confidence": 0.95,
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_11854_missing.svg",
      "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_11854_missing.png",
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_11854_missing_profile.svg"
    },
    {
      "strut_id": 11882,
      "classification": "missing",
      "visual_classification": "missing",
      "visual_confidence": 0.95,
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_11882_missing.svg",
      "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_11882_missing.png",
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_11882_missing_profile.svg"
    },
    {
      "strut_id": 11883,
      "classification": "missing",
      "visual_classification": "missing",
      "visual_confidence": 0.95,
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_11883_missing.svg",
      "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_11883_missing.png",
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_11883_missing_profile.svg"
    },
    {
      "strut_id": 11909,
      "classification": "missing",
      "visual_classification": "missing",
      "visual_confidence": 0.95,
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_11909_missing.svg",
      "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_11909_missing.png",
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_11909_missing_profile.svg"
    },
    {
      "strut_id": 11910,
      "classification": "missing",
      "visual_classification": "missing",
      "visual_confidence": 0.95,
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_11910_missing.svg",
      "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_11910_missing.png",
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_11910_missing_profile.svg"
    },
    {
      "strut_id": 12020,
      "classification": "missing",
      "visual_classification": "missing",
      "visual_confidence": 0.95,
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_12020_missing.svg",
      "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_12020_missing.png",
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_12020_missing_profile.svg"
    },
    {
      "strut_id": 13868,
      "classification": "missing",
      "visual_classification": "missing",
      "visual_confidence": 0.95,
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_13868_missing.svg",
      "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_13868_missing.png",
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_13868_missing_profile.svg"
    },
    {
      "strut_id": 13869,
      "classification": "missing",
      "visual_classification": "missing",
      "visual_confidence": 0.95,
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_13869_missing.svg",
      "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_13869_missing.png",
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_13869_missing_profile.svg"
    },
    {
      "strut_id": 13870,
      "classification": "missing",
      "visual_classification": "missing",
      "visual_confidence": 0.95,
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_13870_missing.svg",
      "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_13870_missing.png",
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_13870_missing_profile.svg"
    },
    {
      "strut_id": 13896,
      "classification": "missing",
      "visual_classification": "missing",
      "visual_confidence": 0.95,
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_13896_missing.svg",
      "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_13896_missing.png",
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_13896_missing_profile.svg"
    },
    {
      "strut_id": 13899,
      "classification": "missing",
      "visual_classification": "missing",
      "visual_confidence": 0.95,
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_13899_missing.svg",
      "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_13899_missing.png",
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_13899_missing_profile.svg"
    },
    {
      "strut_id": 13924,
      "classification": "missing",
      "visual_classification": "missing",
      "visual_confidence": 0.95,
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_13924_missing.svg",
      "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_13924_missing.png",
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_13924_missing_profile.svg"
    },
    {
      "strut_id": 13925,
      "classification": "missing",
      "visual_classification": "missing",
      "visual_confidence": 0.95,
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_13925_missing.svg",
      "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_13925_missing.png",
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_13925_missing_profile.svg"
    },
    {
      "strut_id": 14008,
      "classification": "missing",
      "visual_classification": "missing",
      "visual_confidence": 0.95,
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_14008_missing.svg",
      "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_14008_missing.png",
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_14008_missing_profile.svg"
    },
    {
      "strut_id": 14037,
      "classification": "missing",
      "visual_classification": "missing",
      "visual_confidence": 0.95,
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_14037_missing.svg",
      "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_14037_missing.png",
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_14037_missing_profile.svg"
    },
    {
      "strut_id": 14038,
      "classification": "missing",
      "visual_classification": "missing",
      "visual_confidence": 0.95,
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_14038_missing.svg",
      "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_14038_missing.png",
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_14038_missing_profile.svg"
    },
    {
      "strut_id": 14096,
      "classification": "missing",
      "visual_classification": "missing",
      "visual_confidence": 0.95,
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_14096_missing.svg",
      "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_14096_missing.png",
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_14096_missing_profile.svg"
    },
    {
      "strut_id": 14098,
      "classification": "missing",
      "visual_classification": "missing",
      "visual_confidence": 0.95,
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_14098_missing.svg",
      "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_14098_missing.png",
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_14098_missing_profile.svg"
    },
    {
      "strut_id": 15940,
      "classification": "missing",
      "visual_classification": "missing",
      "visual_confidence": 0.95,
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_15940_missing.svg",
      "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_15940_missing.png",
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_15940_missing_profile.svg"
    },
    {
      "strut_id": 15941,
      "classification": "missing",
      "visual_classification": "missing",
      "visual_confidence": 0.95,
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_15941_missing.svg",
      "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_15941_missing.png",
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_15941_missing_profile.svg"
    },
    {
      "strut_id": 15942,
      "classification": "missing",
      "visual_classification": "missing",
      "visual_confidence": 0.95,
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_15942_missing.svg",
      "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_15942_missing.png",
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_15942_missing_profile.svg"
    },
    {
      "strut_id": 15943,
      "classification": "missing",
      "visual_classification": "missing",
      "visual_confidence": 0.95,
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_15943_missing.svg",
      "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_15943_missing.png",
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_15943_missing_profile.svg"
    },
    {
      "strut_id": 15970,
      "classification": "missing",
      "visual_classification": "missing",
      "visual_confidence": 0.95,
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_15970_missing.svg",
      "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_15970_missing.png",
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_15970_missing_profile.svg"
    },
    {
      "strut_id": 15971,
      "classification": "missing",
      "visual_classification": "missing",
      "visual_confidence": 0.95,
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_15971_missing.svg",
      "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_15971_missing.png",
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_15971_missing_profile.svg"
    },
    {
      "strut_id": 15996,
      "classification": "missing",
      "visual_classification": "missing",
      "visual_confidence": 0.95,
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_15996_missing.svg",
      "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_15996_missing.png",
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_15996_missing_profile.svg"
    },
    {
      "strut_id": 16024,
      "classification": "missing",
      "visual_classification": "missing",
      "visual_confidence": 0.95,
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_16024_missing.svg",
      "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_16024_missing.png",
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_16024_missing_profile.svg"
    },
    {
      "strut_id": 18193,
      "classification": "missing",
      "visual_classification": "missing",
      "visual_confidence": 0.95,
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_18193_missing.svg",
      "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_18193_missing.png",
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_18193_missing_profile.svg"
    },
    {
      "strut_id": 18194,
      "classification": "missing",
      "visual_classification": "missing",
      "visual_confidence": 0.95,
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_18194_missing.svg",
      "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_18194_missing.png",
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_18194_missing_profile.svg"
    },
    {
      "strut_id": 18195,
      "classification": "missing",
      "visual_classification": "missing",
      "visual_confidence": 0.95,
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_18195_missing.svg",
      "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_18195_missing.png",
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_18195_missing_profile.svg"
    },
    {
      "strut_id": 18226,
      "classification": "missing",
      "visual_classification": "missing",
      "visual_confidence": 0.95,
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_18226_missing.svg",
      "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_18226_missing.png",
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_18226_missing_profile.svg"
    },
    {
      "strut_id": 18227,
      "classification": "missing",
      "visual_classification": "missing",
      "visual_confidence": 0.95,
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_18227_missing.svg",
      "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_18227_missing.png",
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_18227_missing_profile.svg"
    },
    {
      "strut_id": 18257,
      "classification": "missing",
      "visual_classification": "missing",
      "visual_confidence": 0.95,
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_18257_missing.svg",
      "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_18257_missing.png",
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_18257_missing_profile.svg"
    },
    {
      "strut_id": 18289,
      "classification": "missing",
      "visual_classification": "missing",
      "visual_confidence": 0.95,
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_18289_missing.svg",
      "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_18289_missing.png",
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_18289_missing_profile.svg"
    },
    {
      "strut_id": 18290,
      "classification": "missing",
      "visual_classification": "missing",
      "visual_confidence": 0.95,
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_18290_missing.svg",
      "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_18290_missing.png",
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_18290_missing_profile.svg"
    },
    {
      "strut_id": 18322,
      "classification": "missing",
      "visual_classification": "missing",
      "visual_confidence": 0.95,
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_18322_missing.svg",
      "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_18322_missing.png",
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_18322_missing_profile.svg"
    },
    {
      "strut_id": 18323,
      "classification": "missing",
      "visual_classification": "missing",
      "visual_confidence": 0.95,
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_18323_missing.svg",
      "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_18323_missing.png",
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_18323_missing_profile.svg"
    },
    {
      "strut_id": 1800,
      "classification": "missing",
      "visual_classification": "missing",
      "visual_confidence": 0.85,
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_01800_missing.svg",
      "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_01800_missing.png",
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_01800_missing_profile.svg"
    },
    {
      "strut_id": 1940,
      "classification": "missing",
      "visual_classification": "missing",
      "visual_confidence": 0.85,
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_01940_missing.svg",
      "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_01940_missing.png",
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_01940_missing_profile.svg"
    },
    {
      "strut_id": 1969,
      "classification": "missing",
      "visual_classification": "missing",
      "visual_confidence": 0.85,
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_01969_missing.svg",
      "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_01969_missing.png",
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_01969_missing_profile.svg"
    },
    {
      "strut_id": 2001,
      "classification": "missing",
      "visual_classification": "missing",
      "visual_confidence": 0.85,
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_02001_missing.svg",
      "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_02001_missing.png",
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_02001_missing_profile.svg"
    },
    {
      "strut_id": 2002,
      "classification": "missing",
      "visual_classification": "missing",
      "visual_confidence": 0.85,
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_02002_missing.svg",
      "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_02002_missing.png",
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_02002_missing_profile.svg"
    },
    {
      "strut_id": 3818,
      "classification": "missing",
      "visual_classification": "missing",
      "visual_confidence": 0.85,
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_03818_missing.svg",
      "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_03818_missing.png",
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_03818_missing_profile.svg"
    },
    {
      "strut_id": 3847,
      "classification": "missing",
      "visual_classification": "missing",
      "visual_confidence": 0.85,
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_03847_missing.svg",
      "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_03847_missing.png",
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_03847_missing_profile.svg"
    },
    {
      "strut_id": 3958,
      "classification": "missing",
      "visual_classification": "missing",
      "visual_confidence": 0.85,
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_03958_missing.svg",
      "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_03958_missing.png",
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_03958_missing_profile.svg"
    },
    {
      "strut_id": 3984,
      "classification": "missing",
      "visual_classification": "missing",
      "visual_confidence": 0.85,
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_03984_missing.svg",
      "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_03984_missing.png",
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_03984_missing_profile.svg"
    },
    {
      "strut_id": 4016,
      "classification": "missing",
      "visual_classification": "missing",
      "visual_confidence": 0.85,
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_04016_missing.svg",
      "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_04016_missing.png",
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_04016_missing_profile.svg"
    },
    {
      "strut_id": 4018,
      "classification": "missing",
      "visual_classification": "missing",
      "visual_confidence": 0.85,
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_04018_missing.svg",
      "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_04018_missing.png",
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_04018_missing_profile.svg"
    },
    {
      "strut_id": 5807,
      "classification": "missing",
      "visual_classification": "missing",
      "visual_confidence": 0.85,
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_05807_missing.svg",
      "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_05807_missing.png",
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_05807_missing_profile.svg"
    },
    {
      "strut_id": 5832,
      "classification": "missing",
      "visual_classification": "missing",
      "visual_confidence": 0.85,
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_05832_missing.svg",
      "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_05832_missing.png",
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_05832_missing_profile.svg"
    },
    {
      "strut_id": 5834,
      "classification": "missing",
      "visual_classification": "missing",
      "visual_confidence": 0.85,
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_05834_missing.svg",
      "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_05834_missing.png",
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_05834_missing_profile.svg"
    },
    {
      "strut_id": 5918,
      "classification": "missing",
      "visual_classification": "missing",
      "visual_confidence": 0.85,
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_05918_missing.svg",
      "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_05918_missing.png",
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_05918_missing_profile.svg"
    },
    {
      "strut_id": 5944,
      "classification": "missing",
      "visual_classification": "missing",
      "visual_confidence": 0.85,
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_05944_missing.svg",
      "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_05944_missing.png",
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_05944_missing_profile.svg"
    },
    {
      "strut_id": 6000,
      "classification": "missing",
      "visual_classification": "missing",
      "visual_confidence": 0.85,
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_06000_missing.svg",
      "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_06000_missing.png",
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_06000_missing_profile.svg"
    },
    {
      "strut_id": 7820,
      "classification": "missing",
      "visual_classification": "missing",
      "visual_confidence": 0.85,
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_07820_missing.svg",
      "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_07820_missing.png",
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_07820_missing_profile.svg"
    },
    {
      "strut_id": 7821,
      "classification": "missing",
      "visual_classification": "missing",
      "visual_confidence": 0.85,
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_07821_missing.svg",
      "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_07821_missing.png",
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_07821_missing_profile.svg"
    },
    {
      "strut_id": 7848,
      "classification": "missing",
      "visual_classification": "missing",
      "visual_confidence": 0.85,
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_07848_missing.svg",
      "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_07848_missing.png",
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_07848_missing_profile.svg"
    },
    {
      "strut_id": 7876,
      "classification": "missing",
      "visual_classification": "missing",
      "visual_confidence": 0.85,
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_07876_missing.svg",
      "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_07876_missing.png",
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_07876_missing_profile.svg"
    },
    {
      "strut_id": 7934,
      "classification": "missing",
      "visual_classification": "missing",
      "visual_confidence": 0.85,
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_07934_missing.svg",
      "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_07934_missing.png",
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_07934_missing_profile.svg"
    },
    {
      "strut_id": 7962,
      "classification": "missing",
      "visual_classification": "missing",
      "visual_confidence": 0.85,
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_07962_missing.svg",
      "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_07962_missing.png",
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_07962_missing_profile.svg"
    },
    {
      "strut_id": 8018,
      "classification": "missing",
      "visual_classification": "missing",
      "visual_confidence": 0.85,
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_08018_missing.svg",
      "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_08018_missing.png",
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_08018_missing_profile.svg"
    },
    {
      "strut_id": 9867,
      "classification": "missing",
      "visual_classification": "missing",
      "visual_confidence": 0.85,
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_09867_missing.svg",
      "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_09867_missing.png",
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_09867_missing_profile.svg"
    },
    {
      "strut_id": 9921,
      "classification": "missing",
      "visual_classification": "missing",
      "visual_confidence": 0.85,
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_09921_missing.svg",
      "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_09921_missing.png",
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_09921_missing_profile.svg"
    },
    {
      "strut_id": 9923,
      "classification": "missing",
      "visual_classification": "missing",
      "visual_confidence": 0.85,
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_09923_missing.svg",
      "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_09923_missing.png",
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_09923_missing_profile.svg"
    },
    {
      "strut_id": 10006,
      "classification": "missing",
      "visual_classification": "missing",
      "visual_confidence": 0.85,
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_10006_missing.svg",
      "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_10006_missing.png",
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_10006_missing_profile.svg"
    },
    {
      "strut_id": 10032,
      "classification": "missing",
      "visual_classification": "missing",
      "visual_confidence": 0.85,
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_10032_missing.svg",
      "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_10032_missing.png",
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_10032_missing_profile.svg"
    },
    {
      "strut_id": 10064,
      "classification": "missing",
      "visual_classification": "missing",
      "visual_confidence": 0.85,
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_10064_missing.svg",
      "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_10064_missing.png",
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_10064_missing_profile.svg"
    },
    {
      "strut_id": 11855,
      "classification": "missing",
      "visual_classification": "missing",
      "visual_confidence": 0.85,
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_11855_missing.svg",
      "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_11855_missing.png",
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_11855_missing_profile.svg"
    },
    {
      "strut_id": 11936,
      "classification": "missing",
      "visual_classification": "missing",
      "visual_confidence": 0.85,
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_11936_missing.svg",
      "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_11936_missing.png",
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_11936_missing_profile.svg"
    },
    {
      "strut_id": 11938,
      "classification": "missing",
      "visual_classification": "missing",
      "visual_confidence": 0.85,
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_11938_missing.svg",
      "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_11938_missing.png",
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_11938_missing_profile.svg"
    },
    {
      "strut_id": 11964,
      "classification": "missing",
      "visual_classification": "missing",
      "visual_confidence": 0.85,
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_11964_missing.svg",
      "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_11964_missing.png",
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_11964_missing_profile.svg"
    }
  ]
}
```

#### Hugging Face model review results

Source: `data/missing_struts/analysis/defect_visual_review/hf_model_review_results.json`

```json
{
  "status": "skipped",
  "reason": "DEFECT_HF_REVIEW_LIMIT is 0",
  "model": "zai-org/GLM-4.5V",
  "requested_limit": 0,
  "reviews": []
}
```

#### Example per-strut classifications

Source: `data/missing_struts/analysis/per_strut_defects.json`

```json
{
  "total_records": 18468,
  "first_10_anomalies": [
    {
      "strut_id": 0,
      "classification": "missing",
      "reason": "material profile is low across the expected strut",
      "coverage_ratio": 0.18181818181818182,
      "profile_classification": "missing",
      "profile_mean": 0.09,
      "profile_min": 0.0,
      "low_profile_segments": [
        0,
        1,
        2,
        3,
        4,
        5,
        6,
        7,
        8,
        9,
        10,
        11,
        12,
        13,
        14,
        15,
        16
      ],
      "longest_low_profile_gap": 17,
      "profile_plot": null,
      "visual_evidence_png": null
    },
    {
      "strut_id": 1,
      "classification": "disconnected",
      "reason": "endpoints have support but one or more middle segments drop below threshold",
      "coverage_ratio": 0.5454545454545454,
      "profile_classification": "broken",
      "profile_mean": 0.24,
      "profile_min": 0.0,
      "low_profile_segments": [
        4,
        5,
        6,
        7,
        8,
        9,
        10,
        11,
        12,
        13,
        14,
        15
      ],
      "longest_low_profile_gap": 12,
      "profile_plot": null,
      "visual_evidence_png": null
    },
    {
      "strut_id": 2,
      "classification": "disconnected",
      "reason": "endpoints have support but one or more middle segments drop below threshold",
      "coverage_ratio": 0.45454545454545453,
      "profile_classification": "broken",
      "profile_mean": 0.33562870818962093,
      "profile_min": 0.0,
      "low_profile_segments": [
        4,
        5,
        6,
        7,
        8,
        9,
        10,
        11,
        12,
        13,
        14
      ],
      "longest_low_profile_gap": 11,
      "profile_plot": null,
      "visual_evidence_png": null
    },
    {
      "strut_id": 3,
      "classification": "disconnected",
      "reason": "endpoints have support but one or more middle segments drop below threshold",
      "coverage_ratio": 0.45454545454545453,
      "profile_classification": "broken",
      "profile_mean": 0.26999999999999996,
      "profile_min": 0.0,
      "low_profile_segments": [
        4,
        5,
        6,
        7,
        8,
        9,
        10,
        11,
        12,
        13,
        14
      ],
      "longest_low_profile_gap": 11,
      "profile_plot": null,
      "visual_evidence_png": null
    },
    {
      "strut_id": 4,
      "classification": "disconnected",
      "reason": "endpoints have support but one or more middle segments drop below threshold",
      "coverage_ratio": 0.5454545454545454,
      "profile_classification": "broken",
      "profile_mean": 0.4016513716513142,
      "profile_min": 0.0,
      "low_profile_segments": [
        0,
        1,
        2,
        3,
        4,
        5,
        6,
        7,
        8,
        9
      ],
      "longest_low_profile_gap": 10,
      "profile_plot": null,
      "visual_evidence_png": null
    },
    {
      "strut_id": 5,
      "classification": "disconnected",
      "reason": "skeleton material is nearby, but no observed path connects both expected endpoints",
      "coverage_ratio": 1.0,
      "profile_classification": "continuous",
      "profile_mean": 0.7193620069153536,
      "profile_min": 0.6,
      "low_profile_segments": [],
      "longest_low_profile_gap": 0,
      "profile_plot": null,
      "visual_evidence_png": null
    },
    {
      "strut_id": 7,
      "classification": "disconnected",
      "reason": "skeleton material is nearby, but no observed path connects both expected endpoints",
      "coverage_ratio": 1.0,
      "profile_classification": "continuous",
      "profile_mean": 0.8609133599314905,
      "profile_min": 0.7,
      "low_profile_segments": [],
      "longest_low_profile_gap": 0,
      "profile_plot": null,
      "visual_evidence_png": null
    },
    {
      "strut_id": 8,
      "classification": "disconnected",
      "reason": "endpoints have support but one or more middle segments drop below threshold",
      "coverage_ratio": 0.7272727272727273,
      "profile_classification": "broken",
      "profile_mean": 0.6267982511152294,
      "profile_min": 0.0,
      "low_profile_segments": [
        0,
        1,
        2,
        3,
        4
      ],
      "longest_low_profile_gap": 5,
      "profile_plot": null,
      "visual_evidence_png": null
    },
    {
      "strut_id": 9,
      "classification": "disconnected",
      "reason": "skeleton material is nearby, but no observed path connects both expected endpoints",
      "coverage_ratio": 0.9090909090909091,
      "profile_classification": "weak",
      "profile_mean": 0.6932441050820582,
      "profile_min": 0.0,
      "low_profile_segments": [
        12
      ],
      "longest_low_profile_gap": 1,
      "profile_plot": null,
      "visual_evidence_png": null
    },
    {
      "strut_id": 10,
      "classification": "disconnected",
      "reason": "endpoints have support but one or more middle segments drop below threshold",
      "coverage_ratio": 0.5454545454545454,
      "profile_classification": "broken",
      "profile_mean": 0.43499999999999994,
      "profile_min": 0.0,
      "low_profile_segments": [
        5,
        6,
        7,
        8,
        9,
        10,
        11,
        12,
        13,
        14
      ],
      "longest_low_profile_gap": 10,
      "profile_plot": null,
      "visual_evidence_png": null
    }
  ]
}
```

#### Anomaly Markdown summary

Source: `data/missing_struts/analysis/anomaly_summary.md`

# Defect Detection Summary

- Expected struts: **18468**
- Observed skeleton struts: **19824**
- Present struts: **16258**
- Weak struts: **0**
- Missing struts: **314**
- Disconnected struts: **1896**
- Confirmed anomalies: **2210**
- Confirmed anomaly percentage: **11.97%**
- Profile segments per strut: **20**
- Profile classification counts: `{'broken': 658, 'continuous': 17193, 'missing': 314, 'weak': 303}`
- Visual review panels generated: **100**
- Visual review index: `/home/mtrev008/Desktop/LLNL_DSC/llnl_data_science_challenge_2026/data/missing_struts/analysis/defect_visual_review/visual_review_index.json`
- Hugging Face model reviews: **0**
- Hugging Face model review results: `/home/mtrev008/Desktop/LLNL_DSC/llnl_data_science_challenge_2026/data/missing_struts/analysis/defect_visual_review/hf_model_review_results.json`

## Decision Rules

- Each expected strut is sampled at 11 evenly spaced points.
- A sample is covered when an observed skeleton point is within 12 voxels.
- `present`: coverage is at least 65% and the same observed skeleton path reaches both endpoints.
- `missing`: coverage is 10% or less.
- `disconnected`: coverage is at least 25%, but no observed path connects both endpoints.
- `weak`: partial coverage remains below the present threshold.

## Node-to-Node Material Profile

- Each expected JSON edge is divided into 20 equal segments from node x to node y.
- Each segment receives a support value from nearby observed skeleton evidence within 12 voxels.
- Segment values below 0.20 are low-support regions.
- `missing`: the profile is low across the expected strut.
- `disconnected`: endpoints have support, but a middle low-support gap appears.
- `weak`: the profile has partial support or isolated low-support segments.
- `continuous`: the profile is supported along the expected edge.

## Visual Review Layer

- Candidate anomalies are rendered as SVG panels with two projections: XY and XZ.
- Red/orange/purple lines show the expected strut; blue points show nearby observed skeleton evidence.
- The visual label is derived from the same panel evidence and stored per strut.
- When `HUGGINGFACE_API_KEY` is set and `DEFECT_HF_REVIEW_LIMIT` is greater than 0, candidate panels are sent to the configured Hugging Face vision-language model.


### Summary Card

```json
{
  "step": "Detecting Defects",
  "subagent": ".codex/agents/defect_detection",
  "status": "passed",
  "command": "/home/mtrev008/miniconda3/bin/python -B .codex/agents/defect_detection/run.py",
  "stdout": "Detecting Defects pipeline step\n{\"status\": \"passed\", \"reference_json\": \"/home/mtrev008/Desktop/LLNL_DSC/llnl_data_science_challenge_2026/data/missing_struts/registered_jsons/210127_Brian_Tran_strut_lattices_0point5dash1 1 Slices.json\", \"observed_json\": \"/home/mtrev008/Desktop/LLNL_DSC/llnl_data_science_challenge_2026/data/missing_struts/analysis/observed_lattice.json\", \"per_strut_json\": \"/home/mtrev008/Desktop/LLNL_DSC/llnl_data_science_challenge_2026/data/missing_struts/analysis/per_strut_defects.json\", \"summary\": \"/home/mtrev008/Desktop/LLNL_DSC/llnl_data_science_challenge_2026/data/missing_struts/analysis/anomaly_summary.md\", \"method\": \"expected-strut skeleton coverage and endpoint-connectivity test\", \"expected_struts\": 18468, \"observed_struts\": 19824, \"classification_counts\": {\"disconnected\": 1896, \"missing\": 314, \"present\": 16258}, \"graph_candidates\": 2210, \"weak_segmentation_candidates\": 0, \"confirmed_anomalies\": 2210, \"confirmed_anomaly_percentage\": 11.96664500758068, \"sample_count\": 11, \"search_radius_voxels\": 12.0, \"profile_segments\": 20, \"low_profile_threshold\": 0.2, \"profile_classification_counts\": {\"broken\": 658, \"continuous\": 17193, \"missing\": 314, \"weak\": 303}, \"visual_review_dir\": \"/home/mtrev008/Desktop/LLNL_DSC/llnl_data_science_challenge_2026/data/missing_struts/analysis/defect_visual_review\", \"visual_review_index\": \"/home/mtrev008/Desktop/LLNL_DSC/llnl_data_science_challenge_2026/data/missing_struts/analysis/defect_visual_review/visual_review_index.json\", \"visual_review_panels\": 100, \"visual_classification_counts\": {\"missing\": 100}, \"hf_model_review_results\": \"/home/mtrev008/Desktop/LLNL_DSC/llnl_data_science_challenge_2026/data/missing_struts/analysis/defect_visual_review/hf_model_review_results.json\", \"hf_model_review_count\": 0, \"hf_model\": \"zai-org/GLM-4.5V\", \"hf_model_classification_counts\": {}}",
  "stderr": "",
  "outputs": [
    {
      "path": "data/missing_struts/analysis/observed_lattice.json",
      "exists": true,
      "size_bytes": 48419091
    },
    {
      "path": "data/missing_struts/analysis/per_strut_defects.json",
      "exists": true,
      "size_bytes": 26388433
    },
    {
      "path": "data/missing_struts/analysis/anomaly_summary.json",
      "exists": true,
      "size_bytes": 1893
    },
    {
      "path": "data/missing_struts/analysis/anomaly_summary.md",
      "exists": true,
      "size_bytes": 2291
    },
    {
      "path": "data/missing_struts/analysis/defect_visual_review/visual_review_index.json",
      "exists": true,
      "size_bytes": 46221
    },
    {
      "path": "data/missing_struts/analysis/defect_visual_review/hf_model_review_results.json",
      "exists": true,
      "size_bytes": 140
    }
  ],
  "results": [
    {
      "title": "Anomaly summary",
      "source": "data/missing_struts/analysis/anomaly_summary.json",
      "content": {
        "reference_json": "/home/mtrev008/Desktop/LLNL_DSC/llnl_data_science_challenge_2026/data/missing_struts/registered_jsons/210127_Brian_Tran_strut_lattices_0point5dash1 1 Slices.json",
        "observed_json": "/home/mtrev008/Desktop/LLNL_DSC/llnl_data_science_challenge_2026/data/missing_struts/analysis/observed_lattice.json",
        "per_strut_json": "/home/mtrev008/Desktop/LLNL_DSC/llnl_data_science_challenge_2026/data/missing_struts/analysis/per_strut_defects.json",
        "summary": "/home/mtrev008/Desktop/LLNL_DSC/llnl_data_science_challenge_2026/data/missing_struts/analysis/anomaly_summary.md",
        "method": "expected-strut skeleton coverage and endpoint-connectivity test",
        "expected_struts": 18468,
        "observed_struts": 19824,
        "classification_counts": {
          "disconnected": 1896,
          "missing": 314,
          "present": 16258
        },
        "graph_candidates": 2210,
        "weak_segmentation_candidates": 0,
        "confirmed_anomalies": 2210,
        "confirmed_anomaly_percentage": 11.96664500758068,
        "sample_count": 11,
        "search_radius_voxels": 12.0,
        "profile_segments": 20,
        "low_profile_threshold": 0.2,
        "profile_classification_counts": {
          "broken": 658,
          "continuous": 17193,
          "missing": 314,
          "weak": 303
        },
        "visual_review_dir": "/home/mtrev008/Desktop/LLNL_DSC/llnl_data_science_challenge_2026/data/missing_struts/analysis/defect_visual_review",
        "visual_review_index": "/home/mtrev008/Desktop/LLNL_DSC/llnl_data_science_challenge_2026/data/missing_struts/analysis/defect_visual_review/visual_review_index.json",
        "visual_review_panels": 100,
        "visual_classification_counts": {
          "missing": 100
        },
        "hf_model_review_results": "/home/mtrev008/Desktop/LLNL_DSC/llnl_data_science_challenge_2026/data/missing_struts/analysis/defect_visual_review/hf_model_review_results.json",
        "hf_model_review_count": 0,
        "hf_model": "zai-org/GLM-4.5V",
        "hf_model_classification_counts": {}
      }
    },
    {
      "title": "Visual review index",
      "source": "data/missing_struts/analysis/defect_visual_review/visual_review_index.json",
      "content": {
        "visual_panel_count": 100,
        "max_visual_panels": 100,
        "panels": [
          {
            "strut_id": 1801,
            "classification": "missing",
            "visual_classification": "missing",
            "visual_confidence": 0.95,
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_01801_missing.svg",
            "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_01801_missing.png",
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_01801_missing_profile.svg"
          },
          {
            "strut_id": 1884,
            "classification": "missing",
            "visual_classification": "missing",
            "visual_confidence": 0.95,
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_01884_missing.svg",
            "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_01884_missing.png",
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_01884_missing_profile.svg"
          },
          {
            "strut_id": 1885,
            "classification": "missing",
            "visual_classification": "missing",
            "visual_confidence": 0.95,
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_01885_missing.svg",
            "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_01885_missing.png",
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_01885_missing_profile.svg"
          },
          {
            "strut_id": 1912,
            "classification": "missing",
            "visual_classification": "missing",
            "visual_confidence": 0.95,
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_01912_missing.svg",
            "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_01912_missing.png",
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_01912_missing_profile.svg"
          },
          {
            "strut_id": 1913,
            "classification": "missing",
            "visual_classification": "missing",
            "visual_confidence": 0.95,
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_01913_missing.svg",
            "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_01913_missing.png",
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_01913_missing_profile.svg"
          },
          {
            "strut_id": 1914,
            "classification": "missing",
            "visual_classification": "missing",
            "visual_confidence": 0.95,
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_01914_missing.svg",
            "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_01914_missing.png",
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_01914_missing_profile.svg"
          },
          {
            "strut_id": 1968,
            "classification": "missing",
            "visual_classification": "missing",
            "visual_confidence": 0.95,
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_01968_missing.svg",
            "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_01968_missing.png",
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_01968_missing_profile.svg"
          },
          {
            "strut_id": 1970,
            "classification": "missing",
            "visual_classification": "missing",
            "visual_confidence": 0.95,
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_01970_missing.svg",
            "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_01970_missing.png",
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_01970_missing_profile.svg"
          },
          {
            "strut_id": 2000,
            "classification": "missing",
            "visual_classification": "missing",
            "visual_confidence": 0.95,
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_02000_missing.svg",
            "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_02000_missing.png",
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_02000_missing_profile.svg"
          },
          {
            "strut_id": 3900,
            "classification": "missing",
            "visual_classification": "missing",
            "visual_confidence": 0.95,
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_03900_missing.svg",
            "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_03900_missing.png",
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_03900_missing_profile.svg"
          },
          {
            "strut_id": 3986,
            "classification": "missing",
            "visual_classification": "missing",
            "visual_confidence": 0.95,
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_03986_missing.svg",
            "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_03986_missing.png",
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_03986_missing_profile.svg"
          },
          {
            "strut_id": 5806,
            "classification": "missing",
            "visual_classification": "missing",
            "visual_confidence": 0.95,
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_05806_missing.svg",
            "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_05806_missing.png",
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_05806_missing_profile.svg"
          },
          {
            "strut_id": 5833,
            "classification": "missing",
            "visual_classification": "missing",
            "visual_confidence": 0.95,
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_05833_missing.svg",
            "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_05833_missing.png",
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_05833_missing_profile.svg"
          },
          {
            "strut_id": 5916,
            "classification": "missing",
            "visual_classification": "missing",
            "visual_confidence": 0.95,
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_05916_missing.svg",
            "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_05916_missing.png",
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_05916_missing_profile.svg"
          },
          {
            "strut_id": 5972,
            "classification": "missing",
            "visual_classification": "missing",
            "visual_confidence": 0.95,
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_05972_missing.svg",
            "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_05972_missing.png",
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_05972_missing_profile.svg"
          },
          {
            "strut_id": 5974,
            "classification": "missing",
            "visual_classification": "missing",
            "visual_confidence": 0.95,
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_05974_missing.svg",
            "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_05974_missing.png",
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_05974_missing_profile.svg"
          },
          {
            "strut_id": 6032,
            "classification": "missing",
            "visual_classification": "missing",
            "visual_confidence": 0.95,
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_06032_missing.svg",
            "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_06032_missing.png",
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_06032_missing_profile.svg"
          },
          {
            "strut_id": 6034,
            "classification": "missing",
            "visual_classification": "missing",
            "visual_confidence": 0.95,
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_06034_missing.svg",
            "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_06034_missing.png",
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_06034_missing_profile.svg"
          },
          {
            "strut_id": 7849,
            "classification": "missing",
            "visual_classification": "missing",
            "visual_confidence": 0.95,
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_07849_missing.svg",
            "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_07849_missing.png",
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_07849_missing_profile.svg"
          },
          {
            "strut_id": 7851,
            "classification": "missing",
            "visual_classification": "missing",
            "visual_confidence": 0.95,
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_07851_missing.svg",
            "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_07851_missing.png",
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_07851_missing_profile.svg"
          },
          {
            "strut_id": 7877,
            "classification": "missing",
            "visual_classification": "missing",
            "visual_confidence": 0.95,
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_07877_missing.svg",
            "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_07877_missing.png",
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_07877_missing_profile.svg"
          },
          {
            "strut_id": 7878,
            "classification": "missing",
            "visual_classification": "missing",
            "visual_confidence": 0.95,
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_07878_missing.svg",
            "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_07878_missing.png",
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_07878_missing_profile.svg"
          },
          {
            "strut_id": 7904,
            "classification": "missing",
            "visual_classification": "missing",
            "visual_confidence": 0.95,
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_07904_missing.svg",
            "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_07904_missing.png",
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_07904_missing_profile.svg"
          },
          {
            "strut_id": 8016,
            "classification": "missing",
            "visual_classification": "missing",
            "visual_confidence": 0.95,
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_08016_missing.svg",
            "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_08016_missing.png",
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_08016_missing_profile.svg"
          },
          {
            "strut_id": 8048,
            "classification": "missing",
            "visual_classification": "missing",
            "visual_confidence": 0.95,
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_08048_missing.svg",
            "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_08048_missing.png",
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_08048_missing_profile.svg"
          },
          {
            "strut_id": 8050,
            "classification": "missing",
            "visual_classification": "missing",
            "visual_confidence": 0.95,
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_08050_missing.svg",
            "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_08050_missing.png",
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_08050_missing_profile.svg"
          },
          {
            "strut_id": 8051,
            "classification": "missing",
            "visual_classification": "missing",
            "visual_confidence": 0.95,
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_08051_missing.svg",
            "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_08051_missing.png",
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_08051_missing_profile.svg"
          },
          {
            "strut_id": 9836,
            "classification": "missing",
            "visual_classification": "missing",
            "visual_confidence": 0.95,
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_09836_missing.svg",
            "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_09836_missing.png",
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_09836_missing_profile.svg"
          },
          {
            "strut_id": 9864,
            "classification": "missing",
            "visual_classification": "missing",
            "visual_confidence": 0.95,
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_09864_missing.svg",
            "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_09864_missing.png",
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_09864_missing_profile.svg"
          },
          {
            "strut_id": 10034,
            "classification": "missing",
            "visual_classification": "missing",
            "visual_confidence": 0.95,
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_10034_missing.svg",
            "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_10034_missing.png",
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_10034_missing_profile.svg"
          },
          {
            "strut_id": 11854,
            "classification": "missing",
            "visual_classification": "missing",
            "visual_confidence": 0.95,
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_11854_missing.svg",
            "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_11854_missing.png",
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_11854_missing_profile.svg"
          },
          {
            "strut_id": 11882,
            "classification": "missing",
            "visual_classification": "missing",
            "visual_confidence": 0.95,
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_11882_missing.svg",
            "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_11882_missing.png",
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_11882_missing_profile.svg"
          },
          {
            "strut_id": 11883,
            "classification": "missing",
            "visual_classification": "missing",
            "visual_confidence": 0.95,
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_11883_missing.svg",
            "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_11883_missing.png",
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_11883_missing_profile.svg"
          },
          {
            "strut_id": 11909,
            "classification": "missing",
            "visual_classification": "missing",
            "visual_confidence": 0.95,
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_11909_missing.svg",
            "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_11909_missing.png",
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_11909_missing_profile.svg"
          },
          {
            "strut_id": 11910,
            "classification": "missing",
            "visual_classification": "missing",
            "visual_confidence": 0.95,
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_11910_missing.svg",
            "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_11910_missing.png",
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_11910_missing_profile.svg"
          },
          {
            "strut_id": 12020,
            "classification": "missing",
            "visual_classification": "missing",
            "visual_confidence": 0.95,
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_12020_missing.svg",
            "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_12020_missing.png",
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_12020_missing_profile.svg"
          },
          {
            "strut_id": 13868,
            "classification": "missing",
            "visual_classification": "missing",
            "visual_confidence": 0.95,
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_13868_missing.svg",
            "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_13868_missing.png",
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_13868_missing_profile.svg"
          },
          {
            "strut_id": 13869,
            "classification": "missing",
            "visual_classification": "missing",
            "visual_confidence": 0.95,
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_13869_missing.svg",
            "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_13869_missing.png",
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_13869_missing_profile.svg"
          },
          {
            "strut_id": 13870,
            "classification": "missing",
            "visual_classification": "missing",
            "visual_confidence": 0.95,
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_13870_missing.svg",
            "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_13870_missing.png",
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_13870_missing_profile.svg"
          },
          {
            "strut_id": 13896,
            "classification": "missing",
            "visual_classification": "missing",
            "visual_confidence": 0.95,
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_13896_missing.svg",
            "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_13896_missing.png",
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_13896_missing_profile.svg"
          },
          {
            "strut_id": 13899,
            "classification": "missing",
            "visual_classification": "missing",
            "visual_confidence": 0.95,
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_13899_missing.svg",
            "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_13899_missing.png",
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_13899_missing_profile.svg"
          },
          {
            "strut_id": 13924,
            "classification": "missing",
            "visual_classification": "missing",
            "visual_confidence": 0.95,
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_13924_missing.svg",
            "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_13924_missing.png",
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_13924_missing_profile.svg"
          },
          {
            "strut_id": 13925,
            "classification": "missing",
            "visual_classification": "missing",
            "visual_confidence": 0.95,
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_13925_missing.svg",
            "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_13925_missing.png",
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_13925_missing_profile.svg"
          },
          {
            "strut_id": 14008,
            "classification": "missing",
            "visual_classification": "missing",
            "visual_confidence": 0.95,
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_14008_missing.svg",
            "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_14008_missing.png",
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_14008_missing_profile.svg"
          },
          {
            "strut_id": 14037,
            "classification": "missing",
            "visual_classification": "missing",
            "visual_confidence": 0.95,
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_14037_missing.svg",
            "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_14037_missing.png",
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_14037_missing_profile.svg"
          },
          {
            "strut_id": 14038,
            "classification": "missing",
            "visual_classification": "missing",
            "visual_confidence": 0.95,
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_14038_missing.svg",
            "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_14038_missing.png",
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_14038_missing_profile.svg"
          },
          {
            "strut_id": 14096,
            "classification": "missing",
            "visual_classification": "missing",
            "visual_confidence": 0.95,
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_14096_missing.svg",
            "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_14096_missing.png",
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_14096_missing_profile.svg"
          },
          {
            "strut_id": 14098,
            "classification": "missing",
            "visual_classification": "missing",
            "visual_confidence": 0.95,
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_14098_missing.svg",
            "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_14098_missing.png",
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_14098_missing_profile.svg"
          },
          {
            "strut_id": 15940,
            "classification": "missing",
            "visual_classification": "missing",
            "visual_confidence": 0.95,
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_15940_missing.svg",
            "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_15940_missing.png",
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_15940_missing_profile.svg"
          },
          {
            "strut_id": 15941,
            "classification": "missing",
            "visual_classification": "missing",
            "visual_confidence": 0.95,
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_15941_missing.svg",
            "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_15941_missing.png",
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_15941_missing_profile.svg"
          },
          {
            "strut_id": 15942,
            "classification": "missing",
            "visual_classification": "missing",
            "visual_confidence": 0.95,
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_15942_missing.svg",
            "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_15942_missing.png",
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_15942_missing_profile.svg"
          },
          {
            "strut_id": 15943,
            "classification": "missing",
            "visual_classification": "missing",
            "visual_confidence": 0.95,
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_15943_missing.svg",
            "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_15943_missing.png",
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_15943_missing_profile.svg"
          },
          {
            "strut_id": 15970,
            "classification": "missing",
            "visual_classification": "missing",
            "visual_confidence": 0.95,
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_15970_missing.svg",
            "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_15970_missing.png",
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_15970_missing_profile.svg"
          },
          {
            "strut_id": 15971,
            "classification": "missing",
            "visual_classification": "missing",
            "visual_confidence": 0.95,
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_15971_missing.svg",
            "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_15971_missing.png",
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_15971_missing_profile.svg"
          },
          {
            "strut_id": 15996,
            "classification": "missing",
            "visual_classification": "missing",
            "visual_confidence": 0.95,
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_15996_missing.svg",
            "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_15996_missing.png",
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_15996_missing_profile.svg"
          },
          {
            "strut_id": 16024,
            "classification": "missing",
            "visual_classification": "missing",
            "visual_confidence": 0.95,
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_16024_missing.svg",
            "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_16024_missing.png",
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_16024_missing_profile.svg"
          },
          {
            "strut_id": 18193,
            "classification": "missing",
            "visual_classification": "missing",
            "visual_confidence": 0.95,
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_18193_missing.svg",
            "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_18193_missing.png",
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_18193_missing_profile.svg"
          },
          {
            "strut_id": 18194,
            "classification": "missing",
            "visual_classification": "missing",
            "visual_confidence": 0.95,
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_18194_missing.svg",
            "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_18194_missing.png",
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_18194_missing_profile.svg"
          },
          {
            "strut_id": 18195,
            "classification": "missing",
            "visual_classification": "missing",
            "visual_confidence": 0.95,
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_18195_missing.svg",
            "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_18195_missing.png",
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_18195_missing_profile.svg"
          },
          {
            "strut_id": 18226,
            "classification": "missing",
            "visual_classification": "missing",
            "visual_confidence": 0.95,
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_18226_missing.svg",
            "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_18226_missing.png",
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_18226_missing_profile.svg"
          },
          {
            "strut_id": 18227,
            "classification": "missing",
            "visual_classification": "missing",
            "visual_confidence": 0.95,
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_18227_missing.svg",
            "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_18227_missing.png",
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_18227_missing_profile.svg"
          },
          {
            "strut_id": 18257,
            "classification": "missing",
            "visual_classification": "missing",
            "visual_confidence": 0.95,
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_18257_missing.svg",
            "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_18257_missing.png",
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_18257_missing_profile.svg"
          },
          {
            "strut_id": 18289,
            "classification": "missing",
            "visual_classification": "missing",
            "visual_confidence": 0.95,
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_18289_missing.svg",
            "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_18289_missing.png",
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_18289_missing_profile.svg"
          },
          {
            "strut_id": 18290,
            "classification": "missing",
            "visual_classification": "missing",
            "visual_confidence": 0.95,
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_18290_missing.svg",
            "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_18290_missing.png",
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_18290_missing_profile.svg"
          },
          {
            "strut_id": 18322,
            "classification": "missing",
            "visual_classification": "missing",
            "visual_confidence": 0.95,
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_18322_missing.svg",
            "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_18322_missing.png",
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_18322_missing_profile.svg"
          },
          {
            "strut_id": 18323,
            "classification": "missing",
            "visual_classification": "missing",
            "visual_confidence": 0.95,
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_18323_missing.svg",
            "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_18323_missing.png",
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_18323_missing_profile.svg"
          },
          {
            "strut_id": 1800,
            "classification": "missing",
            "visual_classification": "missing",
            "visual_confidence": 0.85,
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_01800_missing.svg",
            "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_01800_missing.png",
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_01800_missing_profile.svg"
          },
          {
            "strut_id": 1940,
            "classification": "missing",
            "visual_classification": "missing",
            "visual_confidence": 0.85,
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_01940_missing.svg",
            "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_01940_missing.png",
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_01940_missing_profile.svg"
          },
          {
            "strut_id": 1969,
            "classification": "missing",
            "visual_classification": "missing",
            "visual_confidence": 0.85,
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_01969_missing.svg",
            "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_01969_missing.png",
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_01969_missing_profile.svg"
          },
          {
            "strut_id": 2001,
            "classification": "missing",
            "visual_classification": "missing",
            "visual_confidence": 0.85,
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_02001_missing.svg",
            "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_02001_missing.png",
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_02001_missing_profile.svg"
          },
          {
            "strut_id": 2002,
            "classification": "missing",
            "visual_classification": "missing",
            "visual_confidence": 0.85,
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_02002_missing.svg",
            "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_02002_missing.png",
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_02002_missing_profile.svg"
          },
          {
            "strut_id": 3818,
            "classification": "missing",
            "visual_classification": "missing",
            "visual_confidence": 0.85,
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_03818_missing.svg",
            "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_03818_missing.png",
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_03818_missing_profile.svg"
          },
          {
            "strut_id": 3847,
            "classification": "missing",
            "visual_classification": "missing",
            "visual_confidence": 0.85,
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_03847_missing.svg",
            "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_03847_missing.png",
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_03847_missing_profile.svg"
          },
          {
            "strut_id": 3958,
            "classification": "missing",
            "visual_classification": "missing",
            "visual_confidence": 0.85,
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_03958_missing.svg",
            "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_03958_missing.png",
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_03958_missing_profile.svg"
          },
          {
            "strut_id": 3984,
            "classification": "missing",
            "visual_classification": "missing",
            "visual_confidence": 0.85,
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_03984_missing.svg",
            "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_03984_missing.png",
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_03984_missing_profile.svg"
          },
          {
            "strut_id": 4016,
            "classification": "missing",
            "visual_classification": "missing",
            "visual_confidence": 0.85,
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_04016_missing.svg",
            "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_04016_missing.png",
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_04016_missing_profile.svg"
          },
          {
            "strut_id": 4018,
            "classification": "missing",
            "visual_classification": "missing",
            "visual_confidence": 0.85,
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_04018_missing.svg",
            "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_04018_missing.png",
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_04018_missing_profile.svg"
          },
          {
            "strut_id": 5807,
            "classification": "missing",
            "visual_classification": "missing",
            "visual_confidence": 0.85,
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_05807_missing.svg",
            "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_05807_missing.png",
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_05807_missing_profile.svg"
          },
          {
            "strut_id": 5832,
            "classification": "missing",
            "visual_classification": "missing",
            "visual_confidence": 0.85,
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_05832_missing.svg",
            "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_05832_missing.png",
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_05832_missing_profile.svg"
          },
          {
            "strut_id": 5834,
            "classification": "missing",
            "visual_classification": "missing",
            "visual_confidence": 0.85,
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_05834_missing.svg",
            "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_05834_missing.png",
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_05834_missing_profile.svg"
          },
          {
            "strut_id": 5918,
            "classification": "missing",
            "visual_classification": "missing",
            "visual_confidence": 0.85,
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_05918_missing.svg",
            "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_05918_missing.png",
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_05918_missing_profile.svg"
          },
          {
            "strut_id": 5944,
            "classification": "missing",
            "visual_classification": "missing",
            "visual_confidence": 0.85,
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_05944_missing.svg",
            "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_05944_missing.png",
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_05944_missing_profile.svg"
          },
          {
            "strut_id": 6000,
            "classification": "missing",
            "visual_classification": "missing",
            "visual_confidence": 0.85,
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_06000_missing.svg",
            "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_06000_missing.png",
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_06000_missing_profile.svg"
          },
          {
            "strut_id": 7820,
            "classification": "missing",
            "visual_classification": "missing",
            "visual_confidence": 0.85,
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_07820_missing.svg",
            "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_07820_missing.png",
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_07820_missing_profile.svg"
          },
          {
            "strut_id": 7821,
            "classification": "missing",
            "visual_classification": "missing",
            "visual_confidence": 0.85,
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_07821_missing.svg",
            "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_07821_missing.png",
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_07821_missing_profile.svg"
          },
          {
            "strut_id": 7848,
            "classification": "missing",
            "visual_classification": "missing",
            "visual_confidence": 0.85,
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_07848_missing.svg",
            "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_07848_missing.png",
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_07848_missing_profile.svg"
          },
          {
            "strut_id": 7876,
            "classification": "missing",
            "visual_classification": "missing",
            "visual_confidence": 0.85,
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_07876_missing.svg",
            "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_07876_missing.png",
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_07876_missing_profile.svg"
          },
          {
            "strut_id": 7934,
            "classification": "missing",
            "visual_classification": "missing",
            "visual_confidence": 0.85,
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_07934_missing.svg",
            "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_07934_missing.png",
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_07934_missing_profile.svg"
          },
          {
            "strut_id": 7962,
            "classification": "missing",
            "visual_classification": "missing",
            "visual_confidence": 0.85,
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_07962_missing.svg",
            "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_07962_missing.png",
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_07962_missing_profile.svg"
          },
          {
            "strut_id": 8018,
            "classification": "missing",
            "visual_classification": "missing",
            "visual_confidence": 0.85,
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_08018_missing.svg",
            "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_08018_missing.png",
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_08018_missing_profile.svg"
          },
          {
            "strut_id": 9867,
            "classification": "missing",
            "visual_classification": "missing",
            "visual_confidence": 0.85,
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_09867_missing.svg",
            "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_09867_missing.png",
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_09867_missing_profile.svg"
          },
          {
            "strut_id": 9921,
            "classification": "missing",
            "visual_classification": "missing",
            "visual_confidence": 0.85,
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_09921_missing.svg",
            "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_09921_missing.png",
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_09921_missing_profile.svg"
          },
          {
            "strut_id": 9923,
            "classification": "missing",
            "visual_classification": "missing",
            "visual_confidence": 0.85,
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_09923_missing.svg",
            "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_09923_missing.png",
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_09923_missing_profile.svg"
          },
          {
            "strut_id": 10006,
            "classification": "missing",
            "visual_classification": "missing",
            "visual_confidence": 0.85,
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_10006_missing.svg",
            "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_10006_missing.png",
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_10006_missing_profile.svg"
          },
          {
            "strut_id": 10032,
            "classification": "missing",
            "visual_classification": "missing",
            "visual_confidence": 0.85,
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_10032_missing.svg",
            "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_10032_missing.png",
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_10032_missing_profile.svg"
          },
          {
            "strut_id": 10064,
            "classification": "missing",
            "visual_classification": "missing",
            "visual_confidence": 0.85,
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_10064_missing.svg",
            "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_10064_missing.png",
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_10064_missing_profile.svg"
          },
          {
            "strut_id": 11855,
            "classification": "missing",
            "visual_classification": "missing",
            "visual_confidence": 0.85,
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_11855_missing.svg",
            "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_11855_missing.png",
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_11855_missing_profile.svg"
          },
          {
            "strut_id": 11936,
            "classification": "missing",
            "visual_classification": "missing",
            "visual_confidence": 0.85,
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_11936_missing.svg",
            "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_11936_missing.png",
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_11936_missing_profile.svg"
          },
          {
            "strut_id": 11938,
            "classification": "missing",
            "visual_classification": "missing",
            "visual_confidence": 0.85,
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_11938_missing.svg",
            "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_11938_missing.png",
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_11938_missing_profile.svg"
          },
          {
            "strut_id": 11964,
            "classification": "missing",
            "visual_classification": "missing",
            "visual_confidence": 0.85,
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_11964_missing.svg",
            "visual_evidence_png": "data/missing_struts/analysis/defect_visual_review/strut_11964_missing.png",
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_11964_missing_profile.svg"
          }
        ]
      }
    },
    {
      "title": "Hugging Face model review results",
      "source": "data/missing_struts/analysis/defect_visual_review/hf_model_review_results.json",
      "content": {
        "status": "skipped",
        "reason": "DEFECT_HF_REVIEW_LIMIT is 0",
        "model": "zai-org/GLM-4.5V",
        "requested_limit": 0,
        "reviews": []
      }
    },
    {
      "title": "Example per-strut classifications",
      "source": "data/missing_struts/analysis/per_strut_defects.json",
      "content": {
        "total_records": 18468,
        "first_10_anomalies": [
          {
            "strut_id": 0,
            "classification": "missing",
            "reason": "material profile is low across the expected strut",
            "coverage_ratio": 0.18181818181818182,
            "profile_classification": "missing",
            "profile_mean": 0.09,
            "profile_min": 0.0,
            "low_profile_segments": [
              0,
              1,
              2,
              3,
              4,
              5,
              6,
              7,
              8,
              9,
              10,
              11,
              12,
              13,
              14,
              15,
              16
            ],
            "longest_low_profile_gap": 17,
            "profile_plot": null,
            "visual_evidence_png": null
          },
          {
            "strut_id": 1,
            "classification": "disconnected",
            "reason": "endpoints have support but one or more middle segments drop below threshold",
            "coverage_ratio": 0.5454545454545454,
            "profile_classification": "broken",
            "profile_mean": 0.24,
            "profile_min": 0.0,
            "low_profile_segments": [
              4,
              5,
              6,
              7,
              8,
              9,
              10,
              11,
              12,
              13,
              14,
              15
            ],
            "longest_low_profile_gap": 12,
            "profile_plot": null,
            "visual_evidence_png": null
          },
          {
            "strut_id": 2,
            "classification": "disconnected",
            "reason": "endpoints have support but one or more middle segments drop below threshold",
            "coverage_ratio": 0.45454545454545453,
            "profile_classification": "broken",
            "profile_mean": 0.33562870818962093,
            "profile_min": 0.0,
            "low_profile_segments": [
              4,
              5,
              6,
              7,
              8,
              9,
              10,
              11,
              12,
              13,
              14
            ],
            "longest_low_profile_gap": 11,
            "profile_plot": null,
            "visual_evidence_png": null
          },
          {
            "strut_id": 3,
            "classification": "disconnected",
            "reason": "endpoints have support but one or more middle segments drop below threshold",
            "coverage_ratio": 0.45454545454545453,
            "profile_classification": "broken",
            "profile_mean": 0.26999999999999996,
            "profile_min": 0.0,
            "low_profile_segments": [
              4,
              5,
              6,
              7,
              8,
              9,
              10,
              11,
              12,
              13,
              14
            ],
            "longest_low_profile_gap": 11,
            "profile_plot": null,
            "visual_evidence_png": null
          },
          {
            "strut_id": 4,
            "classification": "disconnected",
            "reason": "endpoints have support but one or more middle segments drop below threshold",
            "coverage_ratio": 0.5454545454545454,
            "profile_classification": "broken",
            "profile_mean": 0.4016513716513142,
            "profile_min": 0.0,
            "low_profile_segments": [
              0,
              1,
              2,
              3,
              4,
              5,
              6,
              7,
              8,
              9
            ],
            "longest_low_profile_gap": 10,
            "profile_plot": null,
            "visual_evidence_png": null
          },
          {
            "strut_id": 5,
            "classification": "disconnected",
            "reason": "skeleton material is nearby, but no observed path connects both expected endpoints",
            "coverage_ratio": 1.0,
            "profile_classification": "continuous",
            "profile_mean": 0.7193620069153536,
            "profile_min": 0.6,
            "low_profile_segments": [],
            "longest_low_profile_gap": 0,
            "profile_plot": null,
            "visual_evidence_png": null
          },
          {
            "strut_id": 7,
            "classification": "disconnected",
            "reason": "skeleton material is nearby, but no observed path connects both expected endpoints",
            "coverage_ratio": 1.0,
            "profile_classification": "continuous",
            "profile_mean": 0.8609133599314905,
            "profile_min": 0.7,
            "low_profile_segments": [],
            "longest_low_profile_gap": 0,
            "profile_plot": null,
            "visual_evidence_png": null
          },
          {
            "strut_id": 8,
            "classification": "disconnected",
            "reason": "endpoints have support but one or more middle segments drop below threshold",
            "coverage_ratio": 0.7272727272727273,
            "profile_classification": "broken",
            "profile_mean": 0.6267982511152294,
            "profile_min": 0.0,
            "low_profile_segments": [
              0,
              1,
              2,
              3,
              4
            ],
            "longest_low_profile_gap": 5,
            "profile_plot": null,
            "visual_evidence_png": null
          },
          {
            "strut_id": 9,
            "classification": "disconnected",
            "reason": "skeleton material is nearby, but no observed path connects both expected endpoints",
            "coverage_ratio": 0.9090909090909091,
            "profile_classification": "weak",
            "profile_mean": 0.6932441050820582,
            "profile_min": 0.0,
            "low_profile_segments": [
              12
            ],
            "longest_low_profile_gap": 1,
            "profile_plot": null,
            "visual_evidence_png": null
          },
          {
            "strut_id": 10,
            "classification": "disconnected",
            "reason": "endpoints have support but one or more middle segments drop below threshold",
            "coverage_ratio": 0.5454545454545454,
            "profile_classification": "broken",
            "profile_mean": 0.43499999999999994,
            "profile_min": 0.0,
            "low_profile_segments": [
              5,
              6,
              7,
              8,
              9,
              10,
              11,
              12,
              13,
              14
            ],
            "longest_low_profile_gap": 10,
            "profile_plot": null,
            "visual_evidence_png": null
          }
        ]
      }
    },
    {
      "title": "Anomaly Markdown summary",
      "source": "data/missing_struts/analysis/anomaly_summary.md",
      "content": "# Defect Detection Summary\n\n- Expected struts: **18468**\n- Observed skeleton struts: **19824**\n- Present struts: **16258**\n- Weak struts: **0**\n- Missing struts: **314**\n- Disconnected struts: **1896**\n- Confirmed anomalies: **2210**\n- Confirmed anomaly percentage: **11.97%**\n- Profile segments per strut: **20**\n- Profile classification counts: `{'broken': 658, 'continuous': 17193, 'missing': 314, 'weak': 303}`\n- Visual review panels generated: **100**\n- Visual review index: `/home/mtrev008/Desktop/LLNL_DSC/llnl_data_science_challenge_2026/data/missing_struts/analysis/defect_visual_review/visual_review_index.json`\n- Hugging Face model reviews: **0**\n- Hugging Face model review results: `/home/mtrev008/Desktop/LLNL_DSC/llnl_data_science_challenge_2026/data/missing_struts/analysis/defect_visual_review/hf_model_review_results.json`\n\n## Decision Rules\n\n- Each expected strut is sampled at 11 evenly spaced points.\n- A sample is covered when an observed skeleton point is within 12 voxels.\n- `present`: coverage is at least 65% and the same observed skeleton path reaches both endpoints.\n- `missing`: coverage is 10% or less.\n- `disconnected`: coverage is at least 25%, but no observed path connects both endpoints.\n- `weak`: partial coverage remains below the present threshold.\n\n## Node-to-Node Material Profile\n\n- Each expected JSON edge is divided into 20 equal segments from node x to node y.\n- Each segment receives a support value from nearby observed skeleton evidence within 12 voxels.\n- Segment values below 0.20 are low-support regions.\n- `missing`: the profile is low across the expected strut.\n- `disconnected`: endpoints have support, but a middle low-support gap appears.\n- `weak`: the profile has partial support or isolated low-support segments.\n- `continuous`: the profile is supported along the expected edge.\n\n## Visual Review Layer\n\n- Candidate anomalies are rendered as SVG panels with two projections: XY and XZ.\n- Red/orange/purple lines show the expected strut; blue points show nearby observed skeleton evidence.\n- The visual label is derived from the same panel evidence and stored per strut.\n- When `HUGGINGFACE_API_KEY` is set and `DEFECT_HF_REVIEW_LIMIT` is greater than 0, candidate panels are sent to the configured Hugging Face vision-language model."
    }
  ],
  "metrics": {
    "return_code": 0
  },
  "issues": []
}
```

## Step 5: Visualization

- Subagent: `.codex/agents/visualization`
- Status: `passed`
- Command: `/home/mtrev008/miniconda3/bin/python -B .codex/agents/visualization/run.py`
- Return code: `0`

### Result Artifacts

- `data/missing_struts/analysis/raw_slice_380.png` - present, 455519 bytes
- `data/missing_struts/analysis/segmentation_view_a.png` - present, 2144540 bytes
- `data/missing_struts/analysis/segmentation_view_b.png` - present, 1997104 bytes

### Result Content

#### Raw slice visualization

Source: `data/missing_struts/analysis/raw_slice_380.png`

```json
{
  "path": "data/missing_struts/analysis/raw_slice_380.png",
  "width": 837,
  "height": 815,
  "format": "PNG"
}
```

#### Segmentation view A

Source: `data/missing_struts/analysis/segmentation_view_a.png`

```json
{
  "path": "data/missing_struts/analysis/segmentation_view_a.png",
  "width": 1482,
  "height": 1482,
  "format": "PNG"
}
```

#### Segmentation view B

Source: `data/missing_struts/analysis/segmentation_view_b.png`

```json
{
  "path": "data/missing_struts/analysis/segmentation_view_b.png",
  "width": 1482,
  "height": 1482,
  "format": "PNG"
}
```


### Summary Card

```json
{
  "step": "Visualization",
  "subagent": ".codex/agents/visualization",
  "status": "passed",
  "command": "/home/mtrev008/miniconda3/bin/python -B .codex/agents/visualization/run.py",
  "stdout": "Visualization pipeline step",
  "stderr": "",
  "outputs": [
    {
      "path": "data/missing_struts/analysis/raw_slice_380.png",
      "exists": true,
      "size_bytes": 455519
    },
    {
      "path": "data/missing_struts/analysis/segmentation_view_a.png",
      "exists": true,
      "size_bytes": 2144540
    },
    {
      "path": "data/missing_struts/analysis/segmentation_view_b.png",
      "exists": true,
      "size_bytes": 1997104
    }
  ],
  "results": [
    {
      "title": "Raw slice visualization",
      "source": "data/missing_struts/analysis/raw_slice_380.png",
      "content": {
        "path": "data/missing_struts/analysis/raw_slice_380.png",
        "width": 837,
        "height": 815,
        "format": "PNG"
      }
    },
    {
      "title": "Segmentation view A",
      "source": "data/missing_struts/analysis/segmentation_view_a.png",
      "content": {
        "path": "data/missing_struts/analysis/segmentation_view_a.png",
        "width": 1482,
        "height": 1482,
        "format": "PNG"
      }
    },
    {
      "title": "Segmentation view B",
      "source": "data/missing_struts/analysis/segmentation_view_b.png",
      "content": {
        "path": "data/missing_struts/analysis/segmentation_view_b.png",
        "width": 1482,
        "height": 1482,
        "format": "PNG"
      }
    }
  ],
  "metrics": {
    "return_code": 0
  },
  "issues": []
}
```
