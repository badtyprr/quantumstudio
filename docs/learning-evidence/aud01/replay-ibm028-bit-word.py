"""Replay the ordered measurement bits and their integer interpretation in IBM-028."""
import argparse
import hashlib
import itertools
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
row = inventory["rows"][102]
assert row["id"].endswith("M103")


def evaluate(text, mode="", valid=True):
    response = subprocess.run([worker, "--json"], input=("quantum:" + mode + text).encode(),
                              capture_output=True, timeout=30)
    if valid:
        assert response.returncode == 0, (text, response.stderr.decode())
        return json.loads(response.stdout)
    assert response.returncode and any(word in response.stderr.lower() for word in (b"bit", b"binary word")), (text, response.stderr)


record = evaluate(row["literal"], "bitword:")
gui = [[row["id"], row["literal"], "5"]]
checks = []
for high, low in itertools.product((0, 1), repeat=2):
    value = 2 * high + low
    expected = f"qbitlabel({value},2)"
    for expression in (record["display_text"], record["copy_text"]):
        assert evaluate(expression, "bitword:")["copy_text"] == record["copy_text"]
        bound = f"replace(replace(({expression}),a_0,{low}),a_1,{high})"
        assert evaluate(bound)["copy_text"] == expected
        assert evaluate(f"bitvalue({bound})")["copy_text"] == str(value)
    gui.append([f"M103-{high}{low}", bound, "5"])
    checks.append(dict(high=high, low=low, word=expected, integer=value))

for literal, expected in [("0", "qbitlabel(0,1)"), ("001", "qbitlabel(1,3)"),
                          ("1" + "0" * 1023, f"qbitlabel({2**1023},1024)")]:
    assert evaluate(literal, "bitword:")["copy_text"] == expected
for literal in ("2", "a_0 2", "1" * 1025):
    evaluate(literal, "bitword:", valid=False)
for literal, expected in [("a_{0} a_{1}", 1), ("a_1 a_0 a_1", 5)]:
    word = evaluate(literal, "bitword:")["copy_text"]
    assert evaluate(f"bitvalue(replace(replace(({word}),a_0,0),a_1,1))")["copy_text"] == str(expected)
evaluate(f"replace(({record['copy_text']}),a_1,2)", valid=False)
product = evaluate(row["literal"])["copy_text"]
assert evaluate(f"replace(replace(({product}),a_1,1),a_0,0)")["copy_text"] == "0"
evidence = dict(source=inventory["source"], worker_sha256=hashlib.sha256(worker.read_bytes()).hexdigest(),
                id=row["id"], source_literal=row["literal"], mode="Binary word",
                display=record["display_text"], copy=record["copy_text"], assignments=checks)
args.output.write_bytes((json.dumps(evidence, indent=2, ensure_ascii=False) + "\n").encode())
if args.gui_inputs:
    args.gui_inputs.write_bytes(json.dumps(gui, ensure_ascii=False).encode())
