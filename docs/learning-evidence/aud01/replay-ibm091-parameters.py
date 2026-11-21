"""Check vector-valued circuit parameters, state arguments and operator lookup."""
from pathlib import Path
import json
import os
import subprocess
import sys

worker=Path(sys.argv[1]).resolve()
env=dict(os.environ,QALCULATE_DEFINITIONS_DIR=str(worker.parent/"data"))
def run(expr, *, error=None, family=None):
    request="quantum:"+expr
    flags=["--json"]
    if family is not None:
        name,body=family
        request=f"QSTATES1\n1\n{len(name.encode())}\n{len(body.encode())}\n{name}{body}"+request
        flags.append("--states")
    p=subprocess.run([worker,*flags],input=request.encode(),capture_output=True,env=env)
    if error:
        assert p.returncode and error in p.stderr.decode(),(expr,p.stdout,p.stderr)
        return
    assert p.returncode==0,(expr,p.stderr)
    return json.loads(p.stdout)["copy_text"]

rows=json.loads(Path(__file__).with_name("ibm091-inventory.json").read_bytes())["rows"]
def source(row):
    a=run(rows[row-1]["literal"])
    assert run(a)==a
    return a
assert source(4)=="qvectorref('θ')"
assert run(source(4).replace("'θ'","vector(2,5)"))=="vector(2,5)"
run("qvectorref(3)",error="row or column vector")
run("qvectorref(matrix(2,2,[1,2,3,4]))",error="row or column vector")
run("qvectorref(vector(1,infinity))",error="finite scalar")
# The index i is an integer placeholder in the source.
assert run(source(46).replace("'i'","0"))==run(source(5))
parameter=source(6)
table="vector(vector(vector(0,0),X),vector(vector(1,0),Z))"
call=parameter.replace('"U_var"',table)
for key,gate in (("0,0","X"),("1,0","Z")):
    expr=call.replace('qindexedlabel("θ_",0,"")',f"vector({key})")
    assert run(f"qcompare({expr},{gate},4)")=="1"
missing=call.replace('qindexedlabel("θ_",0,"")',"vector(4,0)")
run(missing,error="no entry")
run("qoperatorat(vector(vector(vector(0,0),X),vector(vector(0,0),Z)),vector(0,0))",error="Conflicting")
state=source(14).replace("'ψ'","'trial'").replace('qindexedlabel("θ_",0,"")',"vector(2,5)")
assert run(state,family=("trial(x)","|1>"))=="matrix(2,1,[0,1])"
print("Verified the VQE parameter indices, vector shapes, two bound gates and a vector-parameter state family.")

assert source(35)=='qketstate("ψ_var")'
assert source(84)=='"N_GCP"'
assert run(source(81).replace("n","7"))=="7"
assert run(r"$U_{var}(\vec{\theta})$")==run(r"$U_{\text{var}}(\vec{\theta})$")

# Verify each row of the lower-bound derivation for an equal mixture of
# energies 2 and 4. A trial energy can satisfy the bound yet miss the mean.
import re
derivation=source(45).replace('"E_0"', '2')
derivation=re.sub(r'qindexedlabel\("c_","qboundindex_\d+",""\)', '(1/sqrt(2))', derivation)
derivation=re.sub(r'qindexedlabel\("E_",("qboundindex_\d+"),""\)', r'(2+2*\1)', derivation)
derivation=re.sub(r'\bn\b', '1', derivation)
for energy, expected in [(1,(0,0)), (2,(0,1)), (3,(1,1)), (4,(0,1))]:
    assert run(derivation.replace('"E_var"',str(energy))) == (
        r'\begin{gathered}%d\\%d\end{gathered}' % expected)

def course_source(course, row):
    inventory=Path(__file__).with_name(f"ibm{course:03}-inventory.json")
    result=run(json.loads(inventory.read_bytes())["rows"][row-1]["literal"])
    assert run(result)==result
    return result

scaled=course_source(92,81).replace("qketstate('b')","2*|0>").replace("qketstate(x)","|0>")
assert run(scaled.replace("'c'","2"))=="1"
assert run(scaled.replace("'c'","0"))=="0"
assert run(course_source(93,114).replace('"shots"',"400"))=="20"
projected=course_source(94,89)
eigenproblem=course_source(94,90).replace(projected,"Z").replace("qstatecall('ψ','k')","|0>")
energy_label="""qindexedlabel("E(",'k',')')"""
assert run(eigenproblem.replace(energy_label,"1"))=="1"
assert run(eigenproblem.replace(energy_label,"-1"))=="0"
print("Verified the variational energy bound, ket scaling, shot count and sampled eigenproblem.")

# The quadratic objective acts on a correction vector. Its value at |1>
# for A=Z, residual |0> and d=4 is -1-2*0+4=3.
objective=course_source(92,106).replace('qnamedket("p_0")',"|1>").replace('qnamedket("R_0")',"|0>")
objective=objective.replace("'A'","Z").replace("'d'","4")
for value,expected in [(3,"1"),(7,"0")]:
    table=f"vector(vector(|0>,9),vector(|1>,{value}))"
    assert run(objective.replace("'f'",table))==expected
scalar=course_source(92,112).replace('qnamedket("p_0")',"|0>")
assert run(scalar.replace("'f'","vector(vector(|0>,9),vector(|1>,3))"))=="9"
run(scalar.replace("'f'","vector(vector(|1>,3))"),error="no entry")
run(scalar.replace("'f'","vector(vector(|0>,1),vector(|0>,2))"),error="Conflicting")
run(scalar.replace("'f'","vector(vector(|0>,Z))"),error="finite numeric value")
filtered=course_source(92,347).replace('"E_0"',"2")
for value,expected in [(-1,"1"),(1,"1"),(0,"0")]:
    assert run(filtered.replace("'f'",f"vector(vector(2,{value}))"))==expected
normalization=course_source(92,386).replace('"E_0"',"2").replace("'f'","vector(vector(2,1))")
for value,expected in [(1,"1"),(2,"0")]:
    assert run(normalization.replace("'p'",f"vector(vector(0,{value}))"))==expected
print("Verified scalar objective and energy filter values at distinct vector and scalar inputs.")

# The projected Hamiltonian and overlap metric may be nontrivial matrices.
problem=course_source(92,296).replace('"H_tilde"','matrix(2,2,[6,0,0,5])')
problem=problem.replace("'S'","matrix(2,2,[2,0,0,1])").replace('"vector_c"','matrix(2,1,[1,0])')
for eigenvalue,expected in [(3,"1"),(6,"0")]:
    assert run(problem.replace("'c'",str(eigenvalue)))==expected

# <0|exp(+ij Z dt) Z exp(-ik Z dt)|0> equals exp(i(j-k)dt).
entry=course_source(92,313).replace("'H'","Z").replace("qnamedket('ψ')","|0>")
entry=entry.replace('"dt"',"pi/2").replace('''qindexedcoefficient("H_tilde_",'j','k')''','"entry"')
for j,k,expected in [(1,0,"i"),(0,1,"(-i)"),(1,1,"1")]:
    sample=entry.replace("'j'",str(j)).replace("'k'",str(k))
    assert run(sample.replace('"entry"',expected))=="1"
    assert run(sample.replace('"entry"',"0"))=="0"
print("Verified the generalized eigenproblem and both signs of Krylov time evolution.")

# The same polynomial acts on the Hamiltonian and on its eigenvalues.
spectral=course_source(92,333)
index='"qboundindex_0"'
energy=f'qindexedlabel("E_",{index},"")'
spectral=spectral.replace(f"qindexedket({energy})",f"qbasis({index},2)")
spectral=spectral.replace(energy,f"(1-2*{index})").replace(f'qindexedlabel("γ_",{index},"")',"1")
spectral=spectral.replace("'N'","1").replace("'H'","Z").replace("'f'","vector(1,2,3)")
assert run(spectral.replace("qnamedket('ψ')","(|0>+|1>)"))=="1"
assert run(spectral.replace("qnamedket('ψ')","(|0>-|1>)"))=="0"
assert run("qpolynomialat(vector(1,2,3),X)")=="matrix(2,2,[4,2,2,4])"
assert run("qpolynomialat(vector(4),Z)")=="matrix(2,2,[4,0,0,4])"
assert run("qcompare(qpolynomialat(vector(3,2),matrix(1,1,[4])),matrix(1,1,[11]),4)")=="1"
run("qpolynomialat(vector(2,3),matrix(2,1,[1,1]))",error="square matrix")
run("qpolynomialat(vector(2,infinity),X)",error="finite numbers")
print("Verified the polynomial spectral expansion and finite matrix evaluation.")

# At dt=1 and delta=pi/2, the degree-two filter has denominator T_2(3)=17.
filter_chain=course_source(92,378).replace('"dt"',"1").replace("'δ'","(pi/2)")
filter_chain=filter_chain.replace('"E_0"',"0").replace("'d'","2").replace("'E'","(pi/2)")
filter_chain=filter_chain.replace("'g'","vector(vector(pi/2,1/2))").replace('"p_star"',"vector(vector(1/2,1/17))")
for value,expected in [("1/17","1"),("1","0")]:
    assert run(filter_chain.replace("'f'",f"vector(vector(pi/2,{value}))"))==expected
assert run("qchebyshev(0,7)")=="1"
assert run("qchebyshev(3,2)")=="26"
run("qchebyshev(-1,2)",error="degree")
gap=course_source(92,388).replace("'E'","2").replace('"E_0"',"5")
for threshold,result in [(-4,"1"),(2,"1"),(3,"0"),(4,"0")]:
    assert run(gap.replace("'δ'",str(threshold)))==result
print("Verified a normalized Chebyshev filter and the strict energy-gap threshold.")
