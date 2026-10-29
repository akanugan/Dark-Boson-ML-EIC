#!/usr/bin/env python3
"""Draw the exact saved Figure 4 bins with ROOT; no event files required."""
import argparse
import csv
import math
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output-dir', type=Path, default=HERE / 'generated')
out = parser.parse_args().output_dir.resolve()
out.mkdir(parents=True, exist_ok=True)
with (HERE / 'data/bins.csv').open() as stream:
    bins = list(csv.DictReader(stream))
with (HERE / 'data/flows.csv').open() as stream:
    flows = list(csv.DictReader(stream))
if len(bins) != 6 * 36 * 36 or len(flows) != 6:
    raise ValueError('Expected six complete 36 by 36 panels')
for flow in flows:
    visible = sum(float(r['weighted_probability_percent']) for r in bins
                  if (r['class'], r['mass_GeV']) == (flow['class'], flow['mass_GeV']))
    expected = 100 * (1 - float(flow['outside_weight_fraction']))
    if not math.isclose(visible, expected, rel_tol=1e-10, abs_tol=1e-9):
        raise ValueError('Visible panel probabilities disagree with the overflow fraction')
root_config = shutil.which('root-config')
compiler = shutil.which('c++')
if not root_config or not compiler:
    raise SystemExit('ROOT root-config and a C++17 compiler must be on PATH.')
flags = shlex.split(subprocess.check_output([root_config, '--cflags', '--libs'], text=True))
with tempfile.TemporaryDirectory(prefix='dark-figure4-') as temporary:
    binary = Path(temporary) / 'draw'
    subprocess.run([compiler, '-std=c++17', str(HERE / 'draw.cpp'), '-o', str(binary), *flags], check=True)
    subprocess.run([str(binary), str(HERE / 'data/bins.csv'), str(out)], check=True)
