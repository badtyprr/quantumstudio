"""Verify lesson equations against independent values using the three Windows text forms."""
import argparse
from fractions import Fraction
import hashlib
import json
import os
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument("worker", type=Path)
parser.add_argument("records", type=Path)
parser.add_argument("output", type=Path)
args = parser.parse_args()
worker = args.worker.resolve()
env = dict(os.environ, QALCULATE_DEFINITIONS_DIR=str(worker.parent / "data"))
records = {r["id"]: r for r in json.loads(args.records.read_bytes())}
inventory = json.loads(Path(__file__).with_name("ibm028-inventory.json").read_bytes())
checks = {}


def verify(number, bindings, truth):
    key = inventory["rows"][number-1]["id"]
    record = records[key]
    evaluated = {}
    for form in ("display", "copy", "second_copy"):
        expr = record[form]
        for name, value in bindings:
            expr = f"replace(({expr}),{name},({value}))"
        if expr not in evaluated:
            proc = subprocess.run([worker, "--json"], input=("quantum:" + expr).encode(),
                              env=env, timeout=30, capture_output=True, check=True)
            evaluated[expr] = json.loads(proc.stdout)["copy_text"]
        result = evaluated[expr]
        assert result == str(int(truth)), (key, form, bindings, truth, result)
    checks.setdefault(key, []).append(dict(bindings=bindings, expected=int(truth)))


# Independent one-qubit phase gates provide the expected high and low controls.
for number, stage in [(15, 1), (90, 1), (96, 2), (102, 3), (106, 3)]:
    for theta in (("0",) if stage == 1 else ("0", "1/8", "1/4", "3/8", "1/2")):
        for target in ("|0>", "|->"):
            high = "|+>" if stage < 3 else f"(P(4*pi*({theta}))*|+>)"
            low = "|+>" if stage < 2 else f"(P(2*pi*({theta}))*|+>)"
            for state, truth in [(low, True), (f"(Z*{low})", False)]:
                controls = state if number == 15 else f"{high} @ {state}"
                bindings = [("ψ", target)]
                if stage > 1:
                    bindings.append(("θ", theta))
                verify(number, bindings + [(f"pi_{stage}", f"{target} @ {controls}")], truth)

for dimension in (2, 3, 4):
    root = f"exp(2*pi*i/{dimension})"
    reference = [("N", dimension), ("ω_N", root)]
    verify(183, reference, True)
    verify(183, [("N", dimension), ("ω_N", "1")], False)
    for y in range(dimension):
        column = f"fourier({dimension})*basis({y},{dimension})"
        neighbor = f"fourier({dimension})*basis({(y+1)%dimension},{dimension})"
        for state, truth in [(column, True), (neighbor, False)]:
            verify(198, [("φ_y", state), ("y", y)] + reference, truth)
        verify(206, [("φ_y", column)], True)
        verify(206, [("φ_y", "2*("+column+")")], False)
        for z in range(dimension):
            other = f"fourier({dimension})*basis({z},{dimension})"
            for state, reference_y in [(column, y), (neighbor, (y+1)%dimension)]:
                verify(199, [("φ_z", other), ("φ_y", state), ("z", z), ("y", y)] + reference,
                       (z == reference_y) == (z == y))

for width in (1, 2, 3):
    dim = 2**width
    for index in range(dim):
        for basis, truth in [(index, True), ((index+1)%dim, False)]:
            verify(269, [("|u>", f"basis({basis},{dim})"), ("m", width), ("u", index),
                         (f"ω_{dim}", f"exp(2*pi*i/{dim})")], truth)

for width in (1, 2, 3, 4):
    for offset in (0, 1):
        verify(290, [("s_m", width**2 + offset), ("m", width)], offset == 0)

for y in range(4):
    for theta in (Fraction(y, 4), Fraction(1, 8)):
        values = [("m", 2), ("θ", str(theta)), ("y", y)]
        phase = f"exp(2*pi*i*(({theta})-({y}/4)))"
        for sign in ("", "-"):
            verify(331, [("α", sign+phase)] + values, not sign)
        verify(332, values, True)
        if theta != Fraction(y, 4):
            probability = "(2+sqrt(2))/8" if y in (0, 1) else "(2-sqrt(2))/8"
            for offset in ("", "+1/8"):
                verify(336, [("p_y", probability+offset)] + values, not offset)

for delta in (Fraction(-3, 4), Fraction(-1, 2), Fraction(-1, 4), Fraction(0),
              Fraction(1, 4), Fraction(1, 2), Fraction(3, 4)):
    verify(338, [("δ", str(delta))], True)
    if delta:
        verify(341, [("δ", str(delta))], abs(delta) <= Fraction(1, 2))
    verify(342, [("δ", str(delta))], abs(delta) <= Fraction(1, 2))
for y, theta in [(0, "0"), (1, "1/4"), (0, "1/8"), (1, "0"), (0, "1/2"), (0, "3/4")]:
    values = [("m", 2), ("θ", theta), ("y", y)]
    delta = abs(Fraction(theta) - Fraction(y, 4))
    verify(356, values, True)
    verify(373, values, Fraction(1, 4) <= delta <= Fraction(1, 2))

report = dict(source=inventory["source"], worker_sha256=hashlib.sha256(worker.read_bytes()).hexdigest(),
              forms=["Windows display", "Windows Copy", "Windows Copy after re-entry"], checks=checks)
args.output.write_bytes((json.dumps(report, indent=2, ensure_ascii=False) + "\n").encode())
