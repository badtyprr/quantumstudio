"""Replay literal formulas from pinned, single-cell IBM phase-estimation lessons."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument("notebook", type=Path)
parser.add_argument("worker", type=Path)
parser.add_argument("output", type=Path)
parser.add_argument("revision", help="Revision used to build the worker")
parser.add_argument("--lesson", choices=("IBM028", "IBM029"), help="Require this pinned lesson")
args = parser.parse_args()
worker = args.worker.resolve()
data = args.notebook.read_bytes()
digest = hashlib.sha256(data).hexdigest()
lessons = {
    "2ff07f29f923364ca6d47b07a36266bebe64e335cce6d50cdeed2d1cbf39af4e":
        ("IBM028", "phase-estimation-procedure", 396, 17),
    "9ea5aee35aea5a33049ce593ef683ad2dcfc3bfff96f058d9ca8dbe0422c8681":
        ("IBM029", "shor-algorithm", 438, 0),
}
lesson, slug, math_count, image_count = lessons[digest]
if args.lesson and lesson != args.lesson:
    parser.error(f"Expected {args.lesson}, got {lesson}")
cells = json.loads(data)["cells"]
assert [c["cell_type"] for c in cells] == ["markdown"]
body = "".join(cells[0]["source"])
math = re.compile(r"(?<!\\)(\$\$|\$).*?(?<!\\)\1", re.DOTALL)
rows, figures, cache = [], [], {}
for i, match in enumerate(math.finditer(body), 1):
    literal = match.group()
    if literal not in cache:
        result = subprocess.run([worker, "--json"], input=("quantum:" + literal).encode(),
                                capture_output=True, timeout=60)
        if result.returncode == 0:
            value = json.loads(result.stdout)
            cache[literal] = dict(status="approximate" if value["approximate"] else "exact",
                                  display=value["display_text"], copy=value["copy_text"])
        elif result.returncode == 2 and result.stderr.strip():
            cache[literal] = dict(status="diagnostic", message=result.stderr.decode().strip())
        else:
            raise RuntimeError((literal, result.returncode, result.stderr))
    rows.append(dict(id=f"{lesson}-{digest[:8]}-M{i:03d}", cell=0, start=match.start(),
                     end=match.end(), literal=literal, **cache[literal]))
for match in re.finditer(r"!\[([^\]]*)\]\(([^)]+)\)", body):
    figures.append(dict(cell=0, start=match.start(), end=match.end(), alt=match[1], path=match[2]))
assert len(rows) == math_count and len(figures) == image_count
source = ("https://github.com/Qiskit/documentation/blob/f842259423a7adc9adeafd54153cdb5d3c5b680b/"
          "learning/courses/fundamentals-of-quantum-algorithms/phase-estimation-and-factoring/"
          f"{slug}.ipynb")
counts = Counter(row["status"] for row in rows)
report = dict(source=source, source_sha256=digest, worker_sha256=hashlib.sha256(worker.read_bytes()).hexdigest(),
              revision=args.revision, mode="Quantum notation", markdown_cells=1, code_cells=0,
              summary=counts, figures=figures, rows=rows)
if lesson == "IBM029":
    report["panels"] = [dict(title=m[1], cell=0, start=m.start(), end=m.end())
                        for m in re.finditer(r'<Figure title="([^"]+)">(.*?)</Figure>', body, re.DOTALL)]
    assert len(report["panels"]) == 3
args.output.write_bytes((json.dumps(report, ensure_ascii=False, indent=2) + "\n").encode())
print(dict(counts))
