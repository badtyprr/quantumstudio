#!/usr/bin/env python3
"""Source-backed single-bit complement acceptance, including copied guards."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--worker',type=Path,default=Path(os.environ.get('QUANTUM_WORKER','quantum-worker.exe' if os.name=='nt' else 'quantum-worker')))
    ap.add_argument('--definitions',type=Path)
    ap.add_argument('--translator',type=Path)
    ap.add_argument('--output',type=Path)
    args=ap.parse_args()
    args.worker=args.worker.resolve()
    records=[]
    env=dict(os.environ)
    if args.definitions:env['QALCULATE_DEFINITIONS_DIR']=str(args.definitions)
    elif (args.worker.parent/'data').is_dir():env['QALCULATE_DEFINITIONS_DIR']=str(args.worker.parent/'data')
    def execute(expression):
        d=dict(input=expression)
        if args.translator:
            p=subprocess.run([str(args.translator)],input=expression.encode(),capture_output=True,timeout=10)
            d['translation_exit']=p.returncode
            if p.returncode:
                d.update(returncode=p.returncode,stderr=p.stderr.decode());return d
            # Keep quantum evaluation options (symbol names and row matrices).
            # The retained parser sees only canonical functions, never the new
            # complement spelling. Record this two-parser development route.
            expression='quantum:'+p.stdout.decode().strip()
        else:
            expression='quantum:'+expression
        d['evaluator_input']=expression
        p=subprocess.run([str(args.worker),'--json'],input=expression.encode(),capture_output=True,timeout=10,env=env)
        d.update(returncode=p.returncode,stdout=p.stdout.decode(),stderr=p.stderr.decode())
        if p.returncode==0:d['actual']=json.loads(d['stdout'])
        return d
    def matches(a,cells):
        if a.get('approximate') is not False:return False
        # Existing one-row bras serialize as ordinary vectors in this worker.
        # Require the full canonical vector, not just a truthy evaluation.
        if len(cells)==1 and len(cells[0])>1:
            return a.get('rows')==0 and a.get('columns')==0 and a.get('copy_text')=='vector('+','.join(cells[0])+')'
        return a.get('cells')==cells and a.get('rows')==len(cells) and a.get('columns')==len(cells[0])
    def value(name,expression,cells):
        d=execute(expression);a=d.get('actual',{})
        d.update(id=name,expected=cells,passed=matches(a,cells))
        records.append(d)
        if d['passed']:
            copied=execute(a['copy_text']);v=copied.get('actual',{})
            copied.update(id=name+'-copy',expected=cells,passed=matches(v,cells))
            records.append(copied)
        return a.get('copy_text')
    def reject(name,expression):
        d=execute(expression)
        # A crash, timeout or unrelated setup error is not a valid rejection.
        d.update(id=name,passed=d['returncode']==2 and any(s in d.get('stderr','') for s in ('complemented','basis(index,dimension)','Quantum addition cannot broadcast','Unexpected notation')))
        records.append(d)
    for bit in (0,1):
        col=[[str(int(i==1-bit))] for i in range(2)]
        row=[[str(int(i==1-bit)) for i in range(2)]]
        for name,expr in [('natural',f'|¬{bit}>'),('tex',rf'\vert \neg {bit}\rangle'),('xor',f'|{bit} ⊕ 1>'),('x',f'X|{bit}>')]:
            value(f'{name}-{bit}',expr,col)
        value(f'bra-{bit}',f'<¬{bit}|',row)
        value(f'tex-bra-{bit}',rf'\langle \neg {bit}\vert',row)
        value(f'plain-bra-control-{bit}',f'<{1-bit}|',row)
    for symbol in ('b','x_0'):
        for bra,expr in [(False,f'|¬{symbol}>'),(True,f'<¬{symbol}|')]:
            d=execute(expr);copy=d.get('actual',{}).get('copy_text')
            d.update(id=f'deferred-{symbol}-{bra}',passed=d['returncode']==0 and 'qbasis' in (copy or ''))
            records.append(d)
            for kind,form in [('original',expr)]+([('copied',copy)] if copy else []):
                for bit in (0,1):
                    cells=[[str(int(i==1-bit))] for i in range(2)]
                    if bra:cells=[list(row[0] for row in cells)]
                    value(f'{symbol}-{bra}-{kind}-{bit}',f'replace({form},{symbol},{bit})',cells)
                for bad in ('-1','2','1/2','i'):
                    reject(f'invalid-{symbol}-{bra}-{kind}-{bad}',f'replace({form},{symbol},{bad})')
    for bad in ('2','01','-1','(b+1)','b ⊕ 1'):
        reject('syntax-'+bad,f'|¬{bad}>')
    reject('dimension','|¬b>_3')
    for opaque in ('notable','not0'):
        d=execute('|'+opaque+'>')
        d.update(id='opaque-'+opaque,passed=d.get('actual',{}).get('copy_text')=='qketstate("'+opaque+'")')
        records.append(d)
    summary=dict(worker_sha256=hashlib.sha256(args.worker.read_bytes()).hexdigest(),
                 translator_sha256=hashlib.sha256(args.translator.read_bytes()).hexdigest() if args.translator else None,
                 route='standalone parser plus retained evaluator' if args.translator else 'integrated worker',
                 checks=len(records),passed=sum(r['passed'] for r in records),
                 failures=[r['id'] for r in records if not r['passed']])
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(dict(summary=summary,records=records),indent=2),encoding='utf-8')
    print(json.dumps(summary))
    return int(bool(summary['failures']))


if __name__=='__main__':
    raise SystemExit(main())
