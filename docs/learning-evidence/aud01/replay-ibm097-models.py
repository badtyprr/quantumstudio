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
