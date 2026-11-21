"""Check scalar sample complexity, indexed costs and exact probabilities."""
import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess

p=argparse.ArgumentParser()
p.add_argument("worker",type=Path);p.add_argument("sessions",type=Path)
p.add_argument("--report",type=Path)
a=p.parse_args()
worker=a.worker.resolve()
env=dict(os.environ,QALCULATE_DEFINITIONS_DIR=str(worker.parent/"data"))
tests=[]
def run(expr,error=None):
    proc=subprocess.run([worker,"--json"],input=("quantum:"+expr).encode(),capture_output=True,env=env)
    if error:
        assert proc.returncode and error in proc.stderr.decode(),(expr,proc.stderr)
        return
    assert proc.returncode==0,(expr,proc.stderr)
    return json.loads(proc.stdout)["copy_text"]
def check(name,expr,expected=None):
    copied=run(expr)
    assert run(copied)==copied,(name,copied)
    if expected is not None:assert copied==expected,(name,copied,expected)
    tests.append((name,expr,copied))
    return copied
def row(n,i):
    return json.loads(Path(__file__).with_name(f"ibm{n}-inventory.json").read_bytes())["rows"][i-1]["literal"]
# X denotes a scalar improvement factor in the course's sample-complexity prose.
for index,expected in [(1,"1 ∕ 10"),(2,"100"),(3,"10")]:
    literal=row(132,index)
    scalar=check(f"scalar-{index}",literal.replace("X",'"X"'))
    check(f"tenfold-{index}",f'replace({scalar},"X",10)',expected)
check("default-pauli-x",f"qcompare({check('bare-X',row(132,3))},[0,1;1,0],4)","1")
cost=check("source-cost",row(130,6))
for bit,expected in [(0,"5"),(1,"7")]:
    check(f"cost-{bit}",f'replace({cost},vector("C","x_i"),vector(vector(vector(0,5),vector(1,7)),{bit}))',expected)
probability=check("measurement-probability",row(130,8))
for value,expected in [("1/4","1"),("1/2","0")]:
    check("weight-"+expected,f'replace({probability},vector("P_i","w_i"),vector({value},i/2))',expected)
check("hundred-qubits",row(133,1),str(2**100))
a.sessions.mkdir(parents=True,exist_ok=True)
inputs=[[name,expr,"0"] for name,expr,_ in tests]
if not a.report:
    (a.sessions/"inputs.json").write_text(json.dumps(inputs,ensure_ascii=False),encoding="utf8")
else:
    suite=json.loads((a.sessions/"result.json").read_bytes())
    records=json.loads((a.sessions/"records.json").read_bytes())
    assert suite["passed"] and suite["sessionsOnly"] and suite["calls"]==len(tests)==len(records)
    for rec,(name,expr,expected) in zip(records,tests):
        assert rec["id"]==name and rec["restored_same"] and rec["label"]==rec["reentry_label"]=="EXACT RESULT"
        assert expected==rec["copy_text"]==rec["reentry_text"]
        session=json.loads((a.sessions/(name+".qsession")).read_bytes().decode("utf-8-sig"))
        assert session["Expression"]==expr
    a.report.write_text(json.dumps(dict(worker_sha256=sha256(worker.read_bytes()).hexdigest(),
        suite=suite,cases=[dict(name=name,expression=expr,copy=result) for name,expr,result in tests]),
        ensure_ascii=False,indent=2)+"\n",encoding="utf8")
print(len(tests),"finite and symbolic checks")
