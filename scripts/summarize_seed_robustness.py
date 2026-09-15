#!/usr/bin/env python3
"""Select frozen BDT profiles and summarize paired seed-robustness tests."""

from __future__ import annotations

import argparse
import csv
import math
import random
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable


FROZEN_PROFILES = ("depth2", "depth3", "depth4", "depth3_800")
FROZEN_BOX_GRIDS = (40, 80, 160)


def read_row(path: Path) -> dict[str, str]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        row = next(reader, None)
    if row is None:
        raise ValueError(f"missing data row: {path}")
    return dict(row)


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def number(row: dict[str, str], field: str, source: Path) -> float:
    if field not in row or row[field] == "":
        raise ValueError(f"missing {field} in {source}")
    value = float(row[field])
    if not math.isfinite(value):
        raise ValueError(f"non-finite {field} in {source}: {value}")
    return value


def integer(row: dict[str, str], field: str, source: Path) -> int:
    value = number(row, field, source)
    if value != int(value):
        raise ValueError(f"non-integer {field} in {source}: {value}")
    return int(value)


def quantile(values: Iterable[float], probability: float) -> float:
    ordered = sorted(values)
    if not ordered:
        raise ValueError("cannot take a quantile of an empty sample")
    position = probability * (len(ordered) - 1)
    lower = math.floor(position)
    upper = math.ceil(position)
    fraction = position - lower
    return ordered[lower] * (1.0 - fraction) + ordered[upper] * fraction


def write_csv(path: Path, fieldnames: list[str], rows: Iterable[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=fieldnames, lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)


def select_profile(args: argparse.Namespace) -> None:
    profiles = tuple(item.strip() for item in args.profiles.split(",") if item.strip())
    if profiles != FROZEN_PROFILES:
        raise ValueError(
            "profile list must remain frozen as " + ",".join(FROZEN_PROFILES)
        )

    candidates: list[tuple[int, str, Path, dict[str, str], float]] = []
    expected_point: tuple[str, str] | None = None
    for rank, profile in enumerate(profiles):
        metrics_path = args.models_dir / profile / "metrics.csv"
        row = read_row(metrics_path)
        if row.get("model_profile") != profile:
            raise ValueError(f"profile mismatch in {metrics_path}")
        if row.get("feature_set") != "electron":
            raise ValueError(f"non-primary feature set in {metrics_path}")
        if row.get("evaluation_mode") != "validation_all":
            raise ValueError(f"profile selection is not validation-only in {metrics_path}")
        point = (row.get("signal_type", ""), row.get("mass_GeV", ""))
        if expected_point is None:
            expected_point = point
        elif point != expected_point:
            raise ValueError(f"mixed signal or mass in {args.models_dir}")
        score = number(row, "validation_significance_improvement", metrics_path)
        number(row, "validation_threshold", metrics_path)
        candidates.append((rank, profile, metrics_path, row, score))

    # Frozen-order tie break. No final-test information is read here.
    selected = max(candidates, key=lambda item: (item[4], -item[0]))
    selected_row = selected[3]
    fieldnames = list(selected_row.keys())
    write_csv(args.output, fieldnames, [selected_row])

    candidate_path = args.output.with_name(
        args.output.stem + "_profile_candidates.csv"
    )
    candidate_rows = []
    for rank, profile, metrics_path, row, score in candidates:
        candidate_rows.append(
            {
                "frozen_rank": rank,
                "model_profile": profile,
                "validation_RZ": score,
                "validation_threshold": row["validation_threshold"],
                "selected": int(profile == selected[1]),
                "metrics_path": str(metrics_path),
            }
        )
    write_csv(
        candidate_path,
        [
            "frozen_rank",
            "model_profile",
            "validation_RZ",
            "validation_threshold",
            "selected",
            "metrics_path",
        ],
        candidate_rows,
    )
    print(selected[1])


def select_box(args: argparse.Namespace) -> None:
    grids = tuple(int(item.strip()) for item in args.grids.split(",") if item.strip())
    if grids != FROZEN_BOX_GRIDS:
        raise ValueError(
            "box-grid list must remain frozen as "
            + ",".join(str(item) for item in FROZEN_BOX_GRIDS)
        )
    candidates = []
    expected_point = None
    for rank, grid in enumerate(grids):
        path = args.boxes_dir / f"q{grid}.csv"
        row = read_row(path)
        if row.get("feature_set") != "electron" or integer(row, "quantiles", path) != grid:
            raise ValueError(f"box-grid metadata mismatch in {path}")
        point = (row.get("signal_type", ""), row.get("mass_GeV", ""))
        if expected_point is None:
            expected_point = point
        elif point != expected_point:
            raise ValueError(f"mixed signal or mass in {args.boxes_dir}")
        validation = number(row, "validation_significance_improvement", path)
        training = number(row, "training_significance_improvement", path)
        candidates.append((rank, grid, path, row, validation, training))
    selected = max(candidates, key=lambda item: (item[4], item[5], -item[0]))
    write_csv(args.output, list(selected[3].keys()), [selected[3]])
    candidate_path = args.output.with_name(args.output.stem + "_grid_candidates.csv")
    write_csv(
        candidate_path,
        ["frozen_rank", "quantiles", "validation_RZ", "training_RZ", "selected", "path"],
        [
            {
                "frozen_rank": rank,
                "quantiles": grid,
                "validation_RZ": validation,
                "training_RZ": training,
                "selected": int(grid == selected[1]),
                "path": str(path),
            }
            for rank, grid, path, row, validation, training in candidates
        ],
    )
    print(selected[1])


def load_replicate(metadata_path: Path) -> dict:
    point_dir = metadata_path.parent
    metadata = read_row(metadata_path)
    paired_path = point_dir / "paired_test.csv"
    paired = read_row(paired_path)
    model_path = point_dir / "selected_model_metrics.csv"
    model = read_row(model_path)
    box_path = point_dir / "selected_box_metrics.csv"
    box = read_row(box_path)
    bootstrap_path = point_dir / "paired_test_bootstrap.csv"
    bootstrap_rows = read_rows(bootstrap_path)
    if not bootstrap_rows:
        raise ValueError(f"empty paired bootstrap: {bootstrap_path}")

    if metadata.get("feature_set") != "electron":
        raise ValueError(f"non-primary feature set in {metadata_path}")
    if paired.get("feature_set") != "electron":
        raise ValueError(f"non-primary paired result in {paired_path}")
    if model.get("model_profile") != metadata.get("selected_profile"):
        raise ValueError(f"selected-profile mismatch in {point_dir}")
    if model.get("evaluation_mode") != "validation_all":
        raise ValueError(f"model selection was not validation-only in {point_dir}")
    if integer(box, "quantiles", box_path) != int(metadata["selected_box_quantiles"]):
        raise ValueError(f"selected box-grid mismatch in {point_dir}")

    bootstrap_logs = []
    for row in bootstrap_rows:
        bootstrap_ratio = number(row, "RZ_ratio", bootstrap_path)
        bootstrap_log = number(row, "log_RZ_ratio", bootstrap_path)
        if (
            bootstrap_ratio <= 0.0
            or abs(math.log(bootstrap_ratio) - bootstrap_log) > 1.0e-7
        ):
            raise ValueError(f"invalid paired bootstrap ratio in {bootstrap_path}")
        bootstrap_logs.append(bootstrap_log)

    ratio = number(paired, "RZ_ratio", paired_path)
    log_ratio = number(paired, "log_RZ_ratio", paired_path)
    if ratio <= 0.0 or abs(math.log(ratio) - log_ratio) > 1.0e-7:
        raise ValueError(f"inconsistent RZ ratio in {paired_path}")

    return {
        "signal_type": metadata["signal_type"],
        "mass_GeV": float(metadata["mass_GeV"]),
        "replicate": int(metadata["replicate"]),
        "feature_set": metadata["feature_set"],
        "selected_profile": metadata["selected_profile"],
        "selected_box_quantiles": int(metadata["selected_box_quantiles"]),
        "validation_threshold": number(
            model, "validation_threshold", model_path
        ),
        "bdt_validation_RZ": number(
            model, "validation_significance_improvement", model_path
        ),
        "box_validation_RZ": number(
            box, "validation_significance_improvement", box_path
        ),
        "train_signal_entries": integer(
            model, "train_signal_entries", model_path
        ),
        "train_background_entries": integer(
            model, "train_background_entries", model_path
        ),
        "validation_signal_entries": integer(
            model, "evaluation_signal_entries", model_path
        ),
        "validation_background_entries": integer(
            model, "evaluation_background_entries", model_path
        ),
        "test_signal_entries": integer(
            paired, "test_signal_entries", paired_path
        ),
        "test_background_entries": integer(
            paired, "test_background_entries", paired_path
        ),
        "signal_neff": number(paired, "signal_neff", paired_path),
        "background_neff": number(paired, "background_neff", paired_path),
        "signal_max_weight_fraction": number(
            paired, "signal_max_weight_fraction", paired_path
        ),
        "background_max_weight_fraction": number(
            paired, "background_max_weight_fraction", paired_path
        ),
        "bdt_signal_efficiency": number(
            paired, "bdt_signal_efficiency", paired_path
        ),
        "bdt_photon_efficiency": number(
            paired, "bdt_photon_efficiency", paired_path
        ),
        "bdt_RZ": number(paired, "bdt_RZ", paired_path),
        "box_signal_efficiency": number(
            paired, "box_signal_efficiency", paired_path
        ),
        "box_photon_efficiency": number(
            paired, "box_photon_efficiency", paired_path
        ),
        "box_RZ": number(paired, "box_RZ", paired_path),
        "RZ_ratio": ratio,
        "log_RZ_ratio": log_ratio,
        "coupling_advantage": number(
            paired, "coupling_advantage", paired_path
        ),
        "paired_RZ_ratio_q025": number(
            paired, "RZ_ratio_q025", paired_path
        ),
        "paired_RZ_ratio_q50": number(
            paired, "RZ_ratio_q50", paired_path
        ),
        "paired_RZ_ratio_q975": number(
            paired, "RZ_ratio_q975", paired_path
        ),
        "paired_coupling_q025": number(
            paired, "coupling_q025", paired_path
        ),
        "paired_coupling_q50": number(
            paired, "coupling_q50", paired_path
        ),
        "paired_coupling_q975": number(
            paired, "coupling_q975", paired_path
        ),
        "signal_train_seed": int(metadata["signal_train_seed"]),
        "signal_validation_seed": int(metadata["signal_validation_seed"]),
        "signal_test_seed": int(metadata["signal_test_seed"]),
        "photon_train_seed": int(metadata["photon_train_seed"]),
        "photon_validation_seed": int(metadata["photon_validation_seed"]),
        "photon_test_seed": int(metadata["photon_test_seed"]),
        "tmva_seed": int(metadata["tmva_seed"]),
        "box_seed": int(metadata["box_seed"]),
        "paired_bootstrap_seed": int(metadata["paired_bootstrap_seed"]),
        "bootstrap_logs": bootstrap_logs,
    }


REPLICATE_FIELDS = [
    "signal_type",
    "mass_GeV",
    "replicate",
    "feature_set",
    "selected_profile",
    "selected_box_quantiles",
    "validation_threshold",
    "bdt_validation_RZ",
    "box_validation_RZ",
    "train_signal_entries",
    "train_background_entries",
    "validation_signal_entries",
    "validation_background_entries",
    "test_signal_entries",
    "test_background_entries",
    "signal_neff",
    "background_neff",
    "signal_max_weight_fraction",
    "background_max_weight_fraction",
    "bdt_signal_efficiency",
    "bdt_photon_efficiency",
    "bdt_RZ",
    "box_signal_efficiency",
    "box_photon_efficiency",
    "box_RZ",
    "RZ_ratio",
    "log_RZ_ratio",
    "coupling_advantage",
    "paired_RZ_ratio_q025",
    "paired_RZ_ratio_q50",
    "paired_RZ_ratio_q975",
    "paired_coupling_q025",
    "paired_coupling_q50",
    "paired_coupling_q975",
    "signal_train_seed",
    "signal_validation_seed",
    "signal_test_seed",
    "photon_train_seed",
    "photon_validation_seed",
    "photon_test_seed",
    "tmva_seed",
    "box_seed",
    "paired_bootstrap_seed",
]


SUMMARY_FIELDS = [
    "signal_type",
    "mass_GeV",
    "replicates",
    "hierarchical_bootstrap_replicates",
    "hierarchical_bootstrap_seed",
    "selected_profile_counts",
    "selected_box_grid_counts",
    "bdt_RZ_geometric_mean",
    "box_RZ_geometric_mean",
    "RZ_ratio_geometric_mean",
    "between_seed_sd_log_RZ_ratio",
    "seed_win_fraction",
    "hierarchical_RZ_ratio_q025",
    "hierarchical_RZ_ratio_q16",
    "hierarchical_RZ_ratio_q50",
    "hierarchical_RZ_ratio_q84",
    "hierarchical_RZ_ratio_q975",
    "hierarchical_coupling_q025",
    "hierarchical_coupling_q16",
    "hierarchical_coupling_q50",
    "hierarchical_coupling_q84",
    "hierarchical_coupling_q975",
    "familywise_one_sided_coupling_lower",
    "replicates_with_paired_95pct_RZ_ratio_above_one",
    "min_signal_neff",
    "min_background_neff",
    "max_signal_weight_fraction",
    "max_background_weight_fraction",
    "statistical_superiority",
    "practical_superiority_gt_1pct_coupling",
    "practical_equivalence_within_1pct_coupling",
    "verdict",
]


def summarize_group(
    items: list[dict], bootstrap_replicates: int, bootstrap_seed: int,
    generator: random.Random
) -> tuple[dict, list[float], list[float]]:
    nominal_logs = [item["log_RZ_ratio"] for item in items]
    bdt_logs = [math.log(item["bdt_RZ"]) for item in items]
    box_logs = [math.log(item["box_RZ"]) for item in items]

    aggregate_logs: list[float] = []
    for _ in range(bootstrap_replicates):
        sampled = [generator.choice(items) for _ in items]
        aggregate_logs.append(
            sum(generator.choice(item["bootstrap_logs"]) for item in sampled)
            / len(sampled)
        )
    aggregate_ratios = [math.exp(value) for value in aggregate_logs]
    aggregate_couplings = [1.0 - math.exp(-0.5 * value) for value in aggregate_logs]

    ratio_q025 = quantile(aggregate_ratios, 0.025)
    ratio_q975 = quantile(aggregate_ratios, 0.975)
    coupling_q025 = quantile(aggregate_couplings, 0.025)
    coupling_q975 = quantile(aggregate_couplings, 0.975)
    familywise_lower = quantile(aggregate_couplings, 0.05 / 4)
    statistical = familywise_lower > 0.0
    practical = familywise_lower > 0.01
    equivalent = coupling_q025 >= -0.01 and coupling_q975 <= 0.01
    if practical:
        verdict = "practical BDT superiority"
    elif statistical:
        verdict = "statistical but sub-1pct BDT superiority"
    elif equivalent:
        verdict = "practical equivalence"
    else:
        verdict = "no demonstrated BDT superiority"

    profile_counts = Counter(item["selected_profile"] for item in items)
    profile_text = ";".join(
        f"{profile}:{profile_counts.get(profile, 0)}" for profile in FROZEN_PROFILES
    )
    box_counts = Counter(item["selected_box_quantiles"] for item in items)
    box_text = ";".join(
        f"q{grid}:{box_counts.get(grid, 0)}" for grid in FROZEN_BOX_GRIDS
    )
    summary = {
        "signal_type": items[0]["signal_type"],
        "mass_GeV": items[0]["mass_GeV"],
        "replicates": len(items),
        "hierarchical_bootstrap_replicates": bootstrap_replicates,
        "hierarchical_bootstrap_seed": bootstrap_seed,
        "selected_profile_counts": profile_text,
        "selected_box_grid_counts": box_text,
        "bdt_RZ_geometric_mean": math.exp(statistics.fmean(bdt_logs)),
        "box_RZ_geometric_mean": math.exp(statistics.fmean(box_logs)),
        "RZ_ratio_geometric_mean": math.exp(statistics.fmean(nominal_logs)),
        "between_seed_sd_log_RZ_ratio": (
            statistics.stdev(nominal_logs) if len(nominal_logs) > 1 else 0.0
        ),
        "seed_win_fraction": statistics.fmean(
            item["RZ_ratio"] > 1.0 for item in items
        ),
        "hierarchical_RZ_ratio_q025": ratio_q025,
        "hierarchical_RZ_ratio_q16": quantile(aggregate_ratios, 0.16),
        "hierarchical_RZ_ratio_q50": quantile(aggregate_ratios, 0.50),
        "hierarchical_RZ_ratio_q84": quantile(aggregate_ratios, 0.84),
        "hierarchical_RZ_ratio_q975": ratio_q975,
        "hierarchical_coupling_q025": coupling_q025,
        "hierarchical_coupling_q16": quantile(aggregate_couplings, 0.16),
        "hierarchical_coupling_q50": quantile(aggregate_couplings, 0.50),
        "hierarchical_coupling_q84": quantile(aggregate_couplings, 0.84),
        "hierarchical_coupling_q975": coupling_q975,
        "familywise_one_sided_coupling_lower": familywise_lower,
        "replicates_with_paired_95pct_RZ_ratio_above_one": sum(
            item["paired_RZ_ratio_q025"] > 1.0 for item in items
        ),
        "min_signal_neff": min(item["signal_neff"] for item in items),
        "min_background_neff": min(item["background_neff"] for item in items),
        "max_signal_weight_fraction": max(
            item["signal_max_weight_fraction"] for item in items
        ),
        "max_background_weight_fraction": max(
            item["background_max_weight_fraction"] for item in items
        ),
        "statistical_superiority": int(statistical),
        "practical_superiority_gt_1pct_coupling": int(practical),
        "practical_equivalence_within_1pct_coupling": int(equivalent),
        "verdict": verdict,
    }
    return summary, aggregate_ratios, aggregate_couplings


def summarize(args: argparse.Namespace) -> None:
    run_dir = args.run_dir.resolve()
    if not run_dir.is_dir():
        raise ValueError(f"run directory does not exist: {run_dir}")
    config_path = run_dir / "run_config.csv"
    config = read_row(config_path)
    expected_replicates = int(config["replicates"])
    expected_paired_bootstraps = int(config["paired_bootstraps"])
    if expected_replicates < 10:
        raise ValueError("publication robustness summary requires at least 10 replicas")
    if config.get("feature_set") != "electron":
        raise ValueError("primary robustness study must use electron features")
    if config.get("profiles") != ";".join(FROZEN_PROFILES):
        raise ValueError("run did not use the frozen model profiles")
    if config.get("box_quantile_grids") != ";".join(
        str(item) for item in FROZEN_BOX_GRIDS
    ):
        raise ValueError("run did not use the frozen box grids")

    metadata_paths = sorted(run_dir.glob("rep_*/*/point_metadata.csv"))
    if not metadata_paths:
        raise ValueError(f"no completed point metadata found under {run_dir}")
    records = [load_replicate(path) for path in metadata_paths]
    for record in records:
        if len(record["bootstrap_logs"]) != expected_paired_bootstraps:
            raise ValueError(
                "paired-bootstrap count mismatch for "
                f"{record['signal_type']} m={record['mass_GeV']} "
                f"replicate={record['replicate']}"
            )
    keys = [
        (item["signal_type"], item["mass_GeV"], item["replicate"])
        for item in records
    ]
    if len(keys) != len(set(keys)):
        raise ValueError("duplicate benchmark/replicate result")

    groups: dict[tuple[str, float], list[dict]] = defaultdict(list)
    for record in records:
        groups[(record["signal_type"], record["mass_GeV"])].append(record)
    expected_groups = {
        ("vector", 1.0),
        ("vector", 10.0),
        ("scalar", 1.0),
        ("scalar", 6.31),
    }
    if set(groups) != expected_groups:
        raise ValueError(f"benchmark set mismatch: {sorted(groups)}")
    for key, items in groups.items():
        replicate_ids = sorted(item["replicate"] for item in items)
        if replicate_ids != list(range(1, expected_replicates + 1)):
            raise ValueError(f"incomplete replicas for {key}: {replicate_ids}")

    sort_key = lambda item: (
        0 if item["signal_type"] == "vector" else 1,
        item["mass_GeV"],
        item["replicate"],
    )
    records.sort(key=sort_key)
    replicate_rows = [
        {field: record[field] for field in REPLICATE_FIELDS} for record in records
    ]
    write_csv(run_dir / "replicate_metrics.csv", REPLICATE_FIELDS, replicate_rows)

    generator = random.Random(args.bootstrap_seed)
    summaries = []
    aggregate_rows = []
    for key in sorted(groups, key=lambda item: (0 if item[0] == "vector" else 1, item[1])):
        items = sorted(groups[key], key=lambda item: item["replicate"])
        summary, ratios, couplings = summarize_group(
            items, args.bootstrap_replicates, args.bootstrap_seed, generator
        )
        summaries.append(summary)
        for index, (ratio, coupling) in enumerate(zip(ratios, couplings)):
            aggregate_rows.append(
                {
                    "signal_type": key[0],
                    "mass_GeV": key[1],
                    "bootstrap_replicate": index,
                    "RZ_ratio": ratio,
                    "coupling_advantage": coupling,
                }
            )

    write_csv(run_dir / "benchmark_summary.csv", SUMMARY_FIELDS, summaries)
    write_csv(
        run_dir / "hierarchical_bootstrap.csv",
        [
            "signal_type",
            "mass_GeV",
            "bootstrap_replicate",
            "RZ_ratio",
            "coupling_advantage",
        ],
        aggregate_rows,
    )

    lines = [
        "# Seed-robust fair BDT-versus-cuts study",
        "",
        f"Run: `{run_dir.name}`. Independent complete replicas: {expected_replicates}.",
        f"Paired event bootstraps per replica: {expected_paired_bootstraps}; "
        f"hierarchical draws: {args.bootstrap_replicates}; hierarchical seed: "
        f"{args.bootstrap_seed}.",
        "Primary features are recoil-electron quantities only. Each method uses",
        "the same weighted training, validation, and sealed-test samples.",
        "BDT profile/threshold and rectangular bounds are selected on validation;",
        "the final comparison is paired on the same test events.",
        "",
        "| Signal | Mass [GeV] | Selected profiles | Geometric mean RZ ratio | Hierarchical 95% interval | Coupling advantage, median [95%] | Verdict |",
        "|---|---:|---|---:|---:|---:|---|",
    ]
    for row in summaries:
        ratio_interval = (
            f"[{row['hierarchical_RZ_ratio_q025']:.4f}, "
            f"{row['hierarchical_RZ_ratio_q975']:.4f}]"
        )
        coupling_interval = (
            f"{100 * row['hierarchical_coupling_q50']:+.2f}% "
            f"[{100 * row['hierarchical_coupling_q025']:+.2f}%, "
            f"{100 * row['hierarchical_coupling_q975']:+.2f}%]"
        )
        lines.append(
            f"| {row['signal_type']} | {row['mass_GeV']:g} | "
            f"{row['selected_profile_counts']} | "
            f"{row['RZ_ratio_geometric_mean']:.4f} | {ratio_interval} | "
            f"{coupling_interval} | {row['verdict']} |"
        )
    lines.extend(
        [
            "",
            "Intervals use a hierarchical paired bootstrap: complete generator/",
            "training replicas are resampled, then one paired event-bootstrap draw",
            "is taken within every sampled replica. The paired event bootstrap keeps",
            "BDT and rectangular decisions on each event together.",
            "",
            "This is conditional parton-level evidence after Table I preselection.",
            "It does not repair the photon-model mismatch, missing event-level DIS,",
            "selected-signal discrepancy, scalar-amplitude validation, or absent",
            "detector response. It must not be described as detector-level EIC reach.",
        ]
    )
    (run_dir / "seed_robustness_summary.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    print(f"wrote robustness summary under {run_dir}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    select = subparsers.add_parser(
        "select-profile", help="select one frozen BDT profile on validation R_Z"
    )
    select.add_argument("--models-dir", type=Path, required=True)
    select.add_argument("--profiles", required=True)
    select.add_argument("--output", type=Path, required=True)
    select.set_defaults(function=select_profile)

    select_box_parser = subparsers.add_parser(
        "select-box", help="select a frozen box-grid resolution on validation R_Z"
    )
    select_box_parser.add_argument("--boxes-dir", type=Path, required=True)
    select_box_parser.add_argument("--grids", required=True)
    select_box_parser.add_argument("--output", type=Path, required=True)
    select_box_parser.set_defaults(function=select_box)

    summary = subparsers.add_parser(
        "summarize", help="aggregate paired final-test results across seeds"
    )
    summary.add_argument("--run-dir", type=Path, required=True)
    summary.add_argument("--bootstrap-replicates", type=int, default=20000)
    summary.add_argument("--bootstrap-seed", type=int, default=271828)
    summary.set_defaults(function=summarize)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if getattr(args, "bootstrap_replicates", 100) < 100:
        parser.error("--bootstrap-replicates must be at least 100")
    args.function(args)


if __name__ == "__main__":
    main()
