"""Replay the four Boolean circuit figures and M054-M060 on an exact worker.

Each bit of a calculator integer is one independent row of the truth table.
A wire split records a FANOUT. In the expanded model XOR uses the two NOT,
two AND and one OR gates and two wire splits drawn in Boolean-circuit-XOR.
"""
from collections import Counter
from decimal import Decimal
import json
from pathlib import Path
import subprocess
import sys


worker = Path(sys.argv[1]).resolve()
evidence = json.loads(Path(__file__).with_name("ibm024-cost-baseline.json").read_bytes())
literals = {row["id"][-4:]: row["literal"].strip("$").strip() for row in evidence["rows"]}


def exact(expression):
    p = subprocess.run([worker, "--json"], input=expression.encode(), capture_output=True,
                       check=True, timeout=15)
    result = json.loads(p.stdout)
    assert not result["approximate"], expression
    value = Decimal(result["copy_text"])
    assert value == value.to_integral_value(), expression
    return int(value)


def lesson_value(formula, width):
    return exact(f"quantum:replace(({formula}),n,{width})")


class Circuit:
    def __init__(self, rows, native_xor):
        self.rows = rows
        self.native_xor = native_xor
        self.counts = Counter()

    def fanout(self, value):
        self.counts["FANOUT"] += 1
        return value, value

    def gate(self, name, expression):
        self.counts[name] += 1
        return exact(expression)

    def xor(self, a, b):
        if self.native_xor:
            return self.gate("XOR", f"xor({a},{b})")
        a1, a2 = self.fanout(a)
        b1, b2 = self.fanout(b)
        not_a = self.gate("NOT", f"bitcmp({a2},{self.rows},0)")
        not_b = self.gate("NOT", f"bitcmp({b1},{self.rows},0)")
        upper = self.gate("AND", f"{a1} & {not_b}")
        lower = self.gate("AND", f"{not_a} & {b2}")
        return self.gate("OR", f"{upper} | {lower}")

    def half(self, a, b):
        a1, a2 = self.fanout(a)
        b1, b2 = self.fanout(b)
        return self.xor(a1, b1), self.gate("AND", f"{a2} & {b2}")

    def full(self, a, b, carry):
        partial, first_carry = self.half(a, b)
        total, second_carry = self.half(carry, partial)
        return total, self.gate("OR", f"{first_carry} | {second_carry}")


for width in range(1, 5):
    inputs = [(a, b) for a in range(2**width) for b in range(2**width)]
    for native_xor in (False, True):
        circuit = Circuit(len(inputs), native_xor)
        wires = []
        for bit in range(width):
            a = sum(((x >> bit) & 1) << row for row, (x, y) in enumerate(inputs))
            b = sum(((y >> bit) & 1) << row for row, (x, y) in enumerate(inputs))
            total, carry = circuit.half(a, b) if bit == 0 else circuit.full(a, b, carry)
            wires.append(total)
        wires.append(carry)
        for row, (a, b) in enumerate(inputs):
            answer = sum(((wire >> row) & 1) << bit for bit, wire in enumerate(wires))
            assert answer == a + b, (width, a, b, answer)
        counts = circuit.counts
        size = sum(counts.values())

        if native_xor:
            actual = [counts["AND"], counts["XOR"], counts["OR"], counts["FANOUT"],
                      size, size - counts["FANOUT"]]
            expected = [lesson_value(literals[f"M{i:03}"], width) for i in range(55, 61)]
            assert actual == expected, (width, actual, expected)
        else:
            for side in literals["M054"].split("="):
                assert lesson_value(side, width) == size, (width, side, size)
        print(f"width={width} native_xor={native_xor} rows={len(inputs)} gates={size}")
