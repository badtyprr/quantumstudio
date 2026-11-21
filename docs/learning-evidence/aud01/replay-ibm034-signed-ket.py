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
if len(sys.argv) > 2:
    Path(sys.argv[2]).write_text(json.dumps(gui), encoding="utf8")
print("Verified the original formula, Copy re-entry and 15 exact substitutions.")
