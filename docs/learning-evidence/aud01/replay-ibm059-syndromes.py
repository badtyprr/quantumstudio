"""Check the repetition-code stabilizer signs and the two Pauli observables."""
import argparse
import json
import os
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument("worker", type=Path)
worker = parser.parse_args().worker.resolve()
env = dict(os.environ, QALCULATE_DEFINITIONS_DIR=str(worker.parent/"data"))
rows = json.loads(Path(__file__).with_name("ibm059-inventory.json").read_bytes())["rows"]


def evaluate(expr):
    p = subprocess.run([worker,"--json"],input=("quantum:"+expr).encode(),capture_output=True,check=True,env=env,timeout=30)
    result = json.loads(p.stdout)
    assert not result["approximate"]
    return result


assert evaluate(rows[19]["literal"])["copy_text"] == "1"
table = evaluate(rows[52]["literal"])
assert (table["rows"],table["columns"]) == (3,5)
for row,generator in enumerate(("Z@Z@I","I@Z@Z"),1):
    for column,error in enumerate(("I@I@I","X@I@I","I@X@I","I@I@X"),1):
        sign = table["cells"][row][column].replace("−","-")
        assert evaluate(f"({generator})*({error})=={sign}*({error})*({generator})")["copy_text"] == "1"
for state, expected in (("|000>","1"),("|111>","1"),("|010>","0")):
    relation = evaluate(rows[3]["literal"])["copy_text"]
    # The source gives both stabilizer equations as separate aligned rows.
    result = evaluate(f'replace(({relation}),qnamedket("ψ"),{state})')["copy_text"]
    result = evaluate(f'replace(({result}),qketstate("ψ"),{state})')["copy_text"]
    assert result == f"vector({expected},{expected})", result
print("Verified the repetition stabilizer group, eight syndrome signs and three codeword probes.")
