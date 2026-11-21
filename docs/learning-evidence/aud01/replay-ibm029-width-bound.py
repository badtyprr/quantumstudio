"""Check the original width comparison with an explicit relationship between widths."""
import argparse
import json
import os
from pathlib import Path
import subprocess

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument("worker",type=Path)
parser.add_argument("directory",type=Path)
parser.add_argument("--clipboard",action="store_true")
args=parser.parse_args()
if not __debug__: raise RuntimeError("Assertions must be enabled")
worker=args.worker.resolve()
env=dict(os.environ,QALCULATE_DEFINITIONS_DIR=str(worker.parent/"data"))
rows=json.loads(Path(__file__).with_name("ibm029-inventory.json").read_bytes())["rows"]
literal=rows[348]["literal"]
cases=[("independent-widths",literal,"0","0")]
for name,rule,value in (("lesson-upper-bound","2*n+1","1"),("linear","3*n+8","1"),
                        ("quadratic","n^2","0"),("constant","8","1")):
    cases.append((name,f'replace(({literal}),"m",{rule})',"0",value))
cases += [("cubic-circuit-cost","(2*n+1)*n^2+(2*n+1)+(2*n+1)^2=O(n^3)","0","1"),
          ("quadratic-cost-control","(2*n+1)*n^2+(2*n+1)+(2*n+1)^2=O(n^2)","0","0")]
def evaluate(expr):
    p=subprocess.run([worker,"--json"],input=("quantum:"+expr).encode(),capture_output=True,env=env,check=True,timeout=20)
    return json.loads(p.stdout)["copy_text"]

for key,expr,mode,value in cases:
    assert evaluate(expr)==value and evaluate(value)==value,key
moduli=set(range(2,513))
for bits in (16,32,64,128,256,512,1024):
    moduli.update([(1<<bits)+offset for offset in (-1,0,1)])
for N in moduli:
    # ceil(log2(N)) and ceil(log2(N squared)) use integer bit lengths.
    n=(N-1).bit_length()
    m=(N*N-1).bit_length()+1
    assert 0<m<=2*n+1 and (1<<(m-2))<N*N<=(1<<(m-1))
(args.directory/"inputs.json").write_text(json.dumps([list(c[:3]) for c in cases]),"utf8")
report=dict(span=rows[348]["id"],moduli_checked=len(moduli),growth_checks=len(cases))
if args.clipboard:
    records=json.loads((args.directory/"records.json").read_text("utf-8-sig"))
    assert len(records)==len(cases)
    for r,(key,expr,mode,value) in zip(records,cases):
        assert r["id"]==key and r["restored_same"] and r["copy"]==r["second_copy"]==value
    result=json.loads((args.directory/"result.json").read_text("utf-8-sig"))
    assert result["passed"] and result["clipboardRestored"] and not result["sessionsOnly"]
    report["clipboard_sessions"]=len(records)
print(json.dumps(report,indent=2))
