#!/usr/bin/env python3
"""Rebuild current Figures 2–9 and compare pixels without changing checked-in assets."""
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
NAMES = ['01_diagrams','02_cross_sections','03_photon_shapes','04_kinematics',
         '05_selections','06_t_gain','07_methods','08_roc','09_importance']

def run(command, **kwargs):
    result = subprocess.run(list(map(str,command)),capture_output=True,text=True,**kwargs)
    if result.returncode:
        raise RuntimeError('Command failed: '+str(command[0])+'\n'+result.stdout+result.stderr)

def pixels(path, temporary):
    if path.suffix == '.pdf':
        run(['pdftoppm','-r','160','-singlefile','-png',path,temporary])
        path = temporary.with_suffix('.png')
    with Image.open(path) as im:return im.convert('RGB')

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project-root',type=Path,default=HERE.parent,
                        help='Project with historical Figure 3 inclusive ROOT sample and reference inputs')
    parser.add_argument('--skip-legacy',action='store_true',help='Skip Figure 3, which needs the original events')
    parser.add_argument('--report',type=Path,default=HERE/'verification.json')
    args=parser.parse_args()
    report={'comparison':'Exact RGB pixels; PDFs rasterized with Poppler at 160 dpi',
            'figure_1':{'status':'asset_only','reason':'Editable diagram source was not available',
                        'sha256':hashlib.sha256((HERE/NAMES[0]/'figure.png').read_bytes()).hexdigest()},
            'figures':[]}
    with tempfile.TemporaryDirectory(prefix='dark-figure-check-') as name:
        work=Path(name)
        for number,folder_name in enumerate(NAMES[1:],2):
            folder=HERE/folder_name;out=work/folder_name;out.mkdir()
            if number==3 and args.skip_legacy:
                report['figures'].append({'figure':number,'status':'skipped','reason':'Original inclusive events required'})
                continue
            if number==2:
                local=work/'figure2_source';shutil.copytree(folder,local)
                run([sys.executable,local/'plot.py'],cwd=work)
                generated=local
            elif number==3:
                config=os.environ.get('ROOT_CONFIG','root-config')
                flags=shlex.split(subprocess.check_output([config,'--cflags','--libs'],text=True))
                binary=out/'plot'
                run([os.environ.get('CXX','c++'),'-std=c++17',folder/'plot.cpp','-o',binary,*flags,'-lTMVA'])
                run([binary,args.project_root.resolve(),out],cwd=work)
                generated=out
            else:
                run([sys.executable,folder/'plot.py','--output-dir',out],cwd=work)
                generated=out
            checks=[]
            for suffix in ('.png','.pdf'):
                expected=folder/('figure'+suffix)
                if not expected.exists():continue
                actual=generated/(('photon_shape_overlay'+suffix) if number==3 else ('figure'+suffix))
                a=pixels(expected,work/f'expected_{number}');b=pixels(actual,work/f'actual_{number}')
                same=a.size==b.size and ImageChops.difference(a,b).getbbox() is None
                checks.append({'format':suffix[1:],'exact_rgb_pixels':same,'size':list(a.size),
                               'reference_rgb_sha256':hashlib.sha256(a.tobytes()).hexdigest(),
                               'generated_rgb_sha256':hashlib.sha256(b.tobytes()).hexdigest()})
            good=bool(checks) and all(c['exact_rgb_pixels'] for c in checks)
            report['figures'].append({'figure':number,'status':'pass' if good else 'fail','checks':checks})
            print(f'Figure {number}: '+('PASS' if good else 'FAIL'),flush=True)
    report['all_tested_figures_exact']=all(f['status'] in ('pass','skipped') for f in report['figures'])
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps(report,indent=2)+'\n')
    if not report['all_tested_figures_exact']:raise SystemExit(1)

if __name__=='__main__':main()
