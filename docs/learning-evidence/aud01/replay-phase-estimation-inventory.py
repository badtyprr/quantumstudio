"""Replay literal formulas from pinned, single-cell IBM quantum algorithm lessons."""
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
parser.add_argument("--lesson", help="Require this pinned lesson")
args = parser.parse_args()
worker = args.worker.resolve()
data = args.notebook.read_bytes()
digest = hashlib.sha256(data).hexdigest()
lessons = {
    "2ff07f29f923364ca6d47b07a36266bebe64e335cce6d50cdeed2d1cbf39af4e":
        ("IBM028", "phase-estimation-procedure", 396, 17),
    "9ea5aee35aea5a33049ce593ef683ad2dcfc3bfff96f058d9ca8dbe0422c8681":
        ("IBM029", "shor-algorithm", 438, 0),
    "7cd1ba3b4697d4bde922918a060234374ca4fa8137ef221d54944e6c53c24e83":
        ("IBM030", "introduction", 0, 0),
    "9bc1492a52076f45c99e20d10be00d847a3901be147f56caf2a1ba0849a981fc":
        ("IBM031", "unstructured-search", 45, 0),
    "d60b500f57ce51007665c53daae3a04cfc3fef6054af2e6abe27297d2d91151a":
        ("IBM032", "grover-algorithm-description", 59, 3),
    "cf35c6409842268e9913008e61df569cf875bb209765682689bb590b6ed36ebe":
        ("IBM033", "analysis", 117, 3),
    "94ee62dd84ab644d5ba22ba1675fdb29afb0ddc777505af0461f469c9649077b":
        ("IBM034", "number-of-iterations", 155, 0),
    "fb35d58b14dfd991da94ea11ef5e72bcd384287217182ddfebe1a2129b3e254a":
        ("IBM035", "concluding-remarks", 1, 0),
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
chapter = "phase-estimation-and-factoring" if lesson in ("IBM028", "IBM029") else "grover-algorithm"
source = ("https://github.com/Qiskit/documentation/blob/f842259423a7adc9adeafd54153cdb5d3c5b680b/"
          f"learning/courses/fundamentals-of-quantum-algorithms/{chapter}/"
          f"{slug}.ipynb")
counts = Counter(row["status"] for row in rows)
report = dict(source=source, source_sha256=digest, worker_sha256=hashlib.sha256(worker.read_bytes()).hexdigest(),
              revision=args.revision, mode="Quantum notation", markdown_cells=1, code_cells=0,
              summary=counts, figures=figures, rows=rows)
if "<Figure" in body:
    report["panels"] = [dict(title=m[1], cell=0, start=m.start(), end=m.end())
                        for m in re.finditer(r'<Figure title="([^"]+)">(.*?)</Figure>', body, re.DOTALL)]
    assert len(report["panels"]) == body.count("<Figure")
args.output.write_bytes((json.dumps(report, ensure_ascii=False, indent=2) + "\n").encode())
print(dict(counts))
