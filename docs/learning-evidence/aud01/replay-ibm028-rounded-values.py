"""Check the rounded root of unity and probability bound printed in IBM-028."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument("worker", type=Path)
parser.add_argument("output", type=Path)
parser.add_argument("--gui-inputs", type=Path)
args = parser.parse_args()
worker = args.worker.resolve()
env = dict(os.environ, QALCULATE_DEFINITIONS_DIR=str(worker.parent / "data"))
inventory = json.loads(Path(__file__).with_name("ibm028-inventory.json").read_bytes())


def evaluate(expression):
    result = subprocess.run([worker, "--json"], input=("quantum:" + expression).encode(),
                            env=env, capture_output=True, timeout=30)
    assert result.returncode == 0, (expression, result.stderr.decode())
    return json.loads(result.stdout)


def check(expression, expected):
    actual = evaluate(expression)["copy_text"]
    assert actual == expected, (expression, actual, expected)


gui = []
records = []
for number in (176, 358):
    row = inventory["rows"][number - 1]
    assert row["id"].endswith(f"M{number}")
    record = evaluate(row["literal"])
    gui.append([row["id"], row["literal"], "0"])
    records.append(dict(id=row["id"], literal=row["literal"], display=record["display_text"],
                        copy=record["copy_text"]))
    check(record["copy_text"], record["copy_text"])
    if number == 176:
        display = [line.split(". ", 1)[1] for line in record["display_text"].split("\n\n")]
        start, end = r"\begin{gathered}", r"\end{gathered}"
        assert record["copy_text"].startswith(start) and record["copy_text"].endswith(end)
        copied = record["copy_text"][len(start):-len(end)].split(r"\\")
        roots = (1, 2, 3, 4, 8, 16, 100)
        assert len(display) == len(copied) == len(roots)
        for n, shown, saved in zip(roots, display, copied):
            for form in [shown, saved]:
                for sign, expected in [("", "1"), ("-", "0")]:
                    expression = f"replace(({form}),ω_{n},{sign}exp(2*pi*i/{n}))"
                    check(expression, expected)
                    if n in (16, 100) and form == shown:
                        gui.append([f"M176-{n}-{expected}", expression, "0"])
    else:
        for field in ("display_text", "copy_text"):
            for i, (value, expected) in enumerate([("4/pi^2", "1"), ("0.405", "0"),
                                                    ("0.4051", "0"), ("0.406", "1")]):
                expression = f"replace(({record[field]}),p_y,({value}))"
                check(expression, expected)
                if field == "display_text":
                    gui.append([f"M358-{i}-{expected}", expression, "0"])

for expression in ("z≈-0.40+0.060i", "z≈0.4050"):
    symbolic = evaluate(expression)
    assert "≈" in symbolic["display_text"]
    check(symbolic["display_text"], symbolic["copy_text"])
    check(symbolic["copy_text"], symbolic["copy_text"])

# Reported precision applies to each component. A trailing zero changes the test.
for expression, expected in [("4/pi^2≈0.4050", "0"), ("4/pi^2≈0.4053", "1"),
                             ("exp(2*pi*i/100)≈0.998+0.062i", "0"),
                             ("exp(2*pi*i/100)≈0.997+0.063i", "0"),
                             ("0.405+i≈0.405", "0")]:
    check(expression, expected)
report = dict(source=inventory["source"], worker_sha256=hashlib.sha256(worker.read_bytes()).hexdigest(),
              records=records, roots=roots, probability_witnesses=["4/pi^2", "0.405", "0.4051", "0.406"])
args.output.write_bytes((json.dumps(report, indent=2, ensure_ascii=False) + "\n").encode())
if args.gui_inputs:
    args.gui_inputs.write_bytes(json.dumps(gui, ensure_ascii=False).encode())
