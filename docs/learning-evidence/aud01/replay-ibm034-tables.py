"""Compare the three printed Grover probability tables with finite searches."""
from argparse import ArgumentParser
from decimal import Decimal, localcontext
from fractions import Fraction
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import subprocess

parser = ArgumentParser()
parser.add_argument("worker", type=Path)
worker = parser.parse_args().worker.resolve()
env = dict(os.environ, QALCULATE_DEFINITIONS_DIR=str(worker.parent / "data"))
inventory = json.loads(Path(__file__).with_name("ibm034-inventory.json").read_bytes())
assert sha256(worker.read_bytes()).hexdigest() == inventory["worker_sha256"]
tables = [row for row in inventory["rows"] if r"\begin{array}" in row["literal"]]
assert len(tables) == 3


def evaluate(expression, approximate=False):
    args = [worker, "--json"]
    if approximate:
        args.append("--approx")
    p = subprocess.run(args, input=("quantum:" + expression).encode(), env=env,
                       capture_output=True, check=True, timeout=30)
    return json.loads(p.stdout)["copy_text"]


def probability(size, marked, iterations):
    # Track the common amplitude of each group in units of 1/sqrt(size).
    good = bad = Fraction(1)
    for _ in range(iterations):
        mean = ((size-marked)*bad - marked*good) / size
        good, bad = 2*mean + good, 2*mean - bad
    assert marked*good**2 + (size-marked)*bad**2 == size
    return marked*good**2 / size


results = []
for table, marked, assumed, count in zip(tables, (1, 4, 4), (1, 1, 4), (16, 15, 15)):
    rows = re.findall(r"^\s*(\d+)\s*&\s*(\d+\.\d{10})", table["literal"], re.MULTILINE)
    assert len(rows) == count
    tested = []
    for size, printed in rows:
        angle = f"asin(sqrt({assumed}/{size}))"
        t = int(evaluate(f"floor(pi/(4*{angle}))"))
        exact = probability(int(size), marked, t)
        rendered = evaluate(f"sin({2*t+1}*asin(sqrt({marked}/{size})))^2", True)
        value = Fraction(rendered.replace(' ∕ ', '/'))
        with localcontext() as context:
            context.prec = 60
            numeric = Decimal(value.numerator) / Decimal(value.denominator)
            expected = Decimal(exact.numerator) / Decimal(exact.denominator)
            assert abs(expected - numeric) < Decimal("1e-28")
            assert abs(expected - Decimal(printed)) <= Decimal("0.00000000005")
        tested.append(dict(size=int(size), iterations=t, printed=printed))
    results.append(dict(source_id=table["id"], marked=marked, assumed_marked=assumed, rows=tested))

print(json.dumps(dict(source_sha256=inventory["source_sha256"], worker_sha256=inventory["worker_sha256"],
                      tables=results), indent=2))
