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


def bound_forms(key, bindings):
    for form in ("display", "copy", "second_copy"):
        expr = records[key][form]
        for name, value in bindings:
            expr = f"replace(({expr}),{name},({value}))"
        yield form, expr


def exact(expression):
    proc = subprocess.run([worker, "--json"], input=("quantum:" + expression).encode(),
                          env=env, timeout=30, capture_output=True, check=True)
    return json.loads(proc.stdout)["copy_text"]


def verify(number, bindings, truth, reference=None):
    key = inventory["rows"][number-1]["id"]
    evaluated = {}
    for form, expr in bound_forms(key, bindings):
        if reference is not None:
            expr = f"(({expr}) = ({reference}))"
        if expr not in evaluated:
            evaluated[expr] = exact(expr)
        assert evaluated[expr] == str(int(truth)), (key, form, bindings, truth, evaluated[expr])
    case = dict(bindings=bindings, expected=int(truth))
    if reference is not None:
        case["reference"] = reference
    checks.setdefault(key, []).append(case)


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


# Split a two-qubit Fourier circuit into its partial transform, phase, H and swap.
for x in (0, 1):
    for a in (0, 1):
        common = [("m", 2), ("ω_2", "-1"), ("ω_4", "i"), ("x", x), ("a", a)]
        verify(247, [("|x>", f"basis({x},2)"), ("|a>", f"basis({a},2)")] + common, True)
        for y in (0, 1):
            for b in (0, 1):
                for root in ("-1", "1"):
                    roots = [("m", 2), ("ω_2", root), ("ω_4", "i")]
                    labels = [("x", x), ("a", a), ("y", y), ("b", b)]
                    for number in (258, 265):
                        verify(number, roots + labels, root == "-1" or not (x and y))
        phase = f"(P({a}*pi/2)*H*basis({x},2))"
        last = f"basis({a},2)"
        column = f"(fourier(4)*basis({2*x+a},4))"
        for number, state in [(251, f"{phase} @ {last}"), (252, f"{phase} @ (H*{last})"),
                              (253, column)]:
            bound = [("|a>", last)] + common if number == 251 else common
            verify(number, bound, True, state)
            verify(number, bound, False, f"-({state})")
        verify(275, common, True)
        wrong_root = [("m", 2), ("ω_2", "1"), ("ω_4", "i"), ("x", x), ("a", a)]
        verify(247, [("|x>", f"basis({x},2)"), ("|a>", last)] + wrong_root, x == 0)
        verify(275, wrong_root, x == 0)

# Inverse Fourier estimation returns the exact basis label for grid phases.
for width in (1, 2):
    size = 2**width
    for y in range(size):
        theta = f"{y}/{size}"
        target = "|1>"
        values = [("ψ", target), ("m", width)]
        for shift in (0, 1):
            gate = f"P(2*pi*({y+shift})/{size})"
            verify(313, values + [("U", gate), ("θ", theta)], shift == 0)
        verify(317, [("|y>", f"basis({y},{size})")] + values + [("y", y), (f"ω_{size}", f"exp(2*pi*i/{size})")], True)
        verify(317, [("|y>", f"basis({y},{size})")] + values + [("y", y), (f"ω_{size}", "1")], y == 0)
        for z in range(size):
            verify(325, values + [("θ", theta)], z == y, f"{target} @ basis({z},{size})")
            for probability in (0, 1):
                verify(328, [("p_y", probability), ("m", width), ("θ", theta), ("y", z)],
                       probability == int(y == z))


# Repeated lesson labels and arithmetic share expectations, but each row uses
# its own three Windows results. Only identical bound expressions share work.
simple = {}
for label in ("m", "N", "x", "y", "a", "k", "p_y", r"\theta", r"\alpha"):
    symbol = {r"\theta": "θ", r"\alpha": "α"}.get(label, label)
    simple[label] = [([(symbol, value)], value) for value in ("1/4", "3")]
for label in ("U", "V"):
    simple[label] = [([(label, gate)], gate) for gate in ("X", "Z")]
simple[r"\vert\psi\rangle"] = [([("ψ", ket)], ket) for ket in ("|0>", "|->")]
for label in ("0", "1", "2", "4", "1/2", "1/4"):
    simple[label] = [([], label)]
simple[r"40\%"] = [([], "2/5")]
simple[r"25\%"] = [([], "1/4")]
for width in (2, 3):
    size = 2**width
    for label, expected in [("m-1", width-1), ("2^m", size),
                            ("1/2^m", f"1/{size}"), ("2^{-m}", f"1/{size}")]:
        simple.setdefault(label, []).append(([("m", width)], str(expected)))
    for y in (0, size-1):
        simple.setdefault("y/2^m", []).append(([("m", width), ("y", y)], f"{y}/{size}"))
    for n in (size, size+1):
        simple.setdefault("N = 2^m", []).append(([("m", width), ("N", n)], str(int(n == size))))
for label, expected in [(r"\theta = 0", "0"), (r"\theta = 1/2", "1/2"), (r"\theta = 1", "1")]:
    simple[label] = [([("θ", value)], str(int(value == expected))) for value in (expected, "3/4")]

simple_rows = {}
evaluated_simple = set()
for row in inventory["rows"]:
    literal = row["literal"]
    if literal[1:-1] not in simple:
        continue
    cases = simple[literal[1:-1]]
    group = simple_rows.setdefault(literal, dict(rows=[], cases=cases))
    group["rows"].append(row["id"])
    for bindings, expected in cases:
        for form, expr in bound_forms(row["id"], bindings):
            test = f"(({expr}) = ({expected}))"
            if test in evaluated_simple:
                continue
            assert exact(test) == "1", (row["id"], form, test)
            evaluated_simple.add(test)

report = dict(source=inventory["source"], worker_sha256=hashlib.sha256(worker.read_bytes()).hexdigest(),
              forms=["Windows display", "Windows Copy", "Windows Copy after re-entry"], checks=checks, repeated_expressions=simple_rows)
args.output.write_bytes((json.dumps(report, indent=2, ensure_ascii=False) + "\n").encode())
