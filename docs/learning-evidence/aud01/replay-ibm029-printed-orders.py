"""Check the printed array of modular power equations against integer arithmetic."""
import argparse
import json
import os
import subprocess
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("worker", type=Path)
parser.add_argument("directory", type=Path)
parser.add_argument("--verify-clipboard", action="store_true")
args = parser.parse_args()
worker = args.worker.resolve()
env = dict(os.environ, QALCULATE_DEFINITIONS_DIR=str(worker.parent/"data"))
def evaluate(expr, success=True):
    p = subprocess.run([worker,"--json"],input=("quantum:"+expr).encode(),env=env,capture_output=True,timeout=30)
    assert (p.returncode == 0) == success, (expr[:160],p.stderr)
    return json.loads(p.stdout)["copy_text"] if success else p.stderr.decode()

row = json.loads(Path(__file__).with_name("ibm029-inventory.json").read_bytes())["rows"][44]
assert row["id"].endswith("M045")
orders = [(1,1),(8,2),(16,3),(2,6),(10,6),(17,6),(4,3),(11,6),(19,6),(5,6),(13,2),(20,2)]
assert all(next(i for i in range(1,22) if pow(a,i,21)==1)==r for a,r in orders)
tex = row["literal"]
copied = evaluate("modpowers:"+tex)
assert evaluate(copied) == evaluate("modpowers:"+copied) == copied
def bind(text,modulus):
    return f'replace(({text}),"modulus",{modulus})'
def matrix(values):
    return "matrix(4,3,["+",".join(map(str,values))+"])"

cases = {"M045":(tex,7,copied)}
checks = 0
for name, formula, outputs in [("printed",tex,[1]*12),("edited",tex.replace("8^{2} = 1","8^{2} = -2"),[1,-2]+[1]*10)]:
    symbolic = evaluate("modpowers:"+formula)
    for n in (1,2,3,5,7,11,13,19,21,22,29,35):
        expression = bind(symbolic,n)
        wanted = matrix([int(pow(a,r,n)==y%n) for (a,r),y in zip(orders,outputs)])
        assert evaluate(expression) == wanted
        checks += len(outputs)
        if n in (7,21):
            cases[f"{name}-{n}"] = (expression,0,wanted)
for n in (0,-1,"1/2"):
    assert "positive modulus" in evaluate(bind(copied,n),False)
repeat = r"\begin{array}{c}" + r"\\".join(["2^2=4"]*64) + r"\end{array}"
large_copy = evaluate("modpowers:"+repeat)
assert evaluate(large_copy)==large_copy
assert evaluate(bind(large_copy,7)) == "matrix(64,1,["+",".join(["1"]*64)+"])"
assert "positive modulus" in evaluate(bind(large_copy,0),False)
assert "64 editable" in evaluate("modpowers:"+repeat.replace("2^2=4",r"2^2=4\\2^2=4",1),False)
cases["64-equations"] = (repeat,7,large_copy)
evaluate(tex,False)
(args.directory/"inputs.json").write_text(json.dumps([[k,t,str(m)] for k,(t,m,_) in cases.items()]),"utf8")
if args.verify_clipboard:
    records=json.loads((args.directory/"records.json").read_text("utf-8-sig"))
    assert [r["id"] for r in records] == list(cases)
    assert all(r["restored_same"] and r["copy"]==r["second_copy"]==cases[r["id"]][2] for r in records)
    result=json.loads((args.directory/"result.json").read_text("utf-8-sig"))
    assert result["passed"] and result["clipboardRestored"] and not result["sessionsOnly"]
    print(json.dumps(dict(source=row["id"],rows=4,columns=3,finite_equations=checks,verified_orders=12,
                          context_modulus=21,clipboard_sessions=len(records)),indent=2))
