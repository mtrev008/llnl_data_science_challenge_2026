Implement a two-agent workflow for automatically designing a Python method that detects missing and broken struts in 2D CT slices of a lattice structure.

The motivation is to reduce the need for researchers to manually inspect CT images and manually design defect-detection algorithms.

The system must use:

1. Agent 1: a vision-language model that visually inspects one representative 2D CT slice.
2. Agent 2: a Codex subagent that does not visually inspect the slice and does not require vision capabilities.
3. A normal Python controller that runs the generated detector on selected slices from a multi-page TIFF file.

Only detect:

* missing struts
* broken struts

Do not include thin struts, bent struts, porosity, surface roughness, junction defects, or other defect categories.

Do not implement an orchestrator agent.

# Core workflow

The workflow must be:

```text
One representative 2D CT slice
        ↓
Agent 1 visually examines the slice
        ↓
Agent 1 produces structured observations and algorithm-design instructions
        ↓
Agent 2 receives:
    - Agent 1's textual and structured output
    - an uploaded relevant research paper as a local PDF
    - information about available Python libraries and dataset format
        ↓
Agent 2 generates a reusable Python detection script
        ↓
The script is executed on selected slices from the TIFF file
        ↓
The script saves missing-strut and broken-strut candidates,
measurements, masks, and visual overlays
```

Agent 2 must not receive the representative slice as an image.

Agent 2 may receive only textual information derived from Agent 1, the local research paper, and technical information about the input-file formats and execution environment.

The generated Python detector will receive CT slices when it is executed. This is separate from Agent 2 receiving an image during code generation.

# Purpose of Agent 1

Agent 1 replaces the initial manual image examination normally performed by a researcher.

Agent 1 receives exactly one representative grayscale CT slice extracted from the multi-page TIFF file.

Agent 1 must:

1. Visually inspect the lattice structure in the slice.
2. Describe the repeating geometric pattern.
3. Describe the appearance of visible struts and junctions.
4. Identify visual evidence that could indicate a missing strut.
5. Identify visual evidence that could indicate a broken strut.
6. Describe how missing and broken struts may differ visually.
7. Identify repeating spatial relationships that could help infer where struts are expected.
8. Identify measurable image properties that a Python script could calculate.
9. Translate visual observations into detailed image-processing instructions.
10. State ambiguities and limitations of using one 2D slice.
11. Avoid writing Python code.
12. Avoid making final defect classifications for the dataset.
13. Avoid inventing exact thresholds without explaining how they could be estimated adaptively.
14. Avoid relying on neighboring slices.
15. Focus only on information visible in the supplied slice.

Agent 1 must not receive the research paper.

This separation is intentional:

* Agent 1 contributes image-specific visual observations.
* Agent 2 combines those observations with methods from the research paper.

# Agent 1 input

Agent 1 receives:

* one grayscale CT slice
* its slice index
* original image width and height
* a statement that the image is one cross-sectional CT slice of a lattice structure
* a statement that the desired detector should identify missing and broken struts
* no research paper
* no neighboring slices
* no manual labels
* no ground-truth defect locations

Use a high-resolution version of the slice.

Do not reduce the resolution enough to remove thin lattice features or small gaps.

# Agent 1 instructions

Use an Agent 1 system prompt equivalent to:

```text
You are a scientific image-analysis method designer.

You are examining one 2D grayscale CT slice of a repeating lattice
structure. Researchers want to avoid manually examining images and manually
designing a defect-detection algorithm.

Your task is to inspect the supplied image and produce precise observations and
implementation instructions that another non-vision coding agent can use to
write a Python detector.

The detector must identify only:

1. missing-strut candidates
2. broken-strut candidates

Do not write code.

Do not claim that a defect is confirmed.

Describe what is visibly present in the image, how the lattice repeats, how
intact struts appear, where material normally connects, and which measurable
properties could distinguish absence from a localized break.

The coding agent will not see the image. Therefore, your description must be
specific enough for it to design the algorithm without visual access.

Separate direct visual observations from inferred structural assumptions.

Do not invent coordinates, measurements, thresholds, or defect locations.

When suggesting a threshold, explain how it should be estimated adaptively from
the image or from the population of detected structures.

Only discuss the supplied 2D slice. Do not assume access to neighboring slices.
```

# Agent 1 output

Require Agent 1 to return valid JSON.

Use the following structure:

```json
{
  "slice_index": 100,
  "image_description": {
    "overall_structure": "",
    "foreground_appearance": "",
    "background_appearance": "",
    "contrast_characteristics": "",
    "noise_or_artifacts": []
  },
  "lattice_pattern": {
    "repeating_pattern_description": "",
    "apparent_strut_orientations": [],
    "junction_appearance": "",
    "approximate_symmetries": [],
    "how_expected_strut_locations_may_be_inferred": []
  },
  "intact_strut_observations": [
    {
      "observation_id": "intact_001",
      "description": "",
      "measurable_properties": []
    }
  ],
  "missing_strut_observations": {
    "visual_indicators": [],
    "distinction_from_background": [],
    "measurable_tests": [],
    "possible_confounders": []
  },
  "broken_strut_observations": {
    "visual_indicators": [],
    "fragment_patterns": [],
    "measurable_tests": [],
    "possible_confounders": []
  },
  "missing_vs_broken": {
    "key_distinctions": [],
    "ambiguous_cases": [],
    "recommended_uncertainty_rules": []
  },
  "recommended_processing_pipeline": {
    "preprocessing": [],
    "foreground_segmentation": [],
    "lattice_pattern_estimation": [],
    "expected_strut_location_estimation": [],
    "component_and_connectivity_analysis": [],
    "missing_candidate_logic": [],
    "broken_candidate_logic": [],
    "adaptive_threshold_estimation": [],
    "postprocessing": [],
    "required_diagnostics": []
  },
  "recommended_measurements": [
    {
      "measurement_name": "",
      "purpose": "",
      "calculation_description": "",
      "relevant_to": [
        "missing",
        "broken"
      ]
    }
  ],
  "direct_observations": [],
  "inferred_assumptions": [],
  "limitations": [],
  "instructions_for_coding_agent": []
}
```

Validate Agent 1's response against a JSON schema.

If validation fails:

1. Save the invalid response.
2. Make one repair request containing the response, schema, and validation errors.
3. Validate the repaired response.
4. If it remains invalid, mark Agent 1 as failed.
5. Do not fabricate missing content.

Save:

* the representative input slice
* exact Agent 1 system prompt
* exact Agent 1 user prompt
* raw response
* repaired response if applicable
* validated JSON
* model name
* model settings
* token usage
* runtime
* request cost when available

# Research-paper input

Agent 2 receives an uploaded relevant research paper as a local PDF.

Do not ask either agent to browse the internet.

Implement local PDF text extraction.

The paper-processing component must:

1. Accept a configurable PDF path.
2. Extract text locally.
3. Preserve page numbers.
4. Save the full extracted text.
5. Select relevant excerpts using configurable keywords.
6. Allow explicit page ranges.
7. Limit the total excerpt length.
8. Preserve page references in every excerpt.
9. Report PDF extraction failures.
10. Avoid sending the entire paper when only selected sections are relevant.

Default paper-excerpt keywords should include:

```text
lattice
strut
missing strut
broken strut
defect
computed tomography
CT
segmentation
connectivity
connected component
image processing
additive manufacturing
```

The configuration must support:

```yaml
paper:
  path: path/to/paper.pdf
  pages: []
  keywords:
    - lattice
    - strut
    - missing strut
    - broken strut
    - computed tomography
    - segmentation
    - connectivity
  maximum_excerpt_characters: 16000
```

Clearly identify paper excerpts as external methodological context.

Do not present paper claims as observations from the representative CT slice.

# Purpose of Agent 2

Agent 2 is a Codex subagent.

Agent 2 does not need vision capabilities.

Agent 2 must not receive the representative CT slice as an image.

Agent 2 receives:

* Agent 1's validated JSON observations
* selected research-paper excerpts with page references
* a description of the multi-page TIFF input
* expected image data types and dimensions
* available Python libraries
* the designated project and output directories
* requirements for the generated detector

Agent 2 must use Agent 1's observations as the image-specific design input.

Agent 2 must use the paper as methodological support.

Agent 2 must generate a reusable Python script rather than code specialized to only the representative slice.

# Codex subagent configuration

Create a Codex subagent definition similar to:

```toml
name = "strut_detector_builder"
description = "Generates and tests a reusable Python detector for missing and broken lattice struts using VLM observations and a local research paper."
sandbox_mode = "workspace-write"
```

Give the subagent access only to:

* Agent 1's validated JSON
* extracted paper excerpts
* TIFF metadata
* the designated detector-development directory
* a small configurable development subset of TIFF slices for executing and debugging the generated script

The Codex subagent may access CT slices as ordinary numerical data while testing the generated script.

It must not be expected to visually interpret them.

It should use programmatic measurements and generated diagnostic images to debug the implementation.

Do not give the subagent unrelated repository files unless needed.

# Agent 2 prompt

Use a prompt equivalent to:

```text
You are the coding agent responsible for implementing a reusable Python
detector for missing and broken struts in individual 2D CT slices of a lattice
structure.

You do not have vision capabilities and should not attempt to interpret the
representative CT image directly.

A vision-language model has already examined one representative slice and
produced structured observations and image-processing instructions. Treat those
observations as the image-specific design input.

You are also given excerpts from a relevant research paper. Use the paper as
methodological context. Preserve page references in your implementation notes
when a paper-derived method influences the algorithm.

Create a reusable Python script named detector.py.

The script must process individual slices from a multi-page TIFF file and
identify only:

1. possible missing struts
2. possible broken struts

Do not implement thin-strut or bent-strut detection.

Do not require labeled data or supervised training.

Translate the VLM observations and paper methods into measurable,
deterministic, or unsupervised image-processing operations.

Do not merely describe the code. Write the script, execute it on the supplied
development slices, inspect programmatic outputs, repair runtime errors, and
save the final working version.

Do not hardcode defect coordinates from the representative slice.

The detector must generalize to other slices from the same TIFF volume.

Record which VLM instructions and paper-derived methods were implemented,
modified, or rejected.

When evidence is insufficient, return an uncertain candidate rather than
forcing a missing or broken label.
```

# Agent 2 implementation requirements

Agent 2 must create:

```text
detector.py
```

The script must be reusable across slices.

It must accept arguments similar to:

```bash
python detector.py \
  --tiff-path path/to/scan.tif \
  --slice-index 100 \
  --output-dir outputs/slice_000100
```

Also support a range:

```bash
python detector.py \
  --tiff-path path/to/scan.tif \
  --slice-start 100 \
  --slice-end 120 \
  --output-dir outputs/range_100_120
```

And a list:

```bash
python detector.py \
  --tiff-path path/to/scan.tif \
  --slice-indices 100 150 200 \
  --output-dir outputs/selected
```

# Generated detector responsibilities

The generated script must:

1. Load a selected 2D slice from the multi-page TIFF.
2. Preserve the original grayscale image.
3. Normalize intensity without discarding the original values.
4. Segment probable lattice material using an unsupervised method.
5. Clean the mask using configurable morphological operations.
6. Detect connected components.
7. Estimate repeating lattice structure from visible components when possible.
8. Estimate likely strut orientations.
9. Estimate expected strut locations using image repetition, symmetry, junction patterns, or other methods derived from Agent 1's observations.
10. Detect localized connectivity gaps.
11. Distinguish possible missing struts from possible broken struts.
12. Save all computed measurements.
13. Save diagnostic overlays.
14. Return uncertain when the available evidence is insufficient.

Do not use hardcoded image coordinates.

Do not require manual annotations.

Do not require defect labels.

# Missing-strut candidate logic

A missing-strut candidate should represent a location where the inferred lattice pattern suggests a strut should exist, but little or no corresponding foreground material is detected.

Possible measurements include:

* foreground occupancy in an expected strut corridor
* difference from corresponding repeated lattice positions
* absence between expected junction locations
* missing edge in an inferred lattice graph
* low line-response strength along an expected orientation
* lack of connected material through an expected region

The detector must not classify any arbitrary empty background region as a missing strut.

A missing candidate requires an inferred expected strut location.

If no expected location can be inferred confidently, return uncertain.

# Broken-strut candidate logic

A broken-strut candidate should represent a location where partial strut material is present but continuity is interrupted by a localized gap.

Possible measurements include:

* two nearby aligned component fragments
* opposing component endpoints
* short gap between fragments
* similar orientation on each side of the gap
* material present along most of an inferred strut corridor
* failed connectivity between otherwise compatible fragments
* skeleton endpoints separated by a small background region

Distinguish broken from missing using the presence of partial material.

A possible conceptual distinction is:

```text
missing:
expected strut corridor has very little material across most of its length

broken:
expected strut corridor contains substantial partial material but includes a
localized interruption
```

Do not use those definitions as fixed thresholds.

Estimate thresholds adaptively.

# Adaptive and unsupervised thresholds

There is no labeled data.

Do not train a supervised classifier.

Do not use fixed thresholds unless they are exposed in configuration and justified.

Prefer:

* Otsu thresholding
* adaptive thresholding
* percentile-based thresholding
* robust medians
* median absolute deviation
* interquartile range
* robust z-scores
* clustering
* local comparisons
* component-size distributions
* corridor occupancy distributions
* gap-length distributions
* orientation-specific comparisons

Record every threshold and how it was estimated.

Do not assume every unusual structure is defective.

# Expected algorithm components

Agent 2 should decide the final implementation based on Agent 1 and the paper, but the script may use:

* grayscale normalization
* denoising
* contrast enhancement
* Otsu or adaptive segmentation
* morphological cleanup
* connected-component analysis
* skeletonization
* skeleton endpoint detection
* line or ridge detection
* Hough transforms
* graph construction
* junction detection
* orientation clustering
* template-free lattice-period estimation
* autocorrelation
* Fourier-domain periodicity estimation
* symmetry analysis
* component-pair alignment
* gap measurement
* occupancy measurement
* robust outlier detection

Do not force all techniques into the implementation.

Use only techniques justified by Agent 1's observations, the paper, or empirical programmatic diagnostics.

# Detector output schema

For each processed slice, save JSON similar to:

```json
{
  "slice_index": 100,
  "segmentation": {
    "method": "otsu",
    "threshold": 0.42,
    "foreground_fraction": 0.18
  },
  "lattice_estimation": {
    "success": true,
    "estimated_orientations_degrees": [45.0, 135.0],
    "estimated_periodicity_pixels": 36.4,
    "method": "autocorrelation_and_line_orientation"
  },
  "detections": [
    {
      "candidate_id": "candidate_001",
      "label": "possible_broken",
      "confidence": 0.71,
      "bounding_box": {
        "x_min": 120,
        "y_min": 80,
        "x_max": 170,
        "y_max": 140
      },
      "measurements": {
        "corridor_occupancy": 0.68,
        "largest_gap_pixels": 9.0,
        "fragment_alignment_degrees": 4.2,
        "endpoint_distance_pixels": 10.1
      },
      "reason": "Two aligned foreground fragments occupy most of the inferred strut corridor but are separated by a localized gap.",
      "status": "unverified_candidate"
    }
  ],
  "counts": {
    "possible_missing": 0,
    "possible_broken": 1,
    "uncertain": 2
  },
  "warnings": [],
  "errors": []
}
```

Allowed labels are:

* `possible_missing`
* `possible_broken`
* `uncertain`

Do not use:

* confirmed_missing
* confirmed_broken
* ground_truth
* true_positive
* false_positive

There is no labeled data.

# Required script outputs

For each processed slice, save:

* original grayscale slice
* normalized slice
* segmentation mask
* cleaned mask
* connected-component visualization
* skeleton image if used
* inferred lattice structure visualization
* candidate bounding-box overlay
* candidate mask overlay
* detected endpoints or gaps if used
* measurement CSV
* detection JSON
* execution log
* warnings and errors

Overlays should contain:

* slice index
* candidate ID
* possible missing, possible broken, or uncertain
* confidence
* relevant measurement values

# Agent 2 development and testing

Provide Agent 2 with a configurable small subset of slices for implementation testing.

For example:

```yaml
development:
  slice_indices:
    - 100
    - 200
    - 300
```

These are unlabeled development slices.

They must not be described as intact or defective.

Agent 2 should:

1. Generate `detector.py`.
2. Run it on the development slices.
3. Fix syntax and runtime errors.
4. Check that output files are created.
5. Check for empty or full segmentation masks.
6. Check for unreasonable component counts.
7. Check for invalid bounding boxes.
8. Check for NaN or infinite measurements.
9. Save implementation notes.
10. Avoid tuning against manually known defect locations.

Agent 2 does not need to visually inspect output overlays.

The overlays are intended for later researcher review and auditing.

# Agent 2 implementation report

Require Agent 2 to save:

```json
{
  "implemented_vlm_instructions": [],
  "modified_vlm_instructions": [],
  "unsupported_vlm_instructions": [],
  "implemented_paper_methods": [
    {
      "description": "",
      "paper_page": "",
      "implementation_location": ""
    }
  ],
  "rejected_paper_methods": [],
  "added_assumptions": [],
  "threshold_methods": [],
  "known_limitations": [],
  "development_run_results": []
}
```

# Controller responsibilities

Implement a normal Python controller.

Do not use a third AI agent.

The controller must:

1. Load the configuration.
2. Extract the representative TIFF slice.
3. Save the slice in the Agent 1 input directory.
4. Call Agent 1 with the slice.
5. Validate Agent 1's JSON.
6. Extract relevant text from the local research-paper PDF.
7. Build Agent 2's text-only input package.
8. Verify that no image is included in the Agent 2 prompt or attachments.
9. Launch the Codex subagent.
10. Instruct it to generate and test `detector.py`.
11. Save all generated code and implementation notes.
12. Optionally run the completed detector across selected TIFF slices.
13. Record failures without deleting prior outputs.

# Information boundaries

Enforce the following boundaries:

## Agent 1 receives

* one representative CT slice
* slice metadata
* target categories: missing and broken

## Agent 1 does not receive

* paper
* neighboring slices
* labels
* researcher annotations
* Agent 2 outputs

## Agent 2 receives

* Agent 1's validated textual JSON
* paper excerpts
* TIFF metadata
* dataset paths for script execution
* available-library information
* development slice indices
* project requirements

## Agent 2 does not receive

* the representative slice as a prompt image
* manual labels
* defect coordinates
* researcher-written image observations
* ground truth

Agent 2 may load TIFF slices programmatically when executing and debugging the generated script.

This does not mean Agent 2 visually inspects them.

# Project structure

Create a structure similar to:

```text
vlm_strut_method_generation/
├── README.md
├── pyproject.toml
├── config.example.yaml
├── schemas/
│   ├── agent1_observations.schema.json
│   └── detector_output.schema.json
├── prompts/
│   ├── agent1_system.txt
│   ├── agent1_user_template.txt
│   └── agent2_codex_prompt.txt
├── agents/
│   └── strut_detector_builder.toml
├── src/
│   ├── __init__.py
│   ├── cli.py
│   ├── config.py
│   ├── tiff_loader.py
│   ├── slice_exporter.py
│   ├── vlm_client.py
│   ├── agent1.py
│   ├── schema_validation.py
│   ├── paper_extractor.py
│   ├── agent2_input_builder.py
│   ├── codex_subagent_runner.py
│   ├── detector_runner.py
│   └── reporting.py
├── detector/
│   ├── detector.py
│   └── implementation_report.json
├── tests/
└── outputs/
```

# Configuration

Create `config.example.yaml` similar to:

```yaml
data:
  tiff_path: path/to/scan.tif
  paper_path: path/to/relevant_paper.pdf
  output_dir: outputs

representative_slice:
  index: 100
  preserve_full_resolution: true
  export_format: png

volume:
  expected_slice_count: 761
  voxel_spacing:
    x: null
    y: null
    z: null

paper:
  pages: []
  keywords:
    - lattice
    - strut
    - missing strut
    - broken strut
    - computed tomography
    - segmentation
    - connectivity
  maximum_excerpt_characters: 16000

agent1:
  provider: configurable
  model: configurable
  temperature: 0.2
  max_tokens: 6000
  timeout_seconds: 180

agent2:
  type: codex_subagent
  subagent_name: strut_detector_builder
  timeout_seconds: 900

development:
  slice_indices:
    - 100
    - 200
    - 300

detector_execution:
  slice_indices: []
  slice_start: null
  slice_end: null
  continue_on_error: true
  overwrite: false
```

Use environment variables for API credentials.

Do not commit credentials.

# Command-line interface

Provide commands similar to:

```bash
python -m src.cli inspect-data --config config.yaml

python -m src.cli export-representative-slice --config config.yaml

python -m src.cli run-agent1 --config config.yaml

python -m src.cli extract-paper --config config.yaml

python -m src.cli build-agent2-input --config config.yaml

python -m src.cli run-agent2 --config config.yaml

python -m src.cli run-detector \
  --config config.yaml \
  --slice-indices 100 200 300

python -m src.cli run-full-workflow --config config.yaml
```

# Testing requirements

Add tests for:

* loading a multi-page TIFF
* confirming the expected slice count
* exporting exactly one representative slice
* preserving original slice dimensions
* Agent 1 schema validation
* Agent 1 repair behavior
* local PDF text extraction
* page-reference preservation
* paper keyword excerpt selection
* Agent 2 input containing Agent 1 observations
* Agent 2 input containing paper excerpts
* Agent 2 input containing no image attachments
* Agent 2 prompt containing no embedded image data
* generated `detector.py` existence
* detector command-line argument parsing
* single-slice detector execution
* multiple-slice detector execution
* output JSON validation
* missing and broken as the only defect categories
* no supervised-learning requirement
* empty segmentation handling
* execution failure isolation
* output directory safety

Unit tests must not require live VLM or Codex calls.

Use mocked Agent 1 and Agent 2 outputs for tests.

# README requirements

The README must explain:

* the research motivation
* that Agent 1 replaces initial human visual inspection
* that Agent 1 receives one representative slice
* that Agent 2 is text-only during method generation
* that Agent 2 receives Agent 1's observations and a research paper
* that Agent 2 generates a reusable detector
* that the generated script later processes TIFF images
* the difference between Agent 2 receiving an image and the generated script receiving an image
* why missing-strut detection requires estimating expected lattice locations
* why broken-strut detection requires detecting partial material and localized gaps
* why single-slice evidence cannot confirm a 3D defect
* why outputs are unverified candidates
* how to select the representative slice
* how to upload and configure the paper
* how to run the complete workflow
* how to inspect Agent 1's observations
* how to inspect Agent 2's implementation report
* how to run the generated detector across slices
* limitations caused by having no labeled data

# Implementation order

Implement in this order:

1. Inspect the existing repository.
2. Inspect the TIFF format and metadata.
3. Inspect the uploaded PDF format.
4. Create the project structure.
5. Implement configuration loading.
6. Implement TIFF slice extraction.
7. Implement Agent 1 prompt and output schema.
8. Implement Agent 1 VLM call.
9. Implement local paper extraction.
10. Implement Agent 2 text-only input construction.
11. Verify that Agent 2 receives no image attachment.
12. Create the Codex subagent configuration.
13. Implement the Codex subagent runner.
14. Have Agent 2 generate `detector.py`.
15. Have Agent 2 test and repair the script on unlabeled development slices.
16. Implement detector-output validation.
17. Implement the detector execution CLI.
18. Add tests.
19. Write the README.
20. Perform a mocked end-to-end dry run.

Do not modify unrelated repository files.

Do not introduce thin- or bent-strut detection.

Do not introduce labeled-data requirements.

Do not create a third agent.

At completion, report:

* files created
* files modified
* Agent 1 output location
* extracted paper location
* Agent 2 input location
* generated detector location
* implementation-report location
* tests run
* tests passed
* tests failed
* mocked dry-run result
* unresolved assumptions
* exact command for running Agent 1
* exact command for generating the detector
* exact command for running the detector on selected slices
