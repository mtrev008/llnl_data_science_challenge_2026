# Topology metric definitions

Represent the lattice as an undirected graph `G=(V,E)`: nodes are junctions and edges are struts. The node degree is `k(v)`, the number of incident edges. A connected component is a maximal mutually reachable node set.

For declared lower and upper terminal sets `S` and `T`, report whether any path connects `S` to `T`. A bridge is an edge whose removal increases component count; an articulation node is a node whose removal increases component count. These identify topological dependencies, not physical failure locations.

With a validated defect-to-edge mapping, compare an intact graph `G0` to the graph `Gi` with candidate edge `i` removed. For a metric `Q`, report `Delta_Q_i = Q(Gi)-Q(G0)` and, when `Q(G0)` is nonzero, `100*Delta_Q_i/Q(G0)`. For two validated defects, calculate `eta_AB = Delta_Q_AB - (Delta_Q_A + Delta_Q_B)` as a topology-interaction indicator only.
