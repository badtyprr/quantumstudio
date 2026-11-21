"""Verify the lesson's quantified binary dot comparison by enumerating binary strings."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
from learning_clipboard_checks import clipboard_checks

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument("worker",type=Path)
parser.add_argument("notebook",type=Path)
parser.add_argument("--windows",type=Path)
parser.add_argument("--report",type=Path)
args=parser.parse_args()
if not __debug__: raise RuntimeError("Assertions must be enabled")
if args.report and not args.windows: parser.error("--report requires --windows")
worker=args.worker.resolve()
env=dict(os.environ,QALCULATE_DEFINITIONS_DIR=str(worker.parent/"data"))
def evaluate(expr,success=True):
    proc=subprocess.run([worker,"--json"],input=("quantum:"+expr).encode(),env=env,capture_output=True,timeout=30)
    assert (proc.returncode==0)==success,(expr,proc.stderr)
    if success: return json.loads(proc.stdout)["copy_text"]

notebook=args.notebook.read_bytes()
digest=hashlib.sha256(notebook).hexdigest()
mapping=json.loads(Path(__file__).with_name("ibm020-inventory-map.json").read_bytes())
assert digest==mapping["current_sha256"]
cells=json.loads(notebook)["cells"]
source="".join(cells[13]["source"])
sentence=next(line for line in source.splitlines() if line.startswith("If $z = 0^n$, then "))
clause=sentence.split(", then ",1)[1].split(", so ",1)[0]
assert clause==r"$z\cdot x = 0$ for every string $x\in\Sigma^n$"
cases={}
def record(key,expr,expected):
    assert evaluate(expr)==expected
    cases[key]=(expr,expected)

total=0
comparisons=0
for bit in (0,1):
    expr=clause.replace("= 0$","= "+str(bit)+"$")
    form=evaluate(expr)
    assert form==f"qallbitdot('z','n',{bit})" and evaluate(form)==form
    record("target-"+str(bit),expr,form)
    for n in range(6):
        for z in range(1<<n):
            parities=[(z & x).bit_count()%2 for x in range(1<<n)]
            expected=str(int(all(p==bit for p in parities)))
            word=f"qbitlabel({z},{n})"
            if z%2:bound=f'replace(replace(({form}),"n",{n}),"z",{word})'
            else:bound=f'replace(replace(({form}),"z",{word}),"n",{n})'
            assert evaluate(bound)==expected,(bit,z,n)
            if (n,z) in ((0,0),(4,0),(4,3)):record(f"target-{bit}-width-{n}-word-{z}",bound,expected)
            total+=1
            comparisons+=len(parities)
record("big-zero","qallbitdot(qbitlabel(0,1024),1024,0)","1")
record("big-high-bit","qallbitdot(qbitlabel(2^1023,1024),1024,0)","0")
record("ordinary-dot",r"$3\cdot 5=0$","0")
for bad in ("qallbitdot(qbitlabel(0,3),4,0)","qallbitdot(16,4,0)","qallbitdot(0,-1,0)","qallbitdot(0,4,2)",
            clause.replace(r"x\in",r"y\in"),clause.replace(r"\cdot x",r"\cdotx")): evaluate(bad,False)
if args.windows:
    clipboard_checks(worker,args.windows,args.report,cases,11,dict(notebook_sha256=digest,source_clause=clause,
                     predicates=total,parities_enumerated=comparisons,invalid_controls=6))
