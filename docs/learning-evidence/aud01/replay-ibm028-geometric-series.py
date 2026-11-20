"""Replay the geometric series used twice in IBM's phase-estimation lesson."""
import argparse
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument("worker", type=Path)
parser.add_argument("output", type=Path)
parser.add_argument("--gui-inputs", type=Path)
args = parser.parse_args()
worker = args.worker.resolve()
inventory = json.loads(Path(__file__).with_name("ibm028-inventory.json").read_bytes())
rows = [inventory["rows"][n - 1] for n in (201, 329)]
literal = rows[0]["literal"]
assert rows[1]["literal"] == literal


def evaluate(expression):
    result = subprocess.run([worker, "--json"], input=("quantum:" + expression).encode(),
                            capture_output=True, timeout=30)
    assert result.returncode == 0, (expression, result.stderr.decode())
    return json.loads(result.stdout)


def bind(expression, ratio, count):
    return f"replace(replace(({expression}),α,({ratio})),N,{count})"


source = evaluate(literal)
assert evaluate(source["copy_text"])["copy_text"] == source["copy_text"]
gui = [[row["id"], row["literal"], "0"] for row in rows]
cases = []
for ratio in ["0", "1", "-1", "2", "-2", "1/2", "i", "-i"]:
    for count in [1, 2, 5, 8]:
        if ratio.endswith("i"):
            cycle = ["1", "i", "-1", "-i"] if ratio == "i" else ["1", "-i", "-1", "i"]
            expected = "+".join(f"({cycle[k % 4]})" for k in range(count))
        else:
            expected = str(sum(Fraction(ratio) ** k for k in range(count)))
        assert evaluate(f"geosum({ratio},{count})=({expected})")["copy_text"] == "1"
        for form in ("display_text", "copy_text"):
            assert evaluate(bind(source[form], ratio, count))["copy_text"] == "1", (ratio, count, form)
        cases.append(dict(ratio=ratio, terms=count, expected=expected))
assert evaluate("geosum(0,0)")["copy_text"] == "0"

variants = [
    ("numerator", literal.replace(r"\alpha^N - 1", r"\alpha^N + 1"), "2", "0"),
    ("unit-ratio", literal.replace("N &", "N+1 &"), "1", "0"),
    ("numerator-other-branch", literal.replace(r"\alpha^N - 1", r"\alpha^N + 1"), "1", "1"),
    ("unit-ratio-other-branch", literal.replace("N &", "N+1 &"), "2", "1"),
]
for label, changed, ratio, expected in variants:
    assert changed != literal
    record = evaluate(changed)
    for form in ("display_text", "copy_text"):
        expression = bind(record[form], ratio, 4)
        assert evaluate(expression)["copy_text"] == expected, (label, form)
    gui.append([f"{label}-{expected}", expression, "0"])

report = dict(source=inventory["source"], ids=[row["id"] for row in rows], literal=literal,
              worker_sha256=hashlib.sha256(worker.read_bytes()).hexdigest(),
              display=source["display_text"], copy=source["copy_text"], forms=["display", "copy"],
              cases=cases, branch_controls=[dict(case=n, ratio=r, expected=v) for n, _, r, v in variants])
args.output.write_bytes((json.dumps(report, indent=2, ensure_ascii=False) + "\n").encode())
if args.gui_inputs:
    args.gui_inputs.write_bytes(json.dumps(gui, ensure_ascii=False).encode())
