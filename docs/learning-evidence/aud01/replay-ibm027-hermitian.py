"""Replay the arbitrary Hermitian H in M005–M007 and the later Hadamard gate."""
import argparse
import json
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument("worker", type=Path)
parser.add_argument("--gui-inputs", type=Path)
args = parser.parse_args()
rows = json.loads(Path(__file__).with_name("ibm027-inventory.json").read_bytes())["lessons"][1]["rows"]


def evaluate(body, dimension=None, error=None):
    context = f'matrixcontext("H",({dimension}),({dimension}),"hermitian"):' if dimension else ""
    process = subprocess.run([args.worker.resolve(), "--json"], input=("quantum:" + context + body).encode(),
                             capture_output=True, timeout=30)
    if error:
        assert process.returncode != 0 and error in process.stderr.decode(), (body, process.stdout, process.stderr)
        return
    assert process.returncode == 0, (body, process.stderr.decode())
    return json.loads(process.stdout)["copy_text"]


inputs = []
for row in rows:
    number = int(row["id"][-3:])
    entry = [row["id"], row["literal"], "3" if number == 12 else "2" if number == 63 else "0"]
    if number in (5, 6, 7):
        entry.append("N")
    inputs.append(entry)

for index in (4, 6):
    assert evaluate(rows[index]["literal"], "N") == """operatorparam('H','N',"hermitian")"""
assert evaluate(rows[39]["literal"]) == evaluate("H")
assert evaluate("H") != evaluate("H", "N")
assert evaluate("|H>", "N") == evaluate("|H>")
assert evaluate('matrixcontext("A",(2),(3),"general"):$A$') == "matrixparam('A',2,3)"
source = rows[5]["literal"]
canonical = evaluate(source, "N")
assert evaluate(canonical) == canonical == evaluate(canonical, "N")
formula = source.strip("$").strip().rstrip(",")
for name, size, matrix in [
    ("complex-three", 3, "matrix(3,3,[0,i,0,-i,0,0,0,0,3])"),
    ("nonunitary-two", 2, "matrix(2,2,[2,1,1,-3])"),
]:
    direct = f"replace(({formula}),H,{matrix})"
    assert evaluate(direct, size) == "1"
    inputs.append([name, direct, "0", str(size)])
    for body in [f"replace(replace(({canonical}),N,{size}),'H',{matrix})",
                 f"replace(replace(({canonical}),'H',{matrix}),N,{size})"]:
        assert evaluate(body) == "1"
bad = "matrix(3,3,[0,i,0,i,0,0,0,0,3])"
evaluate(f"replace(({formula}),H,{bad})", 3, "operator property")
evaluate(f"replace(replace(({canonical}),N,3),'H',{bad})", error="operator property")
evaluate(f"replace(({formula}),H,identity(2))", 3, "dimension")
if args.gui_inputs:
    args.gui_inputs.write_text(json.dumps(inputs, ensure_ascii=False), encoding="utf-8")
print("Verified the declared Hermitian matrix, substitutions, session inputs and default Hadamard gate.")
