"""Check IBM-081's matrix and scalar limits and their physical time scale."""
import argparse
import json
import os
from pathlib import Path
import subprocess
from learning_clipboard_checks import clipboard_checks

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("worker",type=Path)
parser.add_argument("windows",type=Path)
reports = parser.add_mutually_exclusive_group()
reports.add_argument("--report",type=Path)
reports.add_argument("--session-report",type=Path)
args = parser.parse_args()
worker = args.worker.resolve()
env = dict(os.environ,QALCULATE_DEFINITIONS_DIR=str(worker.parent/"data"))
source = json.loads(Path(__file__).with_name("ibm081-inventory.json").read_bytes())
cases = {}

def evaluate(expr):
    result = subprocess.run([worker,"--json"],input=("quantum:"+expr).encode(),env=env,
                            check=True,capture_output=True,timeout=30)
    value=json.loads(result.stdout)
    assert not value["approximate"],expr
    return value["copy_text"]

def check(name,expr,expected):
    actual=evaluate(expr)
    assert actual==expected,(name,actual,expected)
    cases[name] = expr,expected

_,matrix,initial = source["rows"][218]["literal"].strip("$ \n.").split("=")
check("matrix-at-zero","$"+matrix+"$","matrix(2,2,[1 ∕ 2,1 ∕ 2,1 ∕ 2,1 ∕ 2])")
check("initial-density","$"+matrix+"="+initial+"$","1")
final = matrix.replace(r"\rightarrow 0",r"\rightarrow 1")
check("matrix-at-one","$"+final+"$","matrix(2,2,[1,0,0,0])")
check("different-endpoints","$"+final+"="+initial+"$","0")

literal=source["rows"][218]["literal"]
relation=evaluate(literal)
assert "qchannelendpoint" in relation and evaluate(relation)==relation
cases["M219"] = literal,relation
damping="vector([1,0;0,exp(-t/2)],[0,sqrt(1-exp(-t));0,0])"
plus="[1,1;1,1]/2"
def assign(expr,operators,state,state_first=False):
    bindings=[("Φ",operators),("ρ",state)]
    for name,value in (reversed(bindings) if state_first else bindings):
        expr=f'replace(({expr}),"{name}",({value}))'
    return expr
for state_first in (False,True):
    check(f"source-damping-{state_first}",assign(relation,damping,plus,state_first),"1")
    check(f"source-changed-state-{state_first}",assign(relation,damping,"[1,0;0,0]",state_first),"0")
    check(f"source-phase-flip-{state_first}",assign(relation,"vector(Z)",plus,state_first),"0")
late=evaluate(r"$\Phi(\rho,t\to\infty)$")
check("late-damping",assign(late,damping,plus),"matrix(2,2,[1,0,0,0])")
rotation="vector([cos(pi*t/2),-sin(pi*t/2);sin(pi*t/2),cos(pi*t/2)])"
one=evaluate(r"$\Phi(\rho,t\to1)$")
check("rotation-at-one",assign(one,rotation,"[1,0;0,0]"),"matrix(2,2,[0,0,0,1])")
channel=evaluate(r"$\Phi(\rho)$")
check("ordinary-channel",assign(channel,"vector(Z)",plus),"matrix(2,2,[1 ∕ 2,−1 ∕ 2,−1 ∕ 2,1 ∕ 2])")
unitary_source=source["rows"][179]["literal"]
unitary_relation=evaluate(unitary_source)
cases["M180"] = unitary_source,unitary_relation
for gate,expected in [("X","1"),("Z","0")]:
    bound=assign(unitary_relation,f"vector({gate})",plus)
    check("unitary-channel-"+gate,f'replace(({bound}),"U",X)',expected)

chain = source["rows"][225]["literal"]
for time in ("1","2","(1/4)"):
    check("time-scale-"+str(len(cases)),chain.replace("T_1",time),"1")
check("scalar-at-one","$"+chain.strip("$ \n").split("=")[0]+"$","0")
for name,expr,expected in [
    ("right",r"\lim_{x\to0^+}{\frac{|x|}{x}}","1"),
    ("left",r"\lim_{x\to0^{-}}{\frac{|x|}{x}}","−1"),
    ("removable",r"\lim_{x\to0}\frac{\sin{x}}{x}","1"),
    ("ungrouped",r"\lim_{x\to2}x^2+3","7"),
    ("nested",r"\lim_{p\to1}{\lim_{p\to0}{p}+p}","1"),
    ("outer-point",r"\lim_{x\to3}{\lim_{p\to x}{p+1}}","4"),
]:
    check(name,"$"+expr+"$",expected)
clipboard_checks(worker,args.windows,args.report or args.session_report,cases,27,
                 dict(source_sha256=source["source_sha256"],source_rows=[180,219,226]),
                 sessions_only=bool(args.session_report))
