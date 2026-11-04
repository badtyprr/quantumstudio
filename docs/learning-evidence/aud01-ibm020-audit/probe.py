#!/usr/bin/env python3
"""Finite IBM-020 audit; literal and context failures are not math passes."""
import argparse
import ast
from fractions import Fraction as F
import hashlib
import json
import os
from pathlib import Path
import subprocess

# Independent exact rational field, reused from the earlier IBM-019 audit.
class Q:
    """Exact a + b sqrt(2), independent of the calculator under audit."""
    def __init__(self, a=0, b=0):
        self.a, self.b = F(a), F(b)
    def __add__(self, y):
        return Q(self.a+y.a, self.b+y.b)
    def __neg__(self):
        return Q(-self.a, -self.b)
    def __sub__(self, y):
        return self+-y
    def __mul__(self, y):
        return Q(self.a*y.a+2*self.b*y.b, self.a*y.b+self.b*y.a)
    def __truediv__(self, y):
        d=y.a*y.a-2*y.b*y.b
        return self*Q(y.a/d,-y.b/d)
    def __eq__(self,y):
        return (self.a,self.b)==(y.a,y.b)
    def record(self):
        return [str(self.a),str(self.b)]


def parse_cell(s):
    s=s.replace('−','-').replace('∕','/').replace('√','sqrt').replace('^','**')
    def walk(n):
        if isinstance(n,ast.Constant) and isinstance(n.value,(int,float)):
            return Q(str(n.value))
        if isinstance(n,ast.UnaryOp) and isinstance(n.op,ast.USub):
            return -walk(n.operand)
        if isinstance(n,ast.BinOp):
            a,b=walk(n.left),walk(n.right)
            if isinstance(n.op,ast.Add): return a+b
            if isinstance(n.op,ast.Sub): return a-b
            if isinstance(n.op,ast.Mult): return a*b
            if isinstance(n.op,ast.Div): return a/b
        if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='sqrt' and len(n.args)==1 and isinstance(n.args[0],ast.Constant) and n.args[0].value==2:
            return Q(0,1)
        raise ValueError('Unexpected exact cell syntax: '+s)
    return walk(ast.parse(s,mode='eval').body)



def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--worker',type=Path,default=Path(os.environ.get('QUANTUM_WORKER','quantum-worker.exe' if os.name=='nt' else 'quantum-worker')))
    ap.add_argument('--definitions',type=Path)
    ap.add_argument('--worker-revision',help='Externally verified revision; actual binary hash is always recorded')
    ap.add_argument('--source',type=Path,required=True,help='Pinned original IBM-020 notebook')
    ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args();root=Path(__file__).resolve().parent
    args.worker=args.worker.resolve();definitions=(args.definitions or args.worker.parent/'data').resolve()
    if not definitions.is_dir():raise SystemExit('Definition directory not found')
    args.output.mkdir(parents=True,exist_ok=True)
    if (args.output/'results.json').exists():raise SystemExit('Use a fresh evidence directory')
    raw=args.source.read_bytes();source_sha=hashlib.sha256(raw).hexdigest()
    if source_sha!='513398ae77d7502e7e8c2f2d4bdc85d4a7b5474d25f88a00eb1a2e8a8777586f':raise SystemExit('Pinned source hash mismatch')
    notebook=json.loads(raw);cell=''.join(notebook['cells'][0]['source'])
    inventory=json.loads((root/'inventory.json').read_bytes())
    for occurrence in inventory['occurrences']:
        original=cell[occurrence['cell_offset']:occurrence['end_cell_offset']]
        if original!=occurrence['original'] or hashlib.sha256(original.encode()).hexdigest()!=occurrence['sha256']:raise SystemExit('Source occurrence mismatch: '+occurrence['id'])
    cohort=json.loads((root/'fixtures.json').read_bytes());fixtures=cohort['fixtures']
    if cohort['source_sha256']!=source_sha:raise SystemExit('Fixture source mismatch')
    if len(fixtures)!=186 or len({f['id'] for f in fixtures})!=186:raise SystemExit('Fixture count/identity mismatch')
    env=dict(os.environ,QALCULATE_DEFINITIONS_DIR=str(definitions));records=[];canonical={}
    def execute(expression):
        try:
            p=subprocess.run([str(args.worker),'--json'],input=expression.encode(),capture_output=True,env=env,timeout=20)
            d=dict(input=expression,returncode=p.returncode,stdout=p.stdout.decode(),stderr=p.stderr.decode())
            if p.returncode==0:d['actual']=json.loads(p.stdout)
            return d
        except subprocess.TimeoutExpired:
            return dict(input=expression,returncode=None,stderr='20-second worker timeout')
    def matches(a,expected):
        if a.get('approximate') is not False:return False
        wanted=[[Q(*x) for x in row] for row in expected]
        if len(expected)==1 and len(expected[0])==1:
            return a.get('rows')==0 and a.get('columns')==0 and parse_cell(a['copy_text'])==wanted[0][0]
        return (a.get('rows')==len(expected) and a.get('columns')==len(expected[0])
                and [[parse_cell(c.replace('⋅','*')) for c in row] for row in a.get('cells',[])]==wanted)
    for f in fixtures:
        if 'copy_parent' in f:
            parent=canonical.get(f['copy_parent'])
            if parent is None:
                records.append(dict(id=f['id'],cohort=f['cohort'],status='unexpected_failure',error='Deferred parent copy unavailable'));continue
            expression=f['input_template'].replace('{canonical}',parent)
        else:expression=f['input']
        d=execute(expression);d.update(id=f['id'],source=f['source'],cohort=f['cohort'])
        try:
            if f['cohort']=='original':
                baseline=f['literal_baseline']
                same=(d['returncode']==baseline['returncode'] and d['stderr']==baseline['stderr'])
                if same and d['returncode']==0:
                    same=all(d.get('actual',{}).get(k)==v for k,v in baseline['actual'].items())
                    if same:
                        c=execute(d['actual']['copy_text']);d['copy_observation']=c
                        same=(c['returncode']==0 and all(c.get('actual',{}).get(k)==v for k,v in baseline['copy_actual'].items()))
                d['literal_baseline_matches']=same
                d['status']=('literal_rejected' if d['returncode']==2 else 'literal_observed_unverified') if same else 'unexpected_failure'
            elif f['cohort']=='deferred':
                a=d.get('actual',{});copy=a.get('copy_text','')
                if d['returncode']==0 and 'qsumset' in copy:
                    c=execute(copy);d['copy']=c;reentered=c.get('actual',{}).get('copy_text','')
                    d['status']='deferred_context_retained' if c['returncode']==0 and 'qsumset' in reentered else 'unexpected_failure'
                    if d['status']=='deferred_context_retained':canonical[f['id']]=reentered
                else:d['status']='unexpected_failure'
            else:
                d['mathematical_pass']=matches(d.get('actual',{}),f['expected'])
                if d['mathematical_pass']:
                    c=execute(d['actual']['copy_text']);c['mathematical_pass']=matches(c.get('actual',{}),f['expected']);d['copy']=c
                    d['mathematical_pass']=c['mathematical_pass'];d['status']='verified_value' if c['mathematical_pass'] else 'unexpected_failure'
                elif d['returncode']==2 and f.get('known_context_diagnostic') and f['known_context_diagnostic'] in d.get('stderr',''):
                    # Retain this as a failed value attempt, never a mathematical pass.
                    d['status']='failed_value_missing_context'
                else:d['status']='unexpected_failure'
        except (ValueError,SyntaxError,KeyError,ZeroDivisionError) as error:d.update(status='unexpected_failure',error=str(error))
        records.append(d)
    statuses={s:sum(d['status']==s for d in records) for s in sorted({d['status'] for d in records})}
    summary=dict(cohort_counts=cohort['counts'],statuses=statuses,
                 primary_mathematical_passes=sum(d['cohort']=='primary' and d.get('mathematical_pass',False) for d in records),
                 primary_mathematical_failures=[d['id'] for d in records if d['cohort']=='primary' and d.get('mathematical_pass') is False],
                 context_mathematical_passes=sum(d['cohort']=='context' and d.get('mathematical_pass',False) for d in records),
                 verified_numeric_copies=sum(d.get('copy',{}).get('mathematical_pass',False) for d in records),
                 deferred_context_copies=sum(d['status']=='deferred_context_retained' for d in records),
                 literal_copy_observations=sum('copy_observation' in d for d in records),
                 unexpected_failures=[d['id'] for d in records if d['status']=='unexpected_failure'])
    result=dict(summary=summary,source_sha256=source_sha,worker_revision=args.worker_revision,
                worker_sha256=hashlib.sha256(args.worker.read_bytes()).hexdigest(),
                script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                fixture_sha256=hashlib.sha256((root/'fixtures.json').read_bytes()).hexdigest(),
                definitions_sha256={str(p.relative_to(definitions)):hashlib.sha256(p.read_bytes()).hexdigest() for p in definitions.rglob('*') if p.is_file()},
                route='Actual worker exact mode; canonical copies use ordinary evaluation',records=records)
    (args.output/'results.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(summary))
    # Zero means the finite audit reproduced its documented observations, not whole-source success.
    return int(bool(summary['unexpected_failures']))


if __name__=='__main__':
    raise SystemExit(main())
