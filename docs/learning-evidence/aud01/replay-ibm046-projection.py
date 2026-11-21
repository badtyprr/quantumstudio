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

block_equation = evaluate(rows[194]["literal"])
assert block_equation == rows[194]["copy"]
for dimension in (2, 3):
    size = dimension * dimension
    cells = [0] * (size * size)
    bindings = [("m", str(dimension))]
    for k in range(dimension):
        cells[(k * dimension + k) * size + k] = 1
        ket = f"basis({k},{dimension})"
        bindings.append((f'"Π_{k}"', f"{ket}*dagger({ket})"))
    for changed in (False, True):
        cells[-1] = int(changed)
        matrix = f"matrix({size},{size},[" + ",".join(map(str, cells)) + "])"
        terms = [('"M"', matrix), *bindings]
        for sequence in (terms, list(reversed(terms))):
            bound = block_equation
            for name, value in sequence:
                bound = f"replace(({bound}),{name},{value})"
            assert evaluate(bound) == ("0" if changed else "1")
print("Verified the block matrix layout and its zero-filled columns in dimensions two and three")

completion = evaluate(rows[218]["literal"])
assert completion == rows[218]["copy"]
placeholder = evaluate(rows[220]["literal"])
assert placeholder == "qmissingblock()" and evaluate(placeholder) == placeholder
for dimension in (2, 3):
    size = dimension ** 2
    fixed = [i * dimension + i for i in range(dimension)]
    free = [i for i in range(size) if i not in fixed]
    for remaining in (free, list(reversed(free))):
        for matches in (True, False):
            permutation = fixed + remaining
            if not matches:
                permutation[0], permutation[-1] = permutation[-1], permutation[0]
            cells = [int(permutation[col] == row) for row in range(size) for col in range(size)]
            matrix = f"matrix({size},{size},[" + ",".join(map(str, cells)) + "])"
            assert evaluate(f"dagger({matrix})*{matrix}=identity({size})") == "1"
            bound = f'replace(({completion}),"U",{matrix})'
            for k in range(dimension):
                ket = f"basis({k},{dimension})"
                bound = f'replace(({bound}),"Π_{k}",{ket}*dagger({ket}))'
            assert evaluate(f"replace(({bound}),m,{dimension})") == ("1" if matches else "0")
print("Verified two unitary completions per dimension and rejected unitary matrices with a different first block column")

gram_equation = evaluate(rows[89]["literal"])
for matrix, expected in [("[1,i,0;0,1,1;0,0,1]", "1"), ("[1,0,0;0,1,0;0,0,1]", "0")]:
    equation = f"replace(({gram_equation}),'U',{matrix})"
    for index, column in enumerate(("[1;0;0]", "[i;1;0]", "[0;1;1]"), 1):
        equation = f'replace(({equation}),qnamedket("ψ_{index}"),{column})'
    assert evaluate(equation) == expected
print("Verified the Gram matrix of three complex, nonorthogonal columns and rejected an unrelated identity matrix")

coefficient_equation = evaluate(rows[8]["literal"])
for second_amplitude, expected in [("1", "1"), ("-1", "0")]:
    equation = f"replace(({coefficient_equation}),n,2)"
    for operand, value in [('qnamedket("ψ")', "[i;1]"), ('qnamedket("φ")', "[1;0]"),
                           ('"α_1"', "i"), ('"α_2"', "1"), ('"β_1"', second_amplitude), ('"β_2"', "0")]:
        equation = f"replace(({equation}),{operand},{value})"
    assert evaluate(equation) == expected
print("Verified the conjugated coefficient expansion with complex states and rejected an inconsistent amplitude")
