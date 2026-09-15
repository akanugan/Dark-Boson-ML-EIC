#!/usr/bin/env bash
set -euo pipefail

project_dir=$(cd "$(dirname "$0")/.." && pwd)
cutflow_out="$project_dir/results/signal_cutflow.csv"
events_out="$project_dir/data/signal_events.csv"

cutflow_files=("$project_dir"/results/cutflows/individual/*.csv)
event_files=("$project_dir"/data/csv/*.csv)

if (( ${#cutflow_files[@]} == 0 )) || [[ ! -e "${cutflow_files[0]}" ]]; then
  echo "No cut-flow files found." >&2
  exit 1
fi
if (( ${#event_files[@]} == 0 )) || [[ ! -e "${event_files[0]}" ]]; then
  echo "No event CSV files found." >&2
  exit 1
fi

sed -n '1p' "${cutflow_files[0]}" > "$cutflow_out"
for file in "${cutflow_files[@]}"; do sed -n '2,$p' "$file"; done >> "$cutflow_out"

sed -n '1p' "${event_files[0]}" > "$events_out"
for file in "${event_files[@]}"; do sed -n '2,$p' "$file"; done >> "$events_out"

echo "Created $cutflow_out"
echo "Created $events_out"
