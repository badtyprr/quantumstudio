"""Check that an unsized identity follows the space of an adjoint product."""
import argparse
import json
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument("worker", type=Path)
parser.add_argument("--gui-inputs", type=Path)
args = parser.parse_args()
rows = json.loads(Path(__file__).with_name("ibm027-inventory.json").read_bytes())["lessons"][1]["rows"]
source = rows[3]["literal"]
assert rows[3]["id"].endswith("M004")


def evaluate(expression, field="copy_text"):
    process = subprocess.run([args.worker.resolve(), "--json"], input=("quantum:" + expression).encode(),
                             capture_output=True, timeout=30)
    assert process.returncode == 0, (expression, process.stderr.decode())
    return json.loads(process.stdout)[field]


copied = evaluate(source)
display = evaluate(source, "display_text")
assert evaluate(copied) == copied
inputs = [[row["id"], row["literal"], "2" if row["id"].endswith("M063") else "0"] for row in rows]
for name, operator, expected in [
    ("identity-two", "identity(2)", "1"),
    ("cyclic-three", "matrix(3,3,[0,1,0,0,0,1,1,0,0])", "1"),
    ("complex-three", "matrix(3,3,[1,0,0,0,i,0,0,0,-1])", "1"),
    ("identity-four", "identity(4)", "1"),
    ("nonunitary-three", "matrix(3,3,[1,1,0,0,1,0,0,0,1])", "0"),
    ("isometry", "matrix(3,2,[1,0,0,1,0,0])", "0"),
    ("coisometry", "matrix(2,3,[1,0,0,0,1,0])", "0"),
]:
    for form in (source.strip("$").strip().rstrip("."), display, copied):
        query = f"replace(({form}),U,{operator})"
        assert evaluate(query) == expected, (name, query)
    inputs.append([name + "-" + expected, query, "0"])

for scalar, expected in [("i", "1"), ("2", "0")]:
    assert evaluate(f"replace(({copied}),U,matrix(1,1,[{scalar}]))") == expected

for fixed in ("I", "identity(2)", "matrix(2,2,[1,0,0,1])"):
    assert evaluate(f"replace((U U^{{\\dagger}}={fixed}),U,identity(3))") == "0"
assert evaluate(r"\mathbb{I}") == evaluate("identity(2)")
assert evaluate(r"replace((\mathbb{I}=U U^{\dagger}),U,identity(3))") == "1"
for product in (r"U U^{\dagger}", r"U^{\dagger} U"):
    for depth in range(3):
        term = "(" * depth + product + ")" * depth
        for identity in (r"\mathbb{I}", r"((\mathbb{I}))"):
            for equation in (f"{term}={identity}", f"{identity}={term}", f"{term}={identity}={term}"):
                saved = evaluate(equation)
                for form in (equation, saved):
                    assert evaluate(f"replace(({form}),U,identity(3))") == "1", form
                    assert evaluate(f"replace(({form}),U,matrix(2,2,[1,1,0,1]))") == "0", form
if args.gui_inputs:
    args.gui_inputs.write_text(json.dumps(inputs, ensure_ascii=False), encoding="utf-8")
print("Verified dimension-dependent unitarity and fixed-size identities.")
