# Scientific Plotting Standards

- Use Matplotlib `Agg`, close every figure, and default to PNG at 200 DPI.
- Allow PNG, SVG, and PDF. Refuse overwrite unless explicitly enabled.
- Label quantities accurately; show units only when supplied.
- Verify saved artifacts and record discarded nonnumeric or nonfinite values.
- Use colorblind-accessible colors and avoid relying on color alone.

| Meaning | Style |
|---|---|
| Primary | `#4C78A8` |
| Mean | `#E45756`, dashed |
| Median | `#54A24B`, dotted |
| Threshold | `#F58518`, dash-dot |
| False positive | red |
| False negative | yellow |

Use histograms for continuous data and bars for categories. Label logarithmic
axes. Do not plot identifiers as measurements.

For integer TIFFs, accumulate exact histogram counts page by page when the dtype
range is bounded. For floating TIFFs, label and record sample-derived bin edges
while counting all finite values into those edges. Record page coverage.

Display CT in grayscale. Record orientation, slice, shape, and display window.
Apply windows only to rendering and reuse them in comparisons. Do not add scale
bars without known spacing.

Do not eagerly load a non-memory-mappable TIFF above the configured memory limit.
Use page streaming for axis-0 histograms and slice trends. Keep analytical
sampling separate from display-window sampling.

Require matching image and mask shapes after slice selection. Render masks with
nearest-neighbor interpolation and error classes with a legend. Keep slice,
crop, and normalization fixed across iterations.

Limit rendered images to the configured maximum dimensions. Downsample CT
intensity only for display and use nearest-neighbor reduction for masks. Record
original size, rendered size, method, and strides.

Do not render invalid graph edges as valid. Preserve coordinate conventions,
label 2D projections, and record omissions or sampling.
