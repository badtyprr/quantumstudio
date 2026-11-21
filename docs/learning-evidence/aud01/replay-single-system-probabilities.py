"""Check the source probability equations against their classical and quantum distributions."""
import argparse
import json
import os
from pathlib import Path
import subprocess
from learning_clipboard_checks import clipboard_checks

parser = argparse.ArgumentParser()
parser.add_argument("worker",type=Path)
parser.add_argument("--windows",type=Path)
parser.add_argument("--report",type=Path)
args = parser.parse_args()
if not __debug__: raise RuntimeError("Assertions must be enabled.")
if args.report and not args.windows: parser.error("--report requires --windows")
worker = args.worker.resolve()
env = dict(os.environ,QALCULATE_DEFINITIONS_DIR=str(worker.parent/"data"))

def evaluate(source):
    run = subprocess.run([worker,"--json"],input=("quantum:"+source).encode(),
                         capture_output=True,check=True,timeout=30,env=env)
    value = json.loads(run.stdout)
    assert not value["approximate"], source
    return value["copy_text"]

def rows(lesson):
    return json.loads(Path(__file__).with_name(f"ibm{lesson}-inventory.json").read_bytes())["rows"]

classical = rows("037")
cases = {}
for number in (11,21,34):
    row=classical[number-1]
    cases[row["id"]]=(row["literal"],evaluate(row["literal"]))
domain=classical[20]["literal"].strip("$").split("=")[1]
for name in ("high","medium","low","off","other"):
    expr=rf"$\mathrm{{{name}}}\in {domain}$"
    truth=str(int(name!="other"))
    assert evaluate(expr)==truth
    cases["outcome-"+name]=(expr,truth)
equation = evaluate(classical[33]["literal"])
for distribution, truth in [("[3/4;1/4]","1"),("[1/4;3/4]","0")]:
    bound=f'replace(({equation}),"X",{distribution})'
    assert evaluate(bound)==truth
    cases["classical-distribution-"+truth]=(bound,truth)

quantum = rows("038")
psi = "[(1+2*i)/3;-2/3]"
for number, state in [(69,"|+>"),(70,"|+>"),(72,"|->"),(73,"|->"),(79,psi),(80,psi)]:
    row = quantum[number-1]
    assert row["id"].endswith(f"M{number:03}")
    equation = evaluate(row["literal"])
    cases[row["id"]]=(row["literal"],equation)
    for distribution, truth in [(f"probs({state})","1"), ("[1;0]","0")]:
        bound = f'replace(({equation}),"measurement probabilities",{distribution})'
        if state == psi:
            bound = f'replace({bound},qnamedket("ψ"),{psi})'
        assert evaluate(bound) == truth, row["id"]
        cases[f"M{number:03}-distribution-{truth}"]=(bound,truth)

for vector, index in [("[0;1]",2),("[1/2;1/4]",0),("[-1;2]",1),("[i;1]",0)]:
    run = subprocess.run([worker,"--json"],input=f"quantum:qeventprob({vector},{index})".encode(),
                         capture_output=True,timeout=30,env=env)
    assert run.returncode==2 and run.stderr.strip(), (vector,index)
print("Verified seven source equations, seven changed distributions and four invalid inputs")
if args.windows:
    clipboard_checks(worker,args.windows,args.report,cases,28,dict(classical_spans=[11,21,34],
                     quantum_spans=[69,70,72,73,79,80],outcome_membership_checks=5,
                     probability_equations=7,changed_distributions=7,invalid_inputs=4))
