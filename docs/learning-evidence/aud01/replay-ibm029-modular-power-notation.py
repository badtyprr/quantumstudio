"""Replay IBM-029's modular exponentiation expressions with the lesson's arithmetic selected."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("worker", type=Path)
parser.add_argument("directory", type=Path)
parser.add_argument("--verify-windows", action="store_true")
parser.add_argument("--clipboard", type=Path, help="separate replay using the actual Windows Copy button")
args = parser.parse_args()
worker = args.worker.resolve()
env = dict(os.environ, QALCULATE_DEFINITIONS_DIR=str(worker.parent / "data"))
def evaluate(expr, mode):
    p = subprocess.run([worker, "--json"], input=("quantum:" + ("modpowers:" if mode else "") + expr).encode(),
                       capture_output=True, check=True, env=env, timeout=30)
    return json.loads(p.stdout)["copy_text"]

rows = json.loads(Path(__file__).with_name("ibm029-inventory.json").read_bytes())["rows"]
cases = {}
gui = {}
for i in (176, 178):
    row = rows[i-1]
    assert row["id"].endswith(f"M{i}")
    copy = evaluate(row["literal"], True)
    assert copy == evaluate(copy, False) == evaluate(copy, True)
    gui[f"M{i}"] = (row["literal"], True, copy)
    for n in (6,21,35):
        for a in (-3,0,2,5,8):
            for k in (-1,0,2,7,1000000000):
                if k < 0 and math.gcd(a,n) != 1:
                    continue
                value = pow(a,k,n)
                bound = f'replace(replace(replace(({copy}),"a",{a}),"k",{k}),"N",{n})'
                if i == 178:
                    cases[bound] = "1"
                else:
                    for b in (value, value+n):
                        cases[f'replace(({bound}),"b",{b})'] = str(int(b == value and math.gcd(value,n)==1))

for key, expr, mode, expected in (
    ("reduced",r"$4=5^2\in\mathbb{Z}_{21}^{\ast}$",True,"1"),
    ("unreduced",r"$25=5^2\in\mathbb{Z}_{21}^{\ast}$",True,"0"),
    ("ring",r"$3^2\in\mathbb{Z}_{21}$",True,"1"),
    ("nonunit",r"$3^2\in\mathbb{Z}_{21}^{\ast}$",True,"0"),
    ("ordinary",r"$5^2\in\mathbb{Z}_{21}$",False,"0"),
    ("compound",r"$4=(2+3)^{1+1}\in\mathbb{Z}_{7*3}$",True,"1"),
    ("shared-unit",r"$5^2,5^4\in\mathbb{Z}_{21}^{\ast}$",True,"1"),
    ("shared-nonunit",r"$5^2,3^4\in\mathbb{Z}_{21}^{\ast}$",True,"0"),
    ("inverse",r"$17=5^{-1}\in\mathbb{Z}_{21}$",True,"1")):
    gui[key] = (expr,mode,expected)
    assert evaluate(expr,mode)==expected, key
def check(item):
    expr, expected = item
    assert evaluate(expr,False) == expected, expr
with ThreadPoolExecutor(max_workers=4) as pool:
    list(pool.map(check,cases.items()))
inputs = [[key,expr,"7" if mode else "0"] for key,(expr,mode,_) in gui.items()]
(args.directory / "inputs.json").write_text(json.dumps(inputs), encoding="utf8")
if args.verify_windows:
    records = json.loads((args.directory / "records.json").read_text("utf-8-sig"))
    assert [r["id"] for r in records] == list(gui)
    for record in records:
        key = record["id"]
        assert record["restored_same"] and record["copy_text"]==record["reentry_text"]==gui[key][2]
        session = json.loads((args.directory / (key+".qsession")).read_text("utf-8-sig"))
        assert session["Mode"] == (7 if gui[key][1] else 0)
    if args.clipboard:
        clip = json.loads((args.clipboard / "records.json").read_text("utf-8-sig"))
        summary = json.loads((args.clipboard / "result.json").read_text("utf-8-sig"))
        assert summary["passed"] and summary["clipboardRestored"] and not summary["sessionsOnly"]
        assert [r["id"] for r in clip] == list(gui)
        for r in clip:
            assert r["restored_same"] and r["copy"] == r["second_copy"] == gui[r["id"]][2]
    print(json.dumps(dict(source_ids=[rows[i-1]["id"] for i in (176,178)],
                          worker_sha256=hashlib.sha256(worker.read_bytes()).hexdigest(),
                          finite_cases=len(cases),windows_sessions=len(gui),
                          windows_clipboard_cases=len(clip) if args.clipboard else 0), indent=2))
