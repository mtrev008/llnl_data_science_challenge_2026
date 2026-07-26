# Repository Guidelines

## Project Structure & Module Organization

This repository supports the LLNL 2026 Data Science Challenge workflow for CT lattice analysis. Core Python code lives in `src/`, including `src/mcp_server.py` for FastMCP tool wrappers and `src/skeletonization.py` for skeleton extraction. Challenge data and generated analysis artifacts live under `data/`; keep large CT volumes, masks, skeletons, and reports close to the dataset they describe, such as `data/missing_struts/analysis/`. Project skills are in `.agents/skills/`, while runnable Codex subagents are in `.codex/agents/`. Presentation and challenge materials are in `presentation/` and `DATA_SCIENCE_CHALLENGE_2026.pdf`.

## Build, Test, and Development Commands

Create and activate the recommended environment:

```bash
conda create -n dssi_env python=3.11 -y
conda activate dssi_env
pip install -r requirements.txt
```

Run the MCP server locally:

```bash
python src/mcp_server.py
```

Run the manager workflow when present:

```bash
python .codex/agents/run_workflow.py
```

Use `python -B` for agent scripts when avoiding `__pycache__` writes in read-only agent paths.

## Coding Style & Naming Conventions

Use Python 3.11-compatible code with 4-space indentation. Prefer explicit function signatures and type annotations for MCP tools; FastMCP uses names, docstrings, and annotations to build schemas. Use snake_case for functions, variables, and generated artifact names. Keep scientific wrapper functions small and data-aware: validate shapes, dtypes, and nonblank outputs before downstream stages.

## Testing Guidelines

There is no checked-in pytest configuration. Validate changes with focused smoke tests that exercise real data paths, for example loading `data/unitcell/unitcell.npy`, segmenting to a temporary `.npy`, and skeletonizing the result. For segmentation checks, inspect the input value range before choosing thresholds; this repository has low-intensity CT examples where `0.001` may be more useful than `0.5`. Remove temporary test artifacts unless they are part of the requested deliverable.

## Commit & Pull Request Guidelines

Recent commits use short, imperative summaries such as `updated presentation with github link` and `Add data via Git LFS`. Keep commits focused and mention large data additions explicitly. Pull requests should describe the workflow stage affected, list commands or smoke tests run, identify generated outputs, and note any Git LFS or large-file changes. For UI or report changes, include representative output paths rather than duplicating bulky artifacts.

## Agent-Specific Instructions

For pipeline work, preserve the ordered stages: Data Analyzer, Segmentation, Skeletonization, Detecting Defects, and Visualization. Write a single final manager report to `reports/report.md` when producing a consolidated deliverable. Keep intermediate Markdown and data artifacts in dataset-specific analysis directories, not scattered through `reports/`.
