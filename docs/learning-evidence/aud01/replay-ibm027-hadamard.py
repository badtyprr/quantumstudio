"""Check the Hadamard spectral decomposition and its two eigenstates in IBM-027."""
import argparse
import json
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument("worker", type=Path)
parser.add_argument("--gui-inputs", type=Path)
args = parser.parse_args()
worker = args.worker.resolve()
rows = json.loads(Path(__file__).with_name("ibm027-inventory.json").read_bytes())["lessons"][1]["rows"]
source = {row["id"][-4:]: row["literal"] for row in rows}


def evaluate(body, state=None):
    data = ("quantum:" + body).encode()
    flags = []
    if state is not None:
        name, expression = "ψ(α)".encode(), state.encode()
        data = f"QSTATES1\n1\n{len(name)}\n{len(expression)}\n".encode() + name + expression + data
        flags = ["--states"]
    p = subprocess.run([worker, "--json", *flags], input=data, capture_output=True, timeout=30)
    assert p.returncode == 0, (body, p.stderr.decode())
    return json.loads(p.stdout)


inputs = [[r["id"], r["literal"]] for r in rows]
family = "cos(α)|0> + sin(α)|1>"
for key, expected, rejected in [("M042", "1", "0"),
                                ("M044", r"\begin{gathered}1\\1\end{gathered}", r"\begin{gathered}0\\0\end{gathered}")]:
    original = source[key]
    copied = evaluate(original)["copy_text"]
    assert evaluate(copied)["copy_text"] == copied
    for body in (original, copied):
        assert evaluate(body, family)["copy_text"] == expected
        assert evaluate(body, "|0>")["copy_text"] == rejected
        # A common phase cancels in projectors but changes the state columns.
        phase = expected if key == "M042" else rejected
        assert evaluate(body, f"i*({family})")["copy_text"] == phase
        assert evaluate(body, "cos(α)|0>-sin(α)|1>")["copy_text"] == rejected

# Compare every octant with the known half-angle radicals, including a
# negative revolution and angles beyond 2 pi to check quadrant reduction.
large, small = "sqrt(2+sqrt(2))/2", "sqrt(2-sqrt(2))/2"
octants = [(large, small), (small, large), ("-"+small, large), ("-"+large, small),
           ("-"+large, "-"+small), ("-"+small, "-"+large), (small, "-"+large), (large, "-"+small)]
for n in range(-15, 32, 2):
    cosine, sine = octants[(n % 16)//2]
    angle = f"({n}*pi/8)"
    for function, radical in [("cos", cosine), ("sin", sine)]:
        body = f"{function}({angle})=({radical})"
        assert evaluate(body)["copy_text"] == "1", (n, function)
        if n in (1,5):
            inputs.append([f"{function}-{n}-1", body])
if args.gui_inputs:
    args.gui_inputs.write_text(json.dumps(inputs, ensure_ascii=False), encoding="utf-8")
print("Verified both lesson formulas with matching and mismatching states and 48 exact trigonometric identities.")
