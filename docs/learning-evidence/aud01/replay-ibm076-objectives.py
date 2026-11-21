"""Compare the lesson objectives against independent enumeration of all assignments."""
from pathlib import Path
import itertools
import json
import os
import subprocess
import sys

worker=Path(sys.argv[1]).resolve()
env=dict(os.environ,QALCULATE_DEFINITIONS_DIR=str(worker.parent/"data"))
def run(expr):
    p=subprocess.run([worker,"--json"],input=("quantum:"+expr).encode(),capture_output=True,env=env,check=True)
    return json.loads(p.stdout)["copy_text"]

def matrix(rows):
    return "matrix(%d,%d,[%s])"%(len(rows),len(rows[0]),",".join(str(x) for row in rows for x in row))

source=json.loads(Path(__file__).with_name("ibm076-inventory.json").read_bytes())["rows"]
maximize,minimize,qubo=[run(source[i-1]["literal"]) for i in (1,8,9)]
for width,edges in [(2,[(0,1)]),(3,[(0,1),(1,2),(2,0)]),(4,[(0,1),(1,2),(2,3),(3,0)]),(3,[(0,0),(1,2),(1,2)])]:
    assignments=list(itertools.product(range(2),repeat=width))
    cost=max(sum(x[u]!=x[v] for u,v in edges) for x in assignments)
    for obj,sign in ((maximize,1),(minimize,-1)):
        expr=obj.replace("'E'",matrix(edges)).replace('n)',f'{width})')
        assert run(f"({expr})==({sign*cost})")=="1",(edges,expr)
for q in [((-1,2),(0,-3)),((1,0),(0,1)),((2,-1,0),(3,-2,1),(0,2,-1))]:
    width=len(q)
    optimum=min(sum(q[i][j]*x[i]*x[j] for i in range(width) for j in range(width))
                for x in itertools.product(range(2),repeat=width))
    expr=qubo.replace("'Q'",matrix(q)).replace('n)',f'{width})')
    assert run(f"({expr})==({optimum})")=="1",(q,expr)
assert run("qmaxcut(vector(),3)")=="0" and run("qbinaryminimum(vector(),0)")=="0"
print("Verified MaxCut, its negation, asymmetric quadratic matrices, and empty inputs.")

figures=json.loads(Path(__file__).with_name("ibm074-figures.json").read_bytes())["graph"]
graph=matrix(figures["edges"])
assert run(f"qmaxcut({graph},5)")==str(figures["maximum_cut"])=="5"

# Check both algebraic forms using individual assignments. The affine
# change of variables x=(1-z)/2 preserves the cost including its constant.
identity=run(source[18]["literal"])
objective=run(source[19]["literal"])
for q in [((-1,2),(0,-3)),((2,-1,0),(3,-2,1),(0,2,-1))]:
    for bits in itertools.product(range(2),repeat=len(q)):
        spins="vector("+",".join(str(1-2*x) for x in bits)+")"
        cost=sum(q[i][j]*bits[i]*bits[j] for i in range(len(q)) for j in range(len(q)))
        lhs=identity.replace("'Q'",matrix(q)).replace("'z'",spins)
        rhs=objective.replace("'Q'",matrix(q)).replace("'z'",spins)
        assert run(lhs)=="1" and run(f"({rhs})==({cost})")=="1",(q,bits)
print("Verified the unshifted binary-to-spin objective on twelve assignments.")

# Spin energies and the diagonal Pauli Hamiltonian agree on every basis word.
energy=run(source[27]["literal"])
comparison=run(source[29]["literal"])
hamiltonian=run(source[30]["literal"])
for q in [((-1,2),(0,-3)),((2,-1,0),(3,-2,1),(0,2,-1))]:
    width=len(q);indices=range(width)
    fields=[-sum(q[i][j]+q[j][i] for j in indices) for i in indices]
    field_vector="vector("+",".join(map(str,fields))+")"
    def bind(expr):
        return expr.replace("'Q'",matrix(q)).replace("'b'",field_vector)
    diag=[]
    for bits in itertools.product(range(2),repeat=width):
        z=[1-2*bit for bit in bits]
        value=sum(q[i][j]*z[i]*z[j] for i in indices for j in indices)+sum(fields[i]*z[i] for i in indices)
        diag.append(value)
        expr=bind(energy).replace("'z'","vector("+",".join(map(str,z))+")")
        assert run(f"({expr})==({value})")=="1"
    matrix_rows=[[v if i==j else 0 for j in range(len(diag))] for i,v in enumerate(diag)]
    assert run(bind(hamiltonian).replace('qoperatorref("H_C")',matrix(matrix_rows)))=="1"
    assert run(bind(comparison).replace("n)",f"{width})"))=="1"
assert run("qisingequivalent(matrix(2,2,[-1,0,0,-1]),vector(-5,-5),2)")=="0"
print("Verified spin energies, every diagonal entry, and matching and mismatched optimum sets.")

minimum=run(source[13]["literal"])
graph="qset(vector(qtuple(vector(0,4)),qtuple(vector(1,-3)),qtuple(vector(2,-3))))"
assert run(minimum.replace("'f'",graph))=="−3"
field_equation=run(source[25]["literal"])
grouped=run(source[23]["literal"])
weights=((2,-1,3),(3,-2,1),(0,2,-1))
for i in range(3):
    field=-sum(weights[i][j]+weights[j][i] for j in range(3))
    expr=field_equation.replace("'Q'",matrix(weights)).replace("'i'",str(i))
    assert run(expr.replace('"b_i"',str(field)))=="1"
    assert run(expr.replace('"b_i"',str(field+1)))=="0"
for z in itertools.product((-1,1),repeat=3):
    assert run(grouped.replace("'Q'",matrix(weights)).replace("'z'","vector("+",".join(map(str,z))+")"))=="1"
print("Verified the finite objective minimum and all row-plus-column fields on asymmetric coefficients.")
