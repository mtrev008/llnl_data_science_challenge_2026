# Metric definitions

For graph coordinates `x1` and `x2`, calculate member vector `v = x2 - x1`, length `L = ||v||`, and absolute direction cosines `c = |v| / L`. Report `L` physically only with known calibration.

With a valid circular-equivalent diameter `d` mapped to a graph member, calculate `A = pi*d^2/4`, `I = pi*d^4/64`, radius of gyration `r_g = sqrt(I/A) = d/4`, and, for an explicit effective-length factor `K`, geometric slenderness `lambda = K*L/r_g`.

These are geometry indicators. They require material, loads, boundary conditions, and a validated solver model before becoming structural results. `pi^2*E*I/(K*L)^2` is only an Euler buckling indicator when `E`, `K`, section shape, and imperfection effects are supported.

For a calibrated binary mask, calculate global relative density as `rho_star = V_solid / V_envelope`, where `V_solid` is foreground voxel count times voxel volume and `V_envelope` is the physical foreground bounding-box volume. It is segmentation-sensitive and is not automatically design relative density.

For validated nominal-to-as-built registration, calculate `delta_q = q_as_built - q_nominal` and percent change `100*delta_q/q_nominal` for nonzero nominal `q`.
