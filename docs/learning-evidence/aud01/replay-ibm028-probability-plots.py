"""Compare the source SVG probability curves with the phase-estimation distribution."""
import argparse
import cmath
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET

parser = argparse.ArgumentParser()
parser.add_argument("figures", type=Path, help="Directory containing the pinned lesson SVGs")
parser.add_argument("worker", type=Path)
parser.add_argument("output", type=Path)
args = parser.parse_args()
worker = args.worker.resolve()
plots = [
    ("F04", "kickback-probabilities", 2, 1, [0, 1]),
    ("F06", "double-kickback-probabilities", 2, 2, [0, 1]),
    ("F10", "two-bit-probabilities", 4, 1, [0, 1, 2, 3]),
    ("F16", "three-qubit-probabilities", 8, 1, [3, 4, 5]),
    ("F17", "four-qubit-probabilities", 16, 1, [7, 8, 9]),
]


def vertices(path):
    # These SVGs store their samples as relative and absolute line segments.
    # Later coordinate pairs in a move command are implicit lines.
    tokens = re.findall(r"[a-zA-Z]|[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?", path)
    x = y = 0
    i = 0
    while i < len(tokens):
        if tokens[i].isalpha():
            command = tokens[i]
            assert command in "MmLlHh"
            i += 1
        dx = float(tokens[i])
        i += 1
        x = x + dx if command.islower() else dx
        if command.lower() != "h":
            dy = float(tokens[i])
            i += 1
            y = y + dy if command.islower() else dy
        yield x, y


def probability(n, multiple, outcome, theta):
    phase = multiple * theta - outcome / n
    return abs(sum(cmath.exp(2j * math.pi * x * phase) for x in range(n)) / n) ** 2


report = []
for figure, stem, n, multiple, outcomes in plots:
    path = args.figures / (stem + ".svg")
    source = ("https://raw.githubusercontent.com/Qiskit/documentation/"
              "f842259423a7adc9adeafd54153cdb5d3c5b680b/public/learning/images/courses/"
              "fundamentals-of-quantum-algorithms/phase-estimation-and-factoring/" + path.name)
    root = ET.fromstring(path.read_bytes())
    paths = [node for node in root.iter() if node.tag.endswith("}path")]
    axes = [node for node in paths if node.get("d", "").startswith(("M 0,0 H ", "M 0,0 V "))]
    x_axis, y_axis = [float(node.attrib["d"].split()[-1]) for node in axes]
    curves = [node for node in paths if node.get("style", "").startswith("fill:none;stroke:")
              and len(node.get("d", "")) > 9000]
    legend = [node.attrib["aria-label"] for node in root.iter() if "aria-label" in node.attrib]
    assert legend[-len(outcomes):] == list(map(str, outcomes))
    assert len(curves) == len(outcomes)
    evidence = []
    for outcome, curve in zip(outcomes, curves):
        assert curve.get("transform") == axes[0].get("transform") == axes[1].get("transform")
        points = list(vertices(curve.attrib["d"]))
        assert len(points) >= 990 and abs(points[0][0]) < 0.001 and abs(points[-1][0] / x_axis - 1) < 0.001
        error = max(abs(y / y_axis - probability(n, multiple, outcome, x / x_axis)) for x, y in points)
        assert error < 0.001, (figure, outcome, error)
        # The worker evaluates an explicit Fourier sum at an off-grid phase
        # and at the peak. The reference above uses Python complex arithmetic.
        samples = []
        for numerator, denominator in [(outcome, n * multiple), (2*outcome+1, 2*n*multiple)]:
            delta = f"({multiple}*{numerator}/{denominator}-{outcome}/{n})"
            terms = ["1"] + [f"exp(2*pi*i*{x}*{delta})" for x in range(1, n)]
            expression = "abs((" + "+".join(terms) + f")/{n})^2"
            p = subprocess.run([worker, "--json", "--approx"], input=("quantum:" + expression).encode(),
                               capture_output=True, timeout=30)
            assert p.returncode == 0, (figure, p.stderr.decode())
            value = float(json.loads(p.stdout)["copy_text"])
            assert abs(value - probability(n, multiple, outcome, numerator / denominator)) < 1e-12
            samples.append(dict(phase=f"{numerator}/{denominator}", result=value, input=expression))
        evidence.append(dict(outcome=outcome, vertices=len(points), max_absolute_error=error, worker=samples))
    report.append(dict(id=figure, source=source, file=path.name, sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                       dimension=n, phase_multiplier=multiple, curves=evidence))
args.output.write_bytes((json.dumps(report, indent=2) + "\n").encode())
print(f"Verified {len(report)} plots and {sum(len(p['curves']) for p in report)} probability curves.")
