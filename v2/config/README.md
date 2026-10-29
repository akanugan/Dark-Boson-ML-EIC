# Physical and rate configuration

`paper_cuts.csv` specifies the common mass-dependent electron preselection. `rates.csv` is the starting fitting configuration; its photon entries are overridden by the independent calibration.

The nominal photon calibration is [`../results/photon_calibration_rates.csv`](../results/photon_calibration_rates.csv). The imported per-point `sample_config.json` files record the actual rates used. The DIS contribution remains fixed and unrejected.
