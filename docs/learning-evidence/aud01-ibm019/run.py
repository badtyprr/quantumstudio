"""Bounded IBM-019 Analysis audit. Standard library only; never builds product code."""
import argparse
import ast
from fractions import Fraction as F
import hashlib
import json
import os
from pathlib import Path
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


def hadamard(v,bit):
    r=[Q() for _ in v]
    for i,x in enumerate(v):
        j=i^(1<<bit)
        r[i]=r[i]+x*Q(0,F(1,2))*(Q(-1) if i&(1<<bit) else Q(1))
        r[j]=r[j]+x*Q(0,F(1,2))
    return r


def oracle(v,f):
    r=[Q() for _ in v]
    for i,x in enumerate(v): r[i^(f[i&1]<<1)]=x
    return r


def make_fixtures():
    cases=[]
    def add(id,source,expr,expected,adaptation):
        cases.append(dict(id=id,source=source,input='quantum:'+expr,
                          expected=[x.record() for x in expected],adaptation=adaptation))
    initial=[Q(),Q(),Q(1),Q()]
    p1=hadamard(hadamard(initial,0),1)
    add('initial','M01',r'\vert 1\rangle \vert 0 \rangle',initial,'None; source TeX unchanged')
    for k,e in enumerate(['(H ⊗ H)|10>','|->|+>','1/2*(|0>-|1>)|0>+1/2*(|0>-|1>)|1>']):
        add('pi1-'+str(k),'M02',e,p1,'Extract expression from equation chain; circuit route makes H layers explicit')
    for a in (0,1):
        expected=[Q((-1)**a),Q(-(-1)**a)]
        for k,e in enumerate([rf'\vert 0 \oplus {a}\rangle - \vert 1 \oplus {a}\rangle',f'(-1)^{a}*(|0>-|1>)',('|0>-|1>' if a==0 else '|1>-|0>')]):
            add(f'xor-{a}-{k}','M08,M10',e,expected,'Exhaust both source bit cases; extract individual equality terms')
    add('minus','M14',r'\vert - \rangle',[Q(0,F(1,2)),Q(0,F(-1,2))],'None')
    for c,f in enumerate([(0,0),(0,1),(1,0),(1,1)],1):
        b0,b1=f; parity=b0^b1
        p2=oracle(p1,f);p3=hadamard(p2,0)
        # Complete permutation matrix, basis order |b a>, oracle flips b by f(a).
        matrix='['+';'.join(','.join(str(int(r==(col^(f[col&1]<<1)))) for col in range(4)) for r in range(4))+']'
        add(f'oracle-{c}','M03,M04,M07,M13,M15',matrix+'*(|->|+>)',p2,'Instantiate f by one of all four truth tables; explicit oracle matrix')
        add(f'pi2-xor-{c}','M07',f'1/2*(|0 ⊕ {b0}>-|1 ⊕ {b0}>)|0>+1/2*(|0 ⊕ {b1}>-|1 ⊕ {b1}>)|1>',p2,'Substitute f(0), f(1); extract RHS; retain evaluated XOR labels')
        for k,e in enumerate([f'1/2*(-1)^{b0}*(|0>-|1>)|0>+1/2*(-1)^{b1}*(|0>-|1>)|1>',f'|-> ⊗ (((-1)^{b0}*|0>+(-1)^{b1}*|1>)/sqrt(2))']):
            add(f'pi2-phase-{c}-{k}','M12',e,p2,'Substitute truth-table outputs; extract equality terms; make tensor product explicit')
        for k,e in enumerate([f'(-1)^{b0}*(|-> ⊗ ((|0>+(-1)^{parity}*|1>)/sqrt(2)))',f'(-1)^{b0}*|->|'+('+' if parity==0 else '-')+'>']):
            add(f'pi2-factor-{c}-{k}','M18',e,p2,'Substitute truth-table outputs; evaluate XOR; select source cases branch; explicit tensor product')
        add(f'pi3-{c}','M25',f'(-1)^{b0}*|->|{parity}>',p3,'Substitute truth-table outputs and select appropriate source branch')
        add(f'circuit-{c}','diagram,M25',f'(I ⊗ H)*{matrix}*(H ⊗ H)*|10>',p3,'Translate diagram to exact matrices; |b a> ordering; no Qiskit execution')
        add(f'measure-{c}','M26',f'expect(I ⊗ (|{parity}><{parity}|),(I ⊗ H)*{matrix}*(H ⊗ H)*|10>)',[Q(1)],'Born probability using grouped explicit projector on RIGHT tensor factor; no shot sampling')
        for label,e,expected in [('phase',f'(-1)^{b0}',(-1)**b0),('parity',f'{parity}',parity),('difference',f'{b1}-{b0}',b1-b0),('sign-equivalence',f'(-1)^({b1}-{b0})-(-1)^{parity}',0)]:
            add(f'{label}-{c}','M16,M19,M21,M22',e,[Q(expected)],'Exhaustive truth-table substitution; difference and XOR need only agree modulo two')
    add('minus-one','M20','-1',[Q(-1)],'None')
    add('one','M26','1',[Q(1)],'Scalar alone is not measurement evidence; see measure-1..4')
    return cases


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--evidence',type=Path,required=True);ap.add_argument('--package',type=Path,required=True);ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    pinned=json.loads((args.evidence/'source-manifest.json').read_text(encoding='utf-8'))
    for name,digest in pinned['files'].items():
        assert hashlib.sha256((args.evidence/name).read_bytes()).hexdigest()==digest, name
    inv=json.loads((args.evidence/'inventory.json').read_text(encoding='utf-8'))
    manifest=json.loads((args.package/'build-manifest.json').read_text())
    verified={}
    for entry in manifest['files']:
        f=args.package/entry['path']; h=hashlib.sha256(f.read_bytes()).hexdigest()
        assert h.lower()==entry['sha256'].lower(),f
        verified[entry['path']]=h
    worker=args.package/'quantum-worker.exe'
    env=dict(os.environ,QALCULATE_DEFINITIONS_DIR=str(args.package/'data'))
    def execute(expr):
        try:
            p=subprocess.run([str(worker),'--json'],input=expr.encode('utf-8'),capture_output=True,env=env,timeout=30)
            d=dict(input=expr,returncode=p.returncode,stdout=p.stdout.decode('utf-8'),stderr=p.stderr.decode('utf-8'),route='released quantum-worker.exe --json, exact mode',binary_revision=manifest['revision'])
            if p.returncode==0: d['actual']=json.loads(d['stdout'])
            return d
        except subprocess.TimeoutExpired:
            return dict(input=expr,status='environment_blocker',detail='30-second process timeout')
    # Originals precede adaptations. Contextual symbols are retained and tested,
    # but successful parsing alone will never be classified as semantic support.
    fixtures=make_fixtures()
    (args.output/'fixtures.json').write_text(json.dumps(fixtures,indent=2),encoding='utf-8')
    literal=[]
    for item in inv['formulas']:
        d=dict(item);d.update(execute('quantum:'+item['original']));literal.append(d)
    (args.output/'literal.json').write_text(json.dumps(literal,indent=2),encoding='utf-8')
    results=[]
    for fixture in fixtures:
        d=dict(fixture); d.update(execute(fixture['input']))
        try:
            v=d['actual']; cells=v['cells'] if v['rows'] else [[v['text']]]
            actual=[parse_cell(row[0]) for row in cells]
            expected=[Q(*x) for x in fixture['expected']]
            ok=v['approximate'] is False and v['columns'] in (0,1) and actual==expected
            d['status']='pass_adapted' if ok else 'incorrect_result'
        except (KeyError,ValueError,SyntaxError,ZeroDivisionError) as e:
            d['status']='unsupported' if d.get('returncode')==2 else 'environment_blocker'
            d['comparison_error']=str(e)
        results.append(d)
    (args.output/'checks.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
    provenance=dict(binary_revision=manifest['revision'],worker_sha256=verified['quantum-worker.exe'],verified_payload_files=len(verified),package=str(args.package),runner_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),inventory_sha256=hashlib.sha256((args.evidence/'inventory.json').read_bytes()).hexdigest(),oracle='Exact independent Q(sqrt(2)) butterfly H and bit-permutation oracle, all four Boolean functions; compare every coefficient including global phase',counts={s:sum(x['status']==s for x in results) for s in sorted({x['status'] for x in results})})
    (args.output/'provenance.json').write_text(json.dumps(provenance,indent=2),encoding='utf-8')
    print(json.dumps(provenance))
    for x in results:
        if x['status']!='pass_adapted': print(x['id'],x['status'],x.get('stderr'),x.get('comparison_error'))
    return 0 if all(x['status']=='pass_adapted' for x in results) else 1


if __name__=='__main__':
    raise SystemExit(main())
