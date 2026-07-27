# Visualization Selection

| Question or data | Preferred view | Alternative |
|---|---|---|
| Continuous scalar distribution | Histogram | ECDF |
| Categories or few integer states | Bar chart | Count table |
| Group distributions | Box plot | Violin plot |
| Two numeric variables | Scatter plot | Hexbin |
| CT inspection | Orthogonal slices | Contact sheet |
| Slice anomalies | Slice trend | Anomaly slices |
| Segmentation assessment | CT/mask overlay | Contours |
| Prediction vs truth | Error map | Side-by-side |
| Optimization history | Metric trend | Iteration sheet |
| Lattice topology | Junction-strut graph | Degree histogram |
| Missing struts | Anomaly graph | CT/graph overlay |

Identify source shape, scientific question, validation state, and data type.
Choose the simplest view that preserves relevant structure. Record any sampling.

Treat `id`, `source`, `target`, `junction0`, `junction1`, and names ending in
`_id` or `_ids` as identifiers. Use requested CT slices; otherwise use center
slices. Use deterministic extrema for anomaly selection. Apply robust display
percentiles when needed and reuse the window in comparisons.

Map Locke warnings as follows:

- Constant slices: slice trends and affected slices.
- Skewed intensity: histogram, optionally log-count.
- Invalid references: omit or distinctly mark invalid edges.
- Unusual degree: degree distribution and degree-colored graph.
- Coordinate mismatch: separate bounds, never an overlay.
- Non-watertight STL: surface view with the warning retained.
