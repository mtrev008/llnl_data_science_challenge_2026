---
name: data-analyzer
description: Analyze 3D CT volume metadata and intensity statistics for the LLNL CT workflow.
---

# Data Analyzer Subagent

Validate the default or supplied CT volume, compute shape/dtype/intensity
statistics, and write both JSON and Markdown summaries under
`data/missing_struts/analysis/`.

Run:

```bash
python .codex/agents/data_analyzer/run.py
```
