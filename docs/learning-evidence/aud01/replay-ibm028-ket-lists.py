"""Check the order and dimension of the lesson's Fourier and computational ket lists."""
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
source = json.loads(Path(__file__).with_name("ibm028-inventory.json").read_bytes())


def evaluate(text):
    r = subprocess.run([worker, "--json"], input=("quantum:" + text).encode(), env=env,
                       capture_output=True, timeout=30)
    assert r.returncode == 0, (text, r.stderr.decode())
    data = json.loads(r.stdout)
    assert not data["approximate"], data
    return data


def copy(text):
    return evaluate(text)["copy_text"]


records = []
gui = []
for number in (127, 134, 135, 179):
    row = source["rows"][number - 1]
    assert row["id"].endswith(f"M{number}")
    original = evaluate(row["literal"])
    assert original["rows"] == original["columns"] == 0
    for field in ("display_text", "copy_text"):
        assert copy(original[field]) == original["copy_text"], (number, field)
    gui.append([row["id"], row["literal"], "0"])
    expression = row["literal"].strip("$")
    if number == 179:
        assert copy(f"replace(({expression}),N,4)") == copy("basislist(4)")
    else:
        assert copy(f"qregisterelement(({expression}),1)") == copy(f"qregisterelement(({original['copy_text']}),1)")
    dimensions = [1, 2, 3, 4, 8] if number == 179 else [4]
    for dimension in dimensions:
        for field in ("display_text", "copy_text"):
            form = original[field]
            if number == 179:
                form = f"replace(({form}),N,{dimension})"
            for index in range(dimension):
                entry = f"qregisterelement(({form}),{index})"
                if number in (127, 134):
                    assert copy(entry) == f'qketstate("φ_{index}")'
                    entry = f"replace(({entry}),φ_{index},fourier(4)*basis({index},4))"
                    reference = "fourier(4)*"
                else:
                    reference = ""
                for candidate in {index, (index + 1) % dimension}:
                    expression = f"norm(({entry})-({reference}basis({candidate},{dimension})))=0"
                    expected = str(int(candidate == index))
                    assert copy(expression) == expected, (number, field, dimension, index, candidate)
                    if index == 1 and dimension == 4 and field == "display_text":
                        gui.append([f"M{number}-{expected}", expression, "0"])
    records.append(dict(id=row["id"], input=row["literal"], display=original["display_text"],
                        copy=original["copy_text"], dimensions=dimensions))

report = dict(source=source["source"], worker_sha256=hashlib.sha256(worker.read_bytes()).hexdigest(),
              records=records)
args.output.write_bytes((json.dumps(report, indent=2, ensure_ascii=False) + "\n").encode())
if args.gui_inputs:
    args.gui_inputs.write_bytes(json.dumps(gui, ensure_ascii=False).encode())
