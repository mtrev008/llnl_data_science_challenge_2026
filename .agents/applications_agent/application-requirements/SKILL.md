---
name: application-requirements
description: Establish, validate, and persist the engineering application context required to judge defect criticality. Use before structural, NDE, CT, anomaly, failure-risk, fitness-for-service, or defect-severity analysis whenever application requirements are not already available in a complete application_requirements.json.
---

# Application Requirements

Create a machine-readable application contract before interpreting any observed
condition as a critical defect. Do not substitute an informal conversation,
chat summary, or unstructured report for the JSON artifact.

## Required workflow

1. Search the supplied project, specifications, drawings, metadata, and prior
   pipeline outputs for application requirements. Record the source of each
   value.
2. Collect every required field defined in
   [application-requirements-schema.md](references/application-requirements-schema.md).
   Ask concise, targeted questions only for facts that cannot be established
   from supplied evidence.
3. Preserve unknown facts as `null`; never invent engineering requirements.
   Add each unresolved required field to `missing_required_fields`.
4. Normalize quantities into explicit value-and-unit objects. Preserve the
   original wording in `notes` when normalization is uncertain.
5. Assign `status`:
   - `complete` when every required field has a supported value.
   - `incomplete` when one or more required fields are unknown.
   - `conflicting` when sources disagree and the conflict is unresolved.
6. Write valid UTF-8 JSON named `application_requirements.json` in the current
   dataset's pipeline output directory, preferably
   `<dataset>/pipeline_outputs/application_requirements/`.
7. Re-open and parse the saved JSON. Confirm that all schema keys exist and
   that `missing_required_fields` agrees with the null or unresolved values.
8. Hand the JSON path and status to downstream agents.

## Analysis gate

Do not make an application-specific claim that a defect is critical unless
`status` is `complete`. When status is `incomplete` or `conflicting`:

- Continue application-independent measurements and observations if useful.
- Label any severity or failure-risk discussion as provisional.
- State which missing or conflicting requirements prevent a defensible
  criticality determination.
- Do not silently fill gaps with typical, conservative, or inferred values.

## Revision rules

- Update the existing JSON rather than creating competing requirement files.
- Preserve prior values in `revision_history` when a requirement changes.
- Include timestamp, author or source, changed fields, and reason for change.
- Treat applicable standards and jurisdiction as inputs, not as conclusions;
  do not claim compliance without a separate compliance assessment.
