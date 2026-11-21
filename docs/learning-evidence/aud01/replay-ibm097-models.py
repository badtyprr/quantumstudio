"""Check the actual classical ML formulas with finite features, kernels and models."""
import json
import os
from pathlib import Path
import subprocess
import sys

worker=Path(sys.argv[1]).resolve()
env=dict(os.environ,QALCULATE_DEFINITIONS_DIR=str(worker.parent/"data"))
rows=json.loads(Path(__file__).with_name("ibm097-inventory.json").read_bytes())["rows"]

def run(expr,error=None):
    p=subprocess.run([worker,"--json"],input=("quantum:"+expr).encode(),env=env,capture_output=True)
    if error:
        assert p.returncode and error in p.stderr.decode(),(expr,p.stderr)
        return
    assert p.returncode==0,(expr,p.stderr)
    return json.loads(p.stdout)["copy_text"]

def source(n):
    result=run(rows[n-1]["literal"])
    assert run(result)==result
    return result

def vectors(expr):
    for index,value in [('i','1,2'),('j','3,4')]:
        expr=expr.replace(f"""qindexedlabel("x_",'{index}',"")""",f"vector({value})")
    return expr

features="vector(vector(vector(1,2),vector(1,2,5)),vector(vector(3,4),vector(3,4,25)))"
assert run(vectors(source(19)).replace("'Φ'",features))=="136"
assert run(vectors(source(25)))=="11"
kernel_table="vector(vector(vector(vector(1,2),vector(3,4)),136))"
assert run(vectors(source(20)).replace("'k'",kernel_table))=="136"
feature=source(35).replace("""qindexedlabel("x_",'i',"")""","vector(1,2)")
assert run(feature.replace("'Φ'",features))=="vector(1,2,5)"
assert run("qvectordot(matrix(2,1,[i,1]),vector(i,2))")=="1"
run("qvectordot(vector(1,2),vector(3))","equal lengths")
run("qfeatureat(vector(vector(2,7)),2)","row or column vector")

model=source(9).replace("'Θ'","vector(2,3,4)").replace("'Φ'",features)
model=model.replace("'x'","vector(1,2)").replace("'b'","1")
for value,expected in [(29,"1"),(30,"0")]:
    assert run(model.replace('"f_1"',f"vector(vector(vector(1,2),{value}))"))==expected

dual=source(10)
assert """qvectorref(qindexedlabel("x_","qboundindex_0",""))""" in dual
dual=dual.replace('qindexedlabel("x_","qboundindex_0","")',"vector(1,2)")
dual=dual.replace('qindexedlabel("α_","qboundindex_0","")',"2")
dual=dual.replace('qindexedlabel("y_","qboundindex_0","")',"(-1)")
dual=dual.replace("'Φ'",features).replace("'x'","vector(3,4)").replace("'b'","1").replace(",1,n,",",1,1,")
assert run(dual.replace('"f_2"',"vector(vector(vector(3,4),-271))"))=="1"

neuron=source(42).replace("'w'","vector(2,3)").replace("'x'","vector(1,2)").replace("'b'","-9")
neuron=neuron.replace("'σ'","vector(vector(-1,0),vector(1,1))")
for value,expected in [(0,"1"),(1,"0")]:
    assert run(neuron.replace("'f'",f"vector(vector(vector(1,2),{value}))"))==expected
print("Verified raw and feature-space dot products, kernel lookup, primal and dual models and a nonlinear perceptron.")

def other_source(lesson,n):
    path=Path(__file__).with_name(f"ibm{lesson:03}-inventory.json")
    result=run(json.loads(path.read_bytes())["rows"][n-1]["literal"])
    assert run(result)==result
    return result

born=other_source(96,19).replace('qketstate("φ_i")',"|0>").replace("qketstate('ψ')","(|0>+i*|1>)/sqrt(2)")
assert run(born.replace('"P_i"',"0.5"))=="1"
assert run(born.replace('"P_i"',"1"))=="0"
assert source(31)=="qstatecall('Φ',qvectorref('x'))"
for row,stage,expected in [(172,1,"01"),(174,2,"11")]:
    state=other_source(98,row)
    for index,value in enumerate(["pi","0","pi/2","0"]):
        state=state.replace(f'"θ_{index}"',f"({value})")
    label=f'qketstate("ψ_b{stage}")'
    assert run(state.replace(label,f"(i*|{expected}>)"))=="1"
    assert run(state.replace(label,f"(-i*|{expected}>)"))=="0"
phase=other_source(98,268).replace("'x'","vector(2,4)")
assert run(phase.replace('"φ_S"',"vector(vector(vector(2,4),8))"))=="8"
evolution=other_source(98,272).replace("'H'","Z").replace("'t'","(pi/2)")
assert run(f"qcompare({evolution},(i*Z),4)")=="1"
print("Verified squared overlaps, labeled circuit states and signed encoding phases.")

real_space=other_source(99,2).replace("'d'","2")
for vector,expected in [("vector(2,3)","1"),("vector(i,3)","0"),("vector(2,3,4)","0")]:
    assert run(real_space.replace("'x'",vector))==expected
feature_space=other_source(99,3).replace("'x'","vector(1,2)").replace("'Φ'",features)
assert run(feature_space.replace('"d_prime"',"3"))=="1"
assert run(feature_space.replace('"d_prime"',"2"))=="0"
ordering=other_source(99,4).replace("'d'","2")
assert run(ordering.replace('"d_prime"',"3"))=="1"
assert run(ordering.replace('"d_prime"',"2"))=="0"
for row,fraction in [(3,"7/10"),(4,"3/10"),(20,"3/5")]:
    assert run(f"qcompare({other_source(100,row)},{fraction},4)")=="1"
encoder=other_source(98,215).replace('"U_ZFM"',"vector(vector(vector(2,3),Z))").replace("'x'","vector(2,3)")
assert run(f"qcompare({encoder},Z,4)")=="1"
dataset=other_source(98,35)
# A finite data set contains ordered triples and is insensitive to their listing order.
points=["4,8,5","9,8,6","2,9,2","5,7,0","3,7,5"]
def tuples(items):
    return "qset(vector("+",".join("qtuple(vector("+v+"))" for v in items)+"))"
assert run(dataset.replace('"X_ex"',tuples(points[::-1])))=="1"
assert run(dataset.replace('"X_ex"',tuples(points[:-1])))=="0"
print("Verified real feature-space dimensions, finite datasets, percentages and encoder binding.")

# U acts before W. Reversing X and H would change the sign of <X>.
qnn=other_source(100,9).replace("'θ'","3").replace("'x'","vector(2,4)")
classes=other_source(100,8).replace("'θ'","3").replace("'x'","vector(2,4)")
def model_table(value):
    return f"vector(vector(vector(3,vector(2,4)),{value}))"
for outcome in (-1,0,1):
    assert run(classes.replace("'f'",model_table(outcome)))==("0" if outcome==0 else "1")
for x_gate,h_gate in [("X","H"),("(X ⊗ I)","(H ⊗ I)")]:
    circuit=qnn.replace("'U'",f"vector(vector(vector(2,4),{x_gate}))")
    circuit=circuit.replace("'W'",f"vector(vector(3,{h_gate}))").replace("'O'",x_gate)
    assert run(circuit.replace("'f'",model_table(-1)))=="1"
    assert run(circuit.replace("'f'",model_table(1)))=="0"
run("qzeroimage(matrix(3,3,[1,0,0,0,1,0,0,0,1]))","power-of-two dimension")
print("Verified both classifier labels and signed expectations on one and two qubits.")
