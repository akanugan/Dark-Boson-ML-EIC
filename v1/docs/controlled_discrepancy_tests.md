# Controlled discrepancy tests

## Rules

Each test below changes at most one convention or estimator. Unless stated,
the matrix element, beam energies, phase-space limits, Helm form factor,
coupling, event four-vectors, event weights, and Table I cuts are unchanged.

## Results

1. **Locate the low-mass excess in nuclear momentum transfer.** At
   `m_phi=0.01 GeV`, the independent inclusive sample gives 156,021 pb. The
   contribution from `QA2 >= 1e-6 GeV2` is about 30,331 pb, close to the
   published 29,515 pb. Essentially no selected weight occurs below `1e-6`.
   Therefore the low-mass inclusive difference and post-cut discrepancy occupy
   disjoint regions. This localization alone does not justify deleting the
   low-t contribution.

2. **Evaluate the same amplitude in the ion rest frame.** Reweighting the
   identical events with the rest-frame evaluation changes the integrated
   result by less than the displayed `1e-9`; the largest event change is
   `3.14e-6`. The choice of evaluation frame is not the source.

3. **Use 50-digit arithmetic only in the final reduced-amplitude formula.**
   The integrated total and selected values again change by less than the
   displayed `1e-9`. Cancellation in the final algebraic expression is not
   the source.

4. **Compare sampled QA2 with QA2 reconstructed from ion four-vectors.** In the
   original double-precision angle construction, the
   weighted reconstructed/sampled ratio is about 2710 below `1e-15`, 18 below
   `1e-12`, 1.025 in `1e-9--1e-8`, and 1.00079 above `1e-8 GeV2`. This locates
   a real numerical problem in the construction of nearly collinear ion
   four-vectors. Computing `1-cos(theta_A)` with 50-digit arithmetic fixes the
   invariant consistency. After that correction, however, the unscreened Helm
   vector total at 0.01 GeV is about 179,390 pb, farther above the paper's
   29,515 pb. Thus the numerical defect was real but was not the origin of the
   paper's low-mass suppression.

5. **Fit one scale factor to the published post-cut curves.** The geometric
   mean paper/independent factors are 3.009 for vectors and 3.040 for scalars.
   Dividing the paper curves by exactly three leaves RMS fractional residuals
   of 4.6% and 4.5%, respectively. A common post-cut normalization accounts
   for both boson types; vector polarization cannot be the explanation.

6. **Direct cut integration versus weighted-event acceptance.** At 1 GeV the
   direct result is 0.15705 pb. Three inclusive weighted estimates are
   0.14400, 0.16409, and 0.15730 pb; their mean is 0.15513 pb. Weighted
   acceptance agrees with direct integration and cannot produce a factor of
   three.

7. **Remove only the Qe2 cut.** In three 1 GeV samples, zero events pass
   `pT`, `eta`, and `E` while failing `Qe2 > 10^0.2 GeV2`. The selected cross
   section is unchanged. The undefined Qe2 convention cannot explain this
   benchmark discrepancy.

8. **Reverse only the eta axis.** The selected rate becomes 0.665--0.710 of
   the original. The opposite beam-axis convention worsens the discrepancy.

9. **Apply only the energy cut in the collider CM frame.** The selected rate
   becomes 0.00083--0.00570 of the lab-energy result. A CM energy convention
   cannot explain the enhancement.

10. **Use only the lower edge of the published pT histogram bin.** Replacing
    `pT > 1.3 GeV` by `pT > 1.0 GeV` raises the 1 GeV rate by 1.79--1.83, not
    three. Coarse whole-bin treatment could bias the result but is not the
    full explanation.

11. **Insert only the alternative pair-mass Jacobian factor 2*m(e,phi).** At
    1 GeV this enhances acceptance by 2.77--2.87 and accidentally approaches
    the published value. Across masses it changes from 4.89 at 0.316 GeV to
    1.42 at 6.31 GeV, unlike the observed nearly constant factor three. The
    Jacobian ambiguity is not the general source.

## Public-file provenance

The v2 and v3 `dis_pt.pdf`, `dis_eta.pdf`, and `dis_Q2.pdf` files have identical
SHA-256 hashes. The revised `xsection.pdf` is different and newer. Version 2
contains numerical ancillary files; version 3 contains no ancillary directory,
event sample, joint cut distribution, cutflow, or analysis code. Consequently,
the public record permits identification of the extra common red-curve factor,
but not the exact internal line of author code that introduced it.

## Conclusions

- The original low-mass generator had a numerical problem: sampled `QA2` and
  ion four-vectors ceased to agree at extreme forward momentum transfer. This
  has been fixed with high-precision forward-ion kinematics.
- The corrected, unscreened Helm result remains substantially above the paper
  at 0.01--0.032 GeV. Reproducing the paper there requires an undocumented
  screening prescription, low-t cutoff, or author-side numerical regulator;
  no such ingredient is stated in the public calculation.
- The central-mass inclusive cross sections validate the physical matrix
  element and normalization.
- The remaining post-cut difference is consistent with a paper-side common
  factor of three applied only to both revised red curves.
- No tested physical, frame, cut, weighting, or Jacobian convention produces
  that constant factor across vector and scalar masses while preserving the
  black inclusive curves.

## Exact question for the authors

For the revised Figure 2 red curves, were the post-cut cross sections obtained
from a newly integrated cut matrix element or by multiplying the corrected
inclusive cross section by an acceptance from a separate event/histogram
sample? At `m_phi=1 GeV`, could you provide the unrounded weighted sums before
and after each Table I cut, the definition/frame of `Qe2`, the sampled
pair-mass variable (`m_ephi` or `m_ephi^2`) and its Jacobian, and any factor
applied only when normalizing the red scalar and vector curves? Independent
integration gives 0.1575 pb for the vector and 0.03724 pb for the scalar,
whereas Figure 2 gives 0.46236 pb and 0.11048 pb—factors 2.94 and 2.97,
respectively—while the inclusive curves agree.

At low mass, did you impose atomic screening or a minimum `QA2` beyond the
kinematic bound? With high-precision ion-angle construction and only the stated
Helm form factor, the vector total at 0.01 GeV is about 179,390 pb, whereas
Figure 2 gives about 29,515 pb.
