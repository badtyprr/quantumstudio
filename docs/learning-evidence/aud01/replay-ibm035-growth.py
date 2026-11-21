"""Compare the Grover query bound with exact growth exponents."""
from fractions import Fraction
from itertools import product
import json
import os
from pathlib import Path
import subprocess
import sys

worker = Path(sys.argv[1]).resolve()
env = dict(os.environ, QALCULATE_DEFINITIONS_DIR=str(worker.parent / "data"))


def copy(expr):
    p = subprocess.run([worker, "--json"], input=("quantum:" + expr).encode(),
                       capture_output=True, check=True, timeout=30, env=env)
    result = json.loads(p.stdout)
    assert not result["approximate"]
    return result["copy_text"]


row, = json.loads(Path(__file__).with_name("ibm035-inventory.json").read_bytes())["rows"]
order = copy(row["literal"])
assert order == copy(order) and order.startswith("qbigorder(")
powers = [("1", 0), ("N^(1/3)", Fraction(1, 3)), ("sqrt(N)", Fraction(1, 2)),
          ("N^(2/3)", Fraction(2, 3)), ("N", 1), ("N^(3/2)", Fraction(3, 2))]
for (lhs, a), (rhs, b) in product(powers, repeat=2):
    assert copy(f"{lhs}=O({rhs})") == str(int(a <= b)), (lhs, rhs)
for x, exponent in powers:
    assert copy(f"qcompare({x},{order},4)") == str(int(exponent <= Fraction(1, 2)))

# For independently growing positive inputs, weighted AM-GM proves the first
# bound. Taking m=N gives a counterexample to the second.
for expr, expected in [
        ("sqrt(N*m)=O(N+m)", "1"), ("sqrt(N*m)=O(N^(1/3)+m^(1/3))", "0"),
        ("sqrt(N)=O(sqrt(n))", "0"), ("0=O(sqrt(N))", "1"), ("sqrt(N)=O(0)", "0"),
        ("sqrt(sqrt(N))=O(N^(1/4))", "1"), ("sqrt(N)!=O(N)", "0")]:
    assert copy(expr) == expected, expr
for expr in ["sqrt(N)=O(-N)", "N=O(n*m*k)", "sqrt(N)=O(sin(N))"]:
    assert "qbigorder" in copy(expr), expr
print("Grover's literal and 52 exact growth controls passed.")
