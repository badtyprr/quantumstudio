"""Replay scalar factor identities and the Shor splitting probability bounds."""
import argparse
from collections import Counter
from fractions import Fraction
from functools import lru_cache
from hashlib import sha256
import json
from math import gcd
import os
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument("package", type=Path)
parser.add_argument("directory", type=Path)
parser.add_argument("--report", type=Path)
args = parser.parse_args()
worker = args.package.resolve() / "quantum-worker.exe"
env = dict(os.environ, QALCULATE_DEFINITIONS_DIR=str(worker.parent/"data"))
inventory = json.loads(Path(__file__).with_name("ibm029-inventory.json").read_bytes())
assert sha256(worker.read_bytes()).hexdigest() == inventory["worker_sha256"]
rows = inventory["rows"]
inputs = [[f"M{i}",rows[i-1]["literal"],"0"] for i in (362,363,369,374,408,409,418,425,426,429,431,433,434)]
adapted = {
    "M362-integers": 'b>=2 and "c">=2',
    "M363-integers": 'N=b*"c"',
    "M369-integer": '"c"',
    "M374-integers": '"s">=2 and "j">=2',
    "M425-scalar": '"Z"^2-1=("Z"+1)*("Z"-1)',
    "M425-left": '"Z"^2-1', "M425-right": '("Z"+1)*("Z"-1)',
}
inputs.extend([key,expr,"0"] for key,expr in adapted.items())
directory = args.directory
if not args.report:
    directory.mkdir(parents=True,exist_ok=True)
    (directory/"inputs.json").write_bytes(json.dumps(inputs).encode())
    raise SystemExit()


@lru_cache(maxsize=2048)
def copied(expr):
    proc=subprocess.run([worker,"--json"],env=env,input=("quantum:"+expr).encode(),
                        capture_output=True,timeout=90)
    assert not proc.returncode, (expr[:130],proc.stderr)
    result=json.loads(proc.stdout)
    assert not result["approximate"],expr[:130]
    return result["copy_text"]


suite=json.loads((directory/"result.json").read_bytes())
records_path=directory/"records.json"
records=json.loads(records_path.read_bytes())
assert suite["passed"] and suite["clipboardRestored"] and suite["calls"]==len(records)==len(inputs)
assert json.loads((directory/"inputs.json").read_bytes())==inputs
forms,diagnostics,checks={},{},Counter()
for (key,expr,_),record in zip(inputs,records):
    assert record["id"]==key
    if key in ("M362","M374","M425"):
        assert record["label"]=="CHECK YOUR EXPRESSION"
        diagnostics[key]=record["display"]
        continue
    assert record["label"]==record["reentry_label"]=="EXACT RESULT" and record["restored_same"]
    saved=json.loads((directory/(key+".qsession")).read_bytes().decode("utf-8-sig"))
    assert saved["Expression"]==expr and saved["Mode"]==0 and not saved["Matrices"]
    forms[key]={record["copy"],record["second_copy"]}


def check(key,bindings,expected):
    for form in forms[key]:
        for name,value in bindings.items():
            form=f'replace(({form}),"{name}",({value}))'
        assert copied(f"({form})=({expected})")=="1", (key,bindings,expected)
    checks[key]+=1


unit_outputs = {}
for record in records:
    key = record["id"]
    if key not in ("M363","M369"):
        continue
    first,second = record["copy"],record["second_copy"]
    assert "km" in first and "ms" in first and "'k'" in second and "'s'" in second
    unit_outputs[key] = dict(first=first,second=second)
for b in (-1,1,2,5):
    for c in (1,2,3,7):
        check("M362-integers",dict(b=b,c=c),int(min(b,c)>=2))
        check("M374-integers",dict(s=b,j=c),int(min(b,c)>=2))
        check("M369-integer",dict(c=c),c)
        for n in (b*c,b*c+1):
            check("M363-integers",dict(N=n,b=b,c=c),int(n==b*c))
for z in (-2**53-1,-7,-1,0,1,7,2**53+1):
    for key in ("M425-left","M425-right"):
        check(key,dict(Z=z),z*z-1)
check("M425-scalar",{},1)
check("M426",{},1)
check("M408",{},Fraction(1,2))
for a,r in ((2,4),(2,6),(3,6),(4,2),(5,12),(17,32)):
    for i,expected in ((429,a**r-1),(431,a**r-1),(433,a**(r//2)-1),(434,a**(r//2)+1)):
        check(f"M{i}",dict(a=a,r=r),expected)


def primes(n):
    return [p for p in range(2,n+1) if n%p==0 and all(p%k for k in range(2,int(p**0.5)+1))]


def order(a,n):
    x=a%n
    r=1
    while x!=1:
        x=x*a%n
        r+=1
        assert r<n
    return r


def check_candidates(n):
    terms,expected=[],[]
    routes=Counter()
    for a in range(2,n):
        d=gcd(a,n)
        if d>1:
            label="initial_gcd"
            term=f"integergcd({a},{n})"
        else:
            r=order(a,n)
            if r%2:
                label="odd_order"
                d=1
                term=f"mod({r},2)"
            else:
                x=pow(a,r//2,n)
                d=gcd(x-1,n)
                term=f"integergcd(({a}^{r//2} pmod ({n}))-1,{n})"
                assert (x-1)*(x+1)%n==0 and d<n
                label="trivial_gcd" if d==1 else "even_order_split"
        if d>1:
            assert n%d==0 and d<n
        routes[label]+=1
        terms.append(term)
        expected.append(str(d))
    for start in range(0,len(terms),24):
        group=terms[start:start+24]
        expr="vector("+",".join(group)+")"
        result=copied(expr)
        assert result=="vector("+",".join(expected[start:start+24])+")" or (
            len(group)==1 and result==expected[start]), (n,start,result)
    return routes


reports=[]
for n in [*range(15,150,2),315,1155]:
    factors=primes(n)
    if len(factors)<2:
        continue
    routes=check_candidates(n)
    failure=Fraction(routes["odd_order"]+routes["trivial_gcd"],n-2)
    bound=Fraction(1,2**(len(factors)-1))
    assert failure<=bound
    check("M409",dict(m=len(factors)),bound)
    for t in (1,2,3,8):
        lower=1-Fraction(1,2**t)
        assert 1-failure**t>=lower
        check("M418",dict(t=t),lower)
    reports.append(dict(N=n,prime_divisors=factors,choices=n-2,routes=dict(routes),
                        failure=str(failure),upper_bound=str(bound)))

report=dict(source=inventory["source"],notebook_sha256=inventory["source_sha256"],worker_sha256=inventory["worker_sha256"],
            windows_records_sha256=sha256(records_path.read_bytes()).hexdigest(),inputs=inputs,diagnostics=diagnostics,
            original_unit_outputs=unit_outputs,checks=checks,moduli=reports)
args.report.write_bytes((json.dumps(report,indent=2,ensure_ascii=False)+"\n").encode())
print(len(reports),"moduli,",sum(r["choices"] for r in reports),"choices,",sum(checks.values()),"formula checks")
