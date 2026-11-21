"""Compare the printed width and logarithm with exact integer bit lengths."""
import argparse
import json
import os
import subprocess
from pathlib import Path

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument("worker",type=Path)
parser.add_argument("directory",type=Path)
parser.add_argument("--verify-clipboard",action="store_true")
args=parser.parse_args()
worker=args.worker.resolve()
env=dict(os.environ,QALCULATE_DEFINITIONS_DIR=str(worker.parent/"data"))
def evaluate(expr):
    p=subprocess.run([worker,"--json"],input=("quantum:"+expr).encode(),env=env,capture_output=True,timeout=30,check=True)
    return json.loads(p.stdout)["copy_text"]

rows=json.loads(Path(__file__).with_name("ibm029-inventory.json").read_bytes())["rows"]
width, log = (rows[i-1]["literal"] for i in (136,379))
cases={"M136":(width,8),"M379":(log,8),"explicit-base":(r"$\log_{3}(81)$",8),
       "natural":(r"$\ln(1)$",8),"fraction":(r"$\lfloor\log(7/8)\rfloor$",8),"default":(width,0)}
expected={}
for key,(formula,mode) in cases.items():
    prefix="binarylogs:" if mode==8 else ""
    expected[key]=evaluate(prefix+formula)
    assert expected[key]==evaluate(prefix+expected[key]), key
assert [expected[k] for k in ("explicit-base","natural","fraction")]==["4","0","−1"]
assert expected["M136"] != expected["default"]
def bind_width(copied,modulus,bits):
    return f'replace(replace(({copied}),"N",{modulus}),n,{bits})'
assert evaluate(bind_width(expected["default"],21,5))=="0"
moduli=sorted({21,*(2**k+d for k in (1,2,3,4,5,8,16,32,53,128) for d in (-1,0,1) if 2**k+d>=2)})
for modulus in moduli:
    bits=(modulus-1).bit_length()
    for trial in (bits-1,bits,bits+1):
        assert evaluate(bind_width(expected["M136"],modulus,trial))==str(int(trial==bits)),(modulus,trial)
for k in (1,2,4,8,16,32,53,128):
    assert evaluate(f'replace(({expected["M379"]}),"N",{2**k})')==str(k),k
(args.directory/"inputs.json").write_text(json.dumps([[k,f,str(m)] for k,(f,m) in cases.items()]),"utf8")
if args.verify_clipboard:
    records=json.loads((args.directory/"records.json").read_text("utf-8-sig"))
    assert [r["id"] for r in records]==list(cases)
    for r in records:
        assert r["restored_same"] and r["copy"]==r["second_copy"]==expected[r["id"]]
        session=json.loads((args.directory/(r["id"]+".qsession")).read_text("utf-8-sig"))
        assert session["Mode"]==cases[r["id"]][1]
    result=json.loads((args.directory/"result.json").read_text("utf-8-sig"))
    assert result["passed"] and result["clipboardRestored"] and not result["sessionsOnly"]
    print(json.dumps(dict(sources=[rows[i-1]["id"] for i in (136,379)],moduli=len(moduli),
                          width_checks=3*len(moduli),log_checks=8,clipboard_sessions=len(records)),indent=2))
