"""Replay Simon lesson formulas with an explicit three-bit domain."""
import json
from pathlib import Path
import subprocess
import sys

directory = Path(__file__).resolve().parent
with (directory / "ibm021-literal-results.json").open(encoding="utf-8") as source:
    formulas = {row["id"]: row["literal"] for row in json.load(source)["results"]}


def bound_body(number):
    literal = formulas[f"IBM021-c0-M{number:03}"]
    return literal.strip("$").strip().rstrip(".").replace(r"\Sigma^n", " bitstrings(3)")


def evaluate(expression):
    process = subprocess.run([sys.argv[1], "--json"], input=("quantum:" + expression).encode(),
                             capture_output=True, check=True, timeout=30)
    result = json.loads(process.stdout)
    assert not result["approximate"]
    return result


for number, variable in [(6, "s"), (51, "y"), (71, "x"), (96, "y"), (101, "y")]:
    for value in range(8):
        expr = f"replace(({bound_body(number)}),{variable},bitstring({value},3))"
        assert evaluate(expr)["copy_text"] == "1", (number, value)
    expr = f"replace(({bound_body(number)}),{variable},bitstring(0,4))"
    assert evaluate(expr)["copy_text"] == "0", number

initial = f"sqrt(8)*replace(replace(({bound_body(45)}),m,5),n,3)"
state = evaluate(initial)
assert (state["rows"], state["columns"]) == (256, 1)
amplitudes = ",".join(["1"] * 8 + ["0"] * 248)
assert state["copy_text"] == f"matrix(256,1,[{amplitudes}])"
print("45 membership checks and all 256 scaled initial-state amplitudes passed")

with (directory / "ibm021-oracle-table.json").open(encoding="utf-8") as source:
    table = json.load(source)
outputs = [int(bits, 2) for bits in table["outputs"]]
for number, scale in [(49, "sqrt(8)"), (50, "8")]:
    expr = f"{scale}*replace(replace(({bound_body(number)}),f,{table['graph']}),n,3)"
    state = evaluate(expr)
    expected = [0] * 256
    for x, z in enumerate(outputs):
        if number == 49:
            expected[8*z + x] = 1
        else:
            for y in range(8):
                expected[8*z + y] += (-1) ** ((x & y).bit_count() % 2)
    amplitudes = ",".join(map(str, expected))
    assert (state["rows"], state["columns"]) == (256, 1)
    assert state["copy_text"].replace("\u2212", "-") == f"matrix(256,1,[{amplitudes}])", number
print("Both bound oracle states passed all 256 amplitude checks")

# Compare the source definitions in M056 and M060 with the native operators.
def definition(number):
    return bound_body(number).split(" = ", 1)[1].strip()


image = definition(56)
fiber = definition(60)
values = list(dict.fromkeys(outputs))


def bit_set(values, width):
    entries = ",".join(f"qbitlabel({value},{width})" for value in values)
    return f"qset(vector({entries}))"


assert evaluate(f"replace(({image}),f,{table['graph']})")["copy_text"] == bit_set(values, 5)
native_range = bound_body(100)
assert evaluate(f"replace(({native_range}),f,{table['graph']})")["copy_text"] == bit_set(values, 5)
membership = bound_body(57)
for z in range(32):
    probe = f"replace(replace(({membership}),f,{table['graph']}),z,bitstring({z},5))"
    assert evaluate(probe)["copy_text"] == str(int(z in values))
    expr = f"replace(replace(({fiber}),f,{table['graph']}),z,bitstring({z},5))"
    expected_fiber = bit_set([x for x in range(8) if outputs[x] == z], 3)
    assert evaluate(expr)["copy_text"] == expected_fiber
    direct = f"replace(replace(({bound_body(59)}),f,{table['graph']}),z,bitstring({z},5))"
    assert evaluate(direct)["copy_text"] == expected_fiber
    identity = f"replace(replace(({bound_body(60)}),f,{table['graph']}),z,bitstring({z},5))"
    assert evaluate(identity)["copy_text"] == "1"

probability = definition(74)
for y in range(8):
    expr = f"replace(replace(replace(({probability}),f,{table['graph']}),n,3),y,bitstring({y},3))"
    quarter_units = evaluate(f"4*({expr})")["copy_text"]
    assert quarter_units == str(int((y & 3).bit_count() % 2 == 0)), (y, quarter_units)
    identity = f"replace(replace(({definition(102)}),f,{table['graph']}),n,3)"
    identity = f"replace(replace({identity},s,bitstring(3,3)),y,bitstring({y},3))"
    assert evaluate(identity)["copy_text"] == "1"
print("Exact range, 32 inverse images and all 8 measurement probabilities passed")
