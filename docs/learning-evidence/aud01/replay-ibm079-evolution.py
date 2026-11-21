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

samples="matrix(3,2,[0,1,1,3,2,5])"
for number,factor,answer in ((59,1,"3"),(60,2,"5")):
    ref=run(rows[number-1]["literal"])
    assert run(ref.replace("'A'",samples).replace(f'"λ_{factor}"',str(factor)))==answer
expansion=run(rows[54]["literal"]).replace("'A'",samples).replace("'λ'","2").replace("'m'","1").replace("'R'","0")
coefficients=run(expansion)
for slope,wanted in [(2,"1"),(3,"0")]:
    assert run(coefficients.replace('"a_0"',"0").replace('"a_1"',str(slope)))==wanted
# The notebook puts the opener before the dollar delimiter of the final span.
corrected=r"$\langle "+rows[60]["literal"][1:]
mean=run(corrected)
assert run(mean.replace("'A'",samples).replace('"λ_0"',"0"))=="1"
print("Verified two noisy samples, their zero-noise value and the expansion at two slopes.")
