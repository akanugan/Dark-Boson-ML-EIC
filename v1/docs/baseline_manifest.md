# Frozen baseline manifest

Baseline directory: `/Users/rojaemighty/Dark` (clean source directory at freeze time;
it is not a Git repository, so the file hashes below are the immutable identifiers).

After the September 9 directory merge, the original snapshot remains in
`frozen_baseline/`; active sources at the project root are the extended versions.
The frozen physics
inputs are:

- Process: coherent `e Au -> e Au phi`.
- Electron beam energy: 18 GeV.
- Gold beam energy: 100 GeV per nucleon.
- Gold nucleus: A = 197, Z = 79, ion mass = 183 GeV.
- Scalar/vector electron coupling: `1e-4`.
- Nuclear response: the unscreened Helm form factor stated in the paper.
- Selection: corrected mass-dependent Table I cuts.
- Laboratory convention: incoming gold along +z and electron along -z.
- Electron transfer: `Qe2 = -(k_in - k_out)^2` in the collider laboratory frame.
- Cut comparisons are strict: `Qe2 > min`, `pT > min`, `eta > min`,
  `eta < max`, and `E < max`.

Reference scan files:

- `/Users/rojaemighty/Dark/results/vector_scan_fresh.csv`
- `/Users/rojaemighty/Dark/results/scalar_scan.csv`
- `/Users/rojaemighty/Dark/config/paper_cuts.csv`
- `/Users/rojaemighty/Dark/config/paper_figure2_digitized.csv`

Source SHA-256 values at freeze time:

- `generate_vector.cpp`: `f0c9349e4882652b485cb1a4f03815c2d3d8c3060b51a36069284468a72786af`
- `generate_scalar.cpp`: `7af7b89b02d5f7577a770a3eff4e4203c39705f60ccf4c36705274cd6b5b1dae`
- `DarkBosonKinematics.h`: `195c629ed71b737f04584ed182b3b1259024355dc1eb6b2bdc8c407a89c7261f`

The scalar source copied into this next-stage workspace adds event recording
only. A fixed-seed regression test produced identical original and extended
integrals:

- Inclusive: `5.96553880779 +/- 0.0346124511942 pb`.
- Direct selected integration: `0.0373878825182 +/- 0.000209080395754 pb`.

Configuration for that regression test: mass 1 GeV, 20,000 events, 1000
cells, 300 samples, seed 112233.
