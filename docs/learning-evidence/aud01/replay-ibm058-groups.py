"""Check generated Pauli groups and strict order under concrete substitutions."""
import argparse
import json
import os
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument("worker",type=Path)
worker = parser.parse_args().worker.resolve()
env = dict(os.environ,QALCULATE_DEFINITIONS_DIR=str(worker.parent/"data"))
rows = json.loads(Path(__file__).with_name("ibm058-inventory.json").read_bytes())["rows"]


def evaluate(expression):
    result = subprocess.run([worker,"--json"],input=("quantum:"+expression).encode(),
                            capture_output=True,env=env,timeout=30,check=True)
    return json.loads(result.stdout)["copy_text"]


for n in (34,36,38):
    assert evaluate(rows[n-1]["literal"]) == "1"
group = evaluate(rows[32]["literal"])
for size,generators,expected in [(1,["X"],r"\{I,X\}"),(2,["X","Z"],r"\langle X,Z\rangle")]:
    value = evaluate(f'replace(({group}),r,{size})')
    for i,gate in enumerate(generators,1):
        value = evaluate(f'replace(({value}),"P_{i}",{gate})')
    assert evaluate(f"({value})==({expected})") == "1"
    assert evaluate(f"({value})==qset(vector(I))") == "0"
order = evaluate(rows[52]["literal"])
for seq,expected in [([4,2,1],"1"),([4,2,2],"0"),([1,2,3],"0")]:
    value = evaluate(f'replace(({order}),m,3)')
    for i,num in enumerate(seq,1):
        value = evaluate(f'replace(({value}),"λ_{i}",{num})')
    assert value == expected,(seq,value)
print("Verified phase and tensor Pauli groups, indexed generators and strict eigenvalue ordering.")
