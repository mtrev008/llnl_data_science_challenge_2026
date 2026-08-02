---
name: lattice-structural-mechanics
description: Translate as-built lattice geometry into testable structural-performance hypotheses and select an appropriate deterministic analysis fidelity. Use for lattice mechanics, stiffness, buckling, collapse, load redistribution, stress concentration, boundary effects, defect interaction, fatigue, homogenization, or representative-volume analysis.
---

# Lattice Structural Mechanics

Translate measured as-built geometry into traceable structural-performance
hypotheses. Select and direct an appropriate deterministic calculation; do not
invent mechanics results or present language-model estimates as solver output.

## Required workflow

### 1. Establish application context

1. Locate and parse `application_requirements.json`.
2. Record its path, schema version, and status.
3. Extract the intended function, material, loads, service mode, attachments,
   allowable deformation, environment, expected life, failure consequence,
   criticality classification, industry, and jurisdiction.
4. Preserve missing or conflicting requirements. Do not replace them with
   typical values, hidden assumptions, or values inferred only from geometry.

When the requirements status is not `complete`, permit application-independent
geometry characterization and exploratory screening, but label performance,
severity, safety-margin, and defect-criticality conclusions as provisional.

### 2. Establish geometry evidence

Identify the supplied as-built representation and its provenance:

- Volumetric image, segmentation, surface mesh, skeleton, lattice graph,
  nominal model, or a combination of these.
- Units, coordinate system, specimen orientation, and load-axis mapping.
- Resolution, segmentation or reconstruction method, and known uncertainty.
- Geometry version, source path, and available checksum.
- Registration between nominal and as-built representations.

Stop before solver preparation when units, coordinate axes, or geometry identity
are ambiguous enough to change the model.

### 3. Characterize the structure

Describe only features supported by the supplied evidence:

- Topology, connectivity, cell architecture, and load-path continuity.
- Strut lengths, orientations, cross-sections, slenderness, and variability.
- Joint geometry, nodal offsets, eccentricity, and manufacturing distortion.
- Relative density and spatial variation when measurable.
- Boundary cells, attachment regions, and distance from boundaries.
- Missing, disconnected, undersized, oversized, bent, cracked, porous, or
  otherwise anomalous members.
- Defect proximity, clustering, alignment, and possible interaction.
- Differences between nominal and as-built geometry.

Record measurement uncertainty and distinguish absent evidence from evidence
that a feature is absent.

### 4. Form performance hypotheses

For each relevant observation, create a testable hypothesis containing:

1. The supporting geometry observation.
2. The proposed mechanics mechanism.
3. The expected response quantity and direction of change.
4. The load cases and boundary conditions under which it applies.
5. The deterministic analysis needed to test it.
6. Important alternative explanations.
7. The evidence that would confirm or reject it.

Use qualified language before calculation. For example, state that a missing
member *may redirect load into adjacent struts* rather than claiming a stress
increase without solver evidence.

### 5. Identify candidate governing mechanisms

Read [mechanics-guidance.md](references/mechanics-guidance.md) before forming
or evaluating mechanics hypotheses.

Consider elastic stiffness, effective modulus, member force and bending,
strut buckling, plastic collapse, load redistribution, stress concentration,
boundary effects, interacting defects, fatigue or crack initiation, and
homogenized behavior. Treat these as candidates until deterministic evidence
supports or excludes them.

### 6. Select analysis fidelity

Read [fidelity-selection.md](references/fidelity-selection.md) and apply its
decision and escalation rules.

Choose the lowest fidelity capable of answering the engineering question:

1. Fast graph-based screening.
2. Beam-element finite-element model.
3. Solid-element local submodel.
4. Nonlinear buckling or collapse simulation.
5. Fatigue or damage model.

Record the selected method, decision objective, required outputs, assumptions,
known limitations, and why both lower and higher fidelity are inappropriate or
unnecessary. Escalate when the chosen method cannot represent the suspected
mechanism or cannot support the required decision.

### 7. Prepare deterministic execution

Read [solver-contracts.md](references/solver-contracts.md). Write the request
against
[structural-analysis-request.schema.json](references/structural-analysis-request.schema.json).

Create a machine-readable analysis request for the selected solver. Include
geometry references, units, coordinates, material data and provenance, load
cases, boundary conditions, defect representation, requested outputs,
acceptance or convergence checks, assumptions, and uncertainties.

Do not perform substitute calculations in prose. A deterministic solver must
produce every reported numerical stiffness, modulus, force, stress, strain,
buckling factor, collapse load, fatigue life, or damage value.

### 8. Validate solver evidence

Before interpretation:

- Confirm the solver completed successfully and identify its version.
- Confirm that the executed inputs match the approved analysis request.
- Check units, coordinate mapping, loads, restraints, and material assignment.
- Check equilibrium, rigid-body motion, convergence, and other method-specific
  validity evidence when applicable.
- Confirm that requested outputs exist and are finite and interpretable.
- Preserve solver warnings, failed checks, and model limitations.

Do not convert a failed, unconverged, or inadequately validated calculation
into an engineering conclusion.

### 9. Interpret and report

Write the final structured handoff against
[structural-mechanics-report.schema.json](references/structural-mechanics-report.schema.json).

Separate the final handoff into:

- `observations`: facts measured or read from inputs.
- `hypotheses`: proposed mechanics mechanisms.
- `solver_results`: deterministic calculations with units and provenance.
- `interpretations`: conclusions supported by those results.
- `uncertainties_and_limitations`: unresolved inputs and model limitations.
- `recommended_next_action`: accept the fidelity, refine it, or escalate.

For each interpretation, link the relevant observation, hypothesis, load case,
solver output, and validation status. State when results apply only locally,
only to a modeled load case, or only within an assumed material regime.

## Analysis gates

- Do not call a defect application-critical unless application requirements are
  complete and deterministic evidence supports the claim.
- Do not claim code or regulatory compliance solely from this analysis.
- Do not use homogenized properties when the modeled region is not shown to be
  representative for the requested response.
- Do not equate an eigenvalue buckling factor with an imperfection-sensitive
  collapse load.
- Do not infer fatigue life without a supported cyclic load history and
  appropriate material damage basis.
- Do not hide conflicts between nominal geometry, as-built geometry, and
  application metadata.
