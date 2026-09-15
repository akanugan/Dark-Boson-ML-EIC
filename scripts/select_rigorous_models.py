#!/usr/bin/env python3
import csv
import math
from pathlib import Path


root = Path(__file__).resolve().parents[1]
study = root / "fair_study" / "rigorous"
development = study / "development_frozen"

MASS_VALUES = [
    0.010,
    0.032,
    0.100,
    0.316,
    1.000,
    1.585,
    2.512,
    3.981,
    5.000,
    6.310,
    10.000,
]
EXPECTED_PROFILES = {"depth2", "depth3", "depth4", "depth3_800"}
EXPECTED_FEATURES = {"electron", "electron_qa2"}
EXPECTED_QUANTILES = {40, 80, 160}


def close_mass(left, right):
    return abs(float(left) - float(right)) < 5.0e-7


def finite_number(row, field, path):
    try:
        value = float(row[field])
    except (KeyError, ValueError) as error:
        raise SystemExit(f"bad {field} in {path}") from error
    if not math.isfinite(value):
        raise SystemExit(f"non-finite {field} in {path}")
    return value

rows = []
for metrics_path in sorted((development / "models").glob("*/*/metrics.csv")):
    with metrics_path.open(newline="") as handle:
        row = next(csv.DictReader(handle))
    row["metrics_path"] = str(metrics_path)
    row["model_dir"] = str(metrics_path.parent)
    row["weights_path"] = str(
        metrics_path.parent
        / "dataset"
        / "weights"
        / "TMVAClassification_BDTG.weights.xml"
    )
    if not Path(row["weights_path"]).is_file():
        raise SystemExit(f"missing XML weights for {metrics_path}")
    if row.get("evaluation_mode") != "validation_all":
        raise SystemExit(f"wrong evaluation_mode in {metrics_path}")
    if row.get("feature_set") not in EXPECTED_FEATURES:
        raise SystemExit(f"wrong feature_set in {metrics_path}")
    if metrics_path.parent.name != row.get("model_profile"):
        raise SystemExit(f"profile/path mismatch in {metrics_path}")
    expected_group = (
        f"{row['signal_type']}_m{float(row['mass_GeV']):.3f}".replace(".", "p")
        + f"_{row['feature_set']}"
    )
    if metrics_path.parent.parent.name != expected_group:
        raise SystemExit(f"model path/metadata mismatch in {metrics_path}")
    for field in (
        "validation_auc",
        "validation_threshold",
        "validation_significance_improvement",
    ):
        finite_number(row, field, metrics_path)
    rows.append(row)

groups = {}
for row in rows:
    key = (row["signal_type"], float(row["mass_GeV"]), row["feature_set"])
    groups.setdefault(key, []).append(row)

selected = []
expected_groups = {
    (signal_type, mass, feature)
    for signal_type in ("vector", "scalar")
    for mass in MASS_VALUES
    for feature in EXPECTED_FEATURES
}
if set(groups) != expected_groups:
    missing = sorted(expected_groups - set(groups))
    extra = sorted(set(groups) - expected_groups)
    raise SystemExit(f"development groups mismatch; missing={missing}, extra={extra}")

for key, candidates in sorted(groups.items()):
    profiles = [row["model_profile"] for row in candidates]
    if len(candidates) != 4 or set(profiles) != EXPECTED_PROFILES:
        raise SystemExit(f"incomplete/duplicate profiles for {key}: {profiles}")
    signal_type, mass, feature_set = key
    mass_index = next(
        (index for index, value in enumerate(MASS_VALUES) if close_mass(value, mass)),
        None,
    )
    if mass_index is None:
        raise SystemExit(f"unexpected mass in {key}")
    point_index = mass_index + (len(MASS_VALUES) if signal_type == "scalar" else 0)
    feature_index = 0 if feature_set == "electron" else 1
    expected_seed = 720000 + point_index * 100 + feature_index * 10
    if any(int(row["random_seed"]) != expected_seed for row in candidates):
        raise SystemExit(f"wrong/inconsistent model seed for {key}")
    winner = max(
        candidates,
        key=lambda row: (
            float(row["validation_significance_improvement"]),
            float(row["validation_auc"]),
            row["model_profile"],
        ),
    )
    tag = f"{mass:.3f}".replace(".", "p")
    box_rows = []
    for box_path in sorted(
        (development / "baselines").glob(
            f"{signal_type}_m{tag}_{feature_set}_q*.csv"
        )
    ):
        if box_path.name.endswith("_candidates.csv"):
            continue
        with box_path.open(newline="") as handle:
            box = next(csv.DictReader(handle))
        if box.get("signal_type") != signal_type:
            raise SystemExit(f"box type mismatch in {box_path}")
        if not close_mass(box.get("mass_GeV", "nan"), mass):
            raise SystemExit(f"box mass mismatch in {box_path}")
        if box.get("feature_set") != feature_set:
            raise SystemExit(f"box feature mismatch in {box_path}")
        quantiles = int(box["quantiles"])
        finite_number(box, "validation_significance_improvement", box_path)
        finite_number(box, "training_significance_improvement", box_path)
        box_rows.append((quantiles, box_path, box))
    if {item[0] for item in box_rows} != EXPECTED_QUANTILES or len(box_rows) != 3:
        raise SystemExit(f"missing/duplicate box convergence grids for {key}")
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
    ratio = bdt_rz / box_rz if box_rz > 0 else 0.0
    coupling = 1.0 - (box_rz / bdt_rz) ** 0.5 if bdt_rz > 0 and box_rz > 0 else 0.0
    selected.append(
        {
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
        }
    )

expected = 44
if len(selected) != expected:
    raise SystemExit(f"expected {expected} selected models, found {len(selected)}")

output = development / "selected_models.csv"
output.parent.mkdir(parents=True, exist_ok=True)
with output.open("w", newline="") as handle:
    writer = csv.DictWriter(
        handle, fieldnames=selected[0].keys(), lineterminator="\n"
    )
    writer.writeheader()
    writer.writerows(selected)
print(f"wrote {len(selected)} selections to {output}")
