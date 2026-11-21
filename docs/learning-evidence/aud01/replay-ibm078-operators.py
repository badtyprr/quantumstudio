"""Verify both printed Jordan-Wigner conventions one wire at a time."""
import json
from pathlib import Path
import os
import subprocess
import sys
worker=Path(sys.argv[1]).resolve()
env=dict(os.environ,QALCULATE_DEFINITIONS_DIR=str(worker.parent/"data"))
def run(expr):
    p=subprocess.run([worker,"--json"],input=("quantum:"+expr).encode(),env=env,capture_output=True,check=True)
    return json.loads(p.stdout)["copy_text"]
for width in (1,2,3):
    for site in range(width):
        for create,ladder in [(0,"matrix(2,2,[0,1,0,0])"),(1,"matrix(2,2,[0,0,1,0])")]:
            gates=["(-Z)"]*site+[ladder]+["I"]*(width-site-1)
            matrix=gates[0]
            for gate in gates[1:]:
                matrix=f"qtensor({matrix},{gate})"
            assert run(f"qcompare(qjwimage({width},{site},{create}),{matrix},4)")=="1",(width,site,create)
print("Verified 12 signed Jordan-Wigner matrices across one, two and three wires.")

def source(n,row):
    data=json.loads(Path(__file__).with_name(f"ibm{n:03}-inventory.json").read_bytes())
    return run(data["rows"][row-1]["literal"])
assert source(78,50)=="vector(1,1,1,1)"
for row,selector in [(20,0),(22,1)]:
    equation=source(79,row)
    assert f"qjwimage('N','j',{selector})" in equation
mapping=source(78,29).split(r"\\qcompare")
assert len(mapping)==2 and "qjwimage('N','j',1)" in mapping[0] and "qjwimage('N','j',0)" in mapping[1]
