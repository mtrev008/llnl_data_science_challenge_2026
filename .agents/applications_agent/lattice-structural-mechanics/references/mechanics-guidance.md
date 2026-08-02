# Lattice mechanics reasoning guidance

Use this reference to form testable hypotheses and select evidence. It is not a
substitute for deterministic calculation, material qualification, or an
applicable engineering standard.

For each mechanism, record:

1. Geometry and application evidence inspected.
2. Proposed mechanism and expected direction of response.
3. Load cases and boundary conditions for which it applies.
4. Simplifying assumptions and plausible alternatives.
5. Deterministic method and outputs needed to test it.
6. Conditions that require higher fidelity.

## Beam and frame mechanics

Inspect strut centerlines, lengths, orientations, cross-sections, section
properties, connectivity, joint rigidity, nodal eccentricity, loads, and
restraints.

Use these relationships only for screening and model checks:

- Axial stiffness scales with `E A / L`.
- Bending stiffness scales with `E I / L^3`.
- Torsional stiffness scales with `G J / L`.
- Shear deformation can matter for short, thick members.

Hypothesize how offsets, curvature, section loss, or joint compliance introduce
bending into nominally axial members. Require beam finite-element or higher
evidence for numerical member forces, moments, stresses, or stiffness.

Escalate beyond a beam idealization when cross-sections are not adequately
represented by beam properties, local joint fields control the question,
contact is important, or material or geometric nonlinearity governs.

## Stretch- versus bending-dominated response

Treat deformation mode as dependent on topology, load case, joint behavior, and
boundary conditions rather than as a permanent label inferred from the nominal
cell name.

Inspect connectivity, coordination, triangulation, possible kinematic
mechanisms, member orientation, joint rigidity, defects, and constraints.
Topology may support an initial hypothesis. Prefer beam-model axial and bending
strain-energy fractions to test that hypothesis.

Example: a missing diagonal may convert a locally axial load path into a
bending-sensitive mechanism. Do not generalize a local or single-load-case
classification to the whole lattice without evidence.

## Cellular-solid scaling

Use scaling relationships for trend checks and comparisons:

`E_effective / E_solid ≈ C_E (relative_density)^n`

`strength_effective / strength_solid ≈ C_S (relative_density)^m`

Document the source and applicability of every coefficient and exponent.
Architecture, deformation mode, loading direction, defects, and boundaries can
change them. Never invent coefficients or treat generic scaling as a
specimen-specific calculation.

Use scaling to test physical plausibility, compare regions or specimens, and
identify departures that may arise from defects. Do not use it alone for an
acceptance or criticality decision.

## Elastic stiffness and effective modulus

Distinguish structural stiffness, such as `force / displacement`, from an
effective material property derived from defined nominal stress and strain.

Record the loading direction, reference area, reference or gauge length,
displacement measure, lateral constraint, boundary conditions, and linear
response range. Require solver forces, reactions, and displacements together
with those definitions.

Do not compare effective moduli obtained from incompatible reference dimensions
or boundary conditions. Escalate when nonlinearity, instability, contact, or
localized deformation invalidates a linear effective-property interpretation.

## Strut buckling

Use slenderness and Euler-type relationships only to rank candidates:

`slenderness = K L / r`

`P_cr = pi^2 E I / (K L)^2`

Treat effective length factor `K` as a modeling assumption that depends on
joint and lattice restraint. Account qualitatively for as-built curvature,
eccentricity, section variation, residual stress, and load redistribution.

An isolated-member Euler estimate or eigenvalue buckling factor is not an
imperfection-sensitive lattice collapse load. Escalate to nonlinear analysis
when buckling governs a decision, multiple members interact, or post-buckling
redistribution matters.

## Plastic collapse

Distinguish first yield, plastic-hinge or mechanism formation, peak load,
post-peak response, and global collapse.

Inspect material yield behavior, axial-bending interaction, local section loss,
load-path redundancy, and potential progressive yielding. Use linear elastic
results only to identify high-demand candidates. Require a deterministic
nonlinear material model to claim plastic capacity or collapse load.

Document constitutive data, strain measure, hardening law, geometric
nonlinearity, solver convergence, and the operational collapse criterion.

## Load redistribution

Evaluate redistribution by comparing controlled structural states:

1. Nominal or intact.
2. As-built or defective.
3. Individual defects when interaction is relevant.
4. Combined defects or post-yield/post-buckling states when supported.

Compare member forces and moments, strain energy, reactions, global stiffness,
and neighboring-member demand. Graph centrality and path redundancy may rank
regions but do not establish mechanical force redistribution.

Require identical loads, restraints, units, and response definitions across
comparisons.

## Stress concentration

Distinguish global member demand from local continuum stress or strain. Inspect
joint transitions, fillets, abrupt section changes, pores, cracks, surface
notches, nodal eccentricity, and load introduction.

Use a beam model to locate candidate regions, not to resolve three-dimensional
notch or joint fields. Use a solid local submodel when local stress or strain is
the quantity of interest.

Check geometry resolution, submodel boundary transfer, mesh convergence, and
whether sharp corners or point constraints create singular results. Do not
interpret an unconverged singular peak as a physical finite stress.

## Boundary effects

Separate boundary cells from interior response. Inspect truncated cells, skins,
plates, grips, attachments, load-introduction eccentricity, constrained lateral
motion, and distance from the boundary.

Hypothesize a boundary-layer depth and test whether response converges toward
interior behavior with distance. Do not use disturbed boundary cells to infer
bulk effective properties unless representativeness is demonstrated.

## Defect interaction

Assess whether defects share a load path, joint, orientation, or overlapping
stress and deformation field. Consider separation, alignment with loading,
loss of redundancy, and sequential yielding or buckling.

When possible compare intact, defect-A-only, defect-B-only, and combined-defect
models. Classify the combined response as approximately additive, shielding, or
amplifying only from consistent deterministic results.

Do not assume two spatially close defects interact mechanically without a
load-path or field-based reason.

## Fatigue and crack initiation

Require cyclic loading evidence: range, mean, ratio, cycle count, sequence,
spectrum, and applicable environment. Inspect surface condition, manufacturing
defects, residual stress, local elastic-plastic response, and available material
fatigue data.

Choose a supported stress-life, strain-life, fracture-mechanics, or cumulative
damage basis. A static peak stress alone cannot establish fatigue life.

For every fatigue result, document the material curve or crack-growth data,
corrections, stress or strain extraction method, damage rule, and validity
range. Treat surface-connected defects and bending-sensitive joints as crack
initiation candidates, not confirmed initiation sites without evidence.

## Homogenization and representative volume elements

Use homogenization only when the region adequately represents the architecture
for the requested response and a meaningful separation of scales exists.

Inspect cell count, periodicity or statistical stationarity, anisotropy,
property gradients, boundary-cell fraction, and defect density or clustering.
Test convergence of effective properties as the sampled region grows and
across relevant loading directions.

Require explicit macroscopic boundary conditions and documented volume-averaged
stress and strain definitions. A unit cell, small region, or defect-rich sample
is not automatically a representative volume element.

## Interpretation discipline

- Keep observations, hypotheses, solver results, and interpretations separate.
- Express pre-solver effects directionally and conditionally.
- Attach units, provenance, load case, and validation status to numerical
  evidence.
- Report alternative mechanisms when available evidence cannot distinguish
  them.
- Recommend higher fidelity when the present model omits a mechanism that could
  change the decision.
