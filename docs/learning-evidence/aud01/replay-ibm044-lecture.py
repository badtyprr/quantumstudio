"""Verify the circuit lecture's adapted examples in a packaged calculator."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

from learning_clipboard_checks import clipboard_checks

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("worker", type=Path)
parser.add_argument("windows", type=Path)
reports = parser.add_mutually_exclusive_group()
reports.add_argument("--report", type=Path)
reports.add_argument("--session-report", type=Path)
args = parser.parse_args()
worker = args.worker.resolve()
env = dict(os.environ, QALCULATE_DEFINITIONS_DIR=str(worker.parent/"data"))
prior = json.loads(Path(__file__).with_name("ibm044-caption-checks.json").read_bytes())
cases = {row["case"]:(row["expression"],row["expected"]) for row in prior["cases"]}
assert len(cases)==31

def add(page, label, expression, expected="1"):
    cases[f"p{page}-{label}"] = expression,expected

add(4,"both-columns","(T*H*S*H)==[(1+i)/2,(1-i)/2;1/sqrt(2),i/sqrt(2)]")
add(5,"both-wires","SWAP*CNOT*SWAP*(I@H)==[1,1,0,0;0,0,1,-1;0,0,1,1;1,-1,0,0]/sqrt(2)")
add(12,"coordinate-contraction","[i;2;1-i]~*[1;i;2]==2+3i")
add(14,"geometric-angle","cos(105*pi/180)==(1-sqrt(3))/(2*sqrt(2))")
add(16,"norm","norm([i;2;1-i])^2==7")
add(17,"conjugate-symmetry","[i;2;1-i]~*[1;i;2]==conj([1;i;2]~*[i;2;1-i])")
add(18,"second-slot","[i;1]~*(i*[1;0]+2*[0;1])==3")
add(19,"first-slot","(i*[1;0]+2*[0;1])~*[1;i]==i")
add(20,"dependent","abs([1;i]~*(2i*[1;i]))==norm([1;i])*norm(2i*[1;i])")
add(20,"independent","abs(<0|+>)<1")
bell = "[1,1,0,0;0,0,1,1;0,0,1,-1;1,-1,0,0]/sqrt(2)"
add(22,"bell-basis",f"({bell})~*({bell})==qidentity(4)")
add(24,"basis-completion","[1,0,0;0,1,i;0,i,1]~*[1,0,0;0,1,i;0,i,1]==[1,0,0;0,2,0;0,0,2]")
unitary="[1,0,0;0,1/sqrt(2),i/sqrt(2);0,i/sqrt(2),1/sqrt(2)]"
for label, product in [("columns",f"({unitary})~*({unitary})"),("rows",f"({unitary})*({unitary})~")]:
    add(26,label,product+"==qidentity(3)")
add(27,"given-column",f"({unitary})*[0;1;0]==[0;1;i]/sqrt(2)")
projector = "[1,0,0;0,1/2,-i/2;0,i/2,1/2]"
add(30,"hermitian",f"({projector})~==({projector})")
add(30,"idempotent",f"({projector})*({projector})==({projector})")
add(31,"zero","[0,0;0,0]*[0,0;0,0]==[0,0;0,0]")
add(32,"complete","(|+><+|)+(|-><-|)==I")
add(34,"outcome-phase","((|1><1|)*[1;i]/sqrt(2))/(1/sqrt(2))==i*|1>")
joint="[1;i;2;0]/sqrt(6)"
for bit,p,post in [(0,"1/3","[1;i;0;0]/sqrt(2)"),(1,"2/3","[0;0;1;0]")]:
    projection=f"((|{bit}><{bit}|)@I)*({joint})"
    add(36,f"probability-{bit}",f"norm({projection})^2=={p}")
    add(36,f"state-{bit}",f"({projection})/sqrt({p})=={post}")
add(37,"swap-symmetric","(I@I+SWAP)/2*|00>==|00>")
add(37,"swap-antisymmetric","(I@I-SWAP)/2*(|01>-|10>)==(|01>-|10>)")
add(39,"projected-phase","norm((|+><+|)*(i*|0>))^2==1/2")
add(40,"propagated-phase","H*(i*|->)==i*|1>")
add(49,"adjoint-first","H~*|+>==|0>")
add(49,"adjoint-second","H~*|->==|1>")
for label,state in [("plus","|+>"),("minus","|->")]:
    for bit,project in [(0,"(|+><+|)"),(1,"(I-|+><+|)")]:
        answer=int((bit==0)==(label=="plus"))
        add(50,f"{label}-{bit}",f"norm({project}*{state})^2=={answer}")

for name,(expr,expected) in cases.items():
    proc=subprocess.run([worker,"--json"],input=("quantum:"+expr).encode(),capture_output=True,env=env,timeout=30)
    assert proc.returncode==0,(name,proc.stderr.decode())
    value=json.loads(proc.stdout)
    assert value["copy_text"]==expected and not value["approximate"],(name,value["copy_text"],expected)
clipboard_checks(worker,args.windows,args.report or args.session_report,cases,65,
                 dict(slide_pages=50,original_notebook_formulas=0,
                      application_sha256=hashlib.sha256((worker.parent/"QuantumStudio.exe").read_bytes()).hexdigest()),
                 sessions_only=bool(args.session_report))
