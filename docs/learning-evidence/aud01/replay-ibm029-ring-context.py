"""Check modular unit equations against integer arithmetic and verify Windows re-entry."""
import argparse
import itertools
import json
import math
import os
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("worker", type=Path)
parser.add_argument("directory", type=Path)
parser.add_argument("--clipboard", action="store_true")
args = parser.parse_args()
if not __debug__: raise RuntimeError("Assertions must be enabled")
worker = args.worker.resolve()
env = dict(os.environ, QALCULATE_DEFINITIONS_DIR=str(worker.parent/"data"))
def run(expr, success=True):
    p = subprocess.run([worker,"--json"],input=("quantum:"+expr).encode(),capture_output=True,env=env,timeout=25)
    assert (p.returncode == 0) == success, (expr,p.stderr)
    if success: return json.loads(p.stdout)["copy_text"]

def bind(form, assignments):
    for name,value in assignments:
        form = f'replace(({form}),"{name}",{value})'
    return form

rows = json.loads(Path(__file__).with_name("ibm029-inventory.json").read_bytes())["rows"]
cases = []
expected = {}
def record(key, expression, mode, result):
    cases.append([key,expression,str(mode)])
    expected[key] = result

forms = {}
for span in (19,80,82):
    literal = rows[span-1]["literal"]
    form = run("modpowers:"+literal)
    assert run(form)==form
    forms[span] = form
    record(f"M{span:03}",literal,7,form)

congruences = inverses = invalid = 0
for n in (2,3,5,6,7,9,15,21):
    expr = bind(forms[19],[("modulus",n)])
    value = str(int(15%n == 1))
    assert run(expr)==value
    congruences+=1
    if n in (6,7): record(f"product-{n}",expr,0,value)
    for a in range(n):
        assignments = [("a",a),("modulus",n)]
        unit = math.gcd(a,n)==1
        for perm in itertools.permutations(assignments):
            expr = bind(forms[82],perm)
            if unit:
                value=str(pow(a,-1,n))
                assert run(expr)==value
                inverses+=1
                if (n,a)==(21,5) and perm[0][0]=="modulus":record("inverse-5-mod-21",expr,0,value)
            else:
                run(expr,False)
                invalid+=1
        for b in {0,1,n-1,pow(a,-1,n) if unit else a}:
            expr=bind(forms[80],[("b",b),("modulus",n),("a",a)])
            value=str(int((a*b)%n==1))
            assert run(expr)==value
            congruences+=1
            if (a,b,n)==(5,17,21):record("unit-pair",expr,0,value)
assert run(rows[18]["literal"])=="0"
record("ordinary-product",rows[18]["literal"],0,"0")
(args.directory/"inputs.json").write_text(json.dumps(cases),"utf8")
report=dict(source_spans=[19,80,82],congruences=congruences,inverses=inverses,nonunit_diagnostics=invalid)
if args.clipboard:
    records=json.loads((args.directory/"records.json").read_text("utf-8-sig"))
    assert [r["id"] for r in records]==list(expected)
    for r in records: assert r["restored_same"] and r["copy"]==r["second_copy"]==expected[r["id"]]
    result=json.loads((args.directory/"result.json").read_text("utf-8-sig"))
    assert result["passed"] and result["clipboardRestored"] and not result["sessionsOnly"]
    report["clipboard_sessions"]=len(records)
print(json.dumps(report,indent=2))
