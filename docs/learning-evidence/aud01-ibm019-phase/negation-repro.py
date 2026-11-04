"""Red-capable minimal source-derived bit-negation reproduction."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--package',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args()
    worker=args.package/'quantum-worker.exe'
    manifest=json.loads((args.package/'build-manifest.json').read_text())
    digest=hashlib.sha256(worker.read_bytes()).hexdigest()
    assert digest.lower()==next(e['sha256'].lower() for e in manifest['files'] if e['path']=='quantum-worker.exe')
    cases=[]
    for bit in (0,1):
        for spelling,expr in [('source-tex',rf'\vert \neg {bit}\rangle'),
                              ('natural',f'|¬{bit}>'),
                              ('x-control',f'X|{bit}>'),
                              ('xor-control',f'|{bit} ⊕ 1>')]:
            p=subprocess.run([str(worker),'--json'],input=('quantum:'+expr).encode(),capture_output=True,
                             env=dict(os.environ,QALCULATE_DEFINITIONS_DIR=str(args.package/'data')),timeout=10)
            actual=json.loads(p.stdout) if p.returncode==0 else None
            expected=[[str(int(i==1-bit))] for i in range(2)]
            cases.append(dict(spelling=spelling,bit=bit,input=expr,expected=expected,
                              adaptation='Extract P05 complement term and substitute b; X and XOR are independent controls.',
                              returncode=p.returncode,stdout=p.stdout.decode(),stderr=p.stderr.decode(),
                              passed=actual is not None and actual['rows']==2 and actual['columns']==1 and actual['approximate'] is False and actual['cells']==expected))
    report=dict(revision=manifest['revision'],worker_sha256=digest,cases=cases)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(dict(passed=sum(c['passed'] for c in cases),total=len(cases),failed=[c['input'] for c in cases if not c['passed']])))
    return int(not all(c['passed'] for c in cases))


if __name__=='__main__':
    raise SystemExit(main())
