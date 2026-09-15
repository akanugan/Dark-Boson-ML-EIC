# Exact-t independent-seed robustness protocol

This study tests the two predeclared 10 GeV benchmarks that produced the
largest exact-`t` BDT advantage: vector and scalar signal. Both the BDT and the
multistart rectangular selector receive the same five inputs: `log10(Qe2)`,
recoil-electron `pT`, `eta`, energy, and exact generator-level `t` (stored
internally as `QA2`).

Ten complete replicas independently regenerate signal and photon training,
validation, and sealed-test samples. Four frozen BDT profiles and rectangular
grids with 40, 80, and 160 weighted thresholds are fitted using the same event
budgets and weights. Validation selects the BDT profile, score threshold, box
grid, and box bounds. Test events are generated only after all choices are
frozen and are evaluated once by both methods.

Each replica uses 2,000 paired event-bootstrap draws. The final interval uses
20,000 hierarchical draws that resample complete replicas and then a paired
event-bootstrap draw within each selected replica. The endpoint is
`RZ_BDT/RZ_box`; the coupling-threshold advantage is
`1 - sqrt(RZ_box/RZ_BDT)`. A one-sided familywise lower limit uses `0.05/2` for
the two benchmarks. A lower limit above zero indicates statistical BDT
superiority, while a lower limit above +1% is the preregistered practical
threshold.

Exact `t` remains an oracle input. This protocol tests reproducibility of the
parton-level algorithmic result and does not supply intact-ion acceptance,
reconstruction, resolution, validated DIS events, or detector-level EIC reach.
