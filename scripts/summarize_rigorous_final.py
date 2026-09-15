#!/usr/bin/env python3
import csv
import math
from pathlib import Path


root = Path(__file__).resolve().parents[1]
study = root / "fair_study" / "rigorous"
selected_path = study / "development_frozen" / "selected_models.csv"
final_dir = study / "final"


def quantile(values, probability):
    values = sorted(values)
    if not values:
        return math.nan
    position = probability * (len(values) - 1)
    lower = math.floor(position)
    upper = math.ceil(position)
    fraction = position - lower
    return values[lower] * (1.0 - fraction) + values[upper] * fraction

with selected_path.open(newline="") as handle:
    selected = list(csv.DictReader(handle))

rows = []
for choice in selected:
    tag = f"{float(choice['mass_GeV']):.3f}".replace(".", "p")
    result_path = final_dir / (
        f"{choice['signal_type']}_m{tag}_{choice['feature_set']}.csv"
    )
    with result_path.open(newline="") as handle:
        result = next(csv.DictReader(handle))
    bootstrap_path = result_path.with_name(result_path.stem + "_bootstrap.csv")
    with bootstrap_path.open(newline="") as handle:
        bootstrap_coupling = [
            float(row["coupling_advantage"]) for row in csv.DictReader(handle)
        ]
    requested = int(result["bootstrap_replicates"])
    valid = int(result["bootstrap_valid"])
    invalid = int(result["bootstrap_invalid"])
    if requested != valid + invalid or len(bootstrap_coupling) != valid:
        raise SystemExit(f"bootstrap accounting mismatch in {result_path}")
    if choice["feature_set"] == "electron" and invalid != 0:
        raise SystemExit(f"invalid primary bootstrap draws in {result_path}")
    rows.append({
        "signal_type": choice["signal_type"],
        "mass_GeV": choice["mass_GeV"],
        "feature_set": choice["feature_set"],
        "selected_profile": choice["selected_profile"],
        "model_seed": choice["model_seed"],
        "box_quantiles": choice["box_quantiles"],
        "bdt_RZ": result["bdt_RZ"],
        "box_RZ": result["box_RZ"],
        "RZ_ratio": result["RZ_ratio"],
        "coupling_advantage": result["coupling_advantage"],
        "coupling_q025": result["coupling_q025"],
        "coupling_q05": result["coupling_q05"],
        "coupling_q50": result["coupling_q50"],
        "coupling_q975": result["coupling_q975"],
        "bootstrap_valid": result["bootstrap_valid"],
        "bootstrap_invalid": result["bootstrap_invalid"],
        "primary_bonferroni_lower": (
            f"{quantile(bootstrap_coupling, 0.05 / 22):.12g}"
            if choice["feature_set"] == "electron" else "NA"
        ),
        "bdt_signal_efficiency": result["bdt_signal_efficiency"],
        "bdt_photon_efficiency": result["bdt_photon_efficiency"],
        "box_signal_efficiency": result["box_signal_efficiency"],
        "box_photon_efficiency": result["box_photon_efficiency"],
        "signal_neff": result["signal_neff"],
        "background_neff": result["background_neff"],
        "signal_max_weight_fraction": result["signal_max_weight_fraction"],
        "background_max_weight_fraction": result["background_max_weight_fraction"],
    })

output = final_dir / "rigorous_final_metrics.csv"
with output.open("w", newline="") as handle:
    writer = csv.DictWriter(
        handle, fieldnames=rows[0].keys(), lineterminator="\n"
    )
    writer.writeheader()
    writer.writerows(rows)

summary = final_dir / "rigorous_final_summary.md"
lines = [
    "# Sealed ML-versus-rectangular final-test results",
    "",
    "Positive coupling values favor BDT. Intervals are paired event-bootstrap",
    "intervals for the sealed test sample only; training and generator-model",
    "systematics require the separate seed study.",
    "For the 22 electron-only primary tests, the CSV also gives a conservative",
    "one-sided 95% familywise Bonferroni lower bound (quantile 0.05/22).",
    "",
    "| Signal | Mass | Features | Profile | Box grid | BDT R_Z | Box R_Z | Coupling advantage [95% interval] |",
    "|---|---:|---|---|---:|---:|---:|---:|",
]
for row in sorted(rows, key=lambda item: (
        item["signal_type"], float(item["mass_GeV"]), item["feature_set"])):
    label = "electron only" if row["feature_set"] == "electron" else "electron + truth QA2"
    gain = 100 * float(row["coupling_advantage"])
    low = 100 * float(row["coupling_q025"])
    high = 100 * float(row["coupling_q975"])
    lines.append(
        f"| {row['signal_type']} | {float(row['mass_GeV']):g} | {label} | "
        f"{row['selected_profile']} | {row['box_quantiles']} | {float(row['bdt_RZ']):.4f} | "
        f"{float(row['box_RZ']):.4f} | {gain:+.2f}% [{low:+.2f}, {high:+.2f}] |"
    )
summary.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"wrote {len(rows)} sealed result rows")
print(f"wrote {output}")
print(f"wrote {summary}")
