#!/usr/bin/env python3
"""Select and summarize the exact-t independent-seed robustness study."""

from __future__ import annotations

import argparse
import csv
import math
import random
import sys
from collections import defaultdict
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
import summarize_seed_robustness as base  # noqa: E402


FEATURE_SET = "electron_qa2"
EXPECTED_GROUPS = {("vector", 10.0), ("scalar", 10.0)}


def select_profile(args: argparse.Namespace) -> None:
    profiles = tuple(item.strip() for item in args.profiles.split(",") if item.strip())
    if profiles != base.FROZEN_PROFILES:
        raise ValueError("profile list must remain frozen")
    candidates = []
    expected_point = None
    for rank, profile in enumerate(profiles):
        path = args.models_dir / profile / "metrics.csv"
        row = base.read_row(path)
        if row.get("model_profile") != profile or row.get("feature_set") != FEATURE_SET:
            raise ValueError(f"profile metadata mismatch in {path}")
        if row.get("evaluation_mode") != "validation_all":
            raise ValueError(f"profile selection is not validation-only in {path}")
        point = (row.get("signal_type", ""), row.get("mass_GeV", ""))
        if expected_point is None:
            expected_point = point
        elif point != expected_point:
            raise ValueError(f"mixed signal or mass in {args.models_dir}")
        score = base.number(row, "validation_significance_improvement", path)
        base.number(row, "validation_threshold", path)
        candidates.append((rank, profile, path, row, score))
    selected = max(candidates, key=lambda item: (item[4], -item[0]))
    base.write_csv(args.output, list(selected[3].keys()), [selected[3]])
    base.write_csv(
        args.output.with_name(args.output.stem + "_profile_candidates.csv"),
        ["frozen_rank", "model_profile", "validation_RZ", "validation_threshold", "selected", "metrics_path"],
        [
            {
                "frozen_rank": rank,
                "model_profile": profile,
                "validation_RZ": score,
                "validation_threshold": row["validation_threshold"],
                "selected": int(profile == selected[1]),
                "metrics_path": str(path),
            }
            for rank, profile, path, row, score in candidates
        ],
    )
    print(selected[1])


def select_box(args: argparse.Namespace) -> None:
    grids = tuple(int(item.strip()) for item in args.grids.split(",") if item.strip())
    if grids != base.FROZEN_BOX_GRIDS:
        raise ValueError("box-grid list must remain frozen")
    candidates = []
    expected_point = None
    for rank, grid in enumerate(grids):
        path = args.boxes_dir / f"q{grid}.csv"
        row = base.read_row(path)
        if row.get("feature_set") != FEATURE_SET or base.integer(row, "quantiles", path) != grid:
            raise ValueError(f"box-grid metadata mismatch in {path}")
        point = (row.get("signal_type", ""), row.get("mass_GeV", ""))
        if expected_point is None:
            expected_point = point
        elif point != expected_point:
            raise ValueError(f"mixed signal or mass in {args.boxes_dir}")
        validation = base.number(row, "validation_significance_improvement", path)
        training = base.number(row, "training_significance_improvement", path)
        candidates.append((rank, grid, path, row, validation, training))
    selected = max(candidates, key=lambda item: (item[4], item[5], -item[0]))
    base.write_csv(args.output, list(selected[3].keys()), [selected[3]])
    base.write_csv(
        args.output.with_name(args.output.stem + "_grid_candidates.csv"),
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


def load_exact_t_replicate(path: Path) -> dict:
    original_read_row = base.read_row

    def normalized_read_row(source: Path) -> dict[str, str]:
        row = original_read_row(source)
        if row.get("feature_set") == FEATURE_SET:
            row["feature_set"] = "electron"
        return row

    base.read_row = normalized_read_row
    try:
        record = base.load_replicate(path)
    finally:
        base.read_row = original_read_row
    record["feature_set"] = FEATURE_SET
    return record


def summarize(args: argparse.Namespace) -> None:
    run_dir = args.run_dir.resolve()
    config = base.read_row(run_dir / "run_config.csv")
    expected_replicates = int(config["replicates"])
    expected_paired_bootstraps = int(config["paired_bootstraps"])
    if expected_replicates < 10 or config.get("feature_set") != FEATURE_SET:
        raise ValueError("exact-t robustness study requires at least ten replicas")
    metadata_paths = sorted(run_dir.glob("rep_*/*/point_metadata.csv"))
    records = [load_exact_t_replicate(path) for path in metadata_paths]
    groups: dict[tuple[str, float], list[dict]] = defaultdict(list)
    for record in records:
        if len(record["bootstrap_logs"]) != expected_paired_bootstraps:
            raise ValueError("paired-bootstrap count mismatch")
        groups[(record["signal_type"], record["mass_GeV"])].append(record)
    if set(groups) != EXPECTED_GROUPS:
        raise ValueError(f"benchmark set mismatch: {sorted(groups)}")
    for key, items in groups.items():
        ids = sorted(item["replicate"] for item in items)
        if ids != list(range(1, expected_replicates + 1)):
            raise ValueError(f"incomplete replicas for {key}: {ids}")

    records.sort(key=lambda item: (0 if item["signal_type"] == "vector" else 1, item["replicate"]))
    base.write_csv(
        run_dir / "replicate_metrics.csv",
        base.REPLICATE_FIELDS,
        [{field: record[field] for field in base.REPLICATE_FIELDS} for record in records],
    )

    generator = random.Random(args.bootstrap_seed)
    summaries = []
    aggregate_rows = []
    for key in sorted(groups, key=lambda item: 0 if item[0] == "vector" else 1):
        items = sorted(groups[key], key=lambda item: item["replicate"])
        summary, ratios, couplings = base.summarize_group(
            items, args.bootstrap_replicates, args.bootstrap_seed, generator
        )
        familywise_lower = base.quantile(couplings, 0.05 / len(EXPECTED_GROUPS))
        statistical = familywise_lower > 0.0
        practical = familywise_lower > 0.01
        equivalent = summary["hierarchical_coupling_q025"] >= -0.01 and summary["hierarchical_coupling_q975"] <= 0.01
        summary["familywise_one_sided_coupling_lower"] = familywise_lower
        summary["statistical_superiority"] = int(statistical)
        summary["practical_superiority_gt_1pct_coupling"] = int(practical)
        summary["practical_equivalence_within_1pct_coupling"] = int(equivalent)
        summary["verdict"] = (
            "practical BDT superiority" if practical else
            "statistical but sub-1pct BDT superiority" if statistical else
            "practical equivalence" if equivalent else
            "no demonstrated BDT superiority"
        )
        summaries.append(summary)
        for index, (ratio, coupling) in enumerate(zip(ratios, couplings)):
            aggregate_rows.append({
                "signal_type": key[0], "mass_GeV": key[1],
                "bootstrap_replicate": index, "RZ_ratio": ratio,
                "coupling_advantage": coupling,
            })

    base.write_csv(run_dir / "benchmark_summary.csv", base.SUMMARY_FIELDS, summaries)
    base.write_csv(
        run_dir / "hierarchical_bootstrap.csv",
        ["signal_type", "mass_GeV", "bootstrap_replicate", "RZ_ratio", "coupling_advantage"],
        aggregate_rows,
    )
    lines = [
        "# Exact-t seed-robust BDT-versus-cuts study", "",
        f"Run: `{run_dir.name}`; complete replicas per benchmark: {expected_replicates}.",
        "Both methods use recoil-electron variables plus exact generator-level t.", "",
        "| Signal | Mass [GeV] | RZ ratio | Coupling advantage, median [95%] | Familywise lower | Verdict |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for row in summaries:
        lines.append(
            f"| {row['signal_type']} | {row['mass_GeV']:g} | {row['RZ_ratio_geometric_mean']:.5f} | "
            f"{100*row['hierarchical_coupling_q50']:+.3f}% "
            f"[{100*row['hierarchical_coupling_q025']:+.3f}%, {100*row['hierarchical_coupling_q975']:+.3f}%] | "
            f"{100*row['familywise_one_sided_coupling_lower']:+.3f}% | {row['verdict']} |"
        )
    lines.extend([
        "", "The intervals use a hierarchical paired bootstrap over complete generator/training replicas and paired event resamples.",
        "The result remains conditional parton-level evidence with exact t as an oracle input.",
    ])
    (run_dir / "t_seed_robustness_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote exact-t robustness summary under {run_dir}")


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    subs = result.add_subparsers(dest="command", required=True)
    profile = subs.add_parser("select-profile")
    profile.add_argument("--models-dir", type=Path, required=True)
    profile.add_argument("--profiles", required=True)
    profile.add_argument("--output", type=Path, required=True)
    profile.set_defaults(function=select_profile)
    box = subs.add_parser("select-box")
    box.add_argument("--boxes-dir", type=Path, required=True)
    box.add_argument("--grids", required=True)
    box.add_argument("--output", type=Path, required=True)
    box.set_defaults(function=select_box)
    summary = subs.add_parser("summarize")
    summary.add_argument("--run-dir", type=Path, required=True)
    summary.add_argument("--bootstrap-replicates", type=int, default=20000)
    summary.add_argument("--bootstrap-seed", type=int, required=True)
    summary.set_defaults(function=summarize)
    return result


def main() -> None:
    args = parser().parse_args()
    args.function(args)


if __name__ == "__main__":
    main()
