"""Check the two printed modular eigenstates against independently constructed orbits."""
import argparse
import cmath
import json
import math
import os
from pathlib import Path
import subprocess

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument("worker",type=Path)
parser.add_argument("directory",type=Path)
parser.add_argument("--verify-clipboard",action="store_true")
args=parser.parse_args()
worker=args.worker.resolve()
env=dict(os.environ,QALCULATE_DEFINITIONS_DIR=str(worker.parent/"data"))
def evaluate(expr,approximate=False):
    command=[worker,"--json"]+(["--approx"] if approximate else [])
    p=subprocess.run(command,input=("quantum:"+expr).encode(),env=env,capture_output=True,timeout=30,check=True)
    return json.loads(p.stdout)

rows=json.loads(Path(__file__).with_name("ibm029-inventory.json").read_bytes())["rows"]
cases={}
forms=[]
for j,i in enumerate((92,107)):
    row=rows[i-1]
    form=evaluate("modpowers:"+row["literal"])["copy_text"]
    assert form==f"qorbitket('a','N','r',{j})" and evaluate(form)["copy_text"]==form
    cases[f"M{i:03}"]=(row["literal"],7,form)
    forms.append(form)
proof=rows[97]["literal"]
fixed=evaluate("modpowers:"+proof)["copy_text"]
assert evaluate(fixed)["copy_text"]==fixed
cases["M098"]=(proof,7,fixed)
for incorrect in (proof.replace(r"a^r",r"a^{r+1}"),proof.replace(r"\vert 1 \rangle",r"\vert 0 \rangle")):
    p=subprocess.run([worker,"--json"],input=("quantum:modpowers:"+incorrect).encode(),env=env,capture_output=True)
    assert p.returncode==2

states=amplitudes=exact_checks=0
for n,a in ((3,1),(3,2),(5,2),(7,2),(9,2),(11,2),(13,2),(15,2),(17,3),(21,2),(21,5),(61,2),(64,3)):
    orbit=[1]
    while (x:=orbit[-1]*a%n)!=1:
        assert x not in orbit
        orbit.append(x)
    r=len(orbit)
    claim=f'replace(replace(replace(({fixed}),"a",{a}),"N",{n}),"r",{r})'
    assert evaluate(claim)["copy_text"]=="1"
    for j in sorted({0,1,r-1}-{r}):
        form=forms[j] if j<2 else f'qorbitket("a","N","r",{j})'
        expr=f'replace(replace(replace(({form}),"a",{a}),"N",{n}),"r",{r})'
        result=evaluate(expr)
        assert not result["approximate"] and (result["rows"],result["columns"])==(n,1)
        copied=result["copy_text"]
        assert evaluate(copied)["copy_text"]==copied
        expected=[0j]*n
        for k,x in enumerate(orbit):
            expected[x]=cmath.exp(-2j*math.pi*j*k/r)/math.sqrt(r)
        measured=evaluate(copied,True)["cells"]
        assert len(measured)==n
        for (cell,),target in zip(measured,expected):
            value=complex(cell.replace("−","-").replace(" ","").replace("i","j"))
            assert abs(value-target)<1e-12,(n,a,j,cell,target)
        states+=1; amplitudes+=n
        if r in (1,2,4):
            root={1:"1",2:"(-1)",4:"i"}[r]
            relation=f"norm(qresiduemultiplier({a},{n})*({copied})-({root})^{j}*({copied}))"
            assert evaluate(relation)["copy_text"]=="0"
            assert evaluate(f"({copied})~*({copied})")["copy_text"]=="1"
            exact_checks+=2
        if (n,a,j) in ((3,1,0),(15,2,0),(15,2,1),(21,2,1),(61,2,1)):
            cases[f"{a}-mod-{n}-phase-{j}"]=(expr,0,copied)
(args.directory/"inputs.json").write_text(json.dumps([[k,e,str(m)] for k,(e,m,_) in cases.items()]),"utf8")
if args.verify_clipboard:
    records=json.loads((args.directory/"records.json").read_text("utf-8-sig"))
    assert [rec["id"] for rec in records]==list(cases)
    for rec in records:
        assert rec["restored_same"] and rec["copy"]==rec["second_copy"]==cases[rec["id"]][2]
    summary=json.loads((args.directory/"result.json").read_text("utf-8-sig"))
    assert summary["passed"] and summary["clipboardRestored"] and not summary["sessionsOnly"]
    print(json.dumps(dict(sources=[rows[i-1]["id"] for i in (92,98,107)],states=states,
                          amplitude_comparisons=amplitudes,absolute_tolerance=1e-12,
                          exact_norm_and_eigenvalue_checks=exact_checks,invariance_checks=13,clipboard_sessions=len(cases)),indent=2))
