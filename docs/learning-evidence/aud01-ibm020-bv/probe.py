#!/usr/bin/env python3
"""Replay finite BV observations; preserved rejections are not mathematical passes."""
import argparse
import ast
from fractions import Fraction as F
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

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
    ap.add_argument('--source',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True,help='Fresh directory for raw results and provenance')
    args=ap.parse_args();root=Path(__file__).resolve().parent
    digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    fixtures=json.loads((root/'fixtures.json').read_bytes())
    if digest(args.source)!=fixtures['source']['sha256']:raise SystemExit('Pinned source hash mismatch')
    notebook=json.loads(args.source.read_bytes())
    for r in fixtures['source_literals']:
        cell=notebook['cells'][r['cell_index']];text=''.join(cell['source'])[r['offset']:r['end_offset']]
        if cell['id']!=r['cell_id'] or text!=r['original'] or hashlib.sha256(text.encode()).hexdigest()!=r['sha256']:raise SystemExit('Original formula mismatch: '+r['id'])
    for r in fixtures['original_code_references']:
        cell=notebook['cells'][r['cell_index']];text=''.join(cell['source'])
        if cell['id']!=r['cell_id'] or text!=r['original'] or hashlib.sha256(text.encode()).hexdigest()!=r['sha256']:raise SystemExit('Original code reference mismatch')
    requests=[]
    for r in fixtures['source_literals']:requests.append((r['id'],'original',r,None))
    for r in fixtures['shared_requests']:requests.append((r['id'],'planned',r,fixtures['shared'][r['expected_ref'].split('.')[-1]]))
    cases={c['secret']:c for c in fixtures['cases']}
    for c in fixtures['cases']:
        for r in c['requests']:requests.append((c['id']+'/'+r['id'],'planned',r,c[r['expected_ref']]))
    for r in fixtures['compact_requests']:requests.append((r['id'],'compact',r,cases[r['secret']][r['expected_ref']]))
    if len(requests)!=159 or len({r[0] for r in requests})!=159:raise SystemExit('Fixture count or identity mismatch')
    for _,_,r,_ in requests:
        if 'input_sha256' in r and hashlib.sha256(r['input'].encode()).hexdigest()!=r['input_sha256']:raise SystemExit('Fixture input hash mismatch')
    args.worker=args.worker.resolve();definitions=(args.definitions or args.worker.parent/'data').resolve()
    if not definitions.is_dir():raise SystemExit('Definition directory not found; use --definitions')
    def data_hashes():return {str(p.relative_to(definitions)):digest(p) for p in definitions.rglob('*') if p.is_file()}
    args.output.mkdir(parents=True,exist_ok=False)
    provenance=dict(source_sha256=digest(args.source),worker_sha256=digest(args.worker),worker_revision=args.worker_revision,
                    script_sha256=digest(Path(__file__)),fixtures_sha256=digest(root/'fixtures.json'),definitions_before=data_hashes(),
                    route='Actual worker exact mode; canonical copies use ordinary evaluation')
    (args.output/'probe-snapshot.py').write_bytes(Path(__file__).read_bytes())
    env=dict(os.environ,QALCULATE_DEFINITIONS_DIR=str(definitions));records=[]
    def execute(expression):
        try:
            p=subprocess.run([str(args.worker),'--json'],input=expression.encode(),capture_output=True,env=env,timeout=20)
            d=dict(input=expression,returncode=p.returncode,stdout=p.stdout.decode(),stderr=p.stderr.decode())
            if p.returncode==0:d['actual']=json.loads(d['stdout'])
            return d
        except subprocess.TimeoutExpired:return dict(input=expression,returncode=None,stderr='20-second worker timeout')
    def matches(actual,expected):
        rows,cols=expected['rows'],expected['columns']
        if actual.get('approximate') is not False or (actual.get('rows'),actual.get('columns'))!=(rows,cols):return False
        wanted=[]
        for row in expected['cells']:
            converted=[]
            for v in row:
                if isinstance(v,dict):
                    if F(v['imaginary'])!=0:raise ValueError('Reference outside the real exact-field contract')
                    converted.append(Q(v['rational'],v['sqrt2']))
                else:converted.append(Q(v))
            wanted.append(converted)
        cells=actual.get('cells',[])
        # Worker intentionally omits cells above128entries. These larger outputs
        # are integer oracle matrices; inspect every canonical entry instead.
        if not cells and rows*cols>128:
            match=re.fullmatch(r'matrix\((\d+),(\d+),\[([01, -]+)\]\)',actual.get('copy_text',''))
            if not match or (int(match[1]),int(match[2]))!=(rows,cols):return False
            values=match[3].split(',')
            if len(values)!=rows*cols:return False
            cells=[values[i:i+cols] for i in range(0,len(values),cols)]
        return [[parse_cell(v.replace('\u22c5','*')) for v in row] for row in cells]==wanted
    def flush(summary=None):
        payload=dict(provenance=provenance,records=records)
        if summary is not None:payload['summary']=summary
        (args.output/'results.json').write_text(json.dumps(payload,indent=2),encoding='utf-8')
    flush()
    for id,cohort,r,expected in requests:
        d=execute(r.get('input',r.get('planned_input')));d.update(id=id,cohort=cohort)
        try:
            if 'baseline' in r:
                b=r['baseline'];same=d['returncode']==b['returncode'] and d['stderr'].replace('\r\n','\n')==b['stderr']
                d['baseline_matches']=same;d['mathematical_pass']=False
                d['status']=('literal_rejected' if cohort=='original' else 'expanded_guard_rejected') if same else 'unexpected_failure'
            else:
                d['mathematical_pass']=matches(d.get('actual',{}),expected)
                if d['mathematical_pass']:
                    c=execute(d['actual']['copy_text']);c['mathematical_pass']=matches(c.get('actual',{}),expected);d['copy']=c
                    d['mathematical_pass']=c['mathematical_pass']
                d['status']='verified_value' if d['mathematical_pass'] else 'unexpected_failure'
        except (ValueError,SyntaxError,KeyError,ZeroDivisionError) as error:d.update(status='unexpected_failure',error=str(error))
        records.append(d);flush()
    provenance['definitions_after']=data_hashes()
    provenance['definitions_unchanged']=provenance['definitions_before']==provenance['definitions_after']
    provenance['worker_unchanged']=digest(args.worker)==provenance['worker_sha256']
    summary=dict(requests=len(records),planned_value_passes=sum(d['cohort']=='planned' and d.get('mathematical_pass',False) for d in records),
                 compact_value_passes=sum(d['cohort']=='compact' and d.get('mathematical_pass',False) for d in records),
                 numeric_copies=sum(d.get('copy',{}).get('mathematical_pass',False) for d in records),
                 literal_rejections=sum(d['status']=='literal_rejected' for d in records),
                 expanded_guard_rejections=sum(d['status']=='expanded_guard_rejected' for d in records),
                 unexpected_failures=[d['id'] for d in records if d['status']=='unexpected_failure'])
    flush(summary);print(json.dumps(summary))
    # Success reproduces observations; rejected original/expanded inputs stay failed.
    return int(bool(summary['unexpected_failures']) or not provenance['definitions_unchanged'] or not provenance['worker_unchanged'])


if __name__=='__main__':
    raise SystemExit(main())
