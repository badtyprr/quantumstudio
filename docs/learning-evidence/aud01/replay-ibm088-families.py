"""Bind the SQD lesson's symbolic sets and ket families to finite examples."""
import json
import os
from pathlib import Path
import subprocess
import sys

worker = Path(sys.argv[1]).resolve()
env = dict(os.environ,QALCULATE_DEFINITIONS_DIR=str(worker.parent/"data"))
def run(expression):
    p = subprocess.run([worker,"--json"],input=("quantum:"+expression).encode(),env=env,capture_output=True,check=True)
    return json.loads(p.stdout)["copy_text"]
def source(n,row):
    rows=json.loads(Path(__file__).with_name(f"ibm{n:03}-inventory.json").read_bytes())["rows"]
    copied=run(rows[row-1]["literal"])
    assert run(copied)==copied
    return copied

# The source quiz explicitly contrasts strict and non-strict inclusion.
for row, reverse, strict in ((19,False,True),(20,False,False),(21,True,True),(22,True,False)):
    relation=source(88,row)
    for a,g in (({0,1},{0}),({0},{0}),({0},{0,2}),({0},{1}), (set(),{1})):
        concrete=relation
        for name,values in (("A",a),("G",g)):
            concrete=concrete.replace("'"+name+"'", "qset(vector("+",".join(map(str,sorted(values)))+"))")
        left,right=(g,a) if reverse else (a,g)
        assert run(concrete)==str(int(left<right if strict else left<=right))
basis=source(88,13).replace("'L'","3")
assert run(basis.replace("vector()","vector(1,7,2,4,3,7)"))=="qset(vector(7,4))"
assert run(source(88,13).replace("'L'","0"))=="qset(vector())"
ordered=source(88,28).replace("'d'","3")
assert run(ordered)=='vector(qketstate("φ_0"),qketstate("φ_1"),qketstate("φ_2"))'
assert run(source(88,12).replace("'θ'","0"))=='qoperatorref("U(0)")'
assert run(source(87,1).replace("n","5"))=="4"
print("Verified 20 subset cases, sampled basis de-duplication, Krylov ket order, circuit parameter and ordinal.")

orbit = source(88,26).replace("'H'","X").replace('"δt"',"pi/2").replace("'d'","3").replace('qketstate("φ_0")',"|0>")
for phase, truth in (("-i","1"),("i","0")):
    sequence = f"vector(0,|0>,1,({phase})*|1>,2,(-1)*|0>)"
    assert run(orbit.replace("vector()",sequence))==truth
assert run("qcompare(qkrylovstates(Z,|1>,0,1),qindexedketlist(\"s_\",0,0,vector(0,|1>)),4)")=="1"
for invalid in ("qkrylovstates(X,|0>,0,0)", "qkrylovstates(X,|00>,0,2)"):
    p=subprocess.run([worker,"--json"],input=("quantum:"+invalid).encode(),env=env,capture_output=True)
    assert p.returncode and b"Krylov" in p.stderr
print("Verified the three-step Krylov phase, its counterexample and invalid counts and dimensions.")
