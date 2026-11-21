"""Check the named-outcome examples against the lesson's two explicit basis states."""
import argparse
import json
import os
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument("worker", type=Path)
args = parser.parse_args()
worker = args.worker.resolve()
environment = dict(os.environ, QALCULATE_DEFINITIONS_DIR=str(worker.parent / "data"))

def evaluate(source):
    process = subprocess.run([worker, "--json"], input=source.encode(), capture_output=True,
                             check=True, timeout=30, env=environment)
    result = json.loads(process.stdout)
    assert not result["approximate"], source
    return result["copy_text"]

inventory = json.loads(Path(__file__).with_name("ibm037-inventory.json").read_text(encoding="utf-8"))
heads, tails = evaluate("quantum:|0>"), evaluate("quantum:|1>")
assert heads == "matrix(2,1,[1,0])" and tails == "matrix(2,1,[0,1])"
for number in range(52, 58):
    row = inventory["rows"][number - 1]
    assert row["id"].endswith(f"M{number:03}")
    copied = evaluate("quantum:" + row["literal"])
    if number in (52, 54):
        for heads_value, expected in [(heads, "1"), (tails, "0")]:
            bound = copied
            for name in ("qnamedket", "qketstate"):
                bound = bound.replace(f'{name}("heads")', heads_value)
                bound = bound.replace(f'{name}("tails")', tails)
            assert evaluate(bound) == expected, row["id"]
    elif number == 53:
        assert evaluate(copied) == 'qset(vector("heads","tails"))'
    else:
        assert evaluate(copied) == 'qketstate("tails")'
print("Verified six named-outcome examples and both negative controls")
coordinates = evaluate("quantum:" + inventory["rows"][96]["literal"])
assert coordinates == "qtuple(vector('b','a'))"
assert evaluate("quantum:(3,2)") == "qtuple(vector(3,2))"

# The fourth truth table sends both input bits to one.
chain = evaluate("quantum:" + inventory["rows"][106]["literal"])
assert chain.startswith("qequalchain(")
for zero_image, expected in [(tails, "1"), (heads, "0")]:
    bound = chain.replace('"M_4"', "matrix(2,2,[0,0,1,1])")
    bound = bound.replace('qstatecall("f_4",0)', zero_image)
    bound = bound.replace('qstatecall("f_4",1)', tails)
    assert evaluate(bound) == expected
print("Verified ordered coordinates and the constant-one map")
tables = evaluate("quantum:" + inventory["rows"][66]["literal"])
assert evaluate(tables) == tables
expected_tables = []
for number, (at_zero, at_one) in enumerate([(0,0), (0,1), (1,0), (1,1)], 1):
    expected_tables.append(f"""matrix(3,2,['a',"f_{number}(a)",0,{at_zero},1,{at_one}])""")
assert tables == "vector(" + ",".join(expected_tables) + ")"
print("Verified all eight function values and their table headings")
