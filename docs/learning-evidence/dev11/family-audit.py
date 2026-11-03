"""Finite DEV-11f adaptations, not source notebooks or parameterized proofs."""
import argparse
from fractions import Fraction
import hashlib
import itertools
import importlib.util
import json
import math
import os
from pathlib import Path
import subprocess

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('diagram_audit',HERE/'diagram-audit.py')
diagram=importlib.util.module_from_spec(spec)
spec.loader.exec_module(diagram)


def shor_cases():
    cases=[]
    for positions in itertools.product(range(4),repeat=3):
        xs=[3*b+x-1 for b,x in enumerate(positions) if x]
        for z in [None]+list(range(9)):
            syndrome=0 if z is None else (2,3,1)[z//3]
            record=((syndrome>>1)&1)|((syndrome&1)<<1)
            for witness in ('0','1','i'):
                ops=diagram.prepare(witness)+diagram.SHOR+[('X',q) for q in xs]+([] if z is None else [('Z',z)])
                for block in range(3):
                    a=3*block
                    ops+=diagram.cx((a,9),(a+1,9),(a+1,10),(a+2,10))
                    ops += [('M',9,0,0.3),('M',10,1,0.7)]
                    ops += [('F',a+b,3,value,'X') for b,value in enumerate((1,3,2))]
                    # Reuse workspace only after measuring and resetting it.
                    ops += [('F',9,1,1,'X'),('F',10,2,2,'X')]
                ops+=diagram.SHOR_CHECK+[('M',9,0,0.3),('M',10,1,0.7)]
                ops += [('F',3*b,3,value,'Z') for b,value in enumerate((1,3,2))]
                phase=-1 if z in xs else 1
                expected=diagram.with_syndrome([phase*v for v in diagram.logical_state('shor',witness)],syndrome)
                cases.append(dict(id=f'shor-X{positions}-Z{z}-{witness}',qubits=11,operations=ops,
                                  expected=diagram.sparse(expected),expected_record=record,
                                  source_row='IBM-055',section='Simultaneous bit- and phase-flip errors',
                                  adaptation='Finite source-prose expansion: at most one X per block and one Z anywhere; reused measured/reset ancillas. Not a single original diagram.'))
    return cases


def scalar_cases():
    cases=[]
    for bits in itertools.product((0,1),repeat=3):
        a,b,c=bits
        cases.append(dict(id='majority-'+''.join(map(str,bits)),source_row='IBM-054',
                          section='Classical encoding and decoding',expression=f'{a}*{b}+{a}*{c}+{b}*{c}-2*{a}*{b}*{c}',expected=Fraction(sum(bits)>=2)))
    for p in (Fraction(1,100),Fraction(1,10),Fraction(1,2)):
        # Independent Bernoulli enumeration, not the same polynomial as the input.
        expected=sum(p**sum(bits)*(1-p)**(3-sum(bits)) for bits in itertools.product((0,1),repeat=3) if sum(bits)>=2)
        cases.append(dict(id='repetition-noise-'+str(p).replace('/','-'),source_row='IBM-054',
                          section='Noise reduction for the binary symmetric channel',expression=f'3*({p})^2-2*({p})^3',expected=expected))
    for c in (2,3):
        p=Fraction(1,100)
        expected=p
        for k in range(5):
            cases.append(dict(id=f'threshold-C{c}-k{k}',source_row='IBM-068',section='Threshold theorem',
                              expression=f'({c}*({p}))^({2**k-1})*({p})',expected=expected))
            expected=c*expected**2
    for p in (Fraction(1,100),Fraction(323,10000),Fraction(1,10)):
        expected=sum(Fraction(math.comb(9,k))*p**k*(1-p)**(9-k) for k in range(2,10))
        cases.append(dict(id='shor-noise-'+str(p).replace('/','-'),source_row='IBM-055',section='Error reduction for random errors',
                          expression=f'1-(1-({p}))^9-9*({p})*(1-({p}))^8',expected=expected,
                          limitation='Checks the displayed binomial expression only, not exact logical failure for all higher-weight patterns.'))
    return cases


def main():
    ap=argparse.ArgumentParser()
    for name in ('native','worker','sources','output','toolchain'):
        ap.add_argument('--'+name,type=Path,required=True)
    args=ap.parse_args()
    args.output.mkdir(parents=True,exist_ok=False)
    for row in json.loads((HERE/'source-manifest.json').read_text()):
        assert hashlib.sha256((args.sources/(row['id']+'.ipynb')).read_bytes()).hexdigest()==row['notebook']['sha256']
    assert hashlib.sha256(args.worker.read_bytes()).hexdigest()=='42126088fd76b9dfa5c7787f9bf66a6429c1baa0985ca9543b508322d4dc955d'
    env=dict(os.environ,PATH=str(args.toolchain)+os.pathsep+os.environ['PATH'],QALCULATE_DEFINITIONS_DIR=str(args.worker.parent/'data'))
    cases=shor_cases()
    source=next(r for r in json.loads((HERE/'source-manifest.json').read_text()) if r['id']=='IBM-055')
    notebook=json.loads((args.sources/'IBM-055.ipynb').read_text(encoding='utf-8'))
    for case in cases:
        case.update(source_url=source['url'],notebook_sha256=source['notebook']['sha256'],
                    cell_index=0,cell_id=notebook['cells'][0]['id'])
    results=diagram.execute(args.native,cases,env)
    scalar=[]
    for case in scalar_cases():
        run=subprocess.run([str(args.worker),'--json'],input=case['expression'],encoding='utf-8',capture_output=True,env=env,timeout=30)
        result=dict(case,expected=str(case['expected']),stdout=run.stdout,stderr=run.stderr,returncode=run.returncode)
        try:
            data=json.loads(run.stdout)
            actual=diagram.parse_complex(data['text'])
            result['pass']=run.returncode==0 and abs(actual-float(case['expected']))<max(1e-100,abs(float(case['expected']))*1e-12) and not data['approximate']
        except (ValueError,KeyError,SyntaxError):
            result['pass']=False
        scalar.append(result)
    report={'native_cases':len(cases),'scalar_cases':len(scalar),'results':results,'scalar_results':scalar,
            'provenance':{name:{'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()} for name,path in [('native',args.native),('worker',args.worker)]}}
    (args.output/'fixtures.json').write_text(json.dumps(cases),encoding='utf-8')
    (args.output/'results.json').write_text(json.dumps(report),encoding='utf-8')
    failed=[r['id'] for r in results+scalar if not r['pass']]
    print(json.dumps({'native':len(cases),'scalar':len(scalar),'failures':failed}))
    return bool(failed)


if __name__=='__main__':
    raise SystemExit(main())
