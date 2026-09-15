#!/usr/bin/env python3
"""Fail fast if the exported signal table is internally inconsistent."""

import csv
import math
import sys
from collections import Counter
from pathlib import Path


def fail(message: str) -> None:
    raise SystemExit(f"validation failed: {message}")


def main() -> None:
    project = Path(__file__).resolve().parents[1]
    events_path = project / "data" / "signal_events.csv"
    cutflow_path = project / "results" / "signal_cutflow.csv"
    required = {
        "event_id", "process", "signal_type", "mass_GeV", "coupling",
        "event_weight_pb", "electron_pt_GeV", "electron_eta",
        "electron_energy_GeV", "Qe2_GeV2", "QA2_GeV2", "pair_mass_GeV",
        "pass_Qe2", "pass_pt", "pass_eta", "pass_energy", "pass_all", "split",
    }
    counts = Counter()
    ids = set()
    with events_path.open(newline="") as source:
        reader = csv.DictReader(source)
        if not required.issubset(reader.fieldnames or []):
            fail("event table is missing required columns")
        for row in reader:
            event_id = row["event_id"]
            if event_id in ids:
                fail(f"duplicate event_id {event_id}")
            ids.add(event_id)
            if row["process"] != "signal":
                fail(f"unexpected process in {event_id}")
            if row["split"] not in {"train", "validation", "test"}:
                fail(f"invalid split in {event_id}")
            values = [float(row[name]) for name in (
                "mass_GeV", "coupling", "event_weight_pb", "electron_pt_GeV",
                "electron_eta", "electron_energy_GeV", "Qe2_GeV2", "QA2_GeV2",
                "pair_mass_GeV",
            )]
            if not all(math.isfinite(value) for value in values):
                fail(f"non-finite value in {event_id}")
            if float(row["event_weight_pb"]) < 0.0:
                fail(f"negative weight in {event_id}")
            expected_all = all(row[name] == "1" for name in (
                "pass_Qe2", "pass_pt", "pass_eta", "pass_energy"
            ))
            if (row["pass_all"] == "1") != expected_all:
                fail(f"inconsistent cut flags in {event_id}")
            counts[row["split"]] += 1

    with cutflow_path.open(newline="") as source:
        rows = list(csv.DictReader(source))
    if len(rows) != 105:
        fail(f"expected 105 cut-flow rows, found {len(rows)}")
    if any(float(row["weighted_cross_section_pb"]) < 0.0 for row in rows):
        fail("negative cut-flow cross section")

    total = sum(counts.values())
    print(f"Validated {total:,} events and {len(rows)} cut-flow rows.")
    print("Splits: " + ", ".join(f"{key}={counts[key]:,}" for key in ("train", "validation", "test")))


if __name__ == "__main__":
    main()
