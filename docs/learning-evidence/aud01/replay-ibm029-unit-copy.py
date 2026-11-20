"""Check unit-bearing Quantum-mode Copy results through Windows and fresh worker processes."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

parser=argparse.ArgumentParser()
parser.add_argument("package",type=Path)
parser.add_argument("directory",type=Path)
parser.add_argument("--report",type=Path)
args=parser.parse_args()
worker=args.package.resolve()/"quantum-worker.exe"
env=dict(os.environ,QALCULATE_DEFINITIONS_DIR=str(worker.parent/"data"))
inventory=json.loads(Path(__file__).with_name("ibm029-inventory.json").read_bytes())
cases={}
for number in (363,369,388,399):
    cases[f"M{number}"]=inventory["rows"][number-1]["literal"]
cases.update(speed_squared="c^2",speed_matrix="[c;2*c]",frequency="MHz",
             length='qphysicalunit("m","k")',time='qphysicalunit("s","m")',scalar='"c"', angle="sin(t)", nested_angle="sin(sin(t))")
inputs=[[key,expr,"0"] for key,expr in cases.items()]
directory=args.directory
if not args.report:
    directory.mkdir(parents=True,exist_ok=True)
    (directory/"inputs.json").write_bytes(json.dumps(inputs).encode())
    raise SystemExit()


def evaluate(expr,quantum=True):
    return subprocess.run([worker,"--json"],input=(("quantum:" if quantum else "")+expr).encode(),
                          capture_output=True,env=env,timeout=30)


def copy(expr,quantum=True):
    proc=evaluate(expr,quantum)
    assert proc.returncode==0,(expr,proc.stderr)
    result=json.loads(proc.stdout)
    assert not result["approximate"],expr
    return result["copy_text"]


records_path=directory/"records.json"
records=json.loads(records_path.read_bytes())
suite=json.loads((directory/"result.json").read_bytes())
assert json.loads((directory/"inputs.json").read_bytes())==inputs
assert suite["passed"] and suite["clipboardRestored"] and suite["calls"]==len(inputs)==len(records)
values={}
for (key,expr,_),record in zip(inputs,records):
    assert key==record["id"] and record["restored_same"] and record["label"]==record["reentry_label"]=="EXACT RESULT"
    saved=json.loads((directory/(key+".qsession")).read_bytes().decode("utf-8-sig"))
    assert saved["Mode"]==0 and saved["Expression"]==expr and not saved["Matrices"]
    text=record["copy"]
    assert text==record["second_copy"]==copy(text), key
    def check(expression,expected):
        actual=copy(expression)
        assert actual==str(expected),(key,expression,actual)
    if key=="M363":
        for b,n,k in ((2,2,1),(2,3,0),(-3,-3,1)):
            check(f'replace(replace(({text}),"b",{b}),"N",({n}*c))',k)
    elif key in ("M388","M399"):
        for d,n,k in ((3,3,1),(3,2,0)):
            check(f'replace(replace(({text}),"d",{d}),"N",({n}*c))',k)
    elif key=="M369":
        check(f"({text})/c",1)
    elif key=="speed_squared":
        check(f"({text})/(c*c)",1)
    elif key=="speed_matrix":
        for i in (1,2):
            check(f"element(({text}),{i},1)/c",i)
    elif key=="frequency":
        check(f"({text})/kHz",1000)
    elif key=="length":
        check(f'({text})/qphysicalunit("m","")',1000)
    elif key=="time":
        check(f'1000*({text})/qphysicalunit("s","")',1)
    elif key in ("angle","nested_angle"):
        check(f'replace(({text}),"t",0)',0)
    elif key=="scalar":
        check(f'replace(({text}),"c",7)',7)
    values[key]=dict(display=record["display"],copy=text)

classical=copy("c",False)
assert "qphysicalunit" not in classical and copy(f"({classical})/c",False)=="1"
for bad in ('qphysicalunit("missing_unit","")','qphysicalunit("m","missing_prefix")'):
    proc=evaluate(bad)
    assert proc.returncode==2 and b"Unknown physical unit or prefix" in proc.stderr
report=dict(source=inventory["source"],notebook_sha256=inventory["source_sha256"],
            worker_sha256=hashlib.sha256(worker.read_bytes()).hexdigest(),records_sha256=hashlib.sha256(records_path.read_bytes()).hexdigest(),
            inputs=inputs,values=values,classical_speed_copy=classical)
args.report.write_bytes((json.dumps(report,ensure_ascii=False,indent=2)+"\n").encode())
print(len(records),"Windows round trips passed, including scalar and unit controls")
