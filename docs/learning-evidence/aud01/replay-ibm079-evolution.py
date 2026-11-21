"""Check the Hamiltonian examples without identifying a free H with a Hadamard gate."""
import json
import os
from pathlib import Path
import subprocess
import sys

worker=Path(sys.argv[1]).resolve()
env=dict(os.environ,QALCULATE_DEFINITIONS_DIR=str(worker.parent/"data"))
def run(expr):
    p=subprocess.run([worker,"--json"],input=("quantum:"+expr).encode(),capture_output=True,env=env,check=True)
    return json.loads(p.stdout)["copy_text"]

rows=json.loads(Path(__file__).with_name("ibm079-inventory.json").read_bytes())["rows"]
propagator=run(rows[38]["literal"])
for h,t,expected in [("Z","pi/2","(-i)*Z"),("X","0","I"),("X","pi/2","(-i)*X")]:
    result=propagator.replace("'H'",h).replace("'t'",t)
    assert run(f"qcompare({result},{expected},4)")=="1",(h,t,result)
commutator=run(rows[40]["literal"])
for a,b,expected in [("X","Z","1"),("Z","Z","0"),("I","X","0")]:
    result=commutator.replace('"H_A"',a).replace('"H_B"',b)
    assert run(result)==expected,(a,b,result)
print("Verified the propagators and commuting and noncommuting Hamiltonian terms.")
