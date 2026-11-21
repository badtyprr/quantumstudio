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
        assert evaluate(copied) == 'qset(vector(qoutcome("heads"),qoutcome("tails")))'
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
composition = evaluate("quantum:" + inventory["rows"][147]["literal"])
assert evaluate("quantum:" + composition) == composition
reset = "matrix(2,2,[1,1,0,0])"
flip = "matrix(2,2,[0,1,1,0])"
for first, second, expected in [(reset,flip,"matrix(2,2,[0,0,1,1])"), (flip,reset,reset)]:
    assigned = f'replace(replace({composition},"M_1",{first}),"M_2",{second})'
    assert evaluate(f"quantum:replace({assigned},n,2)") == expected
    assert evaluate(f"quantum:replace({assigned},n,1)") == first
print("Verified ordered matrix composition, reversed order and single-map bounds")

# M021 defines the classical system's four possible outcomes. Keep each
# complete printed word distinct from the product of its component letters.
outcome_definition = inventory["rows"][20]
assert outcome_definition["id"].endswith("M021")
definition = evaluate("quantum:" + outcome_definition["literal"])
domain_source = outcome_definition["literal"].strip("$").split("=")[1]
domain = evaluate("quantum:$" + domain_source + "$")
assert domain == 'qset(vector(qoutcome("high"),qoutcome("medium"),qoutcome("low"),qoutcome("off")))' and domain in definition
assert evaluate(domain) == domain
for name in ("high", "medium", "low", "off"):
    assert evaluate(fr"quantum:$\mathrm{{{name}}}\in {domain_source}$") == "1"
assert evaluate(fr"quantum:$\mathrm{{other}}\in {domain_source}$") == "0"
assert evaluate(f'quantum:cardinality({domain})') == "4"
print("Verified all four named outcomes from M021, including Copy re-entry")
