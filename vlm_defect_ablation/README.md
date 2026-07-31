# VLM defect ablation

This isolated experiment compares six fresh-context VLM requests over ordered seven-slice CT stacks: images only, images plus segmentation, images plus geometry, images plus both, images plus a local paper, and full context. It contains exactly two VLM roles: Agent 1 writes measurable detection instructions; Agent 2 writes a constrained deterministic script. An ordinary Python controller owns the loop—there is deliberately no orchestrator agent.

Each stack is `[z-3, …, z+3]`; thus seven slices provide local evidence only. No labels, training, precision, recall, F1, accuracy, or confusion matrix are used. Outputs are candidate detections, not confirmed defects.

Configuration supplies the TIFF and optional mask, JSON geometry, and local paper. Conditions are independently prompted from scratch, have separate manifests, and are leakage-checked before a request. Unregistered geometry is structural context only: it is never overlaid or spatially assigned. Prompts, manifests, raw responses, scripts, outputs, and failures are retained per condition/center/attempt.

Generated code is AST-inspected for network, shell, destructive, dynamic-execution, absolute-path, and traversal operations, then launched with a timeout in its designated run directory. This is a best-effort local restriction, not a security sandbox against a malicious Python interpreter. The mock client is for testing; `provider: huggingface` uses a fresh stateless request and `HF_TOKEN` without saving credentials.

Reference statistics are per-stack by default; global unlabeled support is available to the reference-statistics module and must be shared across conditions when enabled. Label-free reports compare executable specificity, uncertainty, candidate counts, bounding-box overlap, category agreement, and repeat stability. Agreement or stability never proves correctness.

```bash
cd vlm_defect_ablation
PYTHONPYCACHEPREFIX=/tmp/llnl-pycache /home/mtrev008/miniconda3/envs/dssi_env/bin/python -B -m src.cli run-experiment --config config.yaml --center-slices 100 200 300 --conditions images_only images_segmentation full_context
```

Use `--force` to rerun completed condition-stack pairs. Start with `inspect-data`, then inspect each run's `manifest.json`, `prompts/`, `agent1/`, `agent2/`, and `execution/` records. PDF input requires an already-installed `pypdf`; the project never installs dependencies. VLM-generated methods remain experimental and need human scientific review.
