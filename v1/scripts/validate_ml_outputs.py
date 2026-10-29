#!/usr/bin/env python3
"""Check completeness and internal consistency of the final ML outputs."""

import csv
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
METRICS = ROOT / "results" / "ml" / "ml_metrics.csv"


def require(condition, message):
    if not condition:
        raise SystemExit(f"validation failed: {message}")


with METRICS.open(newline="") as handle:
    rows = list(csv.DictReader(handle))

require(len(rows) == 21, f"expected 21 metric rows, found {len(rows)}")
keys = {(row["signal_type"], float(row["mass_GeV"])) for row in rows}
require(len(keys) == 21, "duplicate signal-type/mass rows")

for row in rows:
    label = f"{row['signal_type']} m={row['mass_GeV']}"
    auc = float(row["auc"])
    signal_eff = float(row["signal_efficiency"])
    photon_eff = float(row["photon_background_efficiency"])
    improvement = float(row["significance_improvement"])
    coupling_gain = float(row["coupling_reach_improvement"])
    require(0.0 <= auc <= 1.0, f"{label}: invalid AUC")
    require(0.0 <= signal_eff <= 1.0, f"{label}: invalid signal efficiency")
    require(0.0 <= photon_eff <= 1.0, f"{label}: invalid photon efficiency")
    require(improvement > 0.0, f"{label}: invalid significance ratio")
    expected_gain = 1.0 - 1.0 / math.sqrt(improvement)
    require(abs(coupling_gain - expected_gain) < 1e-9,
            f"{label}: inconsistent coupling gain")

    tag = f"{float(row['mass_GeV']):.3f}".replace(".", "p")
    model_dir = ROOT / "models" / f"{row['signal_type']}_m{tag}"
    xml_model = model_dir / "dataset" / "weights" / "TMVAClassification_BDTG.weights.xml"
    require(xml_model.is_file(), f"{label}: missing trained XML model")
    require((model_dir / "test_scores.csv").is_file(),
            f"{label}: missing held-out score file")

vector_10 = next(row for row in rows
                 if row["signal_type"] == "vector" and float(row["mass_GeV"]) == 10.0)
require(abs(float(vector_10["significance_improvement"]) - 1.28655951631) < 1e-8,
        "10 GeV vector benchmark changed unexpectedly")

print(f"validated {len(rows)} final ML models and metric rows")
