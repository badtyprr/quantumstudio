"""Evaluate representative assignments for the 59 IBM-018 formula occurrences."""
from functools import cache
import json
import os
import subprocess
from pathlib import Path
import argparse
import sys
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("notebook", type=Path)
parser.add_argument("worker", type=Path)
args = parser.parse_args()
worker = args.worker.resolve()
env = os.environ.copy()
if (worker.parent / "data").is_dir():
    env.setdefault("QALCULATE_DEFINITIONS_DIR", str(worker.parent / "data"))
with tempfile.TemporaryDirectory() as scratch:
    report = Path(scratch) / "inventory.json"
    replay = Path(__file__).with_name("replay-phase-estimation-inventory.py")
    subprocess.run([sys.executable, replay, args.notebook, worker, report, "semantic-replay",
                    "--lesson", "IBM018"], check=True, env=env)
    inventory = json.loads(report.read_bytes())

@cache
def calculate(expression):
    result = subprocess.run([worker, "--json"], input=("quantum:" + expression).encode(),
                            capture_output=True, check=True, env=env, timeout=60)
    value = json.loads(result.stdout)
    if value["approximate"]:
        raise ValueError(f"Expected an exact result for {expression}")
    return value["copy_text"]


def word(value, width):
    return f"qbitlabel({value},{width})"


def graph(outputs, width):
    pairs = []
    for x, output in enumerate(outputs):
        label = word(output, width) if width else output
        pairs.append(f"qtuple(vector({word(x, 2)},{label}))")
    return "qset(vector(" + ",".join(pairs) + "))"


sigma = "\u03a3"
alpha = "qset(vector(0,1))"
values = [1, 4, 0, 1]
boolean = graph([0, 1, 0, 0], 0)
words = graph(values, 3)
onebit = "qset(vector(qtuple(vector(0,1)),qtuple(vector(1,0))))"
common = {"x": word(1, 2), "z": word(1, 2), "y": word(4, 3), "n": "2", "m": "3",
          "f": words, sigma: alpha, '"U_f"': "oracle([1,4,0,1],3)"}
cases = {}


def case(number, symbols, expected, **overrides):
    assignments = common | overrides
    cases[number] = ([(symbol, assignments[symbol]) for symbol in symbols], expected)


# The numbers identify the first occurrence of each distinct source literal.
case(1, [sigma], '1')
case(2, ['f', sigma, 'n', 'm'], '1')
case(3, ['n'], '2')
case(4, ['m'], '3')
case(5, ['f'], words)
case(7, ['x', sigma, 'n'], '1')
case(8, ['f', 'x', sigma, 'm'], '1')
case(9, ['f', sigma, 'n'], '1', f=boolean)
case(10, ['m'], '1', m='1')
case(11, [], '1')
case(12, ['x', sigma, 'n'], '1')
case(13, ['f', 'x'], '1', f=boolean)
case(14, [], '0')
case(16, ['n'], '4')
case(21,['f',sigma,'n'],f'qset(vector({word(1,2)}))',f=boolean)
case(25, ['f', sigma, 'n', 'm'], '1')
case(28, ['f', 'y', sigma, 'n'], '1')
case(29,[sigma,'m'],'qset(vector('+','.join(word(x,3) for x in range(8))+'))')
case(34, ['z', sigma, 'n'], '1')
case(35, ['f', 'z'], '1', f=boolean)
case(36, ['f', 'x'], '1', f=boolean, x=word(0, 2))
case(37, ['x', 'z'], '1', x=word(0, 2))
case(38, ['z'], word(1, 2))
case(41, ['f', sigma], '1', f=onebit)
case(47, ['y', sigma, 'm'], '1')
case(48, ['f', 'x', 'y'], word(5, 3), y=word(1, 3))
case(50, [], '1')
# Bind the operator label to a two-register reversible oracle. Compute
# its permutation independently from the illustrated XOR action.
permutation = [0] * 1024
for column in range(32):
    x, y = divmod(column, 8)
    permutation[(8 * x + (y ^ values[x])) * 32 + column] = 1
oracle_matrix = "matrix(32,32,[" + ",".join(map(str, permutation)) + "])"
case(51, ['"U_f"'], oracle_matrix)
case(53, ['x'], word(1, 2))
case(54, ['f', 'x'], word(4, 3))
case(55, ['y'], word(4, 3))
checked = set()
for row in inventory["rows"]:
    literal = row["literal"]
    if literal in checked:
        continue
    number = int(row["id"].split("-M")[-1])
    bindings, expected = cases[number]
    value = calculate(literal)
    for symbol, replacement in bindings:
        value = calculate(f"replace(({value}),{symbol},{replacement})")
    if value != expected:
        raise ValueError((row["id"], literal, value, expected))
    checked.add(literal)

if len(inventory["rows"]) != 59 or len(checked) != len(cases):
    raise ValueError("The pinned lesson inventory changed")
print("Verified all 59 occurrences with 31 distinct source formulas and concrete assignments.")
