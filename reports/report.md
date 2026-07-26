# LLNL CT Pipeline Manager Report

Passed steps: 5/5

## Step 1: Data Analyzer

- Subagent: `.codex/agents/data_analyzer`
- Status: `passed`
- Command: `/home/mtrev008/miniconda3/envs/dssi_env/bin/python -B .codex/agents/data_analyzer/run.py`
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
  "command": "/home/mtrev008/miniconda3/envs/dssi_env/bin/python -B .codex/agents/data_analyzer/run.py",
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
- Command: `/home/mtrev008/miniconda3/envs/dssi_env/bin/python -B .codex/agents/segmentation/run.py`
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
  "command": "/home/mtrev008/miniconda3/envs/dssi_env/bin/python -B .codex/agents/segmentation/run.py",
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
- Command: `/home/mtrev008/miniconda3/envs/dssi_env/bin/python -B .codex/agents/skeletonization/run.py`
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
  "command": "/home/mtrev008/miniconda3/envs/dssi_env/bin/python -B .codex/agents/skeletonization/run.py",
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
- Command: `/home/mtrev008/miniconda3/envs/dssi_env/bin/python -B .codex/agents/defect_detection/run.py`
- Return code: `0`

### Result Artifacts

- `data/missing_struts/analysis/observed_lattice.json` - present, 204 bytes
- `data/missing_struts/analysis/cluster_summary.json` - present, 4190 bytes
- `data/missing_struts/analysis/cluster_labels.json` - present, 1692 bytes
- `data/missing_struts/analysis/per_strut_defects.json` - present, 38612515 bytes
- `data/missing_struts/analysis/anomaly_summary.json` - present, 3045 bytes
- `data/missing_struts/analysis/anomaly_summary.md` - present, 1414 bytes
- `data/missing_struts/analysis/defect_visual_review/visual_review_index.json` - present, 52283 bytes
- `data/missing_struts/analysis/defect_visual_review/hf_model_review_results.json` - present, 154 bytes

### Result Content

#### Anomaly summary

Source: `data/missing_struts/analysis/anomaly_summary.json`

```json
{
  "reference_json": "/home/mtrev008/Desktop/LLNL_DSC/llnl_data_science_challenge_2026/data/missing_struts/registered_jsons/210127_Brian_Tran_strut_lattices_0point5dash1 1 Slices.json",
  "tif_stack": "/home/mtrev008/Desktop/LLNL_DSC/llnl_data_science_challenge_2026/data/missing_struts/tif_stacks/210127_Brian_Tran_strut_lattices_0point5dash1 1 Slices.tif",
  "per_strut_json": "/home/mtrev008/Desktop/LLNL_DSC/llnl_data_science_challenge_2026/data/missing_struts/analysis/per_strut_defects.json",
  "summary": "/home/mtrev008/Desktop/LLNL_DSC/llnl_data_science_challenge_2026/data/missing_struts/analysis/anomaly_summary.md",
  "method": "unsupervised raw-CT strut embedding clustering with local labeller subagent",
  "defect_definition": "A defective strut is an expected registered-JSON strut assigned to a cluster that the local labeller subagent labels as weak. Weak struts are then subtyped as missing, broken, thin, or uncertain_weak from raw CT support-profile evidence.",
  "expected_struts": 18468,
  "observed_struts": null,
  "selected_cluster_count": 2,
  "silhouette_score": 0.39542695353317475,
  "cluster_metrics": {
    "algorithm": "kmeans",
    "selected_cluster_count": 2,
    "silhouette_score": 0.39542695353317475,
    "silhouette_by_k": {
      "2": 0.39542695353317475,
      "3": 0.3761038174745983,
      "4": 0.33201155744931216,
      "5": 0.32572292322108815
    },
    "cluster_stability": {
      "mean_silhouette_across_seeds": 0.39542695353317475,
      "min_silhouette_across_seeds": 0.39542695353317475,
      "max_silhouette_across_seeds": 0.39542695353317475
    }
  },
  "cluster_summary_json": "/home/mtrev008/Desktop/LLNL_DSC/llnl_data_science_challenge_2026/data/missing_struts/analysis/cluster_summary.json",
  "cluster_labels_json": "/home/mtrev008/Desktop/LLNL_DSC/llnl_data_science_challenge_2026/data/missing_struts/analysis/cluster_labels.json",
  "classification_counts": {
    "present": 12619,
    "weak": 5849
  },
  "weak_subtype_counts": {
    "broken": 328,
    "missing": 640,
    "thin": 4770,
    "uncertain_weak": 111
  },
  "confirmed_weak_subtypes": [
    "missing",
    "broken",
    "thin",
    "uncertain_weak"
  ],
  "graph_candidates": 968,
  "weak_segmentation_candidates": 5849,
  "confirmed_anomalies": 5849,
  "confirmed_anomaly_percentage": 31.670998483863983,
  "nominal_rate_comparison": "detected 31.67% vs nominal 0.5-1.0%",
  "sample_count": 21,
  "patch_radius_voxels": 3,
  "profile_segments": 21,
  "visual_review_dir": "/home/mtrev008/Desktop/LLNL_DSC/llnl_data_science_challenge_2026/data/missing_struts/analysis/defect_visual_review",
  "visual_review_index": "/home/mtrev008/Desktop/LLNL_DSC/llnl_data_science_challenge_2026/data/missing_struts/analysis/defect_visual_review/visual_review_index.json",
  "visual_review_panels": 100,
  "hf_model_review_results": "/home/mtrev008/Desktop/LLNL_DSC/llnl_data_science_challenge_2026/data/missing_struts/analysis/defect_visual_review/hf_model_review_results.json",
  "hf_model_review_count": 0,
  "hf_model": null
}
```

#### Cluster summary

Source: `data/missing_struts/analysis/cluster_summary.json`

```json
{
  "method": "unsupervised raw-CT strut embedding clustering",
  "defect_definition": "A defective strut is an expected registered-JSON strut assigned to a cluster that the local labeller subagent labels as weak. Weak struts are then subtyped as missing, broken, thin, or uncertain_weak from raw CT support-profile evidence.",
  "cluster_metrics": {
    "algorithm": "kmeans",
    "selected_cluster_count": 2,
    "silhouette_score": 0.39542695353317475,
    "silhouette_by_k": {
      "2": 0.39542695353317475,
      "3": 0.3761038174745983,
      "4": 0.33201155744931216,
      "5": 0.32572292322108815
    },
    "cluster_stability": {
      "mean_silhouette_across_seeds": 0.39542695353317475,
      "min_silhouette_across_seeds": 0.39542695353317475,
      "max_silhouette_across_seeds": 0.39542695353317475
    }
  },
  "clusters": [
    {
      "cluster_id": 0,
      "strut_count": 12619,
      "mean_defect_score": 0.35683784000332486,
      "mean_profile_mean": 0.46494614020165914,
      "mean_profile_min": 0.31401196463376446,
      "mean_longest_low_gap": 0.060464379110864566,
      "mean_continuity_score": 0.9971207438518637,
      "representative_strut_ids": [
        2931,
        4976,
        2517,
        12578,
        9450,
        12352,
        8976,
        15894
      ],
      "representative_profiles": [
        [
          0.79089,
          0.6343,
          0.42599,
          0.23119,
          0.11061,
          0.07386,
          0.08815,
          0.12804,
          0.18207,
          0.24216,
          0.29591,
          0.34023,
          0.38509,
          0.43862,
          0.46773,
          0.48072,
          0.55202,
          0.71748,
          0.86301,
          0.90028,
          0.81819
        ],
        [
          0.79571,
          0.63652,
          0.46247,
          0.2952,
          0.15179,
          0.08636,
          0.08774,
          0.11527,
          0.16133,
          0.21469,
          0.27246,
          0.32696,
          0.37045,
          0.4088,
          0.432,
          0.42997,
          0.48359,
          0.59466,
          0.75398,
          0.84785,
          0.81651
        ],
        [
          0.83514,
          0.70999,
          0.51449,
          0.3349,
          0.20106,
          0.1303,
          0.14948,
          0.22753,
          0.31439,
          0.36407,
          0.37757,
          0.38512,
          0.37604,
          0.36369,
          0.36065,
          0.36842,
          0.39847,
          0.50016,
          0.67701,
          0.84153,
          0.82737
        ]
      ]
    },
    {
      "cluster_id": 1,
      "strut_count": 5849,
      "mean_defect_score": 0.5101256956660095,
      "mean_profile_mean": 0.2611625024330019,
      "mean_profile_min": 0.1163423698092687,
      "mean_longest_low_gap": 2.92272183279193,
      "mean_continuity_score": 0.8608227698670511,
      "representative_strut_ids": [
        18447,
        18159,
        18455,
        18454,
        17903,
        18419,
        14096,
        17647
      ],
      "representative_profiles": [
        [
          0.0,
          0.0,
          0.0,
          0.0,
          0.0,
          0.0,
          0.0,
          0.0,
          0.0,
          0.0,
          0.0,
          0.0,
          0.0,
          0.0,
          0.0,
          0.0,
          0.0,
          0.0,
          0.0,
          0.0,
          0.0201
        ],
        [
          0.0,
          0.0,
          0.0,
          0.0,
          0.0,
          0.0,
          0.0,
          0.0,
          0.0,
          0.0,
          0.0,
          0.0,
          0.0,
          0.00702,
          0.01709,
          0.02761,
          0.03362,
          0.02663,
          0.00191,
          0.0,
          0.01206
        ],
        [
          0.0,
          0.0,
          0.0,
          0.0,
          0.0,
          0.0,
          0.0,
          0.0,
          0.0,
          0.0,
          0.0,
          0.00437,
          0.01338,
          0.02032,
          0.02499,
          0.02761,
          0.02955,
          0.03019,
          0.0325,
          0.03019,
          0.02352
        ]
      ]
    }
  ]
}
```

#### Cluster labels

Source: `data/missing_struts/analysis/cluster_labels.json`

```json
{
  "status": "passed",
  "labeller": "local defect_labeler subagent",
  "api_used": false,
  "source": "/home/mtrev008/Desktop/LLNL_DSC/llnl_data_science_challenge_2026/data/missing_struts/analysis/cluster_summary.json",
  "cluster_labels": [
    {
      "cluster_id": 0,
      "label": "present",
      "confidence": 0.9,
      "reason": "cluster has the lowest defect score and the most continuous raw CT support profile",
      "evidence": {
        "strut_count": 12619,
        "mean_defect_score": 0.35683784000332486,
        "mean_profile_mean": 0.46494614020165914,
        "mean_profile_min": 0.31401196463376446,
        "mean_longest_low_gap": 0.060464379110864566,
        "mean_continuity_score": 0.9971207438518637,
        "relative_defect_score": 0.0,
        "representative_strut_ids": [
          2931,
          4976,
          2517,
          12578,
          9450,
          12352,
          8976,
          15894
        ]
      }
    },
    {
      "cluster_id": 1,
      "label": "weak",
      "confidence": 0.8,
      "reason": "cluster has materially reduced raw CT support relative to the present baseline",
      "evidence": {
        "strut_count": 5849,
        "mean_defect_score": 0.5101256956660095,
        "mean_profile_mean": 0.2611625024330019,
        "mean_profile_min": 0.1163423698092687,
        "mean_longest_low_gap": 2.92272183279193,
        "mean_continuity_score": 0.8608227698670511,
        "relative_defect_score": 0.15328785566268466,
        "representative_strut_ids": [
          18447,
          18159,
          18455,
          18454,
          17903,
          18419,
          14096,
          17647
        ]
      }
    }
  ]
}
```

#### Visual review index

Source: `data/missing_struts/analysis/defect_visual_review/visual_review_index.json`

```json
{
  "visual_panel_count": 100,
  "max_visual_panels": 100,
  "panel_type": "raw CT strut support profile",
  "panels": [
    {
      "strut_id": 18447,
      "cluster_id": 1,
      "classification": "weak",
      "weak_subtype": "missing",
      "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
      "defect_score": 0.8999999999883583,
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_18447_weak_missing_profile.svg",
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_18447_weak_missing_profile.svg",
      "visual_evidence_png": null
    },
    {
      "strut_id": 18159,
      "cluster_id": 1,
      "classification": "weak",
      "weak_subtype": "missing",
      "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
      "defect_score": 0.8979011126561091,
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_18159_weak_missing_profile.svg",
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_18159_weak_missing_profile.svg",
      "visual_evidence_png": null
    },
    {
      "strut_id": 18455,
      "cluster_id": 1,
      "classification": "weak",
      "weak_subtype": "missing",
      "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
      "defect_score": 0.8964905747212469,
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_18455_weak_missing_profile.svg",
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_18455_weak_missing_profile.svg",
      "visual_evidence_png": null
    },
    {
      "strut_id": 18454,
      "cluster_id": 1,
      "classification": "weak",
      "weak_subtype": "missing",
      "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
      "defect_score": 0.8918822124600411,
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_18454_weak_missing_profile.svg",
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_18454_weak_missing_profile.svg",
      "visual_evidence_png": null
    },
    {
      "strut_id": 17903,
      "cluster_id": 1,
      "classification": "weak",
      "weak_subtype": "missing",
      "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
      "defect_score": 0.8916213570162653,
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_17903_weak_missing_profile.svg",
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_17903_weak_missing_profile.svg",
      "visual_evidence_png": null
    },
    {
      "strut_id": 18419,
      "cluster_id": 1,
      "classification": "weak",
      "weak_subtype": "missing",
      "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
      "defect_score": 0.8880076033994556,
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_18419_weak_missing_profile.svg",
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_18419_weak_missing_profile.svg",
      "visual_evidence_png": null
    },
    {
      "strut_id": 14096,
      "cluster_id": 1,
      "classification": "weak",
      "weak_subtype": "missing",
      "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
      "defect_score": 0.8876162857748567,
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_14096_weak_missing_profile.svg",
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_14096_weak_missing_profile.svg",
      "visual_evidence_png": null
    },
    {
      "strut_id": 17647,
      "cluster_id": 1,
      "classification": "weak",
      "weak_subtype": "missing",
      "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
      "defect_score": 0.8875145373865961,
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_17647_weak_missing_profile.svg",
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_17647_weak_missing_profile.svg",
      "visual_evidence_png": null
    },
    {
      "strut_id": 18158,
      "cluster_id": 1,
      "classification": "weak",
      "weak_subtype": "missing",
      "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
      "defect_score": 0.8874007098376752,
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_18158_weak_missing_profile.svg",
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_18158_weak_missing_profile.svg",
      "visual_evidence_png": null
    },
    {
      "strut_id": 12080,
      "cluster_id": 1,
      "classification": "weak",
      "weak_subtype": "missing",
      "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
      "defect_score": 0.8871592039242387,
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_12080_weak_missing_profile.svg",
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_12080_weak_missing_profile.svg",
      "visual_evidence_png": null
    },
    {
      "strut_id": 11853,
      "cluster_id": 1,
      "classification": "weak",
      "weak_subtype": "missing",
      "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
      "defect_score": 0.8869494989514352,
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_11853_weak_missing_profile.svg",
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_11853_weak_missing_profile.svg",
      "visual_evidence_png": null
    },
    {
      "strut_id": 12082,
      "cluster_id": 1,
      "classification": "weak",
      "weak_subtype": "missing",
      "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
      "defect_score": 0.8867978440597654,
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_12082_weak_missing_profile.svg",
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_12082_weak_missing_profile.svg",
      "visual_evidence_png": null
    },
    {
      "strut_id": 10064,
      "cluster_id": 1,
      "classification": "weak",
      "weak_subtype": "missing",
      "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
      "defect_score": 0.8867608441971243,
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_10064_weak_missing_profile.svg",
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_10064_weak_missing_profile.svg",
      "visual_evidence_png": null
    },
    {
      "strut_id": 11855,
      "cluster_id": 1,
      "classification": "weak",
      "weak_subtype": "missing",
      "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
      "defect_score": 0.8865815794095396,
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_11855_weak_missing_profile.svg",
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_11855_weak_missing_profile.svg",
      "visual_evidence_png": null
    },
    {
      "strut_id": 13897,
      "cluster_id": 1,
      "classification": "weak",
      "weak_subtype": "missing",
      "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
      "defect_score": 0.8865569587796925,
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_13897_weak_missing_profile.svg",
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_13897_weak_missing_profile.svg",
      "visual_evidence_png": null
    },
    {
      "strut_id": 13899,
      "cluster_id": 1,
      "classification": "weak",
      "weak_subtype": "missing",
      "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
      "defect_score": 0.8863253608345986,
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_13899_weak_missing_profile.svg",
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_13899_weak_missing_profile.svg",
      "visual_evidence_png": null
    },
    {
      "strut_id": 13926,
      "cluster_id": 1,
      "classification": "weak",
      "weak_subtype": "missing",
      "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
      "defect_score": 0.8863180097192526,
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_13926_weak_missing_profile.svg",
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_13926_weak_missing_profile.svg",
      "visual_evidence_png": null
    },
    {
      "strut_id": 11966,
      "cluster_id": 1,
      "classification": "weak",
      "weak_subtype": "missing",
      "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
      "defect_score": 0.8862778028473258,
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_11966_weak_missing_profile.svg",
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_11966_weak_missing_profile.svg",
      "visual_evidence_png": null
    },
    {
      "strut_id": 18452,
      "cluster_id": 1,
      "classification": "weak",
      "weak_subtype": "missing",
      "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
      "defect_score": 0.8862575335428119,
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_18452_weak_missing_profile.svg",
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_18452_weak_missing_profile.svg",
      "visual_evidence_png": null
    },
    {
      "strut_id": 14098,
      "cluster_id": 1,
      "classification": "weak",
      "weak_subtype": "missing",
      "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
      "defect_score": 0.8861972730606794,
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_14098_weak_missing_profile.svg",
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_14098_weak_missing_profile.svg",
      "visual_evidence_png": null
    },
    {
      "strut_id": 12022,
      "cluster_id": 1,
      "classification": "weak",
      "weak_subtype": "missing",
      "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
      "defect_score": 0.8861877614632249,
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_12022_weak_missing_profile.svg",
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_12022_weak_missing_profile.svg",
      "visual_evidence_png": null
    },
    {
      "strut_id": 11938,
      "cluster_id": 1,
      "classification": "weak",
      "weak_subtype": "missing",
      "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
      "defect_score": 0.886146206408739,
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_11938_weak_missing_profile.svg",
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_11938_weak_missing_profile.svg",
      "visual_evidence_png": null
    },
    {
      "strut_id": 11911,
      "cluster_id": 1,
      "classification": "weak",
      "weak_subtype": "missing",
      "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
      "defect_score": 0.886127202771604,
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_11911_weak_missing_profile.svg",
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_11911_weak_missing_profile.svg",
      "visual_evidence_png": null
    },
    {
      "strut_id": 13868,
      "cluster_id": 1,
      "classification": "weak",
      "weak_subtype": "missing",
      "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
      "defect_score": 0.8861207552254199,
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_13868_weak_missing_profile.svg",
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_13868_weak_missing_profile.svg",
      "visual_evidence_png": null
    },
    {
      "strut_id": 9920,
      "cluster_id": 1,
      "classification": "weak",
      "weak_subtype": "missing",
      "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
      "defect_score": 0.8861132320016621,
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_09920_weak_missing_profile.svg",
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_09920_weak_missing_profile.svg",
      "visual_evidence_png": null
    },
    {
      "strut_id": 13869,
      "cluster_id": 1,
      "classification": "weak",
      "weak_subtype": "missing",
      "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
      "defect_score": 0.8861001504585148,
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_13869_weak_missing_profile.svg",
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_13869_weak_missing_profile.svg",
      "visual_evidence_png": null
    },
    {
      "strut_id": 12020,
      "cluster_id": 1,
      "classification": "weak",
      "weak_subtype": "missing",
      "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
      "defect_score": 0.8860869841650129,
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_12020_weak_missing_profile.svg",
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_12020_weak_missing_profile.svg",
      "visual_evidence_png": null
    },
    {
      "strut_id": 9922,
      "cluster_id": 1,
      "classification": "weak",
      "weak_subtype": "missing",
      "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
      "defect_score": 0.8860708085820078,
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_09922_weak_missing_profile.svg",
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_09922_weak_missing_profile.svg",
      "visual_evidence_png": null
    },
    {
      "strut_id": 14066,
      "cluster_id": 1,
      "classification": "weak",
      "weak_subtype": "missing",
      "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
      "defect_score": 0.886055041104555,
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_14066_weak_missing_profile.svg",
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_14066_weak_missing_profile.svg",
      "visual_evidence_png": null
    },
    {
      "strut_id": 14038,
      "cluster_id": 1,
      "classification": "weak",
      "weak_subtype": "missing",
      "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
      "defect_score": 0.8860440013930201,
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_14038_weak_missing_profile.svg",
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_14038_weak_missing_profile.svg",
      "visual_evidence_png": null
    },
    {
      "strut_id": 9867,
      "cluster_id": 1,
      "classification": "weak",
      "weak_subtype": "missing",
      "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
      "defect_score": 0.8860383335500955,
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_09867_weak_missing_profile.svg",
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_09867_weak_missing_profile.svg",
      "visual_evidence_png": null
    },
    {
      "strut_id": 13982,
      "cluster_id": 1,
      "classification": "weak",
      "weak_subtype": "missing",
      "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
      "defect_score": 0.8860292300581932,
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_13982_weak_missing_profile.svg",
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_13982_weak_missing_profile.svg",
      "visual_evidence_png": null
    },
    {
      "strut_id": 12050,
      "cluster_id": 1,
      "classification": "weak",
      "weak_subtype": "missing",
      "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
      "defect_score": 0.8860083384439349,
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_12050_weak_missing_profile.svg",
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_12050_weak_missing_profile.svg",
      "visual_evidence_png": null
    },
    {
      "strut_id": 11908,
      "cluster_id": 1,
      "classification": "weak",
      "weak_subtype": "missing",
      "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
      "defect_score": 0.885991450957954,
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_11908_weak_missing_profile.svg",
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_11908_weak_missing_profile.svg",
      "visual_evidence_png": null
    },
    {
      "strut_id": 11994,
      "cluster_id": 1,
      "classification": "weak",
      "weak_subtype": "missing",
      "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
      "defect_score": 0.8859870556741952,
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_11994_weak_missing_profile.svg",
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_11994_weak_missing_profile.svg",
      "visual_evidence_png": null
    },
    {
      "strut_id": 9978,
      "cluster_id": 1,
      "classification": "weak",
      "weak_subtype": "missing",
      "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
      "defect_score": 0.8859859786927701,
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_09978_weak_missing_profile.svg",
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_09978_weak_missing_profile.svg",
      "visual_evidence_png": null
    },
    {
      "strut_id": 13954,
      "cluster_id": 1,
      "classification": "weak",
      "weak_subtype": "missing",
      "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
      "defect_score": 0.8859719075262545,
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_13954_weak_missing_profile.svg",
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_13954_weak_missing_profile.svg",
      "visual_evidence_png": null
    },
    {
      "strut_id": 13871,
      "cluster_id": 1,
      "classification": "weak",
      "weak_subtype": "missing",
      "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
      "defect_score": 0.8859582901000976,
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_13871_weak_missing_profile.svg",
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_13871_weak_missing_profile.svg",
      "visual_evidence_png": null
    },
    {
      "strut_id": 13927,
      "cluster_id": 1,
      "classification": "weak",
      "weak_subtype": "missing",
      "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
      "defect_score": 0.8859491292387246,
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_13927_weak_missing_profile.svg",
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_13927_weak_missing_profile.svg",
      "visual_evidence_png": null
    },
    {
      "strut_id": 16112,
      "cluster_id": 1,
      "classification": "weak",
      "weak_subtype": "missing",
      "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
      "defect_score": 0.8859123645350336,
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_16112_weak_missing_profile.svg",
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_16112_weak_missing_profile.svg",
      "visual_evidence_png": null
    },
    {
      "strut_id": 9894,
      "cluster_id": 1,
      "classification": "weak",
      "weak_subtype": "missing",
      "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
      "defect_score": 0.8858940036967397,
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_09894_weak_missing_profile.svg",
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_09894_weak_missing_profile.svg",
      "visual_evidence_png": null
    },
    {
      "strut_id": 14010,
      "cluster_id": 1,
      "classification": "weak",
      "weak_subtype": "missing",
      "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
      "defect_score": 0.8858816796913743,
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_14010_weak_missing_profile.svg",
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_14010_weak_missing_profile.svg",
      "visual_evidence_png": null
    },
    {
      "strut_id": 9950,
      "cluster_id": 1,
      "classification": "weak",
      "weak_subtype": "missing",
      "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
      "defect_score": 0.8858671704307198,
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_09950_weak_missing_profile.svg",
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_09950_weak_missing_profile.svg",
      "visual_evidence_png": null
    },
    {
      "strut_id": 13898,
      "cluster_id": 1,
      "classification": "weak",
      "weak_subtype": "missing",
      "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
      "defect_score": 0.885835175216198,
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_13898_weak_missing_profile.svg",
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_13898_weak_missing_profile.svg",
      "visual_evidence_png": null
    },
    {
      "strut_id": 13924,
      "cluster_id": 1,
      "classification": "weak",
      "weak_subtype": "missing",
      "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
      "defect_score": 0.8858232906088234,
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_13924_weak_missing_profile.svg",
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_13924_weak_missing_profile.svg",
      "visual_evidence_png": null
    },
    {
      "strut_id": 7851,
      "cluster_id": 1,
      "classification": "weak",
      "weak_subtype": "missing",
      "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
      "defect_score": 0.8857996817678212,
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_07851_weak_missing_profile.svg",
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_07851_weak_missing_profile.svg",
      "visual_evidence_png": null
    },
    {
      "strut_id": 14064,
      "cluster_id": 1,
      "classification": "weak",
      "weak_subtype": "missing",
      "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
      "defect_score": 0.8857985474169253,
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_14064_weak_missing_profile.svg",
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_14064_weak_missing_profile.svg",
      "visual_evidence_png": null
    },
    {
      "strut_id": 11964,
      "cluster_id": 1,
      "classification": "weak",
      "weak_subtype": "missing",
      "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
      "defect_score": 0.8857393942773343,
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_11964_weak_missing_profile.svg",
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_11964_weak_missing_profile.svg",
      "visual_evidence_png": null
    },
    {
      "strut_id": 11936,
      "cluster_id": 1,
      "classification": "weak",
      "weak_subtype": "missing",
      "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
      "defect_score": 0.8857365231961011,
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_11936_weak_missing_profile.svg",
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_11936_weak_missing_profile.svg",
      "visual_evidence_png": null
    },
    {
      "strut_id": 9837,
      "cluster_id": 1,
      "classification": "weak",
      "weak_subtype": "missing",
      "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
      "defect_score": 0.8857219302444718,
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_09837_weak_missing_profile.svg",
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_09837_weak_missing_profile.svg",
      "visual_evidence_png": null
    },
    {
      "strut_id": 14008,
      "cluster_id": 1,
      "classification": "weak",
      "weak_subtype": "missing",
      "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
      "defect_score": 0.8856946643441915,
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_14008_weak_missing_profile.svg",
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_14008_weak_missing_profile.svg",
      "visual_evidence_png": null
    },
    {
      "strut_id": 15913,
      "cluster_id": 1,
      "classification": "weak",
      "weak_subtype": "missing",
      "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
      "defect_score": 0.8856827719137071,
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_15913_weak_missing_profile.svg",
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_15913_weak_missing_profile.svg",
      "visual_evidence_png": null
    },
    {
      "strut_id": 15941,
      "cluster_id": 1,
      "classification": "weak",
      "weak_subtype": "missing",
      "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
      "defect_score": 0.8856752838939429,
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_15941_weak_missing_profile.svg",
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_15941_weak_missing_profile.svg",
      "visual_evidence_png": null
    },
    {
      "strut_id": 11880,
      "cluster_id": 1,
      "classification": "weak",
      "weak_subtype": "missing",
      "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
      "defect_score": 0.8856340704485773,
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_11880_weak_missing_profile.svg",
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_11880_weak_missing_profile.svg",
      "visual_evidence_png": null
    },
    {
      "strut_id": 9864,
      "cluster_id": 1,
      "classification": "weak",
      "weak_subtype": "missing",
      "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
      "defect_score": 0.8856230881065129,
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_09864_weak_missing_profile.svg",
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_09864_weak_missing_profile.svg",
      "visual_evidence_png": null
    },
    {
      "strut_id": 9892,
      "cluster_id": 1,
      "classification": "weak",
      "weak_subtype": "missing",
      "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
      "defect_score": 0.8856178674846887,
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_09892_weak_missing_profile.svg",
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_09892_weak_missing_profile.svg",
      "visual_evidence_png": null
    },
    {
      "strut_id": 9839,
      "cluster_id": 1,
      "classification": "weak",
      "weak_subtype": "missing",
      "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
      "defect_score": 0.8855874629691244,
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_09839_weak_missing_profile.svg",
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_09839_weak_missing_profile.svg",
      "visual_evidence_png": null
    },
    {
      "strut_id": 9893,
      "cluster_id": 1,
      "classification": "weak",
      "weak_subtype": "missing",
      "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
      "defect_score": 0.8855728246271609,
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_09893_weak_missing_profile.svg",
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_09893_weak_missing_profile.svg",
      "visual_evidence_png": null
    },
    {
      "strut_id": 11881,
      "cluster_id": 1,
      "classification": "weak",
      "weak_subtype": "missing",
      "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
      "defect_score": 0.8855533268302679,
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_11881_weak_missing_profile.svg",
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_11881_weak_missing_profile.svg",
      "visual_evidence_png": null
    },
    {
      "strut_id": 13980,
      "cluster_id": 1,
      "classification": "weak",
      "weak_subtype": "missing",
      "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
      "defect_score": 0.8855500632897019,
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_13980_weak_missing_profile.svg",
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_13980_weak_missing_profile.svg",
      "visual_evidence_png": null
    },
    {
      "strut_id": 14036,
      "cluster_id": 1,
      "classification": "weak",
      "weak_subtype": "missing",
      "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
      "defect_score": 0.8855224072933198,
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_14036_weak_missing_profile.svg",
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_14036_weak_missing_profile.svg",
      "visual_evidence_png": null
    },
    {
      "strut_id": 11882,
      "cluster_id": 1,
      "classification": "weak",
      "weak_subtype": "missing",
      "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
      "defect_score": 0.8854867130517959,
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_11882_weak_missing_profile.svg",
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_11882_weak_missing_profile.svg",
      "visual_evidence_png": null
    },
    {
      "strut_id": 15887,
      "cluster_id": 1,
      "classification": "weak",
      "weak_subtype": "missing",
      "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
      "defect_score": 0.8854647357249633,
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_15887_weak_missing_profile.svg",
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_15887_weak_missing_profile.svg",
      "visual_evidence_png": null
    },
    {
      "strut_id": 7906,
      "cluster_id": 1,
      "classification": "weak",
      "weak_subtype": "missing",
      "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
      "defect_score": 0.8854638252407313,
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_07906_weak_missing_profile.svg",
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_07906_weak_missing_profile.svg",
      "visual_evidence_png": null
    },
    {
      "strut_id": 11852,
      "cluster_id": 1,
      "classification": "weak",
      "weak_subtype": "missing",
      "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
      "defect_score": 0.8854608511552214,
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_11852_weak_missing_profile.svg",
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_11852_weak_missing_profile.svg",
      "visual_evidence_png": null
    },
    {
      "strut_id": 7934,
      "cluster_id": 1,
      "classification": "weak",
      "weak_subtype": "missing",
      "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
      "defect_score": 0.885460433922708,
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_07934_weak_missing_profile.svg",
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_07934_weak_missing_profile.svg",
      "visual_evidence_png": null
    },
    {
      "strut_id": 8048,
      "cluster_id": 1,
      "classification": "weak",
      "weak_subtype": "missing",
      "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
      "defect_score": 0.8854510552482681,
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_08048_weak_missing_profile.svg",
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_08048_weak_missing_profile.svg",
      "visual_evidence_png": null
    },
    {
      "strut_id": 11883,
      "cluster_id": 1,
      "classification": "weak",
      "weak_subtype": "missing",
      "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
      "defect_score": 0.8854219768196344,
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_11883_weak_missing_profile.svg",
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_11883_weak_missing_profile.svg",
      "visual_evidence_png": null
    },
    {
      "strut_id": 13870,
      "cluster_id": 1,
      "classification": "weak",
      "weak_subtype": "missing",
      "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
      "defect_score": 0.8853808142244816,
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_13870_weak_missing_profile.svg",
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_13870_weak_missing_profile.svg",
      "visual_evidence_png": null
    },
    {
      "strut_id": 9976,
      "cluster_id": 1,
      "classification": "weak",
      "weak_subtype": "missing",
      "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
      "defect_score": 0.8853685423731804,
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_09976_weak_missing_profile.svg",
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_09976_weak_missing_profile.svg",
      "visual_evidence_png": null
    },
    {
      "strut_id": 9948,
      "cluster_id": 1,
      "classification": "weak",
      "weak_subtype": "missing",
      "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
      "defect_score": 0.8853605458512902,
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_09948_weak_missing_profile.svg",
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_09948_weak_missing_profile.svg",
      "visual_evidence_png": null
    },
    {
      "strut_id": 10004,
      "cluster_id": 1,
      "classification": "weak",
      "weak_subtype": "missing",
      "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
      "defect_score": 0.8853555807843804,
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_10004_weak_missing_profile.svg",
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_10004_weak_missing_profile.svg",
      "visual_evidence_png": null
    },
    {
      "strut_id": 13952,
      "cluster_id": 1,
      "classification": "weak",
      "weak_subtype": "missing",
      "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
      "defect_score": 0.8853236872702838,
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_13952_weak_missing_profile.svg",
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_13952_weak_missing_profile.svg",
      "visual_evidence_png": null
    },
    {
      "strut_id": 9866,
      "cluster_id": 1,
      "classification": "weak",
      "weak_subtype": "missing",
      "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
      "defect_score": 0.8853035870939493,
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_09866_weak_missing_profile.svg",
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_09866_weak_missing_profile.svg",
      "visual_evidence_png": null
    },
    {
      "strut_id": 11910,
      "cluster_id": 1,
      "classification": "weak",
      "weak_subtype": "missing",
      "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
      "defect_score": 0.8852948512881994,
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_11910_weak_missing_profile.svg",
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_11910_weak_missing_profile.svg",
      "visual_evidence_png": null
    },
    {
      "strut_id": 9865,
      "cluster_id": 1,
      "classification": "weak",
      "weak_subtype": "missing",
      "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
      "defect_score": 0.8852929880842567,
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_09865_weak_missing_profile.svg",
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_09865_weak_missing_profile.svg",
      "visual_evidence_png": null
    },
    {
      "strut_id": 12075,
      "cluster_id": 1,
      "classification": "weak",
      "weak_subtype": "missing",
      "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
      "defect_score": 0.8852917850017549,
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_12075_weak_missing_profile.svg",
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_12075_weak_missing_profile.svg",
      "visual_evidence_png": null
    },
    {
      "strut_id": 5918,
      "cluster_id": 1,
      "classification": "weak",
      "weak_subtype": "missing",
      "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
      "defect_score": 0.8852671965956688,
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_05918_weak_missing_profile.svg",
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_05918_weak_missing_profile.svg",
      "visual_evidence_png": null
    },
    {
      "strut_id": 5807,
      "cluster_id": 1,
      "classification": "weak",
      "weak_subtype": "missing",
      "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
      "defect_score": 0.88525169249624,
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_05807_weak_missing_profile.svg",
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_05807_weak_missing_profile.svg",
      "visual_evidence_png": null
    },
    {
      "strut_id": 13896,
      "cluster_id": 1,
      "classification": "weak",
      "weak_subtype": "missing",
      "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
      "defect_score": 0.8852439749985933,
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_13896_weak_missing_profile.svg",
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_13896_weak_missing_profile.svg",
      "visual_evidence_png": null
    },
    {
      "strut_id": 13953,
      "cluster_id": 1,
      "classification": "weak",
      "weak_subtype": "missing",
      "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
      "defect_score": 0.8852366369217634,
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_13953_weak_missing_profile.svg",
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_13953_weak_missing_profile.svg",
      "visual_evidence_png": null
    },
    {
      "strut_id": 14091,
      "cluster_id": 1,
      "classification": "weak",
      "weak_subtype": "missing",
      "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
      "defect_score": 0.8852361558005214,
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_14091_weak_missing_profile.svg",
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_14091_weak_missing_profile.svg",
      "visual_evidence_png": null
    },
    {
      "strut_id": 10034,
      "cluster_id": 1,
      "classification": "weak",
      "weak_subtype": "missing",
      "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
      "defect_score": 0.8852186020463705,
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_10034_weak_missing_profile.svg",
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_10034_weak_missing_profile.svg",
      "visual_evidence_png": null
    },
    {
      "strut_id": 11909,
      "cluster_id": 1,
      "classification": "weak",
      "weak_subtype": "missing",
      "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
      "defect_score": 0.8852058934047818,
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_11909_weak_missing_profile.svg",
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_11909_weak_missing_profile.svg",
      "visual_evidence_png": null
    },
    {
      "strut_id": 7878,
      "cluster_id": 1,
      "classification": "weak",
      "weak_subtype": "missing",
      "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
      "defect_score": 0.8852000521495939,
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_07878_weak_missing_profile.svg",
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_07878_weak_missing_profile.svg",
      "visual_evidence_png": null
    },
    {
      "strut_id": 13955,
      "cluster_id": 1,
      "classification": "weak",
      "weak_subtype": "missing",
      "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
      "defect_score": 0.8851855754852295,
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_13955_weak_missing_profile.svg",
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_13955_weak_missing_profile.svg",
      "visual_evidence_png": null
    },
    {
      "strut_id": 7960,
      "cluster_id": 1,
      "classification": "weak",
      "weak_subtype": "missing",
      "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
      "defect_score": 0.8851833237335086,
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_07960_weak_missing_profile.svg",
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_07960_weak_missing_profile.svg",
      "visual_evidence_png": null
    },
    {
      "strut_id": 9895,
      "cluster_id": 1,
      "classification": "weak",
      "weak_subtype": "missing",
      "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
      "defect_score": 0.885181918181479,
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_09895_weak_missing_profile.svg",
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_09895_weak_missing_profile.svg",
      "visual_evidence_png": null
    },
    {
      "strut_id": 18445,
      "cluster_id": 1,
      "classification": "weak",
      "weak_subtype": "missing",
      "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
      "defect_score": 0.8851696588099002,
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_18445_weak_missing_profile.svg",
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_18445_weak_missing_profile.svg",
      "visual_evidence_png": null
    },
    {
      "strut_id": 13983,
      "cluster_id": 1,
      "classification": "weak",
      "weak_subtype": "missing",
      "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
      "defect_score": 0.8851593980565667,
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_13983_weak_missing_profile.svg",
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_13983_weak_missing_profile.svg",
      "visual_evidence_png": null
    },
    {
      "strut_id": 11939,
      "cluster_id": 1,
      "classification": "weak",
      "weak_subtype": "missing",
      "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
      "defect_score": 0.8851578569039703,
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_11939_weak_missing_profile.svg",
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_11939_weak_missing_profile.svg",
      "visual_evidence_png": null
    },
    {
      "strut_id": 5835,
      "cluster_id": 1,
      "classification": "weak",
      "weak_subtype": "missing",
      "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
      "defect_score": 0.88514947835356,
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_05835_weak_missing_profile.svg",
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_05835_weak_missing_profile.svg",
      "visual_evidence_png": null
    },
    {
      "strut_id": 7848,
      "cluster_id": 1,
      "classification": "weak",
      "weak_subtype": "missing",
      "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
      "defect_score": 0.8851311031728982,
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_07848_weak_missing_profile.svg",
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_07848_weak_missing_profile.svg",
      "visual_evidence_png": null
    },
    {
      "strut_id": 7932,
      "cluster_id": 1,
      "classification": "weak",
      "weak_subtype": "missing",
      "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
      "defect_score": 0.8851233556866646,
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_07932_weak_missing_profile.svg",
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_07932_weak_missing_profile.svg",
      "visual_evidence_png": null
    },
    {
      "strut_id": 7904,
      "cluster_id": 1,
      "classification": "weak",
      "weak_subtype": "missing",
      "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
      "defect_score": 0.8851118935272096,
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_07904_weak_missing_profile.svg",
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_07904_weak_missing_profile.svg",
      "visual_evidence_png": null
    },
    {
      "strut_id": 5805,
      "cluster_id": 1,
      "classification": "weak",
      "weak_subtype": "missing",
      "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
      "defect_score": 0.8850950712338089,
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_05805_weak_missing_profile.svg",
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_05805_weak_missing_profile.svg",
      "visual_evidence_png": null
    },
    {
      "strut_id": 15884,
      "cluster_id": 1,
      "classification": "weak",
      "weak_subtype": "missing",
      "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
      "defect_score": 0.885089035704732,
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_15884_weak_missing_profile.svg",
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_15884_weak_missing_profile.svg",
      "visual_evidence_png": null
    },
    {
      "strut_id": 13925,
      "cluster_id": 1,
      "classification": "weak",
      "weak_subtype": "missing",
      "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
      "defect_score": 0.8850301433354616,
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_13925_weak_missing_profile.svg",
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_13925_weak_missing_profile.svg",
      "visual_evidence_png": null
    },
    {
      "strut_id": 10032,
      "cluster_id": 1,
      "classification": "weak",
      "weak_subtype": "missing",
      "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
      "defect_score": 0.8849855735898019,
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_10032_weak_missing_profile.svg",
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_10032_weak_missing_profile.svg",
      "visual_evidence_png": null
    },
    {
      "strut_id": 7990,
      "cluster_id": 1,
      "classification": "weak",
      "weak_subtype": "missing",
      "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
      "defect_score": 0.8849774503847584,
      "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_07990_weak_missing_profile.svg",
      "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_07990_weak_missing_profile.svg",
      "visual_evidence_png": null
    }
  ]
}
```

#### External model review compatibility record

Source: `data/missing_struts/analysis/defect_visual_review/hf_model_review_results.json`

```json
{
  "status": "skipped",
  "reason": "No external LLM/API review was used; cluster labels came from the local defect_labeler subagent.",
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
      "strut_id": 4,
      "classification": "weak",
      "weak_subtype": "thin",
      "weak_subtype_reason": "weak strut has reduced average or middle support but no decisive full gap",
      "reason": "cluster has materially reduced raw CT support relative to the present baseline",
      "coverage_ratio": 0.22134053707122803,
      "profile_mean": 0.22134053707122803,
      "profile_min": 0.0,
      "low_profile_segments": [
        0,
        1,
        2,
        3
      ],
      "longest_low_profile_gap": 4,
      "profile_plot": null,
      "visual_evidence_png": null
    },
    {
      "strut_id": 5,
      "classification": "weak",
      "weak_subtype": "thin",
      "weak_subtype_reason": "weak strut has reduced average or middle support but no decisive full gap",
      "reason": "cluster has materially reduced raw CT support relative to the present baseline",
      "coverage_ratio": 0.2445039004087448,
      "profile_mean": 0.2445039004087448,
      "profile_min": 0.07156158238649368,
      "low_profile_segments": [
        2,
        3,
        4
      ],
      "longest_low_profile_gap": 3,
      "profile_plot": null,
      "visual_evidence_png": null
    },
    {
      "strut_id": 7,
      "classification": "weak",
      "weak_subtype": "thin",
      "weak_subtype_reason": "weak strut has reduced average or middle support but no decisive full gap",
      "reason": "cluster has materially reduced raw CT support relative to the present baseline",
      "coverage_ratio": 0.2969948947429657,
      "profile_mean": 0.2969948947429657,
      "profile_min": 0.19451622664928436,
      "low_profile_segments": [],
      "longest_low_profile_gap": 0,
      "profile_plot": null,
      "visual_evidence_png": null
    },
    {
      "strut_id": 8,
      "classification": "weak",
      "weak_subtype": "thin",
      "weak_subtype_reason": "weak strut has reduced average or middle support but no decisive full gap",
      "reason": "cluster has materially reduced raw CT support relative to the present baseline",
      "coverage_ratio": 0.3425348401069641,
      "profile_mean": 0.3425348401069641,
      "profile_min": 0.0,
      "low_profile_segments": [
        0,
        1,
        2
      ],
      "longest_low_profile_gap": 3,
      "profile_plot": null,
      "visual_evidence_png": null
    },
    {
      "strut_id": 10,
      "classification": "weak",
      "weak_subtype": "missing",
      "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
      "reason": "cluster has materially reduced raw CT support relative to the present baseline",
      "coverage_ratio": 0.15391932427883148,
      "profile_mean": 0.15391932427883148,
      "profile_min": 0.09002082794904709,
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
        14,
        15,
        16
      ],
      "longest_low_profile_gap": 12,
      "profile_plot": null,
      "visual_evidence_png": null
    },
    {
      "strut_id": 107,
      "classification": "weak",
      "weak_subtype": "thin",
      "weak_subtype_reason": "weak strut has reduced average or middle support but no decisive full gap",
      "reason": "cluster has materially reduced raw CT support relative to the present baseline",
      "coverage_ratio": 0.3330414295196533,
      "profile_mean": 0.3330414295196533,
      "profile_min": 0.24089112877845764,
      "low_profile_segments": [],
      "longest_low_profile_gap": 0,
      "profile_plot": null,
      "visual_evidence_png": null
    },
    {
      "strut_id": 131,
      "classification": "weak",
      "weak_subtype": "thin",
      "weak_subtype_reason": "weak strut has reduced average or middle support but no decisive full gap",
      "reason": "cluster has materially reduced raw CT support relative to the present baseline",
      "coverage_ratio": 0.2953636646270752,
      "profile_mean": 0.2953636646270752,
      "profile_min": 0.19817933440208435,
      "low_profile_segments": [],
      "longest_low_profile_gap": 0,
      "profile_plot": null,
      "visual_evidence_png": null
    },
    {
      "strut_id": 155,
      "classification": "weak",
      "weak_subtype": "thin",
      "weak_subtype_reason": "weak strut has reduced average or middle support but no decisive full gap",
      "reason": "cluster has materially reduced raw CT support relative to the present baseline",
      "coverage_ratio": 0.24471455812454224,
      "profile_mean": 0.24471455812454224,
      "profile_min": 0.1384022831916809,
      "low_profile_segments": [],
      "longest_low_profile_gap": 0,
      "profile_plot": null,
      "visual_evidence_png": null
    },
    {
      "strut_id": 156,
      "classification": "weak",
      "weak_subtype": "thin",
      "weak_subtype_reason": "weak strut has reduced average or middle support but no decisive full gap",
      "reason": "cluster has materially reduced raw CT support relative to the present baseline",
      "coverage_ratio": 0.3416946828365326,
      "profile_mean": 0.3416946828365326,
      "profile_min": 0.18491539359092712,
      "low_profile_segments": [],
      "longest_low_profile_gap": 0,
      "profile_plot": null,
      "visual_evidence_png": null
    },
    {
      "strut_id": 161,
      "classification": "weak",
      "weak_subtype": "thin",
      "weak_subtype_reason": "weak strut has reduced average or middle support but no decisive full gap",
      "reason": "cluster has materially reduced raw CT support relative to the present baseline",
      "coverage_ratio": 0.35376086831092834,
      "profile_mean": 0.35376086831092834,
      "profile_min": 0.16599097847938538,
      "low_profile_segments": [],
      "longest_low_profile_gap": 0,
      "profile_plot": null,
      "visual_evidence_png": null
    }
  ]
}
```

#### Anomaly Markdown summary

Source: `data/missing_struts/analysis/anomaly_summary.md`

# Defect Detection Summary

- Method: **unsupervised raw-CT strut embedding clustering with local labeller subagent**
- Expected struts: **18468**
- Selected clusters: **2**
- Silhouette score: **0.39542695353317475**
- Present struts: **12619**
- Weak struts: **5849**
- Weak/missing subtype: **640**
- Weak/broken subtype: **328**
- Weak/thin subtype: **4770**
- Weak/uncertain subtype: **111**
- Confirmed defects: **5849**
- Confirmed defect percentage: **31.67%**
- Nominal defect-rate comparison: **detected 31.67% vs nominal 0.5-1.0%**

## Defective Strut Definition

A defective strut is an expected registered-JSON strut assigned to a cluster that the local labeller subagent labels as weak. Weak struts are then subtyped as missing, broken, thin, or uncertain_weak from raw CT support-profile evidence.

## Performance Metric

- Primary metric: unsupervised cluster validity from silhouette score and seed-stability statistics.
- Nominal 0.5-1% defect rate is included only as contextual comparison, not as the performance metric.

## Labeller Subagent

- Cluster labels: `/home/mtrev008/Desktop/LLNL_DSC/llnl_data_science_challenge_2026/data/missing_struts/analysis/cluster_labels.json`
- Labels were assigned after clustering by the local labeller subagent from saved cluster summaries.
- Weak struts were further subtyped from per-strut raw CT support profiles.
- No external LLM/API review was used.


### Summary Card

```json
{
  "step": "Detecting Defects",
  "subagent": ".codex/agents/defect_detection",
  "status": "passed",
  "command": "/home/mtrev008/miniconda3/envs/dssi_env/bin/python -B .codex/agents/defect_detection/run.py",
  "stdout": "Detecting Defects pipeline step\n{\"status\": \"passed\", \"reference_json\": \"/home/mtrev008/Desktop/LLNL_DSC/llnl_data_science_challenge_2026/data/missing_struts/registered_jsons/210127_Brian_Tran_strut_lattices_0point5dash1 1 Slices.json\", \"tif_stack\": \"/home/mtrev008/Desktop/LLNL_DSC/llnl_data_science_challenge_2026/data/missing_struts/tif_stacks/210127_Brian_Tran_strut_lattices_0point5dash1 1 Slices.tif\", \"per_strut_json\": \"/home/mtrev008/Desktop/LLNL_DSC/llnl_data_science_challenge_2026/data/missing_struts/analysis/per_strut_defects.json\", \"summary\": \"/home/mtrev008/Desktop/LLNL_DSC/llnl_data_science_challenge_2026/data/missing_struts/analysis/anomaly_summary.md\", \"method\": \"unsupervised raw-CT strut embedding clustering with local labeller subagent\", \"defect_definition\": \"A defective strut is an expected registered-JSON strut assigned to a cluster that the local labeller subagent labels as weak. Weak struts are then subtyped as missing, broken, thin, or uncertain_weak from raw CT support-profile evidence.\", \"expected_struts\": 18468, \"observed_struts\": null, \"selected_cluster_count\": 2, \"silhouette_score\": 0.39542695353317475, \"cluster_metrics\": {\"algorithm\": \"kmeans\", \"selected_cluster_count\": 2, \"silhouette_score\": 0.39542695353317475, \"silhouette_by_k\": {\"2\": 0.39542695353317475, \"3\": 0.3761038174745983, \"4\": 0.33201155744931216, \"5\": 0.32572292322108815}, \"cluster_stability\": {\"mean_silhouette_across_seeds\": 0.39542695353317475, \"min_silhouette_across_seeds\": 0.39542695353317475, \"max_silhouette_across_seeds\": 0.39542695353317475}}, \"cluster_summary_json\": \"/home/mtrev008/Desktop/LLNL_DSC/llnl_data_science_challenge_2026/data/missing_struts/analysis/cluster_summary.json\", \"cluster_labels_json\": \"/home/mtrev008/Desktop/LLNL_DSC/llnl_data_science_challenge_2026/data/missing_struts/analysis/cluster_labels.json\", \"classification_counts\": {\"present\": 12619, \"weak\": 5849}, \"weak_subtype_counts\": {\"broken\": 328, \"missing\": 640, \"thin\": 4770, \"uncertain_weak\": 111}, \"confirmed_weak_subtypes\": [\"missing\", \"broken\", \"thin\", \"uncertain_weak\"], \"graph_candidates\": 968, \"weak_segmentation_candidates\": 5849, \"confirmed_anomalies\": 5849, \"confirmed_anomaly_percentage\": 31.670998483863983, \"nominal_rate_comparison\": \"detected 31.67% vs nominal 0.5-1.0%\", \"sample_count\": 21, \"patch_radius_voxels\": 3, \"profile_segments\": 21, \"visual_review_dir\": \"/home/mtrev008/Desktop/LLNL_DSC/llnl_data_science_challenge_2026/data/missing_struts/analysis/defect_visual_review\", \"visual_review_index\": \"/home/mtrev008/Desktop/LLNL_DSC/llnl_data_science_challenge_2026/data/missing_struts/analysis/defect_visual_review/visual_review_index.json\", \"visual_review_panels\": 100, \"hf_model_review_results\": \"/home/mtrev008/Desktop/LLNL_DSC/llnl_data_science_challenge_2026/data/missing_struts/analysis/defect_visual_review/hf_model_review_results.json\", \"hf_model_review_count\": 0, \"hf_model\": null}",
  "stderr": "",
  "outputs": [
    {
      "path": "data/missing_struts/analysis/observed_lattice.json",
      "exists": true,
      "size_bytes": 204
    },
    {
      "path": "data/missing_struts/analysis/cluster_summary.json",
      "exists": true,
      "size_bytes": 4190
    },
    {
      "path": "data/missing_struts/analysis/cluster_labels.json",
      "exists": true,
      "size_bytes": 1692
    },
    {
      "path": "data/missing_struts/analysis/per_strut_defects.json",
      "exists": true,
      "size_bytes": 38612515
    },
    {
      "path": "data/missing_struts/analysis/anomaly_summary.json",
      "exists": true,
      "size_bytes": 3045
    },
    {
      "path": "data/missing_struts/analysis/anomaly_summary.md",
      "exists": true,
      "size_bytes": 1414
    },
    {
      "path": "data/missing_struts/analysis/defect_visual_review/visual_review_index.json",
      "exists": true,
      "size_bytes": 52283
    },
    {
      "path": "data/missing_struts/analysis/defect_visual_review/hf_model_review_results.json",
      "exists": true,
      "size_bytes": 154
    }
  ],
  "results": [
    {
      "title": "Anomaly summary",
      "source": "data/missing_struts/analysis/anomaly_summary.json",
      "content": {
        "reference_json": "/home/mtrev008/Desktop/LLNL_DSC/llnl_data_science_challenge_2026/data/missing_struts/registered_jsons/210127_Brian_Tran_strut_lattices_0point5dash1 1 Slices.json",
        "tif_stack": "/home/mtrev008/Desktop/LLNL_DSC/llnl_data_science_challenge_2026/data/missing_struts/tif_stacks/210127_Brian_Tran_strut_lattices_0point5dash1 1 Slices.tif",
        "per_strut_json": "/home/mtrev008/Desktop/LLNL_DSC/llnl_data_science_challenge_2026/data/missing_struts/analysis/per_strut_defects.json",
        "summary": "/home/mtrev008/Desktop/LLNL_DSC/llnl_data_science_challenge_2026/data/missing_struts/analysis/anomaly_summary.md",
        "method": "unsupervised raw-CT strut embedding clustering with local labeller subagent",
        "defect_definition": "A defective strut is an expected registered-JSON strut assigned to a cluster that the local labeller subagent labels as weak. Weak struts are then subtyped as missing, broken, thin, or uncertain_weak from raw CT support-profile evidence.",
        "expected_struts": 18468,
        "observed_struts": null,
        "selected_cluster_count": 2,
        "silhouette_score": 0.39542695353317475,
        "cluster_metrics": {
          "algorithm": "kmeans",
          "selected_cluster_count": 2,
          "silhouette_score": 0.39542695353317475,
          "silhouette_by_k": {
            "2": 0.39542695353317475,
            "3": 0.3761038174745983,
            "4": 0.33201155744931216,
            "5": 0.32572292322108815
          },
          "cluster_stability": {
            "mean_silhouette_across_seeds": 0.39542695353317475,
            "min_silhouette_across_seeds": 0.39542695353317475,
            "max_silhouette_across_seeds": 0.39542695353317475
          }
        },
        "cluster_summary_json": "/home/mtrev008/Desktop/LLNL_DSC/llnl_data_science_challenge_2026/data/missing_struts/analysis/cluster_summary.json",
        "cluster_labels_json": "/home/mtrev008/Desktop/LLNL_DSC/llnl_data_science_challenge_2026/data/missing_struts/analysis/cluster_labels.json",
        "classification_counts": {
          "present": 12619,
          "weak": 5849
        },
        "weak_subtype_counts": {
          "broken": 328,
          "missing": 640,
          "thin": 4770,
          "uncertain_weak": 111
        },
        "confirmed_weak_subtypes": [
          "missing",
          "broken",
          "thin",
          "uncertain_weak"
        ],
        "graph_candidates": 968,
        "weak_segmentation_candidates": 5849,
        "confirmed_anomalies": 5849,
        "confirmed_anomaly_percentage": 31.670998483863983,
        "nominal_rate_comparison": "detected 31.67% vs nominal 0.5-1.0%",
        "sample_count": 21,
        "patch_radius_voxels": 3,
        "profile_segments": 21,
        "visual_review_dir": "/home/mtrev008/Desktop/LLNL_DSC/llnl_data_science_challenge_2026/data/missing_struts/analysis/defect_visual_review",
        "visual_review_index": "/home/mtrev008/Desktop/LLNL_DSC/llnl_data_science_challenge_2026/data/missing_struts/analysis/defect_visual_review/visual_review_index.json",
        "visual_review_panels": 100,
        "hf_model_review_results": "/home/mtrev008/Desktop/LLNL_DSC/llnl_data_science_challenge_2026/data/missing_struts/analysis/defect_visual_review/hf_model_review_results.json",
        "hf_model_review_count": 0,
        "hf_model": null
      }
    },
    {
      "title": "Cluster summary",
      "source": "data/missing_struts/analysis/cluster_summary.json",
      "content": {
        "method": "unsupervised raw-CT strut embedding clustering",
        "defect_definition": "A defective strut is an expected registered-JSON strut assigned to a cluster that the local labeller subagent labels as weak. Weak struts are then subtyped as missing, broken, thin, or uncertain_weak from raw CT support-profile evidence.",
        "cluster_metrics": {
          "algorithm": "kmeans",
          "selected_cluster_count": 2,
          "silhouette_score": 0.39542695353317475,
          "silhouette_by_k": {
            "2": 0.39542695353317475,
            "3": 0.3761038174745983,
            "4": 0.33201155744931216,
            "5": 0.32572292322108815
          },
          "cluster_stability": {
            "mean_silhouette_across_seeds": 0.39542695353317475,
            "min_silhouette_across_seeds": 0.39542695353317475,
            "max_silhouette_across_seeds": 0.39542695353317475
          }
        },
        "clusters": [
          {
            "cluster_id": 0,
            "strut_count": 12619,
            "mean_defect_score": 0.35683784000332486,
            "mean_profile_mean": 0.46494614020165914,
            "mean_profile_min": 0.31401196463376446,
            "mean_longest_low_gap": 0.060464379110864566,
            "mean_continuity_score": 0.9971207438518637,
            "representative_strut_ids": [
              2931,
              4976,
              2517,
              12578,
              9450,
              12352,
              8976,
              15894
            ],
            "representative_profiles": [
              [
                0.79089,
                0.6343,
                0.42599,
                0.23119,
                0.11061,
                0.07386,
                0.08815,
                0.12804,
                0.18207,
                0.24216,
                0.29591,
                0.34023,
                0.38509,
                0.43862,
                0.46773,
                0.48072,
                0.55202,
                0.71748,
                0.86301,
                0.90028,
                0.81819
              ],
              [
                0.79571,
                0.63652,
                0.46247,
                0.2952,
                0.15179,
                0.08636,
                0.08774,
                0.11527,
                0.16133,
                0.21469,
                0.27246,
                0.32696,
                0.37045,
                0.4088,
                0.432,
                0.42997,
                0.48359,
                0.59466,
                0.75398,
                0.84785,
                0.81651
              ],
              [
                0.83514,
                0.70999,
                0.51449,
                0.3349,
                0.20106,
                0.1303,
                0.14948,
                0.22753,
                0.31439,
                0.36407,
                0.37757,
                0.38512,
                0.37604,
                0.36369,
                0.36065,
                0.36842,
                0.39847,
                0.50016,
                0.67701,
                0.84153,
                0.82737
              ]
            ]
          },
          {
            "cluster_id": 1,
            "strut_count": 5849,
            "mean_defect_score": 0.5101256956660095,
            "mean_profile_mean": 0.2611625024330019,
            "mean_profile_min": 0.1163423698092687,
            "mean_longest_low_gap": 2.92272183279193,
            "mean_continuity_score": 0.8608227698670511,
            "representative_strut_ids": [
              18447,
              18159,
              18455,
              18454,
              17903,
              18419,
              14096,
              17647
            ],
            "representative_profiles": [
              [
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0201
              ],
              [
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.00702,
                0.01709,
                0.02761,
                0.03362,
                0.02663,
                0.00191,
                0.0,
                0.01206
              ],
              [
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.0,
                0.00437,
                0.01338,
                0.02032,
                0.02499,
                0.02761,
                0.02955,
                0.03019,
                0.0325,
                0.03019,
                0.02352
              ]
            ]
          }
        ]
      }
    },
    {
      "title": "Cluster labels",
      "source": "data/missing_struts/analysis/cluster_labels.json",
      "content": {
        "status": "passed",
        "labeller": "local defect_labeler subagent",
        "api_used": false,
        "source": "/home/mtrev008/Desktop/LLNL_DSC/llnl_data_science_challenge_2026/data/missing_struts/analysis/cluster_summary.json",
        "cluster_labels": [
          {
            "cluster_id": 0,
            "label": "present",
            "confidence": 0.9,
            "reason": "cluster has the lowest defect score and the most continuous raw CT support profile",
            "evidence": {
              "strut_count": 12619,
              "mean_defect_score": 0.35683784000332486,
              "mean_profile_mean": 0.46494614020165914,
              "mean_profile_min": 0.31401196463376446,
              "mean_longest_low_gap": 0.060464379110864566,
              "mean_continuity_score": 0.9971207438518637,
              "relative_defect_score": 0.0,
              "representative_strut_ids": [
                2931,
                4976,
                2517,
                12578,
                9450,
                12352,
                8976,
                15894
              ]
            }
          },
          {
            "cluster_id": 1,
            "label": "weak",
            "confidence": 0.8,
            "reason": "cluster has materially reduced raw CT support relative to the present baseline",
            "evidence": {
              "strut_count": 5849,
              "mean_defect_score": 0.5101256956660095,
              "mean_profile_mean": 0.2611625024330019,
              "mean_profile_min": 0.1163423698092687,
              "mean_longest_low_gap": 2.92272183279193,
              "mean_continuity_score": 0.8608227698670511,
              "relative_defect_score": 0.15328785566268466,
              "representative_strut_ids": [
                18447,
                18159,
                18455,
                18454,
                17903,
                18419,
                14096,
                17647
              ]
            }
          }
        ]
      }
    },
    {
      "title": "Visual review index",
      "source": "data/missing_struts/analysis/defect_visual_review/visual_review_index.json",
      "content": {
        "visual_panel_count": 100,
        "max_visual_panels": 100,
        "panel_type": "raw CT strut support profile",
        "panels": [
          {
            "strut_id": 18447,
            "cluster_id": 1,
            "classification": "weak",
            "weak_subtype": "missing",
            "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
            "defect_score": 0.8999999999883583,
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_18447_weak_missing_profile.svg",
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_18447_weak_missing_profile.svg",
            "visual_evidence_png": null
          },
          {
            "strut_id": 18159,
            "cluster_id": 1,
            "classification": "weak",
            "weak_subtype": "missing",
            "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
            "defect_score": 0.8979011126561091,
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_18159_weak_missing_profile.svg",
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_18159_weak_missing_profile.svg",
            "visual_evidence_png": null
          },
          {
            "strut_id": 18455,
            "cluster_id": 1,
            "classification": "weak",
            "weak_subtype": "missing",
            "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
            "defect_score": 0.8964905747212469,
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_18455_weak_missing_profile.svg",
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_18455_weak_missing_profile.svg",
            "visual_evidence_png": null
          },
          {
            "strut_id": 18454,
            "cluster_id": 1,
            "classification": "weak",
            "weak_subtype": "missing",
            "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
            "defect_score": 0.8918822124600411,
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_18454_weak_missing_profile.svg",
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_18454_weak_missing_profile.svg",
            "visual_evidence_png": null
          },
          {
            "strut_id": 17903,
            "cluster_id": 1,
            "classification": "weak",
            "weak_subtype": "missing",
            "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
            "defect_score": 0.8916213570162653,
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_17903_weak_missing_profile.svg",
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_17903_weak_missing_profile.svg",
            "visual_evidence_png": null
          },
          {
            "strut_id": 18419,
            "cluster_id": 1,
            "classification": "weak",
            "weak_subtype": "missing",
            "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
            "defect_score": 0.8880076033994556,
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_18419_weak_missing_profile.svg",
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_18419_weak_missing_profile.svg",
            "visual_evidence_png": null
          },
          {
            "strut_id": 14096,
            "cluster_id": 1,
            "classification": "weak",
            "weak_subtype": "missing",
            "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
            "defect_score": 0.8876162857748567,
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_14096_weak_missing_profile.svg",
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_14096_weak_missing_profile.svg",
            "visual_evidence_png": null
          },
          {
            "strut_id": 17647,
            "cluster_id": 1,
            "classification": "weak",
            "weak_subtype": "missing",
            "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
            "defect_score": 0.8875145373865961,
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_17647_weak_missing_profile.svg",
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_17647_weak_missing_profile.svg",
            "visual_evidence_png": null
          },
          {
            "strut_id": 18158,
            "cluster_id": 1,
            "classification": "weak",
            "weak_subtype": "missing",
            "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
            "defect_score": 0.8874007098376752,
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_18158_weak_missing_profile.svg",
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_18158_weak_missing_profile.svg",
            "visual_evidence_png": null
          },
          {
            "strut_id": 12080,
            "cluster_id": 1,
            "classification": "weak",
            "weak_subtype": "missing",
            "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
            "defect_score": 0.8871592039242387,
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_12080_weak_missing_profile.svg",
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_12080_weak_missing_profile.svg",
            "visual_evidence_png": null
          },
          {
            "strut_id": 11853,
            "cluster_id": 1,
            "classification": "weak",
            "weak_subtype": "missing",
            "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
            "defect_score": 0.8869494989514352,
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_11853_weak_missing_profile.svg",
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_11853_weak_missing_profile.svg",
            "visual_evidence_png": null
          },
          {
            "strut_id": 12082,
            "cluster_id": 1,
            "classification": "weak",
            "weak_subtype": "missing",
            "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
            "defect_score": 0.8867978440597654,
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_12082_weak_missing_profile.svg",
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_12082_weak_missing_profile.svg",
            "visual_evidence_png": null
          },
          {
            "strut_id": 10064,
            "cluster_id": 1,
            "classification": "weak",
            "weak_subtype": "missing",
            "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
            "defect_score": 0.8867608441971243,
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_10064_weak_missing_profile.svg",
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_10064_weak_missing_profile.svg",
            "visual_evidence_png": null
          },
          {
            "strut_id": 11855,
            "cluster_id": 1,
            "classification": "weak",
            "weak_subtype": "missing",
            "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
            "defect_score": 0.8865815794095396,
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_11855_weak_missing_profile.svg",
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_11855_weak_missing_profile.svg",
            "visual_evidence_png": null
          },
          {
            "strut_id": 13897,
            "cluster_id": 1,
            "classification": "weak",
            "weak_subtype": "missing",
            "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
            "defect_score": 0.8865569587796925,
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_13897_weak_missing_profile.svg",
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_13897_weak_missing_profile.svg",
            "visual_evidence_png": null
          },
          {
            "strut_id": 13899,
            "cluster_id": 1,
            "classification": "weak",
            "weak_subtype": "missing",
            "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
            "defect_score": 0.8863253608345986,
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_13899_weak_missing_profile.svg",
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_13899_weak_missing_profile.svg",
            "visual_evidence_png": null
          },
          {
            "strut_id": 13926,
            "cluster_id": 1,
            "classification": "weak",
            "weak_subtype": "missing",
            "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
            "defect_score": 0.8863180097192526,
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_13926_weak_missing_profile.svg",
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_13926_weak_missing_profile.svg",
            "visual_evidence_png": null
          },
          {
            "strut_id": 11966,
            "cluster_id": 1,
            "classification": "weak",
            "weak_subtype": "missing",
            "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
            "defect_score": 0.8862778028473258,
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_11966_weak_missing_profile.svg",
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_11966_weak_missing_profile.svg",
            "visual_evidence_png": null
          },
          {
            "strut_id": 18452,
            "cluster_id": 1,
            "classification": "weak",
            "weak_subtype": "missing",
            "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
            "defect_score": 0.8862575335428119,
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_18452_weak_missing_profile.svg",
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_18452_weak_missing_profile.svg",
            "visual_evidence_png": null
          },
          {
            "strut_id": 14098,
            "cluster_id": 1,
            "classification": "weak",
            "weak_subtype": "missing",
            "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
            "defect_score": 0.8861972730606794,
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_14098_weak_missing_profile.svg",
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_14098_weak_missing_profile.svg",
            "visual_evidence_png": null
          },
          {
            "strut_id": 12022,
            "cluster_id": 1,
            "classification": "weak",
            "weak_subtype": "missing",
            "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
            "defect_score": 0.8861877614632249,
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_12022_weak_missing_profile.svg",
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_12022_weak_missing_profile.svg",
            "visual_evidence_png": null
          },
          {
            "strut_id": 11938,
            "cluster_id": 1,
            "classification": "weak",
            "weak_subtype": "missing",
            "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
            "defect_score": 0.886146206408739,
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_11938_weak_missing_profile.svg",
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_11938_weak_missing_profile.svg",
            "visual_evidence_png": null
          },
          {
            "strut_id": 11911,
            "cluster_id": 1,
            "classification": "weak",
            "weak_subtype": "missing",
            "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
            "defect_score": 0.886127202771604,
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_11911_weak_missing_profile.svg",
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_11911_weak_missing_profile.svg",
            "visual_evidence_png": null
          },
          {
            "strut_id": 13868,
            "cluster_id": 1,
            "classification": "weak",
            "weak_subtype": "missing",
            "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
            "defect_score": 0.8861207552254199,
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_13868_weak_missing_profile.svg",
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_13868_weak_missing_profile.svg",
            "visual_evidence_png": null
          },
          {
            "strut_id": 9920,
            "cluster_id": 1,
            "classification": "weak",
            "weak_subtype": "missing",
            "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
            "defect_score": 0.8861132320016621,
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_09920_weak_missing_profile.svg",
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_09920_weak_missing_profile.svg",
            "visual_evidence_png": null
          },
          {
            "strut_id": 13869,
            "cluster_id": 1,
            "classification": "weak",
            "weak_subtype": "missing",
            "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
            "defect_score": 0.8861001504585148,
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_13869_weak_missing_profile.svg",
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_13869_weak_missing_profile.svg",
            "visual_evidence_png": null
          },
          {
            "strut_id": 12020,
            "cluster_id": 1,
            "classification": "weak",
            "weak_subtype": "missing",
            "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
            "defect_score": 0.8860869841650129,
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_12020_weak_missing_profile.svg",
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_12020_weak_missing_profile.svg",
            "visual_evidence_png": null
          },
          {
            "strut_id": 9922,
            "cluster_id": 1,
            "classification": "weak",
            "weak_subtype": "missing",
            "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
            "defect_score": 0.8860708085820078,
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_09922_weak_missing_profile.svg",
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_09922_weak_missing_profile.svg",
            "visual_evidence_png": null
          },
          {
            "strut_id": 14066,
            "cluster_id": 1,
            "classification": "weak",
            "weak_subtype": "missing",
            "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
            "defect_score": 0.886055041104555,
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_14066_weak_missing_profile.svg",
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_14066_weak_missing_profile.svg",
            "visual_evidence_png": null
          },
          {
            "strut_id": 14038,
            "cluster_id": 1,
            "classification": "weak",
            "weak_subtype": "missing",
            "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
            "defect_score": 0.8860440013930201,
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_14038_weak_missing_profile.svg",
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_14038_weak_missing_profile.svg",
            "visual_evidence_png": null
          },
          {
            "strut_id": 9867,
            "cluster_id": 1,
            "classification": "weak",
            "weak_subtype": "missing",
            "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
            "defect_score": 0.8860383335500955,
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_09867_weak_missing_profile.svg",
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_09867_weak_missing_profile.svg",
            "visual_evidence_png": null
          },
          {
            "strut_id": 13982,
            "cluster_id": 1,
            "classification": "weak",
            "weak_subtype": "missing",
            "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
            "defect_score": 0.8860292300581932,
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_13982_weak_missing_profile.svg",
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_13982_weak_missing_profile.svg",
            "visual_evidence_png": null
          },
          {
            "strut_id": 12050,
            "cluster_id": 1,
            "classification": "weak",
            "weak_subtype": "missing",
            "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
            "defect_score": 0.8860083384439349,
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_12050_weak_missing_profile.svg",
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_12050_weak_missing_profile.svg",
            "visual_evidence_png": null
          },
          {
            "strut_id": 11908,
            "cluster_id": 1,
            "classification": "weak",
            "weak_subtype": "missing",
            "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
            "defect_score": 0.885991450957954,
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_11908_weak_missing_profile.svg",
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_11908_weak_missing_profile.svg",
            "visual_evidence_png": null
          },
          {
            "strut_id": 11994,
            "cluster_id": 1,
            "classification": "weak",
            "weak_subtype": "missing",
            "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
            "defect_score": 0.8859870556741952,
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_11994_weak_missing_profile.svg",
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_11994_weak_missing_profile.svg",
            "visual_evidence_png": null
          },
          {
            "strut_id": 9978,
            "cluster_id": 1,
            "classification": "weak",
            "weak_subtype": "missing",
            "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
            "defect_score": 0.8859859786927701,
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_09978_weak_missing_profile.svg",
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_09978_weak_missing_profile.svg",
            "visual_evidence_png": null
          },
          {
            "strut_id": 13954,
            "cluster_id": 1,
            "classification": "weak",
            "weak_subtype": "missing",
            "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
            "defect_score": 0.8859719075262545,
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_13954_weak_missing_profile.svg",
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_13954_weak_missing_profile.svg",
            "visual_evidence_png": null
          },
          {
            "strut_id": 13871,
            "cluster_id": 1,
            "classification": "weak",
            "weak_subtype": "missing",
            "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
            "defect_score": 0.8859582901000976,
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_13871_weak_missing_profile.svg",
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_13871_weak_missing_profile.svg",
            "visual_evidence_png": null
          },
          {
            "strut_id": 13927,
            "cluster_id": 1,
            "classification": "weak",
            "weak_subtype": "missing",
            "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
            "defect_score": 0.8859491292387246,
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_13927_weak_missing_profile.svg",
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_13927_weak_missing_profile.svg",
            "visual_evidence_png": null
          },
          {
            "strut_id": 16112,
            "cluster_id": 1,
            "classification": "weak",
            "weak_subtype": "missing",
            "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
            "defect_score": 0.8859123645350336,
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_16112_weak_missing_profile.svg",
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_16112_weak_missing_profile.svg",
            "visual_evidence_png": null
          },
          {
            "strut_id": 9894,
            "cluster_id": 1,
            "classification": "weak",
            "weak_subtype": "missing",
            "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
            "defect_score": 0.8858940036967397,
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_09894_weak_missing_profile.svg",
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_09894_weak_missing_profile.svg",
            "visual_evidence_png": null
          },
          {
            "strut_id": 14010,
            "cluster_id": 1,
            "classification": "weak",
            "weak_subtype": "missing",
            "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
            "defect_score": 0.8858816796913743,
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_14010_weak_missing_profile.svg",
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_14010_weak_missing_profile.svg",
            "visual_evidence_png": null
          },
          {
            "strut_id": 9950,
            "cluster_id": 1,
            "classification": "weak",
            "weak_subtype": "missing",
            "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
            "defect_score": 0.8858671704307198,
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_09950_weak_missing_profile.svg",
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_09950_weak_missing_profile.svg",
            "visual_evidence_png": null
          },
          {
            "strut_id": 13898,
            "cluster_id": 1,
            "classification": "weak",
            "weak_subtype": "missing",
            "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
            "defect_score": 0.885835175216198,
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_13898_weak_missing_profile.svg",
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_13898_weak_missing_profile.svg",
            "visual_evidence_png": null
          },
          {
            "strut_id": 13924,
            "cluster_id": 1,
            "classification": "weak",
            "weak_subtype": "missing",
            "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
            "defect_score": 0.8858232906088234,
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_13924_weak_missing_profile.svg",
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_13924_weak_missing_profile.svg",
            "visual_evidence_png": null
          },
          {
            "strut_id": 7851,
            "cluster_id": 1,
            "classification": "weak",
            "weak_subtype": "missing",
            "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
            "defect_score": 0.8857996817678212,
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_07851_weak_missing_profile.svg",
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_07851_weak_missing_profile.svg",
            "visual_evidence_png": null
          },
          {
            "strut_id": 14064,
            "cluster_id": 1,
            "classification": "weak",
            "weak_subtype": "missing",
            "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
            "defect_score": 0.8857985474169253,
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_14064_weak_missing_profile.svg",
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_14064_weak_missing_profile.svg",
            "visual_evidence_png": null
          },
          {
            "strut_id": 11964,
            "cluster_id": 1,
            "classification": "weak",
            "weak_subtype": "missing",
            "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
            "defect_score": 0.8857393942773343,
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_11964_weak_missing_profile.svg",
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_11964_weak_missing_profile.svg",
            "visual_evidence_png": null
          },
          {
            "strut_id": 11936,
            "cluster_id": 1,
            "classification": "weak",
            "weak_subtype": "missing",
            "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
            "defect_score": 0.8857365231961011,
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_11936_weak_missing_profile.svg",
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_11936_weak_missing_profile.svg",
            "visual_evidence_png": null
          },
          {
            "strut_id": 9837,
            "cluster_id": 1,
            "classification": "weak",
            "weak_subtype": "missing",
            "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
            "defect_score": 0.8857219302444718,
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_09837_weak_missing_profile.svg",
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_09837_weak_missing_profile.svg",
            "visual_evidence_png": null
          },
          {
            "strut_id": 14008,
            "cluster_id": 1,
            "classification": "weak",
            "weak_subtype": "missing",
            "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
            "defect_score": 0.8856946643441915,
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_14008_weak_missing_profile.svg",
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_14008_weak_missing_profile.svg",
            "visual_evidence_png": null
          },
          {
            "strut_id": 15913,
            "cluster_id": 1,
            "classification": "weak",
            "weak_subtype": "missing",
            "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
            "defect_score": 0.8856827719137071,
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_15913_weak_missing_profile.svg",
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_15913_weak_missing_profile.svg",
            "visual_evidence_png": null
          },
          {
            "strut_id": 15941,
            "cluster_id": 1,
            "classification": "weak",
            "weak_subtype": "missing",
            "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
            "defect_score": 0.8856752838939429,
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_15941_weak_missing_profile.svg",
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_15941_weak_missing_profile.svg",
            "visual_evidence_png": null
          },
          {
            "strut_id": 11880,
            "cluster_id": 1,
            "classification": "weak",
            "weak_subtype": "missing",
            "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
            "defect_score": 0.8856340704485773,
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_11880_weak_missing_profile.svg",
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_11880_weak_missing_profile.svg",
            "visual_evidence_png": null
          },
          {
            "strut_id": 9864,
            "cluster_id": 1,
            "classification": "weak",
            "weak_subtype": "missing",
            "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
            "defect_score": 0.8856230881065129,
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_09864_weak_missing_profile.svg",
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_09864_weak_missing_profile.svg",
            "visual_evidence_png": null
          },
          {
            "strut_id": 9892,
            "cluster_id": 1,
            "classification": "weak",
            "weak_subtype": "missing",
            "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
            "defect_score": 0.8856178674846887,
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_09892_weak_missing_profile.svg",
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_09892_weak_missing_profile.svg",
            "visual_evidence_png": null
          },
          {
            "strut_id": 9839,
            "cluster_id": 1,
            "classification": "weak",
            "weak_subtype": "missing",
            "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
            "defect_score": 0.8855874629691244,
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_09839_weak_missing_profile.svg",
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_09839_weak_missing_profile.svg",
            "visual_evidence_png": null
          },
          {
            "strut_id": 9893,
            "cluster_id": 1,
            "classification": "weak",
            "weak_subtype": "missing",
            "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
            "defect_score": 0.8855728246271609,
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_09893_weak_missing_profile.svg",
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_09893_weak_missing_profile.svg",
            "visual_evidence_png": null
          },
          {
            "strut_id": 11881,
            "cluster_id": 1,
            "classification": "weak",
            "weak_subtype": "missing",
            "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
            "defect_score": 0.8855533268302679,
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_11881_weak_missing_profile.svg",
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_11881_weak_missing_profile.svg",
            "visual_evidence_png": null
          },
          {
            "strut_id": 13980,
            "cluster_id": 1,
            "classification": "weak",
            "weak_subtype": "missing",
            "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
            "defect_score": 0.8855500632897019,
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_13980_weak_missing_profile.svg",
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_13980_weak_missing_profile.svg",
            "visual_evidence_png": null
          },
          {
            "strut_id": 14036,
            "cluster_id": 1,
            "classification": "weak",
            "weak_subtype": "missing",
            "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
            "defect_score": 0.8855224072933198,
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_14036_weak_missing_profile.svg",
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_14036_weak_missing_profile.svg",
            "visual_evidence_png": null
          },
          {
            "strut_id": 11882,
            "cluster_id": 1,
            "classification": "weak",
            "weak_subtype": "missing",
            "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
            "defect_score": 0.8854867130517959,
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_11882_weak_missing_profile.svg",
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_11882_weak_missing_profile.svg",
            "visual_evidence_png": null
          },
          {
            "strut_id": 15887,
            "cluster_id": 1,
            "classification": "weak",
            "weak_subtype": "missing",
            "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
            "defect_score": 0.8854647357249633,
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_15887_weak_missing_profile.svg",
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_15887_weak_missing_profile.svg",
            "visual_evidence_png": null
          },
          {
            "strut_id": 7906,
            "cluster_id": 1,
            "classification": "weak",
            "weak_subtype": "missing",
            "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
            "defect_score": 0.8854638252407313,
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_07906_weak_missing_profile.svg",
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_07906_weak_missing_profile.svg",
            "visual_evidence_png": null
          },
          {
            "strut_id": 11852,
            "cluster_id": 1,
            "classification": "weak",
            "weak_subtype": "missing",
            "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
            "defect_score": 0.8854608511552214,
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_11852_weak_missing_profile.svg",
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_11852_weak_missing_profile.svg",
            "visual_evidence_png": null
          },
          {
            "strut_id": 7934,
            "cluster_id": 1,
            "classification": "weak",
            "weak_subtype": "missing",
            "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
            "defect_score": 0.885460433922708,
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_07934_weak_missing_profile.svg",
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_07934_weak_missing_profile.svg",
            "visual_evidence_png": null
          },
          {
            "strut_id": 8048,
            "cluster_id": 1,
            "classification": "weak",
            "weak_subtype": "missing",
            "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
            "defect_score": 0.8854510552482681,
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_08048_weak_missing_profile.svg",
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_08048_weak_missing_profile.svg",
            "visual_evidence_png": null
          },
          {
            "strut_id": 11883,
            "cluster_id": 1,
            "classification": "weak",
            "weak_subtype": "missing",
            "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
            "defect_score": 0.8854219768196344,
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_11883_weak_missing_profile.svg",
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_11883_weak_missing_profile.svg",
            "visual_evidence_png": null
          },
          {
            "strut_id": 13870,
            "cluster_id": 1,
            "classification": "weak",
            "weak_subtype": "missing",
            "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
            "defect_score": 0.8853808142244816,
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_13870_weak_missing_profile.svg",
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_13870_weak_missing_profile.svg",
            "visual_evidence_png": null
          },
          {
            "strut_id": 9976,
            "cluster_id": 1,
            "classification": "weak",
            "weak_subtype": "missing",
            "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
            "defect_score": 0.8853685423731804,
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_09976_weak_missing_profile.svg",
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_09976_weak_missing_profile.svg",
            "visual_evidence_png": null
          },
          {
            "strut_id": 9948,
            "cluster_id": 1,
            "classification": "weak",
            "weak_subtype": "missing",
            "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
            "defect_score": 0.8853605458512902,
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_09948_weak_missing_profile.svg",
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_09948_weak_missing_profile.svg",
            "visual_evidence_png": null
          },
          {
            "strut_id": 10004,
            "cluster_id": 1,
            "classification": "weak",
            "weak_subtype": "missing",
            "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
            "defect_score": 0.8853555807843804,
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_10004_weak_missing_profile.svg",
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_10004_weak_missing_profile.svg",
            "visual_evidence_png": null
          },
          {
            "strut_id": 13952,
            "cluster_id": 1,
            "classification": "weak",
            "weak_subtype": "missing",
            "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
            "defect_score": 0.8853236872702838,
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_13952_weak_missing_profile.svg",
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_13952_weak_missing_profile.svg",
            "visual_evidence_png": null
          },
          {
            "strut_id": 9866,
            "cluster_id": 1,
            "classification": "weak",
            "weak_subtype": "missing",
            "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
            "defect_score": 0.8853035870939493,
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_09866_weak_missing_profile.svg",
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_09866_weak_missing_profile.svg",
            "visual_evidence_png": null
          },
          {
            "strut_id": 11910,
            "cluster_id": 1,
            "classification": "weak",
            "weak_subtype": "missing",
            "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
            "defect_score": 0.8852948512881994,
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_11910_weak_missing_profile.svg",
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_11910_weak_missing_profile.svg",
            "visual_evidence_png": null
          },
          {
            "strut_id": 9865,
            "cluster_id": 1,
            "classification": "weak",
            "weak_subtype": "missing",
            "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
            "defect_score": 0.8852929880842567,
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_09865_weak_missing_profile.svg",
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_09865_weak_missing_profile.svg",
            "visual_evidence_png": null
          },
          {
            "strut_id": 12075,
            "cluster_id": 1,
            "classification": "weak",
            "weak_subtype": "missing",
            "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
            "defect_score": 0.8852917850017549,
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_12075_weak_missing_profile.svg",
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_12075_weak_missing_profile.svg",
            "visual_evidence_png": null
          },
          {
            "strut_id": 5918,
            "cluster_id": 1,
            "classification": "weak",
            "weak_subtype": "missing",
            "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
            "defect_score": 0.8852671965956688,
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_05918_weak_missing_profile.svg",
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_05918_weak_missing_profile.svg",
            "visual_evidence_png": null
          },
          {
            "strut_id": 5807,
            "cluster_id": 1,
            "classification": "weak",
            "weak_subtype": "missing",
            "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
            "defect_score": 0.88525169249624,
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_05807_weak_missing_profile.svg",
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_05807_weak_missing_profile.svg",
            "visual_evidence_png": null
          },
          {
            "strut_id": 13896,
            "cluster_id": 1,
            "classification": "weak",
            "weak_subtype": "missing",
            "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
            "defect_score": 0.8852439749985933,
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_13896_weak_missing_profile.svg",
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_13896_weak_missing_profile.svg",
            "visual_evidence_png": null
          },
          {
            "strut_id": 13953,
            "cluster_id": 1,
            "classification": "weak",
            "weak_subtype": "missing",
            "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
            "defect_score": 0.8852366369217634,
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_13953_weak_missing_profile.svg",
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_13953_weak_missing_profile.svg",
            "visual_evidence_png": null
          },
          {
            "strut_id": 14091,
            "cluster_id": 1,
            "classification": "weak",
            "weak_subtype": "missing",
            "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
            "defect_score": 0.8852361558005214,
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_14091_weak_missing_profile.svg",
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_14091_weak_missing_profile.svg",
            "visual_evidence_png": null
          },
          {
            "strut_id": 10034,
            "cluster_id": 1,
            "classification": "weak",
            "weak_subtype": "missing",
            "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
            "defect_score": 0.8852186020463705,
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_10034_weak_missing_profile.svg",
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_10034_weak_missing_profile.svg",
            "visual_evidence_png": null
          },
          {
            "strut_id": 11909,
            "cluster_id": 1,
            "classification": "weak",
            "weak_subtype": "missing",
            "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
            "defect_score": 0.8852058934047818,
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_11909_weak_missing_profile.svg",
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_11909_weak_missing_profile.svg",
            "visual_evidence_png": null
          },
          {
            "strut_id": 7878,
            "cluster_id": 1,
            "classification": "weak",
            "weak_subtype": "missing",
            "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
            "defect_score": 0.8852000521495939,
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_07878_weak_missing_profile.svg",
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_07878_weak_missing_profile.svg",
            "visual_evidence_png": null
          },
          {
            "strut_id": 13955,
            "cluster_id": 1,
            "classification": "weak",
            "weak_subtype": "missing",
            "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
            "defect_score": 0.8851855754852295,
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_13955_weak_missing_profile.svg",
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_13955_weak_missing_profile.svg",
            "visual_evidence_png": null
          },
          {
            "strut_id": 7960,
            "cluster_id": 1,
            "classification": "weak",
            "weak_subtype": "missing",
            "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
            "defect_score": 0.8851833237335086,
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_07960_weak_missing_profile.svg",
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_07960_weak_missing_profile.svg",
            "visual_evidence_png": null
          },
          {
            "strut_id": 9895,
            "cluster_id": 1,
            "classification": "weak",
            "weak_subtype": "missing",
            "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
            "defect_score": 0.885181918181479,
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_09895_weak_missing_profile.svg",
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_09895_weak_missing_profile.svg",
            "visual_evidence_png": null
          },
          {
            "strut_id": 18445,
            "cluster_id": 1,
            "classification": "weak",
            "weak_subtype": "missing",
            "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
            "defect_score": 0.8851696588099002,
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_18445_weak_missing_profile.svg",
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_18445_weak_missing_profile.svg",
            "visual_evidence_png": null
          },
          {
            "strut_id": 13983,
            "cluster_id": 1,
            "classification": "weak",
            "weak_subtype": "missing",
            "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
            "defect_score": 0.8851593980565667,
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_13983_weak_missing_profile.svg",
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_13983_weak_missing_profile.svg",
            "visual_evidence_png": null
          },
          {
            "strut_id": 11939,
            "cluster_id": 1,
            "classification": "weak",
            "weak_subtype": "missing",
            "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
            "defect_score": 0.8851578569039703,
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_11939_weak_missing_profile.svg",
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_11939_weak_missing_profile.svg",
            "visual_evidence_png": null
          },
          {
            "strut_id": 5835,
            "cluster_id": 1,
            "classification": "weak",
            "weak_subtype": "missing",
            "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
            "defect_score": 0.88514947835356,
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_05835_weak_missing_profile.svg",
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_05835_weak_missing_profile.svg",
            "visual_evidence_png": null
          },
          {
            "strut_id": 7848,
            "cluster_id": 1,
            "classification": "weak",
            "weak_subtype": "missing",
            "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
            "defect_score": 0.8851311031728982,
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_07848_weak_missing_profile.svg",
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_07848_weak_missing_profile.svg",
            "visual_evidence_png": null
          },
          {
            "strut_id": 7932,
            "cluster_id": 1,
            "classification": "weak",
            "weak_subtype": "missing",
            "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
            "defect_score": 0.8851233556866646,
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_07932_weak_missing_profile.svg",
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_07932_weak_missing_profile.svg",
            "visual_evidence_png": null
          },
          {
            "strut_id": 7904,
            "cluster_id": 1,
            "classification": "weak",
            "weak_subtype": "missing",
            "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
            "defect_score": 0.8851118935272096,
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_07904_weak_missing_profile.svg",
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_07904_weak_missing_profile.svg",
            "visual_evidence_png": null
          },
          {
            "strut_id": 5805,
            "cluster_id": 1,
            "classification": "weak",
            "weak_subtype": "missing",
            "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
            "defect_score": 0.8850950712338089,
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_05805_weak_missing_profile.svg",
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_05805_weak_missing_profile.svg",
            "visual_evidence_png": null
          },
          {
            "strut_id": 15884,
            "cluster_id": 1,
            "classification": "weak",
            "weak_subtype": "missing",
            "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
            "defect_score": 0.885089035704732,
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_15884_weak_missing_profile.svg",
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_15884_weak_missing_profile.svg",
            "visual_evidence_png": null
          },
          {
            "strut_id": 13925,
            "cluster_id": 1,
            "classification": "weak",
            "weak_subtype": "missing",
            "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
            "defect_score": 0.8850301433354616,
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_13925_weak_missing_profile.svg",
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_13925_weak_missing_profile.svg",
            "visual_evidence_png": null
          },
          {
            "strut_id": 10032,
            "cluster_id": 1,
            "classification": "weak",
            "weak_subtype": "missing",
            "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
            "defect_score": 0.8849855735898019,
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_10032_weak_missing_profile.svg",
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_10032_weak_missing_profile.svg",
            "visual_evidence_png": null
          },
          {
            "strut_id": 7990,
            "cluster_id": 1,
            "classification": "weak",
            "weak_subtype": "missing",
            "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
            "defect_score": 0.8849774503847584,
            "profile_plot": "data/missing_struts/analysis/defect_visual_review/strut_07990_weak_missing_profile.svg",
            "visual_evidence": "data/missing_struts/analysis/defect_visual_review/strut_07990_weak_missing_profile.svg",
            "visual_evidence_png": null
          }
        ]
      }
    },
    {
      "title": "External model review compatibility record",
      "source": "data/missing_struts/analysis/defect_visual_review/hf_model_review_results.json",
      "content": {
        "status": "skipped",
        "reason": "No external LLM/API review was used; cluster labels came from the local defect_labeler subagent.",
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
            "strut_id": 4,
            "classification": "weak",
            "weak_subtype": "thin",
            "weak_subtype_reason": "weak strut has reduced average or middle support but no decisive full gap",
            "reason": "cluster has materially reduced raw CT support relative to the present baseline",
            "coverage_ratio": 0.22134053707122803,
            "profile_mean": 0.22134053707122803,
            "profile_min": 0.0,
            "low_profile_segments": [
              0,
              1,
              2,
              3
            ],
            "longest_low_profile_gap": 4,
            "profile_plot": null,
            "visual_evidence_png": null
          },
          {
            "strut_id": 5,
            "classification": "weak",
            "weak_subtype": "thin",
            "weak_subtype_reason": "weak strut has reduced average or middle support but no decisive full gap",
            "reason": "cluster has materially reduced raw CT support relative to the present baseline",
            "coverage_ratio": 0.2445039004087448,
            "profile_mean": 0.2445039004087448,
            "profile_min": 0.07156158238649368,
            "low_profile_segments": [
              2,
              3,
              4
            ],
            "longest_low_profile_gap": 3,
            "profile_plot": null,
            "visual_evidence_png": null
          },
          {
            "strut_id": 7,
            "classification": "weak",
            "weak_subtype": "thin",
            "weak_subtype_reason": "weak strut has reduced average or middle support but no decisive full gap",
            "reason": "cluster has materially reduced raw CT support relative to the present baseline",
            "coverage_ratio": 0.2969948947429657,
            "profile_mean": 0.2969948947429657,
            "profile_min": 0.19451622664928436,
            "low_profile_segments": [],
            "longest_low_profile_gap": 0,
            "profile_plot": null,
            "visual_evidence_png": null
          },
          {
            "strut_id": 8,
            "classification": "weak",
            "weak_subtype": "thin",
            "weak_subtype_reason": "weak strut has reduced average or middle support but no decisive full gap",
            "reason": "cluster has materially reduced raw CT support relative to the present baseline",
            "coverage_ratio": 0.3425348401069641,
            "profile_mean": 0.3425348401069641,
            "profile_min": 0.0,
            "low_profile_segments": [
              0,
              1,
              2
            ],
            "longest_low_profile_gap": 3,
            "profile_plot": null,
            "visual_evidence_png": null
          },
          {
            "strut_id": 10,
            "classification": "weak",
            "weak_subtype": "missing",
            "weak_subtype_reason": "very low mean support with a long contiguous low-support gap",
            "reason": "cluster has materially reduced raw CT support relative to the present baseline",
            "coverage_ratio": 0.15391932427883148,
            "profile_mean": 0.15391932427883148,
            "profile_min": 0.09002082794904709,
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
              14,
              15,
              16
            ],
            "longest_low_profile_gap": 12,
            "profile_plot": null,
            "visual_evidence_png": null
          },
          {
            "strut_id": 107,
            "classification": "weak",
            "weak_subtype": "thin",
            "weak_subtype_reason": "weak strut has reduced average or middle support but no decisive full gap",
            "reason": "cluster has materially reduced raw CT support relative to the present baseline",
            "coverage_ratio": 0.3330414295196533,
            "profile_mean": 0.3330414295196533,
            "profile_min": 0.24089112877845764,
            "low_profile_segments": [],
            "longest_low_profile_gap": 0,
            "profile_plot": null,
            "visual_evidence_png": null
          },
          {
            "strut_id": 131,
            "classification": "weak",
            "weak_subtype": "thin",
            "weak_subtype_reason": "weak strut has reduced average or middle support but no decisive full gap",
            "reason": "cluster has materially reduced raw CT support relative to the present baseline",
            "coverage_ratio": 0.2953636646270752,
            "profile_mean": 0.2953636646270752,
            "profile_min": 0.19817933440208435,
            "low_profile_segments": [],
            "longest_low_profile_gap": 0,
            "profile_plot": null,
            "visual_evidence_png": null
          },
          {
            "strut_id": 155,
            "classification": "weak",
            "weak_subtype": "thin",
            "weak_subtype_reason": "weak strut has reduced average or middle support but no decisive full gap",
            "reason": "cluster has materially reduced raw CT support relative to the present baseline",
            "coverage_ratio": 0.24471455812454224,
            "profile_mean": 0.24471455812454224,
            "profile_min": 0.1384022831916809,
            "low_profile_segments": [],
            "longest_low_profile_gap": 0,
            "profile_plot": null,
            "visual_evidence_png": null
          },
          {
            "strut_id": 156,
            "classification": "weak",
            "weak_subtype": "thin",
            "weak_subtype_reason": "weak strut has reduced average or middle support but no decisive full gap",
            "reason": "cluster has materially reduced raw CT support relative to the present baseline",
            "coverage_ratio": 0.3416946828365326,
            "profile_mean": 0.3416946828365326,
            "profile_min": 0.18491539359092712,
            "low_profile_segments": [],
            "longest_low_profile_gap": 0,
            "profile_plot": null,
            "visual_evidence_png": null
          },
          {
            "strut_id": 161,
            "classification": "weak",
            "weak_subtype": "thin",
            "weak_subtype_reason": "weak strut has reduced average or middle support but no decisive full gap",
            "reason": "cluster has materially reduced raw CT support relative to the present baseline",
            "coverage_ratio": 0.35376086831092834,
            "profile_mean": 0.35376086831092834,
            "profile_min": 0.16599097847938538,
            "low_profile_segments": [],
            "longest_low_profile_gap": 0,
            "profile_plot": null,
            "visual_evidence_png": null
          }
        ]
      }
    },
    {
      "title": "Anomaly Markdown summary",
      "source": "data/missing_struts/analysis/anomaly_summary.md",
      "content": "# Defect Detection Summary\n\n- Method: **unsupervised raw-CT strut embedding clustering with local labeller subagent**\n- Expected struts: **18468**\n- Selected clusters: **2**\n- Silhouette score: **0.39542695353317475**\n- Present struts: **12619**\n- Weak struts: **5849**\n- Weak/missing subtype: **640**\n- Weak/broken subtype: **328**\n- Weak/thin subtype: **4770**\n- Weak/uncertain subtype: **111**\n- Confirmed defects: **5849**\n- Confirmed defect percentage: **31.67%**\n- Nominal defect-rate comparison: **detected 31.67% vs nominal 0.5-1.0%**\n\n## Defective Strut Definition\n\nA defective strut is an expected registered-JSON strut assigned to a cluster that the local labeller subagent labels as weak. Weak struts are then subtyped as missing, broken, thin, or uncertain_weak from raw CT support-profile evidence.\n\n## Performance Metric\n\n- Primary metric: unsupervised cluster validity from silhouette score and seed-stability statistics.\n- Nominal 0.5-1% defect rate is included only as contextual comparison, not as the performance metric.\n\n## Labeller Subagent\n\n- Cluster labels: `/home/mtrev008/Desktop/LLNL_DSC/llnl_data_science_challenge_2026/data/missing_struts/analysis/cluster_labels.json`\n- Labels were assigned after clustering by the local labeller subagent from saved cluster summaries.\n- Weak struts were further subtyped from per-strut raw CT support profiles.\n- No external LLM/API review was used."
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
- Command: `/home/mtrev008/miniconda3/envs/dssi_env/bin/python -B .codex/agents/visualization/run.py`
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
  "command": "/home/mtrev008/miniconda3/envs/dssi_env/bin/python -B .codex/agents/visualization/run.py",
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
