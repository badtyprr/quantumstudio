"""Verify prepared states, indexed circuits, cost functions and gradient steps."""
from pathlib import Path
import json
import os
import subprocess
import sys

worker=Path(sys.argv[1]).resolve()
env=dict(os.environ,QALCULATE_DEFINITIONS_DIR=str(worker.parent/"data"))
def run(expr, error=None):
    p=subprocess.run([worker,"--json"],input=("quantum:"+expr).encode(),env=env,capture_output=True)
    if error:
        assert p.returncode and error in p.stderr.decode(),(expr,p.stderr)
        return
    assert p.returncode==0,(expr,p.stderr)
    return json.loads(p.stdout)["copy_text"]

def row(n,i):
    path=Path(__file__).with_name(f"ibm{n}-inventory.json")
    return json.loads(path.read_bytes())["rows"][i-1]["literal"]

def source(n,i):
    s=run(row(n,i));assert run(s)==s,(n,i,s,run(s))
    return s

prepared=source(102,2).replace('"U_R"',"X")
assert run(prepared.replace('"ρ_ref"',"|1>"))=="1"
assert run(prepared.replace('"ρ_ref"',"|0>"))=="0"
for gate,expected in [("(I ⊗ I)","1"),("(X ⊗ I)","0")]:
    assert run(source(102,5).replace('"U_R"',gate))==expected
assert source(102,9)=="1"
for gate,expected in [("(I ⊗ X)","1"),("(X ⊗ I)","0")]:
    assert run(source(102,10).replace('"U_R"',gate))==expected
superposition=row(102,22).replace("U_{R}",r"|\rho\rangle")
target=run(superposition)
assert run(target.replace('"ρ_ref"',"((|100>+|111>)/sqrt(2))"))=="1"
assert run(target.replace('"ρ_ref"',"((|100>-|111>)/sqrt(2))"))=="0"
run(row(102,22),"cannot equal a prepared ket")
run("qwireapply(X,2,-1,|00>)","in-range wires")
run("qwireapply(X,0,0,|00>)","distinct")
assert run("qwireapply(Y,0,-1,|00>)")==run("(i*|01>)")
assert run("qwireapply(X,0,1,|01>)")==run("|01>")
assert run("qwireapply(X,0,1,|11>)")==run("|10>")

for n,i in [(101,31),(104,24),(104,81)]:
    s=source(n,i)
    assert "qbars(" in s
cost=source(105,10).replace("'C'","vector(vector(vector(1,2),5))").replace("'θ'","vector(1,2)")
assert run(cost)=="5"
grad=source(105,11).replace('"∇C"',"vector(vector(vector(1,2),vector(2,4)))").replace("'θ'","vector(1,2)")
assert run(grad)=="vector(2,4)"
assert source(105,1)=='qvectorref("θ_star")'
print("Verified reference-state preparation, register width, little-endian gates, probability expressions and parameter lookups.")

update=source(105,12).replace('qindexedlabel("θ_",\'n\',"")',"vector(1,2)")
update=update.replace('qindexedlabel("θ_",qadd(\'n\',1),"")',"vector(0,0)")
update=update.replace("'θ'","vector(1,2)").replace('"∇C"',"vector(vector(vector(1,2),vector(2,4)))")
assert run(update.replace("'η'","(1/2)"))=="1"
assert run(update.replace("'η'","0"))=="0"
energy=source(106,74).replace("qstatecall('ψ',qvectorref('θ'))","|1>").replace("'H'","Z")
energy=energy.replace("'θ'","vector(1,2)")
for value,expected in [(-1,"1"),(1,"0")]:
    assert run(energy.replace('"C_VQE"',f"vector(vector(vector(1,2),{value}))"))==expected

# Bind the source observables to an independent Pauli construction. Check
# the eigenpairs in the displayed order, including the repeated eigenvalue.
operator="(2*(I ⊗ I)-2*(X ⊗ X)+3*(Y ⊗ Y)-3*(Z ⊗ Z))"
assert run(source(107,1).replace('"O_1"',operator))=="1"
assert run(source(107,1).replace('"O_1"',"(I ⊗ I)"))=="0"
states=["((|00>+|11>)/sqrt(2))","((|00>-|11>)/sqrt(2))",
        "((|01>-|10>)/sqrt(2))","((|01>+|10>)/sqrt(2))"]
values=source(107,2);vectors=source(107,3)
for j,(state,value) in enumerate(zip(states,[-6,4,4,6])):
    values=values.replace(f'"λ_{j}"',f"({value})")
    vectors=vectors.replace(f'"φ_{j}"',state)
    assert run(f"qcompare(qmul({operator},{state}),qmul({value},{state}),4)")=="1"
assert run(values)==run(vectors)==r"\begin{gathered}1\\1\\1\\1\end{gathered}"
diagonal=source(104,154)
for index in range(16):
    bits=f"{index:04b}"
    signs=[1 if b=="0" else -1 for b in bits]
    expected=sum(signs[a]*signs[b] for a,b in [(2,3),(1,3),(1,2),(0,3),(0,1)])
    assert run(f"qexpect({diagonal},|{bits}>)")==run(str(expected))
run("$XX + XYZ$","equal register width")
print("Verified four eigenpairs and all 16 diagonal Max-Cut energies.")

indexed_cost=source(106,110)
indexed_cost=indexed_cost.replace('qindexedlabel("C_",\'k\',"")',"vector(vector(vector(1,2),7))")
assert run(indexed_cost.replace("'θ'","vector(1,2)"))=="7"
coefficients=source(106,123).replace("'S'","2")
assert run(coefficients)=='qset(vector("a_0","a_1","a_2","b_1","b_2"))'
# The least-squares residual (-1,-1,1) is nonzero but orthogonal to both columns.
normal=source(106,132).replace("'F'","matrix(3,2,[1,0,0,1,1,1])")
normal=normal.replace("'c'","matrix(3,1,[1,3,7])")
assert run(normal.replace("'a'","matrix(2,1,[2,4])"))=="1"
assert run(normal.replace("'a'","matrix(2,1,[2,3])"))=="0"
print("Verified indexed costs, Fourier coefficients and the rectangular least-squares system.")
