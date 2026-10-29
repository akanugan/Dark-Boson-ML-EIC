# Fair same-complexity pilot results

All values use held-out weighted events after the common Table I preselection.
The final column measures BDT coupling-threshold improvement relative to the
optimized rectangular selection using the same feature set.

| Signal | Mass [GeV] | Features | BDT R_Z | Optimized-cut R_Z | BDT coupling gain vs optimized cuts |
|---|---:|---|---:|---:|---:|
| scalar | 1 | electron only | 1.0401 | 1.0347 | +0.26% |
| scalar | 1 | electron + truth QA2 | 1.0401 | 1.0351 | +0.24% |
| scalar | 6.31 | electron only | 1.0279 | 1.0297 | -0.08% |
| scalar | 6.31 | electron + truth QA2 | 1.1188 | 1.0960 | +1.02% |
| vector | 1 | electron only | 1.0002 | 1.0000 | +0.01% |
| vector | 1 | electron + truth QA2 | 0.9986 | 0.9997 | -0.05% |
| vector | 10 | electron only | 1.0088 | 1.0033 | +0.27% |
| vector | 10 | electron + truth QA2 | 1.2866 | 1.2459 | +1.59% |

## Pilot conclusion

Using only Table I electron variables, the BDT is comparable to optimized
rectangular cuts and provides at most a sub-percent coupling-threshold change
at these representative points. Adding exact truth-level QA2 produces a much
larger gain relative to Table I, but optimized rectangular cuts using the same
QA2 information capture most of it. The remaining BDT advantage over those
fair cuts is about 1.6% in coupling threshold for the 10 GeV vector and about
1.0% for the 6.31 GeV scalar in this pilot.

These are model-dependent parton-level results. Photon-shape validation, DIS
events, signal-cut normalization, scalar-amplitude validation, and detector
effects remain outside this pilot.
