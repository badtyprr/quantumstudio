"""Check both seven-step Grover identities against independently constructed operators."""
import argparse
import json
import os
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument("worker", type=Path)
worker = parser.parse_args().worker.resolve()
env = dict(os.environ, QALCULATE_DEFINITIONS_DIR=str(worker.parent / "data"))
rows = json.loads(Path(__file__).with_name("ibm033-inventory.json").read_bytes())["rows"]


def evaluate(source):
    result = subprocess.run([worker, "--json"], input=("quantum:" + source).encode(),
                            capture_output=True, env=env, timeout=30)
    assert result.returncode == 0, result.stderr.decode()
    return json.loads(result.stdout)["copy_text"]


def matrix(rows):
    entries = ",".join(str(x) for row in rows for x in row)
    return f"matrix({len(rows)},{len(rows[0])},vector({entries}))"


def uniform(size, support):
    return matrix([[f"1/sqrt({len(support)})" if i in support else 0] for i in range(size)])


names = 'vector("G","Z_f","N","u",qnamedket("A_0"),qnamedket("A_1"),qbars("A_0"),qbars("A_1"))'
checks = 0
for row in rows:
    if not row["id"].endswith(("M064", "M067")):
        continue
    formula = evaluate(row["literal"])
    assert evaluate(formula) == formula
    # Alter an intermediate term only. Both endpoints of the chain stay intact.
    altered = row["literal"].replace(r"\sqrt{\frac", r"3\sqrt{\frac", 1)
    assert altered != row["literal"]
    wrong_step = evaluate(altered)
    for size, marked in [(2, {1}), (4, {0}), (4, {0, 2}), (8, {1, 4, 7})]:
        basis = set(range(size))
        unmarked = basis - marked
        signs = [-1 if i in marked else 1 for i in range(size)]
        oracle = matrix([[signs[j] if i == j else 0 for j in range(size)] for i in range(size)])
        # Column j of (2|u><u|-I) Z_f is the diffusion column times its oracle sign.
        iterate = matrix([[f"{(2 - size * (i == j))*signs[j]}/{size}"
                           for j in range(size)] for i in range(size)])
        for chain, gate, expected in ((formula, iterate, "1"), (formula, f"-({iterate})", "0"),
                                      (wrong_step, iterate, "0")):
            args = [gate, oracle, str(size), uniform(size, basis), uniform(size, unmarked),
                    uniform(size, marked), str(len(unmarked)), str(len(marked))]
            observed = evaluate(f'replace(({chain}),{names},vector({",".join(args)}))')
            assert observed == expected, (row["id"], marked, observed, expected)
            checks += 1
assert checks == 24
print(f"{checks} Grover derivation controls passed.")
