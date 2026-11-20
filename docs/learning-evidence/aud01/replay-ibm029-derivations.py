"""Check the Shor lesson's repeating decimal and error bound with rational arithmetic."""
import argparse
from fractions import Fraction
import hashlib
import json
import os
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument("package", type=Path)
parser.add_argument("directory", type=Path)
parser.add_argument("output", type=Path)
args = parser.parse_args()
worker = args.package.resolve() / "quantum-worker.exe"
env = dict(os.environ, QALCULATE_DEFINITIONS_DIR=str(worker.parent / "data"))
records_path = args.directory / "records.json"
records = json.loads(records_path.read_bytes())
cases = []


def verify(number, bindings, expected):
    record = records[number - 1]
    assert record["id"].endswith(f"M{number}-original") and record["restored_same"]
    fields = ("display", "copy", "second_copy") if number == 219 else ("copy", "second_copy")
    for form in {record[key] for key in fields}:
        expression = form
        for name, value in bindings.items():
            symbol = "y" if name == "y" else f"'{name}'"
            expression = f"replace(({expression}),{symbol},({value}))"
        proc = subprocess.run([worker, "--json"], input=("quantum:" + expression).encode(),
                              env=env, timeout=30, capture_output=True)
        assert proc.returncode == 0, (number, bindings, form[:60], proc.stderr.decode())
        result = json.loads(proc.stdout)
        assert not result["approximate"] and result["copy_text"] == str(int(expected)), (
            number, bindings, result["copy_text"])
    cases.append(dict(id=record["id"], values={k:str(v) for k,v in bindings.items()}, expected=expected))


for m in (4, 5, 6):
    for y in (3 * 2**(m-4), 3 * 2**(m-4) + 1):
        verify(219, dict(m=m,y=y), Fraction(2**m,y) == Fraction(16,3))

for r in (1, 2, 5, 6, 21):
    limit = Fraction(1, 2*r*(r+1))
    for epsilon in (0, limit/2, -limit/2, limit, -limit, 3*limit, -3*limit):
        bound = Fraction(r, 2*r+1)
        actual = abs(Fraction(epsilon*r*r, 1+epsilon*r))
        verify(243, {"r":r, "ε":epsilon}, abs(epsilon) < limit)
        verify(246, {"r":r, "ε":epsilon}, actual <= bound < Fraction(1,2))

for r in (3, 5, 6):
    for m in (4, 6):
        scale = 2**m
        for y in range(scale//r - 1, scale//r + 3):
            verify(234, dict(m=m, r=r, y=y),
                   abs(Fraction(y, scale) - Fraction(1,r)) < Fraction(1,2*r*(r+1)))

for n, u, v in ((5,1,3), (7,2,5), (21,1,6)):
    for distance in (0, Fraction(1,4*n*n), Fraction(1,2*n*n), Fraction(-1,n*n)):
        alpha = Fraction(u,v) + distance
        verify(282, {"N":n, "u":u, "v":v, "α":alpha}, abs(distance) < Fraction(1,2*n*n))

report = dict(worker_sha256=hashlib.sha256(worker.read_bytes()).hexdigest(),
              windows_records_sha256=hashlib.sha256(records_path.read_bytes()).hexdigest(), cases=cases)
args.output.write_bytes((json.dumps(report, ensure_ascii=False, indent=2)+"\n").encode())
print(len(cases), "exact substitution cases passed")
