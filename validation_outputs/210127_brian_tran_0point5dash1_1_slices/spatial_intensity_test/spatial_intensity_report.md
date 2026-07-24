# Spatial intensity-location test

- TIFF: `C:\Users\andre\llnl_data_science_challenge_2026\data\missing_struts\tif_stacks\210127_Brian_Tran_strut_lattices_0point5dash1 1 Slices.tif`
- Shape (Z,Y,X): `(761, 815, 837)`
- Low band: intensity ≤ global P01 = `29789`
- High band: intensity ≥ global P99 = `54370`
- Selected slice: Z=`266`, the maximum-SD slice within interior Z=`77`–`684`
- Selected slice mean / SD / range: `33367.967` / `5700.260` / `28292`–`59213`

## Low band

- Count: `5193905` (1.000521% of voxels)
- ZYX bounding box: `[0, 0, 0]` to `[760, 814, 836]`
- Mean nearest-boundary distance: `50.958` voxels
- Nearest center point ZYX / XYZ: `[382, 406, 417]` / `[417, 406, 382]`
- Deepest point ZYX / XYZ: `[382, 396, 414]` / `[414, 396, 382]`

## High band

- Count: `5192220` (1.000197% of voxels)
- ZYX bounding box: `[0, 47, 61]` to `[760, 754, 769]`
- Mean nearest-boundary distance: `28.669` voxels
- Nearest center point ZYX / XYZ: `[386, 407, 450]` / `[450, 407, 386]`
- Deepest point ZYX / XYZ: `[380, 403, 454]` / `[454, 403, 380]`

## Exact extrema

- Minimum: `0` at ZYX `[760, 753, 772]`, XYZ `[772, 753, 760]`
- Maximum: `65535` at ZYX `[34, 636, 730]`, XYZ `[730, 636, 34]`

## Selected-slice representative points

- Low: intensity `29776` at ZYX `[266, 407, 435]`, XYZ `[435, 407, 266]`
- High: intensity `54452` at ZYX `[266, 408, 418]`, XYZ `[418, 408, 266]`

## Polarity interpretation

On the selected slice, the high-band marker lies on a bright lattice line and the low-band marker lies in a dark cell void. This supports using higher stored intensity as lattice foreground and lower stored intensity as background/void for segmentation polarity in this TIFF.

This does not establish material identity, attenuation, density, or the accuracy of a single global threshold across all slices.

Quantile bands are intensity categories, not material labels. Their alignment with recognizable lattice lines supports polarity here, but does not prove attenuation calibration or material identity.