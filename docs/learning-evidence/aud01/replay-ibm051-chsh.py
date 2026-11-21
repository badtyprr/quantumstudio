"""Check every classical CHSH table entry and each amplitude of the four quantum strategies."""
import argparse
import json
import math
import os
from pathlib import Path
import re
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument("worker", type=Path)
parser.add_argument("inventory", type=Path)
args = parser.parse_args()
worker = args.worker.resolve()
rows = json.loads(args.inventory.read_bytes())["rows"]
env = dict(os.environ, QALCULATE_DEFINITIONS_DIR=str(worker.parent / "data"))


def evaluate(expression, numeric=False):
    name, definition = "ψ(t)", "cos(t)*|0>+sin(t)*|1>"
    request = f"QSTATES1\n1\n{len(name.encode())}\n{len(definition.encode())}\n{name}{definition}quantum:{expression}"
    flags = ["--approx"] if numeric else []
    result = subprocess.run([worker, "--states", "--json", *flags], input=request.encode(), env=env, capture_output=True, timeout=30)
    assert result.returncode == 0, result.stderr.decode()
    return json.loads(result.stdout)


table = evaluate(rows[32]["literal"])["copy_text"]
for a in (0, 1):
    for b in (0, 1):
        cells = evaluate(f"replace(replace(({table}),a,{a}),b,{b})")["cells"]
        for x in (0, 1):
            for y in (0, 1):
                win = (a ^ b) == (x & y)
                assert cells[1 + 2*x + y][1:] == [str(int(win)), str(int(not win))]

for number, x, y in [(122,0,0), (135,0,1), (148,1,0), (166,1,1)]:
    row = rows[number-1]["literal"]
    aligned = row.split(r"\begin{aligned}")[1].split(r"\end{aligned}")[0]
    terms = re.split(r"&\s*=", aligned)
    assert len(terms) == 3
    delta = math.pi * (x/4 - (1-2*y)/8)
    expected = [v / math.sqrt(2) for v in [math.cos(delta), math.sin(delta), -math.sin(delta), math.cos(delta)]]
    for term in terms:
        term = re.sub(r"\\\\(?:\[[^\]]*\])?", " ", term).replace("&","").strip().rstrip(".")
        for angle in ["0", r"\pi/4", r"\pi/8", r"-\pi/8"]:
            t = angle.replace(r"\pi","pi")
            term = f"replace(({term}),U_{{{angle}}},[cos({t}),sin({t});-sin({t}),cos({t})])"
        cells = evaluate(term, True)["cells"]
        assert len(cells) == 4
        amplitudes = [float(cell[0].replace("−","-")) for cell in cells]
        assert all(abs(a-b)<1e-13 for a,b in zip(amplitudes,expected)), (number, amplitudes)
        probability = sum(a*a for index,a in enumerate(amplitudes) if ((index//2) ^ (index%2)) == (x & y))
        assert abs(probability - (2 + math.sqrt(2))/4) < 1e-13
print("Verified 16 classical outcomes and all 48 amplitudes from the four three-part CHSH equations.")
