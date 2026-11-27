"""Check the four printed eigenstates, their phase signs and their sum."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent.parent/"aud01"))
from learning_clipboard_checks import clipboard_checks

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("notebook",type=Path)
parser.add_argument("worker",type=Path)
parser.add_argument("windows",type=Path)
reports = parser.add_mutually_exclusive_group()
reports.add_argument("--report",type=Path)
reports.add_argument("--session-report",type=Path)
args = parser.parse_args()
source = args.notebook.read_bytes()
digest = hashlib.sha256(source).hexdigest()
assert digest=="2e7d0842cbf9f1d426ed3fda184de58f5d3459956867f9d9dc6ab2d75f4bd6ae"
cell = "".join(json.loads(source)["cells"][8]["source"])
answer = cell.split("The four eigenstates were:",1)[1].split(r"\end{aligned}",1)[0]
rows = re.findall(r"^\|\\psi_(\d)\\rangle\s*&=\s*(.*?)\s*\\\\\s*$",answer,re.M)
assert [label for label,_ in rows]==list("0123")
worker = args.worker.resolve()
env = dict(os.environ,QALCULATE_DEFINITIONS_DIR=str(worker.parent/"data"))
cases = {}

def evaluate(expression):
    proc = subprocess.run([worker,"--json"],input=("quantum:"+expression).encode(),
                          capture_output=True,env=env,check=True,timeout=30)
    result = json.loads(proc.stdout)
    assert not result["approximate"],expression
    return result["copy_text"]

def check(name,expression,expected):
    actual = evaluate(expression)
    assert actual==expected,(name,actual,expected)
    cases[name] = expression,expected

states = []
for label,rhs in rows:
    # Decimal ket labels index the four-qubit register used in the lesson.
    expression = "$"+rhs.replace(r"\rangle",r"\rangle_{16}")+"$"
    state = evaluate(expression)
    assert evaluate(state)==state
    cases["source-state-"+label] = expression,state
    states.append(state)
    phase = ["1","-i","-1","i"][int(label)]
    check("forward-phase-"+label,f"modmul(2,15)*{state}==({phase})*{state}","1")
    check("inverse-phase-"+label,f"modmul(8,15)*{state}==conj({phase})*{state}","1")

for i,left in enumerate(states):
    for j,right in enumerate(states):
        check(f"gram-{i}-{j}",f"({left})~*({right})=={int(i==j)}","1")
total = "("+"+".join(states)+")/2"
check("initial-state",total+"==basis(1,16)","1")
check("missing-eigenstate","("+"+".join(states[:3])+")/2==basis(1,16)","0")
check("reversed-phase-label",f"modmul(2,15)*{states[1]}==i*{states[1]}","0")
for power in range(5):
    check(f"orbit-{power}",f"modmul(2,15)^{power}*basis(1,16)==basis({pow(2,power,15)},16)","1")

clipboard_checks(worker,args.windows,args.report or args.session_report,cases,36,
                 dict(source_sha256=digest,source_cell=8,register_qubits=4),
                 sessions_only=bool(args.session_report))
