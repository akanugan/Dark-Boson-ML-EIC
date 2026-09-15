#!/usr/bin/env python3
"""Validate the completed development grid and freeze validation-only choices."""

import csv
import math
from pathlib import Path


root = Path(__file__).resolve().parents[1]
development = root / "fair_study" / "rigorous" / "development_frozen"
MASS_VALUES = [
    0.010, 0.032, 0.100, 0.316, 1.000, 1.585, 2.512, 3.981,
    5.000, 6.310, 10.000,
]
PROFILES = {"depth2", "depth3", "depth4", "depth3_800"}
FEATURES = {"electron", "electron_qa2"}
QUANTILES = (40, 80, 160)


def close_mass(left, right):
    return abs(float(left) - float(right)) < 5.0e-7


def finite(row, field, path):
    try:
        value = float(row[field])
    except (KeyError, ValueError) as error:
        raise SystemExit(f"bad {field} in {path}") from error
    if not math.isfinite(value):
        raise SystemExit(f"non-finite {field} in {path}")
    return value


model_rows = []
for metrics_path in sorted((development / "models").glob("*/*/metrics.csv")):
    with metrics_path.open(newline="") as handle:
        row = next(csv.DictReader(handle))
    weights_path = (
        metrics_path.parent / "dataset" / "weights" /
        "TMVAClassification_BDTG.weights.xml"
    )
    if not weights_path.is_file():
        raise SystemExit(f"missing XML weights for {metrics_path}")
    if row.get("evaluation_mode") != "validation_all":
        raise SystemExit(f"wrong evaluation mode in {metrics_path}")
    if row.get("feature_set") not in FEATURES:
        raise SystemExit(f"wrong feature set in {metrics_path}")
    if row.get("model_profile") != metrics_path.parent.name:
        raise SystemExit(f"profile/path mismatch in {metrics_path}")
    expected_group = (
        f"{row['signal_type']}_m{float(row['mass_GeV']):.3f}".replace(".", "p")
        + f"_{row['feature_set']}"
    )
    if metrics_path.parent.parent.name != expected_group:
        raise SystemExit(f"model path/metadata mismatch in {metrics_path}")
    for field in (
        "validation_auc", "validation_threshold",
        "validation_significance_improvement",
    ):
        finite(row, field, metrics_path)
    row["metrics_path"] = str(metrics_path)
    row["weights_path"] = str(weights_path)
    model_rows.append(row)

groups = {}
for row in model_rows:
    key = (row["signal_type"], float(row["mass_GeV"]), row["feature_set"])
    groups.setdefault(key, []).append(row)

expected_groups = {
    (signal_type, mass, feature)
    for signal_type in ("vector", "scalar")
    for mass in MASS_VALUES
    for feature in FEATURES
}
if set(groups) != expected_groups:
    raise SystemExit(
        f"development groups mismatch; missing={sorted(expected_groups-set(groups))}, "
        f"extra={sorted(set(groups)-expected_groups)}"
    )

selected = []
for key, candidates in sorted(groups.items()):
    signal_type, mass, feature_set = key
    profiles = [row["model_profile"] for row in candidates]
    if len(candidates) != 4 or set(profiles) != PROFILES:
        raise SystemExit(f"incomplete/duplicate profiles for {key}: {profiles}")
    mass_index = next(
        index for index, value in enumerate(MASS_VALUES) if close_mass(value, mass)
    )
    point_index = mass_index + (len(MASS_VALUES) if signal_type == "scalar" else 0)
    feature_index = 0 if feature_set == "electron" else 1
    expected_seed = 720000 + point_index * 100 + feature_index * 10
    if any(int(row["random_seed"]) != expected_seed for row in candidates):
        raise SystemExit(f"wrong/inconsistent model seed for {key}")
    winner = max(
        candidates,
        key=lambda row: (
            finite(row, "validation_significance_improvement", row["metrics_path"]),
            finite(row, "validation_auc", row["metrics_path"]),
            row["model_profile"],
        ),
    )

    tag = f"{mass:.3f}".replace(".", "p")
    box_rows = []
    for quantiles in QUANTILES:
        box_path = development / "baselines" / (
            f"{signal_type}_m{tag}_{feature_set}_q{quantiles}.csv"
        )
        if not box_path.is_file():
            raise SystemExit(f"missing box grid {box_path}")
        with box_path.open(newline="") as handle:
            box = next(csv.DictReader(handle))
        if (
            box.get("signal_type") != signal_type
            or box.get("feature_set") != feature_set
            or not close_mass(box.get("mass_GeV", "nan"), mass)
            or int(box.get("quantiles", "-1")) != quantiles
        ):
            raise SystemExit(f"box metadata mismatch in {box_path}")
        finite(box, "validation_significance_improvement", box_path)
        finite(box, "training_significance_improvement", box_path)
        box_rows.append((quantiles, box_path, box))
    box_quantiles, box_path, box = max(
        box_rows,
        key=lambda item: (
            float(item[2]["validation_significance_improvement"]),
            float(item[2]["training_significance_improvement"]),
            -item[0],
        ),
    )
    bdt_rz = float(winner["validation_significance_improvement"])
    box_rz = float(box["validation_significance_improvement"])
    if not (bdt_rz > 0.0 and box_rz > 0.0):
        raise SystemExit(f"undefined validation comparison for {key}")
    ratio = bdt_rz / box_rz
    coupling = 1.0 - math.sqrt(box_rz / bdt_rz)
    selected.append({
        "signal_type": signal_type,
        "mass_GeV": f"{mass:g}",
        "feature_set": feature_set,
        "selected_profile": winner["model_profile"],
        "model_seed": winner["random_seed"],
        "validation_bdt_RZ": f"{bdt_rz:.12g}",
        "validation_box_RZ": f"{box_rz:.12g}",
        "validation_RZ_ratio": f"{ratio:.12g}",
        "validation_coupling_advantage": f"{coupling:.12g}",
        "box_quantiles": str(box_quantiles),
        "metrics_path": winner["metrics_path"],
        "weights_path": winner["weights_path"],
        "box_path": str(box_path),
    })

if len(selected) != 44:
    raise SystemExit(f"expected 44 selected models, found {len(selected)}")
output = development / "selected_models.csv"
if output.exists():
    raise SystemExit(f"refusing to overwrite {output}")
with output.open("w", newline="") as handle:
    writer = csv.DictWriter(
        handle, fieldnames=selected[0].keys(), lineterminator="\n"
    )
    writer.writeheader()
    writer.writerows(selected)
print(f"wrote {len(selected)} validation-only selections to {output}")
