"""Verify the Grover lecture query circuit, plotted iterates and success probabilities."""
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
parser.add_argument("--windows", type=Path, help="Prepare or verify the exact-result Windows session inputs")
report_options = parser.add_mutually_exclusive_group()
report_options.add_argument("--report", type=Path)
report_options.add_argument("--session-report", type=Path)
args = parser.parse_args()
if (args.report or args.session_report) and not args.windows:
    parser.error("Report verification requires a Windows session directory")
windows_cases = {}
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
    value = json.loads(output.stdout)
    if args.windows and not approximate:
        assert not value["approximate"]
        windows_cases.setdefault(expression, value["copy_text"])
    return value["copy_text"]


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

# Page 4 asks for the inverse of the phase-kickback construction.
query_checks = 0
for mask in range(16):
    entries = [str(1-2*((mask >> c) & 1) if r == c else 0) for r in range(4) for c in range(4)]
    phase = "matrix(4,4,[" + ",".join(entries) + "])"
    circuit = f"(H @ identity(4))*controlled({phase})*(H @ identity(4))"
    for state in range(8):
        target = state ^ (((mask >> (state % 4)) & 1) << 2)
        assert evaluate(f"norm(({circuit})*basis({state},8)-basis({target},8))") == "0"
        query_checks += 1

# The page 25 table prints at most seven decimal places. Independently rotate
# the two amplitude classes using the mean after the marked amplitude flips.
displayed = [".5", "1.0", ".9453125", ".9613190", ".9991823", ".9965857",
             ".9956199", ".9999470", ".9994480", ".9994612", ".9999968", ".9999453"]
table = []
for k, printed in enumerate(displayed, 1):
    size = 2**k
    angle = f"asin(sqrt(1/{size}))"
    iterations = int(evaluate(f"floor(pi/(4*{angle}))"))
    marked, unmarked = Fraction(1), Fraction(1)
    for _ in range(iterations):
        mean = ((size-1)*unmarked-marked)/size
        marked, unmarked = 2*mean+marked, 2*mean-unmarked
    probability = marked**2/size
    assert probability >= 1-Fraction(1,size)
    with localcontext() as ctx:
        ctx.prec = 50
        exact = Decimal(probability.numerator)/Decimal(probability.denominator)
        assert abs(exact-Decimal(printed)) <= Decimal("0.00000005")
        numeric = Decimal(evaluate(f"sin((2*{iterations}+1)*{angle})^2", True))
        assert abs(numeric-exact) < Decimal("1e-28")
    table.append(dict(inputs=size, iterations=iterations, printed=printed))

# Page 29 samples from 1 through floor(pi*sqrt(N)/4), inclusive.
# For N=4 and three marked inputs, that distribution contains only t=1.
assert evaluate("floor(pi*sqrt(4)/4)") == "1"
assert evaluate("sin(3*asin(sqrt(3/4)))^2") == "0"
diffusion = "matrix(4,4,[" + ",".join(str(Fraction(1,2)-int(r==c)) for r in range(4) for c in range(4)) + "])"
oracle = "matrix(4,4,[1,0,0,0,0,-1,0,0,0,0,-1,0,0,0,0,-1])"
assert evaluate(f"norm({diffusion}*{oracle}*matrix(4,1,[1,1,1,1])/2+basis(0,4))") == "0"
if args.windows:
    from learning_clipboard_checks import clipboard_checks
    cases = {f"lecture-{i:03}": case for i, case in enumerate(windows_cases.items(), 1)}
    clipboard_checks(worker, args.windows, args.report or args.session_report, cases, 144,
                     dict(slides_sha256=slides_hash), sessions_only=bool(args.session_report))
print(json.dumps(dict(slides_sha256=slides_hash, worker_sha256=sha256(worker.read_bytes()).hexdigest(),
                      search_space=128, cases=reports, controlled_query_checks=query_checks,
                      unique_search_table=table,
                      printed_random_schedule=dict(inputs=4, marked=3, iterations=[1], success=0)), indent=2))
