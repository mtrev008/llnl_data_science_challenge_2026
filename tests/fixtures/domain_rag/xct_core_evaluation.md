# XCT core domain-RAG evaluation specification

## Corpus

Only these papers are in scope:

1. `LatticeAnalytics-Strut-Level-Visualization-and-Inspection-of-Additively-Manufactured-Lattice.pdf`
2. `TheRoleofX-rayCTinAMupdated.pdf`
3. `X-ray computed tomography for additive manufacture a review_unformatted.pdf`

`srep43554.pdf` and `v36i3pp647-666.pdf` are excluded.

## LatticeAnalytics questions

1. What problem is LatticeAnalytics designed to solve?
2. How are the nominal lattice model and XCT volume aligned?
3. Why does the framework extract individual-strut subvolumes?
4. Which visualizations support strut-defect inspection?
5. What limitations do the authors report?

## Role of computed tomography questions

1. Why are external inspection techniques insufficient for many AM parts?
2. What roles can computed tomography perform in AM inspection?
3. How does CT relate to nondestructive testing and dimensional metrology?
4. What internal flaws motivate CT inspection?
5. What measurement challenges are described?

## XCT review questions

1. Why is volumetric dimensional measurement important for AM parts?
2. How did XCT transition from imaging to industrial metrology?
3. How is XCT used for porosity measurement?
4. How is XCT used for dimensional measurement?
5. What barriers to continued XCT adoption are identified?

## Unsupported challenge-specific questions

1. What is the calibrated voxel size of the LLNL challenge CT volume?
2. What defect-diameter threshold determines acceptance?
3. What registration transform maps the challenge JSON to its TIFF?
4. Which observed struts are intentional design deviations?
5. What TIFF intensity represents physical density?

## Baseline criteria

- All three PDFs load and produce chunks.
- No scoped PDF requires OCR.
- All chunks retain source, section, page, and stable ID metadata.
- All three files are unchanged on an immediate second ingestion.
- Expected paper recall at five is at least 0.80.
- Mean reciprocal rank is at least 0.65.
- Every fetched citation resolves to exact stored metadata.
- Neighbor expansion stays inside the selected document.
- Existing repository tests continue to pass.

The run uses the repository's local feature-hash embeddings together with
FTS5/BM25. It requires no API key and makes no embedding network calls. Results
measure the supported local retrieval configuration, not OpenAI embedding
quality.
