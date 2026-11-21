"""Check the normalized projected state in IBM-046 with both computational projectors."""
import argparse
import json
import os
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument("worker", type=Path)
worker = parser.parse_args().worker.resolve()
env = dict(os.environ, QALCULATE_DEFINITIONS_DIR=str(worker.parent / "data"))

def evaluate(expression):
    run = subprocess.run([worker, "--json"], input=("quantum:" + expression).encode(),
                         capture_output=True, check=True, timeout=30, env=env)
    value = json.loads(run.stdout)
    assert not value["approximate"]
    return value["copy_text"]

rows = json.loads(Path(__file__).with_name("ibm046-inventory.json").read_bytes())["rows"]
row = rows[135]
assert row["id"] == "IBM046-3c1262a5-M136"
expression = evaluate(row["literal"])
assert expression == row["copy"]
for projector, expected in [("[1,0;0,0]", "|0>"), ("[0,0;0,1]", "|1>")]:
    bound = f'replace(replace(({expression}),"Π_k",{projector}),qnamedket("ψ"),|+>)'
    assert evaluate(bound) == evaluate(expected)
print("Verified both normalized projections of the plus state from IBM-046 M136")

def verify_distribution(equation, bindings):
    for operand, value in bindings:
        equation = f"replace(({equation}),{operand},{value})"
    for distribution, expected in [("[1;0]", "1"), ("[0;1]", "0")]:
        bound = f'replace(({equation}),"measurement probabilities",{distribution})'
        assert evaluate(bound) == expected

projection_probability = evaluate(rows[132]["literal"])
verify_distribution(projection_probability, [('"k"', "0"), ('"Π_k"', "[1,0;0,0]"),
                                             ('qnamedket("ψ")', "|0>")])
limitations = json.loads(Path(__file__).with_name("ibm047-inventory.json").read_bytes())["rows"]
branch_probabilities = evaluate(limitations[104]["literal"])
verify_distribution(branch_probabilities, [('qnamedket("γ_0")', "|0>"),
                                            ('qnamedket("γ_1")', "[0;0]")])
print("Verified both lesson probabilities with matching and reversed distributions")

inequality = rows[47]["literal"]
for source, orthogonal in [(inequality, "1"), (inequality.replace(r"\leq", r"\geq"), "0")]:
    equation = evaluate(source)
    for phi, expected in [("|0>", "1"), ("|1>", orthogonal)]:
        bound = f'replace(replace(({equation}),qnamedket("ψ"),|0>),qnamedket("φ"),{phi})'
        assert evaluate(bound) == expected
print("Verified the Cauchy-Schwarz bound and its reversal for parallel and orthogonal states")

# Extending an m-vector orthonormal list to dimension n introduces indices m+1 through n.
for index in (76, 100):
    family = evaluate(rows[index - 1]["literal"])
    assert family == rows[index - 1]["copy"]
    for start, end in [(0, 2), (1, 4), (2, 2)]:
        names = ",".join(f'qketstate("ψ_{j}")' for j in range(start + 1, end + 1))
        expected = evaluate(f"vector({names})")
        assert evaluate(f"replace(replace(({family}),m,{start}),n,{end})") == expected
        assert evaluate(f"replace(replace(({family}),n,{end}),m,{start})") == expected
print("Verified both basis-completion ranges, including an already complete basis")

for index in (127, 167, 176, 207, 220, 238):
    family = evaluate(rows[index - 1]["literal"])
    assert family == rows[index - 1]["copy"]
    first, second = "|0><0|", "|1><1|"
    bindings = [("m", "2"), ('"Π_0"', first), ('"Π_1"', second)]
    for sequence in (bindings, list(reversed(bindings))):
        bound = family
        for name, value in sequence:
            bound = f"replace(({bound}),{name},{value})"
        if index == 220:
            assert evaluate(bound) == evaluate(f"vector({first},{second})")
            assert evaluate(bound) != evaluate(f"vector({second},{first})")
        else:
            assert evaluate(f"cardinality({bound})") == "2"
            assert evaluate(f"({second}) ∈ ({bound})") == "1"
            assert evaluate(f"(|+><+|) ∈ ({bound})") == "0"
print("Verified five projector sets and the ordered operator list in both binding orders")

completeness = evaluate(rows[127]["literal"])
assert completeness == rows[127]["copy"]
for dimension in (2, 3):
    for complete in (True, False):
        bindings = [("m", str(dimension))]
        for index in range(dimension):
            ket = f"basis({index if complete else 0},{dimension})"
            bindings.append((f'"Π_{index}"', f"{ket}*dagger({ket})"))
        for sequence in (bindings, list(reversed(bindings))):
            bound = completeness
            for name, value in sequence:
                bound = f"replace(({bound}),{name},{value})"
            assert evaluate(bound) == ("1" if complete else "0")
print("Verified projector completeness in two and three dimensions and rejected repeated projectors")
