"""Exercise the no-cloning argument using a controlled NOT and an independent identity."""
import argparse
import json
import os
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument("worker", type=Path)
worker = parser.parse_args().worker.resolve()
env = dict(os.environ, QALCULATE_DEFINITIONS_DIR=str(worker.parent / "data"))

def evaluate(source):
    run = subprocess.run([worker, "--json"], input=("quantum:" + source).encode(),
                         env=env, check=True, capture_output=True, timeout=30)
    value = json.loads(run.stdout)
    assert not value["approximate"]
    return value["copy_text"]

def check(index, substitutions, expected):
    row = rows[index - 1]
    equation = evaluate(row["literal"])
    assert equation == row["copy"], row["id"]
    for name, value in substitutions:
        equation = f"replace(({equation}),{name},{value})"
    assert evaluate(equation) == expected, (row["id"], substitutions)

rows = json.loads(Path(__file__).with_name("ibm047-inventory.json").read_bytes())["rows"]
blank = ('qnamedket("φ")', "|0>")
for index in (42, 62, 67, 72):
    for state, truth in [("|0>", "1"), ("|1>", "1"), ("|+>", "0")]:
        check(index, [('"U"', "CNOT"), ('qnamedket("ψ")', state), blank], truth)

basis = [('qketstate("a")', "|0>"), ('qketstate("b")', "|1>"), blank]
for index in (65, 66):
    for gate, truth in [("CNOT", "1"), ("identity(4)", "0")]:
        check(index, [('"U"', gate), *basis], truth)

# The hypothetical cloning equation contradicts the linear action on the sum.
check(69, [('"U"', "CNOT"), *basis], "0")
mapping = evaluate(rows[52]["literal"])
assert mapping == rows[52]["copy"]
for state, truth in [("|0>", "1"), ("|1>", "1"), ("|+>", "0")]:
    bound = f'replace(replace(({mapping}),qnamedket("ψ"),{state}),qnamedket("φ"),|0>)'
    assert evaluate(f"checkaction(CNOT,{bound})") == truth
print("Verified eight source formulas with 20 no-cloning checks")

# The distinguishability proof leaves the workspace width unspecified.
workspace = evaluate(rows[97]["literal"])
for width in (1, 2, 3):
    zeros = "|" + "0" * width + ">"
    ones = "|" + "1" * width + ">"
    assert evaluate(f'replace(({workspace}),"register width",{width})') == evaluate(zeros)
    assert evaluate(f'replace(|1...1>,"register width",{width})') == evaluate(ones)
    for index in (100, 109, 111, 114, 116):
        for output_bit, truth in [(0, "1"), (1, "0")]:
            bindings = [('"register width"', str(width)), ('"U"', f"identity({2**(width+1)})"),
                        ('qnamedket("ψ")', f"|{output_bit}>"), ('qnamedket("φ")', f"|{1-output_bit}>"),
                        ('qnamedket("γ_0")', zeros), ('qnamedket("δ_1")', zeros),
                        ('qnamedket("γ_1")', f"0*{zeros}")]
            check(index, bindings, truth)
print("Verified the repeated-bit register and five distinguishability equations at three widths")

factors = list(zip(["qketstate('u')", "qketstate('v')", "qketstate('w')", "qketstate(x)"],
                   ["|0>", "|1>", "|0>", "|1>"]))
check(124, factors, "1")
swapped = rows[123]["literal"].replace(r"w \otimes x", r"x \otimes w")
equation = evaluate(swapped)
for name, value in factors:
    equation = f"replace(({equation}),{name},{value})"
assert evaluate(equation) == "0"
for width in (1, 2):
    for other, truth in [("|1>", "1"), ("|0>", "0")]:
        check(135, [('"register width"', str(width)), ('qnamedket("ψ")', "|0>"),
                    ('qnamedket("φ")', other)], truth)
print("Verified tensor factor order and workspace overlaps for orthogonal and identical states")

phase_states = [('qketstate("a")', "|0>"), ('qnamedket("ψ")', "|+>"),
                ('qnamedket("φ")', "i*|+>")]
for phase, truth in [("i", "1"), ("-i", "1"), ("2", "0")]:
    bindings = [*phase_states, ('"α"', phase)]
    check(18, bindings, truth)
    check(18, list(reversed(bindings)), truth)
print("Verified global-phase invariance with imaginary phases and a non-unit magnitude control")

measurement = evaluate(rows[141]["literal"])
assert measurement == rows[141]["copy"]
for state, control, orthogonal in [("|0>", "|+>", "|1>"), ("[0;0;1]", "[1;0;0]", "[0;1;0]")]:
    bound = f'replace(({measurement}),qnamedket("φ"),{state})'
    assert evaluate(f"cardinality({bound})") == "2"
    assert evaluate(f"(({state})*dagger({state})) ∈ ({bound})") == "1"
    assert evaluate(f"(({control})*dagger({control})) ∈ ({bound})") == "0"
    check(144, [('qnamedket("φ")', state)], "vector(1,1)")
    check(144, [('qnamedket("φ")', f"2*({state})")], "vector(0,0)")
    for psi, truth in [(orthogonal, "vector(1,1)"), (state, "vector(0,0)")]:
        check(146, [('qnamedket("φ")', state), ('qnamedket("ψ")', psi)], truth)
print("Verified the projector set and both measurement derivations in two and three dimensions")
