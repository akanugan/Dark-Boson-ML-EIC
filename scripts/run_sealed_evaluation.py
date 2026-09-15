#!/usr/bin/env python3
import csv
import math
import subprocess
import sys
from pathlib import Path


def read_one(path):
    with path.open(newline="") as handle:
        return next(csv.DictReader(handle))


def close(left, right):
    left = float(left)
    right = float(right)
    return math.isfinite(left) and math.isfinite(right) and abs(left - right) <= 1.0e-10 * max(1.0, abs(left), abs(right))


root = Path(__file__).resolve().parents[1]
study = root / "fair_study" / "rigorous"
selected_path = study / "development_frozen" / "selected_models.csv"
sealed = root / "data" / "ml" / "sealed" / "root"
output = study / "final"
primary_bootstrap = int(sys.argv[1]) if len(sys.argv) > 1 else 50000
oracle_bootstrap = int(sys.argv[2]) if len(sys.argv) > 2 else 5000
validate_only = len(sys.argv) > 3 and sys.argv[3] == "--validate-only"
if len(sys.argv) > 3 and not validate_only:
    raise SystemExit("unknown argument")
if primary_bootstrap < 50000 or oracle_bootstrap < 500:
    raise SystemExit("insufficient frozen bootstrap counts")

with selected_path.open(newline="") as handle:
    choices = list(csv.DictReader(handle))
if len(choices) != 44:
    raise SystemExit(f"expected 44 frozen selections, found {len(choices)}")

with (root / "results" / "background_rates_from_table_I.csv").open(newline="") as handle:
    rates = {round(float(row["mass_GeV"]), 3): row for row in csv.DictReader(handle)}

for index, choice in enumerate(choices):
    signal_type = choice["signal_type"]
    mass = float(choice["mass_GeV"])
    feature = choice["feature_set"]
    if signal_type not in {"vector", "scalar"} or feature not in {"electron", "electron_qa2"}:
        raise SystemExit(f"invalid frozen selection row {index}")
    metrics_path = Path(choice["metrics_path"])
    weights_path = Path(choice["weights_path"])
    box_path = Path(choice["box_path"])
    for path in (metrics_path, weights_path, box_path):
        if not path.is_file():
            raise SystemExit(f"missing frozen input: {path}")
    metrics = read_one(metrics_path)
    box = read_one(box_path)
    for row, label in ((metrics, "BDT"), (box, "box")):
        if row["signal_type"] != signal_type or row["feature_set"] != feature or not close(row["mass_GeV"], mass):
            raise SystemExit(f"{label} metadata mismatch for row {index}")
    if metrics["model_profile"] != choice["selected_profile"]:
        raise SystemExit(f"profile mismatch for row {index}")
    if metrics["random_seed"] != choice["model_seed"] or metrics["evaluation_mode"] != "validation_all":
        raise SystemExit(f"model seed/mode mismatch for row {index}")
    if box["quantiles"] != choice["box_quantiles"]:
        raise SystemExit(f"box-grid mismatch for row {index}")
    rate = rates.get(round(mass, 3))
    if rate is None:
        raise SystemExit(f"missing background rate for mass {mass}")
    photon_xs = rate["photon_effective_pb_epsilon_1e-6"]
    dis_xs = rate["DIS_effective_pb_epsilon_1e-6_ZDC95"]
    for row, label in ((metrics, "BDT"), (box, "box")):
        if not close(row["photon_xs_pb"], photon_xs) or not close(row["dis_xs_pb"], dis_xs):
            raise SystemExit(f"{label} background-rate mismatch for row {index}")

    if validate_only:
        continue

    tag = f"{mass:.3f}".replace(".", "p")
    signal_test = sealed / f"{signal_type}_m{tag}_sealed.root"
    photon_test = sealed / f"photon_m{tag}_sealed.root"
    result = output / f"{signal_type}_m{tag}_{feature}.csv"
    log = output / f"{signal_type}_m{tag}_{feature}.log"
    command = [
        str(root / "bin" / "evaluate_fair_model"),
        str(signal_test),
        str(photon_test),
        str(weights_path),
        str(metrics_path),
        str(box_path),
        str(result),
        feature,
        photon_xs,
        dis_xs,
        str(primary_bootstrap if feature == "electron" else oracle_bootstrap),
        str(960000 + index),
    ]
    with log.open("w") as stream:
        subprocess.run(command, check=True, stdout=stream, stderr=subprocess.STDOUT)
    print(f"sealed evaluation complete: {signal_type} {mass:g} {feature}", flush=True)

if validate_only:
    print(f"validated {len(choices)} frozen selections without opening sealed data")
