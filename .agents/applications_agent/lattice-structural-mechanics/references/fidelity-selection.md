# Analysis fidelity selection

Select the lowest-cost deterministic method that can represent the suspected
mechanism and support the required engineering decision. Fidelity is driven by
the question, not by which solver happens to be available.

## Selection record

For every selection, record:

- Decision objective and required confidence.
- Application-requirements status.
- Candidate governing mechanisms.
- Spatial scale: lattice, region, member, joint, pore, or crack.
- Required outputs and acceptance criteria.
- Relevant linearity, material, geometry, and damage assumptions.
- Selected method and required solver capability.
- Why each lower fidelity is inadequate.
- Why each higher fidelity is unnecessary at this stage.
- Validation evidence and escalation triggers.

If no available method can support the decision, return `unsupported` rather
than selecting an inadequate solver.

## Decision sequence

1. Use graph screening when topology and relative risk are sufficient.
2. Use beam finite elements when global response or member forces and moments
   are required and members remain adequately beam-like.
3. Use a solid local submodel when three-dimensional joint, notch, pore, or
   local stress and strain fields control the question.
4. Use nonlinear buckling or collapse analysis when instability, yielding,
   large deformation, contact, or post-peak behavior controls the decision.
5. Use a fatigue or damage model when cyclic degradation, crack initiation, or
   crack growth is the requested outcome.

These methods may be staged. A later method may consume validated outputs from
an earlier method, but it must preserve provenance and verify transferred
quantities.

## Fidelity 1: Fast graph-based screening

### Appropriate questions

- Is the lattice connected between required boundaries?
- Which nodes or members are topologically important?
- Where are redundant or disrupted load paths?
- Which defects are clustered or share a candidate load path?
- Which members are geometrically slender or poorly aligned with loading?
- Which regions should be prioritized for deterministic mechanical modeling?

### Required inputs

- Node coordinates and member connectivity.
- Units and coordinate system.
- Boundary-node or attachment-region definitions.
- Load direction or load-region context.
- Member dimensions when slenderness or weighted screening is requested.
- Defect labels and geometry provenance.

### Permitted outputs

- Connectivity and disconnected-component results.
- Coordination, path, redundancy, and centrality measures.
- Orientation and boundary-distance measures.
- Geometric slenderness and idealized buckling rankings.
- Relative screening scores and prioritized regions.

Label these as screening indicators rather than force, stress, stiffness,
capacity, life, or safety margin.

### Cannot adequately represent

- Joint rigidity and continuum stress fields.
- Physical force redistribution without a mechanical formulation.
- Local three-dimensional geometry.
- Material yielding, large deformation, contact, or post-buckling response.
- Fatigue life or crack evolution.

### Validation

- Confirm valid node identifiers and finite coordinates.
- Confirm member endpoints exist and reject invalid self-loops or duplicates
  unless intentionally represented.
- Confirm boundary sets and coordinate mapping.
- Check graph invariants on small analytical fixtures.
- Report sensitivity to uncertain connectivity or defect classification.

### Escalate when

- Numerical stiffness, force, stress, strain, or capacity is required.
- Joint or section mechanics influence the conclusion.
- Several mechanically plausible paths cannot be distinguished topologically.
- Screening could change an acceptance or safety-critical decision.

## Fidelity 2: Beam-element finite-element model

### Appropriate questions

- What are global elastic stiffness and displacement?
- How are axial forces, shears, moments, and torsion distributed?
- Does deformation appear predominantly axial or bending?
- How do as-built defects change member demand or load redistribution?
- Which members are candidates for elastic buckling or local solid analysis?
- What boundary forces or displacements should drive a submodel?

### Required inputs

- Connected centerline geometry with section orientation where needed.
- Cross-sectional area, moments of inertia, torsion constant, or reproducible
  rules for deriving them.
- Elastic material properties and provenance.
- Loads, constraints, attachments, and coordinate definitions.
- Joint representation: rigid, released, compliant, offset, or otherwise
  explicitly modeled.
- Beam theory and element formulation.

### Permitted outputs

- Linear global displacement and reaction response.
- Member forces, moments, strain energy, and beam-theory stress recovery.
- Structural stiffness and consistently defined effective elastic properties.
- Axial-versus-bending energy comparisons.
- Elastic eigenvalue or Euler-type buckling indicators when explicitly solved.

### Cannot adequately represent

- Resolved three-dimensional joint, notch, pore, or crack fields.
- Local warping outside the selected beam formulation.
- Imperfection-sensitive collapse from a linear or eigenvalue-only solution.
- Plastic progression, contact, or large deformation in a linear model.
- Fatigue life without a separate supported damage model.

### Validation

- Check units, material and section assignments, and local element axes.
- Detect rigid-body modes and unintended mechanisms.
- Confirm reaction equilibrium and energy consistency.
- Check discretization sensitivity where member subdivision matters.
- Compare simple members and frames with analytical solutions.
- Preserve solver warnings and conditioning information.

### Escalate when

- Local joint or defect fields determine the decision.
- Cross-sections or joints violate beam assumptions.
- Yielding, instability, contact, or large rotation is plausible.
- Fatigue is governed by a local feature not resolved by beam recovery.

## Fidelity 3: Solid-element local submodel

### Appropriate questions

- What local stress or strain field develops at a joint or attachment?
- How does a pore, notch, surface defect, or section transition affect demand?
- Where is a credible crack-initiation hot spot?
- Can a beam-model result be refined around a candidate critical region?

### Required inputs

- Resolved local solid geometry with documented image or mesh resolution.
- Constitutive material data appropriate to the requested response.
- Loads or boundary fields transferred from a validated global model, or
  independently justified local boundary conditions.
- Submodel extent, interface definition, and coordinate registration.
- Mesh controls appropriate to curvature and defect scale.

### Permitted outputs

- Local continuum stress and strain fields.
- Stress or strain concentration measures with explicit reference values.
- Local deformation and interface reactions.
- Candidate hot-spot locations.

### Cannot adequately represent

- Whole-lattice response unless the whole lattice is modeled.
- Valid local fields when the submodel boundary is too close to the feature.
- Finite peak stress at an idealized mathematical singularity.
- Collapse or fatigue life unless the corresponding nonlinear or damage
  formulation is included and validated.

### Validation

- Check geometry fidelity and mesh quality.
- Demonstrate mesh convergence using a stable quantity of interest.
- Check submodel boundary sensitivity and transferred-field consistency.
- Confirm interface reaction or energy agreement with the global model.
- Identify singularities and avoid reporting unconverged nodal peaks.

### Escalate when

- Material nonlinearity or large deformation changes the local field.
- Crack growth, progressive damage, contact, or collapse is required.

## Fidelity 4: Nonlinear buckling or collapse simulation

### Appropriate questions

- What is the imperfection-sensitive instability load?
- How do yielding and geometric nonlinearity interact?
- What sequence of member buckling, yielding, contact, and redistribution
  produces peak load or collapse?
- What is the post-buckling or post-yield response within the modeled range?

### Required inputs

- Valid beam or solid model appropriate to the governing mechanism.
- Nonlinear constitutive data and applicability range.
- Geometric imperfections with measured or justified amplitude and shape.
- Large-deformation formulation and load-control strategy.
- Contact definitions when relevant.
- Operational definitions for instability, peak load, and collapse.

### Permitted outputs

- Nonlinear load-displacement response.
- Onset and sequence of modeled instability or yielding.
- Peak modeled load and stated collapse indicator.
- Redistribution and post-critical response supported by convergence evidence.

### Cannot adequately represent

- Unmodeled manufacturing damage, residual stress, fracture, or material
  degradation.
- Unique collapse capacity when imperfection uncertainty is not explored.
- Physical response beyond the constitutive and numerical validity range.

### Validation

- Check solution-path and step-size sensitivity.
- Demonstrate equilibrium and convergence through the response of interest.
- Run imperfection-amplitude and shape sensitivity studies.
- Check mesh or discretization sensitivity.
- Distinguish numerical termination from physical collapse.
- Compare limiting cases with analytical, experimental, or benchmark evidence.

### Escalate or qualify when

- Results are highly imperfection-sensitive without measured bounds.
- Fracture or cyclic damage, rather than instability or plasticity, controls.
- Convergence cannot be maintained through the required decision point.

## Fidelity 5: Fatigue or damage model

### Appropriate questions

- Where is cyclic crack initiation most plausible?
- What damage accumulates under a defined load history?
- What relative or absolute fatigue life is supported by available data?
- How might an existing crack propagate under the modeled conditions?

### Required inputs

- Validated cyclic load history, range, mean, ratio, count, and sequence.
- Local stress or strain history from an appropriate structural model.
- Supported material fatigue, strain-life, or crack-growth data.
- Surface, size, environment, manufacturing, residual-stress, and mean-stress
  corrections when applicable.
- Initial flaw definition for fracture-mechanics analysis.

### Permitted outputs

- Hot-spot ranking.
- Damage fraction under a stated accumulation rule.
- Cycles to initiation within a documented model range.
- Crack-growth increments or remaining-life estimate when fracture inputs are
  sufficient.

### Cannot adequately represent

- Fatigue life from static loading alone.
- Unqualified material or surface behavior outside source-data validity.
- Crack initiation and propagation as the same physical event without an
  explicit combined model.

### Validation

- Confirm load-history and material-data compatibility.
- Check stress or strain extraction and cycle counting.
- Document every correction and damage rule.
- Perform sensitivity to uncertain load and material inputs.
- Compare against representative coupon, component, or published benchmark
  evidence when available.

## Coupled and staged analyses

Use staged analyses when different scales or mechanisms require different
representations:

- Graph screening may prioritize regions for beam modeling.
- Beam analysis may supply forces or displacements to a solid submodel.
- Beam or solid analysis may supply stress or strain histories to fatigue.
- An eigenmode may seed geometric imperfections in a nonlinear analysis.
- Nonlinear analysis may identify load histories for progressive-damage work.

For every transfer:

1. Record source model, result, load case, units, and coordinate transformation.
2. Confirm the receiving model represents the transferred quantity.
3. Check equilibrium or energy consistency when applicable.
4. Test sensitivity to transfer boundaries and interpolation.
5. Do not give the staged result greater validity than its least-supported
   upstream input.

## Selection examples

- Use graph screening to rank missing struts across a large scan when the
  objective is triage, not capacity.
- Use beam finite elements to quantify elastic stiffness loss and member-demand
  redistribution caused by those missing struts.
- Add a solid local submodel when a joint pore or notch controls local stress.
- Add nonlinear collapse analysis when slender compression members, yielding,
  or post-buckling behavior governs capacity.
- Add fatigue or damage analysis when complete cyclic service requirements and
  suitable material data exist.

If application requirements are incomplete, restrict the selected analysis to
application-independent characterization or clearly provisional screening.
