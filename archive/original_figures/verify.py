#!/usr/bin/env python3
"""Rebuild Figures 2-8 and compare rendered pixels with the manuscript assets.
Requires ROOT/TMVA, a C++ compiler, Matplotlib, Pillow, and pdftoppm.
Large input events/models must be restored from the data release.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
from PIL import Image, ImageChops

HERE = Path(__file__).resolve().parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--project-root', type=Path, default=HERE.parent)
parser.add_argument('--report', type=Path)
args = parser.parse_args()
project = args.project_root.resolve()

def run(command):
    result = subprocess.run([str(x) for x in command], capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(' '.join(map(str, command)) + '\n' + result.stdout + result.stderr)

def raster(path, destination):
    if path.suffix == '.pdf':
        run(['pdftoppm', '-r', '160', '-singlefile', '-png', path, destination])
        path = destination.with_suffix('.png')
    with Image.open(path) as im:
        return im.convert('RGB')

names = ['02_cross_sections', '03_photon_shapes', '04_kinematics',
         '05_mass_scan', '06_roc', '07_importance', '08_independent_runs']
outputs = ['figure.png', 'photon_shape_overlay.png', 't_pt_density.png',
           'figure.pdf', 'roc_t_comparison.png', 'tmva_t_importance.png', 'figure.pdf']
report = {'comparison': 'Exact RGB pixels; PDFs rasterized at 160 dpi with pdftoppm',
          'figure_1': 'Rendered diagram only; no editable drawing source available',
          'figures': []}
with tempfile.TemporaryDirectory(prefix='dark-figure-verification-') as tmp:
    work = Path(tmp)
    flags = shlex.split(subprocess.check_output(['root-config', '--cflags', '--libs'], text=True))
    for n, name, output in zip(range(2,9), names, outputs):
        folder = work/name
        shutil.copytree(HERE/name, folder)
        if (folder/'plot.py').exists():
            run([sys.executable, folder/'plot.py'])
        else:
            binary = work/f'plot_{n}'
            run(['c++', '-std=c++17', folder/'plot.cpp', '-o', binary, *flags, '-lTMVA'])
            data = folder/'data/tmva_t_importance_10gev.csv' if n == 7 else project
            run([binary, data, folder])
        expected = HERE/name/('figure.pdf' if n in [5,8] else 'figure.png')
        a = raster(expected, work/f'reference_{n}')
        b = raster(folder/output, work/f'generated_{n}')
        same = a.size == b.size and ImageChops.difference(a,b).getbbox() is None
        report['figures'].append({'figure': n, 'identical_pixels': same,
                                  'reference_size': list(a.size), 'generated_size': list(b.size),
                                  'reference_rgb_sha256': hashlib.sha256(a.tobytes()).hexdigest(),
                                  'generated_rgb_sha256': hashlib.sha256(b.tobytes()).hexdigest()})
        print(f'Figure {n}: '+('PASS' if same else 'FAIL'), flush=True)
if args.report:
    args.report.write_text(json.dumps(report, indent=2)+'\n')
if not all(r['identical_pixels'] for r in report['figures']):
    raise SystemExit(1)
