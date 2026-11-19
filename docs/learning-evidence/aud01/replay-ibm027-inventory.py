"""Inventory the pinned phase-estimation introduction and replay the problem lesson."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument("introduction", type=Path)
parser.add_argument("problem", type=Path)
parser.add_argument("worker", type=Path)
parser.add_argument("output", type=Path)
parser.add_argument("--gui-inputs", type=Path)
args = parser.parse_args()
worker = args.worker.resolve()
revision = "f842259423a7adc9adeafd54153cdb5d3c5b680b"
base = f"https://github.com/Qiskit/documentation/blob/{revision}/learning/courses/fundamentals-of-quantum-algorithms/phase-estimation-and-factoring/"
math = re.compile(r"(?<!\\)(\$\$|\$).*?(?<!\\)\1", re.DOTALL)
cache = {}
inputs = []
lessons = []

def evaluate(literal):
    if literal not in cache:
        result = subprocess.run([worker, "--json"], input=("quantum:" + literal).encode(),
                                capture_output=True, timeout=45)
        if result.returncode == 0:
            value = json.loads(result.stdout)
            cache[literal] = dict(label="approximate" if value["approximate"] else "exact",
                                  copy=value["copy_text"])
        elif result.returncode == 2 and result.stderr.strip():
            cache[literal] = dict(label="diagnostic", diagnostic=result.stderr.decode().strip())
        else:
            raise RuntimeError(f"Worker failed for {literal!r}: {result.returncode}")
    return cache[literal]

for lesson, path, digest in [
    ("IBM026", args.introduction, "ce4e2e6a9fa01f1d6a65551f0dff19740e524620bb41c434f9bd9e3f1f310787"),
    ("IBM027", args.problem, "64df86108de2261d346c56c7b6ea16ac70058718e16207075b4f47d89e069e12"),
]:
    raw = path.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == digest
    cells = json.loads(raw)["cells"]
    assert [cell["cell_type"] for cell in cells] == ["markdown"]
    body = "".join(cells[0]["source"])
    matches = list(math.finditer(body))
    assert "$" not in math.sub("", body)
    rows = []
    for index, match in enumerate(matches, 1):
        literal = match.group()
        key = f"{lesson}-{digest[:8]}-M{index:03}"
        rows.append(dict(id=key, cell=0, start=match.start(), end=match.end(),
                         literal=literal, **evaluate(literal)))
        inputs.append([key, literal])
    lessons.append(dict(lesson=lesson, source=base+path.name, sha256=digest,
                        markdown_cells=1, code_cells=0, rows=rows))
assert not lessons[0]["rows"] and lessons[1]["rows"]
# The lesson's nonnormal matrix sends |1> to |0> and annihilates |0>.
# Its two products with its adjoint are different one-dimensional projectors.
by_id = {row["id"][-4:]: row for row in lessons[1]["rows"]}
matrix = by_id["M008"]["copy"]
controls = [
    ("basis-0", f"({matrix})*|0>=matrix(2,1,[0,0])", "1"),
    ("basis-1", f"({matrix})*|1>=|0>", "1"),
    ("left-projector", f"({matrix})*dagger({matrix})=matrix(2,2,[1,0,0,0])", "1"),
    ("right-projector", f"dagger({matrix})*({matrix})=matrix(2,2,[0,0,0,1])", "1"),
    ("normal", f"({matrix})*dagger({matrix})=dagger({matrix})*({matrix})", "0"),
]
for key in ("M009", "M010", "M027", "M036"):
    assert by_id[key]["copy"] == "1", key
for key, expression, answer in controls:
    assert evaluate(expression) == dict(label="exact", copy=answer), key
report = dict(worker_sha256=hashlib.sha256(worker.read_bytes()).hexdigest(), lessons=lessons, matrix_controls=controls)
args.output.write_bytes((json.dumps(report, indent=2, ensure_ascii=False)+"\n").encode())
if args.gui_inputs:
    args.gui_inputs.write_text(json.dumps(inputs, ensure_ascii=False), encoding="utf-8")
print(len(inputs), "source spans,", len(set(literal for _, literal in inputs)), "distinct literals,",
      dict(Counter(row["label"] for lesson in lessons for row in lesson["rows"])))
