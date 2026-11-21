"""Check Shor lesson Clipboard batches against their source, worker output, and stored sessions."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from fractions import Fraction
import hashlib
import json
import os
from pathlib import Path
import subprocess

if not __debug__:
    raise SystemExit("Run this evidence verifier without Python optimization.")

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("worker", type=Path)
parser.add_argument("directory", type=Path)
parser.add_argument("report", type=Path)
parser.add_argument("--prepare", action="store_true")
parser.add_argument("--profile",choices=("original","current","orbit"),default="original")
args = parser.parse_args()
worker = args.worker.resolve()
env = dict(os.environ,QALCULATE_DEFINITIONS_DIR=str(worker.parent/"data"))
inventory = json.loads(Path(__file__).with_name("ibm029-inventory.json").read_bytes())
row_ids = [row["id"] for row in inventory["rows"]]
assert len(row_ids) == len(set(row_ids)) == 438
if args.profile == "original":
    historical = json.loads(Path(__file__).with_name("ibm029-clipboard-corpus.json").read_bytes())
    rejected = set(historical["diagnostics"])
else:
    remaining = {51,52,152,157,162}
    if args.profile=="current": remaining.update((92,98,107))
    rejected = {key for key in row_ids if int(key[-3:]) in remaining}
assert len(rejected)=={"original":16,"current":8,"orbit":5}[args.profile] and rejected <= set(row_ids)
required = set(row_ids) - rejected

def check_expected(expected):
    assert set(expected)==required, (sorted(required-set(expected)),sorted(set(expected)-required))

def notation(key):
    span = int(key[-3:])
    if args.profile == "orbit" and span in (92,98,107):return "7"
    if args.profile != "original":
        if span in (136,379):return "8"
        if span == 45:return "7"
    if span in (176,178):return "7"
    if span in (362,363,369,374,425):return "6"
    return "0"

def evaluate(expr, mode="0"):
    prefix = {"0":"", "6":"scalars:", "7":"modpowers:", "8":"binarylogs:"}[mode]
    p = subprocess.run([worker,"--json"],input=("quantum:"+prefix+expr).encode(),env=env,
                       capture_output=True,timeout=30)
    if p.returncode:
        assert p.returncode == 2 and p.stderr, p.stderr
        return None
    return json.loads(p.stdout)["copy_text"]

if args.prepare:
    rows = inventory["rows"]
    with ThreadPoolExecutor(6) as pool:
        values = list(pool.map(lambda row:evaluate(row["literal"],notation(row["id"])),rows))
    expected = {row["id"]:value for row,value in zip(rows,values) if value is not None}
    check_expected(expected)
    args.directory.mkdir(parents=True,exist_ok=True)
    (args.directory/"expected.json").write_text(json.dumps(expected),"utf8")
    inputs = [[row["id"],row["literal"],notation(row["id"])] for row in rows if row["id"] in expected]
    for i in range(0,len(inputs),20):
        batch = args.directory/f"{i:03d}"
        batch.mkdir(exist_ok=True)
        (batch/"inputs.json").write_text(json.dumps(inputs[i:i+20]),"utf8")
    print(f"Prepared {len(inputs)} original expressions in {(len(inputs)+19)//20} batches.")
    raise SystemExit

expected = json.loads((args.directory/"expected.json").read_bytes())
check_expected(expected)
sessions = {}
modes = Counter()
for result in sorted(args.directory.glob("*/result.json")):
    d = result.parent
    summary = json.loads(result.read_text("utf-8-sig"))
    records = json.loads((d/"records.json").read_text("utf-8-sig"))
    inputs = json.loads((d/"inputs.json").read_bytes())
    assert summary["passed"] and summary["clipboardRestored"] and not summary["sessionsOnly"]
    assert len(records) == summary["calls"] == len(inputs)
    for (key,expr,mode),record in zip(inputs,records):
        assert key == record["id"] and key not in sessions
        session = json.loads((d/(key+".qsession")).read_text("utf-8-sig"))
        assert session["Expression"] == expr and session["Mode"] == int(mode)
        assert record["restored_same"] and record["copy"] == record["second_copy"] == expected[key], key
        sessions[key] = (expr,mode)
        modes[mode] += 1
assert sessions.keys() == expected.keys()
diagnostics = []
for row in inventory["rows"]:
    key = row["id"]
    mode = notation(key)
    value = evaluate(row["literal"],mode)
    if key in sessions:
        assert sessions[key] == (row["literal"],mode) and value == expected[key], key
    else:
        assert value is None, key
        diagnostics.append(key)
row = inventory["rows"][233]
assert row["id"].endswith("M234")
copy = expected[row["id"]]
finite = 0
for m in (1,2,3,6):
    for r in (1,2,3,5):
        for y in range(2**m//r-2,2**m//r+3):
            bound = f'replace(replace(replace(({copy}),"r",{r}),"m",{m}),y,{y})'
            truth = abs(Fraction(y,2**m)-Fraction(1,r)) < Fraction(1,2*r*(r+1))
            assert evaluate(bound) == str(int(truth)), (m,r,y)
            finite += 1
report = dict(profile=args.profile,source_sha256=inventory["source_sha256"],worker_sha256=hashlib.sha256(worker.read_bytes()).hexdigest(),
              source_spans=len(inventory["rows"]),clipboard_sessions=len(sessions),stable_copies=len(sessions),
              mode_counts=dict(modes),diagnostics=diagnostics,M234_exact_rational_checks=finite)
args.report.write_text(json.dumps(report,indent=2)+"\n",encoding="utf8")
