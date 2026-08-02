# Deterministic solver contracts

Use two artifacts:

1. `structural_analysis_request.json` records what is to be calculated and why.
2. `structural_mechanics_report.json` records what ran, whether it was valid,
   the returned evidence, and the supported interpretation.

Validate each artifact against its schema:

- [structural-analysis-request.schema.json](structural-analysis-request.schema.json)
- [structural-mechanics-report.schema.json](structural-mechanics-report.schema.json)

## Responsibility boundary

The language model may characterize evidence, form hypotheses, select fidelity,
assemble supported inputs, request quantities of interest, and interpret
validated results. It must not fabricate solver execution or numerical results.

The deterministic solver or adapter must read the request, reject unsupported
or incomplete inputs, execute a reproducible calculation, and return numerical
results with units and provenance.

## Request construction

- Use stable identifiers for hypotheses, load cases, boundary conditions,
  defects, and requested quantities.
- Reference geometry by path and checksum when available.
- State units and coordinate systems explicitly.
- Record the source of material values; do not silently populate defaults.
- Keep loads separate from boundary conditions.
- State modeling assumptions and unresolved uncertainties.
- Request only quantities the selected fidelity can produce defensibly.
- Define method-specific validation checks before execution.
- Use `provisional` scope when application requirements are incomplete.
- Use `unsupported` fidelity selection when no available deterministic method
  can answer the question.

## Solver response

The report status has these meanings:

- `complete`: execution and required validation checks succeeded.
- `provisional`: useful evidence exists, but requirements or validation limits
  prevent a final application-specific conclusion.
- `failed`: execution or a required validity check failed.
- `unsupported`: the requested capability was not available or the selected
  method could not represent the requested mechanism.

Every result must identify its quantity, value, unit, load case, source solver
output, and validation status. Vector, tensor, field, and file-based results may
store their data in an external artifact and reference its path and checksum.

## Evidence linkage

Maintain this trace:

`observation -> hypothesis -> analysis request -> solver result -> validation -> interpretation`

An interpretation must cite the identifiers of the observations, hypotheses,
results, and validation checks that support it. Failed validation prevents the
associated result from supporting a conclusion.

## Revision and reproducibility

- Preserve request and report identifiers across reruns of the same analysis.
- Increment the revision when inputs or model decisions change.
- Record creation time, generator, solver name and version, configuration, and
  input checksums.
- Never overwrite a completed report with a different run without preserving
  the prior artifact or revision history.
- Treat paths as references, not proof that a file was actually consumed;
  solver provenance must record the resolved execution inputs.
