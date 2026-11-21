"""Verify Grover's alphabet, partition and uniform-state formulas in Sets mode."""
import argparse
import json
import os
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument("worker", type=Path)
parser.add_argument("--gui-inputs", type=Path)
args = parser.parse_args()
worker = args.worker.resolve()
env = dict(os.environ, QALCULATE_DEFINITIONS_DIR=str(worker.parent / "data"))
inventory = json.loads(Path(__file__).with_name("ibm033-inventory.json").read_bytes())


def evaluate(expr):
    result = subprocess.run([worker, "--json"], input=("quantum:" + expr).encode(),
                            env=env, capture_output=True, check=True, timeout=30)
    return json.loads(result.stdout)["copy_text"]


def bind(formula, bindings):
    names = ",".join(bindings)
    values = ",".join(bindings.values())
    return evaluate(f"replace(({formula}),vector({names}),vector({values}))")


def finite(entries):
    return f'qset(vector({",".join(entries)}))'


forms = {}
inputs = []
for row in inventory["rows"]:
    literal = row["literal"]
    if r"\Sigma" not in literal and literal != "$S$":
        continue
    copy = evaluate("sets:" + literal)
    assert evaluate(copy) == copy
    number = int(row["id"][-3:])
    forms[number] = copy
    inputs.append([row["id"], literal, "2"])
assert set(forms) == {2, 6, 7, 13, 15, 18, 38, 52}
assert forms[13] == forms[15] == evaluate('"S"')
assert evaluate("$S$") == evaluate("matrix(2,2,[1,0,0,i])")

for width in range(4):
    size = 2**width
    words = [f"qbitlabel({i},{width})" for i in range(size)]
    common = {'"Σ"': finite(["0", "1"]), "n": str(width)}
    assert bind(forms[7], common) == evaluate(finite(words))
    for number in (38, 52):
        for word, expected in ((words[-1], "1"), (f"qbitlabel(0,{width+1})", "0")):
            assert bind(forms[number], dict(common, x=word)) == expected
    if width == 0:
        continue
    groups = [finite(words[offset::2]) for offset in (0, 1)]
    assignments = dict(common)
    assignments.update({'"A_0"': groups[0], '"A_1"': groups[1],
                        '"f"': finite([f"qtuple(vector({w},{j%2}))" for j, w in enumerate(words)])})
    # The first display defines two disjoint sets by parity of the word.
    equations = forms[2].removeprefix(r"\begin{gathered}").removesuffix(r"\end{gathered}").split(r"\\")
    assert len(equations) == 2
    for key, formula in zip(('"A_0"', '"A_1"'), equations):
        assert bind(formula, assignments) == "1"
        assert bind(formula, {**assignments, key: finite([])}) == "0"
    assert bind(forms[6], assignments) == "1"
    assert bind(forms[6], {**assignments, '"A_0"': groups[1]}) == "0"
    amplitudes = ",".join([f"1/sqrt({size})"] * size)
    uniform = f"matrix({size},1,vector({amplitudes}))"
    for state, expected in ((uniform, "1"), (f"-({uniform})", "0")):
        assert bind(forms[18], {**common, '"N"': str(size), '"u"': state}) == expected

# A nonbinary alphabet contains ordered tuples, including repetitions.
ordered = [f"qtuple(vector({a},{b}))" for a in (2, 3, 4) for b in (2, 3, 4)]
assert bind(forms[7], {'"Σ"': finite(["2", "3", "4"]), "n": "2"}) == evaluate(finite(ordered))
if args.gui_inputs:
    args.gui_inputs.write_text(json.dumps(inputs, ensure_ascii=False), encoding="utf-8")
print("Eight lesson inputs passed in Sets mode with binary and ternary alphabet checks.")
