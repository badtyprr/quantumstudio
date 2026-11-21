"""Check the symbolic Grover iteration update against exact integer arithmetic."""
import json
import os
from pathlib import Path
import subprocess
import sys

worker = Path(sys.argv[1]).resolve()
source = json.loads(Path(__file__).with_name("ibm034-inventory.json").read_bytes())
row, = [r for r in source["rows"] if r["id"].endswith("-M137")]


def evaluate(expr):
    proc = subprocess.run([worker, "--json"], input=("quantum:"+expr).encode(),
                          capture_output=True, check=True, timeout=30,
                          env=dict(os.environ, QALCULATE_DEFINITIONS_DIR=str(worker.parent/"data")))
    value = json.loads(proc.stdout)
    assert not value["approximate"]
    return value["copy_text"]


rule = evaluate(row["literal"])
assert rule.startswith("qscalarupdate(") and evaluate(rule) == rule
inputs = [["original", row["literal"], "0"]]
expected = {"original": rule}
for current in [*range(33), 2**53-1, 2**53, 2**53+1, 10**24+3]:
    expr = f"qstepvalue({rule},{current})"
    result = str((5*current+3)//4)
    assert evaluate(expr) == result
    name = f"limit-{current}"
    inputs.append([name, expr, "0"])
    expected[name] = result
for name, expr, result in [
        ("constant", "qstepvalue(x ← 3,8)", "3"),
        ("adjacent", "qstepvalue(T ← T(T+1),3)", "12"),
        ("separate", "qstepvalue(T ← T+1,3)+qstepvalue(T ← T-1,3)", "6"),
        ("alias", r"qstepvalue(t \gets t^2,4)", "16")]:
    assert evaluate(expr) == result
    inputs.append([name, expr, "0"])
    expected[name] = result
if len(sys.argv)>2:
    target=Path(sys.argv[2])
    (target/"inputs.json").write_text(json.dumps(inputs),encoding="utf8")
    (target/"expected.json").write_text(json.dumps(expected),encoding="utf8")
print(f"Passed {len(inputs)} exact source and control checks.")
