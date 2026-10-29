#!/usr/bin/env python3
"""Create a safe versioned study view; never replace original study files."""
import hashlib
import json
from pathlib import Path
import shutil

ROOT=Path(__file__).resolve().parents[1]
OLD=ROOT.parent/'stratified_refit'
CHANGES=[(4,1.585,'train'),(7,1.585,'train'),(5,1.585,'test'),
         (5,2.512,'test'),(1,5.,'validation'),(4,6.31,'validation')]

def label(m):return f'm{m:.3f}'.replace('.','p')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def link(src,dst):
    if dst.is_symlink() or dst.exists():return
    dst.parent.mkdir(parents=True,exist_ok=True);dst.symlink_to(src.resolve())

def main():
    ROOT.mkdir(exist_ok=True)
    changed={(f'rep_{r:03d}',label(m)):s for r,m,s in CHANGES}
    for rep in sorted((OLD/'data').glob('rep_*')):
        for directory in sorted(rep.iterdir()):
            if not directory.is_dir():continue
            dest=ROOT/'data'/rep.name/directory.name
            split=changed.get((rep.name,directory.name))
            if split is None:link(directory,dest);continue
            dest.mkdir(parents=True,exist_ok=True)
            for p in directory.iterdir():
                if p.name==split+'.root' or p.name.startswith(split+'_outside.') or p.name.startswith(split+'_merge'):continue
                link(p,dest/p.name)
    inventory=[]
    for rep in sorted((OLD/'fits').glob('rep_*')):
        for point in sorted(rep.iterdir()):
            if not point.is_dir():continue
            tag=point.name.split('_',1)[1];split=changed.get((rep.name,tag))
            dest=ROOT/'fits'/rep.name/point.name
            dest.mkdir(parents=True,exist_ok=True)
            if split is None:
                for p in point.iterdir():link(p,dest/p.name)
            else:
                # Signal generation is unchanged; retain exactly the same files.
                data=dest/'data';data.mkdir(exist_ok=True)
                for p in (point/'data').iterdir():link(p,data/p.name)
                link(point/'sample_config.json',dest/'original_sample_config.json')
                if not (dest/'sample_config.json').exists():shutil.copy2(point/'sample_config.json',dest/'sample_config.json')
                if split!='train':
                    for feature in ('electron','electron_qa2'):
                        target=dest/feature
                        if not target.exists():
                            shutil.copytree(point/feature,target,symlinks=True)
                            # New test exports must be made for every affected point.
                            for p in list(target.glob('test_*')):
                                if p.is_file() or p.is_symlink():p.unlink()
                    if not (dest/'fit_complete.json').exists():shutil.copy2(point/'fit_complete.json',dest/'fit_complete.json')
                    if not (dest/'validation_support.csv').exists():shutil.copy2(point/'validation_support.csv',dest/'validation_support.csv')
            inventory.append(dict(rep=int(rep.name.split('_')[1]),signal_type=point.name.split('_')[0],
                                  mass_GeV=float(tag[1:].replace('p','.')),split=split,
                                  old_point=str(point),new_point=str(dest)))
    link(OLD/'smearing',ROOT/'smearing')
    shutil.copy2(OLD/'fit_protocol_gate.json',ROOT/'original_fit_protocol_gate.json')
    out=dict(original_root=str(OLD),repair_root=str(ROOT),points=inventory,
        affected=[x for x in inventory if x['split']],
        original_gate_sha256=sha(OLD/'fit_protocol_gate.json'),
        protocol_sha256=sha(ROOT/'protocol.md'))
    (ROOT/'inventory.json').write_text(json.dumps(out,indent=2)+'\n')
    assert len(inventory)==220 and len(out['affected'])==12
    print('Versioned view ready: 12 affected points; 208 read-only reused points.')

if __name__=='__main__':main()
