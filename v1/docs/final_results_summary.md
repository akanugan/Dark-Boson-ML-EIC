# Final proof-of-concept results

The weighted held-out test results show that ML improvement is mass dependent.
For vector signals at or below 1 GeV, the classifier has little useful
separation from coherent photon bremsstrahlung and does not improve the
Table I significance. The gain increases at higher mass, reaching
`R_Z = 1.2866 +/- 0.0078` at 10 GeV. Under the stated approximation this is a
28.7% significance increase and an 11.8% lower coupling threshold.

Scalar signals are more separable in this implementation. The conservative
gain, with the published DIS rate treated as completely unrejected, reaches
`R_Z = 1.1188 +/- 0.0058` at 6.31 GeV, equivalent to a 5.5% lower coupling
threshold. At low scalar masses the gain is consistent with zero.

These results demonstrate that multivariate correlations can add information
beyond rectangular cuts in the medium- and high-mass region. They do not show
that ML universally improves this search, and they do not establish a detector-
level EIC projection. The largest vector gain is driven primarily by `QA2`,
followed by `Qe2`, electron energy, electron `pT`, and electron `eta` in the
TMVA importance ranking.

The coherent-photon sample is our matrix-element baseline, not a
reproduction of the authors' private background events. Compared with the old
public one-dimensional ancillary histograms, its inclusive marginal shapes
have total-variation distances of 0.715 in `log10(electron pT)` and 0.409 in
electron `eta`. Because those coarse histograms do not resolve the selected
joint tail, they are validation references only and are not used to tune or
reweight the training sample. This background-shape difference is the dominant
unquantified modeling uncertainty in the reported proof-of-concept gains.
