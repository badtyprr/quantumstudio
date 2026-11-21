"""Check the source probability equations against their classical and quantum distributions."""
import argparse
import json
import os
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument("worker",type=Path)
worker = parser.parse_args().worker.resolve()
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
equation = evaluate(classical[33]["literal"])
for distribution, truth in [("[3/4;1/4]","1"),("[1/4;3/4]","0")]:
    assert evaluate(f'replace(({equation}),"X",{distribution})') == truth

quantum = rows("038")
psi = "[(1+2*i)/3;-2/3]"
for number, state in [(69,"|+>"),(70,"|+>"),(72,"|->"),(73,"|->"),(79,psi),(80,psi)]:
    row = quantum[number-1]
    assert row["id"].endswith(f"M{number:03}")
    equation = evaluate(row["literal"])
    for distribution, truth in [(f"probs({state})","1"), ("[1;0]","0")]:
        bound = f'replace(({equation}),"measurement probabilities",{distribution})'
        if state == psi:
            bound = f'replace({bound},qnamedket("ψ"),{psi})'
        assert evaluate(bound) == truth, row["id"]

for vector, index in [("[0;1]",2),("[1/2;1/4]",0),("[-1;2]",1),("[i;1]",0)]:
    run = subprocess.run([worker,"--json"],input=f"quantum:qeventprob({vector},{index})".encode(),
                         capture_output=True,timeout=30,env=env)
    assert run.returncode==2 and run.stderr.strip(), (vector,index)
print("Verified seven source equations, seven changed distributions and four invalid inputs")
