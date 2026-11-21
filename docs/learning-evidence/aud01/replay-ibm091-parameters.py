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
