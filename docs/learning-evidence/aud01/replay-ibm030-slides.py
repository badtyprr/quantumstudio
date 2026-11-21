"""Check the plotted Grover iterates on pages 24 and 26 of the IBM lesson slides."""
import argparse
from decimal import Decimal, localcontext
from fractions import Fraction
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument("slides", type=Path)
parser.add_argument("worker", type=Path)
args = parser.parse_args()
slides_hash = sha256(args.slides.read_bytes()).hexdigest()
assert slides_hash == "02be18ffcd56ac5b9d4bd43a69180ac1330f285fc8dfc30ed5559142d04091c1"
worker = args.worker.resolve()
env = dict(os.environ, QALCULATE_DEFINITIONS_DIR=str(worker.parent / "data"))


def evaluate(expression, approximate=False):
    command = [worker, "--json"]
    if approximate:
        command.append("--approx")
    output = subprocess.run(command, input=("quantum:" + expression).encode(),
                            env=env, capture_output=True, timeout=30, check=True)
    return json.loads(output.stdout)["copy_text"]


reports = []
for page, marked, optimum, plotted in [(24, 1, 8, {0, 1, 2, 8, 12}), (26, 4, 4, {0, 1, 2, 3, 4, 8})]:
    angle = f"asin(sqrt({marked}/128))"
    assert evaluate(f"floor(pi/(4*{angle}))") == str(optimum)
    # Amplitudes are scaled by sqrt(128), so the reflection stays rational.
    amplitudes = [Fraction(1)] * 128
    probabilities = {}
    for iteration in range(max(plotted) + 1):
        if iteration in plotted:
            exact = sum(a*a for a in amplitudes[:marked]) / 128
            numeric = evaluate(f"sin({2*iteration+1}*{angle})^2", approximate=True)
            with localcontext() as context:
                context.prec = 45
                reference = Decimal(exact.numerator) / Decimal(exact.denominator)
                assert abs(Decimal(numeric) - reference) < Decimal("1e-28")
            probabilities[iteration] = numeric
        reflected = [-a if i < marked else a for i, a in enumerate(amplitudes)]
        mean = sum(reflected) / 128
        amplitudes = [2*mean - a for a in reflected]
    reports.append(dict(page=page, marked=marked, iterations=optimum, probabilities=probabilities))

print(json.dumps(dict(slides_sha256=slides_hash, worker_sha256=sha256(worker.read_bytes()).hexdigest(),
                      search_space=128, cases=reports), indent=2))
