"""Verify Bell labels, Hadamard columns and the source's little-endian CNOT."""
import json
import os
from pathlib import Path
import subprocess
import sys

worker=Path(sys.argv[1]).resolve()
env=dict(os.environ,QALCULATE_DEFINITIONS_DIR=str(worker.parent/"data"))
def run(expr):
    p=subprocess.run([worker,"--json"],input=("quantum:"+expr).encode(),env=env,capture_output=True,check=True)
    return json.loads(p.stdout)["copy_text"]
def inventory(n):
    return json.loads(Path(__file__).with_name(f"ibm{n}-inventory.json").read_bytes())["rows"]
for row,target in [(3,"(|00>+|11>)/sqrt(2)"),(16,"(|01>-|10>)/sqrt(2)")]:
    state=run(inventory("069")[row-1]["literal"])
    assert run(f"qcompare({state},{target},4)")=="1"
rows=inventory("070")
assert all(run(rows[i-1]["literal"])=="1" for i in [5,25,26,27])
definition=run(rows[87]["literal"])
# In this lesson IBM numbers the least significant wire as control.
gate="qmul(SWAP,qmul(CNOT,SWAP))"
assert run(definition.replace('qoperatorref("CNOT")',gate))=="1"
assert run(definition.replace('qoperatorref("CNOT")',"CNOT"))=="0"
print("Verified Bell amplitudes, both Hadamard columns and CNOT wire order.")
