"""Check TeX probability percentages from IBM-028, arithmetic grouping and Copy."""
import argparse
import json
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument("worker", type=Path)
parser.add_argument("--gui-inputs", type=Path)
args = parser.parse_args()
rows = json.loads(Path(__file__).with_name("ibm028-inventory.json").read_bytes())["rows"]


def evaluate(expression):
    p = subprocess.run([args.worker.resolve(), "--json"], input=("quantum:" + expression).encode(),
                       capture_output=True, timeout=30)
    assert p.returncode == 0, (expression, p.stderr.decode())
    return json.loads(p.stdout)["copy_text"]


controls = [
    ("probability", r"40\%", "2/5"),
    ("quarter", r"25\%", "1/4"),
    ("sum", r"40\% + 25\%", "13/20"),
    ("negative", r"-25\%", "-1/4"),
    ("denominator", r"1 / 25\%", "4"),
    ("whole-power", r"2^{3}\%", "2/25"),
    ("percent-power", r"50\%^{2}", "1/4"),
    ("in-exponent", r"16^{50\%}", "4"),
    ("symbolic", r"replace((x\%),x,25)", "1/4"),
    ("modulo", "40 % 7", "5"),
]
inputs = [[r["id"], r["literal"], "0"] for r in rows]
matches = [r for r in rows if r["literal"] in (r"$40\%$", r"$25\%$")]
assert len(matches) == 7
for r in matches:
    expected = "2/5" if "40" in r["literal"] else "1/4"
    assert evaluate(r["literal"]) == evaluate(expected)
for name, expression, expected in controls:
    copy = evaluate(expression)
    assert copy == evaluate(expected) and evaluate(copy) == copy, (expression, expected, copy)
    inputs.append([name, expression, "0"])
assert evaluate(r"sets:S\%^{1}") == evaluate("S/100")
if args.gui_inputs:
    args.gui_inputs.write_text(json.dumps(inputs, ensure_ascii=False), encoding="utf8")
print("Verified seven lesson percentages and ten arithmetic controls.")
