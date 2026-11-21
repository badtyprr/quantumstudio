"""Exercise both signs of IBM-034's constant phase-oracle relation."""
import json
import os
from pathlib import Path
import subprocess
import sys

worker = Path(sys.argv[1]).resolve()
source = json.loads(Path(__file__).with_name("ibm034-inventory.json").read_bytes())
row, = [r for r in source["rows"] if r["id"].endswith("-M152")]


def evaluate(expression):
    result = subprocess.run([worker, "--json"], input=("quantum:" + expression).encode(),
                            capture_output=True, check=True, timeout=30,
                            env=dict(os.environ, QALCULATE_DEFINITIONS_DIR=str(worker.parent/"data")))
    value = json.loads(result.stdout)
    assert not value["approximate"]
    return value["copy_text"]


relation = evaluate(row["literal"])
assert relation.startswith("qsignedequal(") and evaluate(relation) == relation
gui = [["source", row["literal"], "0"]]
for width in range(1, 4):
    size = 2**width
    uniform = "(" + "@".join(["|+>"] * width) + ")"
    for name, diagonal, expected in [
            ("identity", [1]*size, "1"), ("negative-identity", [-1]*size, "1"),
            ("one-marked", [-1]+[1]*(size-1), "0"), ("one-unmarked", [1]+[-1]*(size-1), "0"),
            ("wrong-magnitude", [2]*size, "0")]:
        entries = [str(diagonal[i] if i == j else 0) for i in range(size) for j in range(size)]
        matrix = f"matrix({size},{size},[{','.join(entries)}])"
        formula = f"""replace(({relation}),vector("Z_f",qketstate('u')),vector({matrix},{uniform}))"""
        assert evaluate(formula) == expected, (width, name)
        gui.append([f"{name}-{width}", formula, "0"])
chain_row, = [r for r in source["rows"] if r["id"].endswith("-M153")]
chain = evaluate(chain_row["literal"])
assert evaluate(chain) == chain
gui.append(["original-chain", chain_row["literal"], "0"])
# Flip only the signed reflection in the middle. The endpoints are identical.
wrong_literal = chain_row["literal"].replace(r"\pm \bigl", r"\pm (-1) \bigl")
assert wrong_literal != chain_row["literal"]
wrong_chain = evaluate(wrong_literal)
for width in range(1, 4):
    size = 2**width
    uniform = "(" + "@".join(["|+>"] * width) + ")"
    for sign in (1, -1):
        phase = [str(sign if i == j else 0) for i in range(size) for j in range(size)]
        # R=2|u><u|-I. Its entries are 2/size minus the Kronecker delta.
        step = [f"{sign * (2 - size * int(i == j))}/{size}" for i in range(size) for j in range(size)]
        phase_matrix = f"matrix({size},{size},[{','.join(phase)}])"
        step_matrix = f"matrix({size},{size},[{','.join(step)}])"
        symbols = """vector(qoperatorref('G'),qoperatorref("Z_f"),qketstate('u'))"""
        for label, expression, gate, expected in [
                ("valid", chain, step_matrix, "1"), ("wrong-iterate", chain, f"(-{step_matrix})", "0"),
                ("wrong-intermediate", wrong_chain, step_matrix, "0")]:
            bound = f"replace(({expression}),{symbols},vector({gate},{phase_matrix},{uniform}))"
            assert evaluate(bound) == expected, (width, sign, label)
            gui.append([f"chain-{label}-{sign}-{width}", bound, "0"])
# Compare chains with independent enumeration of the two allowed signs.
# Batch by the first operand to keep each worker invocation small.
for left in range(-3, 4):
    formulas, expected = [], []
    for a in range(-2, 3):
        for b in range(-2, 3):
            formulas.append(f"({left}=1±({a})=±({b})+1)")
            expected.append(str(int(any(left == 1+sign*a == sign*b+1 for sign in (1, -1)))))
    assert evaluate("vector("+",".join(formulas)+")") == "vector("+",".join(expected)+")"
if len(sys.argv) > 2:
    Path(sys.argv[2]).write_text(json.dumps(gui), encoding="utf8")
print("Verified both original formulas, Copy re-entry and 33 exact substitutions.")
