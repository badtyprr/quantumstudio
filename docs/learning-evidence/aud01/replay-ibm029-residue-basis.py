"""Verify each matrix column for the printed multiplication operator on Z_N."""
import argparse
import json
import math
import os
from pathlib import Path
import subprocess

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument("worker",type=Path)
parser.add_argument("directory",type=Path)
parser.add_argument("--verify-clipboard",action="store_true")
args=parser.parse_args()
worker=args.worker.resolve()
env=dict(os.environ,QALCULATE_DEFINITIONS_DIR=str(worker.parent/"data"))
def evaluate(s,success=True):
    p=subprocess.run([worker,"--json"],input=("quantum:"+s).encode(),env=env,capture_output=True,timeout=30)
    assert (p.returncode==0)==success,(s[:100],p.stderr)
    return json.loads(p.stdout)["copy_text"] if success else p.stderr.decode()

rows=json.loads(Path(__file__).with_name("ibm029-inventory.json").read_bytes())["rows"]
source=rows[60]
assert source["id"].endswith("M061")
original=source["literal"]
copied=evaluate(original)
assert evaluate(copied)==copied
cases={"M061":(original,copied)}
matrices=entries=0
for n in (*range(2,17),21,64):
    for a in range(1,n):
        if math.gcd(a,n)!=1: continue
        expr=f'replace(replace(({copied}),"a",{a}),"N",{n})'
        values=",".join(str(int(y==a*x%n)) for y in range(n) for x in range(n))
        expected=f"matrix({n},{n},[{values}])"
        actual=evaluate(expr)
        # Large identity matrices have a compact exact tensor-product Copy.
        assert actual==expected or actual==evaluate(expected),(a,n)
        matrices+=1; entries+=n*n
        if (a,n) in ((2,3),(2,15),(5,21),(63,64)):
            cases[f"{a}-mod-{n}"]=(expr,expected)
        if (a,n)==(2,15):
            assert evaluate(rows[67]["literal"])==expected
for a,n in ((3,15),(0,5),(5,5),(2,65),(1,"3/2")):
    evaluate(f'qresiduemultiplier({a},{n})',False)
evaluate(original.replace(r"\vert ax",r"\vert bx"),False)
(args.directory/"inputs.json").write_text(json.dumps([[k,x,"0"] for k,(x,_) in cases.items()]),"utf8")
if args.verify_clipboard:
    records=json.loads((args.directory/"records.json").read_text("utf-8-sig"))
    assert [r["id"] for r in records]==list(cases)
    assert all(r["restored_same"] and r["copy"]==r["second_copy"]==cases[r["id"]][1] for r in records)
    summary=json.loads((args.directory/"result.json").read_text("utf-8-sig"))
    assert summary["passed"] and summary["clipboardRestored"] and not summary["sessionsOnly"]
    print(json.dumps(dict(source=source["id"],finite_matrices=matrices,matrix_entries=entries,
                          largest_dimension=64,clipboard_sessions=len(cases)),indent=2))
