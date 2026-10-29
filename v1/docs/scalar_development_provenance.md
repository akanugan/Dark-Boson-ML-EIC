# Scalar development-sample provenance note

The scalar training and validation ROOT files under `data/ml/root/` were
generated before the 14 August 2026 metadata-hardening edit to
`src/generate_scalar.cpp`. That edit changed only construction of the
`generator_configuration` `TNamed`: it added explicit cut mass, ion mass,
`A`, `Z`, and selected-integration fields. It did not change the scalar matrix
element, phase-space map, Table-I cut test, event branches, TFoam weights, or
normalization.

The exact development ROOT files, together with the training and rectangular
selection binaries, are fixed by
`fair_study/rigorous/development_frozen/development_inputs_and_methods.sha256`.
Fresh sealed scalar files are generated with the metadata-hardened binary and
are checked against the expected process, mass, coupling, beams, seed, run
size, and cuts before evaluation.
