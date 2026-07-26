---
name: defect-detection
description: Detect missing, disconnected, or anomalous struts from segmentation and skeleton outputs.
---

# Detecting Defects Subagent

Compare the observed skeleton geometry with the registered lattice JSON and
write defect summaries under `data/missing_struts/analysis/`.

Run `python .codex/agents/defect_detection/run.py`.
