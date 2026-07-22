\# Segmentation Evaluation Rubric



\## Task



Compare the two attached images:



1\. The first image is the ground-truth segmentation.

2\. The second image is the predicted segmentation result.



Evaluate only the segmented lattice structure. Ignore differences caused solely

by titles, margins, axes, image scaling, or other presentation elements.



\## Evaluation Criteria



\### 1. Structural Integrity



Determine whether the predicted segmentation captures the same lattice struts

and connections as the ground truth.



Consider:



\- Whether all major struts are present

\- Whether struts remain connected

\- Whether any struts are broken, shortened, merged, or incorrectly shaped

\- Whether the overall lattice geometry matches the ground truth



\### 2. False Positives and False Negatives



Identify segmentation errors.



False positives include:



\- Extra foreground regions

\- Background noise labeled as lattice material

\- Struts or blobs not present in the ground truth

\- Struts that are substantially thicker than in the ground truth



False negatives include:



\- Missing struts

\- Missing portions of struts

\- Gaps in otherwise connected structures

\- Struts that are substantially thinner than in the ground truth



\### 3. Topology and Junction Preservation



Evaluate whether the predicted result preserves the topology of the lattice.



Consider:



\- Whether junctions and nodes occur at the correct locations

\- Whether the correct number of struts meet at each junction

\- Whether connected structures remain connected

\- Whether separate structures remain separate

\- Whether holes and enclosed regions are preserved



Topology and connectivity errors should be treated as more serious than small

boundary or thickness differences.



\### 4. Noise and Artifacts



Determine whether the predicted result contains artifacts absent from the

ground truth.



Examples include:



\- Isolated foreground pixels or blobs

\- Speckle noise

\- Jagged or irregular boundaries

\- Unnatural holes

\- Boundary fragments

\- Streaks or processing artifacts



\## Scoring Scale



Assign one integer score from 0 through 5.



\- 5: The result is effectively identical to the ground truth. All structures,

&#x20; connections, and junctions are preserved, with no meaningful false positives,

&#x20; false negatives, noise, or artifacts.



\- 4: Excellent agreement. The topology and all important structures are

&#x20; preserved, with only very minor boundary, thickness, or isolated-pixel

&#x20; differences.



\- 3: The main topology is correct, but noticeable segmentation errors are

&#x20; present. Examples include noise, small false-positive regions, local gaps, or

&#x20; missing thin portions of struts.



\- 2: Fair agreement, but significant differences are present. Examples include

&#x20; large missing portions, broken connections, incorrect junctions, substantial

&#x20; over-segmentation, or substantial under-segmentation.



\- 1: Major structural failure. Much of the lattice is missing, incorrectly

&#x20; connected, overwhelmed by false positives, or otherwise inconsistent with

&#x20; the ground truth.



\- 0: The result is blank, unrelated, unusable, or does not depict the requested

&#x20; segmentation.



\## Evaluation Instructions



Inspect the complete images before scoring. Base the score primarily on

structural agreement and topology. Then consider false positives, false

negatives, boundary quality, noise, and artifacts.



Do not award a score of 5 when any meaningful structural difference exists.

Do not reduce the score solely because of plot titles, margins, or display

formatting.



Return only a valid JSON object. Do not use Markdown fences or include text

outside the JSON.



Use exactly this schema:



{

&#x20; "reasoning": "Concise explanation addressing structural integrity, false positives or negatives, topology, and noise or artifacts.",

&#x20; "score": 0

}



The score must be an integer from 0 through 5.

