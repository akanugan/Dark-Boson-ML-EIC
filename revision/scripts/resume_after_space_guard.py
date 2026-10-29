#!/usr/bin/env python3
"""One safe coordinator restart after the old operational space guard stops it."""
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import time

BASE = Path(__file__).resolve().parents[1]
OUT = BASE / 'stratified_refit'


def record(action, **extra):
    value = dict(action=action, updated=time.time(), **extra)
    temporary = OUT / 'reserve_resume_status.json.tmp'
    temporary.write_text(json.dumps(value, indent=2) + '\n')
    temporary.replace(OUT / 'reserve_resume_status.json')
    print(json.dumps(value), flush=True)


def main():
    lock = (OUT / 'reserve_resume.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    record('waiting_for_existing_coordinator', next_reserve_GiB=10)
    while True:
        state = json.loads((OUT / 'study_status.json').read_text())
        if state['phase'] == 'numerical_results_complete':
            record('complete_without_restart')
            return
        if state['phase'] == 'needs_attention':
            prefix = 'Evaluation failures in '
            error = state.get('error', '')
            if not error.startswith(prefix):
                raise RuntimeError('Coordinator needs review for a non-evaluation error: ' + error)
            stage = error[len(prefix):]
            if stage not in ('final_evaluation', 'smearing_10pct', 'smearing_20pct'):
                raise RuntimeError('Unexpected stopped stage: ' + stage)
            status = json.loads((OUT / (stage + '_status.json')).read_text())
            failures = status.get('errors', [])
            if not failures or any(
                    not item.get('error', '').replace(' ', '').startswith('Lessthan15GiBfree;')
                    for item in failures):
                raise RuntimeError('Stopped evaluations include a non-storage failure; automatic restart refused')
            record('restarting_after_old_space_guard', stage=stage,
                   completed=status['completed'], next_reserve_GiB=10)
            environment = dict(os.environ, DARK_STUDY_MIN_FREE_GIB='10')
            result = subprocess.run([sys.executable, str(BASE / 'scripts/continue_stratified_study.py')],
                                    env=environment)
            if result.returncode:
                raise RuntimeError('Resumed coordinator needs review; exit ' + str(result.returncode))
            final = json.loads((OUT / 'study_status.json').read_text())
            if final['phase'] != 'numerical_results_complete':
                raise RuntimeError('Coordinator returned without numerical completion')
            record('numerical_results_complete')
            return
        time.sleep(20)


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        record('needs_attention', error=str(error))
        raise
