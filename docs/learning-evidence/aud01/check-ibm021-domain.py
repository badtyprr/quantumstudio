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
