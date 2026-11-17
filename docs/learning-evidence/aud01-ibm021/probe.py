#!/usr/bin/env python3
"""Replay finite IBM021 observations; rejected originals are not math passes."""
import argparse,ast,hashlib,json,os,re,subprocess
from fractions import Fraction as F
from pathlib import Path

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
    for name in ('worker','definitions','source','output'):ap.add_argument('--'+name,type=Path,required=True)
    ap.add_argument('--worker-revision',help='Externally verified worker revision; binary hash is always recorded')
    args=ap.parse_args();root=Path(__file__).resolve().parent
    digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    plan=json.loads((root/'fixtures.json').read_bytes())
    if digest(args.source)!=plan['source_sha256']:raise SystemExit('Pinned source mismatch')
    notebook=json.loads(args.source.read_bytes());fixtures=plan['fixtures']
    if len(fixtures)!=44 or len({f['id'] for f in fixtures})!=44:raise SystemExit('Fixture count/identity mismatch')
    inventory=json.loads((root/'source-inventory.json').read_bytes())
    if inventory['source_sha256']!=plan['source_sha256']:raise SystemExit('Inventory source mismatch')
    originals=inventory['records']+[f['source'] for f in fixtures if f['cohort']=='original']+[plan['source_table_original']]
    for r in originals:
        c=notebook['cells'][r['cell_index']];body=''.join(c['source'])[r['offset']:r['end_offset']]
        if c['id']!=r['cell_id'] or body!=r['original'] or hashlib.sha256(body.encode()).hexdigest()!=r['sha256']:raise SystemExit('Original occurrence mismatch')
    for f in fixtures:
        if hashlib.sha256(f['input'].encode()).hexdigest()!=f['input_sha256']:raise SystemExit('Input hash mismatch')
    if not args.definitions.is_dir():raise SystemExit('Definitions directory missing')
    args.output.mkdir(parents=True,exist_ok=False)
    def data_hashes():return {str(p.relative_to(args.definitions)):digest(p) for p in args.definitions.rglob('*') if p.is_file()}
    meta=dict(source_sha256=digest(args.source),worker_sha256=digest(args.worker),worker_revision=args.worker_revision,inventory_sha256=digest(root/'source-inventory.json'),fixture_sha256=digest(root/'fixtures.json'),script_sha256=digest(Path(__file__)),definitions_before=data_hashes(),route='Actual worker exact mode, ordinary canonical copies')
    (args.output/'probe-snapshot.py').write_bytes(Path(__file__).read_bytes())
    env=dict(os.environ,QALCULATE_DEFINITIONS_DIR=str(args.definitions.resolve()));records=[]
    def run(expr):
        try:
            p=subprocess.run([str(args.worker.resolve()),'--json'],input=expr.encode(),capture_output=True,env=env,timeout=20)
            d=dict(input=expr,returncode=p.returncode,stdout=p.stdout.decode(),stderr=p.stderr.decode())
            if p.returncode==0:d['actual']=json.loads(d['stdout'])
            return d
        except subprocess.TimeoutExpired:return dict(input=expr,returncode=None,stderr='20-second worker timeout')
    def matrix(a):
        # Always use the complete canonical matrix, including 256-entry columns.
        match=re.fullmatch(r'matrix\((\d+),(\d+),\[([^\[\]]+)\]\)',a.get('copy_text',''))
        if not match:raise ValueError('Expected complete canonical real matrix')
        rows,cols=int(match[1]),int(match[2]);values=match[3].split(',')
        if (rows,cols)!=(a.get('rows'),a.get('columns')) or len(values)!=rows*cols:raise ValueError('Canonical matrix shape mismatch')
        values=[parse_cell(v.replace(chr(0x22c5),'*')) for v in values]
        return [values[i:i+cols] for i in range(0,len(values),cols)]
    def matches(a,e):
        if a.get('approximate') is not False:return False
        if 'scalar' in e:return a.get('rows')==a.get('columns')==0 and parse_cell(a['copy_text'])==Q(e['scalar'])
        if e.get('kind')=='typed_bit_set':
            if a.get('rows')!=0 or a.get('columns')!=0:return False
            text=a.get('copy_text','')
            if not re.fullmatch(r'qset\(vector\(qbitlabel\(\d+,\d+\)(?:,qbitlabel\(\d+,\d+\))*\)\)',text):return False
            labels=[(int(v),int(w)) for v,w in re.findall(r'qbitlabel\((\d+),(\d+)\)',text)]
            if any(w!=e['width'] or v>=1<<w for v,w in labels):return False
            bits=[format(v,'0'+str(w)+'b') for v,w in labels]
            return len(bits)==len(set(bits)) and set(bits)==set(e['bits'])
        actual=matrix(a)
        if e.get('kind')=='gf2_span':
            if len(actual)!=e['rows'] or not 1<=len(actual[0])<=3:return False
            cols=len(actual[0]);bits=[]
            for row in actual:
                if any(v not in (Q(0),Q(1)) for v in row):return False
                bits.append([int(v==Q(1)) for v in row])
            span=set()
            for mask in range(1<<cols):span.add(''.join(str(sum(row[j] for j in range(cols) if mask>>j&1)%2) for row in bits))
            return span==set(e['expected_span']) and len(span)==1<<cols
        return (a.get('rows'),a.get('columns'))==(e['rows'],e['columns']) and actual==[[Q(*v) for v in row] for row in e['cells']]
    def flush(summary=None):
        d=dict(provenance=meta,records=records)
        if summary is not None:d['summary']=summary
        (args.output/'results.json').write_text(json.dumps(d,indent=2),encoding='utf-8')
    flush()
    for f in fixtures:
        d=run(f['input']);d.update(id=f['id'],cohort=f['cohort'])
        try:
            if f['cohort']=='original':
                baseline=f['baseline']
                same=d['returncode']==baseline['returncode'] and d['stderr'].replace('\r\n','\n')==baseline['stderr']
                d['baseline_matches']=same;d['mathematical_pass']=False
                d['status']='literal_rejected' if same else 'unexpected_failure'
            else:
                d['mathematical_pass']=matches(d.get('actual',{}),f['expected'])
                if d['mathematical_pass']:
                    c=run(d['actual']['copy_text']);c['mathematical_pass']=matches(c.get('actual',{}),f['expected']);d['copy']=c;d['mathematical_pass']=c['mathematical_pass']
                d['status']='verified_value' if d['mathematical_pass'] else 'failed_value'
        except (ValueError,KeyError,SyntaxError,ZeroDivisionError) as error:d.update(status='harness_error',error=str(error))
        records.append(d);flush()
    meta['definitions_after']=data_hashes();meta['definitions_unchanged']=meta['definitions_before']==meta['definitions_after'];meta['worker_unchanged']=digest(args.worker)==meta['worker_sha256']
    meta['inputs_unchanged']=(digest(args.source)==meta['source_sha256'] and digest(root/'fixtures.json')==meta['fixture_sha256'] and digest(root/'source-inventory.json')==meta['inventory_sha256'] and digest(Path(__file__))==meta['script_sha256'])
    summary=dict(requests=len(records),value_passes_by_cohort={cohort:sum(d['cohort']==cohort and d.get('mathematical_pass',False) for d in records) for cohort in ('pilot_adaptation','joint_adaptation','authored_gf2_control')},
                 full_value_passes=sum(d.get('mathematical_pass',False) for d in records),ordinary_copy_passes=sum(d.get('copy',{}).get('mathematical_pass',False) for d in records),
                 literal_rejections=sum(d['status']=='literal_rejected' for d in records),
                 failures=[d['id'] for d in records if d['status'] in ('failed_value','unexpected_failure','harness_error')])
    flush(summary);print(json.dumps(summary))
    return int(bool(summary['failures']) or not meta['definitions_unchanged'] or not meta['worker_unchanged'] or not meta['inputs_unchanged'])

if __name__=='__main__':raise SystemExit(main())
