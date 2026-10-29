"""Additional independent runs selected by original pointwise interval width."""
import os
import concurrent.futures
import json
from pathlib import Path
from run_comparison import BASE, rows, digest, run_point

project = Path(os.environ.get('DARK_PROJECT_ROOT', str(Path(__file__).resolve().parents[2])))
output = BASE/'wide_interval_reruns'
output.mkdir(exist_ok=True)
selected = [r for r in rows(BASE/'results/summary.csv')
            if 100*(float(r['ci95_high'])-float(r['ci95_low'])) > 10]
points = {(r['signal_type'], float(r['mass_GeV'])) for r in selected}
rates = rows(BASE/'config/rates.csv')
# Preserve original point indices; repetitions 11--20 use new seed blocks.
tasks = [(rep,i,r) for rep in range(11,21) for i,r in enumerate(rates)
         if (r['signal_type'],float(r['mass_GeV'])) in points]
original = json.loads((BASE/'results/method_manifest.json').read_text())
for path, expected in original.items():
    if digest(path) != expected:
        raise RuntimeError('Original method changed: '+path)
plan = dict(selection='Original pointwise 95% interval full width > 10 percentage points',
            selected_rows=selected, repetitions=list(range(11,21)), workers=2,
            expected_points=len(tasks), original_results_preserved=True,
            interpretation='Targeted follow-up; do not replace original runs or treat as a new full scan',
            method_manifest=original, driver_sha256=digest(__file__))
plan_path=output/'plan.json'
if plan_path.exists() and json.loads(plan_path.read_text()) != plan:
    raise RuntimeError('Rerun plan changed')
plan_path.write_text(json.dumps(plan,indent=2))

def status(state, error=None):
    done=len(list(output.glob('rep_*/*/complete.json')))
    (output/'status.json').write_text(json.dumps(dict(state=state,completed_points=done,
        expected_points=len(tasks),error=error),indent=2))
status('running')
try:
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        futures=[pool.submit(run_point,project,output,*task) for task in tasks]
        for future in concurrent.futures.as_completed(futures):
            future.result()
            status('running')
    status('complete')
except BaseException as exc:
    status('failed',str(exc))
    raise
