"""Replay two expected failures and selected existing tests without editing product files."""
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

from run import Q, parse_cell

ap=argparse.ArgumentParser()
ap.add_argument('--source',type=Path,required=True)
ap.add_argument('--package',type=Path,required=True)
ap.add_argument('--output',type=Path,required=True)
a=ap.parse_args();a.output.mkdir(parents=True,exist_ok=True)
worker=a.package/'quantum-worker.exe'
os.environ['QALCULATE_DEFINITIONS_DIR']=str(a.package/'data')
source=a.source/'src/quantum-worker-test.py';text=source.read_text(encoding='utf-8')
tree=ast.parse(text);nodes=[];selected=[]
for n in tree.body:
    fragment=ast.get_source_segment(text,n) or ''
    if isinstance(n,(ast.Import,ast.ImportFrom,ast.FunctionDef)) and (not isinstance(n,ast.FunctionDef) or n.name in ('run','data')):
        nodes.append(n)
    elif isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in ('worker','checks') for t in n.targets):
        nodes.append(n)
    elif isinstance(n,ast.For) and ('2^Tr(I)' in fragment or '\\begin{aligned}1+1&=2' in fragment):
        nodes.append(n);selected.append(dict(line=n.lineno,end_line=n.end_lineno,sha256=hashlib.sha256(fragment.encode()).hexdigest()))
assert len(selected)==2
old=sys.argv;sys.argv=[str(source),str(worker)]
scope={};exec(compile(ast.Module(body=nodes,type_ignores=[]),str(source),'exec'),scope)
sys.argv=old
record=dict(source=str(source),source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),selected_nodes=selected,worker_checks=scope['checks'],status='pass')
(a.output/'existing-tests.json').write_text(json.dumps(record,indent=2))
rows=[]
for exponent in (0,1):
    for braced in (False,True):
        power='{'+str(exponent)+'}' if braced else str(exponent)
        expression=r'quantum:(-1)^'+power+r' \bigl( \vert 0\rangle - \vert 1\rangle \bigr)'
        r=subprocess.run([str(worker),'--json'],input=expression.encode(),capture_output=True,timeout=30)
        d=dict(input=expression,returncode=r.returncode,stdout=r.stdout.decode(),stderr=r.stderr.decode(),expected=[str((-1)**exponent),str(-(-1)**exponent)],source='M10',control=braced)
        value=json.loads(d['stdout']) if r.returncode==0 else {}
        d['matches_expected']=value.get('rows')==2 and value.get('columns')==1 and not value.get('approximate') and [parse_cell(x[0]) for x in value['cells']]==[Q((-1)**exponent),Q(-(-1)**exponent)]
        d['status']='pass' if d['matches_expected'] else 'incorrect_result'
        rows.append(d)
(a.output/'proposed-regressions.json').write_text(json.dumps(rows,indent=2))
print(json.dumps(dict(existing=record,regressions=[dict(control=r['control'],status=r['status']) for r in rows])))
# Known red reproductions are evidence, not failures of this audit runner.
assert all(r['matches_expected']==r['control'] for r in rows), 'Behavior changed; reassess the ledger'
