Implement a two-agent experimental pipeline that uses a vision-language model to generate and test defect-detection methods from small stacks of consecutive 2D CT slices in a multi-page TIFF file.

The goal is to compare how the information provided to the VLM changes the detection instructions and generated code.

The experiment must compare:

1. VLM receives images only.
2. VLM receives images plus segmentation masks.
3. VLM receives images plus JSON geometry.
4. VLM receives images, segmentation masks, and JSON geometry.
5. VLM receives images plus a relevant research paper.
6. VLM receives all available context.

Implement only:

1. An instruction-generation agent.
2. A code-generation and execution agent.
3. A normal deterministic Python controller that loops through slice stacks and experimental conditions.

The only target defect categories are:

* missing struts
* broken struts
* thin struts
* bent struts

Do not add other defect categories.

# Overall architecture

The workflow must be:

```text
multi-page TIFF
    ↓
construct seven-slice stack
    ↓
build condition-specific context
    ↓
Agent 1 analyzes the stack
    ↓
Agent 1 writes detailed detection instructions
    ↓
Agent 2 receives the same permitted context and Agent 1 instructions
    ↓
Agent 2 generates Python code
    ↓
execute generated code on the stack
    ↓
save measurements, detections, overlays, uncertainty, and diagnostics
    ↓
repeat for all selected stacks and experimental conditions
```

Do not use an AI agent to control the loop.

The experiment loop must be ordinary Python code.

# Input data

The project must support the following configurable inputs:

* one multi-page grayscale TIFF file
* optional binary segmentation TIFF or directory of binary mask images
* optional JSON geometry describing the intended lattice
* optional local PDF or text file containing a relevant research paper
* output directory
* VLM provider
* VLM model
* VLM generation settings
* selected experimental conditions
* selected center slices
* random seed
* timeout settings
* maximum token usage
* voxel spacing when known
* whether JSON geometry is registered to the TIFF

The TIFF currently contains 761 slices.

Do not hardcode file names or paths.

Use a YAML configuration file and allow important options to be overridden through the command line.

# Slice-stack construction

Construct ordered stacks of seven consecutive slices:

```text
[z-3, z-2, z-1, z, z+1, z+2, z+3]
```

Use stride 1 by default.

For 761 slices and zero-based indexing:

* the first valid center slice is 3
* the last valid center slice is 757
* the number of valid stacks is 755

The program must support:

* all valid stacks
* a manually specified list of center slices
* a configurable range of center slices
* random selection of a configurable number of stacks
* reproducible random selection using a seed

Each stack must preserve:

* original grayscale arrays
* original image dimensions
* original slice indices
* slice order
* center-slice identity

Create a labeled contact sheet for VLM input.

The contact sheet must clearly show:

* the seven slices in order
* the absolute slice index of each image
* which slice is the center slice
* no defect labels
* no JSON-derived overlay unless the condition permits JSON
* no segmentation overlay unless the condition permits segmentation

Do not resize images in a way that removes thin-strut details.

Any resizing must:

* preserve aspect ratio
* be configurable
* record the original and resized dimensions
* preserve a high-resolution copy for Agent 2

# Experimental conditions

Each condition must use an independent VLM request with a fresh context.

Do not share conversation history between conditions.

Do not let outputs from one condition appear in another condition's prompt.

## Condition A: images_only

Agent 1 receives only:

* seven consecutive grayscale CT slices
* their slice indices and order
* the center-slice index
* a statement that the images are consecutive CT slices of a lattice structure
* the four defect names

Agent 1 must not receive:

* segmentation masks
* JSON geometry
* expected strut paths
* junction coordinates
* strut IDs
* voxel spacing
* research papers
* outputs from other conditions
* manually written detection rules

## Condition B: images_segmentation

Agent 1 receives:

* seven grayscale CT slices
* corresponding binary segmentation masks
* slice indices and order
* center-slice index
* the four defect names

Agent 1 must not receive:

* JSON geometry
* strut IDs
* expected junctions
* expected strut paths
* research papers
* outputs from other conditions

## Condition C: images_geometry

Agent 1 receives:

* seven grayscale CT slices
* relevant JSON geometry
* available junction records
* available strut records
* strut IDs when present
* endpoint information when present
* coordinate conventions when known
* voxel spacing when known
* whether the geometry is registered to the TIFF
* the four defect names

Agent 1 must not receive:

* segmentation masks
* research papers
* outputs from other conditions

## Condition D: images_segmentation_geometry

Agent 1 receives:

* seven grayscale CT slices
* corresponding binary masks
* relevant JSON geometry
* available strut IDs
* available expected strut paths
* available junction locations
* coordinate and voxel-spacing information
* whether geometry is registered
* the four defect names

Agent 1 must not receive:

* research papers
* outputs from other conditions

## Condition E: images_paper

Agent 1 receives:

* seven grayscale CT slices
* selected excerpts from a relevant local research paper
* paper title and page or section identifiers
* slice indices and order
* center-slice index
* the four defect names

Agent 1 must not receive:

* segmentation masks
* JSON geometry
* strut IDs
* expected strut paths
* outputs from other conditions

## Condition F: full_context

Agent 1 receives:

* seven grayscale CT slices
* corresponding binary masks
* relevant JSON geometry
* available strut IDs
* expected strut and junction information
* coordinate conventions
* voxel spacing
* whether geometry is registered
* selected research-paper excerpts
* paper page or section identifiers
* the four defect names

The configuration must allow any condition to be enabled or disabled.

# Strict context isolation

This is an ablation experiment.

The implementation must enforce strict information isolation.

For every condition:

1. Build a new prompt from scratch.
2. Create a new condition-specific file manifest.
3. Include only files permitted for that condition.
4. Use a fresh VLM request with no prior chat history.
5. Save the exact system prompt, user prompt, images, text context, and manifest.
6. Run a leakage check before calling the VLM.

The leakage checker must fail the run when prohibited information appears.

Examples of prohibited terms and fields include:

* `strut_id` in image-only conditions
* `junction` in image-only conditions
* `geometry` in image-only conditions
* `segmentation` in conditions without segmentation
* `paper` in conditions without paper context
* JSON-derived coordinates in conditions without JSON
* filenames that reveal defect categories
* outputs from previous conditions

Do not use filenames such as:

```text
missing_strut_example.png
broken_slice_100.png
thin_defect_stack.png
```

Use neutral filenames such as:

```text
stack_000100.png
slice_000097.png
mask_000097.png
```

# Agent 1: instruction-generation agent

Agent 1 analyzes one seven-slice stack under one experimental condition.

Agent 1 must not directly act as the final detector.

Its task is to produce precise, executable, image-processing instructions for Agent 2.

Agent 1 must be instructed to:

1. Analyze the seven slices in their correct order.
2. Examine how visible structures appear, disappear, thicken, thin, shift, connect, or disconnect across slices.
3. Identify possible visual evidence for missing, broken, thin, and bent struts.
4. Separate direct observations from assumptions.
5. Avoid claiming that a defect definitely exists without measurable evidence.
6. Avoid inventing coordinates, thresholds, strut IDs, geometry, or paper results.
7. Define measurable operations that Agent 2 can implement in Python.
8. Explain how evidence should be combined across all seven slices.
9. Explain how to handle uncertain or insufficient evidence.
10. State when seven slices are insufficient for a reliable decision.
11. Avoid vague instructions such as:

* detect abnormal shapes
* look for irregularities
* find unusual regions

12. Avoid requiring model training or labeled data.
13. Prefer deterministic or unsupervised image-processing methods.
14. Only use JSON-specific methods when JSON is available.
15. Only use segmentation-specific methods when masks are available.
16. Only use paper-derived methods when paper context is available.
17. Cite the supplied paper page or section when using a paper-derived idea.

Agent 1 may propose measurable operations including:

* foreground occupancy
* grayscale intensity statistics
* local contrast
* connected-component analysis
* connectivity across slices
* component persistence
* gap length
* endpoint connectivity
* cross-sectional area
* equivalent diameter
* local width
* local radius
* distance transform
* skeletonization
* centerline extraction
* centerline continuity
* straight-line fitting
* curvature
* tortuosity
* centerline displacement
* deviation from an expected line
* orientation changes
* shape consistency across slices
* comparison with nearby similar structures
* robust statistical outlier detection
* comparison with expected JSON geometry when available

Agent 1 must not choose arbitrary fixed thresholds without explaining how they are estimated from the current stack or from comparable structures.

Prefer adaptive measurements such as:

* median-based thresholds
* median absolute deviation
* percentile-based thresholds
* local reference comparisons
* robust z-scores
* ratios relative to neighboring struts
* ratios relative to the same structure in nearby slices

# Agent 1 output schema

Agent 1 must return valid JSON with the following structure:

```json
{
  "condition": "images_only",
  "center_slice": 100,
  "observations": [
    {
      "observation_id": "obs_001",
      "description": "Visible structure becomes discontinuous between consecutive slices.",
      "evidence_slices": [99, 100, 101],
      "observation_type": "direct",
      "confidence": 0.75
    }
  ],
  "assumptions": [
    {
      "assumption_id": "assumption_001",
      "description": "Bright segmented regions represent solid lattice material.",
      "required_for_method": true
    }
  ],
  "defect_definitions": {
    "missing": {
      "visual_indicators": [],
      "measurable_tests": [],
      "confounding_cases": []
    },
    "broken": {
      "visual_indicators": [],
      "measurable_tests": [],
      "confounding_cases": []
    },
    "thin": {
      "visual_indicators": [],
      "measurable_tests": [],
      "confounding_cases": []
    },
    "bent": {
      "visual_indicators": [],
      "measurable_tests": [],
      "confounding_cases": []
    }
  },
  "algorithm": {
    "preprocessing": [],
    "candidate_detection": [],
    "feature_measurement": [],
    "unsupervised_reference_estimation": [],
    "classification_logic": [],
    "uncertainty_handling": []
  },
  "required_inputs_for_code": [],
  "expected_outputs": [],
  "paper_citations": [],
  "limitations": [],
  "implementation_instructions": []
}
```

Valid values for `observation_type` are:

* `direct`
* `inferred`
* `paper_derived`
* `geometry_derived`

Validate Agent 1 output using a JSON schema.

When validation fails:

1. Save the raw invalid response.
2. Send one repair request containing:

   * the invalid response
   * the schema
   * validation errors
3. Validate the repaired response.
4. If it still fails, mark the run as failed.
5. Continue to the next stack or condition.

Do not fabricate a replacement response.

Save:

* raw Agent 1 response
* repaired response when applicable
* validated JSON
* exact prompts
* model name
* model parameters
* token usage when available
* request cost when available
* runtime
* condition manifest

# Agent 2: code-generation and execution agent

Agent 2 receives:

* the same seven-slice stack
* only the files and context permitted for the current condition
* Agent 1's validated instructions
* a description of available Python libraries
* a designated output directory

Agent 2 must generate a standalone Python script that attempts to apply Agent 1's instructions to the stack.

The script must attempt to detect evidence of:

* missing struts
* broken struts
* thin struts
* bent struts

Agent 2 must not assume that Agent 1 is correct.

It must explicitly record:

* which instructions were implemented
* which instructions were partially implemented
* which instructions could not be implemented
* missing information
* assumptions added by Agent 2
* generated thresholds
* how each threshold was estimated
* runtime warnings
* errors
* uncertain results

Prefer deterministic and unsupervised techniques using available libraries such as:

* NumPy
* SciPy
* scikit-image
* OpenCV
* tifffile
* Pillow
* pandas
* matplotlib
* networkx when needed

Do not automatically install packages.

When a package is unavailable:

* record the missing dependency
* use a simpler available alternative when reasonable
* otherwise mark the operation as unsupported

Agent 2 must not:

* access the network
* install packages
* execute destructive shell commands
* modify source files
* write outside the designated run directory
* inspect files not listed in the condition manifest
* read outputs from another condition
* fabricate strut IDs

# Generated detector behavior

The generated detector must:

1. Load only the current seven-slice stack and permitted condition files.
2. Preserve the original input files.
3. Perform preprocessing described by Agent 1.
4. identify candidate structures or regions.
5. Compute measurable features.
6. Estimate unsupervised reference values when possible.
7. Assign one of:

   * missing
   * broken
   * thin
   * bent
   * apparently_intact
   * uncertain
8. Save structured results.
9. Save diagnostic overlays.
10. Save intermediate masks and measurements.
11. Explain each classification using computed values.

Because there are no labels, classifications must be framed as candidate detections rather than confirmed ground truth.

# Strut identity handling

For conditions without JSON geometry:

* `strut_id` must be `null`
* use a local candidate ID such as `candidate_001`
* do not invent a strut identity

For conditions with JSON geometry:

* use a real `strut_id` only when the geometry contains it
* use it only when an explicit spatial association is possible
* record the matching method
* record the matching distance or overlap
* record whether registration is known or assumed

When geometry is not registered to the TIFF:

* do not use JSON coordinates as image coordinates
* do not spatially assign detections to strut IDs
* geometry may only be used as structural context
* set `strut_id` to `null` unless a valid registration transform exists

# Agent 2 detection output schema

Agent 2 must produce JSON matching:

```json
{
  "condition": "images_only",
  "center_slice": 100,
  "detections": [
    {
      "candidate_id": "candidate_001",
      "strut_id": null,
      "label": "thin",
      "confidence": 0.68,
      "status": "candidate",
      "evidence_slices": [98, 99, 100, 101],
      "bounding_box": {
        "x_min": 120,
        "y_min": 80,
        "x_max": 170,
        "y_max": 145
      },
      "measurements": {
        "median_width": 3.2,
        "reference_median_width": 5.7,
        "width_ratio": 0.56
      },
      "thresholds": {
        "thin_width_ratio": 0.65
      },
      "threshold_estimation": {
        "thin_width_ratio": "Derived from the lower tail of widths among comparable components in the current stack."
      },
      "reason": "The candidate remains connected but has a substantially smaller local width than comparable structures.",
      "limitations": [
        "Only seven slices were available."
      ]
    }
  ],
  "counts": {
    "missing": 0,
    "broken": 0,
    "thin": 1,
    "bent": 0,
    "apparently_intact": 4,
    "uncertain": 2
  },
  "implemented_instructions": [],
  "partially_implemented_instructions": [],
  "unsupported_instructions": [],
  "agent2_assumptions": [],
  "uncertain_candidates": [],
  "errors": []
}
```

Allowed labels are:

* `missing`
* `broken`
* `thin`
* `bent`
* `apparently_intact`
* `uncertain`

The `status` field must be `candidate`.

Do not describe any result as verified or confirmed.

# Distinguishing defect categories

The generated method should attempt to use the following conceptual distinctions, but it must derive actual measurements from the available data.

## Missing strut candidate

Possible evidence includes:

* little or no material in a region where a strut-like structure is expected
* absence persists across multiple consecutive slices
* no connected component follows the expected path
* geometry-based absence only when registered JSON is available

Do not infer a missing strut solely because one slice has no visible material.

## Broken strut candidate

Possible evidence includes:

* material exists on both sides of a gap
* connected components terminate near each other
* continuity is lost across slices
* no connected path spans the candidate structure
* expected endpoint regions are not connected when registered geometry is available

Distinguish broken from missing by the presence of partial strut material.

## Thin strut candidate

Possible evidence includes:

* continuity remains
* local width, radius, area, or volume is smaller than comparable structures
* reduced thickness persists across multiple slices
* the measurement is an outlier relative to nearby or similarly oriented structures

Do not use a single global hardcoded width threshold.

## Bent strut candidate

Possible evidence includes:

* a connected centerline exists
* the centerline deviates from a straight or expected path
* curvature or tortuosity is unusually large
* the observed path shifts laterally across slices
* the deviation is large relative to comparable structures

Do not classify a naturally tilted or diagonally oriented strut as bent solely because it is not vertical or horizontal.

# Unsupervised reference estimation

There is no labeled data.

The generated detector must estimate reference behavior from the current stack or from other available unlabeled stacks.

Support unsupervised reference approaches such as:

* median feature values
* median absolute deviation
* robust z-scores
* interquartile range
* percentile thresholds
* clustering
* isolation forest
* local neighborhood comparisons
* comparison among structures with similar orientation
* comparison among structures with similar apparent size
* comparison across adjacent slices
* consensus across multiple stacks

Do not assume that the majority of every individual stack is defect-free unless explicitly recorded as an assumption.

Prefer pooling measurements across multiple stacks when the experiment configuration enables it.

Implement two modes:

## Per-stack mode

Reference statistics are estimated only from the current seven-slice stack.

## Global-unlabeled mode

Reference statistics are estimated from a configurable collection of unlabeled stacks.

Global-unlabeled mode must:

1. extract features from selected stacks
2. build a reference feature table
3. compute robust distributions
4. save the reference statistics
5. apply the same reference statistics to all compared conditions when possible

Do not allow condition-specific reference datasets to create an unfair comparison unless clearly recorded.

# Geometry adapter

Inspect the actual JSON file rather than assuming fixed key names.

Implement a geometry adapter that attempts to identify:

* strut records
* junction records
* strut IDs
* junction IDs
* endpoint IDs
* endpoint coordinates
* x, y, and z coordinate ordering
* voxel coordinates
* physical coordinates
* units
* voxel spacing
* orientation metadata
* slice references

Save a normalized geometry file.

Use a normalized structure similar to:

```json
{
  "metadata": {
    "coordinate_order": "xyz",
    "units": "unknown",
    "registered_to_tiff": false
  },
  "junctions": [
    {
      "junction_id": "j_001",
      "x": 0.0,
      "y": 0.0,
      "z": 0.0
    }
  ],
  "struts": [
    {
      "strut_id": "s_001",
      "junction_ids": ["j_001", "j_002"],
      "endpoint_a": [0.0, 0.0, 0.0],
      "endpoint_b": [1.0, 1.0, 1.0]
    }
  ]
}
```

Do not fabricate missing values.

Use `null` for unavailable values.

Add this required configuration field:

```yaml
geometry_registered_to_tiff: false
```

When `false`:

* state clearly in prompts that coordinates are not aligned
* do not create JSON overlays on CT slices
* do not crop geometry by image coordinates
* do not assign detections to strut IDs spatially

When `true`:

* allow geometry near the current seven-slice z-range to be selected
* include only relevant struts and junctions
* record the geometry filtering method

# Segmentation handling

Support:

* a multi-page binary-mask TIFF
* a directory containing one mask per slice
* optional on-the-fly segmentation when no masks are provided

On-the-fly segmentation must be disabled by default.

When enabled, support simple unsupervised methods such as:

* Otsu thresholding
* adaptive thresholding
* percentile thresholding
* morphological cleanup

Do not describe an automatically generated mask as ground truth.

Record:

* segmentation method
* parameters
* foreground fraction
* connected-component count
* warnings for empty or nearly full masks

# Paper handling

Do not ask the VLM to browse the internet.

Accept a local PDF or text file.

For PDFs:

* extract text locally
* preserve page identifiers
* allow configured page ranges
* allow keyword-based excerpt selection
* limit maximum excerpt length
* save extracted text and selected excerpts

Clearly label paper content as external methodological context.

Do not present paper-derived statements as observations from the current CT images.

Agent 1 must include a page or section reference when it uses a paper-derived idea.

If PDF extraction fails:

* record the failure
* continue without paper context only when configured to do so
* otherwise mark paper conditions as failed

# Agent 2 code execution

Run generated code inside a separate output directory for each:

* condition
* center slice
* run attempt

Use a directory structure such as:

```text
outputs/
└── condition_name/
    └── center_000100/
        ├── manifest.json
        ├── prompts/
        ├── agent1/
        ├── agent2/
        ├── generated_code/
        ├── execution/
        ├── measurements/
        ├── overlays/
        └── intermediate/
```

Apply a configurable execution timeout.

Restrict generated code so it cannot:

* access the network
* install packages
* delete files
* write outside the output directory
* execute arbitrary shell commands
* access unrelated repository files
* inspect other condition outputs

At minimum, inspect generated code before execution for dangerous operations such as:

* `subprocess`
* `os.system`
* `shutil.rmtree`
* network libraries
* package installation commands
* writes to absolute paths
* parent-directory traversal
* dynamic execution through `eval` or `exec`

Reject unsafe code and save the rejection reason.

A failure for one stack must not stop the overall experiment.

# Ordinary Python experiment loop

Implement the controller using ordinary Python.

Use logic equivalent to:

```text
for each enabled condition:
    for each selected center slice:
        build the seven-slice stack
        build the permitted condition context
        create the condition manifest
        run the leakage check
        call Agent 1
        validate Agent 1 output
        call Agent 2
        validate and save generated code
        inspect generated code for unsafe operations
        execute generated code
        validate Agent 2 output
        collect diagnostics and comparison metrics
```

Do not create a third AI agent.

# Resume and failure handling

Add resume support.

A condition-stack pair is complete only when it has:

* saved manifest
* Agent 1 validated output
* Agent 2 generated code
* code-execution status
* Agent 2 structured output or a recorded failure

Skip completed runs unless `--force` is supplied.

Record failures independently for:

* stack construction
* missing condition inputs
* leakage check
* VLM request
* invalid Agent 1 JSON
* code generation
* unsafe generated code
* timeout
* runtime exception
* invalid Agent 2 output

Continue after failures.

# Evaluation without labels

There is no labeled dataset.

Do not compute:

* precision
* recall
* F1 score
* accuracy
* confusion matrix
* true positives
* false positives
* false negatives

Instead, compare conditions using label-free measures.

Create one summary row per condition and center-slice stack containing:

* condition
* center slice
* Agent 1 request success
* Agent 1 schema-valid output
* Agent 2 request success
* generated-code safety status
* generated-code execution success
* runtime
* token usage
* estimated request cost
* number of direct observations
* number of inferred observations
* number of assumptions
* number of measurable tests
* number of preprocessing steps
* number of features proposed
* number of classification rules
* number of uncertainty rules
* number of instructions implemented
* number of instructions partially implemented
* number of unsupported instructions
* number of Agent 2 assumptions
* number of detections by category
* number of uncertain candidates
* percentage of candidates classified as uncertain
* number of intermediate outputs generated
* number of runtime warnings
* number of execution errors

# Instruction-quality comparison

Programmatically compare Agent 1 outputs across conditions.

Measure:

* specificity of instructions
* number of executable operations
* number of measurable quantities
* number of adaptive thresholds
* number of unexplained hardcoded thresholds
* number of unsupported assumptions
* whether uncertainty is explicitly handled
* whether cross-slice evidence is used
* whether candidate localization is described
* whether strut-level identity is possible
* whether geometry alignment limitations are acknowledged
* whether paper-derived ideas are cited
* percentage of instructions successfully implemented by Agent 2

Do not use another VLM as the sole evaluator.

Use deterministic text and structure checks where possible.

# Cross-condition consistency

Because no labels exist, implement consistency analysis.

For the same center slice across conditions, compare:

* number of candidates
* spatial overlap of candidates
* predicted category agreement
* confidence differences
* uncertainty differences
* feature differences
* whether JSON context causes strut IDs to be assigned
* whether segmentation changes detected regions
* whether paper context changes algorithm complexity
* whether full context reduces uncertainty

Use bounding-box intersection-over-union or mask overlap when available.

Do not assume that agreement means correctness.

Describe agreement only as cross-condition consistency.

# Repeated-run stability

Support repeated VLM runs using different random seeds or temperatures.

For repeated runs of the same condition and stack, compare:

* Agent 1 instruction overlap
* selected features
* proposed thresholds
* generated algorithm structure
* number and location of candidates
* predicted categories
* confidence values
* uncertainty values

Report instability when results vary substantially.

Do not interpret stability as proof of correctness.

# Visual diagnostic outputs

Save overlays for every successful run.

Overlays should include, when available:

* slice index
* center-slice indicator
* candidate bounding boxes
* candidate masks
* candidate ID
* predicted category
* confidence
* uncertainty marker
* observed centerline
* measured width regions
* detected gaps
* expected JSON path only when permitted and registered
* strut ID only when validly associated

Also create:

* a seven-slice result contact sheet
* per-candidate crops
* feature tables
* distribution plots for widths, areas, curvature, and occupancy
* comparison plots across conditions
* uncertainty summaries

Do not use manual annotations.

# Project structure

Create a project structure similar to:

```text
vlm_defect_ablation/
├── README.md
├── pyproject.toml
├── config.example.yaml
├── schemas/
│   ├── agent1_output.schema.json
│   └── agent2_output.schema.json
├── prompts/
│   ├── agent1_system.txt
│   ├── agent1_user_template.txt
│   ├── agent2_system.txt
│   ├── agent2_user_template.txt
│   └── conditions/
│       ├── images_only.txt
│       ├── images_segmentation.txt
│       ├── images_geometry.txt
│       ├── images_segmentation_geometry.txt
│       ├── images_paper.txt
│       └── full_context.txt
├── src/
│   ├── __init__.py
│   ├── cli.py
│   ├── config.py
│   ├── paths.py
│   ├── tiff_loader.py
│   ├── stack_builder.py
│   ├── contact_sheet.py
│   ├── segmentation_loader.py
│   ├── geometry_adapter.py
│   ├── paper_extractor.py
│   ├── condition_builder.py
│   ├── manifest.py
│   ├── leakage_check.py
│   ├── vlm_client.py
│   ├── agent1.py
│   ├── agent2.py
│   ├── schema_validation.py
│   ├── code_safety.py
│   ├── code_runner.py
│   ├── reference_statistics.py
│   ├── consistency_analysis.py
│   ├── stability_analysis.py
│   ├── reporting.py
│   └── experiment.py
├── tests/
└── outputs/
```

# VLM interface

Keep provider-specific code behind a common interface.

Support at minimum:

```python
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class VLMResponse:
    text: str
    model: str
    usage: dict[str, Any] | None
    cost: float | None
    raw_response: dict[str, Any] | None


class VLMClient:
    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        images: list[Path],
        response_schema: dict[str, Any] | None = None,
        seed: int | None = None,
    ) -> VLMResponse:
        raise NotImplementedError
```

Use environment variables for API keys.

Never commit credentials.

Add a mock VLM client for tests and dry runs.

# Configuration

Create `config.example.yaml` containing fields similar to:

```yaml
data:
  tiff_path: path/to/scan.tif
  segmentation_path: null
  geometry_json_path: null
  paper_path: null
  output_dir: outputs

volume:
  expected_slice_count: 761
  voxel_spacing:
    x: null
    y: null
    z: null

stacks:
  size: 7
  stride: 1
  center_slices: []
  random_count: null
  random_seed: 42
  preserve_full_resolution: true
  contact_sheet_max_dimension: 2048

geometry:
  registered_to_tiff: false
  transform_path: null

paper:
  pages: []
  keywords: []
  maximum_excerpt_characters: 12000

experiment:
  conditions:
    - images_only
    - images_segmentation
    - images_geometry
    - images_segmentation_geometry
    - images_paper
    - full_context
  repeats: 1
  force: false
  continue_on_error: true
  reference_mode: per_stack

vlm:
  provider: configurable
  model: configurable
  temperature: 0.2
  max_tokens: 6000
  timeout_seconds: 180

execution:
  timeout_seconds: 120
  allow_network: false
  allow_package_installation: false
  allow_shell_commands: false
```

Validate the configuration before running.

Skip conditions whose required inputs are unavailable, but report exactly why they were skipped.

# Command-line interface

Provide commands similar to:

```bash
python -m src.cli inspect-data --config config.yaml
python -m src.cli build-stacks --config config.yaml
python -m src.cli inspect-geometry --config config.yaml
python -m src.cli extract-paper --config config.yaml
python -m src.cli run-agent1 --config config.yaml
python -m src.cli run-agent2 --config config.yaml
python -m src.cli run-experiment --config config.yaml
python -m src.cli analyze-consistency --config config.yaml
python -m src.cli analyze-stability --config config.yaml
python -m src.cli create-report --config config.yaml
```

Support a small initial experiment:

```bash
python -m src.cli run-experiment \
  --config config.yaml \
  --center-slices 100 200 300 \
  --conditions images_only images_segmentation full_context
```

Support a single-stack debug run:

```bash
python -m src.cli run-experiment \
  --config config.yaml \
  --center-slices 100 \
  --conditions images_only \
  --force
```

# Tests

Add unit tests for:

* loading the multi-page TIFF
* confirming the expected number of slices
* creating seven-slice stacks
* boundary handling
* producing 755 valid stacks from 761 slices
* preserving slice order
* contact-sheet labels
* condition-specific file inclusion
* prohibited-context leakage
* independent prompts across conditions
* segmentation loading
* geometry normalization
* unregistered-geometry behavior
* paper excerpt extraction
* Agent 1 schema validation
* Agent 1 repair behavior
* Agent 2 schema validation
* unsafe generated-code rejection
* path traversal rejection
* execution timeout
* missing dependency handling
* failure isolation
* resume behavior
* mocked VLM requests
* repeated-run stability calculations
* bounding-box consistency calculations
* no labeled-data requirements

Unit tests must not require live API calls.

# README requirements

The README must explain:

* the purpose of the experiment
* the two-agent architecture
* why no orchestrator agent is used
* the six context conditions
* how seven-slice stacks are constructed
* why seven slices provide only local evidence
* how to configure TIFF, masks, JSON, and paper inputs
* how context leakage is prevented
* how Agent 1 differs from Agent 2
* how generated code is restricted
* how unsupervised reference statistics are estimated
* how conditions are compared without labels
* why agreement does not prove correctness
* why stability does not prove correctness
* how to inspect all prompts and manifests
* how to run a three-stack test
* how to resume failed experiments
* known limitations of VLM-generated image-processing methods

# Implementation order

Implement in this order:

1. Inspect the existing repository and input-file formats.
2. Create the project structure.
3. Implement configuration loading and validation.
4. Implement TIFF loading.
5. Implement seven-slice stack generation.
6. Implement contact-sheet generation.
7. Implement segmentation loading.
8. Implement JSON geometry normalization.
9. Implement paper extraction.
10. Implement condition-specific context building.
11. Implement manifests and leakage checks.
12. Implement the VLM client interface and mock client.
13. Implement Agent 1 prompts and schema validation.
14. Implement Agent 2 prompts and schema validation.
15. Implement generated-code safety checks.
16. Implement restricted code execution.
17. Implement the ordinary Python experiment loop.
18. Implement resume and failure isolation.
19. Implement label-free comparison metrics.
20. Implement cross-condition consistency analysis.
21. Implement repeated-run stability analysis.
22. Implement reports and visual diagnostics.
23. Add unit tests.
24. Write the README.
25. Run all tests.
26. Perform a complete dry run using mocked VLM responses.

Begin by inspecting the repository and the actual structure of the TIFF, optional segmentation data, JSON file, and paper files.

Do not assume that optional files exist.

Do not alter unrelated repository files.

At completion, report:

* files created
* files modified
* tests run
* tests passed
* tests failed
* dry-run results
* unavailable optional inputs
* unresolved assumptions
* any safety limitations
* the exact command for a small live experiment using three center slices
