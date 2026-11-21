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

# The side condition N=2^n is independent of entrywise matrix equality.
definition = run(source(88,3).replace("'N'","4"))
for r in range(4):
    for c in range(4):
        definition=definition.replace(f'"H_{r},{c}"',str(int(r==c)))
for qubits,operator,truth in [(2,"identity(4)","1"),(1,"identity(4)","0"),(2,"2*identity(4)","0")]:
    bound=definition.replace("(n)",f"({qubits})").replace("qoperatorref('H')",operator)
    assert run(bound)==truth

expansion=run(source(88,8).replace("'Q'","2"))
for label,value in (("α_1","2"),("P_1","X"),("α_2","-1"),("P_2","Z")):
    expansion=expansion.replace('"'+label+'"',"("+value+")")
for total,truth in [("(2*X-Z)","1"),("(2*X+Z)","0")]:
    assert run(expansion.replace("qoperatorref('H')",total))==truth

# A finite realization of M004's annotated project/diagonalize diagram.
# Columns are |00> and |11>. Couplings to omitted basis vectors drop out.
hamiltonian="matrix(4,4,[2,1,0,i,1,4,0,0,0,0,-2,0,-i,0,0,2])"
basis="matrix(4,2,[1,0,0,0,0,0,0,1])"
projection=f"qmul(qdag({basis}),qmul({hamiltonian},{basis}))"
assert run(f"qcompare({projection},matrix(2,2,[2,i,-i,2]),4)")=="1"
assert run(f"qcompare(qheigenvalues({projection}),matrix(2,1,[1,3]),4)")=="1"
print("Verified Hamiltonian dimension, signed Pauli expansion, subspace projection and projected energies.")

rows=json.loads(Path(__file__).with_name("ibm088-inventory.json").read_bytes())["rows"]
context='matrixcontext("H",(4),(4),"hermitian"):'
for row in (3,7,8,15):
    expr=run(context+rows[row-1]["literal"])
    assert """operatorparam('H',4,"hermitian")""" in expr
    assert run(expr)==expr
entry=run(context+rows[6]["literal"])
entry=entry.replace("""operatorparam('H',4,"hermitian")""",hamiltonian)
for first,last,value in (("00","11","i"),("11","00","-i")):
    actual=entry.replace('qnamedket("b_i")',f"|{first}>").replace('qnamedket("b_j")',f"|{last}>")
    assert run(f"qcompare({actual},{value},4)")=="1"
print("Verified the declared Hamiltonian across four formulas and both conjugate entries.")
