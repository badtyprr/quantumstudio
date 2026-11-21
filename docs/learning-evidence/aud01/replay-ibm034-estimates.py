"""Evaluate the error bounds and iteration update in the Grover lesson."""
import argparse
from decimal import Decimal, localcontext
from fractions import Fraction
from hashlib import sha256
import json
import os
import re
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument("worker", type=Path)
worker = parser.parse_args().worker.resolve()
env = dict(os.environ, QALCULATE_DEFINITIONS_DIR=str(worker.parent / "data"))
inventory = json.loads(Path(__file__).with_name("ibm034-inventory.json").read_bytes())
indices = (26, 28, 40, 137)
sources = [inventory["rows"][i-1] for i in indices]
assert all(row["id"].endswith(f"M{i:03}") for row,i in zip(sources,indices))


def calculate(expression, approximate):
    command = [worker, "--json"]
    if approximate:
        command.append("--approx")
    result = subprocess.run(command, input=("quantum:"+expression).encode(), env=env,
                            capture_output=True, check=True, timeout=30)
    data = json.loads(result.stdout)
    if not approximate:
        assert not data["approximate"]
    value = Fraction(data["copy_text"].replace(" ∕ ", "/"))
    return Decimal(value.numerator) / Decimal(value.denominator)


cases, small_angles, updates = [], [], []
with localcontext() as context:
    context.prec = 45
    tolerance = Decimal("1e-27")
    for qubits in range(1, 10):
        size = 2**qubits
        for marked in sorted({1, 2, size//2, size-1, size}):
            angle = f"asin(sqrt({marked}/{size}))"
            theta = calculate(angle, True)
            iterations = calculate(f"floor(pi/(4*{angle}))", False)
            # With every input marked, theta is pi/2 and both errors are exactly zero.
            target = calculate(f"pi/(4*{angle})-1/2", marked != size)
            error = calculate(f"abs((2*{iterations}+1)*{angle}-pi/2)", marked != size)
            assert abs(iterations-target) <= Decimal("0.5")+tolerance
            assert error <= theta+tolerance
            cases.append(dict(size=size,marked=marked,iterations=int(iterations),phase_error=str(error)))
        x = Decimal(1)/Decimal(size).sqrt()
        root = (1-x*x).sqrt()
        # Integrate (1-t²)^(-1/2)-1 from 0 to x, bounding its rationalized denominator at x.
        upper = x**3/(3*root*(1+root))
        error = calculate(f"asin(sqrt(1/{size}))-sqrt(1/{size})", True)
        assert 0 < error <= upper
        assert not small_angles or error < Decimal(small_angles[-1]["error"])
        small_angles.append(dict(size=size,error=str(error),upper_bound=str(upper)))
    for current in [*range(1,33), 2**53-1, 2**53, 2**53+1]:
        # Evaluate the right side of the assignment in exact arithmetic.
        updated = calculate(f"ceil((5/4)*{current})", False)
        assert updated == (5*current+3)//4
        updates.append(dict(current=current,updated=int(updated)))

# Fix the sign by choosing a constant oracle, then check each signed term.
constant_oracles = []
for i in (152,153):
    row = inventory["rows"][i-1]
    for size in (2,4,8):
        ket = "(["+";".join(["1"]*size)+f"]/sqrt({size}))"
        bra = "(["+",".join(["1"]*size)+f"]/sqrt({size}))"
        identity = f"(identity({size}))"
        for sign in (1,-1):
            oracle = f"({sign}*{identity})"
            step = f"((2*{ket}*{bra}-{identity})*{oracle})"
            literal = row["literal"].replace("G",step).replace("Z_f",oracle).replace(r"\mathbb{I}",identity)
            literal = re.sub(r"\\vert\s*u\s*\\rangle",lambda _:ket,literal)
            literal = re.sub(r"\\langle\s*u\s*\\vert",lambda _:bra,literal)
            pieces = literal.split(r"\pm")
            for wrong_term in range(len(pieces)):
                expr = pieces[0]
                for j,part in enumerate(pieces[1:],1):
                    expr += ("-" if (sign < 0) != (j == wrong_term) else "+") + part
                value = calculate(expr,False)
                assert value == int(wrong_term == 0), (i,size,sign,wrong_term,value)
                constant_oracles.append(dict(source_id=row["id"],size=size,oracle_sign=sign,
                                             reversed_term=wrong_term,equality=int(value)))

print(json.dumps(dict(source_sha256=inventory["source_sha256"],worker_sha256=sha256(worker.read_bytes()).hexdigest(),
                      source_ids=[r["id"] for r in sources],iteration_estimates=cases,
                      small_angle_estimates=small_angles,iteration_updates=updates,constant_oracles=constant_oracles),indent=2))
