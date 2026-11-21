"""Verify the total-spin context and compare the source rotation to the actual gate."""
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
for i in (1,2):
    expr=check(f"spin-source-{i}","spin:"+row(109,i))
    for twice_spin in (0,1,2,3,4):
        check(f"spin-{i}-{twice_spin}",expr.replace("'S'",f"({twice_spin}/2)"),str(twice_spin+i-1))
check("phase-gate-default","qcompare(2*S,matrix(2,2,[2,0,0,2*i]),4)","1")
run("qspinnumber(-1/2)","nonnegative")
run("qspinnumber(1/3)","half-integer")
check("molecule",row(109,3))
rotation=check("rotation-source",row(110,3))
check("rotation-axis",f"qcompare({rotation},Ry(pi/4),4)","1")
check("rotation-sign",f"qcompare({rotation},Ry(-pi/4),4)","0")
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
