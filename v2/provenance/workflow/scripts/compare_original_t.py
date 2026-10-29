#!/usr/bin/env python3
"""Compare saved original and revised within-method gains from adding t."""

import os
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path


def read_rows(path):
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original", type=Path, default=Path(os.environ.get('DARK_PROJECT_ROOT', str(Path(__file__).resolve().parents[2]))))
    args = parser.parse_args()
    revision = Path(__file__).resolve().parents[1]
    old_path = args.original / "fair_study/rigorous/final/rigorous_final_metrics.csv"
    rates_path = args.original / "config/paper_cuts.csv"
    new_path = revision / "stratified_refit/summary.csv"
    original_rates = {float(r["mass_GeV"]): r for r in read_rows(rates_path)}
    old_rows = read_rows(old_path)
    old = {(r["signal_type"], float(r["mass_GeV"]), r["feature_set"]): r
           for r in old_rows}
    if len(old) != len(old_rows) or len(old) != 44:
        raise ValueError("Expected 44 unique original mass/type/input rows")
    new = {(r["signal_type"], float(r["mass_GeV"]), r["method"]): r
           for r in read_rows(new_path) if r["kind"] == "direct_t"}
    results = []
    rate_checks = []
    for signal, mass in sorted({(k[0], k[1]) for k in old}):
        electron = old[signal, mass, "electron"]
        with_t = old[signal, mass, "electron_qa2"]
        for method, column in (("cuts", "box_RZ"), ("bdt", "bdt_RZ")):
            before, after = float(electron[column]), float(with_t[column])
            original_gain = 100 * (after / before - 1)
            revised = new[signal, mass, method]
            revised_gain = float(revised["advantage_pct"])
            results.append(dict(
                signal_type=signal, mass_GeV=mass, method=method,
                original_RZ_electron=before, original_RZ_with_t=after,
                original_t_gain_pct=original_gain, new_t_gain_pct=revised_gain,
                change_percentage_points=revised_gain-original_gain,
                original_runs=1, new_runs=int(revised["independent_runs"]),
            ))
            rates = original_rates[mass]
            original_photon = float(rates["photon_effective_pb_at_epsilon_1e-6"])
            original_dis = float(rates["DIS_effective_pb_at_epsilon_1e-6_ZDC95"])
            revised_photon = float(revised["photon_xs_pb"])
            if not math.isclose(original_dis, float(revised["dis_xs_pb"]), abs_tol=1e-12):
                raise ValueError("DIS changed: cannot label this a photon-rate-only check")
            prefix = "box" if method == "cuts" else "bdt"

            def original_selection_rz(row, photon_rate):
                signal_eff = float(row[prefix + "_signal_efficiency"])
                photon_eff = float(row[prefix + "_photon_efficiency"])
                return signal_eff * math.sqrt((photon_rate + original_dis) /
                                              (photon_rate * photon_eff + original_dis))

            for row, saved in ((electron, before), (with_t, after)):
                if not math.isclose(original_selection_rz(row, original_photon), saved,
                                    rel_tol=1e-9, abs_tol=1e-10):
                    raise ValueError("Original rate/efficiency formula does not reproduce saved RZ")
            rate_only_gain = 100 * (original_selection_rz(with_t, revised_photon) /
                                   original_selection_rz(electron, revised_photon) - 1)
            rate_checks.append(dict(
                signal_type=signal, mass_GeV=mass, method=method,
                original_photon_rate_pb=original_photon,
                revised_photon_rate_pb=revised_photon, fixed_DIS_pb=original_dis,
                original_t_gain_pct=original_gain,
                original_selections_at_revised_rate_t_gain_pct=rate_only_gain,
                evaluation_rate_effect_percentage_points=rate_only_gain-original_gain,
                revised_study_t_gain_pct=revised_gain,
                remaining_difference_percentage_points=revised_gain-rate_only_gain,
                scope="Fixed original selections and original test efficiencies; no reselection or refitting",
            ))
    destination = revision / "original_comparison"
    destination.mkdir(exist_ok=True)
    with (destination / "t_gain.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(results[0]))
        writer.writeheader()
        writer.writerows(results)
    with (destination / "rate_check.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rate_checks[0]))
        writer.writeheader()
        writer.writerows(rate_checks)
    provenance = dict(
        formula="100 * (RZ_with_t / RZ_electron - 1)",
        quantity="relative significance gain from adding t to the same method",
        original_scope="Original full mass scan: one selected fit and test per input set",
        revised_scope="Geometric mean paired ratios across ten independent runs",
        original_normalization="Published effective photon rates, fixed unrejected DIS",
        revised_normalization="Independently calibrated own photon rates, fixed unrejected DIS",
        interpretation="Descriptive comparison across changed studies; not a matched uncertainty test",
        original_direct_t_intervals="Not reconstructed; separate input-set bootstrap rows cannot be assumed paired",
        rate_check_scope="Only photon normalization is varied with original selections and test efficiencies fixed; all original RZ values independently reproduced from efficiencies and published rates",
        rows=len(results),
        sources=[dict(path=str(p), sha256=hashlib.sha256(p.read_bytes()).hexdigest())
                 for p in (old_path, rates_path, new_path)],
    )
    (destination / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")
    lines = [
        "# Original and revised benefit of t", "",
        "Calculated from preserved numerical results; no new simulation or fitting.", "",
        "The original column refers to the full-scan fits behind original Figure 7,",
        "not to the separate ten-run t-inclusive summary. The revised column uses",
        "ten independent runs. Both columns measure 100 * (Z_with_t/Z_electron - 1).", "",
        "| Signal at 10 GeV | Method | Original gain | Revised gain |",
        "|---|---|---:|---:|",
    ]
    for row in results:
        if row["mass_GeV"] == 10:
            lines.append(f"| {row['signal_type']} | {row['method']} | "
                         f"{row['original_t_gain_pct']:.2f}% | {row['new_t_gain_pct']:.2f}% |")
    lines += ["", "Sampling, fitting, photon normalization and test statistics changed.",
              "These numbers establish the direction and magnitude in each saved study;",
              "they do not isolate a cause or establish agreement within uncertainty.",
              "No original direct-t confidence intervals have been reconstructed.", "",
              "All 44 comparisons are in t_gain.csv; source paths and hashes are in provenance.json.",
              "Likelihood was absent from the original paper and has no original comparison.", ""]
    lines += [
        "## Photon-rate-only check", "",
        "Original selections and test efficiencies are held fixed while replacing only",
        "the photon rate with the revised calibration. The DIS rate is unchanged.",
        "The original RZ values were reproduced independently from the saved efficiencies.", "",
        "| Signal at 10 GeV | Method | Original | Original selections, revised rate | Revised study |",
        "|---|---|---:|---:|---:|",
    ]
    for row in rate_checks:
        if row["mass_GeV"] == 10:
            lines.append(f"| {row['signal_type']} | {row['method']} | "
                         f"{row['original_t_gain_pct']:.2f}% | "
                         f"{row['original_selections_at_revised_rate_t_gain_pct']:.2f}% | "
                         f"{row['revised_study_t_gain_pct']:.2f}% |")
    lines += ["", "This isolates the evaluation effect of photon normalization for the old",
              "selections. It does not include normalization-dependent reselection, refitting,",
              "sampling changes, or a matched uncertainty test. The remaining difference",
              "cannot be assigned solely to improved training. Full values: rate_check.csv.", ""]
    (destination / "README.md").write_text("\n".join(lines))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
