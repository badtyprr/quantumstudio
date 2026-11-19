"""Replay Simon lesson formulas with an explicit three-bit domain."""
import json
from pathlib import Path
import subprocess
import sys

directory = Path(__file__).resolve().parent
with (directory / "ibm021-literal-results.json").open(encoding="utf-8") as source:
    formulas = {row["id"]: row["literal"] for row in json.load(source)["results"]}


def source_body(number):
    literal = formulas[f"IBM021-c0-M{number:03}"]
    return literal.strip("$").strip().rstrip(".")


def evaluate(expression, bind_alphabet=True):
    if bind_alphabet and r"\Sigma" in expression:
        expression = rf"replace(({expression}),\Sigma,\{{0,1\}})"
    process = subprocess.run([sys.argv[1], "--json"], input=("quantum:" + expression).encode(),
                             capture_output=True, check=True, timeout=30)
    result = json.loads(process.stdout)
    assert not result["approximate"]
    return result


def width_three(expression):
    return f"replace(({expression}),n,3)"


for number, variable in [(6, "s"), (51, "y"), (71, "x"), (96, "y"), (101, "y")]:
    domain_test = width_three(source_body(number))
    for value in range(8):
        expr = f"replace(({domain_test}),{variable},bitstring({value},3))"
        assert evaluate(expr)["copy_text"] == "1", (number, value)
    expr = f"replace(({domain_test}),{variable},bitstring(0,4))"
    assert evaluate(expr)["copy_text"] == "0", number

initial = f"sqrt(8)*replace(replace(({source_body(45)}),m,5),n,3)"
state = evaluate(initial)
assert (state["rows"], state["columns"]) == (256, 1)
amplitudes = ",".join(["1"] * 8 + ["0"] * 248)
assert state["copy_text"] == f"matrix(256,1,[{amplitudes}])"
print("45 membership checks and all 256 scaled initial-state amplitudes passed")

with (directory / "ibm021-oracle-table.json").open(encoding="utf-8") as source:
    table = json.load(source)
outputs = [int(bits, 2) for bits in table["outputs"]]
for number, scale in [(49, "sqrt(8)"), (50, "8")]:
    expr = f"{scale}*replace(replace(({source_body(number)}),f,{table['graph']}),n,3)"
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
    return source_body(number).split(" = ", 1)[1].strip()


image = width_three(definition(56))
fiber = width_three(definition(60))
values = list(dict.fromkeys(outputs))


def bit_set(values, width):
    entries = ",".join(f"qbitlabel({value},{width})" for value in values)
    return f"qset(vector({entries}))"


assert evaluate(f"replace(({image}),f,{table['graph']})")["copy_text"] == bit_set(values, 5)
native_range = source_body(100)
assert evaluate(f"replace(({native_range}),f,{table['graph']})")["copy_text"] == bit_set(values, 5)
membership = source_body(57)
for z in range(32):
    probe = f"replace(replace(({membership}),f,{table['graph']}),z,bitstring({z},5))"
    assert evaluate(probe)["copy_text"] == str(int(z in values))
    expr = f"replace(replace(({fiber}),f,{table['graph']}),z,bitstring({z},5))"
    expected_fiber = bit_set([x for x in range(8) if outputs[x] == z], 3)
    assert evaluate(expr)["copy_text"] == expected_fiber
    direct = f"replace(replace(({source_body(59)}),f,{table['graph']}),z,bitstring({z},5))"
    assert evaluate(direct)["copy_text"] == expected_fiber
    identity = f"replace(replace(({width_three(source_body(60))}),f,{table['graph']}),z,bitstring({z},5))"
    assert evaluate(identity)["copy_text"] == "1"

probability = definition(74)
for y in range(8):
    expr = f"replace(replace(replace(({probability}),f,{table['graph']}),n,3),y,bitstring({y},3))"
    quarter_units = evaluate(f"4*({expr})")["copy_text"]
    assert quarter_units == str(int((y & 3).bit_count() % 2 == 0)), (y, quarter_units)
    for number in (54, 70):
        norm = source_body(number).split("=", 1)[1]
        measured = f"replace(replace(replace(({norm}),f,{table['graph']}),n,3),y,bitstring({y},3))"
        assert evaluate(f"4*({measured})")["copy_text"] == quarter_units, (number, y)
    identity = f"replace(replace(({definition(102)}),f,{table['graph']}),n,3)"
    identity = f"replace(replace({identity},s,bitstring(3,3)),y,bitstring({y},3))"
    assert evaluate(identity)["copy_text"] == "1"
print("Exact range, 32 inverse images and all 8 measurement probabilities passed")

# The source groups each side of the Simon promise in square brackets.
left, right = [side.strip().removeprefix("[").removesuffix("]")
               for side in source_body(7).split(r"\Leftrightarrow")]
def at_pair(body, x, y):
    return f"replace(replace(({body}),x,bitstring({x},3)),y,bitstring({y},3))"


left = f"replace(({left}),f,{table['graph']})"
right = f"replace(({right}),s,bitstring(3,3))"
for x, output in enumerate(outputs):
    for y in range(8):
        lhs = evaluate(at_pair(left, x, y))["copy_text"]
        rhs = evaluate(at_pair(right, x, y))["copy_text"]
        assert lhs == rhs == str(int(output == outputs[y])), (x, y)

        # Either member of the output's inverse image may be used as w.
        chain = f"replace(replace(({source_body(88)}),f,{table['graph']}),s,bitstring(3,3))"
        chain = f"replace(replace(replace({chain},z,bitstring({output},5)),w,bitstring({x},3)),y,bitstring({y},3))"
        assert evaluate(chain)["copy_text"] == "1", (x, y)
print("Both promise predicates and the M088 equality chain passed for all 64 pairs")

# Exercise complete source expressions and their copied symbolic forms.
injective = "qset(vector(" + ",".join(
    f"tuple(bitstring({x},3),bitstring({x},5))" for x in range(8)) + "))"
for number, graph, secret in [(7, table["graph"], 3), (7, table["graph"], 4),
                              (16, table["graph"], 0), (16, injective, 0)]:
    source = source_body(number)
    copied = evaluate(source)["copy_text"]
    for body in (source, copied):
        predicate = f"replace(({body}),f,{graph})"
        if number == 7:
            predicate = f"replace({predicate},s,bitstring({secret},3))"
        for x in range(8):
            for y in range(8):
                same_output = x == y if graph == injective else outputs[x] == outputs[y]
                expected = same_output == (x == y or (x ^ secret) == y)
                assert evaluate(at_pair(predicate, x, y))["copy_text"] == str(int(expected)), (number, secret, x, y)
print("Complete M007 and M016 predicates passed for source and copied input")

# Copy an unbound formula first. Supply all lesson parameters only on re-entry.
reversed_pairs = [f"tuple(bitstring({x},3),bitstring({outputs[x]},5))" for x in reversed(range(8))]
reversed_graph = "qset(vector(" + ",".join(reversed_pairs) + "))"
for number in (49, 50, 56, 60):
    source = source_body(number)
    copy = evaluate(source, bind_alphabet=False)["copy_text"]
    for z in (range(32) if number == 60 else [None]):
        answers = []
        for body, graph in [(source, table["graph"]), (source, reversed_graph), (copy, reversed_graph)]:
            expression = f"replace(({body}),f,{graph})"
            if z is not None:
                expression = f"replace(({expression}),z,bitstring({z},5))"
            expression = rf"replace(({width_three(expression)}),\Sigma,\{{0,1\}})"
            answers.append(evaluate(expression, bind_alphabet=False)["copy_text"])
        assert answers[0] == answers[1] == answers[2], (number, z)
        if number in (56, 60):
            assert answers[0] == "1", (number, z)
print("Four unbound copies accepted the oracle in reverse row order")

# Equation (1) is zero on an empty fiber. On a two-element fiber its
# squared magnitude is four exactly when the measurement is orthogonal to s.
numbered = formulas["IBM021-c0-M075"]
contribution = evaluate(numbered)["copy_text"]
assert r"\tag{1}" in numbered
assert evaluate(numbered.replace(r"\tag{1}", ""))["copy_text"] == contribution
derivation = evaluate(formulas["IBM021-c0-M088"])["copy_text"]
def bind_output(body, z, y):
    return f"replace(replace(replace(({body}),f,{table['graph']}),z,bitstring({z},5)),y,bitstring({y},3))"


for z in range(32):
    for y in range(8):
        expected = 4 if z in values and (3 & y).bit_count() % 2 == 0 else 0
        assert evaluate(bind_output(contribution, z, y))["copy_text"] == str(expected), (z, y)
        for w in (x for x in range(8) if outputs[x] == z):
            chain = f"replace(replace(({bind_output(derivation, z, y)}),w,bitstring({w},3)),s,bitstring(3,3))"
            assert evaluate(chain)["copy_text"] == "1", (w, y)
print("Numbered equation passed 256 contributions and its copied derivation passed 64 checks")

# Bind p to both the predicted distribution and one assigning probability 1/8
# everywhere. The full source equality must distinguish them at every outcome.
probabilities = ["1/4" if (y & 3).bit_count() % 2 == 0 else "0" for y in range(8)]
for values, truth in [(probabilities, "1"), (["1/8"] * 8, "0")]:
    entries = [f"tuple(bitstring({y},3),{value})" for y, value in enumerate(values)]
    distribution = "qset(vector(" + ",".join(entries) + "))"
    for number in (54, 70):
        formula = f"replace(replace(({source_body(number)}),p,{distribution}),f,{table['graph']})"
        for y in range(8):
            expr = f"replace(({width_three(formula)}),y,bitstring({y},3))"
            assert evaluate(expr)["copy_text"] == truth, (number, y, truth)
print("Both full norm equations distinguished the predicted and uniform distributions")

for number in (54, 70):
    rhs = source_body(number).split("=", 1)[1]
    copy = evaluate(rhs, bind_alphabet=False)["copy_text"]
    for y, probability in enumerate(probabilities):
        expr = f"replace(replace(replace(({copy}),f,{table['graph']}),n,3),y,bitstring({y},3))"
        if number == 54:
            expr = rf"replace(({expr}),\Sigma,\{{0,1\}})"
        assert evaluate(f"4*({expr})", bind_alphabet=False)["copy_text"] == ("1" if probability == "1/4" else "0")
print("Both copied squared norms reproduced all eight measurement probabilities")
