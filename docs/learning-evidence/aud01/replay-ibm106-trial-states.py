"""Verify excited-state deflation with a declared, vector-parameter trial family."""
from pathlib import Path
import json
import os
import subprocess
import sys

worker = Path(sys.argv[1]).resolve()
env = dict(os.environ, QALCULATE_DEFINITIONS_DIR=str(worker.parent / "data"))
data = Path(__file__).parent


def table(values):
    return "vector(" + ",".join(f"vector(vector({index},0),{value})" for index, value in enumerate(values)) + ")"


# The ansatz prepares |0>, |1>, and (3|0>+4|1>)/5 and |+> at four parameter vectors.
parameters = [f"vector({i},0)" for i in range(4)]
rotation = "matrix(2,2,[3/5,-4/5,4/5,3/5])"
gates = table(["I", "X", rotation, "H"])
top = table(["1", "0", "3/5", "1/sqrt(2)"])
bottom = table(["0", "1", "4/5", "1/sqrt(2)"])
body = f"matrix(2,1,vector(qscalarat({top},x),qscalarat({bottom},x)))"
declaration = f"QSTATES1\n1\n8\n{len(body)}\ntrial(x){body}"


def run(expr, family=False):
    request = (declaration if family else "") + "quantum:" + expr
    command = [worker, "--json"] + (["--states"] if family else [])
    p = subprocess.run(command, input=request.encode(), capture_output=True, env=env, timeout=30)
    assert p.returncode == 0, (expr, p.stderr.decode())
    return json.loads(p.stdout)["copy_text"]


def source(lesson, index):
    raw = json.loads((data / f"ibm{lesson}-inventory.json").read_bytes())["rows"][index-1]
    expr = run(raw["literal"])
    assert run(expr) == expr, raw["id"]
    return expr


def assign(expr, current, trial, index):
    return (expr.replace("'ψ'", '"trial"').replace("'θ'", parameters[current])
            .replace(f'qindexedlabel("θ^",{index},"")', parameters[trial]))


for i, row in enumerate([67, 78, 89]):
    expr = assign(source(106, row), 0, i, str(i))
    expected = ("|0>", "|1>", f"{rotation}*|0>")[i]
    assert run(f"qcompare({expr},{expected},4)", True) == "1"

# The printed H is an observable. Changing the energy alone falsifies the source.
for i, row in [(1, 81), (2, 92)]:
    for state, energy in [(0, "1"), (1, "-1"), (2, "-7/25"), (3, "0")]:
        expr = assign(source(106, row), 0, state, str(i)).replace("'H'", "Z")
        for candidate in (energy, "2"):
            assert run(expr.replace(f'"λ_{i}"', str(candidate)), True) == str(int(candidate == energy))

overlap = source(107, 18)
circuit = source(107, 20)
identity = source(107, 21)
for left, right, probability in [(0, 0, "1"), (0, 1, "0"), (1, 2, "16/25"), (2, 2, "1"), (3, 1, "1/2")]:
    args = (left, right, "'j'")
    expr = assign(overlap, *args)
    assert run(f"qcompare({expr},{probability},4)", True) == "1"
    eq = assign(identity, *args).replace('"U_A"', gates)
    for value, expected in [(probability, "1"), ("2", "0")]:
        assert run(eq.replace('"p_0"', value), True) == expected
# The rotation differs from its adjoint and does not commute with X.
ordered = assign(circuit, 2, 1, "'j'").replace('"U_A"', gates)
for product, expected in [(f"qdag({rotation})*X", "1"), (f"{rotation}*X", "0"), (f"X*qdag({rotation})", "0")]:
    assert run(f"qcompare({ordered},{product},4)") == expected, (ordered, product, run(ordered), run(product))

for i, row in [(0, 71), (1, 83)]:
    cost = source(106, row)
    for previous, next_value, expected in [(0, 5, "1"), (1, 2, "1"), (2, 2, "0")]:
        # At current |0>, the overlap penalties with |0>, |1>, (3|0>+4|1>)/5 are 3, 0, 27/25.
        expr = assign(cost, 0, previous, str(i)).replace(f'"β_{i}"', "3")
        expr = expr.replace(f'qindexedlabel("C_",{i},"")', table(["2"]))
        expr = expr.replace(f'qindexedlabel("C_",{i+1},"")', table([str(next_value)]))
        assert run(expr, True) == expected
for invalid in ("x", "infinity", "undefined", "matrix(2,2,[1,0,0,1])"):
    expr = f"quantum:qscalarat(vector(vector(0,{invalid})),0)"
    p = subprocess.run([worker, "--json"], input=expr.encode(), capture_output=True, env=env, timeout=30)
    assert p.returncode == 2 and not p.stdout and b"finite numeric value" in p.stderr, invalid

print("Trial states, energy, overlap probabilities, gate order and deflation costs passed.")
