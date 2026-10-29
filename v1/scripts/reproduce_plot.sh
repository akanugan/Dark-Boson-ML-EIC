#!/usr/bin/env bash
set -euo pipefail

project_dir=$(cd "$(dirname "$0")/.." && pwd)

if [[ -n "${DARK_PYTHON:-}" ]]; then
  python_executable="$DARK_PYTHON"
elif [[ -x "$project_dir/.venv/bin/python" ]]; then
  python_executable="$project_dir/.venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  python_executable=python3
else
  echo "Python 3 is required." >&2
  exit 1
fi

if ! "$python_executable" -c "import matplotlib" >/dev/null 2>&1; then
  echo "Matplotlib is missing. Run:" >&2
  echo "  python3 -m pip install -r $project_dir/requirements.txt" >&2
  exit 1
fi

"$python_executable" "$project_dir/scripts/plot_vector_scalar.py"

echo "Created:"
echo "  $project_dir/plots/vector_scalar_cross_section_validation.png"
echo "  $project_dir/plots/vector_scalar_cross_section_validation.pdf"
